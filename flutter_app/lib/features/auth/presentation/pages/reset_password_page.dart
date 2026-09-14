// lib/features/auth/presentation/pages/reset_password_page.dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../../../config/design_tokens.dart';
import '../../../../shared/widgets/common/app_button.dart';
import '../../../../shared/widgets/common/app_input.dart';
import '../../../../shared/widgets/common/app_snackbar.dart';
import '../providers/password_reset_provider.dart';

/// Backend password rules: 8+ chars, 1 uppercase, 1 lowercase, 1 digit.
final _passwordRule = RegExp(r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).{8,}$');

class ResetPasswordPage extends ConsumerStatefulWidget {
  /// Token from a deep link / route query param (`/reset-password?token=...`).
  final String? token;

  const ResetPasswordPage({super.key, this.token});

  @override
  ConsumerState<ResetPasswordPage> createState() => _ResetPasswordPageState();
}

class _ResetPasswordPageState extends ConsumerState<ResetPasswordPage> {
  final _formKey = GlobalKey<FormState>();
  late final TextEditingController _tokenController;
  final _passwordController = TextEditingController();
  final _confirmPasswordController = TextEditingController();
  bool _obscurePassword = true;
  bool _obscureConfirmPassword = true;

  @override
  void initState() {
    super.initState();
    _tokenController = TextEditingController(text: widget.token ?? '');
    WidgetsBinding.instance.addPostFrameCallback((_) {
      ref.read(passwordResetProvider.notifier).reset();
    });
  }

  @override
  void dispose() {
    _tokenController.dispose();
    _passwordController.dispose();
    _confirmPasswordController.dispose();
    super.dispose();
  }

  /// Accepts either a raw token or a full pasted reset URL
  /// (https://.../reset-password?token=...).
  String _extractToken(String input) {
    final trimmed = input.trim();
    final uri = Uri.tryParse(trimmed);
    final fromUrl = uri?.queryParameters['token'];
    if (fromUrl != null && fromUrl.isNotEmpty) return fromUrl;
    return trimmed;
  }

  Future<void> _handleSubmit() async {
    if (!_formKey.currentState!.validate()) return;
    final ok = await ref.read(passwordResetProvider.notifier).submitReset(
          token: _extractToken(_tokenController.text),
          newPassword: _passwordController.text,
        );
    if (ok && mounted) {
      AppSnackbar.success(context, 'Password reset successfully. Please sign in.');
      context.go('/login');
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final resetState = ref.watch(passwordResetProvider);
    final isLoading = resetState.isLoading;

    return Scaffold(
      appBar: AppBar(title: const Text('Set New Password')),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: SingleChildScrollView(
            child: Form(
              key: _formKey,
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
                        Icons.password_rounded,
                        size: 42,
                        color: Colors.white,
                      ),
                    ),
                  ),
                  const SizedBox(height: 20),
                  Text(
                    'Choose a new password',
                    style: theme.textTheme.headlineSmall?.copyWith(
                      fontWeight: FontWeight.bold,
                    ),
                    textAlign: TextAlign.center,
                  ),
                  const SizedBox(height: 8),
                  Text(
                    'Paste the reset link (or token) from the email we sent, '
                    'then choose your new password.',
                    style: theme.textTheme.bodyMedium?.copyWith(
                      color: theme.colorScheme.onSurface.withOpacity(0.6),
                    ),
                    textAlign: TextAlign.center,
                  ),
                  const SizedBox(height: 32),
                  AppInput(
                    label: 'Reset link or token',
                    hint: 'Paste the link or token from the email',
                    controller: _tokenController,
                    textInputAction: TextInputAction.next,
                    validator: (value) {
                      if (value == null || value.trim().isEmpty) {
                        return 'The reset link or token is required';
                      }
                      return null;
                    },
                    prefixIcon: const Icon(Icons.vpn_key_outlined),
                  ),
                  const SizedBox(height: 16),
                  AppInput(
                    label: 'New Password',
                    hint: '8+ chars with upper, lower and a digit',
                    controller: _passwordController,
                    obscureText: _obscurePassword,
                    textInputAction: TextInputAction.next,
                    validator: (value) {
                      if (value == null || value.isEmpty) {
                        return 'Password is required';
                      }
                      if (!_passwordRule.hasMatch(value)) {
                        return 'Use 8+ characters with an uppercase letter, a lowercase letter and a digit';
                      }
                      return null;
                    },
                    prefixIcon: const Icon(Icons.lock_outlined),
                    suffixIcon: IconButton(
                      icon: Icon(_obscurePassword
                          ? Icons.visibility_outlined
                          : Icons.visibility),
                      onPressed: () {
                        setState(() => _obscurePassword = !_obscurePassword);
                      },
                    ),
                  ),
                  const SizedBox(height: 16),
                  AppInput(
                    label: 'Confirm New Password',
                    hint: 'Re-enter your new password',
                    controller: _confirmPasswordController,
                    obscureText: _obscureConfirmPassword,
                    textInputAction: TextInputAction.done,
                    onFieldSubmitted: (_) => _handleSubmit(),
                    validator: (value) {
                      if (value == null || value.isEmpty) {
                        return 'Please confirm your password';
                      }
                      if (value != _passwordController.text) {
                        return 'Passwords do not match';
                      }
                      return null;
                    },
                    prefixIcon: const Icon(Icons.lock_outlined),
                    suffixIcon: IconButton(
                      icon: Icon(_obscureConfirmPassword
                          ? Icons.visibility_outlined
                          : Icons.visibility),
                      onPressed: () {
                        setState(() =>
                            _obscureConfirmPassword = !_obscureConfirmPassword);
                      },
                    ),
                  ),
                  if (resetState.hasError) ...[
                    const SizedBox(height: 12),
                    Text(
                      resetState.error.toString(),
                      style: TextStyle(color: theme.colorScheme.error),
                      textAlign: TextAlign.center,
                    ),
                  ],
                  const SizedBox(height: 24),
                  AppButton(
                    text: 'Reset Password',
                    onPressed: _handleSubmit,
                    isLoading: isLoading,
                    isFullWidth: true,
                  ),
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
      ),
    );
  }
}
