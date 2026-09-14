import 'dart:io';
import 'package:flutter/foundation.dart';
import 'package:flutter/gestures.dart';
import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter/services.dart';
import '../../../core/utils/bunny_video.dart';
import '../../../config/app_config.dart';

/// A specialized video player for Bunny.net Stream videos.
///
/// Uses our custom native platform view 'sasha_bunny_player_view' for Android
/// to capture playback state changes (like completion/ended) and bubble them
/// back to Flutter.
class BunnyVideoPlayerWidget extends StatelessWidget {
  final String hlsUrl;
  final bool autoPlay;
  final int libraryId;
  final bool isPortrait;
  final VoidCallback? onEnded;

  const BunnyVideoPlayerWidget({
    super.key,
    required this.hlsUrl,
    required this.libraryId,
    this.autoPlay = false,
    this.isPortrait = false,
    this.onEnded,
  });

  @override
  Widget build(BuildContext context) {
    final uri = Uri.tryParse(hlsUrl);
    if (uri == null) {
      return const _ErrorPlaceholder(message: 'Invalid video URL');
    }

    final videoId = BunnyVideo.extractGuid(hlsUrl);
    if (videoId == null) {
      return const _ErrorPlaceholder(message: 'Could not extract Video ID');
    }

    final token = uri.queryParameters['token'];
    final expiresStr = uri.queryParameters['expires'];
    final expires = expiresStr != null ? int.tryParse(expiresStr) : null;

    return AspectRatio(
      aspectRatio: isPortrait ? 9 / 16 : 16 / 9,
      child: SashaBunnyPlayerView(
        videoId: videoId,
        libraryId: libraryId,
        token: token,
        expire: expires,
        isPortrait: isPortrait,
        onEnded: onEnded,
        // Prefer short-lived signed tokens (token/expire from the backend's
        // HLS URL); fall back to an access key only if one is provided via
        // --dart-define. Null means "use token auth only".
        accessKey:
            AppConfig.bunnyAccessKey.isEmpty ? null : AppConfig.bunnyAccessKey,
      ),
    );
  }
}

class SashaBunnyPlayerView extends StatefulWidget {
  final String? accessKey;
  final String videoId;
  final int libraryId;
  final String? token;
  final int? expire;
  final String? referer;
  final bool isPortrait;
  final bool isScreenShotProtectEnable;
  final VoidCallback? onEnded;

  const SashaBunnyPlayerView({
    super.key,
    required this.accessKey,
    required this.videoId,
    required this.libraryId,
    this.token,
    this.referer,
    this.expire,
    this.isPortrait = false,
    this.isScreenShotProtectEnable = false,
    this.onEnded,
  });

  @override
  State<SashaBunnyPlayerView> createState() => _SashaBunnyPlayerViewState();
}

class _SashaBunnyPlayerViewState extends State<SashaBunnyPlayerView> {
  static const MethodChannel _channel = MethodChannel('com.sashainfinity.sasha_lms/bunny_player');
  static final List<_SashaBunnyPlayerViewState> _activeStates = [];
  static bool _channelInitialized = false;

  static void _ensureChannelInitialized() {
    if (_channelInitialized) return;
    _channelInitialized = true;
    _channel.setMethodCallHandler((call) async {
      if (call.method == 'onEnded') {
        final videoId = call.arguments['videoId'] as String?;
        for (final state in List.from(_activeStates)) {
          if (state.widget.videoId == videoId && state.mounted) {
            state.widget.onEnded?.call();
          }
        }
      }
    });
  }

  @override
  void initState() {
    super.initState();
    SystemChrome.setPreferredOrientations([
      DeviceOrientation.portraitUp,
      DeviceOrientation.portraitDown,
      DeviceOrientation.landscapeLeft,
      DeviceOrientation.landscapeRight,
    ]);
    _activeStates.add(this);
    _ensureChannelInitialized();
  }

  @override
  void dispose() {
    _activeStates.remove(this);
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    const viewType = 'sasha_bunny_player_view';

    final Map<String, dynamic> creationParams = {
      'accessKey': widget.accessKey,
      'videoId': widget.videoId,
      'libraryId': widget.libraryId,
      'token': widget.token,
      'expire': widget.expire,
      'referer': widget.referer,
      'isPortrait': widget.isPortrait,
      'isScreenShotProtectEnable': widget.isScreenShotProtectEnable,
    };

    if (Platform.isAndroid) {
      return PlatformViewLink(
        viewType: viewType,
        surfaceFactory: (context, controller) {
          return AndroidViewSurface(
            controller: controller as AndroidViewController,
            gestureRecognizers: const <Factory<OneSequenceGestureRecognizer>>{},
            hitTestBehavior: PlatformViewHitTestBehavior.opaque,
          );
        },
        onCreatePlatformView: (PlatformViewCreationParams params) {
          return PlatformViewsService.initSurfaceAndroidView(
            id: params.id,
            viewType: viewType,
            layoutDirection: TextDirection.ltr,
            creationParams: creationParams,
            creationParamsCodec: const StandardMessageCodec(),
          )
            ..addOnPlatformViewCreatedListener(params.onPlatformViewCreated)
            ..create();
        },
      );
    }
    return const SizedBox();
  }
}

class _ErrorPlaceholder extends StatelessWidget {
  final String message;
  const _ErrorPlaceholder({required this.message});

  @override
  Widget build(BuildContext context) {
    return AspectRatio(
      aspectRatio: 16 / 9,
      child: Container(
        color: Colors.black,
        child: Center(
          child: Text(
            message,
            style: const TextStyle(color: Colors.white),
          ),
        ),
      ),
    );
  }
}
