// lib/features/admin/presentation/pages/admin_orders_page.dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:google_fonts/google_fonts.dart';
import '../../../../shared/widgets/common/error_display.dart';
import '../../../../shared/widgets/common/skeleton_loader.dart';
import '../providers/admin_provider.dart';
import '../widgets/admin_filter_chips.dart';
import '../widgets/admin_status_chip.dart';

class AdminOrdersPage extends ConsumerStatefulWidget {
  const AdminOrdersPage({super.key});

  @override
  ConsumerState<AdminOrdersPage> createState() => _AdminOrdersPageState();
}

class _AdminOrdersPageState extends ConsumerState<AdminOrdersPage> {
  int _statusIndex = 0;

  static const _statusFilters = ['All', 'Pending', 'Completed', 'Failed', 'Refunded'];
  static const _statusValues = [null, 'pending', 'completed', 'failed', 'refunded'];

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final ordersAsync = ref.watch(adminOrdersProvider(
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
          child: ordersAsync.when(
            data: (orders) => _buildList(orders, theme),
            loading: () => const Padding(
              padding: EdgeInsets.all(16),
              child: SkeletonList(itemCount: 6),
            ),
            error: (err, _) => ErrorDisplay(
              message: 'Error loading orders: $err',
              onRetry: () => ref.invalidate(adminOrdersProvider(
                status: _statusValues[_statusIndex],
              )),
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildList(List<Map<String, dynamic>> orders, ThemeData theme) {
    if (orders.isEmpty) {
      return Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.receipt_long_outlined, size: 48, color: Colors.grey.shade400),
            const SizedBox(height: 12),
            Text(
              'No orders found',
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
      onRefresh: () => ref.refresh(adminOrdersProvider(
        status: _statusValues[_statusIndex],
      ).future),
      child: ListView.builder(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
        itemCount: orders.length,
        itemBuilder: (context, index) => _OrderCard(order: orders[index]),
      ),
    );
  }
}

class _OrderCard extends StatelessWidget {
  final Map<String, dynamic> order;

  const _OrderCard({required this.order});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;

    final orderKey = (order['order_key'] as String?) ?? (order['id']?.toString() ?? '');
    final userName = (order['user_name'] as String?) ?? (order['user_email'] as String?) ?? 'Unknown';
    final courseTitle = (order['course_title'] as String?) ?? 'N/A';
    final amount = order['total'] ?? order['amount'] ?? 0;
    final status = (order['status'] as String?) ?? 'pending';
    final createdAt = order['created_at'] as String?;

    final statusEnum = switch (status) {
      'completed' => AdminStatus.completed,
      'failed' => AdminStatus.failed,
      'refunded' => AdminStatus.refunded,
      'pending' => AdminStatus.pending,
      _ => AdminStatus.pending,
    };

    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: isDark ? const Color(0xFF1E293B) : Colors.white,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(
            color: isDark ? const Color(0xFF334155) : const Color(0xFFEEF2F6),
          ),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: Text(
                    '#$orderKey',
                    style: GoogleFonts.inter(
                      fontSize: 12,
                      color: theme.colorScheme.onSurface.withValues(alpha: 0.5),
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                ),
                AdminStatusChip(label: status, status: statusEnum),
              ],
            ),
            const SizedBox(height: 8),
            Text(
              courseTitle,
              style: GoogleFonts.plusJakartaSans(
                fontSize: 14,
                fontWeight: FontWeight.w600,
              ),
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
            ),
            const SizedBox(height: 4),
            Text(
              userName,
              style: GoogleFonts.inter(
                fontSize: 12,
                color: theme.colorScheme.onSurface.withValues(alpha: 0.6),
              ),
            ),
            const SizedBox(height: 8),
            Row(
              children: [
                Text(
                  '₹${amount}',
                  style: GoogleFonts.plusJakartaSans(
                    fontSize: 16,
                    fontWeight: FontWeight.bold,
                    color: const Color(0xFF059669),
                  ),
                ),
                if (createdAt != null) ...[
                  const Spacer(),
                  Text(
                    _formatDate(createdAt),
                    style: GoogleFonts.inter(
                      fontSize: 11,
                      color: theme.colorScheme.onSurface.withValues(alpha: 0.45),
                    ),
                  ),
                ],
              ],
            ),
          ],
        ),
      ),
    );
  }

  String _formatDate(String iso) {
    try {
      final dt = DateTime.parse(iso);
      return '${dt.day}/${dt.month}/${dt.year}';
    } catch (_) {
      return iso;
    }
  }
}
