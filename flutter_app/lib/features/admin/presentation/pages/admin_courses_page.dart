// lib/features/admin/presentation/pages/admin_courses_page.dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:cached_network_image/cached_network_image.dart';
import '../../../../shared/widgets/common/error_display.dart';
import '../../../../shared/widgets/common/skeleton_loader.dart';
import '../providers/admin_provider.dart';
import '../widgets/admin_filter_chips.dart';
import '../widgets/admin_status_chip.dart';

class AdminCoursesPage extends ConsumerStatefulWidget {
  const AdminCoursesPage({super.key});

  @override
  ConsumerState<AdminCoursesPage> createState() => _AdminCoursesPageState();
}

class _AdminCoursesPageState extends ConsumerState<AdminCoursesPage> {
  int _statusIndex = 0;

  static const _statusFilters = ['All', 'Published', 'Draft', 'Pending', 'Private'];
  static const _statusValues = [null, 'publish', 'draft', 'pending', 'private'];

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final coursesAsync = ref.watch(adminCoursesProvider(
      status: _statusValues[_statusIndex],
    ));

    return Column(
      children: [
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
          child: AdminFilterChips(
            labels: _statusFilters,
            selectedIndex: _statusIndex,
            onChanged: (i) => setState(() => _statusIndex = i),
          ),
        ),
        const SizedBox(height: 8),
        Expanded(
          child: coursesAsync.when(
            data: (courses) => _buildList(courses, theme),
            loading: () => const Padding(
              padding: EdgeInsets.all(16),
              child: SkeletonList(itemCount: 6),
            ),
            error: (err, _) => ErrorDisplay(
              message: 'Error loading courses: $err',
              onRetry: () => ref.invalidate(adminCoursesProvider(
                status: _statusValues[_statusIndex],
              )),
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildList(List<Map<String, dynamic>> courses, ThemeData theme) {
    if (courses.isEmpty) {
      return Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.menu_book_outlined, size: 48, color: Colors.grey.shade400),
            const SizedBox(height: 12),
            Text(
              'No courses found',
              style: GoogleFonts.plusJakartaSans(
                color: Colors.grey.shade600,
                fontWeight: FontWeight.w600,
              ),
            ),
          ],
        ),
      );
    }

    return RefreshIndicator(
      onRefresh: () => ref.refresh(adminCoursesProvider(
        status: _statusValues[_statusIndex],
      ).future),
      child: ListView.builder(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
        itemCount: courses.length,
        itemBuilder: (context, index) =>
            _CourseCard(course: courses[index]),
      ),
    );
  }
}

class _CourseCard extends ConsumerStatefulWidget {
  final Map<String, dynamic> course;

  const _CourseCard({required this.course});

  @override
  ConsumerState<_CourseCard> createState() => _CourseCardState();
}

class _CourseCardState extends ConsumerState<_CourseCard> {
  bool _isUpdating = false;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;
    final course = widget.course;
    final title = (course['title'] as String?) ?? 'Untitled';
    final instructor = (course['instructor_name'] as String?) ?? 'Unknown';
    final price = course['price'];
    final enrolled = (course['enrolled_students'] as int?) ?? 0;
    final rating = (course['rating'] as num?);
    final status = (course['status'] as String?) ?? 'draft';
    final bannerUrl = (course['banner_url'] as String?) ??
        (course['thumbnail_url'] as String?);

    final statusEnum = switch (status) {
      'publish' || 'published' => AdminStatus.published,
      'draft' => AdminStatus.draft,
      'pending' => AdminStatus.pending,
      'private' => AdminStatus.private,
      'archived' => AdminStatus.archived,
      _ => AdminStatus.draft,
    };

    final displayStatus = status == 'published' ? 'published' : status;

    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Container(
        decoration: BoxDecoration(
          color: isDark ? const Color(0xFF1E293B) : Colors.white,
          borderRadius: BorderRadius.circular(14),
          border: Border.all(
            color: isDark ? const Color(0xFF334155) : const Color(0xFFEEF2F6),
          ),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Banner thumbnail
            if (bannerUrl != null && bannerUrl.isNotEmpty)
              ClipRRect(
                borderRadius: const BorderRadius.vertical(
                    top: Radius.circular(14)),
                child: CachedNetworkImage(
                  imageUrl: bannerUrl,
                  height: 120,
                  width: double.infinity,
                  fit: BoxFit.cover,
                  placeholder: (_, __) => Container(
                    height: 120,
                    color: isDark
                        ? const Color(0xFF334155)
                        : const Color(0xFFF1F5F9),
                    child: const Center(
                      child: Icon(Icons.menu_book,
                          size: 32, color: Colors.grey),
                    ),
                  ),
                  errorWidget: (_, __, ___) => Container(
                    height: 120,
                    color: isDark
                        ? const Color(0xFF334155)
                        : const Color(0xFFF1F5F9),
                    child: const Center(
                      child: Icon(Icons.broken_image,
                          size: 32, color: Colors.grey),
                    ),
                  ),
                ),
              ),
            Padding(
              padding: const EdgeInsets.all(14),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // Status + title row
                  Row(
                    children: [
                      AdminStatusChip(
                          label: displayStatus, status: statusEnum),
                      const Spacer(),
                      if (!_isUpdating)
                        PopupMenuButton<String>(
                          onSelected: _changeStatus,
                          child: Container(
                            padding: const EdgeInsets.symmetric(
                                horizontal: 10, vertical: 4),
                            decoration: BoxDecoration(
                              borderRadius: BorderRadius.circular(8),
                              border: Border.all(color: theme.dividerColor),
                            ),
                            child: Row(
                              mainAxisSize: MainAxisSize.min,
                              children: [
                                Text(
                                  'Status',
                                  style: GoogleFonts.inter(
                                    fontSize: 12,
                                    fontWeight: FontWeight.w500,
                                  ),
                                ),
                                const SizedBox(width: 4),
                                Icon(Icons.arrow_drop_down, size: 18),
                              ],
                            ),
                          ),
                          itemBuilder: (context) => [
                            const PopupMenuItem(
                                value: 'publish', child: Text('Publish')),
                            const PopupMenuItem(
                                value: 'draft', child: Text('Draft')),
                            const PopupMenuItem(
                                value: 'pending', child: Text('Pending')),
                            const PopupMenuItem(
                                value: 'private', child: Text('Private')),
                            const PopupMenuItem(
                                value: 'archive', child: Text('Archive')),
                          ],
                        )
                      else
                        const SizedBox(
                          width: 20,
                          height: 20,
                          child:
                              CircularProgressIndicator(strokeWidth: 2),
                        ),
                    ],
                  ),
                  const SizedBox(height: 8),
                  Text(
                    title,
                    style: GoogleFonts.plusJakartaSans(
                      fontSize: 15,
                      fontWeight: FontWeight.w600,
                    ),
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                  ),
                  const SizedBox(height: 6),
                  Text(
                    instructor,
                    style: GoogleFonts.inter(
                      fontSize: 12,
                      color: theme.colorScheme.onSurface
                          .withValues(alpha: 0.6),
                    ),
                  ),
                  const SizedBox(height: 10),
                  Row(
                    children: [
                      Text(
                        price != null ? '₹${price}' : 'Free',
                        style: GoogleFonts.plusJakartaSans(
                          fontSize: 16,
                          fontWeight: FontWeight.bold,
                          color: const Color(0xFF059669),
                        ),
                      ),
                      const SizedBox(width: 16),
                      if (rating != null)
                        Row(
                          children: [
                            const Icon(Icons.star, size: 14, color: Color(0xFFF59E0B)),
                            const SizedBox(width: 2),
                            Text(
                              rating.toStringAsFixed(1),
                              style: GoogleFonts.inter(
                                fontSize: 13,
                                fontWeight: FontWeight.w600,
                              ),
                            ),
                          ],
                        ),
                      const Spacer(),
                      Text(
                        '$enrolled enrolled',
                        style: GoogleFonts.inter(
                          fontSize: 12,
                          color: theme.colorScheme.onSurface
                              .withValues(alpha: 0.5),
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _changeStatus(String newStatus) async {
    setState(() => _isUpdating = true);
    try {
      final courseId = widget.course['id'];
      if (courseId == null) return;
      await ref
          .read(adminRepositoryProvider)
          .updateCourseStatus(courseId as int, newStatus);
      if (mounted) {
        setState(() => _isUpdating = false);
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Course status changed to $newStatus'),
            backgroundColor: const Color(0xFF059669),
          ),
        );
        ref.invalidate(adminCoursesProvider);
      }
    } catch (e) {
      if (mounted) {
        setState(() => _isUpdating = false);
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Failed to update: $e')),
        );
      }
    }
  }
}
