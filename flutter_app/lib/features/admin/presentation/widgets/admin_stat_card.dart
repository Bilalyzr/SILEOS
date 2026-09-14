// lib/features/admin/presentation/widgets/admin_stat_card.dart
import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

/// A compact stat card for the admin dashboard: icon, value, label.
class AdminStatCard extends StatelessWidget {
  final IconData icon;
  final String value;
  final String label;
  final Color iconColor;
  final Color? backgroundColor;

  const AdminStatCard({
    super.key,
    required this.icon,
    required this.value,
    required this.label,
    required this.iconColor,
    this.backgroundColor,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: isDark
            ? const Color(0xFF1E293B)
            : (backgroundColor ?? Colors.white),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
          color: isDark
              ? const Color(0xFF334155)
              : const Color(0xFFEEF2F6),
        ),
        boxShadow: isDark
            ? null
            : [
                BoxShadow(
                  color: Colors.black.withValues(alpha: 0.04),
                  blurRadius: 8,
                  offset: const Offset(0, 2),
                ),
              ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: 40,
            height: 40,
            decoration: BoxDecoration(
              color: iconColor.withValues(alpha: 0.1),
              borderRadius: BorderRadius.circular(12),
            ),
            child: Icon(icon, color: iconColor, size: 20),
          ),
          const SizedBox(height: 12),
          Text(
            value,
            style: GoogleFonts.plusJakartaSans(
              fontSize: 22,
              fontWeight: FontWeight.bold,
              letterSpacing: -0.5,
            ),
          ),
          const SizedBox(height: 2),
          Text(
            label,
            style: GoogleFonts.inter(
              fontSize: 12,
              color: isDark
                  ? Colors.white.withValues(alpha: 0.6)
                  : Colors.grey.shade600,
            ),
          ),
        ],
      ),
    );
  }
}
