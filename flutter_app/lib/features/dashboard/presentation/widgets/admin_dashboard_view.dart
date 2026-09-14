// lib/features/dashboard/presentation/widgets/admin_dashboard_view.dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:google_fonts/google_fonts.dart';
import '../../../../shared/widgets/common/error_display.dart';
import '../../../../shared/widgets/common/skeleton_loader.dart';
import '../providers/dashboard_provider.dart';
import 'role_dashboard_common.dart';

/// Admin dashboard fed by GET /api/v1/dashboard/admin:
/// {stats: {total_courses, total_students, total_revenue, active_enrollments},
///  recent_courses: [...], recent_enrollments: [...]}
class AdminDashboardView extends ConsumerWidget {
  const AdminDashboardView({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final dashboardAsync = ref.watch(adminDashboardProvider);

    return Scaffold(
      appBar: AppBar(
        title: Text(
          'Admin Dashboard',
          style: GoogleFonts.plusJakartaSans(fontWeight: FontWeight.bold),
        ),
        elevation: 0,
        backgroundColor: Colors.transparent,
      ),
      body: RefreshIndicator(
        onRefresh: () => ref.refresh(adminDashboardProvider.future),
        child: dashboardAsync.when(
          data: (data) {
            final stats = (data['stats'] as Map<String, dynamic>?) ?? {};
            final recentCourses = (data['recent_courses'] as List?) ?? [];
            final recentEnrollments =
                (data['recent_enrollments'] as List?) ?? [];

            return SingleChildScrollView(
              physics: const AlwaysScrollableScrollPhysics(),
              padding:
                  const EdgeInsets.symmetric(horizontal: 16.0, vertical: 12.0),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  RoleDashboardHero(
                    title: 'Admin Workspace',
                    subtitle: 'Platform-wide overview',
                    gradient: const [
                      Color(0xFF0F172A), // Slate
                      Color(0xFF1E40AF), // Blue
                      Color(0xFF0891B2), // Cyan
                    ],
                    stats: [
                      ('Courses', '${stats['total_courses'] ?? 0}'),
                      ('Students', '${stats['total_students'] ?? 0}'),
                      ('Revenue', '${stats['total_revenue'] ?? '₹0'}'),
                      ('Enrollments', '${stats['active_enrollments'] ?? 0}'),
                    ],
                  ),
                  const SizedBox(height: 28),
                  const RoleDashboardSectionTitle('Top Courses'),
                  const SizedBox(height: 12),
                  if (recentCourses.isEmpty)
                    Text(
                      'No courses yet.',
                      style: GoogleFonts.plusJakartaSans(color: Colors.grey),
                    )
                  else
                    for (final course in recentCourses)
                      RoleDashboardListCard(
                        icon: Icons.menu_book_outlined,
                        iconColor: const Color(0xFF1E40AF),
                        title: '${course['title'] ?? 'Untitled course'}',
                        subtitle:
                            '${course['students'] ?? 0} students · rating ${course['rating'] != null ? (course['rating'] as num).toStringAsFixed(1) : '—'}',
                        trailing: '${course['revenue'] ?? ''}',
                      ),
                  const SizedBox(height: 28),
                  if (recentEnrollments.isNotEmpty) ...[
                    const RoleDashboardSectionTitle('Recent Enrollments'),
                    const SizedBox(height: 12),
                    for (final item in recentEnrollments.take(8))
                      RoleDashboardListCard(
                        icon: Icons.person_add_alt_outlined,
                        iconColor: const Color(0xFF0891B2),
                        title: '${item['student'] ?? ''}',
                        subtitle:
                            '${item['course'] ?? ''}${item['date'] != null ? ' · ${item['date']}' : ''}',
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
            message: 'Error loading admin dashboard: $err',
            onRetry: () => ref.refresh(adminDashboardProvider),
          ),
        ),
      ),
    );
  }
}
