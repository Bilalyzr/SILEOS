// lib/features/admin/presentation/widgets/admin_user_list_tile.dart
import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:cached_network_image/cached_network_image.dart';
import 'admin_status_chip.dart';

/// A standardised list tile for user rows in the admin Students / Staff lists.
class AdminUserListTile extends StatelessWidget {
  final Map<String, dynamic> user;
  final VoidCallback? onTap;

  const AdminUserListTile({super.key, required this.user, this.onTap});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;
    final name = (user['display_name'] as String?) ??
        (user['username'] as String?) ??
        'Unknown';
    final email = (user['email'] as String?) ?? '';
    final role = (user['role'] as String?) ?? 'student';
    final status = (user['status'] as String?) ?? 'active';
    final avatarUrl = (user['avatar_url'] as String?) ??
        (user['profile_photo_url'] as String?);
    final joinedDate = user['joined_date'] as String?;
    final totalCourses = user['total_courses'] as int?;

    final statusEnum = switch (status) {
      'active' => AdminStatus.active,
      'inactive' => AdminStatus.inactive,
      'suspended' => AdminStatus.suspended,
      _ => AdminStatus.pending,
    };

    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(12),
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 10),
          child: Row(
            children: [
              // Avatar
              CircleAvatar(
                radius: 22,
                backgroundColor: isDark
                    ? const Color(0xFF334155)
                    : const Color(0xFFF1F5F9),
                backgroundImage: avatarUrl != null && avatarUrl.isNotEmpty
                    ? CachedNetworkImageProvider(avatarUrl)
                    : null,
                child: avatarUrl == null || avatarUrl.isEmpty
                    ? Text(
                        name.isNotEmpty ? name[0].toUpperCase() : '?',
                        style: GoogleFonts.inter(
                          fontWeight: FontWeight.w600,
                          color: theme.colorScheme.primary,
                        ),
                      )
                    : null,
              ),
              const SizedBox(width: 12),

              // Name + email + metadata
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Flexible(
                          child: Text(
                            name,
                            style: GoogleFonts.plusJakartaSans(
                              fontSize: 14,
                              fontWeight: FontWeight.w600,
                            ),
                            overflow: TextOverflow.ellipsis,
                          ),
                        ),
                        const SizedBox(width: 6),
                        AdminStatusChip(
                          label: role == 'instructor' ? 'Staff' : role,
                          status: role == 'instructor'
                              ? AdminStatus.private
                              : AdminStatus.active,
                        ),
                      ],
                    ),
                    const SizedBox(height: 2),
                    Text(
                      email,
                      style: GoogleFonts.inter(
                        fontSize: 12,
                        color: theme.colorScheme.onSurface
                            .withValues(alpha: 0.5),
                      ),
                      overflow: TextOverflow.ellipsis,
                    ),
                    if (joinedDate != null || totalCourses != null) ...[
                      const SizedBox(height: 4),
                      Row(
                        children: [
                          if (joinedDate != null) ...[
                            Icon(Icons.calendar_today,
                                size: 12,
                                color: theme.colorScheme.onSurface
                                    .withValues(alpha: 0.35)),
                            const SizedBox(width: 4),
                            Text(
                              _formatDate(joinedDate),
                              style: GoogleFonts.inter(
                                fontSize: 11,
                                color: theme.colorScheme.onSurface
                                    .withValues(alpha: 0.45),
                              ),
                            ),
                            const SizedBox(width: 12),
                          ],
                          if (totalCourses != null) ...[
                            Icon(Icons.menu_book,
                                size: 12,
                                color: theme.colorScheme.onSurface
                                    .withValues(alpha: 0.35)),
                            const SizedBox(width: 4),
                            Text(
                              '$totalCourses courses',
                              style: GoogleFonts.inter(
                                fontSize: 11,
                                color: theme.colorScheme.onSurface
                                    .withValues(alpha: 0.45),
                              ),
                            ),
                          ],
                          const Spacer(),
                          AdminStatusChip(label: status, status: statusEnum),
                        ],
                      ),
                    ],
                  ],
                ),
              ),
              const SizedBox(width: 8),
              Icon(Icons.chevron_right,
                  size: 20,
                  color: theme.colorScheme.onSurface.withValues(alpha: 0.3)),
            ],
          ),
        ),
      ),
    );
  }

  String _formatDate(String iso) {
    try {
      final dt = DateTime.parse(iso);
      return '${dt.day}/${dt.month}/${dt.year}';
    } catch (_) {
      return iso;
    }
  }
}
