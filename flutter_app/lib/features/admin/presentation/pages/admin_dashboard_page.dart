// lib/features/admin/presentation/pages/admin_dashboard_page.dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:google_fonts/google_fonts.dart';
import '../../../../shared/widgets/common/error_display.dart';
import '../../../../shared/widgets/common/skeleton_loader.dart';
import '../providers/admin_provider.dart';
import '../widgets/admin_stat_card.dart';
import '../widgets/admin_filter_chips.dart';

class AdminDashboardPage extends ConsumerStatefulWidget {
  const AdminDashboardPage({super.key});

  @override
  ConsumerState<AdminDashboardPage> createState() => _AdminDashboardPageState();
}

class _AdminDashboardPageState extends ConsumerState<AdminDashboardPage> {
  int _periodIndex = 1; // 30d default
  static const _periods = ['7d', '30d', '90d', '1y'];

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final statsAsync =
        ref.watch(adminStatsProvider(period: _periods[_periodIndex]));

    return RefreshIndicator(
      onRefresh: () => ref.refresh(
          adminStatsProvider(period: _periods[_periodIndex]).future),
      child: statsAsync.when(
        data: (data) => _buildContent(context, theme, data),
        loading: () => const Padding(
          padding: EdgeInsets.all(16),
          child: SkeletonList(itemCount: 6),
        ),
        error: (err, _) => ErrorDisplay(
          message: 'Error loading admin stats: $err',
          onRetry: () => ref.invalidate(
              adminStatsProvider(period: _periods[_periodIndex])),
        ),
      ),
    );
  }

  Widget _buildContent(
      BuildContext context, ThemeData theme, Map<String, dynamic> data) {
    final userStats = (data['user_stats'] as Map<String, dynamic>?) ?? {};
    final courseStats = (data['course_stats'] as Map<String, dynamic>?) ?? {};
    final enrollmentStats =
        (data['enrollment_stats'] as Map<String, dynamic>?) ?? {};
    final revenueStats =
        (data['revenue_stats'] as Map<String, dynamic>?) ?? {};

    final recentCourses =
        (courseStats['recent_courses'] as List?)?.cast<Map>() ?? [];
    final recentEnrollments =
        (enrollmentStats['recent_enrollments'] as List?)?.cast<Map>() ?? [];

    return SingleChildScrollView(
      physics: const AlwaysScrollableScrollPhysics(),
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Period selector
          AdminFilterChips(
            labels: const ['7 Days', '30 Days', '90 Days', '1 Year'],
            selectedIndex: _periodIndex,
            onChanged: (i) => setState(() => _periodIndex = i),
          ),
          const SizedBox(height: 20),

          // Primary stat cards
          GridView.count(
            crossAxisCount: 2,
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            mainAxisSpacing: 12,
            crossAxisSpacing: 12,
            childAspectRatio: 1.1,
            children: [
              AdminStatCard(
                icon: Icons.people,
                value: '${userStats['total_users'] ?? 0}',
                label: 'Total Users',
                iconColor: const Color(0xFF2563EB),
              ),
              AdminStatCard(
                icon: Icons.school,
                value: '${userStats['students'] ?? 0}',
                label: 'Students',
                iconColor: const Color(0xFF059669),
              ),
              AdminStatCard(
                icon: Icons.currency_rupee,
                value: '₹${_formatNumber(revenueStats['total_revenue'])}',
                label: 'Total Revenue',
                iconColor: const Color(0xFFD97706),
              ),
              AdminStatCard(
                icon: Icons.menu_book,
                value: '${courseStats['total_courses'] ?? 0}',
                label: 'Courses',
                iconColor: const Color(0xFF7C3AED),
              ),
            ],
          ),
          const SizedBox(height: 24),

          // Secondary stats row
          _SectionTitle(title: 'At a Glance'),
          const SizedBox(height: 12),
          Row(
            children: [
              _MiniStat(
                label: 'Active',
                value: '${userStats['active_users'] ?? 0}',
                color: const Color(0xFF059669),
              ),
              const SizedBox(width: 12),
              _MiniStat(
                label: 'New',
                value: '${userStats['new_users_count'] ?? 0}',
                color: const Color(0xFF2563EB),
              ),
              const SizedBox(width: 12),
              _MiniStat(
                label: 'Enrolled',
                value: '${enrollmentStats['total_enrollments'] ?? 0}',
                color: const Color(0xFF7C3AED),
              ),
              const SizedBox(width: 12),
              _MiniStat(
                label: 'Completed',
                value:
                    '${enrollmentStats['completed_enrollments'] ?? 0}',
                color: const Color(0xFFD97706),
              ),
            ],
          ),
          const SizedBox(height: 28),

          // Top Courses
          _SectionTitle(title: 'Top Courses'),
          const SizedBox(height: 12),
          if (recentCourses.isEmpty)
            Text(
              'No courses yet.',
              style: GoogleFonts.plusJakartaSans(color: Colors.grey),
            )
          else
            for (final course in recentCourses)
              _ListCard(
                icon: Icons.menu_book_outlined,
                iconColor: const Color(0xFF7C3AED),
                title: '${course['title'] ?? 'Untitled'}',
                subtitle:
                    '${course['students'] ?? 0} students · ${(course['rating'] as num?)?.toStringAsFixed(1) ?? '—'}',
              ),
          const SizedBox(height: 28),

          // Recent Enrollments
          if (recentEnrollments.isNotEmpty) ...[
            _SectionTitle(title: 'Recent Enrollments'),
            const SizedBox(height: 12),
            for (final item in recentEnrollments.take(8))
              _ListCard(
                icon: Icons.person_add_alt_outlined,
                iconColor: const Color(0xFF2563EB),
                title: '${item['student'] ?? ''}',
                subtitle:
                    '${item['course'] ?? ''}${item['date'] != null ? ' · ${item['date']}' : ''}',
              ),
            const SizedBox(height: 24),
          ],
        ],
      ),
    );
  }

  String _formatNumber(dynamic value) {
    if (value == null) return '0';
    if (value is num) {
      if (value >= 10000000) return '${(value / 10000000).toStringAsFixed(1)}Cr';
      if (value >= 100000) return '${(value / 100000).toStringAsFixed(1)}L';
      if (value >= 1000) return '${(value / 1000).toStringAsFixed(0)}K';
      return value.toInt().toString();
    }
    return '$value';
  }
}

class _SectionTitle extends StatelessWidget {
  final String title;
  const _SectionTitle({required this.title});

  @override
  Widget build(BuildContext context) {
    return Text(
      title,
      style: GoogleFonts.plusJakartaSans(
        fontSize: 16,
        fontWeight: FontWeight.w700,
      ),
    );
  }
}

class _MiniStat extends StatelessWidget {
  final String label;
  final String value;
  final Color color;

  const _MiniStat({
    required this.label,
    required this.value,
    required this.color,
  });

  @override
  Widget build(BuildContext context) {
    return Expanded(
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 12, horizontal: 8),
        decoration: BoxDecoration(
          color: color.withValues(alpha: 0.08),
          borderRadius: BorderRadius.circular(12),
        ),
        child: Column(
          children: [
            Text(
              value,
              style: GoogleFonts.plusJakartaSans(
                fontSize: 16,
                fontWeight: FontWeight.bold,
                color: color,
              ),
            ),
            const SizedBox(height: 2),
            Text(
              label,
              style: GoogleFonts.inter(
                fontSize: 11,
                color: Colors.grey.shade600,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _ListCard extends StatelessWidget {
  final IconData icon;
  final Color iconColor;
  final String title;
  final String subtitle;

  const _ListCard({
    required this.icon,
    required this.iconColor,
    required this.title,
    required this.subtitle,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: theme.dividerColor),
        ),
        child: Row(
          children: [
            Icon(icon, size: 20, color: iconColor),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    title,
                    style: GoogleFonts.plusJakartaSans(
                      fontSize: 13,
                      fontWeight: FontWeight.w600,
                    ),
                    overflow: TextOverflow.ellipsis,
                  ),
                  const SizedBox(height: 2),
                  Text(
                    subtitle,
                    style: GoogleFonts.inter(
                      fontSize: 12,
                      color: theme.colorScheme.onSurface
                          .withValues(alpha: 0.5),
                    ),
                    overflow: TextOverflow.ellipsis,
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
