// lib/shared/widgets/common/app_loader.dart
import 'package:flutter/material.dart';
import '../../../core/constants/assets.dart';

enum LoaderSize { small, medium, large }

/// Centered, branded loading state for full pages / sections: a gently pulsing
/// SashaInfinity logo above a spinner, the app name and a short message. Use
/// this for any page-level `loading:` state so the indicator sits in the middle
/// with context, instead of a bare spinner stuck in a corner.
class BrandedLoader extends StatelessWidget {
  final String? message;
  const BrandedLoader({super.key, this.message});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const _PulsingLogo(),
            const SizedBox(height: 24),
            SizedBox(
              width: 26,
              height: 26,
              child: CircularProgressIndicator(
                strokeWidth: 2.6,
                valueColor: AlwaysStoppedAnimation(theme.colorScheme.primary),
              ),
            ),
            const SizedBox(height: 18),
            Text(
              'SashaInfinity',
              style: theme.textTheme.titleLarge?.copyWith(fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 4),
            Text(
              message ?? 'Loading your learning experience…',
              textAlign: TextAlign.center,
              style: theme.textTheme.bodySmall?.copyWith(
                color: theme.colorScheme.onSurface.withOpacity(0.6),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// The logo, breathing in and out, to make the wait feel alive.
class _PulsingLogo extends StatefulWidget {
  const _PulsingLogo();

  @override
  State<_PulsingLogo> createState() => _PulsingLogoState();
}

class _PulsingLogoState extends State<_PulsingLogo> with SingleTickerProviderStateMixin {
  late final AnimationController _controller =
      AnimationController(vsync: this, duration: const Duration(milliseconds: 1100))..repeat(reverse: true);
  late final Animation<double> _scale =
      Tween<double>(begin: 0.9, end: 1.0).animate(CurvedAnimation(parent: _controller, curve: Curves.easeInOut));

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return ScaleTransition(
      scale: _scale,
      child: Image.asset(Assets.sashaLogo, width: 84, height: 84, fit: BoxFit.contain),
    );
  }
}

class AppLoader extends StatelessWidget {
  final LoaderSize size;
  final Color? color;

  const AppLoader({
    super.key,
    this.size = LoaderSize.medium,
    this.color,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final effectiveColor = color ?? theme.colorScheme.primary;

    return SizedBox(
      width: _getDimension(),
      height: _getDimension(),
      child: CircularProgressIndicator(
        strokeWidth: _getStrokeWidth(),
        valueColor: AlwaysStoppedAnimation(effectiveColor),
      ),
    );
  }

  double _getDimension() {
    switch (size) {
      case LoaderSize.small:
        return 20;
      case LoaderSize.medium:
        return 32;
      case LoaderSize.large:
        return 48;
    }
  }

  double _getStrokeWidth() {
    switch (size) {
      case LoaderSize.small:
        return 2;
      case LoaderSize.medium:
        return 3;
      case LoaderSize.large:
        return 4;
    }
  }
}

class FullScreenLoader extends StatelessWidget {
  final String? message;

  const FullScreenLoader({
    super.key,
    this.message,
  });

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.black.withOpacity(0.5),
      body: Center(
        child: Card(
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                const AppLoader(size: LoaderSize.large),
                if (message != null) ...[
                  const SizedBox(height: 16),
                  Text(message!),
                ],
              ],
            ),
          ),
        ),
      ),
    );
  }
}
