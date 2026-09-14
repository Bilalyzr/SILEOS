// lib/features/auth/presentation/pages/splash_page.dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../../config/design_tokens.dart';
import '../../../../config/theme.dart';
import '../../../../core/constants/assets.dart';
import '../../../../core/services/initialization_service.dart';
import '../providers/auth_provider.dart';
import '../providers/onboarding_provider.dart';

class SplashPage extends ConsumerStatefulWidget {
  const SplashPage({super.key});

  @override
  ConsumerState<SplashPage> createState() => _SplashPageState();
}

class _SplashPageState extends ConsumerState<SplashPage> {
  @override
  void initState() {
    super.initState();
    _initializeApp();
  }

  Future<void> _initializeApp() async {
    // 1. Core service initialization (Firebase, Hive, etc.)
    // We do this here rather than in main() so the UI can show the splash
    // screen instantly while heavy tasks run in the background.
    await InitializationService.initialize();

    // 1b. Load the first-launch onboarding flag BEFORE auth resolves, so the
    // redirect can send a brand-new user to Get Started (not straight to Login).
    await ref.read(onboardingCompletedProvider.notifier).load();

    // 2. Resolve auth from the stored token. This flips the auth state out of
    // `initial`, at which point the router's redirect takes over: authenticated
    // users land on `/` (home), everyone else on `/login`.
    await ref.read(authProvider.notifier).checkAuthStatus();

    // Auto-login for development if requested via dart-define.
    const autoLogin = bool.fromEnvironment('AUTO_LOGIN', defaultValue: false);
    if (autoLogin) {
      final isAuth = ref.read(authProvider).maybeWhen(
            authenticated: (_) => true,
            orElse: () => false,
          );
      if (!isAuth) {
        debugPrint('Auto-logging in for development...');
        await ref.read(authProvider.notifier).login(
              email: 'admin@sashainfinity.com',
              password: 'password123',
            );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Scaffold(
      backgroundColor: Colors.white,
      body: Container(
        width: double.infinity,
        // Light, mostly-white canvas with the faintest warm tint at the top —
        // the orange now reads as a whisper of brand, not a flood of colour.
        decoration: const BoxDecoration(gradient: AppGradients.subtle),
        child: SafeArea(
          child: Column(
            children: [
              const Spacer(flex: 3),
              // Soft slate-tinted badge holding the logo — a hairline border and
              // whisper shadow give depth without leaning on colour.
              Container(
                width: 148,
                height: 148,
                padding: const EdgeInsets.all(24),
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(AppRadius.xl),
                  border: Border.all(color: AppNeutrals.slate200),
                  boxShadow: AppShadows.cardRaised,
                ),
                child: Image.asset(Assets.sashaLogo, fit: BoxFit.contain),
              ),
              const SizedBox(height: 28),
              Text(
                'SashaInfinity',
                style: theme.textTheme.headlineMedium?.copyWith(
                  color: AppNeutrals.slate900,
                  fontWeight: FontWeight.w800,
                ),
              ),
              const SizedBox(height: 8),
              Text(
                'Learn boldly. Grow infinitely.',
                style: theme.textTheme.bodyLarge?.copyWith(
                  color: AppNeutrals.slate500,
                ),
              ),
              const Spacer(flex: 4),
              // The single touch of orange — the spinner — so the brand accent
              // lands exactly where the eye is already waiting.
              const SizedBox(
                width: 30,
                height: 30,
                child: CircularProgressIndicator(
                  strokeWidth: 3,
                  valueColor: AlwaysStoppedAnimation<Color>(AppTheme.primary),
                ),
              ),
              const SizedBox(height: 48),
            ],
          ),
        ),
      ),
    );
  }
}
