// lib/features/profile/presentation/pages/settings_page.dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:url_launcher/url_launcher.dart';
import 'package:sashalms/config/theme.dart';
import 'package:sashalms/config/design_tokens.dart';
import 'package:sashalms/config/theme_mode_provider.dart';
import 'package:sashalms/core/constants/storage_keys.dart';
import 'package:sashalms/core/storage/prefs_storage.dart';
import 'package:sashalms/shared/widgets/common/app_snackbar.dart';
import 'package:sashalms/features/about/presentation/pages/about_page.dart';
import '../../../auth/presentation/providers/auth_provider.dart';
import '../../../auth/presentation/providers/password_reset_provider.dart';

/// Keep in sync with `version:` in pubspec.yaml (currently 1.0.0+1).
const String kAppVersion = '1.0.0 (build 1)';

/// A small description of a persisted on/off setting.
class _Toggle {
  final String key;
  final String label;
  final bool defaultValue;
  const _Toggle(this.key, this.label, this.defaultValue);
}

class SettingsPage extends ConsumerStatefulWidget {
  const SettingsPage({super.key});

  @override
  ConsumerState<SettingsPage> createState() => _SettingsPageState();
}

class _SettingsPageState extends ConsumerState<SettingsPage> {
  static const List<_Toggle> _notifToggles = [
    _Toggle('set_notif_email', 'Email notifications', true),
    _Toggle('set_notif_push', 'Push notifications', true),
    _Toggle('set_notif_course', 'Course updates', true),
    _Toggle('set_notif_promo', 'Promotions & offers', false),
  ];
  static const List<_Toggle> _privacyToggles = [
    _Toggle('set_priv_public', 'Show profile publicly', true),
    _Toggle('set_priv_email', 'Show email on profile', false),
    _Toggle('set_priv_activity', 'Show activity status', true),
  ];

  final PrefsStorage _prefs = PrefsStorage();
  Map<String, bool> _values = {};
  bool _loaded = false;

  @override
  void initState() {
    super.initState();
    _loadToggles();
  }

  Future<void> _loadToggles() async {
    final map = <String, bool>{};
    for (final t in [..._notifToggles, ..._privacyToggles]) {
      map[t.key] = (await _prefs.readBool(t.key)) ?? t.defaultValue;
    }
    if (mounted) {
      setState(() {
        _values = map;
        _loaded = true;
      });
    }
  }

  Future<void> _setToggle(String key, bool value) async {
    setState(() => _values[key] = value);
    await _prefs.writeBool(key, value);
  }

  // ----- Actions ------------------------------------------------------------

  Future<void> _resetPassword() async {
    final email = ref.read(authProvider).maybeWhen(
          authenticated: (u) => u.email,
          orElse: () => '',
        );
    if (email.isEmpty) {
      AppSnackbar.error(context, 'No email on file for this account.');
      return;
    }
    final ok = await showDialog<bool>(
      context: context,
      builder: (c) => AlertDialog(
        title: const Text('Reset password by email?'),
        content: Text('We will send a password reset link to $email.'),
        actions: [
          TextButton(
              onPressed: () => Navigator.pop(c, false),
              child: const Text('Cancel')),
          FilledButton(
              onPressed: () => Navigator.pop(c, true),
              child: const Text('Send')),
        ],
      ),
    );
    if (ok != true || !mounted) return;
    final sent =
        await ref.read(passwordResetProvider.notifier).sendForgotEmail(email);
    if (!mounted) return;
    if (sent) {
      AppSnackbar.success(
          context,
          'Password reset link sent to $email. Open it from your inbox '
          '(check spam) to set a new password.');
    } else {
      AppSnackbar.error(context, 'Could not send the reset email. Try again.');
    }
  }

  Future<void> _signOut() async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (c) => AlertDialog(
        title: const Text('Sign out?'),
        content: const Text(
            'You will need to sign in again to access your courses.'),
        actions: [
          TextButton(
              onPressed: () => Navigator.pop(c, false),
              child: const Text('Cancel')),
          FilledButton(
              onPressed: () => Navigator.pop(c, true),
              child: const Text('Sign Out')),
        ],
      ),
    );
    if (confirmed != true || !mounted) return;
    // Pop settings first; the router redirect then takes over to /login.
    if (Navigator.canPop(context)) Navigator.pop(context);
    await ref.read(authProvider.notifier).logout();
  }

  Future<void> _clearCache() async {
    await _prefs.delete(StorageKeys.coursesCacheTimestamp);
    await _prefs.delete(StorageKeys.profileCacheTimestamp);
    if (mounted) AppSnackbar.success(context, 'Cache cleared.');
  }

  void _showLanguageInfo() {
    showDialog<void>(
      context: context,
      builder: (c) => AlertDialog(
        title: const Text('Language'),
        content: const Text(
            'English is currently the default language. More languages are '
            'coming soon.'),
        actions: [
          TextButton(
              onPressed: () => Navigator.pop(c), child: const Text('OK')),
        ],
      ),
    );
  }

  Future<void> _openSupport() async {
    final emailUri = Uri(
      scheme: 'mailto',
      path: 'support@sashainfinity.com',
      queryParameters: {'subject': 'SashaInfinity Support'},
    );
    if (await canLaunchUrl(emailUri)) {
      await launchUrl(emailUri);
    } else if (mounted) {
      AppSnackbar.info(context, 'Email us at support@sashainfinity.com');
    }
  }

  void _openAbout() {
    Navigator.push(
      context,
      MaterialPageRoute(builder: (_) => const AboutPage()),
    );
  }

  Future<void> _setTheme(ThemeMode mode) =>
      ref.read(themeModeProvider.notifier).setThemeMode(mode);

  // ----- Build --------------------------------------------------------------

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final themeMode = ref.watch(themeModeProvider);

    return Scaffold(
      backgroundColor: theme.colorScheme.surface,
      body: Column(
        children: [
          _buildHeader(theme),
          Expanded(
            child: Container(
              width: double.infinity,
              decoration: BoxDecoration(
                color: theme.colorScheme.surface,
                borderRadius:
                    const BorderRadius.vertical(top: Radius.circular(28)),
              ),
              transform: Matrix4.translationValues(0, -24, 0),
              clipBehavior: Clip.antiAlias,
              child: ListView(
                padding: const EdgeInsets.fromLTRB(20, 16, 20, 32),
                children: [
                  // Appearance
                  _group('Appearance', [
                    _choiceTile('System default', Icons.brightness_auto_outlined,
                        themeMode == ThemeMode.system,
                        () => _setTheme(ThemeMode.system)),
                    _divider(),
                    _choiceTile('Light', Icons.light_mode_outlined,
                        themeMode == ThemeMode.light,
                        () => _setTheme(ThemeMode.light)),
                    _divider(),
                    _choiceTile('Dark', Icons.dark_mode_outlined,
                        themeMode == ThemeMode.dark,
                        () => _setTheme(ThemeMode.dark)),
                  ]),
                  const SizedBox(height: 16),

                  // Notifications
                  _group('Notifications', _toggleTiles(_notifToggles)),
                  const SizedBox(height: 16),

                  // Privacy
                  _group('Privacy', _toggleTiles(_privacyToggles)),
                  const SizedBox(height: 16),

                  // Account
                  _group('Account preferences', [
                    _navTile('Reset password via email',
                        Icons.mark_email_read_outlined, _resetPassword),
                    _divider(),
                    _navTile('Sign out', Icons.logout_outlined, _signOut,
                        danger: true),
                  ]),
                  const SizedBox(height: 16),

                  // General
                  _group('General', [
                    _navTile('Language', Icons.translate_outlined,
                        _showLanguageInfo,
                        trailingText: 'English'),
                    _divider(),
                    _navTile('Clear cache', Icons.cached_outlined, _clearCache),
                    _divider(),
                    _navTile('Help & Support',
                        Icons.contact_support_outlined, _openSupport),
                    _divider(),
                    _navTile('About SashaInfinity', Icons.info_outline,
                        _openAbout),
                  ]),
                  const SizedBox(height: 16),

                  // About / version
                  _buildAbout(theme),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  List<Widget> _toggleTiles(List<_Toggle> toggles) {
    final tiles = <Widget>[];
    for (var i = 0; i < toggles.length; i++) {
      final t = toggles[i];
      tiles.add(
        SwitchListTile(
          value: _values[t.key] ?? t.defaultValue,
          onChanged: _loaded ? (v) => _setToggle(t.key, v) : null,
          activeColor: AppTheme.primary,
          contentPadding: const EdgeInsets.symmetric(horizontal: 16),
          visualDensity: VisualDensity.compact,
          title: Text(t.label),
        ),
      );
      if (i != toggles.length - 1) tiles.add(_divider());
    }
    return tiles;
  }

  Widget _buildHeader(ThemeData theme) {
    return Container(
      width: double.infinity,
      decoration: const BoxDecoration(
        gradient: AppGradients.primary,
        borderRadius: BorderRadius.vertical(bottom: Radius.circular(AppRadius.banner)),
      ),
      child: SafeArea(
        bottom: false,
        child: Padding(
          padding: const EdgeInsets.fromLTRB(8, 4, 24, 28),
          child: Row(
            children: [
              IconButton(
                onPressed: () => Navigator.maybePop(context),
                icon: const Icon(Icons.arrow_back, color: Colors.white),
                tooltip: 'Back',
              ),
              const SizedBox(width: 4),
              Text(
                'Settings',
                style: theme.textTheme.titleLarge?.copyWith(
                  color: Colors.white,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildAbout(ThemeData theme) {
    return Column(
      children: [
        Container(
          width: 44,
          height: 44,
          decoration: BoxDecoration(
            color: AppTheme.primary.withValues(alpha: 0.1),
            borderRadius: BorderRadius.circular(14),
          ),
          child: const Icon(Icons.school_outlined,
              color: AppTheme.primary, size: 22),
        ),
        const SizedBox(height: 10),
        Text(
          'SashaInfinity LMS',
          style: GoogleFonts.plusJakartaSans(
            fontWeight: FontWeight.bold,
            fontSize: 16,
          ),
        ),
        const SizedBox(height: 2),
        Text(
          'Version $kAppVersion',
          style: theme.textTheme.bodySmall?.copyWith(
            color: theme.colorScheme.onSurface.withValues(alpha: 0.6),
          ),
        ),
        const SizedBox(height: 2),
        Text(
          '© 2026 SashaInfinity. All rights reserved.',
          style: theme.textTheme.labelSmall?.copyWith(
            color: theme.colorScheme.onSurface.withValues(alpha: 0.45),
          ),
        ),
      ],
    );
  }

  // ----- Reusable pieces ----------------------------------------------------

  Widget _group(String title, List<Widget> children) {
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.only(left: 4, bottom: 8),
          child: Row(
            children: [
              Container(
                width: 4,
                height: 20,
                decoration: BoxDecoration(
                  color: AppTheme.primary,
                  borderRadius: BorderRadius.circular(999),
                ),
              ),
              const SizedBox(width: 12),
              Text(
                title,
                style: GoogleFonts.plusJakartaSans(
                  fontWeight: FontWeight.w700,
                  fontSize: 15,
                  letterSpacing: -0.3,
                ),
              ),
            ],
          ),
        ),
        Container(
          decoration: BoxDecoration(
            color: isDark ? AppTheme.surfaceDark : Colors.white,
            borderRadius: BorderRadius.circular(AppRadius.lg),
            border: Border.all(
              color: isDark ? AppTheme.borderDark : AppTheme.borderLight,
            ),
            boxShadow: isDark ? null : AppShadows.soft,
          ),
          clipBehavior: Clip.antiAlias,
          child: Column(children: children),
        ),
      ],
    );
  }

  Widget _divider() {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    // Soft gray hairline between options (replaces the default dark divider).
    return Divider(
      height: 1,
      thickness: 1,
      indent: 16,
      endIndent: 16,
      color: isDark ? const Color(0xFF334155) : const Color(0xFFE2E8F0),
    );
  }

  Widget _choiceTile(
      String label, IconData icon, bool selected, VoidCallback onTap) {
    return ListTile(
      visualDensity: VisualDensity.compact,
      leading: Icon(icon, color: AppTheme.primary),
      title: Text(label),
      trailing: selected
          ? const Icon(Icons.check_circle, color: AppTheme.primary)
          : const Icon(Icons.radio_button_unchecked, color: Colors.grey),
      onTap: onTap,
    );
  }

  Widget _navTile(String title, IconData icon, VoidCallback onTap,
      {String? trailingText, bool danger = false}) {
    final color = danger ? AppTheme.danger : null;
    return ListTile(
      visualDensity: VisualDensity.compact,
      leading: Icon(icon, color: danger ? AppTheme.danger : AppTheme.primary),
      title: Text(title, style: color != null ? TextStyle(color: color) : null),
      trailing: trailingText != null
          ? Text(trailingText, style: const TextStyle(color: Colors.grey))
          : const Icon(Icons.chevron_right, color: Colors.grey),
      onTap: onTap,
    );
  }
}
