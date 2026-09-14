// lib/features/live_classes/presentation/live_class_list_screen.dart
import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../../config/design_tokens.dart';
import '../../../config/theme.dart';
import '../../../shared/widgets/common/app_loader.dart';
import '../../../shared/widgets/common/error_display.dart';
import '../domain/entities/live_class.dart';
import 'providers.dart';

/// Upcoming live classes for the current user's enrolled/taught courses, with
/// a LIVE badge and a per-card countdown driven by server time (server_ts on
/// each fetched class, offset against local elapsed time — see
/// [_LiveClassCard] for the offset math, mirroring the web ClassCountdown
/// helper from docs/superpowers/plans/2026-09-02-live-classes.md Task 7).
class LiveClassListScreen extends ConsumerStatefulWidget {
  const LiveClassListScreen({super.key});

  @override
  ConsumerState<LiveClassListScreen> createState() => _LiveClassListScreenState();
}

class _LiveClassListScreenState extends ConsumerState<LiveClassListScreen> {
  @override
  Widget build(BuildContext context) {
    final upcomingAsync = ref.watch(liveClassesProvider(scope: 'upcoming'));

    return Scaffold(
      appBar: AppBar(title: const Text('Live Classes')),
      body: RefreshIndicator(
        onRefresh: () async {
          ref.invalidate(liveClassesProvider);
        },
        child: upcomingAsync.when(
          data: (classes) => _buildList(classes),
          loading: () => const BrandedLoader(),
          error: (error, stack) => ErrorDisplay(
            message: error.toString(),
            onRetry: () => ref.refresh(liveClassesProvider(scope: 'upcoming')),
          ),
        ),
      ),
    );
  }

  Widget _buildList(List<LiveClass> classes) {
    if (classes.isEmpty) {
      return const EmptyState(
        message: 'No upcoming live classes yet.',
        icon: Icons.video_camera_front_outlined,
      );
    }
    return ListView.separated(
      padding: const EdgeInsets.all(AppSpacing.md),
      itemCount: classes.length,
      separatorBuilder: (_, __) => const SizedBox(height: AppSpacing.md),
      itemBuilder: (context, index) => _LiveClassCard(liveClass: classes[index]),
    );
  }
}

class _LiveClassCard extends StatefulWidget {
  final LiveClass liveClass;
  const _LiveClassCard({required this.liveClass});

  @override
  State<_LiveClassCard> createState() => _LiveClassCardState();
}

class _LiveClassCardState extends State<_LiveClassCard> {
  Timer? _ticker;
  Duration _remaining = Duration.zero;
  late final DateTime _fetchedAtLocal;

  @override
  void initState() {
    super.initState();
    _fetchedAtLocal = DateTime.now();
    _recompute();
    _ticker = Timer.periodic(const Duration(seconds: 1), (_) => _recompute());
  }

  @override
  void dispose() {
    _ticker?.cancel();
    super.dispose();
  }

  /// offset = serverTs - fetchedAtLocal (when the list was fetched), applied
  /// to "now" so the countdown stays correct even if the device clock is
  /// skewed from the server — mirrors ClassCountdown.computeRemaining on web.
  void _recompute() {
    final liveClass = widget.liveClass;
    final offset = liveClass.serverTs.difference(_fetchedAtLocal);
    final nowOnServer = DateTime.now().add(offset);
    final target = liveClass.countdownTarget;
    final remaining = target.difference(nowOnServer);
    if (!mounted) return;
    setState(() => _remaining = remaining.isNegative ? Duration.zero : remaining);
  }

  String get _countdownText {
    final liveClass = widget.liveClass;
    if (liveClass.isLive) return 'LIVE now';
    if (liveClass.isEnded) return 'Ended';
    if (liveClass.isCancelled) return 'Cancelled';
    if (_remaining == Duration.zero) return 'Starting soon';
    final d = _remaining;
    if (d.inDays > 0) return 'Starts in ${d.inDays}d ${d.inHours % 24}h';
    if (d.inHours > 0) return 'Starts in ${d.inHours}h ${d.inMinutes % 60}m';
    if (d.inMinutes > 0) return 'Starts in ${d.inMinutes}m';
    return 'Starts in <1m';
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;
    final liveClass = widget.liveClass;

    return DecoratedBox(
      decoration: BoxDecoration(
        color: theme.cardTheme.color,
        borderRadius: AppRadius.lgAll,
        border: Border.all(color: isDark ? AppTheme.borderDark : AppTheme.borderLight),
        boxShadow: isDark ? null : AppShadows.soft,
      ),
      child: Material(
        type: MaterialType.transparency,
        child: InkWell(
          borderRadius: AppRadius.lgAll,
          onTap: () => context.push('/live-classes/${liveClass.id}'),
          child: Padding(
            padding: const EdgeInsets.all(AppSpacing.card),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    if (liveClass.isLive) const _LiveBadge(),
                    if (liveClass.isLive) const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        liveClass.title,
                        style: theme.textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w700),
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 8),
                Text(
                  _countdownText,
                  style: theme.textTheme.bodyMedium?.copyWith(
                    color: liveClass.isLive ? AppTheme.danger : theme.colorScheme.primary,
                    fontWeight: FontWeight.w600,
                  ),
                ),
                const SizedBox(height: 12),
                SizedBox(
                  width: double.infinity,
                  child: ElevatedButton(
                    onPressed: () => context.push('/live-classes/${liveClass.id}'),
                    child: Text(liveClass.isLive ? 'Join now' : 'View details'),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _LiveBadge extends StatelessWidget {
  const _LiveBadge();

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(
        color: AppTheme.danger,
        borderRadius: BorderRadius.circular(AppRadius.pill),
      ),
      child: const Text(
        'LIVE',
        style: TextStyle(color: Colors.white, fontSize: 11, fontWeight: FontWeight.w800),
      ),
    );
  }
}
