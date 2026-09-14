// lib/features/auth/presentation/widgets/social_login_buttons.dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_svg/flutter_svg.dart';
import '../../../../config/app_config.dart';
import '../providers/auth_provider.dart';

class SocialLoginButtons extends ConsumerWidget {
  const SocialLoginButtons({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final theme = Theme.of(context);
    final isLoading = ref.watch(authProvider).maybeWhen(
          loading: () => true,
          orElse: () => false,
        );

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Row(
          children: [
            const Expanded(child: Divider()),
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 12),
              child: Text(
                'or continue with',
                style: theme.textTheme.bodySmall?.copyWith(
                  color: theme.colorScheme.onSurface.withOpacity(0.5),
                ),
              ),
            ),
            const Expanded(child: Divider()),
          ],
        ),
        const SizedBox(height: 16),
        _GoogleSignInButton(
          isLoading: isLoading,
          onPressed: () => ref.read(authProvider.notifier).loginWithGoogle(),
        ),
        // LinkedIn is feature-flagged off: the backend's OAuth redirect is
        // hardcoded to the web domain, which mobile cannot intercept yet.
        if (AppConfig.enableLinkedInLogin) ...[
          const SizedBox(height: 12),
          OutlinedButton.icon(
            onPressed: isLoading
                ? null
                : () {
                    ScaffoldMessenger.of(context).showSnackBar(
                      const SnackBar(
                        content:
                            Text('LinkedIn sign-in is not available yet.'),
                      ),
                    );
                  },
            icon: const Icon(Icons.business_center_outlined),
            label: const Text('Sign in with LinkedIn'),
            style: OutlinedButton.styleFrom(
              padding: const EdgeInsets.symmetric(vertical: 12),
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(8),
              ),
            ),
          ),
        ],
      ],
    );
  }
}

/// A neat, Google-branded "Continue with Google" button: white surface, subtle
/// border, the official multi-colour G mark, and an inline spinner while the
/// sign-in is in flight (so the user gets immediate feedback on tap).
class _GoogleSignInButton extends StatelessWidget {
  const _GoogleSignInButton({
    required this.isLoading,
    required this.onPressed,
  });

  final bool isLoading;
  final VoidCallback onPressed;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;

    // Google brand guidance: white button in light mode, dark grey (#131314)
    // in dark mode, with a 1px neutral border and Roboto-ish medium label.
    final backgroundColor = isDark ? const Color(0xFF131314) : Colors.white;
    final foregroundColor = isDark ? Colors.white : const Color(0xFF1F1F1F);
    final borderColor =
        isDark ? const Color(0xFF5F6368) : const Color(0xFFDADCE0);

    return SizedBox(
      height: 52,
      child: OutlinedButton(
        onPressed: isLoading ? null : onPressed,
        style: OutlinedButton.styleFrom(
          backgroundColor: backgroundColor,
          foregroundColor: foregroundColor,
          disabledBackgroundColor: backgroundColor,
          side: BorderSide(color: borderColor),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(10),
          ),
        ),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            if (isLoading)
              SizedBox(
                width: 20,
                height: 20,
                child: CircularProgressIndicator(
                  strokeWidth: 2.2,
                  valueColor: AlwaysStoppedAnimation<Color>(
                    foregroundColor.withOpacity(0.7),
                  ),
                ),
              )
            else
              SvgPicture.asset(
                'assets/icons/google_logo.svg',
                width: 20,
                height: 20,
              ),
            const SizedBox(width: 12),
            Text(
              isLoading ? 'Signing in…' : 'Continue with Google',
              style: theme.textTheme.titleSmall?.copyWith(
                color: foregroundColor,
                fontWeight: FontWeight.w600,
                letterSpacing: 0.2,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
