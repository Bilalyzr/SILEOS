import 'package:flutter/material.dart';

/// Visual intent of a snackbar.
enum AppSnackbarType { success, error, info }

/// Polished, app-wide snackbar: floating, rounded, colored by intent, with a
/// leading icon and a dismiss action. Replaces ad-hoc `ScaffoldMessenger`
/// calls so success/error feedback looks consistent everywhere.
class AppSnackbar {
  static void show(
    BuildContext context,
    String message, {
    AppSnackbarType type = AppSnackbarType.info,
    Duration duration = const Duration(seconds: 3),
  }) {
    final scheme = Theme.of(context).colorScheme;

    late final Color background;
    late final IconData icon;
    switch (type) {
      case AppSnackbarType.success:
        background = const Color(0xFF2E7D32);
        icon = Icons.check_circle_outline;
        break;
      case AppSnackbarType.error:
        background = scheme.error;
        icon = Icons.error_outline;
        break;
      case AppSnackbarType.info:
        background = const Color(0xFF37474F);
        icon = Icons.info_outline;
        break;
    }

    final messenger = ScaffoldMessenger.of(context);
    // Don't stack: a fresh message replaces whatever's showing.
    messenger.clearSnackBars();
    messenger.showSnackBar(
      SnackBar(
        behavior: SnackBarBehavior.floating,
        backgroundColor: background,
        elevation: 6,
        duration: duration,
        margin: const EdgeInsets.all(16),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
        content: Row(
          children: [
            Icon(icon, color: Colors.white, size: 20),
            const SizedBox(width: 12),
            Expanded(
              child: Text(
                message,
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 14,
                  fontWeight: FontWeight.w500,
                ),
              ),
            ),
          ],
        ),
        // No action button — it auto-dismisses after [duration].
      ),
    );
  }

  static void success(BuildContext context, String message) =>
      show(context, message, type: AppSnackbarType.success);

  static void error(BuildContext context, String message) =>
      show(context, message, type: AppSnackbarType.error);

  static void info(BuildContext context, String message) =>
      show(context, message, type: AppSnackbarType.info);
}
