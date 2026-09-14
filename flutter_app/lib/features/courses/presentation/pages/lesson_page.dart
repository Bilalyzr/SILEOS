import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../providers/course_provider.dart';
import '../providers/video_playback_provider.dart';
import '../widgets/next_lesson_card.dart';
import '../../domain/entities/course.dart';
import '../../domain/entities/lesson.dart';
import '../../../../core/utils/bunny_video.dart';
import '../../../../shared/widgets/video/video_player_widget.dart';
import '../../../../shared/widgets/common/app_loader.dart';
import '../../../../shared/widgets/common/app_button.dart';
import '../../../../shared/widgets/common/error_display.dart';

class LessonPage extends ConsumerStatefulWidget {
  final String lessonId;

  const LessonPage({super.key, required this.lessonId});

  @override
  ConsumerState<LessonPage> createState() => _LessonPageState();
}

class _LessonPageState extends ConsumerState<LessonPage> {
  bool _isCompleting = false;
  final GlobalKey<State> _videoPlayerKey = GlobalKey<State>();

  Future<void> _markAsComplete(int courseId, int lessonId) async {
    setState(() {
      _isCompleting = true;
    });

    final result = await ref.read(completeLessonUseCaseProvider).call(
          courseId: courseId,
          lessonId: lessonId,
        );

    setState(() {
      _isCompleting = false;
    });

    result.fold(
      (failure) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Failed: ${failure.message}')),
        );
      },
      (_) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Lesson marked as complete!')),
        );
        // Refresh course to update progress (and the next-lesson lookup).
        ref.invalidate(courseByIdProvider(courseId.toString()));
      },
    );
  }

  /// The lesson immediately after [current] within its course (by `order`).
  /// Returns null when [current] is the last lesson. `number` is the next
  /// lesson's 1-based position.
  ({Lesson lesson, int number})? _nextLesson(Course course, Lesson current) {
    if (course.lessons.isEmpty) return null;
    final sorted = [...course.lessons]
      ..sort((a, b) => a.order.compareTo(b.order));
    final idx = sorted.indexWhere((l) => l.id == current.id);
    if (idx < 0 || idx + 1 >= sorted.length) return null;
    return (lesson: sorted[idx + 1], number: idx + 2);
  }

  @override
  Widget build(BuildContext context) {
    final lessonAsync = ref.watch(lessonByIdProvider(widget.lessonId));
    final theme = Theme.of(context);
    final isLandscape = MediaQuery.orientationOf(context) == Orientation.landscape;

    return Scaffold(
      appBar: isLandscape ? null : AppBar(
        title: const Text('Lesson'),
      ),
      body: lessonAsync.when(
        data: (lesson) {
          // Sibling lessons live on the parent course, so a "next lesson"
          // becomes available once that course has loaded.
          final next =
              ref.watch(courseByIdProvider(lesson.courseId)).maybeWhen(
                    data: (course) => _nextLesson(course, lesson),
                    orElse: () => null,
                  );
          // Decide the video source. A genuine YouTube link plays directly;
          // anything else — direct files and Bunny URLs, including the
          // `mediadelivery.net` embed links the CMS sometimes stored in the
          // youtube field — is resolved to a playable URL first.
          final yt = lesson.youtubeUrl;
          final isYoutube =
              yt != null && yt.isNotEmpty && !BunnyVideo.isBunnyUrl(yt);
          final hasDirectVideo =
              lesson.videoUrl != null && lesson.videoUrl!.isNotEmpty;
          final videoSource = hasDirectVideo ? lesson.videoUrl : yt;

          final videoPlayer = isYoutube && !hasDirectVideo
              ? VideoPlayerWidget(
                  key: _videoPlayerKey,
                  youtubeUrl: yt,
                  autoPlay: true,
                  videoDuration: lesson.duration,
                  nextVideoTitle: next?.lesson.title,
                  onPlayNext: next != null
                      ? () => context.pushReplacement('/lessons/${next.lesson.id}')
                      : null,
                )
              : ref.watch(playableVideoUrlProvider(videoSource)).when(
                    data: (url) => VideoPlayerWidget(
                      key: _videoPlayerKey,
                      videoUrl: url,
                      autoPlay: true,
                      videoDuration: lesson.duration,
                      nextVideoTitle: next?.lesson.title,
                      onPlayNext: next != null
                          ? () => context.pushReplacement('/lessons/${next.lesson.id}')
                          : null,
                    ),
                    loading: () => const AspectRatio(
                      aspectRatio: 16 / 9,
                      child: Center(child: CircularProgressIndicator()),
                    ),
                    error: (_, __) => VideoPlayerWidget(
                      key: _videoPlayerKey,
                      videoUrl: videoSource,
                      autoPlay: true,
                      videoDuration: lesson.duration,
                      nextVideoTitle: next?.lesson.title,
                      onPlayNext: next != null
                          ? () => context.pushReplacement('/lessons/${next.lesson.id}')
                          : null,
                    ),
                  );

          if (isLandscape) {
            return Container(
              color: Colors.black,
              alignment: Alignment.center,
              child: videoPlayer,
            );
          }

          return SingleChildScrollView(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                videoPlayer,
                Padding(
                  padding: const EdgeInsets.all(20.0),
                  child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    // Title
                    Text(
                      lesson.title,
                      style: theme.textTheme.headlineSmall?.copyWith(
                        fontWeight: FontWeight.w700,
                        letterSpacing: -0.4,
                      ),
                    ),
                    const SizedBox(height: 16),
                    // Content/Description
                    if (lesson.content != null && lesson.content!.isNotEmpty)
                      Text(
                        lesson.content!,
                        style: theme.textTheme.bodyLarge?.copyWith(height: 1.6),
                      ),
                    const SizedBox(height: 32),
                    AppButton(
                      text: 'Mark as complete',
                      icon: Icons.check_circle_outline,
                      size: ButtonSize.large,
                      isFullWidth: true,
                      isLoading: _isCompleting,
                      onPressed: () =>
                          _markAsComplete(int.parse(lesson.courseId), int.parse(lesson.id)),
                    ),
                    // Up-next card — jump straight to the following lesson.
                    if (next != null) ...[
                      const SizedBox(height: 16),
                      NextLessonCard(
                        lesson: next.lesson,
                        lessonNumber: next.number,
                        onTap: () => context
                            .pushReplacement('/lessons/${next.lesson.id}'),
                      ),
                    ],
                    const SizedBox(height: 32),
                  ],
                ),
              ),
            ],
          ),
        );
        },
        loading: () => const BrandedLoader(),
        error: (error, stack) => ErrorDisplay(
          message: error.toString(),
          onRetry: () => ref.refresh(lessonByIdProvider(widget.lessonId)),
        ),
      ),
    );
  }
}

