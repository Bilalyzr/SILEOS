// lib/features/admin/presentation/pages/admin_staff_page.dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:google_fonts/google_fonts.dart';
import '../../../../shared/widgets/common/error_display.dart';
import '../../../../shared/widgets/common/skeleton_loader.dart';
import '../providers/admin_provider.dart';
import '../widgets/admin_filter_chips.dart';
import '../widgets/admin_user_list_tile.dart';

class AdminStaffPage extends ConsumerStatefulWidget {
  const AdminStaffPage({super.key});

  @override
  ConsumerState<AdminStaffPage> createState() => _AdminStaffPageState();
}

class _AdminStaffPageState extends ConsumerState<AdminStaffPage>
    with SingleTickerProviderStateMixin {
  late final TabController _tabController;
  int _appStatusIndex = 0;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 2, vsync: this);
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        TabBar(
          controller: _tabController,
          labelStyle: GoogleFonts.plusJakartaSans(
            fontWeight: FontWeight.w700,
            fontSize: 14,
          ),
          unselectedLabelStyle: GoogleFonts.plusJakartaSans(
            fontWeight: FontWeight.w500,
            fontSize: 14,
          ),
          indicatorSize: TabBarIndicatorSize.label,
          dividerColor: Colors.transparent,
          tabs: const [
            Tab(text: 'Instructors'),
            Tab(text: 'Applications'),
          ],
        ),
        Expanded(
          child: TabBarView(
            controller: _tabController,
            children: [
              _InstructorsList(),
              _ApplicationsList(
                statusIndex: _appStatusIndex,
                onStatusChanged: (i) => setState(() => _appStatusIndex = i),
              ),
            ],
          ),
        ),
      ],
    );
  }
}

class _InstructorsList extends ConsumerWidget {
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final instructorsAsync = ref.watch(adminInstructorsProvider());

    return instructorsAsync.when(
      data: (result) {
        if (result.users.isEmpty) {
          return Center(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(Icons.school_outlined, size: 48, color: Colors.grey.shade400),
                const SizedBox(height: 12),
                Text(
                  'No instructors yet',
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
          onRefresh: () => ref.refresh(adminInstructorsProvider().future),
          child: ListView.builder(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
            itemCount: result.users.length,
            itemBuilder: (context, index) {
              return AdminUserListTile(
                user: result.users[index],
                onTap: () => _showInstructorDetail(context, result.users[index]),
              );
            },
          ),
        );
      },
      loading: () => const Padding(
        padding: EdgeInsets.all(16),
        child: SkeletonList(itemCount: 6),
      ),
      error: (err, _) => ErrorDisplay(
        message: 'Error loading instructors: $err',
        onRetry: () => ref.invalidate(adminInstructorsProvider()),
      ),
    );
  }

  void _showInstructorDetail(BuildContext context, Map<String, dynamic> user) {
    final name = (user['display_name'] as String?) ??
        (user['username'] as String?) ?? 'Unknown';
    final email = (user['email'] as String?) ?? '';
    showModalBottomSheet(
      context: context,
      builder: (context) => Container(
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
            Text(name,
                style: GoogleFonts.plusJakartaSans(
                    fontSize: 20, fontWeight: FontWeight.bold)),
            const SizedBox(height: 4),
            Text(email,
                style:
                    GoogleFonts.inter(fontSize: 14, color: Colors.grey.shade600)),
            const SizedBox(height: 8),
          ],
        ),
      ),
    );
  }
}

class _ApplicationsList extends ConsumerWidget {
  final int statusIndex;
  final ValueChanged<int> onStatusChanged;

  const _ApplicationsList({
    required this.statusIndex,
    required this.onStatusChanged,
  });

  static const _labels = ['Pending', 'Approved', 'Rejected'];
  static const _values = ['pending', 'approved', 'rejected'];

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final appsAsync = ref.watch(adminApplicationsProvider(status: _values[statusIndex]));

    return Column(
      children: [
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
          child: AdminFilterChips(
            labels: _labels,
            selectedIndex: statusIndex,
            onChanged: onStatusChanged,
          ),
        ),
        const SizedBox(height: 8),
        Expanded(
          child: appsAsync.when(
            data: (apps) {
              if (apps.isEmpty) {
                return Center(
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(Icons.pending_actions, size: 48, color: Colors.grey.shade400),
                      const SizedBox(height: 12),
                      Text(
                        'No applications',
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
                onRefresh: () => ref.refresh(adminApplicationsProvider(status: _values[statusIndex]).future),
                child: ListView.builder(
                  padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
                  itemCount: apps.length,
                  itemBuilder: (context, index) =>
                      _ApplicationCard(app: apps[index]),
                ),
              );
            },
            loading: () => const Padding(
              padding: EdgeInsets.all(16),
              child: SkeletonList(itemCount: 4),
            ),
            error: (err, _) => ErrorDisplay(
              message: 'Error loading applications: $err',
              onRetry: () => ref.invalidate(adminApplicationsProvider(status: _values[statusIndex])),
            ),
          ),
        ),
      ],
    );
  }
}

class _ApplicationCard extends ConsumerStatefulWidget {
  final Map<String, dynamic> app;

  const _ApplicationCard({required this.app});

  @override
  ConsumerState<_ApplicationCard> createState() => _ApplicationCardState();
}

class _ApplicationCardState extends ConsumerState<_ApplicationCard> {
  bool _isProcessing = false;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final app = widget.app;
    final name = (app['display_name'] as String?) ??
        (app['username'] as String?) ?? 'Unknown';
    final email = (app['email'] as String?) ?? '';
    final bio = (app['bio'] as String?) ?? '';
    final designation = (app['designation'] as String?) ?? '';

    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: theme.dividerColor),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        name,
                        style: GoogleFonts.plusJakartaSans(
                          fontSize: 14,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                      const SizedBox(height: 2),
                      Text(
                        email,
                        style: GoogleFonts.inter(
                          fontSize: 12,
                          color: theme.colorScheme.onSurface
                              .withValues(alpha: 0.5),
                        ),
                      ),
                    ],
                  ),
                ),
                if (!_isProcessing) ...[
                  _ActionChip(
                    label: 'Approve',
                    color: const Color(0xFF059669),
                    onTap: () => _process('approve'),
                  ),
                  const SizedBox(width: 8),
                  _ActionChip(
                    label: 'Reject',
                    color: const Color(0xFFDC2626),
                    onTap: () => _process('reject'),
                  ),
                ] else
                  const SizedBox(
                    width: 24,
                    height: 24,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  ),
              ],
            ),
            if (designation.isNotEmpty) ...[
              const SizedBox(height: 6),
              Text(
                designation,
                style: GoogleFonts.inter(
                  fontSize: 12,
                  color: const Color(0xFF7C3AED),
                  fontWeight: FontWeight.w500,
                ),
              ),
            ],
            if (bio.isNotEmpty) ...[
              const SizedBox(height: 6),
              Text(
                bio,
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
                style: GoogleFonts.inter(
                  fontSize: 12,
                  color: theme.colorScheme.onSurface.withValues(alpha: 0.6),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Future<void> _process(String action) async {
    setState(() => _isProcessing = true);
    try {
      final id = widget.app['id'];
      if (id == null) return;
      await ref.read(adminRepositoryProvider).processInstructorApplication(
            id as int,
            action,
          );
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Application ${action}d'),
            backgroundColor: action == 'approve'
                ? const Color(0xFF059669)
                : const Color(0xFFDC2626),
          ),
        );
        ref.invalidate(adminApplicationsProvider);
      }
    } catch (e) {
      if (mounted) {
        setState(() => _isProcessing = false);
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Failed: $e')),
        );
      }
    }
  }
}

class _ActionChip extends StatelessWidget {
  final String label;
  final Color color;
  final VoidCallback onTap;

  const _ActionChip({
    required this.label,
    required this.color,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
        decoration: BoxDecoration(
          color: color,
          borderRadius: BorderRadius.circular(8),
        ),
        child: Text(
          label,
          style: GoogleFonts.inter(
            fontSize: 12,
            fontWeight: FontWeight.w600,
            color: Colors.white,
          ),
        ),
      ),
    );
  }
}
