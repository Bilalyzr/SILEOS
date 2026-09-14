import 'dart:ui' show ImageFilter;
import 'package:flutter/material.dart';
import 'package:cached_network_image/cached_network_image.dart';
import 'package:go_router/go_router.dart';
import 'package:sashalms/config/app_config.dart';
import 'package:sashalms/config/design_tokens.dart';
import 'package:sashalms/config/theme.dart';
import '../../domain/entities/course.dart';

/// Professional course card — hairline-bordered surface, soft shadow, a clean
/// thumbnail carrying the category + price, slate-toned metadata and a single
/// clear CTA. Follows the Stripe/Notion design DNA (see design_tokens.dart).
class CourseCard extends StatelessWidget {
  final Course course;

  const CourseCard({super.key, required this.course});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;
    final muted = isDark ? AppTheme.mutedDark : AppTheme.mutedLight;
    final radius = BorderRadius.circular(12.0);

    return DecoratedBox(
      decoration: BoxDecoration(
        color: theme.cardTheme.color,
        borderRadius: radius,
        border: Border.all(
          color: isDark ? AppTheme.borderDark : AppTheme.borderLight,
        ),
        boxShadow: isDark ? null : AppShadows.card,
      ),
      child: Material(
        type: MaterialType.transparency,
        child: InkWell(
          onTap: () => context.push('/courses/${course.id}'),
          borderRadius: radius,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              _thumbnail(context, theme, muted),
              Padding(
                padding: const EdgeInsets.all(AppSpacing.card),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    _ratingRow(theme, muted),
                    const SizedBox(height: 10),
                    Text(
                      course.title,
                      style: theme.textTheme.titleMedium?.copyWith(
                        fontWeight: FontWeight.w700,
                        letterSpacing: -0.2,
                        height: 1.25,
                      ),
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                    ),
                    const SizedBox(height: 6),
                    Row(
                      children: [
                        CircleAvatar(
                          radius: 10,
                          backgroundColor: AppNeutrals.slate100,
                          backgroundImage: course.instructor.avatar.startsWith('http')
                              ? CachedNetworkImageProvider(course.instructor.avatar)
                              : CachedNetworkImageProvider(
                                  '${AppConfig.baseUrl}${course.instructor.avatar}'),
                          onBackgroundImageError: (_, __) {},
                          child: Text(
                            course.instructor.name.isNotEmpty
                                ? course.instructor.name[0].toUpperCase()
                                : '?',
                            style: TextStyle(
                              fontSize: 11,
                              fontWeight: FontWeight.w700,
                              color: AppTheme.primary,
                            ),
                          ),
                        ),
                        const SizedBox(width: 6),
                        Expanded(
                          child: Text(
                            'By ${course.instructor.name}',
                            style: theme.textTheme.bodySmall?.copyWith(color: muted),
                            overflow: TextOverflow.ellipsis,
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 14),
                    if (course.isEnrolled) ...[
                      _progress(theme),
                      const SizedBox(height: 14),
                    ],
                    _metaRow(theme, muted),
                    const SizedBox(height: 16),
                    _ctaRow(context, theme),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  // --- Thumbnail with category pill + price tag ------------------------------
  Widget _thumbnail(BuildContext context, ThemeData theme, Color muted) {
    final imageUrl = course.featuredImage.startsWith('http')
        ? course.featuredImage
        : '${AppConfig.baseUrl}${course.featuredImage}';
    return ClipRRect(
      borderRadius: const BorderRadius.vertical(
        top: Radius.circular(12.0),
      ),
      child: AspectRatio(
        aspectRatio: 16 / 9,
        child: Stack(
          fit: StackFit.expand,
          children: [
            // Blurred, zoomed copy fills the 16:9 frame so the full (uncropped)
            // thumbnail below never sits on empty letterbox bars.
            ImageFiltered(
              imageFilter: ImageFilter.blur(sigmaX: 22, sigmaY: 22),
              child: CachedNetworkImage(
                imageUrl: imageUrl,
                fit: BoxFit.cover,
                placeholder: (context, url) =>
                    Container(color: AppNeutrals.slate100),
                errorWidget: (context, url, error) =>
                    Container(color: AppNeutrals.slate100),
              ),
            ),
            // Soft darken so the white category pill + price tag stay legible.
            Container(color: Colors.black.withOpacity(0.06)),
            // The full thumbnail, shown complete — no cropping.
            CachedNetworkImage(
              imageUrl: imageUrl,
              fit: BoxFit.contain,
              placeholder: (context, url) => const SizedBox.shrink(),
              errorWidget: (context, url, error) => Container(
                color: AppNeutrals.slate100,
                child: Icon(Icons.image_outlined, size: 40, color: muted),
              ),
            ),
            // Category pill (bottom-left over the image)
            Positioned(
              left: 12,
              bottom: 12,
              child: _pill(
                course.category.toUpperCase(),
                bg: Colors.white.withOpacity(0.92),
                fg: AppTheme.primaryDark,
              ),
            ),
            // Price tag (bottom-right)
            Positioned(
              right: 12,
              bottom: 12,
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                decoration: BoxDecoration(
                  color: course.price == 0
                      ? AppTheme.success
                      : AppNeutrals.slate900.withOpacity(0.88),
                  borderRadius: BorderRadius.circular(AppRadius.pill),
                  boxShadow: [
                    BoxShadow(
                      color: Colors.black.withOpacity(0.12),
                      blurRadius: 4,
                      offset: const Offset(0, 2),
                    ),
                  ],
                ),
                child: Text(
                  course.price == 0
                      ? 'FREE'
                      : '₹${course.price.toStringAsFixed(0)}',
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 13,
                    fontWeight: FontWeight.w800,
                    letterSpacing: 0.2,
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _pill(String text, {required Color bg, required Color fg}) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
      decoration: BoxDecoration(
        color: bg,
        borderRadius: BorderRadius.circular(AppRadius.pill),
      ),
      child: Text(
        text,
        style: TextStyle(
          color: fg,
          fontSize: 11,
          fontWeight: FontWeight.w700,
          letterSpacing: 0.3,
        ),
      ),
    );
  }

  Widget _ratingRow(ThemeData theme, Color muted) {
    return Row(
      children: [
        Icon(Icons.star_rounded, size: 18, color: AppTheme.warning),
        const SizedBox(width: 4),
        Text(
          course.rating.toStringAsFixed(1),
          style: theme.textTheme.labelLarge?.copyWith(
            fontWeight: FontWeight.w700,
          ),
        ),
        const SizedBox(width: 4),
        Text(
          '(${course.stats.students})',
          style: theme.textTheme.bodySmall?.copyWith(color: muted),
        ),
        const Spacer(),
        Text(
          course.level,
          style: theme.textTheme.labelMedium?.copyWith(
            color: muted,
            fontWeight: FontWeight.w600,
          ),
        ),
      ],
    );
  }

  Widget _progress(ThemeData theme) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        ClipRRect(
          borderRadius: BorderRadius.circular(AppRadius.pill),
          child: LinearProgressIndicator(
            value: course.progress / 100,
            minHeight: 7,
            backgroundColor: AppNeutrals.slate100,
            valueColor: AlwaysStoppedAnimation(theme.colorScheme.primary),
          ),
        ),
        const SizedBox(height: 6),
        Text(
          '${course.progress.toInt()}% complete',
          style: theme.textTheme.labelSmall?.copyWith(
            color: theme.colorScheme.primary,
            fontWeight: FontWeight.w600,
          ),
        ),
      ],
    );
  }

  Widget _metaRow(ThemeData theme, Color muted) {
    Widget item(IconData icon, String label) => Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, size: 15, color: muted),
            const SizedBox(width: 5),
            Text(label, style: theme.textTheme.bodySmall?.copyWith(color: muted)),
          ],
        );
    return Row(
      children: [
        item(Icons.play_circle_outline, '${course.stats.lessons} lessons'),
        const SizedBox(width: 16),
        item(Icons.schedule, '${course.stats.duration}h'),
      ],
    );
  }

  Widget _ctaRow(BuildContext context, ThemeData theme) {
    final enrolled = course.isEnrolled;
    return SizedBox(
      width: double.infinity,
      child: ElevatedButton(
        onPressed: () {
          if (enrolled) {
            if (course.lessons.isNotEmpty) {
              context.push('/lessons/${course.lessons.first.id}');
            } else {
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(content: Text('No lessons available yet.')),
              );
            }
          } else {
            context.push('/courses/${course.id}');
          }
        },
        style: ElevatedButton.styleFrom(
          padding: const EdgeInsets.symmetric(vertical: 13),
          elevation: 0,
          backgroundColor:
              enrolled ? theme.colorScheme.primary : AppNeutrals.slate900,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(AppRadius.md),
          ),
        ),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Text(enrolled ? 'Continue learning' : 'View course'),
            const SizedBox(width: 6),
            Icon(enrolled ? Icons.play_arrow_rounded : Icons.arrow_forward,
                size: 18),
          ],
        ),
      ),
    );
  }
}
