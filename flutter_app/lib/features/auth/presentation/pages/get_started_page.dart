// lib/features/auth/presentation/pages/get_started_page.dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:google_fonts/google_fonts.dart';
import '../../../../config/theme.dart';
import '../../../../config/design_tokens.dart';
import '../providers/onboarding_provider.dart';
import '../widgets/login_hero.dart';

/// Onboarding "Get Started" screen — shown once, on the first launch.
///
/// Step 1 of registration lives here: the user picks how they want to join
/// (Student or Staff). The choice is carried to `/register?role=...`, where the
/// wizard is pre-selected to that role and jumps straight to the details step.
class GetStartedPage extends ConsumerWidget {
  const GetStartedPage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final theme = Theme.of(context);
    final size = MediaQuery.sizeOf(context);

    // Same hero sizing as the Login page.
    final heroHeight = (size.height * 0.38).clamp(280.0, 420.0).toDouble();

    // Mark onboarding done the moment the user acts, so Get Started never
    // appears again on later launches.
    void start(String role) {
      ref.read(onboardingCompletedProvider.notifier).complete();
      context.go('/register?role=$role');
    }

    void signIn() {
      ref.read(onboardingCompletedProvider.notifier).complete();
      context.go('/login');
    }

    return Scaffold(
      backgroundColor: theme.colorScheme.surface,
      body: SingleChildScrollView(
        padding: EdgeInsets.zero,
        child: Column(
          children: [
            // Same hero as the Login page — room background + 3D character + wave.
            LoginHero(height: heroHeight),

            // White role-selection sheet, tucked into the wave exactly like login.
            Container(
              width: double.infinity,
              color: Colors.transparent,
              transform: Matrix4.translationValues(0, -28, 0),
              child: Padding(
                padding: const EdgeInsets.fromLTRB(24, 8, 24, 32),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    // Welcome text — centered above the role cards.
                    Text(
                      'Welcome to Sasha Infinity',
                      textAlign: TextAlign.center,
                      style: GoogleFonts.plusJakartaSans(
                        fontSize: 26,
                        fontWeight: FontWeight.w800,
                        letterSpacing: -0.5,
                      ),
                    ),
                    const SizedBox(height: 8),
                    Text(
                      'Immersive, AI-powered learning. Choose how you\'d like to join.',
                      textAlign: TextAlign.center,
                      style: GoogleFonts.inter(
                        fontSize: 14,
                        height: 1.45,
                        color: theme.colorScheme.onSurface
                            .withValues(alpha: 0.6),
                      ),
                    ),
                    const SizedBox(height: 28),
                    Text(
                      'I want to join as',
                      style: GoogleFonts.plusJakartaSans(
                        fontSize: 20,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      'You can change other details on the next step.',
                      style: theme.textTheme.bodyMedium?.copyWith(
                        color: theme.colorScheme.onSurface
                            .withValues(alpha: 0.6),
                      ),
                    ),
                    const SizedBox(height: 22),
                    _RoleCard(
                      title: 'Student',
                      subtitle:
                          'Learn from expert-led courses, AR labs and more.',
                      icon: Icons.school_rounded,
                      color: AppTheme.primary,
                      onTap: () => start('student'),
                    ),
                    const SizedBox(height: 14),
                    _RoleCard(
                      title: 'Staff',
                      subtitle: 'Teach, mentor and manage courses & learners.',
                      icon: Icons.workspace_premium_rounded,
                      color: const Color(0xFF7C3AED),
                      onTap: () => start('instructor'),
                    ),
                    const SizedBox(height: 24),
                    Center(
                      child: Wrap(
                        crossAxisAlignment: WrapCrossAlignment.center,
                        children: [
                          Text(
                            'Already have an account? ',
                            style: theme.textTheme.bodyMedium?.copyWith(
                              color: theme.colorScheme.onSurface
                                  .withValues(alpha: 0.7),
                            ),
                          ),
                          GestureDetector(
                            onTap: signIn,
                            child: Text(
                              'Sign in',
                              style: GoogleFonts.inter(
                                fontWeight: FontWeight.w700,
                                color: AppTheme.primary,
                              ),
                            ),
                          ),
                        ],
                      ),
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

/// A large, tappable role choice card.
class _RoleCard extends StatelessWidget {
  final String title;
  final String subtitle;
  final IconData icon;
  final Color color;
  final VoidCallback onTap;

  const _RoleCard({
    required this.title,
    required this.subtitle,
    required this.icon,
    required this.color,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;

    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(18),
        child: Container(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: isDark ? AppTheme.surfaceDark : Colors.white,
            borderRadius: BorderRadius.circular(18),
            border: Border.all(
              color: isDark ? const Color(0xFF273449) : const Color(0xFFEEF2F6),
            ),
            boxShadow: isDark ? null : AppShadows.card,
          ),
          child: Row(
            children: [
              Container(
                width: 52,
                height: 52,
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                    colors: [
                      color,
                      Color.alphaBlend(
                          Colors.white.withValues(alpha: 0.28), color),
                    ],
                  ),
                  borderRadius: BorderRadius.circular(15),
                  boxShadow: [
                    BoxShadow(
                      color: color.withValues(alpha: 0.32),
                      blurRadius: 10,
                      offset: const Offset(0, 4),
                    ),
                  ],
                ),
                child: Icon(icon, color: Colors.white, size: 26),
              ),
              const SizedBox(width: 16),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      title,
                      style: GoogleFonts.plusJakartaSans(
                        fontWeight: FontWeight.w700,
                        fontSize: 17,
                      ),
                    ),
                    const SizedBox(height: 3),
                    Text(
                      subtitle,
                      style: theme.textTheme.bodySmall?.copyWith(
                        color: theme.colorScheme.onSurface
                            .withValues(alpha: 0.65),
                        height: 1.35,
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 8),
              Icon(Icons.arrow_forward_rounded, color: color, size: 20),
            ],
          ),
        ),
      ),
    );
  }
}
