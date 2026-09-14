// lib/features/dashboard/presentation/widgets/instructor_dashboard_view.dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:google_fonts/google_fonts.dart';
import '../../../../shared/widgets/common/error_display.dart';
import '../../../../shared/widgets/common/skeleton_loader.dart';
import '../providers/dashboard_provider.dart';
import 'role_dashboard_common.dart';

/// Instructor dashboard fed by GET /api/v1/dashboard/instructor:
/// {stats: {total_courses, total_students, total_earnings, average_rating},
///  courses: [...], recent_activity: [...]}
class InstructorDashboardView extends ConsumerWidget {
  const InstructorDashboardView({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final dashboardAsync = ref.watch(instructorDashboardProvider);

    return Scaffold(
      appBar: AppBar(
        title: Text(
          'Instructor Dashboard',
          style: GoogleFonts.plusJakartaSans(fontWeight: FontWeight.bold),
        ),
        elevation: 0,
        backgroundColor: Colors.transparent,
      ),
      body: RefreshIndicator(
        onRefresh: () => ref.refresh(instructorDashboardProvider.future),
        child: dashboardAsync.when(
          data: (data) {
            final stats = (data['stats'] as Map<String, dynamic>?) ?? {};
            final courses = (data['courses'] as List?) ?? [];
            final activity = (data['recent_activity'] as List?) ?? [];

            return SingleChildScrollView(
              physics: const AlwaysScrollableScrollPhysics(),
              padding:
                  const EdgeInsets.symmetric(horizontal: 16.0, vertical: 12.0),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  RoleDashboardHero(
                    title: 'Instructor Workspace',
                    subtitle: 'Your courses, students and earnings',
                    gradient: const [
                      Color(0xFF7C3AED), // Violet
                      Color(0xFF4F46E5), // Indigo
                      Color(0xFF0EA5E9), // Sky
                    ],
                    stats: [
                      ('Courses', '${stats['total_courses'] ?? 0}'),
                      ('Students', '${stats['total_students'] ?? 0}'),
                      ('Earnings', '${stats['total_earnings'] ?? '₹0'}'),
                      (
                        'Avg Rating',
                        stats['average_rating'] != null
                            ? (stats['average_rating'] as num)
                                .toStringAsFixed(1)
                            : '—'
                      ),
                    ],
                  ),
                  const SizedBox(height: 28),
                  const RoleDashboardSectionTitle('My Courses'),
                  const SizedBox(height: 12),
                  if (courses.isEmpty)
                    Text(
                      'No published courses yet.',
                      style: GoogleFonts.plusJakartaSans(color: Colors.grey),
                    )
                  else
                    for (final course in courses)
                      RoleDashboardListCard(
                        icon: Icons.menu_book_outlined,
                        iconColor: const Color(0xFF7C3AED),
                        title: '${course['title'] ?? 'Untitled course'}',
                        subtitle:
                            '${course['students'] ?? 0} students · rating ${course['rating'] != null ? (course['rating'] as num).toStringAsFixed(1) : '—'}',
                        trailing:
                            '₹${((course['earnings'] as num?) ?? 0).toStringAsFixed(0)}',
                      ),
                  const SizedBox(height: 28),
                  if (activity.isNotEmpty) ...[
                    const RoleDashboardSectionTitle('Recent Enrollments'),
                    const SizedBox(height: 12),
                    for (final item in activity.take(5))
                      RoleDashboardListCard(
                        icon: Icons.person_add_alt_outlined,
                        iconColor: const Color(0xFF0EA5E9),
                        title: '${item['title'] ?? item['action'] ?? ''}',
                        subtitle:
                            '${item['course'] ?? ''}${item['time'] != null ? ' · ${item['time']}' : ''}',
                      ),
                    const SizedBox(height: 24),
                  ],
                ],
              ),
            );
          },
          loading: () => const Padding(
            padding: EdgeInsets.all(16),
            child: SkeletonList(itemCount: 4),
          ),
          error: (err, stack) => ErrorDisplay(
            message: 'Error loading instructor dashboard: $err',
            onRetry: () => ref.refresh(instructorDashboardProvider),
          ),
        ),
      ),
    );
  }
}
