import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:intl/intl.dart';
import 'package:url_launcher/url_launcher.dart';
import 'package:cached_network_image/cached_network_image.dart';
import 'package:sashalms/config/app_config.dart';
import 'package:sashalms/config/theme.dart';
import 'package:sashalms/config/design_tokens.dart';
import 'package:sashalms/core/network/network_provider.dart';
import 'package:sashalms/shared/widgets/common/app_loader.dart';
import 'package:sashalms/shared/widgets/common/error_display.dart';

/// Fetches a user's public profile by username from
/// `GET /api/v1/users/public/{username}` (unauthenticated, read-only).
final publicProfileProvider =
    FutureProvider.family<Map<String, dynamic>, String>((ref, username) async {
  final client = ref.watch(apiClientProvider);
  final response = await client.get('/api/v1/users/public/$username');
  if (response.statusCode == 200) {
    return response.data as Map<String, dynamic>;
  }
  throw Exception('Profile not found');
});

/// Read-only public profile, reachable at `/u/<username>`. Mirrors the web
/// public-profile page: cover banner, avatar, identity, stats and social links.
class PublicProfilePage extends ConsumerWidget {
  final String username;
  const PublicProfilePage({super.key, required this.username});

  /// Resolves a backend-relative path (e.g. `/uploads/...`) to an absolute URL.
  String _resolve(String raw) {
    final url = raw.trim();
    if (url.isEmpty || url.startsWith('http')) return url;
    final separator = url.startsWith('/') ? '' : '/';
    return '${AppConfig.baseUrl}$separator$url';
  }

  String _formatDate(String raw) {
    if (raw.isEmpty) return '';
    final parsed = DateTime.tryParse(raw);
    if (parsed == null) return raw;
    return DateFormat('MMMM y').format(parsed.toLocal());
  }

  String _roleLabel(String role) {
    switch (role.toLowerCase()) {
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
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;
    final async = ref.watch(publicProfileProvider(username));

    return Scaffold(
      backgroundColor: isDark ? theme.colorScheme.surface : AppNeutrals.slate50,
      extendBodyBehindAppBar: true,
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        elevation: 0,
        foregroundColor: Colors.white,
        systemOverlayStyle: SystemUiOverlayStyle.light,
        leading: IconButton(
          icon: const Icon(Icons.arrow_back_rounded),
          onPressed: () {
            if (Navigator.of(context).canPop()) {
              Navigator.of(context).pop();
            } else {
              context.go('/');
            }
          },
        ),
      ),
      body: async.when(
        data: (data) => _buildContent(context, data, theme, isDark),
        loading: () => const BrandedLoader(),
        error: (e, _) => SafeArea(
          child: ErrorDisplay(
            message: "We couldn't find this profile.",
            onRetry: () => ref.refresh(publicProfileProvider(username)),
          ),
        ),
      ),
    );
  }

  Widget _buildContent(BuildContext context, Map<String, dynamic> data, ThemeData theme, bool isDark) {
    final cover = _resolve((data['cover_photo'] ?? '').toString());
    final photo = _resolve((data['profile_photo'] ?? '').toString());
    final displayName =
        (data['display_name'] ?? 'SashaInfinity Member').toString().trim();
    final uname = (data['username'] ?? username).toString().trim();
    final role = _roleLabel((data['role'] ?? 'student').toString());
    final designation = (data['designation'] ?? '').toString().trim();
    final bio = (data['bio'] ?? '').toString().trim();
    final location = (data['location'] ?? '').toString().trim();
    final joined = _formatDate((data['joined_date'] ?? '').toString());
    final social = (data['social_links'] as Map?) ?? const {};
    final stats = (data['stats'] as Map?) ?? const {};

    final topPad = MediaQuery.of(context).padding.top;

    return SingleChildScrollView(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          _buildCoverHeader(
            cover: cover,
            photo: photo,
            displayName: displayName,
            uname: uname,
            role: role,
            location: location,
            topPad: topPad,
          ),
          Transform.translate(
            offset: const Offset(0, -28),
            child: Container(
              decoration: BoxDecoration(
                color: isDark ? theme.colorScheme.surface : AppNeutrals.slate50,
                borderRadius:
                    const BorderRadius.vertical(top: Radius.circular(AppRadius.card)),
              ),
              padding: const EdgeInsets.fromLTRB(20, 22, 20, 36),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  if (designation.isNotEmpty) ...[
                    Text(designation,
                        style: GoogleFonts.plusJakartaSans(
                            fontSize: 15.5,
                            fontWeight: FontWeight.w600,
                            color: AppTheme.primary)),
                    const SizedBox(height: 14),
                  ],
                  _buildStats(stats, isDark, theme),
                  if (bio.isNotEmpty) ...[
                    const SizedBox(height: 22),
                    _sectionLabel('About'),
                    const SizedBox(height: 8),
                    Text(bio,
                        style: GoogleFonts.inter(
                            fontSize: 14.5,
                            height: 1.6,
                            color: theme.colorScheme.onSurface
                                .withValues(alpha: 0.82))),
                  ],
                  if (joined.isNotEmpty) ...[
                    const SizedBox(height: 18),
                    Row(
                      children: [
                        Icon(Icons.calendar_month_outlined,
                            size: 16,
                            color: theme.colorScheme.onSurface
                                .withValues(alpha: 0.5)),
                        const SizedBox(width: 6),
                        Text('Joined $joined',
                            style: GoogleFonts.inter(
                                fontSize: 12.5,
                                color: theme.colorScheme.onSurface
                                    .withValues(alpha: 0.55))),
                      ],
                    ),
                  ],
                  if (_hasSocial(social)) ...[
                    const SizedBox(height: 22),
                    _sectionLabel('Connect'),
                    const SizedBox(height: 12),
                    _buildSocial(context, social),
                  ],
                  const SizedBox(height: 28),
                  // Shareable link back to the public profile (web).
                  OutlinedButton.icon(
                    onPressed: () =>
                        _copyLink(context, uname),
                    icon: const Icon(Icons.link_rounded, size: 18),
                    label: const Text('Copy profile link'),
                    style: OutlinedButton.styleFrom(
                      foregroundColor: AppTheme.primary,
                      side: const BorderSide(color: AppTheme.primary),
                      padding: const EdgeInsets.symmetric(vertical: 14),
                      shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(AppRadius.md)),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  bool _hasSocial(Map social) {
    for (final k in ['website', 'facebook', 'twitter', 'linkedin']) {
      if ((social[k] ?? '').toString().trim().isNotEmpty) return true;
    }
    return false;
  }

  Widget _buildCoverHeader({
    required String cover,
    required String photo,
    required String displayName,
    required String uname,
    required String role,
    required String location,
    required double topPad,
  }) {
    const coverHeight = 320.0;
    return SizedBox(
      height: coverHeight,
      child: Stack(
        fit: StackFit.expand,
        children: [
          if (cover.isNotEmpty)
            Image(
              image: NetworkImage(cover),
              fit: BoxFit.cover,
              errorBuilder: (_, __, ___) =>
                  Container(decoration: const BoxDecoration(gradient: AppGradients.primary)),
            )
          else
            Container(decoration: const BoxDecoration(gradient: AppGradients.primary)),
          const DecoratedBox(
            decoration: BoxDecoration(
              gradient: LinearGradient(
                begin: Alignment.topCenter,
                end: Alignment.bottomCenter,
                colors: [
                  Color(0x55000000),
                  Color(0x00000000),
                  Color(0x00000000),
                  Color(0xCC000000),
                ],
                stops: [0.0, 0.30, 0.55, 1.0],
              ),
            ),
          ),
          Padding(
            padding: EdgeInsets.fromLTRB(20, topPad + 12, 20, 24),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Spacer(),
                // Avatar
                Container(
                  width: 92,
                  height: 92,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    border: Border.all(color: Colors.white, width: 3),
                    color: Colors.white,
                  ),
                  clipBehavior: Clip.antiAlias,
                  child: photo.isNotEmpty
                      ? CachedNetworkImage(
                          imageUrl: photo,
                          fit: BoxFit.cover,
                          placeholder: (context, url) => const Center(
                            child: SizedBox(
                              width: 24,
                              height: 24,
                              child: CircularProgressIndicator(
                                strokeWidth: 2.0,
                                valueColor: AlwaysStoppedAnimation(AppTheme.primary),
                              ),
                            ),
                          ),
                          errorWidget: (context, url, error) => Image.asset(
                            'assets/images/sasha-logo.png',
                            fit: BoxFit.contain,
                          ),
                        )
                      : Image.asset(
                          'assets/images/sasha-logo.png',
                          fit: BoxFit.contain,
                        ),
                ),
                const SizedBox(height: 14),
                Text(displayName,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: GoogleFonts.plusJakartaSans(
                        color: Colors.white,
                        fontSize: 28,
                        fontWeight: FontWeight.w800,
                        letterSpacing: -0.5)),
                const SizedBox(height: 3),
                Text('@$uname',
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: GoogleFonts.inter(
                        color: Colors.white.withValues(alpha: 0.85), fontSize: 14)),
                const SizedBox(height: 12),
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: [
                    _pill(role.toUpperCase()),
                    if (location.isNotEmpty) _pill(location, icon: Icons.place_outlined),
                  ],
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _pill(String text, {IconData? icon}) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
      decoration: BoxDecoration(
        color: Colors.black.withValues(alpha: 0.30),
        borderRadius: BorderRadius.circular(AppRadius.pill),
        border: Border.all(color: Colors.white.withValues(alpha: 0.45)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          if (icon != null) ...[
            Icon(icon, color: Colors.white, size: 13),
            const SizedBox(width: 4),
          ],
          Text(text,
              style: GoogleFonts.inter(
                  color: Colors.white,
                  fontSize: 11,
                  fontWeight: FontWeight.w700,
                  letterSpacing: 0.4)),
        ],
      ),
    );
  }

  Widget _sectionLabel(String text) => Row(
        children: [
          Container(
              width: 4,
              height: 18,
              decoration: BoxDecoration(
                  color: AppTheme.primary, borderRadius: BorderRadius.circular(999))),
          const SizedBox(width: 10),
          Text(text,
              style: GoogleFonts.plusJakartaSans(
                  fontSize: 16, fontWeight: FontWeight.w700)),
        ],
      );

  Widget _buildStats(Map stats, bool isDark, ThemeData theme) {
    final tiles = <_PStat>[];
    final courses = stats['courses'];
    if (courses is num) {
      tiles.add(_PStat(Icons.menu_book_outlined, '$courses', 'Courses', AppTheme.primary));
    }
    final students = stats['students'];
    if (students is num) {
      tiles.add(_PStat(Icons.people_alt_outlined, '$students', 'Students',
          const Color(0xFF3B82F6)));
    }
    final rating = stats['rating'];
    if (rating is num) {
      tiles.add(_PStat(Icons.star_rounded, rating.toStringAsFixed(1), 'Rating',
          const Color(0xFFF59E0B)));
    }
    if (tiles.isEmpty) return const SizedBox.shrink();

    return Row(
      children: [
        for (var i = 0; i < tiles.length; i++) ...[
          Expanded(child: _statTile(tiles[i], isDark, theme)),
          if (i != tiles.length - 1) const SizedBox(width: 12),
        ],
      ],
    );
  }

  Widget _statTile(_PStat s, bool isDark, ThemeData theme) {
    return Container(
      padding: const EdgeInsets.symmetric(vertical: 16, horizontal: 8),
      decoration: BoxDecoration(
        color: isDark ? AppTheme.surfaceDark : Colors.white,
        borderRadius: BorderRadius.circular(AppRadius.lg),
        border: Border.all(color: isDark ? AppTheme.borderDark : AppTheme.borderLight),
        boxShadow: isDark ? null : AppShadows.soft,
      ),
      child: Column(
        children: [
          Icon(s.icon, color: s.color, size: 24),
          const SizedBox(height: 8),
          Text(s.value,
              style: GoogleFonts.plusJakartaSans(
                  fontWeight: FontWeight.w800,
                  fontSize: 20,
                  color: isDark ? AppTheme.textDark : AppNeutrals.slate900)),
          const SizedBox(height: 2),
          Text(s.label,
              textAlign: TextAlign.center,
              style: GoogleFonts.inter(
                  fontSize: 12,
                  color: isDark ? AppTheme.mutedDark : AppTheme.mutedLight)),
        ],
      ),
    );
  }

  Widget _buildSocial(BuildContext context, Map social) {
    final items = <_SocialEntry>[];
    void add(String key, String label, IconData icon, Color color) {
      final v = (social[key] ?? '').toString().trim();
      if (v.isNotEmpty) items.add(_SocialEntry(label, icon, color, v));
    }

    add('website', 'Website', Icons.language_rounded, const Color(0xFF0EA5E9));
    add('facebook', 'Facebook', Icons.facebook, const Color(0xFF1877F2));
    add('twitter', 'Twitter', Icons.alternate_email, const Color(0xFF1DA1F2));
    add('linkedin', 'LinkedIn', Icons.business_rounded, const Color(0xFF0A66C2));

    return Wrap(
      spacing: 12,
      runSpacing: 12,
      children: items
          .map((e) => GestureDetector(
                onTap: () => _openLink(context, e.url),
                child: Container(
                  width: 56,
                  height: 56,
                  decoration: BoxDecoration(
                    color: e.color.withValues(alpha: 0.14),
                    shape: BoxShape.circle,
                    border: Border.all(color: e.color.withValues(alpha: 0.55), width: 1.5),
                  ),
                  child: Icon(e.icon, color: e.color, size: 24),
                ),
              ))
          .toList(),
    );
  }

  Future<void> _openLink(BuildContext context, String raw) async {
    var url = raw.trim();
    if (url.isEmpty) return;
    if (!url.startsWith('http://') && !url.startsWith('https://')) {
      url = 'https://$url';
    }
    final uri = Uri.tryParse(url);
    if (uri != null && await canLaunchUrl(uri)) {
      await launchUrl(uri, mode: LaunchMode.externalApplication);
    }
  }

  Future<void> _copyLink(BuildContext context, String uname) async {
    final link = 'https://sashainfinity.com/u/$uname';
    await Clipboard.setData(ClipboardData(text: link));
    if (context.mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Profile link copied to clipboard.')),
      );
    }
  }
}

class _PStat {
  final IconData icon;
  final String value;
  final String label;
  final Color color;
  const _PStat(this.icon, this.value, this.label, this.color);
}

class _SocialEntry {
  final String label;
  final IconData icon;
  final Color color;
  final String url;
  const _SocialEntry(this.label, this.icon, this.color, this.url);
}
