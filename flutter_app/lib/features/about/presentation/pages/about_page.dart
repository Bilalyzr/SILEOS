import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:sashalms/config/theme.dart';
import 'package:sashalms/config/design_tokens.dart';

class AboutPage extends StatelessWidget {
  const AboutPage({super.key});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;

    return Scaffold(
      appBar: AppBar(
        title: const Text('About SashaInfinity'),
      ),
      body: SingleChildScrollView(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Hero / Who We Are Section
            Container(
              width: double.infinity,
              padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 44),
              decoration: const BoxDecoration(gradient: AppGradients.deep),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                    decoration: BoxDecoration(
                      gradient: AppGradients.fire,
                      borderRadius: BorderRadius.circular(AppRadius.pill),
                    ),
                    child: Text(
                      '✨ WHO WE ARE',
                      style: GoogleFonts.plusJakartaSans(
                        color: Colors.white,
                        fontSize: 11,
                        fontWeight: FontWeight.w700,
                        letterSpacing: 1.2,
                      ),
                    ),
                  ),
                  const SizedBox(height: 16),
                  Text(
                    'The Leading Global Marketplace For Learning And Instruction',
                    style: theme.textTheme.headlineSmall?.copyWith(
                      color: Colors.white,
                      fontWeight: FontWeight.w800,
                      height: 1.2,
                    ),
                  ),
                  const SizedBox(height: 16),
                  Text(
                    'SashaInfinity is reimagining the future of learning through immersive AR/VR experiences, hybrid tutoring centers, and data-driven personalized education for K12 and college students across India.',
                    style: theme.textTheme.bodyMedium?.copyWith(
                      color: Colors.white.withOpacity(0.9),
                      height: 1.5,
                    ),
                    textAlign: TextAlign.justify,
                  ),
                ],
              ),
            ),

            // Problem & Mission Section
            Padding(
              padding: const EdgeInsets.all(24.0),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  _buildSectionCard(
                    title: '🧩 THE PROBLEM WE\'RE SOLVING',
                    subtitle: 'Bridging the Educational Divide',
                    body: 'Over 80% of students in India\'s smaller cities lack access to quality math education. We\'re here to change that through interactive, contextual, and immersive learning models.',
                    icon: Icons.extension_outlined,
                    color: AppTheme.danger,
                    isDark: isDark,
                    theme: theme,
                  ),
                  const SizedBox(height: 16),
                  _buildSectionCard(
                    title: '🎯 OUR MISSION',
                    subtitle: 'Accessible, Engaging Education',
                    body: 'To make quality math and science education engaging, accessible, and effective by leveraging immersive technologies and hybrid tutoring, empowering learners regardless of geography.',
                    icon: Icons.track_changes_outlined,
                    color: AppTheme.success,
                    isDark: isDark,
                    theme: theme,
                  ),
                ],
              ),
            ),

            // Top Class Mentors Section
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 8),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Top Class Mentors',
                    style: theme.textTheme.titleLarge?.copyWith(fontWeight: FontWeight.bold),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    'Our qualified people matter',
                    style: theme.textTheme.bodySmall?.copyWith(color: Colors.grey),
                  ),
                  const SizedBox(height: 16),
                  _buildMentorCard(
                    name: 'Deepikasri',
                    expertise: 'Expert in Data Analytics',
                    photoUrl: 'https://sashainfinity.com/wp-content/uploads/2025/06/Sasha_tutor_profile.jpg',
                    rating: 5.0,
                    isDark: isDark,
                    theme: theme,
                  ),
                  const SizedBox(height: 12),
                  _buildMentorCard(
                    name: 'Sowmiya',
                    expertise: 'Specialist in Mathematics',
                    photoUrl: 'https://ui-avatars.com/api/?name=Sowmiya&background=6366f1&color=fff&size=200',
                    rating: 4.9,
                    isDark: isDark,
                    theme: theme,
                  ),
                  const SizedBox(height: 12),
                  _buildMentorCard(
                    name: 'Saran',
                    expertise: 'Expert in Full Stack Web Development',
                    photoUrl: 'https://ui-avatars.com/api/?name=Saran&background=8b5cf6&color=fff&size=200',
                    rating: 4.8,
                    isDark: isDark,
                    theme: theme,
                  ),
                  const SizedBox(height: 24),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildSectionCard({
    required String title,
    required String subtitle,
    required String body,
    required IconData icon,
    required Color color,
    required bool isDark,
    required ThemeData theme,
  }) {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: isDark ? AppTheme.surfaceDark : Colors.white,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(
          color: isDark ? const Color(0xFF273449) : const Color(0xFFEEF2F6),
        ),
        boxShadow: isDark ? null : AppShadows.card,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(icon, color: color, size: 24),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  title,
                  style: GoogleFonts.plusJakartaSans(
                    fontWeight: FontWeight.bold,
                    color: color,
                    fontSize: 12,
                    letterSpacing: 1.1,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Text(
            subtitle,
            style: theme.textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 8),
          Text(
            body,
            style: theme.textTheme.bodyMedium?.copyWith(
              color: theme.textTheme.bodyMedium?.color?.withOpacity(0.7),
              height: 1.4,
            ),
            textAlign: TextAlign.justify,
          ),
        ],
      ),
    );
  }

  Widget _buildMentorCard({
    required String name,
    required String expertise,
    required String photoUrl,
    required double rating,
    required bool isDark,
    required ThemeData theme,
  }) {
    return Container(
      padding: const EdgeInsets.all(12),
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
          CircleAvatar(
            radius: 30,
            foregroundImage: NetworkImage(photoUrl),
            onForegroundImageError: (_, __) {},
            backgroundColor: AppTheme.primary.withOpacity(0.1),
            child: const Icon(Icons.person_outline),
          ),
          const SizedBox(width: 16),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  name,
                  style: GoogleFonts.plusJakartaSans(
                    fontWeight: FontWeight.bold,
                    fontSize: 15,
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  expertise,
                  style: theme.textTheme.bodySmall?.copyWith(
                    color: theme.textTheme.bodySmall?.color?.withOpacity(0.7),
                  ),
                ),
                const SizedBox(height: 4),
                Row(
                  children: [
                    const Icon(Icons.star, color: Colors.amber, size: 14),
                    const SizedBox(width: 4),
                    Text(
                      rating.toStringAsFixed(1),
                      style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 12),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
