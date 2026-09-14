import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:cached_network_image/cached_network_image.dart';
import 'package:sashalms/config/app_config.dart';
import 'package:sashalms/config/theme.dart';
import 'package:sashalms/config/design_tokens.dart';
import 'package:sashalms/shared/widgets/common/error_display.dart';
import 'package:sashalms/shared/widgets/common/skeleton_loader.dart';
import '../../domain/entities/dashboard_data.dart';
import '../providers/dashboard_provider.dart';

/// Dedicated "Continue learning" page — the full list of the student's enrolled
/// courses (the dashboard only shows the first few in a carousel).
class ContinueLearningPage extends ConsumerWidget {
  const ContinueLearningPage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;
    final dashAsync = ref.watch(studentDashboardProvider);

    return Scaffold(
      backgroundColor: isDark ? theme.colorScheme.surface : AppNeutrals.slate50,
      appBar: AppBar(
        title: const Text('Continue Learning'),
      ),
      body: dashAsync.when(
        data: (data) {
          final courses = data.enrolledCourses;
          if (courses.isEmpty) {
            return _EmptyState(theme: theme);
          }
          return RefreshIndicator(
            color: AppTheme.primary,
            onRefresh: () => ref.refresh(studentDashboardProvider.future),
            child: ListView.separated(
              physics: const AlwaysScrollableScrollPhysics(),
              padding: const EdgeInsets.fromLTRB(20, 20, 20, 32),
              itemCount: courses.length,
              separatorBuilder: (_, __) => const SizedBox(height: 14),
              itemBuilder: (context, i) => _CourseRow(
                course: courses[i],
                isDark: isDark,
                onResume: () => context.push('/courses/${courses[i].id}'),
              ),
            ),
          );
        },
        loading: () => const Padding(
          padding: EdgeInsets.all(20),
          child: SkeletonList(itemCount: 4),
        ),
        error: (err, stack) => ErrorDisplay(
          message: 'Error loading your courses: $err',
          onRetry: () => ref.refresh(studentDashboardProvider),
        ),
      ),
    );
  }
}

/// One full-width enrolled-course card with thumbnail, progress and a resume CTA.
class _CourseRow extends StatelessWidget {
  final DashboardCourse course;
  final bool isDark;
  final VoidCallback onResume;
  const _CourseRow(
      {required this.course, required this.isDark, required this.onResume});

  String _resolveThumb(String raw) {
    final url = raw.trim();
    if (url.isEmpty || url.startsWith('http')) return url;
    return '${AppConfig.baseUrl}$url';
  }

  ({Color color, IconData icon, String text}) _tag() {
    final t = course.title.toLowerCase();
    if (t.contains('ai') || t.contains('machine')) {
      return (color: const Color(0xFF7C3AED), icon: Icons.psychology_rounded, text: 'AI / ML');
    }
    if (t.contains('cloud') || t.contains('devops')) {
      return (color: const Color(0xFF0D9488), icon: Icons.cloud_queue_rounded, text: 'Cloud');
    }
    return (color: AppTheme.primary, icon: Icons.code_rounded, text: 'Full stack');
  }

  @override
  Widget build(BuildContext context) {
    final muted = isDark ? AppTheme.mutedDark : AppTheme.mutedLight;
    final tag = _tag();
    final pct = (course.progress / 100).clamp(0.0, 1.0);
    final thumb = _resolveThumb(course.thumbnail);
    final lessonsLeft =
        (course.totalLessons - course.completedLessons).clamp(0, course.totalLessons);

    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: onResume,
        borderRadius: BorderRadius.circular(AppRadius.lg),
        child: Container(
          padding: const EdgeInsets.all(14),
          decoration: BoxDecoration(
            color: isDark ? AppTheme.surfaceDark : Colors.white,
            borderRadius: BorderRadius.circular(AppRadius.lg),
            border: Border.all(
                color: isDark ? AppTheme.borderDark : AppTheme.borderLight),
            boxShadow: isDark ? null : AppShadows.soft,
          ),
          child: Column(
            children: [
              Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // Thumbnail (falls back to a tinted tag icon).
                  ClipRRect(
                    borderRadius: BorderRadius.circular(AppRadius.md),
                    child: SizedBox(
                      width: 84,
                      height: 84,
                      child: thumb.isEmpty
                          ? _thumbFallback(tag)
                          : CachedNetworkImage(
                              imageUrl: thumb,
                              fit: BoxFit.cover,
                              placeholder: (_, __) =>
                                  Container(color: tag.color.withValues(alpha: 0.08)),
                              errorWidget: (_, __, ___) => _thumbFallback(tag),
                            ),
                    ),
                  ),
                  const SizedBox(width: 14),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Container(
                          padding: const EdgeInsets.symmetric(
                              horizontal: 8, vertical: 3),
                          decoration: BoxDecoration(
                            color: tag.color.withValues(alpha: 0.12),
                            borderRadius: BorderRadius.circular(999),
                          ),
                          child: Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              Icon(tag.icon, size: 11, color: tag.color),
                              const SizedBox(width: 4),
                              Text(tag.text,
                                  style: GoogleFonts.inter(
                                      fontSize: 10.5,
                                      fontWeight: FontWeight.w600,
                                      color: tag.color)),
                            ],
                          ),
                        ),
                        const SizedBox(height: 7),
                        Text(
                          course.title,
                          maxLines: 2,
                          overflow: TextOverflow.ellipsis,
                          style: GoogleFonts.inter(
                            fontSize: 14.5,
                            fontWeight: FontWeight.w700,
                            height: 1.25,
                            color: isDark ? Colors.white : AppNeutrals.slate900,
                          ),
                        ),
                        const SizedBox(height: 4),
                        Row(
                          children: [
                            Icon(Icons.account_circle_outlined,
                                size: 14, color: muted),
                            const SizedBox(width: 4),
                            Expanded(
                              child: Text(course.instructorName,
                                  maxLines: 1,
                                  overflow: TextOverflow.ellipsis,
                                  style: GoogleFonts.inter(
                                      fontSize: 12, color: muted)),
                            ),
                          ],
                        ),
                      ],
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 12),
              // Progress
              Row(
                children: [
                  Expanded(
                    child: ClipRRect(
                      borderRadius: BorderRadius.circular(999),
                      child: LinearProgressIndicator(
                        value: pct,
                        minHeight: 7,
                        backgroundColor:
                            isDark ? AppNeutrals.slate800 : AppNeutrals.slate100,
                        valueColor: AlwaysStoppedAnimation(tag.color),
                      ),
                    ),
                  ),
                  const SizedBox(width: 10),
                  Text('${(pct * 100).round()}%',
                      style: GoogleFonts.plusJakartaSans(
                          fontSize: 12.5,
                          fontWeight: FontWeight.w700,
                          color: isDark ? Colors.white : AppNeutrals.slate900)),
                ],
              ),
              const SizedBox(height: 12),
              Row(
                children: [
                  Icon(Icons.check_circle_outline_rounded,
                      size: 14, color: muted),
                  const SizedBox(width: 4),
                  Text('${course.completedLessons}/${course.totalLessons} lessons',
                      style: GoogleFonts.inter(fontSize: 11.5, color: muted)),
                  const Spacer(),
                  Text('$lessonsLeft left',
                      style: GoogleFonts.inter(fontSize: 11.5, color: muted)),
                ],
              ),
              const SizedBox(height: 12),
              SizedBox(
                width: double.infinity,
                child: ElevatedButton.icon(
                  onPressed: onResume,
                  icon: const Icon(Icons.play_arrow_rounded, size: 18),
                  label: const Text('Resume lesson'),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: tag.color,
                    foregroundColor: Colors.white,
                    elevation: 0,
                    padding: const EdgeInsets.symmetric(vertical: 12),
                    shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(AppRadius.md)),
                    textStyle: GoogleFonts.inter(
                        fontSize: 13, fontWeight: FontWeight.w700),
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _thumbFallback(({Color color, IconData icon, String text}) tag) =>
      Container(
        color: tag.color.withValues(alpha: 0.12),
        child: Icon(tag.icon, color: tag.color, size: 30),
      );
}

class _EmptyState extends StatelessWidget {
  final ThemeData theme;
  const _EmptyState({required this.theme});

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.auto_stories_outlined,
                size: 56, color: theme.colorScheme.onSurface.withValues(alpha: 0.3)),
            const SizedBox(height: 16),
            Text("You haven't enrolled in any courses yet.",
                textAlign: TextAlign.center,
                style: GoogleFonts.inter(
                    fontSize: 15,
                    color: theme.colorScheme.onSurface.withValues(alpha: 0.6))),
          ],
        ),
      ),
    );
  }
}
