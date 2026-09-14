// lib/features/admin/presentation/pages/admin_students_page.dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:google_fonts/google_fonts.dart';
import '../../../../shared/widgets/common/error_display.dart';
import '../../../../shared/widgets/common/skeleton_loader.dart';
import '../../../../features/admin/domain/repositories/admin_repository.dart';
import '../providers/admin_provider.dart';
import '../widgets/admin_search_bar.dart';
import '../widgets/admin_filter_chips.dart';
import '../widgets/admin_user_list_tile.dart';

class AdminStudentsPage extends ConsumerStatefulWidget {
  const AdminStudentsPage({super.key});

  @override
  ConsumerState<AdminStudentsPage> createState() => _AdminStudentsPageState();
}

class _AdminStudentsPageState extends ConsumerState<AdminStudentsPage> {
  int _statusIndex = 0;
  String _search = '';

  static const _statusFilters = ['All', 'Active', 'Inactive', 'Suspended'];
  static const _statusValues = [null, 'active', 'inactive', 'suspended'];

  @override
  Widget build(BuildContext context) {
    final studentsAsync = ref.watch(adminStudentsProvider(
      status: _statusValues[_statusIndex],
      search: _search.isEmpty ? null : _search,
    ));

    return Column(
      children: [
        // Search + filters
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 12, 16, 8),
          child: AdminSearchBar(
            hintText: 'Search students by name or email…',
            onSearch: (value) => setState(() => _search = value),
          ),
        ),
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16),
          child: AdminFilterChips(
            labels: _statusFilters,
            selectedIndex: _statusIndex,
            onChanged: (i) => setState(() => _statusIndex = i),
          ),
        ),
        const SizedBox(height: 8),

        // Student list
        Expanded(
          child: studentsAsync.when(
            data: (result) => _buildList(result),
            loading: () => const Padding(
              padding: EdgeInsets.all(16),
              child: SkeletonList(itemCount: 6),
            ),
            error: (err, _) => ErrorDisplay(
              message: 'Error loading students: $err',
              onRetry: () => ref.invalidate(adminStudentsProvider(
                status: _statusValues[_statusIndex],
                search: _search.isEmpty ? null : _search,
              )),
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildList(AdminUserListResult result) {
    if (result.users.isEmpty) {
      return Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.people_outline,
                size: 48, color: Colors.grey.shade400),
            const SizedBox(height: 12),
            Text(
              'No students found',
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
      onRefresh: () => ref.refresh(adminStudentsProvider(
        status: _statusValues[_statusIndex],
        search: _search.isEmpty ? null : _search,
      ).future),
      child: ListView.builder(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
        itemCount: result.users.length,
        itemBuilder: (context, index) {
          return AdminUserListTile(
            user: result.users[index],
            onTap: () => _showUserDetail(result.users[index]),
          );
        },
      ),
    );
  }

  void _showUserDetail(Map<String, dynamic> user) {
    final status = (user['status'] as String?) ?? 'active';
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      builder: (context) => _UserDetailSheet(user: user, currentStatus: status),
    );
  }
}

class _UserDetailSheet extends ConsumerStatefulWidget {
  final Map<String, dynamic> user;
  final String currentStatus;

  const _UserDetailSheet({
    required this.user,
    required this.currentStatus,
  });

  @override
  ConsumerState<_UserDetailSheet> createState() => _UserDetailSheetState();
}

class _UserDetailSheetState extends ConsumerState<_UserDetailSheet> {
  late String _selectedStatus;
  bool _isUpdating = false;

  @override
  void initState() {
    super.initState();
    _selectedStatus = widget.currentStatus;
  }

  @override
  Widget build(BuildContext context) {
    final user = widget.user;
    final name = (user['display_name'] as String?) ??
        (user['username'] as String?) ??
        'Unknown';
    final email = (user['email'] as String?) ?? '';
    final role = (user['role'] as String?) ?? 'student';
    final joinedDate = user['joined_date'] as String?;
    final lastLogin = user['last_login'] as String?;
    final isVerified = user['is_verified'] as bool?;
    final totalCourses = user['total_courses'] as int?;

    return Container(
      padding: const EdgeInsets.fromLTRB(24, 20, 24, 32),
      decoration: const BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Center(
            child: Container(
              width: 40,
              height: 4,
              decoration: BoxDecoration(
                color: Colors.grey.shade300,
                borderRadius: BorderRadius.circular(2),
              ),
            ),
          ),
          const SizedBox(height: 16),
          Text(
            name,
            style: GoogleFonts.plusJakartaSans(
              fontSize: 20,
              fontWeight: FontWeight.bold,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            email,
            style: GoogleFonts.inter(
              fontSize: 14,
              color: Colors.grey.shade600,
            ),
          ),
          const SizedBox(height: 20),
          _DetailRow(
              icon: Icons.badge_outlined, label: 'Role', value: role),
          _DetailRow(
              icon: Icons.verified_user_outlined,
              label: 'Verified',
              value: isVerified == true ? 'Yes' : 'No'),
          if (joinedDate != null)
            _DetailRow(
                icon: Icons.calendar_today, label: 'Joined', value: joinedDate),
          if (lastLogin != null)
            _DetailRow(
                icon: Icons.access_time, label: 'Last Login', value: lastLogin),
          if (totalCourses != null)
            _DetailRow(
                icon: Icons.menu_book, label: 'Courses', value: '$totalCourses'),
          const Divider(height: 32),
          Text(
            'Change Status',
            style: GoogleFonts.plusJakartaSans(
              fontSize: 14,
              fontWeight: FontWeight.w700,
            ),
          ),
          const SizedBox(height: 12),
          Row(
            children: [
              _StatusButton(
                label: 'Active',
                selected: _selectedStatus == 'active',
                color: const Color(0xFF059669),
                onTap: () => setState(() => _selectedStatus = 'active'),
              ),
              const SizedBox(width: 8),
              _StatusButton(
                label: 'Inactive',
                selected: _selectedStatus == 'inactive',
                color: Colors.grey.shade600,
                onTap: () =>
                    setState(() => _selectedStatus = 'inactive'),
              ),
              const SizedBox(width: 8),
              _StatusButton(
                label: 'Suspended',
                selected: _selectedStatus == 'suspended',
                color: const Color(0xFFDC2626),
                onTap: () =>
                    setState(() => _selectedStatus = 'suspended'),
              ),
            ],
          ),
          const SizedBox(height: 16),
          SizedBox(
            width: double.infinity,
            child: ElevatedButton(
              onPressed: _isUpdating ? null : _updateStatus,
              style: ElevatedButton.styleFrom(
                padding: const EdgeInsets.symmetric(vertical: 14),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(12),
                ),
              ),
              child: _isUpdating
                  ? const SizedBox(
                      height: 20,
                      width: 20,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : Text(
                      'Update Status',
                      style: GoogleFonts.inter(
                        fontWeight: FontWeight.w600,
                        fontSize: 15,
                      ),
                    ),
            ),
          ),
        ],
      ),
    );
  }

  Future<void> _updateStatus() async {
    if (_selectedStatus == widget.currentStatus) {
      Navigator.pop(context);
      return;
    }

    setState(() => _isUpdating = true);
    try {
      final userId = widget.user['id'];
      if (userId == null) return;
      await ref.read(adminRepositoryProvider).updateUserStatus(
            userId as int,
            _selectedStatus,
          );
      if (mounted) {
        Navigator.pop(context);
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Status updated to $_selectedStatus'),
            backgroundColor: const Color(0xFF059669),
          ),
        );
        ref.invalidate(adminStudentsProvider);
      }
    } catch (e) {
      if (mounted) {
        setState(() => _isUpdating = false);
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Failed to update status: $e')),
        );
      }
    }
  }
}

class _DetailRow extends StatelessWidget {
  final IconData icon;
  final String label;
  final String value;

  const _DetailRow(
      {required this.icon, required this.label, required this.value});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Row(
        children: [
          Icon(icon, size: 18, color: theme.colorScheme.primary),
          const SizedBox(width: 10),
          Text(
            label,
            style: GoogleFonts.inter(
              fontSize: 13,
              color: theme.colorScheme.onSurface.withValues(alpha: 0.6),
            ),
          ),
          const Spacer(),
          Flexible(
            child: Text(
              value,
              textAlign: TextAlign.right,
              style: GoogleFonts.inter(
                fontSize: 13,
                fontWeight: FontWeight.w600,
              ),
              overflow: TextOverflow.ellipsis,
            ),
          ),
        ],
      ),
    );
  }
}

class _StatusButton extends StatelessWidget {
  final String label;
  final bool selected;
  final Color color;
  final VoidCallback onTap;

  const _StatusButton({
    required this.label,
    required this.selected,
    required this.color,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return Expanded(
      child: GestureDetector(
        onTap: onTap,
        child: Container(
          padding: const EdgeInsets.symmetric(vertical: 10),
          decoration: BoxDecoration(
            color: selected ? color : color.withValues(alpha: 0.08),
            borderRadius: BorderRadius.circular(10),
            border: Border.all(
              color: selected ? color : color.withValues(alpha: 0.3),
            ),
          ),
          child: Text(
            label,
            textAlign: TextAlign.center,
            style: GoogleFonts.inter(
              fontSize: 12,
              fontWeight: FontWeight.w600,
              color: selected ? Colors.white : color,
            ),
          ),
        ),
      ),
    );
  }
}
