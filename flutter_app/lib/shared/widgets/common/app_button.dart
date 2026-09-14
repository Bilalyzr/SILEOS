// lib/shared/widgets/common/app_button.dart
import 'package:flutter/material.dart';
import '../../../config/design_tokens.dart';

enum ButtonSize { small, medium, large }

/// [primary] is the default professional action — a solid orange fill with a
/// restrained lift. [gradient] keeps a subtle orange sweep for the occasional
/// hero CTA; it is no longer the default.
enum ButtonVariant { primary, gradient, secondary, outline, text, danger }

class AppButton extends StatelessWidget {
  final String text;
  final VoidCallback? onPressed;
  final ButtonVariant variant;
  final ButtonSize size;
  final bool isLoading;
  final bool isFullWidth;
  final IconData? icon;
  final Widget? trailing;

  const AppButton({
    super.key,
    required this.text,
    this.onPressed,
    this.variant = ButtonVariant.primary,
    this.size = ButtonSize.medium,
    this.isLoading = false,
    this.isFullWidth = false,
    this.icon,
    this.trailing,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final enabled = onPressed != null && !isLoading;

    final Widget button = variant == ButtonVariant.gradient
        ? _buildGradientButton(context, enabled)
        : _buildStandardButton(context, theme, enabled);

    return SizedBox(
      width: isFullWidth ? double.infinity : null,
      child: button,
    );
  }

  // --- Gradient (hero) button -------------------------------------------------

  Widget _buildGradientButton(BuildContext context, bool enabled) {
    final radius = BorderRadius.circular(AppRadius.md);
    return DecoratedBox(
      decoration: BoxDecoration(
        gradient: enabled
            ? AppGradients.primary
            : LinearGradient(
                colors: [Colors.grey.shade400, Colors.grey.shade500],
              ),
        borderRadius: radius,
        boxShadow: enabled ? AppShadows.primaryGlow : null,
      ),
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: enabled ? onPressed : null,
          borderRadius: radius,
          child: Padding(
            padding: _getPadding(),
            child: _buildChild(context, Colors.white),
          ),
        ),
      ),
    );
  }

  // --- Standard (themed) buttons ---------------------------------------------

  Widget _buildStandardButton(
      BuildContext context, ThemeData theme, bool enabled) {
    final foregroundColor = _getForegroundColor(theme);
    final radius = BorderRadius.circular(AppRadius.md);
    final child = _buildChild(context, foregroundColor);

    if (variant == ButtonVariant.text) {
      return TextButton(
        onPressed: enabled ? onPressed : null,
        style: TextButton.styleFrom(
          foregroundColor: foregroundColor,
          padding: _getPadding(),
        ),
        child: child,
      );
    }

    if (variant == ButtonVariant.outline) {
      return OutlinedButton(
        onPressed: enabled ? onPressed : null,
        style: OutlinedButton.styleFrom(
          foregroundColor: foregroundColor,
          side: BorderSide(color: theme.colorScheme.primary, width: 1.5),
          padding: _getPadding(),
          shape: RoundedRectangleBorder(borderRadius: radius),
        ),
        child: child,
      );
    }

    // The solid primary/secondary/danger fills get a restrained lift; flat
    // (no glow) keeps the professional feel while still reading as a CTA.
    final hasLift = variant == ButtonVariant.primary ||
        variant == ButtonVariant.secondary ||
        variant == ButtonVariant.danger;
    return ElevatedButton(
      onPressed: enabled ? onPressed : null,
      style: ElevatedButton.styleFrom(
        backgroundColor: _getBackgroundColor(theme),
        foregroundColor: foregroundColor,
        padding: _getPadding(),
        shape: RoundedRectangleBorder(borderRadius: radius),
        elevation: hasLift ? 2 : 0,
        shadowColor: _getBackgroundColor(theme).withOpacity(0.28),
      ),
      child: child,
    );
  }

  Widget _buildChild(BuildContext context, Color foregroundColor) {
    final textStyle = _getTextStyle(context).copyWith(color: foregroundColor);
    return Row(
      mainAxisSize: MainAxisSize.min,
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        if (icon != null && !isLoading) ...[
          Icon(icon, size: _getIconSize(), color: foregroundColor),
          const SizedBox(width: 8),
        ],
        if (isLoading)
          SizedBox(
            width: _getIconSize(),
            height: _getIconSize(),
            child: CircularProgressIndicator(
              strokeWidth: 2.5,
              color: foregroundColor,
            ),
          )
        else
          Flexible(
            child: Text(
              text,
              style: textStyle,
              overflow: TextOverflow.ellipsis,
            ),
          ),
        if (trailing != null && !isLoading) ...[
          const SizedBox(width: 8),
          trailing!,
        ],
      ],
    );
  }

  Color _getBackgroundColor(ThemeData theme) {
    switch (variant) {
      case ButtonVariant.gradient:
      case ButtonVariant.primary:
        return theme.colorScheme.primary;
      case ButtonVariant.danger:
        return theme.colorScheme.error;
      case ButtonVariant.secondary:
        return theme.colorScheme.secondary;
      case ButtonVariant.outline:
      case ButtonVariant.text:
        return Colors.transparent;
    }
  }

  Color _getForegroundColor(ThemeData theme) {
    switch (variant) {
      case ButtonVariant.gradient:
      case ButtonVariant.primary:
      case ButtonVariant.danger:
      case ButtonVariant.secondary:
        return Colors.white;
      case ButtonVariant.outline:
      case ButtonVariant.text:
        return theme.colorScheme.primary;
    }
  }

  EdgeInsets _getPadding() {
    switch (size) {
      case ButtonSize.small:
        return const EdgeInsets.symmetric(horizontal: 16, vertical: 10);
      case ButtonSize.medium:
        return const EdgeInsets.symmetric(horizontal: 20, vertical: 14);
      case ButtonSize.large:
        return const EdgeInsets.symmetric(horizontal: 28, vertical: 18);
    }
  }

  TextStyle _getTextStyle(BuildContext context) {
    final theme = Theme.of(context);
    switch (size) {
      case ButtonSize.small:
        return theme.textTheme.bodyMedium!.copyWith(
          fontWeight: FontWeight.w600,
          letterSpacing: 0.1,
        );
      case ButtonSize.medium:
        return theme.textTheme.bodyLarge!.copyWith(
          fontWeight: FontWeight.w600,
          letterSpacing: 0.1,
        );
      case ButtonSize.large:
        return theme.textTheme.titleMedium!.copyWith(
          fontSize: 16.5,
          fontWeight: FontWeight.w600,
          letterSpacing: 0.1,
        );
    }
  }

  double _getIconSize() {
    switch (size) {
      case ButtonSize.small:
        return 16;
      case ButtonSize.medium:
        return 18;
      case ButtonSize.large:
        return 20;
    }
  }
}
