import 'package:flutter/material.dart';

import 'package:sashalms/config/theme.dart';

/// Full-bleed page background: a solid base with a soft warm-orange radial
/// glow anchored to the top-right corner.
///
/// Flutter port of the web hero treatment:
/// ```css
/// background: #ffffff;
/// background-image: radial-gradient(circle at top right,
///     rgba(255,140,60,0.5), transparent 70%);
/// filter: blur(80px);
/// ```
/// The radial gradient is inherently soft, so it reproduces the blurred glow
/// without an expensive full-screen blur filter. Place it behind a transparent
/// Scaffold (set `Scaffold.backgroundColor: Colors.transparent`).
class WarmGlowBackground extends StatelessWidget {
  const WarmGlowBackground({super.key, required this.child});

  final Widget child;

  /// The glow colour — orange-ish #FF8C3C, matching the web source.
  static const Color _glow = Color(0xFFFF8C3C);

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final base = isDark ? AppTheme.backgroundDark : Colors.white;
    // Slightly dialled back on dark so it reads as a glow, not a wash.
    final glow = _glow.withOpacity(isDark ? 0.32 : 0.5);

    return DecoratedBox(
      decoration: BoxDecoration(color: base),
      child: Stack(
        children: [
          Positioned.fill(
            child: DecoratedBox(
              decoration: BoxDecoration(
                gradient: RadialGradient(
                  center: Alignment.topRight,
                  radius: 1.1,
                  colors: [glow, glow.withOpacity(0)],
                  stops: const [0.0, 0.7],
                ),
              ),
            ),
          ),
          child,
        ],
      ),
    );
  }
}
