import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:sashalms/config/theme.dart';
import 'package:sashalms/config/app_config.dart';
import '../../../features/auth/domain/entities/user.dart';
import '../../../features/auth/presentation/providers/auth_provider.dart';
import '../../../features/courses/presentation/providers/course_filter_providers.dart';
import '../../../features/dashboard/domain/entities/dashboard_data.dart';

// Shared user menu surfaces used by both the Home app bar and the Dashboard
// hero: a profile card (user details + actions) and a notifications panel.
// Keeping them here avoids duplicating the sheets across pages.

// ── Local palette (kept self-contained so callers don't need to share tokens)
const Color _bg = Color(0xFFF4F5F9);
const Color _surface = Color(0xFFFFFFFF);
const Color _border = Color(0x0F101828);
const Color _ink = Color(0xFF101828);
const Color _textSecondary = Color(0xFF667085);
const Color _textTertiary = Color(0xFF98A2B3);
const Color _orange = Color(0xFFEA580C);
const Color _orangeLight = Color(0xFFFFF1E7);
const Color _teal = Color(0xFF0F766E);
const Color _purple = Color(0xFF6D5AE0);
const Color _amber = Color(0xFFB45309);
const Color _green = Color(0xFF3B7A2A);

// ── Notification model ──────────────────────────────────────────────────────
class AppNotification {
  final IconData icon;
  final Color color;
  final String title;
  final String body;
  final String time;
  final bool unread;
  const AppNotification({
    required this.icon,
    required this.color,
    required this.title,
    required this.body,
    required this.time,
    required this.unread,
  });

  /// Stable identity for "clear" tracking. Time is excluded because it is a
  /// relative label ("2h ago") that drifts between rebuilds.
  String get key => '$title|$body';
}

/// Session-scoped set of notification [AppNotification.key]s the user has
/// cleared. Notifications are synthesized from dashboard data on every build,
/// so we suppress the cleared ones here rather than mutating a stored feed.
/// New (differently-keyed) notifications still surface after a clear.
final notificationsClearedProvider =
    StateProvider<Set<String>>((ref) => <String>{});

/// Builds a notification feed from the dashboard data when it's available
/// (course progress, internships, certificates). When [data] is null — e.g.
/// on the Home tab before the dashboard has loaded — a sensible default set
/// is returned so the bell always surfaces something.
List<AppNotification> buildDashboardNotifications(DashboardData? data) {
  if (data == null) return _defaultNotifications;

  final list = <AppNotification>[];

  if (data.stats.certificates > 0) {
    list.add(AppNotification(
      icon: Icons.workspace_premium_rounded,
      color: _purple,
      title: 'Certificate available',
      body: 'You have ${data.stats.certificates} certificate'
          '${data.stats.certificates == 1 ? '' : 's'} ready to download.',
      time: 'Just now',
      unread: true,
    ));
  }

  for (final c in data.enrolledCourses) {
    if (c.progress > 0 && c.progress < 100) {
      list.add(AppNotification(
        icon: Icons.play_circle_fill_rounded,
        color: _orange,
        title: 'Continue ${c.title}',
        body: "You're ${c.progress.round()}% through — resume your next lesson.",
        time: 'Today',
        unread: true,
      ));
    } else if (c.progress >= 100) {
      list.add(AppNotification(
        icon: Icons.check_circle_rounded,
        color: _green,
        title: 'Course completed',
        body: 'You finished ${c.title}. Great work!',
        time: 'This week',
        unread: false,
      ));
    }
  }

  for (final i in data.internships.take(3)) {
    list.add(AppNotification(
      icon: Icons.work_outline_rounded,
      color: _amber,
      title: 'Internship: ${i.title}',
      body: 'Status — ${i.status}.'
          '${(i.hiredCompany != null && i.hiredCompany!.isNotEmpty) ? ' Hired at ${i.hiredCompany}.' : ''}',
      time: 'Pending',
      unread: i.status.toLowerCase() != 'completed',
    ));
  }

  for (final a in data.recentActivity.take(3)) {
    list.add(AppNotification(
      icon: Icons.history_rounded,
      color: _teal,
      title: a.title,
      body: a.description.isNotEmpty ? a.description : a.course,
      time: a.time,
      unread: false,
    ));
  }

  return list.isEmpty ? _defaultNotifications : list;
}

const List<AppNotification> _defaultNotifications = [
  AppNotification(
    icon: Icons.celebration_rounded,
    color: _orange,
    title: 'Welcome to SashaInfinity',
    body: 'Explore AR/VR programs and start your first course today.',
    time: 'Just now',
    unread: true,
  ),
  AppNotification(
    icon: Icons.view_in_ar_rounded,
    color: _purple,
    title: 'New in AR Gallery',
    body: 'Fresh interactive 3D models were just added — take a look.',
    time: 'Today',
    unread: true,
  ),
  AppNotification(
    icon: Icons.menu_book_rounded,
    color: _teal,
    title: 'Latest from the blog',
    body: 'The Future of Spatial Computing in Classrooms is now live.',
    time: 'This week',
    unread: false,
  ),
];

// ── Entry points ────────────────────────────────────────────────────────────
/// Opens the profile card for the currently-authenticated user. No-op when
/// signed out.
Future<void> showUserProfileSheet(BuildContext context, WidgetRef ref) {
  final user = ref.read(authProvider).maybeWhen(
        authenticated: (u) => u,
        orElse: () => null,
      );
  if (user == null) return Future<void>.value();
  return showModalBottomSheet<void>(
    context: context,
    backgroundColor: Colors.transparent,
    isScrollControlled: true,
    builder: (_) => _ProfileCardSheet(user: user),
  );
}

/// Opens the notifications panel with the given [items].
Future<void> showNotificationsSheet(BuildContext context, List<AppNotification> items) {
  return showModalBottomSheet<void>(
    context: context,
    backgroundColor: Colors.transparent,
    isScrollControlled: true,
    builder: (_) => _NotificationsSheet(items: items),
  );
}

// ── Profile card ────────────────────────────────────────────────────────────
class _ProfileCardSheet extends ConsumerWidget {
  final User user;
  const _ProfileCardSheet({required this.user});

  String get _roleLabel {
    switch (user.role) {
      case 'instructor':
        return 'Instructor';
      case 'admin':
        return 'Administrator';
      case 'company':
        return 'Company';
      case 'company_manager':
        return 'Company Manager';
      default:
        return 'Student';
    }
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final initials = user.firstName.isNotEmpty ? user.firstName.substring(0, 1).toUpperCase() : 'U';
    final hasAvatar = user.avatarUrl != null && user.avatarUrl!.isNotEmpty;
    // Resolve the relative /uploads path to an absolute URL for NetworkImage.
    final avatarUrl = hasAvatar
        ? (user.avatarUrl!.startsWith('http')
            ? user.avatarUrl!
            : '${AppConfig.baseUrl}${user.avatarUrl!}')
        : null;

    return SafeArea(
      top: false,
      child: Container(
        margin: const EdgeInsets.all(12),
        padding: const EdgeInsets.fromLTRB(20, 14, 20, 16),
        decoration: BoxDecoration(color: _surface, borderRadius: BorderRadius.circular(24)),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              width: 40,
              height: 4,
              decoration: BoxDecoration(color: const Color(0xFFE4E7EC), borderRadius: BorderRadius.circular(2)),
            ),
            const SizedBox(height: 18),
            Row(
              children: [
                Container(
                  width: 64,
                  height: 64,
                  alignment: Alignment.center,
                  decoration: BoxDecoration(
                    gradient: const LinearGradient(
                      begin: Alignment.topLeft,
                      end: Alignment.bottomRight,
                      colors: [AppTheme.primary, AppTheme.primaryDark],
                    ),
                    shape: BoxShape.circle,
                    image: hasAvatar ? DecorationImage(image: NetworkImage(avatarUrl!), fit: BoxFit.cover) : null,
                  ),
                  child: hasAvatar
                      ? null
                      : Text(initials, style: GoogleFonts.plusJakartaSans(fontSize: 26, fontWeight: FontWeight.w700, color: Colors.white)),
                ),
                const SizedBox(width: 16),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(user.fullName,
                          maxLines: 1, overflow: TextOverflow.ellipsis,
                          style: GoogleFonts.plusJakartaSans(fontSize: 19, fontWeight: FontWeight.w700, color: _ink)),
                      const SizedBox(height: 3),
                      Text(user.email,
                          maxLines: 1, overflow: TextOverflow.ellipsis,
                          style: GoogleFonts.inter(fontSize: 13, color: _textSecondary)),
                      const SizedBox(height: 7),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 3),
                        decoration: BoxDecoration(color: _orangeLight, borderRadius: BorderRadius.circular(20)),
                        child: Text(_roleLabel, style: GoogleFonts.inter(fontSize: 11, fontWeight: FontWeight.w700, color: _orange)),
                      ),
                    ],
                  ),
                ),
              ],
            ),
            if (user.phone != null && user.phone!.isNotEmpty) ...[
              const SizedBox(height: 16),
              _infoRow(Icons.phone_outlined, 'Phone', user.phone!),
            ],
            _infoRow(Icons.verified_user_outlined, 'Account', user.isActive == true ? 'Active' : 'Pending verification'),
            const SizedBox(height: 18),
            _actionTile(
              icon: Icons.person_outline_rounded,
              label: 'View full profile',
              onTap: () {
                final tab = ref.read(scaffoldTabProvider.notifier);
                Navigator.pop(context);
                tab.state = 3;
              },
            ),
            const SizedBox(height: 10),
            _actionTile(
              icon: Icons.edit_outlined,
              label: 'Edit profile',
              onTap: () {
                final tab = ref.read(scaffoldTabProvider.notifier);
                Navigator.pop(context);
                tab.state = 3;
              },
            ),
            const SizedBox(height: 10),
            _actionTile(
              icon: Icons.logout_rounded,
              label: 'Log out',
              danger: true,
              onTap: () {
                // Defer logout until the sheet has detached: logging out rebuilds
                // the whole router stack (it watches authProvider) and tearing it
                // down while this modal is still unmounting trips the framework's
                // `_dependents.isEmpty` assertion.
                final auth = ref.read(authProvider.notifier);
                Navigator.pop(context);
                WidgetsBinding.instance.addPostFrameCallback((_) => auth.logout());
              },
            ),
          ],
        ),
      ),
    );
  }

  Widget _infoRow(IconData icon, String label, String value) => Padding(
        padding: const EdgeInsets.only(top: 10),
        child: Row(
          children: [
            Icon(icon, size: 17, color: _textSecondary),
            const SizedBox(width: 10),
            Text(label, style: GoogleFonts.inter(fontSize: 13, color: _textSecondary)),
            const Spacer(),
            Flexible(
              child: Text(value,
                  maxLines: 1, overflow: TextOverflow.ellipsis,
                  style: GoogleFonts.inter(fontSize: 13, fontWeight: FontWeight.w600, color: _ink)),
            ),
          ],
        ),
      );

  Widget _actionTile({required IconData icon, required String label, required VoidCallback onTap, bool danger = false}) {
    final color = danger ? const Color(0xFFEF4444) : _ink;
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(14),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 13),
        decoration: BoxDecoration(
          color: danger ? const Color(0xFFFEF2F2) : _bg,
          borderRadius: BorderRadius.circular(14),
        ),
        child: Row(
          children: [
            Icon(icon, size: 19, color: color),
            const SizedBox(width: 12),
            Text(label, style: GoogleFonts.inter(fontSize: 14, fontWeight: FontWeight.w600, color: color)),
            const Spacer(),
            if (!danger) Icon(Icons.chevron_right_rounded, size: 18, color: _textTertiary),
          ],
        ),
      ),
    );
  }
}

// ── Notifications panel ─────────────────────────────────────────────────────
class _NotificationsSheet extends ConsumerWidget {
  final List<AppNotification> items;
  const _NotificationsSheet({required this.items});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final cleared = ref.watch(notificationsClearedProvider);
    final visible =
        items.where((n) => !cleared.contains(n.key)).toList(growable: false);
    final unread = visible.where((n) => n.unread).length;
    return SafeArea(
      top: false,
      child: Container(
        margin: const EdgeInsets.all(12),
        constraints: BoxConstraints(maxHeight: MediaQuery.of(context).size.height * 0.7),
        decoration: BoxDecoration(color: _surface, borderRadius: BorderRadius.circular(24)),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const SizedBox(height: 14),
            Container(
              width: 40,
              height: 4,
              decoration: BoxDecoration(color: const Color(0xFFE4E7EC), borderRadius: BorderRadius.circular(2)),
            ),
            Padding(
              padding: const EdgeInsets.fromLTRB(20, 16, 20, 10),
              child: Row(
                children: [
                  Text('Notifications', style: GoogleFonts.plusJakartaSans(fontSize: 19, fontWeight: FontWeight.w700, color: _ink)),
                  const SizedBox(width: 8),
                  if (unread > 0)
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                      decoration: BoxDecoration(color: _orangeLight, borderRadius: BorderRadius.circular(20)),
                      child: Text('$unread new', style: GoogleFonts.inter(fontSize: 11, fontWeight: FontWeight.w700, color: _orange)),
                    ),
                  const Spacer(),
                  if (visible.isNotEmpty)
                    TextButton.icon(
                      onPressed: () {
                        // Suppress every currently-visible notification.
                        ref.read(notificationsClearedProvider.notifier).update(
                              (s) => {...s, ...visible.map((n) => n.key)},
                            );
                      },
                      icon: const Icon(Icons.clear_all_rounded, size: 18),
                      label: const Text('Clear all'),
                      style: TextButton.styleFrom(
                        foregroundColor: _orange,
                        textStyle: GoogleFonts.inter(
                            fontSize: 12.5, fontWeight: FontWeight.w700),
                        padding: const EdgeInsets.symmetric(horizontal: 8),
                        minimumSize: const Size(0, 0),
                        tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                      ),
                    ),
                  const SizedBox(width: 4),
                  GestureDetector(
                    onTap: () => Navigator.pop(context),
                    child: Container(
                      width: 30,
                      height: 30,
                      alignment: Alignment.center,
                      decoration: const BoxDecoration(color: _bg, shape: BoxShape.circle),
                      child: const Icon(Icons.close_rounded, size: 17, color: _textSecondary),
                    ),
                  ),
                ],
              ),
            ),
            if (visible.isEmpty)
              Padding(
                padding: const EdgeInsets.fromLTRB(20, 24, 20, 40),
                child: Column(
                  children: [
                    Icon(Icons.notifications_off_outlined, size: 40, color: _textTertiary),
                    const SizedBox(height: 12),
                    Text("You're all caught up", style: GoogleFonts.inter(fontSize: 14, fontWeight: FontWeight.w600, color: _ink)),
                    const SizedBox(height: 4),
                    Text('No new notifications right now.', style: GoogleFonts.inter(fontSize: 12.5, color: _textSecondary)),
                  ],
                ),
              )
            else
              Flexible(
                child: ListView.separated(
                  shrinkWrap: true,
                  padding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
                  physics: const BouncingScrollPhysics(),
                  itemCount: visible.length,
                  separatorBuilder: (_, __) => Divider(height: 1, color: _border.withOpacity(0.6), indent: 60),
                  itemBuilder: (_, i) => _NotificationTile(item: visible[i]),
                ),
              ),
          ],
        ),
      ),
    );
  }
}

class _NotificationTile extends StatelessWidget {
  final AppNotification item;
  const _NotificationTile({required this.item});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 12),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: 40,
            height: 40,
            decoration: BoxDecoration(color: item.color.withOpacity(0.12), shape: BoxShape.circle),
            child: Icon(item.icon, size: 19, color: item.color),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Expanded(
                      child: Text(item.title,
                          maxLines: 1, overflow: TextOverflow.ellipsis,
                          style: GoogleFonts.inter(fontSize: 13.5, fontWeight: FontWeight.w700, color: _ink)),
                    ),
                    if (item.unread) ...[
                      const SizedBox(width: 6),
                      Container(width: 8, height: 8, decoration: const BoxDecoration(color: _orange, shape: BoxShape.circle)),
                    ],
                  ],
                ),
                const SizedBox(height: 3),
                Text(item.body, style: GoogleFonts.inter(fontSize: 12, color: _textSecondary, height: 1.35)),
                const SizedBox(height: 4),
                Text(item.time, style: GoogleFonts.inter(fontSize: 11, color: _textTertiary)),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
