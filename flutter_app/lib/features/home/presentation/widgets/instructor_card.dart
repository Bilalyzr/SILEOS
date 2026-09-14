import 'package:flutter/material.dart';
import 'package:cached_network_image/cached_network_image.dart';
import 'package:sashalms/config/app_config.dart';
import 'package:sashalms/config/design_tokens.dart';
import 'package:sashalms/config/theme.dart';
import 'package:sashalms/features/courses/domain/entities/course.dart';

/// Compact instructor card for the horizontal-scroll "Our Instructors" section
/// on the home page. Shows avatar + name in a bordered surface card.
class InstructorCard extends StatelessWidget {
  final Instructor instructor;
  final VoidCallback? onTap;

  const InstructorCard({super.key, required this.instructor, this.onTap});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;
    final muted = isDark ? AppTheme.mutedDark : AppTheme.mutedLight;

    // Resolve avatar URL — backend may return relative paths
    final avatarUrl = instructor.avatar.startsWith('http')
        ? instructor.avatar
        : '${AppConfig.baseUrl}${instructor.avatar}';

    // Initial for fallback when avatar fails to load
    final initial = instructor.name.isNotEmpty
        ? instructor.name.split(' ').map((w) => w.isNotEmpty ? w[0].toUpperCase() : '').take(2).join()
        : '?';

    return GestureDetector(
      onTap: onTap,
      behavior: HitTestBehavior.opaque,
      child: Container(
        width: 110,
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 16),
        decoration: BoxDecoration(
          color: isDark ? AppTheme.surfaceDark : Colors.white,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(
            color: isDark ? AppTheme.borderDark : AppTheme.borderLight,
          ),
          boxShadow: isDark ? null : AppShadows.soft,
        ),
        child: Column(
          children: [
            CircleAvatar(
              radius: 32,
              backgroundColor: AppTheme.primary.withOpacity(0.08),
              backgroundImage: CachedNetworkImageProvider(avatarUrl),
              onBackgroundImageError: (_, __) {},
              child: Text(
                initial,
                style: TextStyle(
                  fontSize: 14,
                  fontWeight: FontWeight.w700,
                  color: AppTheme.primary,
                  letterSpacing: -0.3,
                ),
              ),
            ),
            const SizedBox(height: 10),
            Text(
              instructor.name,
              style: theme.textTheme.bodySmall?.copyWith(
                fontWeight: FontWeight.w600,
                color: isDark ? AppNeutrals.slate200 : _ink,
                height: 1.2,
              ),
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 2),
            Text(
              'Instructor',
              style: theme.textTheme.labelSmall?.copyWith(color: muted),
            ),
          ],
        ),
      ),
    );
  }
}

const Color _ink = Color(0xFF1E293B);
