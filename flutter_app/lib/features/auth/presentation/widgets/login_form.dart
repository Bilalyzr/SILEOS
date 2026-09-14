// lib/features/auth/presentation/widgets/login_form.dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../../../shared/widgets/common/app_input.dart';
import '../../../../shared/widgets/common/app_button.dart';
import '../../../../shared/widgets/common/app_snackbar.dart';
import '../providers/auth_provider.dart';
import '../providers/email_verification_provider.dart';
import '../utils/auth_error_text.dart';

class LoginForm extends ConsumerStatefulWidget {
  const LoginForm({super.key});

  @override
  ConsumerState<LoginForm> createState() => _LoginFormState();
}

class _LoginFormState extends ConsumerState<LoginForm> {
  final _formKey = GlobalKey<FormState>();
  final _emailController = TextEditingController();
  final _passwordController = TextEditingController();
  bool _obscurePassword = true;
  // Shown when login fails with the backend's "verify your email" 403.
  bool _showResendVerification = false;
  // Prevents a double-submit (button tap + keyboard "done" both firing).
  bool _isSubmitting = false;

  @override
  void dispose() {
    _emailController.dispose();
    _passwordController.dispose();
    super.dispose();
  }

  void _handleSubmit() async {
    if (_isSubmitting) return;
    if (_formKey.currentState!.validate()) {
      _isSubmitting = true;
      try {
        await ref.read(authProvider.notifier).login(
              email: _emailController.text.trim(),
              password: _passwordController.text,
            );
      } finally {
        if (mounted) _isSubmitting = false;
      }
    }
  }

  Future<void> _handleResendVerification() async {
    final email = _emailController.text.trim();
    if (email.isEmpty) return;
    final ok =
        await ref.read(emailVerificationProvider.notifier).resend(email);
    if (!mounted) return;
    if (ok) {
      AppSnackbar.success(context,
          'If the account exists and needs verification, a new email has been sent.');
    } else {
      AppSnackbar.error(context, 'Could not resend the email. Please try again.');
    }
  }

  @override
  Widget build(BuildContext context) {
    final authState = ref.watch(authProvider);
    final isLoading = authState.maybeWhen(
      loading: () => true,
      orElse: () => false,
    );

    // Show a polished, humanized error snackbar.
    authState.maybeWhen(
      error: (errorMessage) {
        if (errorMessage.isNotEmpty) {
          WidgetsBinding.instance.addPostFrameCallback((_) {
            if (!mounted) return;
            AppSnackbar.error(context, humanizeAuthError(errorMessage));
            // Unverified-email 403 gets an inline resend action.
            final needsVerification =
                errorMessage.toLowerCase().contains('verif');
            if (needsVerification != _showResendVerification) {
              setState(() => _showResendVerification = needsVerification);
            }
            ref.read(authProvider.notifier).clearError();
          });
        }
        return null;
      },
      orElse: () {},
    );

    return Form(
      key: _formKey,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          AppInput(
            label: 'Email',
            hint: 'Enter your email',
            controller: _emailController,
            keyboardType: TextInputType.emailAddress,
            textInputAction: TextInputAction.next,
            validator: (value) {
              if (value == null || value.trim().isEmpty) {
                return 'Email is required';
              }
              if (!RegExp(r'^[\w-\.]+@([\w-]+\.)+[\w-]{2,4}$').hasMatch(value)) {
                return 'Enter a valid email';
              }
              return null;
            },
            prefixIcon: const Icon(Icons.email_outlined),
          ),
          const SizedBox(height: 16),
          AppInput(
            label: 'Password',
            hint: 'Enter your password',
            controller: _passwordController,
            obscureText: _obscurePassword,
            textInputAction: TextInputAction.done,
            onFieldSubmitted: (_) => _handleSubmit(),
            validator: (value) {
              if (value == null || value.isEmpty) {
                return 'Password is required';
              }
              if (value.length < 6) {
                return 'Password must be at least 6 characters';
              }
              return null;
            },
            prefixIcon: const Icon(Icons.lock_outlined),
            suffixIcon: IconButton(
              icon: Icon(_obscurePassword ? Icons.visibility_outlined : Icons.visibility),
              onPressed: () {
                setState(() => _obscurePassword = !_obscurePassword);
              },
            ),
          ),
          const SizedBox(height: 8),
          Align(
            alignment: Alignment.centerRight,
            child: TextButton(
              onPressed: () => context.push('/forgot-password'),
              child: const Text('Forgot password?'),
            ),
          ),
          if (_showResendVerification)
            Align(
              alignment: Alignment.center,
              child: TextButton.icon(
                onPressed: _handleResendVerification,
                icon: const Icon(Icons.mark_email_unread_outlined, size: 18),
                label: const Text('Resend verification email'),
              ),
            ),
          const SizedBox(height: 24),
          AppButton(
            text: 'Sign In',
            onPressed: _handleSubmit,
            isLoading: isLoading,
            isFullWidth: true,
          ),
        ],
      ),
    );
  }
}
