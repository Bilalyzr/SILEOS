// lib/features/auth/presentation/widgets/register_form.dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../../../shared/widgets/common/app_input.dart';
import '../../../../shared/widgets/common/app_button.dart';
import '../../../../shared/widgets/common/app_snackbar.dart';
import '../providers/auth_provider.dart';
import '../providers/auth_state.dart';
import '../utils/auth_error_text.dart';

/// A four-step registration wizard:
///   1. Pick a role (student / instructor)
///   2. Enter personal details (name, email, phone)
///   3. Create a password (+ confirm)
///   4. Review & create the account
///
/// Steps slide/fade between each other and each step validates before the
/// user is allowed to advance, so they never reach the final submit with a
/// half-filled form.
class RegisterForm extends ConsumerStatefulWidget {
  /// When provided (from the Get Started screen), pre-selects the role and
  /// starts the wizard at the details step instead of the role step.
  final String? initialRole;

  const RegisterForm({super.key, this.initialRole});

  @override
  ConsumerState<RegisterForm> createState() => _RegisterFormState();
}

class _RegisterFormState extends ConsumerState<RegisterForm> {
  static const int _totalSteps = 4;

  // Mirrors the backend password rule: 8+ chars with an upper, a lower and a
  // digit. The form enforces it so registration isn't rejected server-side
  // (which would otherwise look like "create account doesn't work").
  static final RegExp _passwordRule =
      RegExp(r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).{8,}$');

  // Each step that has inputs owns its own form key so we can validate just
  // that step before advancing, rather than the whole wizard at once.
  final _detailsFormKey = GlobalKey<FormState>();
  final _passwordFormKey = GlobalKey<FormState>();

  final _emailController = TextEditingController();
  final _phoneController = TextEditingController();
  final _passwordController = TextEditingController();
  final _confirmPasswordController = TextEditingController();

  String _userType = 'student';
  bool _obscurePassword = true;
  bool _obscureConfirmPassword = true;

  int _currentStep = 0;
  // Drives the slide direction of the step transition (forward vs. back).
  bool _isForward = true;

  // Guards against a double-submit (button tap + keyboard "done" both firing),
  // which would create the account on the first call and then get a 400
  // "already registered" on the second — wrongly overwriting the success.
  bool _isSubmitting = false;

  @override
  void initState() {
    super.initState();
    // A role chosen on the Get Started screen pre-selects it here and skips the
    // role step, dropping the user straight onto the details step (step 2).
    final role = widget.initialRole;
    if (role == 'student' || role == 'instructor') {
      _userType = role!;
      _currentStep = 1;
    }
  }

  @override
  void dispose() {
    _emailController.dispose();
    _phoneController.dispose();
    _passwordController.dispose();
    _confirmPasswordController.dispose();
    super.dispose();
  }

  bool _validateCurrentStep() {
    switch (_currentStep) {
      case 0:
        return true; // Role is always selected (defaults to student).
      case 1:
        return _detailsFormKey.currentState?.validate() ?? false;
      case 2:
        return _passwordFormKey.currentState?.validate() ?? false;
      default:
        return true;
    }
  }

  void _goToStep(int step, {required bool forward}) {
    FocusScope.of(context).unfocus();
    setState(() {
      _isForward = forward;
      _currentStep = step;
    });
  }

  void _nextStep() {
    if (!_validateCurrentStep()) return;
    if (_currentStep < _totalSteps - 1) {
      _goToStep(_currentStep + 1, forward: true);
    }
  }

  void _previousStep() {
    if (_currentStep > 0) {
      _goToStep(_currentStep - 1, forward: false);
    }
  }

  void _handleSubmit() async {
    if (_isSubmitting) return;

    // Validate from the captured VALUES, not the step Forms. By the review step
    // the data-step Forms are unmounted (the AnimatedSwitcher only keeps the
    // current step), so their GlobalKey state is null — relying on it would
    // wrongly read as "invalid" and bounce the user back to step 1. The values
    // live in the controllers and are always available.
    final email = _emailController.text.trim();
    final password = _passwordController.text;
    final confirm = _confirmPasswordController.text;

    final emailOk =
        RegExp(r'^[\w-\.]+@([\w-]+\.)+[\w-]{2,4}$').hasMatch(email);
    if (!emailOk) {
      _goToStep(1, forward: false);
      // Re-show the inline field errors once the Form is mounted again.
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (mounted) _detailsFormKey.currentState?.validate();
      });
      return;
    }
    if (!_passwordRule.hasMatch(password) || password != confirm) {
      _goToStep(2, forward: false);
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (mounted) _passwordFormKey.currentState?.validate();
      });
      return;
    }

    _isSubmitting = true;
    try {
      await ref.read(authProvider.notifier).register(
            email: email,
            password: password,
            firstName: '',
            lastName: '',
            phone: _phoneController.text.trim().isEmpty
                ? null
                : _phoneController.text.trim(),
            userType: _userType,
          );
    } finally {
      if (mounted) _isSubmitting = false;
    }
  }

  @override
  Widget build(BuildContext context) {
    final authState = ref.watch(authProvider);
    final theme = Theme.of(context);
    final isLoading = authState.maybeWhen(
      loading: () => true,
      orElse: () => false,
    );

    // Registration issues no tokens. When the account still needs email
    // verification we go to the verify-email notice. When AUTO_VERIFY already
    // activated it, the provider emits `unauthenticated` with a success
    // message and we send the user straight to login. The `wasLoading` guard
    // ensures we only react to a fresh register attempt, not stale state on
    // first build.
    ref.listen<AuthState>(authProvider, (previous, next) {
      final wasLoading =
          previous?.maybeWhen(loading: () => true, orElse: () => false) ??
              false;
      next.maybeWhen(
        registrationSuccess: (email, message) {
          context.go('/verify-email?email=${Uri.encodeQueryComponent(email)}');
        },
        unauthenticated: (message) {
          if (wasLoading) context.go('/login');
        },
        orElse: () {},
      );
    });

    // Show a polished, humanized error snackbar.
    authState.maybeWhen(
      error: (errorMessage) {
        if (errorMessage.isNotEmpty) {
          WidgetsBinding.instance.addPostFrameCallback((_) {
            if (!mounted) return;
            AppSnackbar.error(context, humanizeAuthError(errorMessage));
            ref.read(authProvider.notifier).clearError();
          });
        }
        return null;
      },
      orElse: () {},
    );

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        _StepProgressBar(currentStep: _currentStep, totalSteps: _totalSteps),
        const SizedBox(height: 28),
        AnimatedSwitcher(
          duration: const Duration(milliseconds: 300),
          switchInCurve: Curves.easeOutCubic,
          switchOutCurve: Curves.easeInCubic,
          transitionBuilder: (child, animation) {
            final slide = Tween<Offset>(
              begin: Offset(_isForward ? 0.12 : -0.12, 0),
              end: Offset.zero,
            ).animate(animation);
            return FadeTransition(
              opacity: animation,
              child: SlideTransition(position: slide, child: child),
            );
          },
          // Keep step sizes from jumping; align tops while heights animate.
          layoutBuilder: (currentChild, previousChildren) => Stack(
            alignment: Alignment.topCenter,
            children: [...previousChildren, if (currentChild != null) currentChild],
          ),
          child: KeyedSubtree(
            key: ValueKey<int>(_currentStep),
            child: _buildStep(theme),
          ),
        ),
        const SizedBox(height: 28),
        _buildNavigation(isLoading),
      ],
    );
  }

  Widget _buildStep(ThemeData theme) {
    switch (_currentStep) {
      case 0:
        return _buildRoleStep(theme);
      case 1:
        return _buildDetailsStep(theme);
      case 2:
        return _buildPasswordStep(theme);
      default:
        return _buildReviewStep(theme);
    }
  }

  // ----- Step 1: role -------------------------------------------------------

  Widget _buildRoleStep(ThemeData theme) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        const _StepHeader(
          title: 'I want to join as',
          subtitle: 'Select your role',
        ),
        const SizedBox(height: 20),
        Row(
          children: [
            Expanded(
              child: _buildRoleCard(
                title: 'Student',
                subtitle: 'Learn from experts',
                icon: Icons.person_outline,
                isSelected: _userType == 'student',
                onTap: () => setState(() => _userType = 'student'),
                activeColor: theme.colorScheme.primary,
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: _buildRoleCard(
                title: 'Staff',
                subtitle: 'Teach & mentor',
                icon: Icons.school_outlined,
                isSelected: _userType == 'instructor',
                onTap: () => setState(() => _userType = 'instructor'),
                activeColor: Colors.deepPurple,
              ),
            ),
          ],
        ),
      ],
    );
  }

  // ----- Step 2: details ----------------------------------------------------

  Widget _buildDetailsStep(ThemeData theme) {
    return Form(
      key: _detailsFormKey,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          const _StepHeader(
            title: 'Enter your details',
            subtitle: 'Tell us a little about yourself',
          ),
          const SizedBox(height: 20),
          AppInput(
            label: 'Email Address',
            hint: 'Enter your email address',
            helperText: "We'll send a verification link to this address",
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
            label: 'Phone Number',
            hint: 'Enter your phone number',
            helperText: 'Optional · used for account recovery',
            controller: _phoneController,
            keyboardType: TextInputType.phone,
            textInputAction: TextInputAction.done,
            onFieldSubmitted: (_) => _nextStep(),
            prefixIcon: const Icon(Icons.phone_outlined),
          ),
        ],
      ),
    );
  }

  // ----- Step 3: password ---------------------------------------------------

  Widget _buildPasswordStep(ThemeData theme) {
    return Form(
      key: _passwordFormKey,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          const _StepHeader(
            title: 'Create your password',
            subtitle: 'Keep your account secure',
          ),
          const SizedBox(height: 20),
          AppInput(
            label: 'Password',
            hint: 'Enter your password',
            helperText: 'At least 8 characters with an uppercase, a lowercase and a number',
            controller: _passwordController,
            obscureText: _obscurePassword,
            textInputAction: TextInputAction.next,
            validator: (value) {
              if (value == null || value.isEmpty) {
                return 'Password is required';
              }
              if (!_passwordRule.hasMatch(value)) {
                return 'Use 8+ characters with an uppercase, a lowercase & a number';
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
            label: 'Confirm Password',
            hint: 'Re-enter your password',
            helperText: 'Must match the password above',
            controller: _confirmPasswordController,
            obscureText: _obscureConfirmPassword,
            textInputAction: TextInputAction.done,
            onFieldSubmitted: (_) => _nextStep(),
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
                setState(
                    () => _obscureConfirmPassword = !_obscureConfirmPassword);
              },
            ),
          ),
        ],
      ),
    );
  }

  // ----- Step 4: review -----------------------------------------------------

  Widget _buildReviewStep(ThemeData theme) {
    final phone = _phoneController.text.trim();
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        const _StepHeader(
          title: 'Almost there',
          subtitle: 'Review your details and create your account',
        ),
        const SizedBox(height: 20),
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
          decoration: BoxDecoration(
            color: theme.colorScheme.surfaceVariant.withOpacity(0.4),
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: theme.dividerColor),
          ),
          child: Column(
            children: [
              _ReviewRow(
                icon: _userType == 'instructor'
                    ? Icons.school_outlined
                    : Icons.person_outline,
                label: 'Role',
                value: _userType == 'instructor' ? 'Staff' : 'Student',
              ),
              _ReviewRow(
                icon: Icons.email_outlined,
                label: 'Email',
                value: _emailController.text.trim(),
              ),
              if (phone.isNotEmpty)
                _ReviewRow(
                  icon: Icons.phone_outlined,
                  label: 'Phone',
                  value: phone,
                ),
            ],
          ),
        ),
      ],
    );
  }

  // ----- Navigation ---------------------------------------------------------

  Widget _buildNavigation(bool isLoading) {
    final isFirst = _currentStep == 0;
    final isLast = _currentStep == _totalSteps - 1;

    return Row(
      children: [
        if (!isFirst) ...[
          Expanded(
            child: AppButton(
              text: 'Back',
              variant: ButtonVariant.outline,
              icon: Icons.arrow_back,
              onPressed: isLoading ? null : _previousStep,
              isFullWidth: true,
            ),
          ),
          const SizedBox(width: 12),
        ],
        Expanded(
          child: isLast
              ? AppButton(
                  text: 'Create Account',
                  icon: Icons.check_circle_outline,
                  onPressed: _handleSubmit,
                  isLoading: isLoading,
                  isFullWidth: true,
                )
              : AppButton(
                  text: 'Continue',
                  trailing: const Icon(Icons.arrow_forward, size: 18),
                  onPressed: _nextStep,
                  isFullWidth: true,
                ),
        ),
      ],
    );
  }

  Widget _buildRoleCard({
    required String title,
    required String subtitle,
    required IconData icon,
    required bool isSelected,
    required VoidCallback onTap,
    required Color activeColor,
  }) {
    return GestureDetector(
      onTap: onTap,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 200),
        curve: Curves.easeOut,
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: isSelected ? activeColor.withOpacity(0.1) : Colors.transparent,
          border: Border.all(
            color: isSelected ? activeColor : Colors.grey.shade300,
            width: 2,
          ),
          borderRadius: BorderRadius.circular(12),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Icon(
                  icon,
                  color: isSelected ? activeColor : Colors.grey,
                  size: 28,
                ),
                AnimatedScale(
                  duration: const Duration(milliseconds: 200),
                  scale: isSelected ? 1 : 0,
                  child: Icon(Icons.check_circle, color: activeColor, size: 20),
                ),
              ],
            ),
            const SizedBox(height: 12),
            Text(
              title,
              style: TextStyle(
                fontWeight: FontWeight.bold,
                fontSize: 15,
                color: isSelected ? activeColor : Colors.black87,
              ),
            ),
            const SizedBox(height: 2),
            Text(
              subtitle,
              style: TextStyle(
                fontSize: 11,
                color: Colors.grey.shade600,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// Animated segmented progress bar showing wizard position (1 of 4 …).
class _StepProgressBar extends StatelessWidget {
  final int currentStep;
  final int totalSteps;

  const _StepProgressBar({required this.currentStep, required this.totalSteps});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Row(
          children: List.generate(totalSteps, (index) {
            final isActive = index <= currentStep;
            return Expanded(
              child: Padding(
                padding: EdgeInsets.only(right: index == totalSteps - 1 ? 0 : 6),
                child: AnimatedContainer(
                  duration: const Duration(milliseconds: 300),
                  height: 6,
                  decoration: BoxDecoration(
                    color: isActive
                        ? theme.colorScheme.primary
                        : theme.colorScheme.primary.withOpacity(0.15),
                    borderRadius: BorderRadius.circular(3),
                  ),
                ),
              ),
            );
          }),
        ),
        const SizedBox(height: 8),
        Text(
          'Step ${currentStep + 1} of $totalSteps',
          style: theme.textTheme.bodySmall?.copyWith(
            color: theme.colorScheme.onSurface.withOpacity(0.6),
            fontWeight: FontWeight.w500,
          ),
        ),
      ],
    );
  }
}

/// Title + subtitle shown at the top of each wizard step.
class _StepHeader extends StatelessWidget {
  final String title;
  final String subtitle;

  const _StepHeader({required this.title, required this.subtitle});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          title,
          style: theme.textTheme.titleLarge?.copyWith(
            fontWeight: FontWeight.bold,
          ),
        ),
        const SizedBox(height: 4),
        Text(
          subtitle,
          style: theme.textTheme.bodyMedium?.copyWith(
            color: theme.colorScheme.onSurface.withOpacity(0.6),
          ),
        ),
      ],
    );
  }
}

/// A single labeled row in the review-step summary card.
class _ReviewRow extends StatelessWidget {
  final IconData icon;
  final String label;
  final String value;

  const _ReviewRow({
    required this.icon,
    required this.label,
    required this.value,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 10),
      child: Row(
        children: [
          Icon(icon, size: 20, color: theme.colorScheme.primary),
          const SizedBox(width: 12),
          Text(
            label,
            style: theme.textTheme.bodyMedium?.copyWith(
              color: theme.colorScheme.onSurface.withOpacity(0.6),
            ),
          ),
          const Spacer(),
          Flexible(
            child: Text(
              value,
              textAlign: TextAlign.right,
              overflow: TextOverflow.ellipsis,
              style: theme.textTheme.bodyMedium?.copyWith(
                fontWeight: FontWeight.w600,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
