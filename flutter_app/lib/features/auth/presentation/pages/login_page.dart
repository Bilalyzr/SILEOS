// lib/features/auth/presentation/pages/login_page.dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../../../shared/widgets/common/app_snackbar.dart';
import '../providers/auth_provider.dart';
import '../providers/auth_state.dart';
import '../widgets/login_form.dart';
import '../widgets/login_hero.dart';
import '../widgets/role_selection_sheet.dart';
import '../widgets/social_login_buttons.dart';

class LoginPage extends ConsumerStatefulWidget {
  const LoginPage({super.key});

  @override
  ConsumerState<LoginPage> createState() => _LoginPageState();
}

class _LoginPageState extends ConsumerState<LoginPage> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      ref.read(authProvider.notifier).clearError();
      // A notice set before this page mounted (e.g. "Registration successful"
      // from the register flow) won't trigger ref.listen, so surface it here.
      final pending = ref.read(authProvider).maybeWhen(
            unauthenticated: (m) => m,
            orElse: () => null,
          );
      if (pending != null && pending.isNotEmpty) {
        _showAuthNotice(pending);
        ref.read(authProvider.notifier).consumeMessage();
      }
    });
  }

  /// Shows a one-time auth notice: green for success messages, slate otherwise.
  void _showAuthNotice(String message) {
    if (!mounted || message.isEmpty) return;
    if (message.toLowerCase().contains('success')) {
      AppSnackbar.success(context, message);
    } else {
      AppSnackbar.info(context, message);
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    ref.listen<AuthState>(authProvider, (previous, next) {
      next.maybeWhen(
        // First-time Google user: backend wants a role before creating the
        // account.
        googleRoleSelection: (email, name, picture, firebaseToken) {
          RoleSelectionSheet.show(
            context,
            email: email,
            name: name,
            picture: picture,
            firebaseToken: firebaseToken,
          );
        },
        // One-time notice (e.g. "session expired") set by the network layer.
        unauthenticated: (message) {
          if (message != null && message.isNotEmpty) {
            _showAuthNotice(message);
            ref.read(authProvider.notifier).consumeMessage();
          }
        },
        orElse: () {},
      );
    });

    final size = MediaQuery.sizeOf(context);
    // Shrink the hero when the keyboard is open so the form has room; otherwise
    // size it to ~38% of the screen. The whole page scrolls as one unit (the
    // hero scrolls away with the content) so nothing gets squeezed.
    final keyboardOpen = MediaQuery.viewInsetsOf(context).bottom > 0;
    final heroHeight = keyboardOpen
        ? 0.0
        : (size.height * 0.38).clamp(280.0, 420.0).toDouble();

    return Scaffold(
      backgroundColor: theme.colorScheme.surface,
      body: SingleChildScrollView(
        padding: EdgeInsets.zero,
        child: Column(
          children: [
            // Movable 3D character on the scene background, with a wave-shaped
            // bottom edge flowing into the white login sheet. Hidden while the
            // keyboard is open to give the form full height.
            if (heroHeight > 0) LoginHero(height: heroHeight),
            Container(
              width: double.infinity,
              color: Colors.transparent,
              // Tuck the sheet up into the wave so the white reads as continuous.
              transform: Matrix4.translationValues(0, heroHeight > 0 ? -28 : 0, 0),
              child: Padding(
                padding: EdgeInsets.fromLTRB(24, keyboardOpen ? 32 : 8, 24, 32),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    _FadeSlideIn(
                      child: Column(
                        children: [
                          Text(
                            'Welcome Back',
                            style: theme.textTheme.headlineMedium?.copyWith(
                              fontWeight: FontWeight.bold,
                            ),
                            textAlign: TextAlign.center,
                          ),
                          const SizedBox(height: 6),
                          Text(
                            'Sign in to continue learning',
                            style: theme.textTheme.bodyMedium?.copyWith(
                              color:
                                  theme.colorScheme.onSurface.withOpacity(0.6),
                            ),
                            textAlign: TextAlign.center,
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(height: 28),
                    const LoginForm(),
                    const SizedBox(height: 24),
                    const SocialLoginButtons(),
                    const SizedBox(height: 24),
                    Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Text(
                          "Don't have an account? ",
                          style: theme.textTheme.bodyMedium?.copyWith(
                            color:
                                theme.colorScheme.onSurface.withOpacity(0.7),
                          ),
                        ),
                        TextButton(
                          onPressed: () => context.go('/get-started'),
                          style: TextButton.styleFrom(
                            padding: const EdgeInsets.symmetric(horizontal: 4),
                            minimumSize: const Size(0, 0),
                            tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                          ),
                          child: const Text(
                            'Register',
                            style: TextStyle(fontWeight: FontWeight.bold),
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// Fade + upward-slide entrance for the welcome text, per design.md
/// ("smooth entrance animations for text and CTA buttons").
class _FadeSlideIn extends StatefulWidget {
  const _FadeSlideIn({required this.child});

  final Widget child;

  @override
  State<_FadeSlideIn> createState() => _FadeSlideInState();
}

class _FadeSlideInState extends State<_FadeSlideIn>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller = AnimationController(
    vsync: this,
    duration: const Duration(milliseconds: 600),
  )..forward();

  late final Animation<double> _fade =
      CurvedAnimation(parent: _controller, curve: Curves.easeOut);

  late final Animation<Offset> _slide = Tween<Offset>(
    begin: const Offset(0, 0.18),
    end: Offset.zero,
  ).animate(CurvedAnimation(parent: _controller, curve: Curves.easeOutCubic));

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return FadeTransition(
      opacity: _fade,
      child: SlideTransition(position: _slide, child: widget.child),
    );
  }
}
