// lib/features/admin/presentation/widgets/admin_search_bar.dart
import 'dart:async';
import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

/// A search input with debounced onChange (300ms) to avoid hammering the API
/// on every keystroke.
class AdminSearchBar extends StatefulWidget {
  final ValueChanged<String> onSearch;
  final String hintText;

  const AdminSearchBar({
    super.key,
    required this.onSearch,
    this.hintText = 'Search…',
  });

  @override
  State<AdminSearchBar> createState() => _AdminSearchBarState();
}

class _AdminSearchBarState extends State<AdminSearchBar> {
  final _controller = TextEditingController();
  Timer? _debounce;

  @override
  void dispose() {
    _debounce?.cancel();
    _controller.dispose();
    super.dispose();
  }

  void _onChanged(String value) {
    _debounce?.cancel();
    _debounce = Timer(const Duration(milliseconds: 300), () {
      widget.onSearch(value.trim());
    });
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Container(
      height: 44,
      decoration: BoxDecoration(
        color: theme.colorScheme.surface,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: theme.dividerColor),
      ),
      child: TextField(
        controller: _controller,
        onChanged: _onChanged,
        style: GoogleFonts.inter(fontSize: 14),
        decoration: InputDecoration(
          hintText: widget.hintText,
          hintStyle: GoogleFonts.inter(
            fontSize: 14,
            color: theme.colorScheme.onSurface.withValues(alpha: 0.4),
          ),
          prefixIcon: Icon(
            Icons.search,
            size: 20,
            color: theme.colorScheme.onSurface.withValues(alpha: 0.4),
          ),
          border: InputBorder.none,
          contentPadding:
              const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
          isDense: true,
        ),
      ),
    );
  }
}
