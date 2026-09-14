// lib/features/auth/presentation/pages/verify_email_page.dart
import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../../../config/design_tokens.dart';
import '../../../../shared/widgets/common/app_button.dart';
import '../../../../shared/widgets/common/app_input.dart';
import '../../../../shared/widgets/common/app_snackbar.dart';
import '../providers/email_verification_provider.dart';

/// Post-register notice + manual verification screen.
/// Reached via `/verify-email?email=...` after registering, or
/// `/verify-email?token=...` from a link (Phase 3 deep links plug in here).
class VerifyEmailPage extends ConsumerStatefulWidget {
  final String? email;
  final String? token;

  const VerifyEmailPage({super.key, this.email, this.token});

  @override
  ConsumerState<VerifyEmailPage> createState() => _VerifyEmailPageState();
}

class _VerifyEmailPageState extends ConsumerState<VerifyEmailPage> {
  late final TextEditingController _tokenController;
  static const _resendCooldown = Duration(seconds: 30);
  Timer? _cooldownTimer;
  int _cooldownRemaining = 0;

  @override
  void initState() {
    super.initState();
    _tokenController = TextEditingController(text: widget.token ?? '');
    WidgetsBinding.instance.addPostFrameCallback((_) {
      ref.read(emailVerificationProvider.notifier).reset();
      // Arrived with a token (e.g. from a link): verify immediately.
      if ((widget.token ?? '').isNotEmpty) _handleVerify();
    });
  }

  @override
  void dispose() {
    _cooldownTimer?.cancel();
    _tokenController.dispose();
    super.dispose();
  }

  void _startCooldown() {
    setState(() => _cooldownRemaining = _resendCooldown.inSeconds);
    _cooldownTimer?.cancel();
    _cooldownTimer = Timer.periodic(const Duration(seconds: 1), (timer) {
      if (!mounted) {
        timer.cancel();
        return;
      }
      setState(() {
        _cooldownRemaining--;
        if (_cooldownRemaining <= 0) timer.cancel();
      });
    });
  }

  String _extractToken(String input) {
    final trimmed = input.trim();
    final uri = Uri.tryParse(trimmed);
    final fromUrl = uri?.queryParameters['token'];
    if (fromUrl != null && fromUrl.isNotEmpty) return fromUrl;
    return trimmed;
  }

  Future<void> _handleResend() async {
    final email = widget.email;
    if (email == null || email.isEmpty) return;
    final ok =
        await ref.read(emailVerificationProvider.notifier).resend(email);
    if (!mounted) return;
    if (ok) {
      _startCooldown();
      AppSnackbar.success(context,
          'If the account exists and needs verification, a new email has been sent.');
    }
  }

  Future<void> _handleVerify() async {
    final token = _extractToken(_tokenController.text);
    if (token.isEmpty) return;
    final ok = await ref.read(emailVerificationProvider.notifier).verify(token);
    if (ok && mounted) {
      AppSnackbar.success(context, 'Email verified! You can sign in now.');
      context.go('/login');
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final verifyState = ref.watch(emailVerificationProvider);
    final isLoading = verifyState.isLoading;
    final email = widget.email;

    return Scaffold(
      appBar: AppBar(title: const Text('Verify Email')),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: SingleChildScrollView(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Center(
                  child: Container(
                    width: 84,
                    height: 84,
                    decoration: BoxDecoration(
                      gradient: AppGradients.primary,
                      borderRadius: BorderRadius.circular(AppRadius.lg),
                      boxShadow: AppShadows.primaryGlow,
                    ),
                    child: const Icon(
                      Icons.mark_email_unread_rounded,
                      size: 42,
                      color: Colors.white,
                    ),
                  ),
                ),
                const SizedBox(height: 20),
                Text(
                  'Verify your email',
                  style: theme.textTheme.headlineSmall?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: 8),
                Text(
                  email != null && email.isNotEmpty
                      ? 'We sent a verification email to $email. Open the link '
                          'inside it, or paste the link (or token) below.'
                      : 'Paste the verification link (or token) from the email '
                          'we sent you.',
                  style: theme.textTheme.bodyMedium?.copyWith(
                    color: theme.colorScheme.onSurface.withOpacity(0.6),
                  ),
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: 32),
                AppInput(
                  label: 'Verification link or token',
                  hint: 'Paste the link or token from the email',
                  controller: _tokenController,
                  textInputAction: TextInputAction.done,
                  onFieldSubmitted: (_) => _handleVerify(),
                  prefixIcon: const Icon(Icons.vpn_key_outlined),
                ),
                if (verifyState.hasError) ...[
                  const SizedBox(height: 12),
                  Text(
                    verifyState.error.toString(),
                    style: TextStyle(color: theme.colorScheme.error),
                    textAlign: TextAlign.center,
                  ),
                ],
                const SizedBox(height: 24),
                AppButton(
                  text: 'Verify Email',
                  onPressed: _handleVerify,
                  isLoading: isLoading,
                  isFullWidth: true,
                ),
                if (email != null && email.isNotEmpty) ...[
                  const SizedBox(height: 12),
                  AppButton(
                    text: _cooldownRemaining > 0
                        ? 'Resend email (${_cooldownRemaining}s)'
                        : 'Resend verification email',
                    variant: ButtonVariant.outline,
                    onPressed: _cooldownRemaining > 0 ? null : _handleResend,
                    isFullWidth: true,
                  ),
                ],
                const SizedBox(height: 12),
                AppButton(
                  text: 'Back to Sign In',
                  variant: ButtonVariant.text,
                  onPressed: () => context.go('/login'),
                  isFullWidth: true,
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
