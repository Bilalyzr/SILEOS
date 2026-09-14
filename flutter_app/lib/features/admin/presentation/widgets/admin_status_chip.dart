// lib/features/admin/presentation/widgets/admin_status_chip.dart
import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

/// A color-coded status chip for admin lists.
class AdminStatusChip extends StatelessWidget {
  final String label;
  final AdminStatus status;

  const AdminStatusChip({super.key, required this.label, required this.status});

  @override
  Widget build(BuildContext context) {
    final color = _color;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(20),
      ),
      child: Text(
        label,
        style: GoogleFonts.inter(
          fontSize: 11,
          fontWeight: FontWeight.w600,
          color: color,
        ),
      ),
    );
  }

  Color get _color => switch (status) {
        AdminStatus.active => const Color(0xFF059669),
        AdminStatus.published => const Color(0xFF059669),
        AdminStatus.completed => const Color(0xFF059669),
        AdminStatus.approved => const Color(0xFF059669),
        AdminStatus.inactive => Colors.grey.shade600,
        AdminStatus.draft => Colors.grey.shade600,
        AdminStatus.pending => const Color(0xFF2563EB),
        AdminStatus.suspended => const Color(0xFFDC2626),
        AdminStatus.failed => const Color(0xFFDC2626),
        AdminStatus.rejected => const Color(0xFFDC2626),
        AdminStatus.private => const Color(0xFF8B5CF6),
        AdminStatus.archived => Colors.grey.shade500,
        AdminStatus.refunded => const Color(0xFFF59E0B),
      };
}

/// Maps admin entity statuses to the chip color scheme.
enum AdminStatus {
  active,
  inactive,
  suspended,
  published,
  draft,
  pending,
  private,
  archived,
  completed,
  failed,
  refunded,
  approved,
  rejected,
}
