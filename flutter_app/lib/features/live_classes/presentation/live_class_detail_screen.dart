// lib/features/live_classes/presentation/live_class_detail_screen.dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';
import '../../../config/design_tokens.dart';
import '../../../shared/widgets/common/app_loader.dart';
import '../../../shared/widgets/common/error_display.dart';
import '../../../shared/widgets/video/video_player_widget.dart';
import '../domain/entities/live_class.dart';
import 'providers.dart';

/// Class detail: schedule info + Join button while joinable, or the
/// recording via the EXISTING [VideoPlayerWidget] (reused as-is — it already
/// detects Bunny HLS urls and renders BunnyVideoPlayerWidget) once the class
/// has ended and a recording is available.
class LiveClassDetailScreen extends ConsumerWidget {
  final int classId;
  const LiveClassDetailScreen({super.key, required this.classId});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final classAsync = ref.watch(liveClassByIdProvider(classId));

    return Scaffold(
      appBar: AppBar(title: const Text('Live Class')),
      body: classAsync.when(
        data: (liveClass) => _DetailBody(liveClass: liveClass),
        loading: () => const BrandedLoader(),
        error: (error, stack) => ErrorDisplay(
          message: error.toString(),
          onRetry: () => ref.refresh(liveClassByIdProvider(classId)),
        ),
      ),
    );
  }
}

class _DetailBody extends ConsumerWidget {
  final LiveClass liveClass;
  const _DetailBody({required this.liveClass});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final theme = Theme.of(context);
    final dateFmt = DateFormat('EEE, d MMM yyyy · h:mm a');

    return SingleChildScrollView(
      padding: const EdgeInsets.all(AppSpacing.md),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(liveClass.title,
              style: theme.textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.w800)),
          const SizedBox(height: 8),
          Text(
            dateFmt.format(liveClass.scheduledStart.toLocal()),
            style: theme.textTheme.bodyMedium?.copyWith(color: theme.colorScheme.onSurface.withOpacity(0.7)),
          ),
          if (liveClass.description != null) ...[
            const SizedBox(height: 16),
            Text(liveClass.description!, style: theme.textTheme.bodyMedium),
          ],
          const SizedBox(height: 24),
          if (liveClass.isEnded) OutlinedButton.icon(onPressed: () => context.push('/recordings/${liveClass.id}'), icon: const Icon(Icons.description_outlined), label: const Text('Lesson notes & transcript')),
          if (liveClass.isEnded && liveClass.hasRecording)
            _RecordingSection(classId: liveClass.id)
          else
            _JoinSection(liveClass: liveClass),
        ],
      ),
    );
  }
}

class _JoinSection extends StatelessWidget {
  final LiveClass liveClass;
  const _JoinSection({required this.liveClass});

  @override
  Widget build(BuildContext context) {
    final canJoin = liveClass.isLive || liveClass.canStart;
    final label = liveClass.isLive
        ? 'Join now'
        : liveClass.isEnded
            ? 'Class ended'
            : liveClass.isCancelled
                ? 'Class cancelled'
                : 'Join opens 15 minutes before start';

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        SizedBox(
          height: 48,
          child: ElevatedButton(
            onPressed: canJoin ? () => context.push('/live-classes/${liveClass.id}/join') : null,
            child: Text(canJoin ? 'Join class' : label),
          ),
        ),
        if (!canJoin) ...[
          const SizedBox(height: 8),
          Text(label, textAlign: TextAlign.center, style: Theme.of(context).textTheme.bodySmall),
        ],
      ],
    );
  }
}

class _RecordingSection extends ConsumerWidget {
  final int classId;
  const _RecordingSection({required this.classId});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final playbackAsync = ref.watch(liveClassRecordingPlaybackProvider(classId));

    return playbackAsync.when(
      data: (playback) {
        if (playback == null) {
          return const EmptyState(
            message: 'Recording is not available yet.',
            icon: Icons.movie_creation_outlined,
          );
        }
        return ClipRRect(
          borderRadius: AppRadius.lgAll,
          child: VideoPlayerWidget(videoUrl: playback.hlsUrl),
        );
      },
      loading: () => const AppLoader(),
      error: (error, stack) => ErrorDisplay(
        message: error.toString(),
        onRetry: () => ref.refresh(liveClassRecordingPlaybackProvider(classId)),
      ),
    );
  }
}
