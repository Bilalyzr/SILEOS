// lib/features/live_classes/presentation/join_live_class_screen.dart
import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:jitsi_meet_flutter_sdk/jitsi_meet_flutter_sdk.dart';
import '../../../config/design_tokens.dart';
import '../../../shared/widgets/common/app_button.dart';
import '../../../shared/widgets/common/app_loader.dart';
import '../../../shared/widgets/common/error_display.dart';
import '../../auth/presentation/providers/auth_provider.dart';
import '../../auth/presentation/providers/auth_state.dart';
import '../domain/entities/live_class.dart';
import 'providers.dart';

/// Minimal precheck -> join-token -> JitsiMeet().join() flow, per
/// docs/superpowers/plans/2026-09-02-live-classes.md Task 9 binding.
///
/// Device pre-check here is intentionally light (a single "ready to join"
/// confirmation, not a full mic/cam level-meter like the web DevicePrecheck)
/// — the Jitsi Flutter SDK's own prejoin/native permission prompts are the
/// mobile equivalent, and there's no existing mobile precheck widget to
/// mirror (see the Task 9 report — conventions were followed as closely as
/// a genuinely new mobile-only flow allows).
class JoinLiveClassScreen extends ConsumerStatefulWidget {
  final int classId;
  const JoinLiveClassScreen({super.key, required this.classId});

  @override
  ConsumerState<JoinLiveClassScreen> createState() => _JoinLiveClassScreenState();
}

enum _JoinPhase { precheck, joining, inCall, left, error }

/// Attendance heartbeat cadence. Matches the web client (JitsiStage) and the
/// 2-minute staleness window the backend's attendance summary uses to decide
/// who is still in the room — beat twice per window so one dropped beat does
/// not drop a participant off the live count.
const _kHeartbeatInterval = Duration(seconds: 60);

class _JoinLiveClassScreenState extends ConsumerState<JoinLiveClassScreen> {
  final JitsiMeet _jitsiMeet = JitsiMeet();
  _JoinPhase _phase = _JoinPhase.precheck;
  String? _errorMessage;

  /// Periodic attendance heartbeat, live only while the conference is joined.
  /// Without it, mobile attendance accrued nothing between join and leave —
  /// the single final heartbeat on the way out gave the server one timestamp
  /// and therefore zero accumulated time, so mobile attendees were recorded
  /// as present-for-0-minutes and failed every attendance threshold.
  Timer? _heartbeatTimer;

  bool get _isModerator {
    final authState = ref.read(authProvider);
    return authState.maybeWhen(
      authenticated: (user) => user.isInstructor || user.isAdmin,
      orElse: () => false,
    );
  }

  Future<void> _startJoin() async {
    setState(() {
      _phase = _JoinPhase.joining;
      _errorMessage = null;
    });

    try {
      final result = await ref.refresh(liveClassJoinTokenProvider(widget.classId).future);
      await _joinJitsi(result);
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _phase = _JoinPhase.error;
        _errorMessage = e.toString();
      });
    }
  }

  Future<void> _joinJitsi(LiveClassJoinToken token) async {
    final moderator = _isModerator;
    final authState = ref.read(authProvider);
    final user = authState.maybeWhen(authenticated: (u) => u, orElse: () => null);

    // configOverrides per role — students join muted (mic + camera off) with
    // a restricted toolbar; the moderator (instructor/admin) keeps the full
    // set incl. recording, per the deviations file's role matrix and the
    // backend JWT's context.features (screen-sharing/recording true only for
    // the moderator token).
    final configOverrides = <String, Object?>{
      'startWithAudioMuted': !moderator,
      'startWithVideoMuted': !moderator,
      'prejoinPageEnabled': false,
      'disableDeepLinking': true,
      'requireDisplayName': false,
      'toolbarButtons': moderator
          ? [
              'microphone',
              'camera',
              'closedcaptions',
              'desktop',
              'fullscreen',
              'fodeviceselection',
              'hangup',
              'chat',
              'raisehand',
              'tileview',
              'select-background',
              'whiteboard',
              'recording',
            ]
          : [
              'microphone',
              'camera',
              'closedcaptions',
              'fullscreen',
              'fodeviceselection',
              'hangup',
              'chat',
              'raisehand',
              'tileview',
            ],
    };

    final featureFlags = <String, Object?>{
      'welcomepage.enabled': false,
      'prejoinpage.enabled': false,
      'invite.enabled': false,
      'meeting-name.enabled': false,
      'recording.enabled': moderator,
      'live-streaming.enabled': false,
      'screen-sharing.enabled': moderator,
      'add-people.enabled': false,
    };

    final options = JitsiMeetConferenceOptions(
      serverURL: token.jitsiUrl,
      room: token.roomName,
      token: token.jwt,
      configOverrides: configOverrides,
      featureFlags: featureFlags,
      userInfo: user == null
          ? null
          : JitsiMeetUserInfo(
              displayName: user.fullName,
              email: user.email,
            ),
    );

    final listener = JitsiMeetEventListener(
      conferenceJoined: (url) {
        if (!mounted) return;
        setState(() => _phase = _JoinPhase.inCall);
        _startHeartbeats();
      },
      conferenceTerminated: (url, error) {
        _stopHeartbeats();
        _handleLeft();
      },
      readyToClose: () {
        _stopHeartbeats();
        _handleLeft();
      },
    );

    await _jitsiMeet.join(options, listener);
  }

  void _startHeartbeats() {
    _heartbeatTimer?.cancel();
    // Beat once immediately so attendance starts accruing from the join
    // instant rather than 60s later, then on the interval.
    _sendHeartbeat();
    _heartbeatTimer = Timer.periodic(_kHeartbeatInterval, (_) => _sendHeartbeat());
  }

  void _stopHeartbeats() {
    _heartbeatTimer?.cancel();
    _heartbeatTimer = null;
  }

  Future<void> _sendHeartbeat() async {
    final result = await ref.read(liveClassRepositoryProvider).heartbeat(widget.classId);
    result.fold(
      (failure) {
        // 403 = access revoked mid-class (unenrolled, or the instructor
        // reassigned off it); 409 = the class ended or was cancelled. Both
        // are terminal for this session — the server will reject every
        // subsequent beat identically, so keeping the timer alive would just
        // retry a permanent failure once a minute for as long as the app
        // stays open. Anything else (network blip, 5xx) is transient: leave
        // the timer running so the next beat can recover.
        final terminal = failure.maybeWhen(
          forbidden: (_) => true,
          server: (_, statusCode) => statusCode == 403 || statusCode == 409,
          orElse: () => false,
        );
        if (terminal) _stopHeartbeats();
      },
      (_) {},
    );
  }

  void _handleLeft() {
    if (!mounted) return;
    _stopHeartbeats();
    setState(() => _phase = _JoinPhase.left);
    // Final heartbeat on the way out, best-effort — the session lifecycle is
    // server-truth anyway (heartbeats + join-token redemption).
    ref.read(liveClassRepositoryProvider).heartbeat(widget.classId);
    if (context.canPop()) {
      context.pop();
    } else {
      context.go('/live-classes');
    }
  }

  @override
  void dispose() {
    // Must cancel before super.dispose(): a Timer that fires after the State
    // is disposed would call ref.read() on a torn-down ConsumerState.
    _stopHeartbeats();
    if (_phase == _JoinPhase.inCall) {
      _jitsiMeet.hangUp();
    }
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final classAsync = ref.watch(liveClassByIdProvider(widget.classId));

    return Scaffold(
      appBar: AppBar(title: const Text('Join Live Class')),
      body: classAsync.when(
        data: (liveClass) => _buildBody(liveClass),
        loading: () => const BrandedLoader(),
        error: (error, stack) => ErrorDisplay(message: error.toString()),
      ),
    );
  }

  Widget _buildBody(LiveClass liveClass) {
    switch (_phase) {
      case _JoinPhase.precheck:
        return _PrecheckView(liveClass: liveClass, onJoin: _startJoin);
      case _JoinPhase.joining:
        return const BrandedLoader(message: 'Connecting to class…');
      case _JoinPhase.inCall:
        // The Jitsi SDK renders its own native full-screen conference UI; this
        // screen just needs to stay mounted underneath it.
        return const Center(child: Text('In class — return here when you leave.'));
      case _JoinPhase.left:
        return const Center(child: Text('You left the class.'));
      case _JoinPhase.error:
        return ErrorDisplay(
          message: _errorMessage ?? 'Could not join the class.',
          onRetry: _startJoin,
        );
    }
  }
}

class _PrecheckView extends StatelessWidget {
  final LiveClass liveClass;
  final VoidCallback onJoin;
  const _PrecheckView({required this.liveClass, required this.onJoin});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Padding(
      padding: const EdgeInsets.all(AppSpacing.md),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(Icons.video_camera_front_outlined, size: 64, color: theme.colorScheme.primary),
          const SizedBox(height: 16),
          Text(liveClass.title,
              style: theme.textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w700),
              textAlign: TextAlign.center),
          const SizedBox(height: 8),
          Text(
            'Check your microphone and camera permissions are allowed, then join. '
            'You will join muted by default.',
            style: theme.textTheme.bodyMedium,
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: 24),
          AppButton(text: 'Continue to class', onPressed: onJoin),
        ],
      ),
    );
  }
}
