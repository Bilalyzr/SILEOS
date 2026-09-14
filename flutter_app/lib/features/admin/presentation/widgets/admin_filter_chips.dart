// lib/features/admin/presentation/widgets/admin_filter_chips.dart
import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

/// A horizontal row of filter chips. The selected chip uses the primary color.
class AdminFilterChips extends StatelessWidget {
  final List<String> labels;
  final int selectedIndex;
  final ValueChanged<int> onChanged;

  const AdminFilterChips({
    super.key,
    required this.labels,
    required this.selectedIndex,
    required this.onChanged,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return SizedBox(
      height: 40,
      child: ListView.separated(
        scrollDirection: Axis.horizontal,
        itemCount: labels.length,
        separatorBuilder: (_, __) => const SizedBox(width: 8),
        itemBuilder: (context, index) {
          final selected = index == selectedIndex;
          return GestureDetector(
            onTap: () => onChanged(index),
            child: AnimatedContainer(
              duration: const Duration(milliseconds: 200),
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
              decoration: BoxDecoration(
                color: selected
                    ? theme.colorScheme.primary
                    : theme.colorScheme.surface,
                borderRadius: BorderRadius.circular(20),
                border: Border.all(
                  color: selected
                      ? theme.colorScheme.primary
                      : theme.dividerColor,
                ),
              ),
              child: Text(
                labels[index],
                style: GoogleFonts.inter(
                  fontSize: 13,
                  fontWeight: selected ? FontWeight.w600 : FontWeight.w500,
                  color: selected
                      ? Colors.white
                      : theme.colorScheme.onSurface
                          .withValues(alpha: 0.7),
                ),
              ),
            ),
          );
        },
      ),
    );
  }
}
