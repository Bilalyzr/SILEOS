// lib/features/courses/presentation/widgets/next_lesson_card.dart
//
// A compact, tappable card that points the learner at a specific lesson —
// used as the "Continue learning" card on the course detail page and the
// "Up next" card at the end of a lesson.
import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import '../../../../config/theme.dart';
import '../../domain/entities/lesson.dart';

class NextLessonCard extends StatelessWidget {
  const NextLessonCard({
    super.key,
    required this.lesson,
    required this.lessonNumber,
    required this.onTap,
    this.label = 'Up next',
  });

  /// The lesson to open.
  final Lesson lesson;

  /// 1-based position of the lesson within the course (for the subtitle).
  final int lessonNumber;

  /// Small eyebrow label, e.g. "Up next" or "Continue learning".
  final String label;

  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;
    final onSurface = theme.colorScheme.onSurface;

    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(16),
        child: Container(
          padding: const EdgeInsets.all(14),
          decoration: BoxDecoration(
            color: isDark
                ? const Color(0xFF1E293B)
                : AppTheme.primary.withOpacity(0.06),
            borderRadius: BorderRadius.circular(16),
            border: Border.all(color: AppTheme.primary.withOpacity(0.25)),
          ),
          child: Row(
            children: [
              Container(
                width: 46,
                height: 46,
                decoration: BoxDecoration(
                  color: AppTheme.primary,
                  borderRadius: BorderRadius.circular(12),
                ),
                child: const Icon(Icons.play_arrow_rounded,
                    color: Colors.white, size: 26),
              ),
              const SizedBox(width: 14),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      label.toUpperCase(),
                      style: GoogleFonts.inter(
                        fontSize: 11,
                        fontWeight: FontWeight.w700,
                        letterSpacing: 0.6,
                        color: AppTheme.primary,
                      ),
                    ),
                    const SizedBox(height: 3),
                    Text(
                      lesson.title,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: GoogleFonts.plusJakartaSans(
                        fontSize: 15,
                        fontWeight: FontWeight.w700,
                        color: onSurface,
                      ),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      'Lesson $lessonNumber'
                      '${lesson.duration != null ? ' · ${lesson.duration} mins' : ''}',
                      style: GoogleFonts.inter(
                        fontSize: 12,
                        color: onSurface.withOpacity(0.6),
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 8),
              const Icon(Icons.arrow_forward_ios_rounded,
                  size: 15, color: AppTheme.primary),
            ],
          ),
        ),
      ),
    );
  }
}
