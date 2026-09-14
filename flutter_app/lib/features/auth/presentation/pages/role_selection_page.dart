// lib/features/auth/presentation/pages/role_selection_page.dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../providers/auth_provider.dart';

class RoleSelectionPage extends ConsumerWidget {
  final String email;
  final String name;
  final String picture;
  final String token;

  const RoleSelectionPage({
    super.key,
    required this.email,
    required this.name,
    required this.picture,
    required this.token,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final theme = Theme.of(context);

    return Scaffold(
      backgroundColor: theme.colorScheme.surface,
      body: SafeArea(
        child: Center(
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                if (picture.isNotEmpty)
                  CircleAvatar(
                    radius: 48,
                    backgroundImage: NetworkImage(picture),
                  )
                else
                  const CircleAvatar(
                    radius: 48,
                    child: Icon(Icons.person_outline, size: 48),
                  ),
                const SizedBox(height: 24),
                Text(
                  'Welcome${name.isNotEmpty ? ', $name' : ''}!',
                  style: theme.textTheme.headlineMedium?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: 8),
                Text(
                  email,
                  style: theme.textTheme.bodyLarge?.copyWith(
                    color: theme.colorScheme.onSurface.withOpacity(0.6),
                  ),
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: 32),
                Text(
                  'How do you want to join?',
                  style: theme.textTheme.titleLarge?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: 24),
                Row(
                  children: [
                    Expanded(
                      child: _RoleCard(
                        title: 'Student',
                        subtitle: 'Learn from experts',
                        icon: Icons.person_outline,
                        color: theme.colorScheme.primary,
                        onTap: () => _selectRole(context, ref, 'student'),
                      ),
                    ),
                    const SizedBox(width: 16),
                    Expanded(
                      child: _RoleCard(
                        title: 'Instructor',
                        subtitle: 'Teach & earn',
                        icon: Icons.school_outlined,
                        color: Colors.deepPurple,
                        onTap: () => _selectRole(context, ref, 'instructor'),
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  void _selectRole(BuildContext context, WidgetRef ref, String role) {
    ref.read(authProvider.notifier).completeGoogleSignIn(
          firebaseToken: token,
          role: role,
        );
  }
}

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
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(16),
      child: Container(
        padding: const EdgeInsets.all(24),
        decoration: BoxDecoration(
          border: Border.all(color: color, width: 2),
          borderRadius: BorderRadius.circular(16),
          color: color.withOpacity(0.05),
        ),
        child: Column(
          children: [
            Icon(icon, color: color, size: 48),
            const SizedBox(height: 16),
            Text(
              title,
              style: TextStyle(
                fontWeight: FontWeight.bold,
                color: color,
                fontSize: 18,
              ),
            ),
            const SizedBox(height: 8),
            Text(
              subtitle,
              style: TextStyle(
                fontSize: 14,
                color: Colors.grey.shade700,
              ),
              textAlign: TextAlign.center,
            ),
          ],
        ),
      ),
    );
  }
}
