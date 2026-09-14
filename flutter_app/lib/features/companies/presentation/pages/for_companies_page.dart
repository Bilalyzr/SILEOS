import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:sashalms/config/theme.dart';
import 'package:sashalms/config/design_tokens.dart';
import 'company_signup_page.dart';

class ForCompaniesPage extends StatelessWidget {
  const ForCompaniesPage({super.key});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;

    return Scaffold(
      appBar: AppBar(
        title: const Text('For Companies'),
      ),
      body: SingleChildScrollView(
        child: Padding(
          padding: const EdgeInsets.all(24.0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Hero Section
              Center(
                child: Column(
                  children: [
                    Container(
                      width: 92,
                      height: 92,
                      decoration: BoxDecoration(
                        gradient: AppGradients.primary,
                        borderRadius: BorderRadius.circular(AppRadius.lg),
                        boxShadow: AppShadows.primaryGlow,
                      ),
                      child: const Icon(Icons.business_center_rounded,
                          size: 46, color: Colors.white),
                    ),
                    const SizedBox(height: 24),
                    Text(
                      'Hire Pre-Vetted, Course-Certified Talent',
                      textAlign: TextAlign.center,
                      style: GoogleFonts.plusJakartaSans(
                        fontWeight: FontWeight.w800,
                        fontSize: 25,
                        letterSpacing: -0.5,
                        height: 1.15,
                      ),
                    ),
                    const SizedBox(height: 12),
                    Text(
                      'SashaInfinity LMS graduates complete rigorous, instructor-led courses. Get access to students who are ready to contribute from day one — filtered by skills, roles, and availability.',
                      textAlign: TextAlign.center,
                      style: theme.textTheme.bodyMedium?.copyWith(
                        color: theme.textTheme.bodyMedium?.color?.withOpacity(0.7),
                        height: 1.5,
                      ),
                    ),
                    const SizedBox(height: 24),
                    Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        ElevatedButton(
                          onPressed: () => Navigator.push(
                            context,
                            MaterialPageRoute(
                              builder: (_) => const CompanySignupPage(),
                            ),
                          ),
                          style: ElevatedButton.styleFrom(
                            padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
                          ),
                          child: const Text('Create Company Account'),
                        ),
                      ],
                    ),
                  ],
                ),
              ),

              const SizedBox(height: 40),

              Text(
                'Why Hire From SashaInfinity?',
                style: theme.textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 16),

              // Benefits
              _buildBenefitCard(
                title: 'Pre-filtered candidates',
                body: 'See only students who finished a course and opted in to be hired.',
                icon: Icons.filter_alt_outlined,
                isDark: isDark,
                theme: theme,
              ),
              const SizedBox(height: 12),
              _buildBenefitCard(
                title: 'Express interest, no spam',
                body: 'Send one message. Candidate accepts or declines. Contact revealed on acceptance.',
                icon: Icons.chat_bubble_outline,
                isDark: isDark,
                theme: theme,
              ),
              const SizedBox(height: 12),
              _buildBenefitCard(
                title: 'No recruiter fees',
                body: 'Free to browse. No per-hire placement charges while in beta.',
                icon: Icons.money_off_outlined,
                isDark: isDark,
                theme: theme,
              ),

              const SizedBox(height: 32),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildBenefitCard({
    required String title,
    required String body,
    required IconData icon,
    required bool isDark,
    required ThemeData theme,
  }) {
    return Container(
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
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, color: AppTheme.primary, size: 24),
          const SizedBox(width: 16),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: GoogleFonts.plusJakartaSans(
                    fontWeight: FontWeight.bold,
                    fontSize: 14,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  body,
                  style: theme.textTheme.bodyMedium?.copyWith(
                    color: theme.textTheme.bodyMedium?.color?.withOpacity(0.7),
                    fontSize: 12,
                    height: 1.4,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
