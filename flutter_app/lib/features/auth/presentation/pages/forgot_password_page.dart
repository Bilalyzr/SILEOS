// lib/features/auth/presentation/pages/forgot_password_page.dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../../../config/design_tokens.dart';
import '../../../../shared/widgets/common/app_button.dart';
import '../../../../shared/widgets/common/app_input.dart';
import '../providers/password_reset_provider.dart';

class ForgotPasswordPage extends ConsumerStatefulWidget {
  const ForgotPasswordPage({super.key});

  @override
  ConsumerState<ForgotPasswordPage> createState() => _ForgotPasswordPageState();
}

class _ForgotPasswordPageState extends ConsumerState<ForgotPasswordPage> {
  final _formKey = GlobalKey<FormState>();
  final _emailController = TextEditingController();
  bool _emailSent = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      ref.read(passwordResetProvider.notifier).reset();
    });
  }

  @override
  void dispose() {
    _emailController.dispose();
    super.dispose();
  }

  Future<void> _handleSubmit() async {
    if (!_formKey.currentState!.validate()) return;
    final ok = await ref
        .read(passwordResetProvider.notifier)
        .sendForgotEmail(_emailController.text.trim());
    if (ok && mounted) setState(() => _emailSent = true);
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final resetState = ref.watch(passwordResetProvider);
    final isLoading = resetState.isLoading;

    return Scaffold(
      appBar: AppBar(title: const Text('Forgot Password')),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: SingleChildScrollView(
            child: _emailSent ? _buildSuccess(theme) : _buildForm(theme, isLoading, resetState),
          ),
        ),
      ),
    );
  }

  Widget _buildForm(
    ThemeData theme,
    bool isLoading,
    AsyncValue<String?> resetState,
  ) {
    return Form(
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
                Icons.lock_reset_rounded,
                size: 42,
                color: Colors.white,
              ),
            ),
          ),
          const SizedBox(height: 20),
          Text(
            'Reset your password',
            style: theme.textTheme.headlineSmall?.copyWith(
              fontWeight: FontWeight.bold,
            ),
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: 8),
          Text(
            'Enter the email for your account and we will send you a password reset link.',
            style: theme.textTheme.bodyMedium?.copyWith(
              color: theme.colorScheme.onSurface.withOpacity(0.6),
            ),
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: 32),
          AppInput(
            label: 'Email',
            hint: 'Enter your email',
            controller: _emailController,
            keyboardType: TextInputType.emailAddress,
            textInputAction: TextInputAction.done,
            onFieldSubmitted: (_) => _handleSubmit(),
            validator: (value) {
              if (value == null || value.trim().isEmpty) {
                return 'Email is required';
              }
              if (!RegExp(r'^[\w-\.]+@([\w-]+\.)+[\w-]{2,4}$')
                  .hasMatch(value)) {
                return 'Enter a valid email';
              }
              return null;
            },
            prefixIcon: const Icon(Icons.email_outlined),
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
            text: 'Send Reset Link',
            onPressed: _handleSubmit,
            isLoading: isLoading,
            isFullWidth: true,
          ),
        ],
      ),
    );
  }

  Widget _buildSuccess(ThemeData theme) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Center(
          child: Container(
            width: 84,
            height: 84,
            decoration: BoxDecoration(
              color: const Color(0xFF22C55E).withOpacity(0.12),
              borderRadius: BorderRadius.circular(AppRadius.lg),
            ),
            child: const Icon(Icons.mark_email_read_rounded,
                size: 42, color: Color(0xFF16A34A)),
          ),
        ),
        const SizedBox(height: 20),
        Text(
          'Check your inbox',
          style: theme.textTheme.headlineSmall?.copyWith(
            fontWeight: FontWeight.bold,
          ),
          textAlign: TextAlign.center,
        ),
        const SizedBox(height: 8),
        Text(
          'If an account exists for ${_emailController.text.trim()}, a password '
          'reset link has been sent. Open the link from your email to set a new '
          'password, then return here to sign in with it.',
          style: theme.textTheme.bodyMedium?.copyWith(
            color: theme.colorScheme.onSurface.withOpacity(0.6),
          ),
          textAlign: TextAlign.center,
        ),
        const SizedBox(height: 32),
        AppButton(
          text: 'Back to Sign In',
          onPressed: () => context.go('/login'),
          isFullWidth: true,
        ),
      ],
    );
  }
}
