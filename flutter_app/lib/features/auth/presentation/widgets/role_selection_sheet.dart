// lib/features/auth/presentation/widgets/role_selection_sheet.dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../providers/auth_provider.dart';

/// Bottom sheet asking a first-time Google user to pick a role before the
/// backend creates their account (POST /auth/google/complete).
class RoleSelectionSheet extends ConsumerWidget {
  final String email;
  final String name;
  final String picture;
  final String firebaseToken;

  const RoleSelectionSheet({
    super.key,
    required this.email,
    required this.name,
    required this.picture,
    required this.firebaseToken,
  });

  static Future<void> show(
    BuildContext context, {
    required String email,
    required String name,
    required String picture,
    required String firebaseToken,
  }) {
    return showModalBottomSheet(
      context: context,
      isDismissible: false,
      enableDrag: false,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (_) => RoleSelectionSheet(
        email: email,
        name: name,
        picture: picture,
        firebaseToken: firebaseToken,
      ),
    );
  }

  void _selectRole(BuildContext context, WidgetRef ref, String role) {
    Navigator.of(context).pop();
    ref.read(authProvider.notifier).completeGoogleSignIn(
          firebaseToken: firebaseToken,
          role: role,
        );
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final theme = Theme.of(context);

    return SafeArea(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            if (picture.isNotEmpty)
              CircleAvatar(
                radius: 28,
                backgroundImage: NetworkImage(picture),
              )
            else
              const CircleAvatar(
                radius: 28,
                child: Icon(Icons.person_outline),
              ),
            const SizedBox(height: 12),
            Text(
              'Welcome${name.isNotEmpty ? ', $name' : ''}!',
              style: theme.textTheme.titleLarge?.copyWith(
                fontWeight: FontWeight.bold,
              ),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 4),
            Text(
              email,
              style: theme.textTheme.bodySmall?.copyWith(
                color: theme.colorScheme.onSurface.withOpacity(0.6),
              ),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 16),
            Text(
              'How do you want to join?',
              style: theme.textTheme.bodyMedium?.copyWith(
                fontWeight: FontWeight.bold,
              ),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 16),
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
                const SizedBox(width: 12),
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
      borderRadius: BorderRadius.circular(12),
      child: Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          border: Border.all(color: color, width: 2),
          borderRadius: BorderRadius.circular(12),
        ),
        child: Column(
          children: [
            Icon(icon, color: color, size: 32),
            const SizedBox(height: 8),
            Text(
              title,
              style: TextStyle(
                fontWeight: FontWeight.bold,
                color: color,
              ),
            ),
            Text(
              subtitle,
              style: TextStyle(
                fontSize: 11,
                color: Colors.grey.shade600,
              ),
              textAlign: TextAlign.center,
            ),
          ],
        ),
      ),
    );
  }
}
