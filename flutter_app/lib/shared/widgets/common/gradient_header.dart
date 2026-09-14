// lib/shared/widgets/common/gradient_header.dart
import 'package:flutter/material.dart';
import '../../../config/design_tokens.dart';

/// A bold gradient header used at the top of pages (auth, profile, detail
/// screens). Renders a brand-orange sweep with an optional title/subtitle and
/// arbitrary [child] content. The body below it typically overlaps with a
/// rounded top using [overlap].
class GradientHeader extends StatelessWidget {
  final String? title;
  final String? subtitle;
  final Widget? leading;
  final Widget? trailing;
  final Widget? child;
  final Gradient gradient;
  final EdgeInsets padding;
  final bool safeTop;

  const GradientHeader({
    super.key,
    this.title,
    this.subtitle,
    this.leading,
    this.trailing,
    this.child,
    this.gradient = AppGradients.primary,
    this.padding = const EdgeInsets.fromLTRB(20, 16, 20, 32),
    this.safeTop = true,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final content = Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        if (leading != null || trailing != null)
          Row(
            children: [
              if (leading != null) leading!,
              const Spacer(),
              if (trailing != null) trailing!,
            ],
          ),
        if (title != null) ...[
          if (leading != null || trailing != null)
            const SizedBox(height: 16),
          Text(
            title!,
            style: theme.textTheme.headlineMedium?.copyWith(
              color: Colors.white,
              fontWeight: FontWeight.w700,
            ),
          ),
        ],
        if (subtitle != null) ...[
          const SizedBox(height: 6),
          Text(
            subtitle!,
            style: theme.textTheme.bodyMedium?.copyWith(
              color: Colors.white.withOpacity(0.9),
            ),
          ),
        ],
        if (child != null) child!,
      ],
    );

    return Container(
      width: double.infinity,
      decoration: BoxDecoration(gradient: gradient),
      child: SafeArea(
        bottom: false,
        top: safeTop,
        child: Padding(padding: padding, child: content),
      ),
    );
  }
}
