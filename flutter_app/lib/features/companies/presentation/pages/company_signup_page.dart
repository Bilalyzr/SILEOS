import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:sashalms/config/theme.dart';
import 'package:sashalms/config/design_tokens.dart';
import 'package:sashalms/core/network/network_provider.dart';
import 'package:sashalms/shared/widgets/common/app_snackbar.dart';

/// Self-serve company signup, mirroring the web `for-companies/signup` page.
/// Posts to `POST /api/v1/companies/signup`; the account is created
/// unapproved, and an admin reviews it before it can sign in.
class CompanySignupPage extends ConsumerStatefulWidget {
  const CompanySignupPage({super.key});

  @override
  ConsumerState<CompanySignupPage> createState() => _CompanySignupPageState();
}

class _CompanySignupPageState extends ConsumerState<CompanySignupPage> {
  final _formKey = GlobalKey<FormState>();

  final _name = TextEditingController();
  final _email = TextEditingController();
  final _phone = TextEditingController();
  final _website = TextEditingController();
  final _industry = TextEditingController();
  final _description = TextEditingController();
  final _password = TextEditingController();

  String? _teamSize;
  bool _obscure = true;
  bool _submitting = false;

  static const _teamSizes = ['1-10', '11-50', '51-200', '200+'];

  @override
  void dispose() {
    _name.dispose();
    _email.dispose();
    _phone.dispose();
    _website.dispose();
    _industry.dispose();
    _description.dispose();
    _password.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() => _submitting = true);
    try {
      await ref.read(apiClientProvider).post(
        '/api/v1/companies/signup',
        data: {
          'name': _name.text.trim(),
          'contact_email': _email.text.trim(),
          'password': _password.text,
          'contact_phone': _phone.text.trim(),
          'website': _website.text.trim(),
          'industry': _industry.text.trim(),
          'team_size': _teamSize ?? '',
          'description': _description.text.trim(),
        },
      );
      if (!mounted) return;
      AppSnackbar.success(
        context,
        'Signup received — we will notify you by email once approved.',
      );
      context.go('/login');
    } on DioException catch (e) {
      if (!mounted) return;
      final detail = e.response?.data is Map
          ? (e.response?.data['detail']?.toString())
          : null;
      AppSnackbar.error(context, detail ?? 'Signup failed. Please try again.');
    } catch (_) {
      if (mounted) {
        AppSnackbar.error(context, 'Signup failed. Please try again.');
      }
    } finally {
      if (mounted) setState(() => _submitting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;

    return Scaffold(
      backgroundColor: isDark ? AppTheme.backgroundDark : AppNeutrals.slate50,
      appBar: AppBar(title: const Text('Create Company Account')),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.fromLTRB(20, 16, 20, 32),
          child: Form(
            key: _formKey,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Container(
                  width: 64,
                  height: 64,
                  decoration: BoxDecoration(
                    gradient: AppGradients.primary,
                    borderRadius: BorderRadius.circular(AppRadius.lg),
                    boxShadow: AppShadows.primaryGlow,
                  ),
                  child: const Icon(Icons.business_center_rounded,
                      size: 32, color: Colors.white),
                ),
                const SizedBox(height: 18),
                Text(
                  'Create a company account',
                  style: GoogleFonts.plusJakartaSans(
                    fontWeight: FontWeight.w800,
                    fontSize: 23,
                    letterSpacing: -0.4,
                  ),
                ),
                const SizedBox(height: 6),
                Text(
                  'After you submit, an administrator reviews your account. '
                  'You will be notified by email once approved.',
                  style: theme.textTheme.bodyMedium?.copyWith(
                    color: theme.textTheme.bodyMedium?.color?.withOpacity(0.7),
                    height: 1.45,
                  ),
                ),
                const SizedBox(height: 24),

                _field(
                  controller: _name,
                  label: 'Company name *',
                  validator: (v) => (v == null || v.trim().isEmpty)
                      ? 'Company name is required'
                      : null,
                ),
                _field(
                  controller: _email,
                  label: 'Contact email *',
                  keyboardType: TextInputType.emailAddress,
                  validator: (v) {
                    final t = v?.trim() ?? '';
                    if (t.isEmpty) return 'Contact email is required';
                    if (!t.contains('@') || !t.contains('.')) {
                      return 'Enter a valid email';
                    }
                    return null;
                  },
                ),
                Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Expanded(
                      child: _field(
                        controller: _phone,
                        label: 'Phone',
                        keyboardType: TextInputType.phone,
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: _field(
                        controller: _website,
                        label: 'Website',
                        hint: 'https://...',
                        keyboardType: TextInputType.url,
                      ),
                    ),
                  ],
                ),
                Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Expanded(
                      child: _field(
                        controller: _industry,
                        label: 'Industry',
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(child: _teamSizeField(theme, isDark)),
                  ],
                ),
                _field(
                  controller: _description,
                  label: 'About the company',
                  maxLines: 3,
                ),
                _field(
                  controller: _password,
                  label: 'Password *',
                  obscure: _obscure,
                  suffix: IconButton(
                    icon: Icon(_obscure
                        ? Icons.visibility_outlined
                        : Icons.visibility_off_outlined),
                    onPressed: () => setState(() => _obscure = !_obscure),
                  ),
                  validator: (v) => (v == null || v.length < 8)
                      ? 'Password must be at least 8 characters'
                      : null,
                ),
                const SizedBox(height: 8),
                SizedBox(
                  height: 52,
                  child: ElevatedButton(
                    onPressed: _submitting ? null : _submit,
                    child: _submitting
                        ? const SizedBox(
                            height: 22,
                            width: 22,
                            child: CircularProgressIndicator(
                                strokeWidth: 2, color: Colors.white),
                          )
                        : const Text('Create account'),
                  ),
                ),
                const SizedBox(height: 16),
                Center(
                  child: Wrap(
                    crossAxisAlignment: WrapCrossAlignment.center,
                    children: [
                      Text(
                        'Already have a company account? ',
                        style: theme.textTheme.bodySmall?.copyWith(
                          color: theme.textTheme.bodySmall?.color
                              ?.withOpacity(0.7),
                        ),
                      ),
                      GestureDetector(
                        onTap: () => context.go('/login'),
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
      ),
    );
  }

  Widget _field({
    required TextEditingController controller,
    required String label,
    String? hint,
    bool obscure = false,
    int maxLines = 1,
    TextInputType keyboardType = TextInputType.text,
    String? Function(String?)? validator,
    Widget? suffix,
  }) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            label,
            style: GoogleFonts.inter(
              fontSize: 13.5,
              fontWeight: FontWeight.w600,
            ),
          ),
          const SizedBox(height: 7),
          TextFormField(
            controller: controller,
            obscureText: obscure,
            maxLines: obscure ? 1 : maxLines,
            keyboardType: keyboardType,
            validator: validator,
            decoration: InputDecoration(
              hintText: hint,
              isDense: true,
              suffixIcon: suffix,
            ),
          ),
        ],
      ),
    );
  }

  Widget _teamSizeField(ThemeData theme, bool isDark) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Team size',
            style: GoogleFonts.inter(
              fontSize: 13.5,
              fontWeight: FontWeight.w600,
            ),
          ),
          const SizedBox(height: 7),
          DropdownButtonFormField<String>(
            value: _teamSize,
            isDense: true,
            decoration: const InputDecoration(isDense: true),
            hint: const Text('—'),
            items: _teamSizes
                .map((s) => DropdownMenuItem(value: s, child: Text(s)))
                .toList(),
            onChanged: (v) => setState(() => _teamSize = v),
          ),
        ],
      ),
    );
  }
}
