// lib/shared/widgets/common/app_card.dart
import 'package:flutter/material.dart';
import '../../../config/design_tokens.dart';
import '../../../config/theme.dart';

/// The standard professional surface — a hairline-bordered card with a
/// whisper-soft shadow (Stripe / Notion feel). Use instead of a raw [Card] or a
/// bare [Container] so radius, border and elevation stay consistent everywhere.
///
/// Defaults: 28px radius, 20px padding, slate hairline border, soft shadow on
/// light backgrounds. Pass [gradient] for accent surfaces, [onTap] to make the
/// whole card tappable, or override [border]/[boxShadow]/[radius] as needed.
class AppCard extends StatelessWidget {
  final Widget child;
  final EdgeInsetsGeometry padding;
  final VoidCallback? onTap;
  final Gradient? gradient;
  final Color? color;
  final List<BoxShadow>? boxShadow;
  final double radius;
  final BoxBorder? border;

  /// When true, no border/shadow is drawn (for nested or already-elevated use).
  final bool flat;

  const AppCard({
    super.key,
    required this.child,
    this.padding = const EdgeInsets.all(AppSpacing.card),
    this.onTap,
    this.gradient,
    this.color,
    this.boxShadow,
    this.radius = AppRadius.card,
    this.border,
    this.flat = false,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;
    final borderRadius = BorderRadius.circular(radius);
    final bg = gradient == null
        ? (color ?? theme.cardTheme.color ?? theme.colorScheme.surface)
        : null;

    // Resolve the resting border/shadow. Accent (gradient) cards skip both.
    final BoxBorder? resolvedBorder = gradient != null || flat
        ? border
        : (border ??
            Border.all(
              color: isDark ? AppTheme.borderDark : AppTheme.borderLight,
              width: 1,
            ));
    final List<BoxShadow>? resolvedShadow = gradient != null || flat
        ? boxShadow
        : (boxShadow ?? (isDark ? null : AppShadows.card));

    return DecoratedBox(
      decoration: BoxDecoration(
        color: bg,
        gradient: gradient,
        borderRadius: borderRadius,
        boxShadow: resolvedShadow,
        border: resolvedBorder,
      ),
      child: Material(
        type: MaterialType.transparency,
        child: InkWell(
          onTap: onTap,
          borderRadius: borderRadius,
          child: Padding(padding: padding, child: child),
        ),
      ),
    );
  }
}
