import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:image_picker/image_picker.dart';
import 'package:image_cropper/image_cropper.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:share_plus/share_plus.dart';
import 'package:sashalms/config/app_config.dart';
import 'package:sashalms/config/theme.dart';
import 'package:sashalms/config/design_tokens.dart';
import 'package:sashalms/features/about/presentation/pages/about_page.dart';
import 'package:sashalms/shared/widgets/common/app_loader.dart';
import 'package:sashalms/shared/widgets/common/error_display.dart';
import 'package:url_launcher/url_launcher.dart';
import 'package:sashalms/core/constants/api_endpoints.dart';
import 'package:sashalms/core/errors/exceptions.dart';
import 'package:sashalms/core/network/network_provider.dart';
import 'package:sashalms/shared/widgets/common/app_snackbar.dart';
import '../../../auth/presentation/providers/auth_provider.dart';
import '../../../auth/presentation/providers/auth_state.dart';
import '../../../auth/presentation/utils/auth_error_text.dart';
import '../../../dashboard/presentation/providers/dashboard_provider.dart';
import '../providers/profile_provider.dart';
import 'settings_page.dart';

/// Backend password rule: 8+ chars with upper, lower, and a digit.
final _passwordRule = RegExp(r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).{8,}$');

class ProfilePage extends ConsumerStatefulWidget {
  const ProfilePage({super.key});

  @override
  ConsumerState<ProfilePage> createState() => _ProfilePageState();
}

class _ProfilePageState extends ConsumerState<ProfilePage> {
  bool _isSaving = false;
  Map<String, dynamic>? _loadedProfile;
  // Bumped on every successful avatar upload so the displayed photo URL changes
  // (cache-bust), forcing Flutter's ImageCache to fetch the new bytes.
  int _avatarVersion = 0;

  // Controllers
  final _firstNameController = TextEditingController();
  final _lastNameController = TextEditingController();
  final _phoneController = TextEditingController();
  final _dobController = TextEditingController();
  final _designationController = TextEditingController();
  final _bioController = TextEditingController();

  final _addressController = TextEditingController();
  final _cityController = TextEditingController();
  final _stateController = TextEditingController();
  final _countryController = TextEditingController();
  final _postalCodeController = TextEditingController();

  final _websiteController = TextEditingController();
  final _facebookController = TextEditingController();
  final _instagramController = TextEditingController();
  final _twitterController = TextEditingController();
  final _linkedinController = TextEditingController();
  final _youtubeController = TextEditingController();

  @override
  void dispose() {
    _firstNameController.dispose();
    _lastNameController.dispose();
    _phoneController.dispose();
    _dobController.dispose();
    _designationController.dispose();
    _bioController.dispose();
    _addressController.dispose();
    _cityController.dispose();
    _stateController.dispose();
    _countryController.dispose();
    _postalCodeController.dispose();
    _websiteController.dispose();
    _facebookController.dispose();
    _instagramController.dispose();
    _twitterController.dispose();
    _linkedinController.dispose();
    _youtubeController.dispose();
    super.dispose();
  }

  void _populateFields(Map<String, dynamic> data) {
    _loadedProfile = data;
    _firstNameController.text = data['first_name'] ?? '';
    _lastNameController.text = data['last_name'] ?? '';
    _phoneController.text = data['phone'] ?? '';
    // Date of birth has no backend column yet — keep whatever the user typed
    // this session so the field doesn't clear on refresh.
    _dobController.text = data['date_of_birth'] ?? _dobController.text;
    _designationController.text = data['designation'] ?? '';
    _bioController.text = data['description'] ?? '';

    _addressController.text = data['address'] ?? '';
    _cityController.text = data['city'] ?? '';
    _stateController.text = data['state'] ?? '';
    _countryController.text = data['country'] ?? '';
    _postalCodeController.text = data['postal_code'] ?? '';

    _websiteController.text = data['website'] ?? '';
    _facebookController.text = data['facebook'] ?? '';
    _twitterController.text = data['twitter'] ?? '';
    _linkedinController.text = data['linkedin'] ?? '';
    // Mock values for items not stored in database schemas
    _instagramController.text = data['instagram'] ?? '';
    _youtubeController.text = data['youtube'] ?? '';
  }

  Future<void> _pickAndUploadAvatar() async {
    // Let the user choose where the new photo comes from.
    final source = await showModalBottomSheet<ImageSource>(
      context: context,
      showDragHandle: true,
      builder: (ctx) => SafeArea(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(20, 4, 20, 8),
              child: Align(
                alignment: Alignment.centerLeft,
                child: Text('Update profile photo',
                    style: GoogleFonts.plusJakartaSans(
                        fontSize: 17, fontWeight: FontWeight.w600)),
              ),
            ),
            ListTile(
              leading: const Icon(Icons.photo_camera_outlined),
              title: const Text('Take a photo'),
              onTap: () => Navigator.pop(ctx, ImageSource.camera),
            ),
            ListTile(
              leading: const Icon(Icons.photo_library_outlined),
              title: const Text('Choose from gallery'),
              onTap: () => Navigator.pop(ctx, ImageSource.gallery),
            ),
            const SizedBox(height: 8),
          ],
        ),
      ),
    );
    if (source == null) return;

    // Camera capture needs a runtime permission; the gallery uses the OS photo
    // picker, which needs none.
    if (!await _ensureCameraPermission(source)) return;

    final picker = ImagePicker();
    try {
      final pickedFile = await picker.pickImage(
        source: source,
        imageQuality: 92,
        maxWidth: 1600,
      );

      if (pickedFile == null) return;

      // Let the user crop / zoom to a square before uploading — gives a clean,
      // consistent avatar instead of an arbitrarily-framed photo.
      final cropped = await ImageCropper().cropImage(
        sourcePath: pickedFile.path,
        aspectRatio: const CropAspectRatio(ratioX: 1, ratioY: 1),
        compressQuality: 85,
        uiSettings: [
          AndroidUiSettings(
            toolbarTitle: 'Crop photo',
            toolbarColor: AppTheme.primary,
            toolbarWidgetColor: Colors.white,
            activeControlsWidgetColor: AppTheme.primary,
            lockAspectRatio: true,
            hideBottomControls: false,
          ),
          IOSUiSettings(
            title: 'Crop photo',
            aspectRatioLockEnabled: true,
            resetAspectRatioEnabled: false,
          ),
        ],
      );
      // User backed out of the crop screen — abort the whole flow.
      if (cropped == null) return;

      setState(() {
        _isSaving = true;
      });

      // Read the cropped bytes (CroppedFile.readAsBytes works on web + native);
      // the cropper always emits JPEG, so upload it as avatar.jpg.
      final bytes = await cropped.readAsBytes();
      final repository = ref.read(profileRepositoryProvider);
      final result = await repository.uploadAvatar(bytes, 'avatar.jpg');

      if (!mounted) return;

      result.fold(
        (failure) {
          AppSnackbar.error(context, 'Photo upload failed: ${failure.toString()}');
        },
        (photoUrl) {
          // The backend returns a NEW unique path for each upload, so drop every
          // cached copy of the old bytes, bump the version token (so the hero
          // fetches fresh), refresh the profile data, and push the new photo URL
          // into the auth user so the Home app bar and user-menu avatar rebuild
          // with it too. (`/auth/me` doesn't return the photo, so a plain
          // checkAuthStatus() would keep showing the stale avatar.)
          _evictAvatar(photoUrl);
          setState(() => _avatarVersion++);
          ref.invalidate(profileFutureProvider);
          ref.read(authProvider.notifier).updateAvatarUrl(photoUrl);
          AppSnackbar.success(context, 'Profile photo updated!');
        },
      );
    } catch (e) {
      if (mounted) AppSnackbar.error(context, 'Error selecting photo: $e');
    } finally {
      if (mounted) {
        setState(() {
          _isSaving = false;
        });
      }
    }
  }

  /// Ensures the CAMERA permission for camera capture, surfacing a Settings
  /// prompt when it's permanently denied. The gallery needs no runtime grant
  /// (it uses the system photo picker). Returns whether picking may proceed.
  Future<bool> _ensureCameraPermission(ImageSource source) async {
    if (source == ImageSource.gallery) return true;

    var status = await Permission.camera.status;
    if (status.isGranted) return true;
    status = await Permission.camera.request();
    if (status.isGranted) return true;

    if (!mounted) return false;
    if (status.isPermanentlyDenied) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: const Text(
              'Camera permission is off. Enable it in Settings to take a photo.'),
          action: SnackBarAction(label: 'Settings', onPressed: openAppSettings),
        ),
      );
    } else {
      AppSnackbar.error(context, 'Camera permission is required to take a photo.');
    }
    return false;
  }

  /// Sends the current controller values to the backend. Returns whether the
  /// save succeeded; on failure it surfaces an error snackbar. Shared by the
  /// Personal Information sheet and the per-icon social-link editor.
  Future<bool> _persistProfile() async {
    final payload = {
      'first_name': _firstNameController.text.trim(),
      'last_name': _lastNameController.text.trim(),
      'phone': _phoneController.text.trim(),
      // date_of_birth has no backend column; sent but harmlessly ignored.
      'date_of_birth': _dobController.text.trim(),
      'designation': _designationController.text.trim(),
      'description': _bioController.text.trim(),
      'address': _addressController.text.trim(),
      'city': _cityController.text.trim(),
      'state': _stateController.text.trim(),
      'country': _countryController.text.trim(),
      'postal_code': _postalCodeController.text.trim(),
      'website': _websiteController.text.trim(),
      'facebook': _facebookController.text.trim(),
      'twitter': _twitterController.text.trim(),
      'linkedin': _linkedinController.text.trim(),
      // In dev we keep simulated local links too
      'instagram': _instagramController.text.trim(),
      'youtube': _youtubeController.text.trim(),
    };

    final repository = ref.read(profileRepositoryProvider);
    final result = await repository.updateProfile(payload);

    if (!mounted) return false;

    return result.fold(
      (failure) {
        AppSnackbar.error(
          context,
          failure.maybeWhen(
            server: (msg, _) => msg,
            orElse: () => 'Failed to save changes.',
          ),
        );
        return false;
      },
      (updatedData) {
        _populateFields(updatedData);
        ref.invalidate(profileFutureProvider);
        return true;
      },
    );
  }

  Future<void> _shareProfile() async {
    if (_loadedProfile == null) return;
    final data = _loadedProfile!;
    final username = (data['username'] ?? '').toString().trim();
    final displayName = (data['display_name'] ??
            '${data['first_name'] ?? ''} ${data['last_name'] ?? ''}'.trim())
        .toString()
        .trim();

    // Public, read-only profile page (/u/<username>) — works for any role and
    // opens for anyone. Falls back to the site root if username is missing.
    final shareUrl = username.isNotEmpty
        ? 'https://sashainfinity.com/u/$username'
        : 'https://sashainfinity.com';

    final name = displayName.isNotEmpty ? displayName : 'My';
    final message = 'Check out $name on SashaInfinity:\n$shareUrl';

    try {
      // Opens the native OS share card (WhatsApp, Gmail, copy, etc.).
      final result = await SharePlus.instance.share(
        ShareParams(
          text: message,
          subject: 'SashaInfinity Profile',
        ),
      );
      // Fallback to clipboard if the user dismissed the sheet without sharing.
      if (mounted && result.status == ShareResultStatus.dismissed) {
        await Clipboard.setData(ClipboardData(text: shareUrl));
        if (mounted) {
          AppSnackbar.success(context, 'Profile link copied to clipboard.');
        }
      }
    } catch (_) {
      // If the platform share sheet is unavailable, fall back to clipboard.
      await Clipboard.setData(ClipboardData(text: shareUrl));
      if (mounted) {
        AppSnackbar.success(context, 'Profile link copied to clipboard.');
      }
    }
  }

  /// Opens the in-app public profile (/u/<username>) for the current user — a
  /// read-only, shareable view of how others see this profile.
  void _openPublicProfile(Map<String, dynamic> data) {
    final username = (data['username'] ?? '').toString().trim();
    if (username.isEmpty) {
      AppSnackbar.error(context, 'Public profile is unavailable right now.');
      return;
    }
    context.push('/u/$username');
  }

  void _openAboutUs() {
    Navigator.push(
      context,
      MaterialPageRoute(builder: (context) => const AboutPage()),
    );
  }

  Future<void> _openContact() async {
    final emailUri = Uri(
      scheme: 'mailto',
      path: 'support@sashainfinity.com',
      queryParameters: {
        'subject': 'SashaInfinity Profile Support',
      },
    );

    if (await canLaunchUrl(emailUri)) {
      await launchUrl(emailUri);
      return;
    }

    if (!mounted) return;
    _showInfoSheet(
      title: 'Contact',
      icon: Icons.contact_support_outlined,
      lines: const [
        'Email: support@sashainfinity.com',
        'Website: sashainfinity.com',
      ],
    );
  }

  void _showInfoSheet({
    required String title,
    required IconData icon,
    required List<String> lines,
  }) {
    showModalBottomSheet<void>(
      context: context,
      showDragHandle: true,
      builder: (context) {
        final theme = Theme.of(context);
        return Padding(
          padding: const EdgeInsets.fromLTRB(24, 8, 24, 32),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Icon(icon, color: AppTheme.primary),
                  const SizedBox(width: 12),
                  Text(
                    title,
                    style: theme.textTheme.titleLarge?.copyWith(
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 16),
              ...lines.map(
                (line) => Padding(
                  padding: const EdgeInsets.only(bottom: 10),
                  child: Text(
                    line,
                    style: theme.textTheme.bodyMedium?.copyWith(height: 1.4),
                  ),
                ),
              ),
            ],
          ),
        );
      },
    );
  }

  Future<void> _handleLogout() async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: const Text('Sign out?'),
        content:
            const Text('You will need to sign in again to access your courses.'),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(dialogContext).pop(false),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () => Navigator.of(dialogContext).pop(true),
            child: const Text('Sign Out'),
          ),
        ],
      ),
    );
    if (confirmed == true && mounted) {
      await ref.read(authProvider.notifier).logout();
    }
  }

  /// Change password (authenticated) — opens the change-password sheet, which
  /// owns its own controllers (disposed in its State, avoiding the
  /// "controller used after disposed" race on sheet close).
  /// Currently unused: the Change Password tile is hidden (see Settings).
  /// Kept for easy re-enable.
  // ignore: unused_element
  Future<void> _changePassword() async {
    final changed = await showModalBottomSheet<bool>(
      context: context,
      isScrollControlled: true,
      showDragHandle: true,
      builder: (_) => const _ChangePasswordSheet(),
    );
    if (changed == true && mounted) {
      AppSnackbar.success(context, 'Password changed successfully.');
    }
  }

  void _openSettings() {
    Navigator.push(
      context,
      MaterialPageRoute(builder: (_) => const SettingsPage()),
    );
  }

  @override
  Widget build(BuildContext context) {
    final authState = ref.watch(authProvider);
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;

    // The page stays mounted in the IndexedStack, so the cached profile (and
    // the populated form fields) survive login/logout. Reset on user change.
    ref.listen<AuthState>(authProvider, (previous, next) {
      final prevUser =
          previous?.maybeWhen(authenticated: (u) => u.id, orElse: () => null);
      final nextUser =
          next.maybeWhen(authenticated: (u) => u.id, orElse: () => null);
      if (prevUser != nextUser) {
        setState(() {
          _loadedProfile = null;
        });
        ref.invalidate(profileFutureProvider);
      }
    });

    final isAuth = authState.maybeWhen(
      authenticated: (_) => true,
      orElse: () => false,
    );

    if (!isAuth) {
      return Scaffold(
        appBar: AppBar(title: const Text('My Profile')),
        body: Center(
          child: Padding(
            padding: const EdgeInsets.all(32.0),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Icon(Icons.person_off_outlined,
                    size: 80,
                    color: theme.colorScheme.primary.withOpacity(0.5)),
                const SizedBox(height: 24),
                Text(
                  'Login Required',
                  style: GoogleFonts.plusJakartaSans(
                      fontSize: 24, fontWeight: FontWeight.bold),
                ),
                const SizedBox(height: 12),
                Text(
                  'Please sign in to view and edit your profile.',
                  textAlign: TextAlign.center,
                  style: GoogleFonts.plusJakartaSans(color: Colors.grey),
                ),
                const SizedBox(height: 32),
                ElevatedButton(
                  onPressed: () => context.go('/login'),
                  style: ElevatedButton.styleFrom(
                    padding: const EdgeInsets.symmetric(
                        horizontal: 48, vertical: 16),
                    shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(12)),
                  ),
                  child: const Text('Sign In'),
                ),
              ],
            ),
          ),
        ),
      );
    }

    final profileAsync = ref.watch(profileFutureProvider);

    return Scaffold(
      backgroundColor: isDark ? theme.colorScheme.surface : AppNeutrals.slate50,
      body: profileAsync.when(
        data: (data) {
          if (_loadedProfile == null) {
            _populateFields(data);
          }
          return _buildProfileContent(data, isDark, theme);
        },
        loading: () => const BrandedLoader(),
        error: (error, stack) => ErrorDisplay(
          message: error.toString(),
          onRetry: () => ref.refresh(profileFutureProvider),
        ),
      ),
    );
  }

  BoxDecoration _cardDecoration(bool isDark) => BoxDecoration(
        color: isDark ? AppTheme.surfaceDark : Colors.white,
        borderRadius: BorderRadius.circular(AppRadius.lg),
        border:
            Border.all(color: isDark ? AppTheme.borderDark : AppTheme.borderLight),
        boxShadow: isDark ? null : AppShadows.soft,
      );

  Widget _buildProfileContent(
      Map<String, dynamic> data, bool isDark, ThemeData theme) {
    return _RevealOnOpen(
      child: Stack(
        children: [
          SingleChildScrollView(
            padding: EdgeInsets.zero,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                // 1. Hero header — full-bleed photo with the page actions and
                // the user's name / email overlaid.
                _buildHeroHeader(data, isDark, theme),
                // Content sheet pulled up to overlap the hero with a rounded top.
                Transform.translate(
                  offset: const Offset(0, -28),
                  child: Container(
                    decoration: BoxDecoration(
                      color:
                          isDark ? theme.colorScheme.surface : AppNeutrals.slate50,
                      borderRadius: const BorderRadius.vertical(
                          top: Radius.circular(AppRadius.card)),
                    ),
                    padding: const EdgeInsets.fromLTRB(20, 24, 20, 32),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        // 2. Dashboard summary
                        _buildSectionHeader('Dashboard Summary'),
                        const SizedBox(height: 16),
                        _buildDashboardSummary(data, isDark, theme),
                        const SizedBox(height: 16),

                        // 3. Personal information (opens an editor sheet)
                        _buildActionTile(
                          title: 'Personal Information',
                          subtitle: 'First name, email, phone, date of birth',
                          icon: Icons.person_outline,
                          onTap: () => _openPersonalInfoSheet(data),
                        ),
                        const SizedBox(height: 24),

                        // 4. Social links
                        _buildSocialLinksSection(isDark, theme),
                        const SizedBox(height: 24),

                        // 5. Settings
                        _buildSectionHeader('Settings'),
                        const SizedBox(height: 12),
                        _buildActionTile(
                          title: 'Settings',
                          subtitle: 'Appearance, notifications, privacy and more',
                          icon: Icons.settings_outlined,
                          onTap: _openSettings,
                        ),
                        const SizedBox(height: 24),

                        // 6. About & support
                        _buildSectionHeader('About & Support'),
                        const SizedBox(height: 12),
                        _buildActionTile(
                          title: 'About Us',
                          subtitle: 'Learn more about SashaInfinity',
                          icon: Icons.info_outline,
                          onTap: _openAboutUs,
                        ),
                        const SizedBox(height: 12),
                        _buildActionTile(
                          title: 'Contact',
                          subtitle: 'Reach SashaInfinity support',
                          icon: Icons.contact_support_outlined,
                          onTap: _openContact,
                        ),
                        const SizedBox(height: 28),

                        // 7. Sign out
                        OutlinedButton.icon(
                          onPressed: _handleLogout,
                          icon: const Icon(Icons.logout, size: 20),
                          label: const Text('Sign Out'),
                          style: OutlinedButton.styleFrom(
                            foregroundColor: AppTheme.primary,
                            side: const BorderSide(color: AppTheme.primary),
                            padding: const EdgeInsets.symmetric(vertical: 16),
                            shape: RoundedRectangleBorder(
                                borderRadius:
                                    BorderRadius.circular(AppRadius.md)),
                            textStyle: GoogleFonts.inter(
                                fontSize: 15.5, fontWeight: FontWeight.w700),
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ],
            ),
          ),
          // A subtle saving overlay while a background persist runs.
          if (_isSaving)
            const Positioned(
              top: 0,
              left: 0,
              right: 0,
              child: LinearProgressIndicator(minHeight: 3),
            ),
        ],
      ),
    );
  }

  /// Resolves a stored photo path to a loadable URL. The backend stores a
  /// relative path (e.g. `/uploads/avatars/x.jpg`); [NetworkImage] needs an
  /// absolute URL, so prefix it with the API host (same pattern as course art).
  /// A `?v=<n>` token is appended after each upload: the backend overwrites the
  /// avatar at the same path, so without a changed URL Flutter's ImageCache
  /// would keep showing the old image.
  String _resolveAvatarUrl(String raw) {
    var url = raw.trim();
    if (url.isEmpty) return url;
    if (!url.startsWith('http')) {
      final separator = url.startsWith('/') ? '' : '/';
      url = '${AppConfig.baseUrl}$separator$url';
    }
    if (_avatarVersion > 0) {
      url = '$url${url.contains('?') ? '&' : '?'}v=$_avatarVersion';
    }
    return url;
  }

  /// Evicts every cached form of the avatar URL from Flutter's global image
  /// cache after an upload. The profile hero uses the versioned URL above
  /// (always fresh); this targets the non-versioned absolute URL that the Home
  /// app bar and the user-menu sheet cache.
  void _evictAvatar(String photoUrl) {
    final cache = PaintingBinding.instance.imageCache;
    final absolute =
        photoUrl.startsWith('http') ? photoUrl : '${AppConfig.baseUrl}$photoUrl';
    cache.evict(photoUrl);
    cache.evict(absolute);
  }

  /// 1. Hero header — a full-width photo (the uploaded profile photo, or a
  /// brand gradient fallback) with the page actions across the top and the
  /// name / email / role badge overlaid at the bottom.
  Widget _buildHeroHeader(
      Map<String, dynamic> data, bool isDark, ThemeData theme) {
    final photo = _resolveAvatarUrl((data['profile_photo'] ?? '').toString());
    final email = (data['email'] ?? '').toString();
    final role = (data['role'] ?? 'Student').toString();
    final displayName = (data['display_name'] ??
            '${data['first_name'] ?? ''} ${data['last_name'] ?? ''}'.trim())
        .toString()
        .trim();
    final topPad = MediaQuery.of(context).padding.top;
    const heroHeight = 360.0;

    return SizedBox(
      height: heroHeight,
      child: Stack(
        fit: StackFit.expand,
        children: [
          // Background: photo or brand gradient.
          if (photo.isNotEmpty)
            Image(
              image: NetworkImage(photo),
              fit: BoxFit.cover,
              errorBuilder: (_, __, ___) => Container(
                decoration: const BoxDecoration(gradient: AppGradients.primary),
              ),
            )
          else
            Container(
              decoration: const BoxDecoration(gradient: AppGradients.primary),
            ),
          // Legibility scrims — darken the top (for the action row) and the
          // bottom (behind the name block).
          const DecoratedBox(
            decoration: BoxDecoration(
              gradient: LinearGradient(
                begin: Alignment.topCenter,
                end: Alignment.bottomCenter,
                colors: [
                  Color(0x66000000),
                  Color(0x00000000),
                  Color(0x00000000),
                  Color(0xB3000000),
                ],
                stops: [0.0, 0.25, 0.55, 1.0],
              ),
            ),
          ),
          // Foreground content.
          Padding(
            padding: EdgeInsets.fromLTRB(16, topPad + 6, 6, 30),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Page title + actions
                Row(
                  children: [
                    Expanded(
                      child: Text(
                        'My Profile',
                        style: GoogleFonts.plusJakartaSans(
                          color: Colors.white,
                          fontSize: 22,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                    ),
                    _headerAction(Icons.public_rounded, 'View public profile',
                        () => _openPublicProfile(data)),
                    _headerAction(Icons.share_outlined, 'Share', _shareProfile),
                    _headerAction(Icons.edit_outlined, 'Edit profile',
                        () => _openPersonalInfoSheet(data)),
                    _headerAction(
                        Icons.settings_outlined, 'Settings', _openSettings),
                    _headerAction(Icons.logout, 'Sign out', _handleLogout),
                  ],
                ),
                const Spacer(),
                // Name
                Text(
                  displayName.isNotEmpty ? displayName : 'Sasha Scholar',
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: GoogleFonts.plusJakartaSans(
                    color: Colors.white,
                    fontSize: 34,
                    fontWeight: FontWeight.w800,
                    letterSpacing: -0.5,
                    shadows: const [
                      Shadow(color: Color(0x66000000), blurRadius: 12),
                    ],
                  ),
                ),
                if (email.isNotEmpty) ...[
                  const SizedBox(height: 4),
                  Text(
                    email,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: GoogleFonts.inter(
                      color: Colors.white.withValues(alpha: 0.9),
                      fontSize: 14.5,
                      shadows: const [
                        Shadow(color: Color(0x40000000), blurRadius: 8),
                      ],
                    ),
                  ),
                ],
                const SizedBox(height: 14),
                // Role badge + change photo
                Row(
                  children: [
                    Container(
                      padding: const EdgeInsets.symmetric(
                          horizontal: 16, vertical: 8),
                      decoration: BoxDecoration(
                        color: Colors.black.withValues(alpha: 0.28),
                        borderRadius: BorderRadius.circular(AppRadius.pill),
                        border: Border.all(
                            color: Colors.white.withValues(alpha: 0.6)),
                      ),
                      child: Text(
                        role.toUpperCase(),
                        style: GoogleFonts.inter(
                          color: Colors.white,
                          fontSize: 11.5,
                          fontWeight: FontWeight.w700,
                          letterSpacing: 0.8,
                        ),
                      ),
                    ),
                    const Spacer(),
                    GestureDetector(
                      onTap: _pickAndUploadAvatar,
                      child: Container(
                        padding: const EdgeInsets.symmetric(
                            horizontal: 16, vertical: 9),
                        decoration: BoxDecoration(
                          color: Colors.black.withValues(alpha: 0.40),
                          borderRadius: BorderRadius.circular(AppRadius.pill),
                          border: Border.all(
                              color: Colors.white.withValues(alpha: 0.25)),
                        ),
                        child: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            const Icon(Icons.photo_camera_outlined,
                                color: Colors.white, size: 18),
                            const SizedBox(width: 8),
                            Text(
                              'Change Photo',
                              style: GoogleFonts.inter(
                                color: Colors.white,
                                fontSize: 13.5,
                                fontWeight: FontWeight.w600,
                              ),
                            ),
                          ],
                        ),
                      ),
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

  Widget _headerAction(IconData icon, String tooltip, VoidCallback onTap) {
    return IconButton(
      icon: Icon(icon, color: Colors.white),
      tooltip: tooltip,
      onPressed: onTap,
    );
  }

  /// 2. Dashboard Summary — three stat tiles. Instructors/admins see
  /// Courses / Students / Rating (their teaching metrics); students see
  /// Courses / Completed / Certificates from their learning dashboard.
  Widget _buildDashboardSummary(
      Map<String, dynamic> data, bool isDark, ThemeData theme) {
    final role = (data['role'] ?? 'student').toString().toLowerCase();
    final stats = _summaryStats(role);
    return Row(
      children: [
        for (var i = 0; i < stats.length; i++) ...[
          Expanded(child: _statTile(stats[i], isDark, theme)),
          if (i != stats.length - 1) const SizedBox(width: 12),
        ],
      ],
    );
  }

  List<_Stat> _summaryStats(String role) {
    if (role == 'instructor' || role == 'admin') {
      final map = ref.watch(instructorDashboardProvider).valueOrNull ?? {};
      final s = (map['stats'] as Map?) ?? const {};
      final rating = s['average_rating'];
      return [
        _Stat(Icons.menu_book_outlined, '${s['total_courses'] ?? 0}', 'Courses',
            AppTheme.primary),
        _Stat(Icons.people_alt_outlined, '${s['total_students'] ?? 0}',
            'Students', const Color(0xFF3B82F6)),
        _Stat(
            Icons.star_rounded,
            rating is num ? rating.toStringAsFixed(1) : '0.0',
            'Rating',
            const Color(0xFFF59E0B)),
      ];
    }
    final s = ref.watch(studentDashboardProvider).valueOrNull?.stats;
    return [
      _Stat(Icons.menu_book_outlined, '${s?.enrolledCourses ?? 0}', 'Courses',
          AppTheme.primary),
      _Stat(Icons.check_circle_outline, '${s?.completedCourses ?? 0}',
          'Completed', const Color(0xFF22C55E)),
      _Stat(Icons.workspace_premium_outlined, '${s?.certificates ?? 0}',
          'Certificates', const Color(0xFF7C3AED)),
    ];
  }

  Widget _statTile(_Stat stat, bool isDark, ThemeData theme) {
    final muted = isDark ? AppTheme.mutedDark : AppTheme.mutedLight;
    return Container(
      padding: const EdgeInsets.symmetric(vertical: 18, horizontal: 8),
      decoration: _cardDecoration(isDark),
      child: Column(
        children: [
          Icon(stat.icon, color: stat.color, size: 26),
          const SizedBox(height: 10),
          Text(
            stat.value,
            style: GoogleFonts.plusJakartaSans(
              fontWeight: FontWeight.w800,
              fontSize: 22,
              color: isDark ? AppTheme.textDark : AppNeutrals.slate900,
            ),
          ),
          const SizedBox(height: 2),
          Text(
            stat.label,
            textAlign: TextAlign.center,
            style: GoogleFonts.inter(fontSize: 12, color: muted),
          ),
        ],
      ),
    );
  }

  Widget _buildActionTile({
    required String title,
    required String subtitle,
    required IconData icon,
    required VoidCallback onTap,
  }) {
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;

    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(AppRadius.lg),
      child: Container(
        padding: const EdgeInsets.all(16),
        decoration: _cardDecoration(isDark),
        child: Row(
          children: [
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: AppTheme.primary.withValues(alpha: 0.12),
                borderRadius: BorderRadius.circular(AppRadius.md),
              ),
              child: Icon(icon, color: AppTheme.primary, size: 24),
            ),
            const SizedBox(width: 14),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    title,
                    style: GoogleFonts.plusJakartaSans(
                      fontWeight: FontWeight.w700,
                      fontSize: 16,
                    ),
                  ),
                  const SizedBox(height: 2),
                  Text(
                    subtitle,
                    style: theme.textTheme.bodySmall?.copyWith(
                      color: theme.textTheme.bodySmall?.color
                          ?.withValues(alpha: 0.65),
                    ),
                  ),
                ],
              ),
            ),
            const Icon(Icons.chevron_right, color: Colors.grey),
          ],
        ),
      ),
    );
  }

  Widget _buildSectionHeader(String title) {
    return Row(
      children: [
        Container(
          width: 4,
          height: 22,
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
            fontSize: 20,
            letterSpacing: -0.3,
          ),
        ),
      ],
    );
  }

  /// 3. Personal Information — a bottom sheet editor for the core identity
  /// fields, matching the design (First/Last Name, Email read-only, Phone,
  /// Date of Birth). Saves through the shared [_persistProfile].
  Future<void> _openPersonalInfoSheet(Map<String, dynamic> data) async {
    final email = (data['email'] ?? '').toString();
    final formKey = GlobalKey<FormState>();
    bool saving = false;

    final saved = await showModalBottomSheet<bool>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (ctx) {
        final th = Theme.of(ctx);
        final isDark = th.brightness == Brightness.dark;
        return StatefulBuilder(
          builder: (ctx, setSheet) {
            Future<void> save() async {
              if (!formKey.currentState!.validate()) return;
              setSheet(() => saving = true);
              final ok = await _persistProfile();
              if (!mounted) return;
              if (ok) {
                Navigator.pop(ctx, true);
              } else {
                setSheet(() => saving = false);
              }
            }

            return Container(
              decoration: BoxDecoration(
                color: isDark ? AppTheme.surfaceDark : Colors.white,
                borderRadius: const BorderRadius.vertical(
                    top: Radius.circular(AppRadius.card)),
              ),
              padding: EdgeInsets.fromLTRB(
                  24, 12, 24, 24 + MediaQuery.of(ctx).viewInsets.bottom),
              child: Form(
                key: formKey,
                child: SingleChildScrollView(
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      Center(
                        child: Container(
                          width: 44,
                          height: 4,
                          decoration: BoxDecoration(
                            color: th.colorScheme.onSurface
                                .withValues(alpha: 0.18),
                            borderRadius: BorderRadius.circular(999),
                          ),
                        ),
                      ),
                      const SizedBox(height: 18),
                      Center(
                        child: Text(
                          'Personal Information',
                          style: GoogleFonts.plusJakartaSans(
                            fontWeight: FontWeight.w800,
                            fontSize: 22,
                          ),
                        ),
                      ),
                      const SizedBox(height: 4),
                      Center(
                        child: Text(
                          'Update your personal details',
                          style: th.textTheme.bodyMedium?.copyWith(
                            color:
                                th.colorScheme.onSurface.withValues(alpha: 0.6),
                          ),
                        ),
                      ),
                      const SizedBox(height: 24),
                      _sheetField(
                        controller: _firstNameController,
                        label: 'First Name',
                        validator: (v) => (v == null || v.trim().isEmpty)
                            ? 'First name is required'
                            : null,
                      ),
                      _sheetField(
                        controller: _lastNameController,
                        label: 'Last Name',
                      ),
                      _sheetField(
                        label: 'Email',
                        initialValue: email,
                        readOnly: true,
                      ),
                      _sheetField(
                        controller: _phoneController,
                        label: 'Phone',
                        keyboardType: TextInputType.phone,
                        validator: (v) {
                          if (v == null || v.trim().isEmpty) {
                            return 'Phone number is required';
                          }
                          if (v.trim().length < 10) {
                            return 'Must be at least 10 digits';
                          }
                          return null;
                        },
                      ),
                      _sheetField(
                        controller: _dobController,
                        label: 'Date of Birth',
                        readOnly: true,
                        suffixIcon: Icons.keyboard_arrow_down,
                        onTap: () async {
                          final now = DateTime.now();
                          final picked = await showDatePicker(
                            context: ctx,
                            initialDate: _parseDob() ?? DateTime(2000, 1, 1),
                            firstDate: DateTime(1900),
                            lastDate: now,
                          );
                          if (picked != null) {
                            setSheet(() => _dobController.text =
                                _formatDob(picked));
                          }
                        },
                      ),
                      const SizedBox(height: 8),
                      Row(
                        children: [
                          Expanded(
                            child: OutlinedButton(
                              onPressed:
                                  saving ? null : () => Navigator.pop(ctx, false),
                              style: OutlinedButton.styleFrom(
                                foregroundColor: AppTheme.primary,
                                side: const BorderSide(color: AppTheme.primary),
                                padding:
                                    const EdgeInsets.symmetric(vertical: 16),
                                shape: RoundedRectangleBorder(
                                    borderRadius:
                                        BorderRadius.circular(AppRadius.md)),
                              ),
                              child: const Text('Cancel'),
                            ),
                          ),
                          const SizedBox(width: 14),
                          Expanded(
                            child: DecoratedBox(
                              decoration: BoxDecoration(
                                gradient: AppGradients.fire,
                                borderRadius:
                                    BorderRadius.circular(AppRadius.md),
                              ),
                              child: ElevatedButton(
                                onPressed: saving ? null : save,
                                style: ElevatedButton.styleFrom(
                                  backgroundColor: Colors.transparent,
                                  shadowColor: Colors.transparent,
                                  padding:
                                      const EdgeInsets.symmetric(vertical: 16),
                                  shape: RoundedRectangleBorder(
                                      borderRadius:
                                          BorderRadius.circular(AppRadius.md)),
                                ),
                                child: saving
                                    ? const SizedBox(
                                        height: 20,
                                        width: 20,
                                        child: CircularProgressIndicator(
                                            strokeWidth: 2,
                                            color: Colors.white))
                                    : const Text('Save'),
                              ),
                            ),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
              ),
            );
          },
        );
      },
    );

    if (saved == true && mounted) {
      setState(() {});
      AppSnackbar.success(context, 'Profile updated successfully!');
    }
  }

  /// A filled, rounded text field used inside the Personal Information sheet.
  Widget _sheetField({
    TextEditingController? controller,
    String? initialValue,
    required String label,
    bool readOnly = false,
    TextInputType keyboardType = TextInputType.text,
    String? Function(String?)? validator,
    IconData? suffixIcon,
    VoidCallback? onTap,
  }) {
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;
    return Padding(
      padding: const EdgeInsets.only(bottom: 18),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            label,
            style: GoogleFonts.inter(
              fontSize: 13.5,
              fontWeight: FontWeight.w600,
              color: theme.colorScheme.onSurface.withValues(alpha: 0.7),
            ),
          ),
          const SizedBox(height: 8),
          TextFormField(
            controller: controller,
            initialValue: controller == null ? initialValue : null,
            readOnly: readOnly,
            onTap: onTap,
            keyboardType: keyboardType,
            validator: validator,
            style: GoogleFonts.inter(fontSize: 15.5),
            decoration: InputDecoration(
              filled: true,
              fillColor: isDark
                  ? Colors.white.withValues(alpha: 0.04)
                  : AppNeutrals.slate100,
              suffixIcon: suffixIcon != null
                  ? Icon(suffixIcon,
                      color: theme.colorScheme.onSurface.withValues(alpha: 0.5))
                  : null,
              contentPadding:
                  const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
              enabledBorder: OutlineInputBorder(
                borderRadius: BorderRadius.circular(AppRadius.md),
                borderSide: BorderSide(
                    color:
                        isDark ? AppTheme.borderDark : AppNeutrals.slate200),
              ),
              border: OutlineInputBorder(
                borderRadius: BorderRadius.circular(AppRadius.md),
                borderSide: BorderSide(
                    color:
                        isDark ? AppTheme.borderDark : AppNeutrals.slate200),
              ),
              focusedBorder: OutlineInputBorder(
                borderRadius: BorderRadius.circular(AppRadius.md),
                borderSide:
                    const BorderSide(color: AppTheme.primary, width: 1.5),
              ),
            ),
          ),
        ],
      ),
    );
  }

  /// Parses the stored MM/DD/YYYY date string back into a [DateTime].
  DateTime? _parseDob() {
    final parts = _dobController.text.trim().split('/');
    if (parts.length != 3) return null;
    final m = int.tryParse(parts[0]);
    final d = int.tryParse(parts[1]);
    final y = int.tryParse(parts[2]);
    if (m == null || d == null || y == null) return null;
    return DateTime(y, m, d);
  }

  String _formatDob(DateTime dt) =>
      '${dt.month.toString().padLeft(2, '0')}/${dt.day.toString().padLeft(2, '0')}/${dt.year}';

  List<_SocialPlatform> get _socialPlatforms => [
        _SocialPlatform('Website', Icons.language, const Color(0xFF0EA5E9),
            _websiteController),
        _SocialPlatform('Facebook', Icons.facebook, const Color(0xFF1877F2),
            _facebookController),
        _SocialPlatform('Instagram', Icons.camera_alt_outlined,
            const Color(0xFFE4405F), _instagramController),
        _SocialPlatform('Twitter (X)', Icons.alternate_email,
            const Color(0xFF1DA1F2), _twitterController),
        _SocialPlatform('LinkedIn', Icons.business, const Color(0xFF0A66C2),
            _linkedinController),
        _SocialPlatform('YouTube', Icons.video_library_outlined,
            const Color(0xFFFF0000), _youtubeController),
      ];

  Widget _buildSocialLinksSection(bool isDark, ThemeData theme) {
    final platforms = _socialPlatforms;
    final hasAny = platforms.any((p) => p.controller.text.trim().isNotEmpty);

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: _cardDecoration(isDark),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.share_outlined,
                  color: AppTheme.primary, size: 20),
              const SizedBox(width: 8),
              Text(
                'Social Links',
                style: GoogleFonts.plusJakartaSans(
                  fontWeight: FontWeight.bold,
                  fontSize: 16,
                ),
              ),
              const Spacer(),
              Container(
                padding:
                    const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                decoration: BoxDecoration(
                  color: theme.colorScheme.onSurface.withValues(alpha: 0.06),
                  borderRadius: BorderRadius.circular(20),
                ),
                child: Text(
                  'OPTIONAL',
                  style: GoogleFonts.inter(
                    fontSize: 10.5,
                    fontWeight: FontWeight.w700,
                    letterSpacing: 0.5,
                    color: theme.colorScheme.onSurface.withValues(alpha: 0.55),
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 18),
          // 3 per row to match the design grid.
          LayoutBuilder(
            builder: (context, constraints) {
              const perRow = 3;
              const spacing = 12.0;
              final itemWidth =
                  (constraints.maxWidth - spacing * (perRow - 1)) / perRow;
              return Wrap(
                spacing: spacing,
                runSpacing: 18,
                children: platforms
                    .map((p) => SizedBox(width: itemWidth, child: _socialIcon(p)))
                    .toList(),
              );
            },
          ),
          if (!hasAny) ...[
            const SizedBox(height: 18),
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                color: AppTheme.primary.withValues(alpha: 0.10),
                borderRadius: BorderRadius.circular(AppRadius.md),
              ),
              child: Row(
                children: [
                  const Icon(Icons.lightbulb_outline,
                      color: AppTheme.primary, size: 20),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Text(
                      'Add your social accounts to increase your profile '
                      'visibility.',
                      style: theme.textTheme.bodyMedium?.copyWith(
                        color:
                            theme.colorScheme.onSurface.withValues(alpha: 0.75),
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ],
        ],
      ),
    );
  }

  Widget _socialIcon(_SocialPlatform p) {
    final hasLink = p.controller.text.trim().isNotEmpty;
    // Icons stay in their brand color whether or not a link is set; an empty
    // slot is signalled with a lighter fill and a small "+" badge.
    return GestureDetector(
      onTap: () => _editSocialLink(p),
      child: Column(
        children: [
          Stack(
            alignment: Alignment.bottomRight,
            children: [
              Container(
                width: 64,
                height: 64,
                decoration: BoxDecoration(
                  color: p.color.withValues(alpha: hasLink ? 0.20 : 0.12),
                  shape: BoxShape.circle,
                  border: Border.all(
                    color: p.color.withValues(alpha: hasLink ? 1 : 0.45),
                    width: hasLink ? 2 : 1.5,
                  ),
                ),
                child: Icon(p.icon, color: p.color, size: 28),
              ),
              // Small "+" badge to signal the slot can be added/edited.
              Container(
                padding: const EdgeInsets.all(3),
                decoration: BoxDecoration(
                  color: AppTheme.primary,
                  shape: BoxShape.circle,
                  border: Border.all(color: Colors.white, width: 2),
                ),
                child: const Icon(Icons.add, color: Colors.white, size: 12),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            p.label,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            textAlign: TextAlign.center,
            style: GoogleFonts.inter(
              fontSize: 12.5,
              color: p.color,
              fontWeight: hasLink ? FontWeight.w700 : FontWeight.w600,
            ),
          ),
        ],
      ),
    );
  }

  /// Opens a sheet to add / edit / remove a single social link, then persists
  /// the change immediately.
  Future<void> _editSocialLink(_SocialPlatform p) async {
    final temp = TextEditingController(text: p.controller.text.trim());
    final existing = temp.text.isNotEmpty;

    final action = await showModalBottomSheet<String>(
      context: context,
      isScrollControlled: true,
      showDragHandle: true,
      builder: (ctx) {
        final th = Theme.of(ctx);
        return Padding(
          padding: EdgeInsets.fromLTRB(
              24, 8, 24, 24 + MediaQuery.of(ctx).viewInsets.bottom),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Row(
                children: [
                  Container(
                    padding: const EdgeInsets.all(10),
                    decoration: BoxDecoration(
                      color: p.color.withValues(alpha: 0.12),
                      borderRadius: BorderRadius.circular(10),
                    ),
                    child: Icon(p.icon, color: p.color),
                  ),
                  const SizedBox(width: 12),
                  Text(
                    '${existing ? 'Edit' : 'Add'} ${p.label}',
                    style: th.textTheme.titleLarge
                        ?.copyWith(fontWeight: FontWeight.bold),
                  ),
                ],
              ),
              const SizedBox(height: 16),
              TextField(
                controller: temp,
                autofocus: !existing,
                keyboardType: TextInputType.url,
                decoration: InputDecoration(
                  hintText: 'https://...',
                  prefixIcon: Icon(p.icon, size: 20),
                  border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(12)),
                ),
              ),
              const SizedBox(height: 16),
              ElevatedButton(
                onPressed: () => Navigator.pop(ctx, temp.text.trim()),
                style: ElevatedButton.styleFrom(
                  padding: const EdgeInsets.symmetric(vertical: 14),
                  shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(12)),
                ),
                child: const Text('Save'),
              ),
              if (existing) ...[
                const SizedBox(height: 8),
                Row(
                  children: [
                    Expanded(
                      child: OutlinedButton.icon(
                        onPressed: () => _openExternalLink(temp.text),
                        icon: const Icon(Icons.open_in_new, size: 18),
                        label: const Text('Open'),
                        style: OutlinedButton.styleFrom(
                          padding: const EdgeInsets.symmetric(vertical: 12),
                          shape: RoundedRectangleBorder(
                              borderRadius: BorderRadius.circular(12)),
                        ),
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: OutlinedButton.icon(
                        onPressed: () => Navigator.pop(ctx, '__remove__'),
                        icon: const Icon(Icons.delete_outline, size: 18),
                        label: const Text('Remove'),
                        style: OutlinedButton.styleFrom(
                          foregroundColor: AppTheme.danger,
                          side: const BorderSide(color: AppTheme.danger),
                          padding: const EdgeInsets.symmetric(vertical: 12),
                          shape: RoundedRectangleBorder(
                              borderRadius: BorderRadius.circular(12)),
                        ),
                      ),
                    ),
                  ],
                ),
              ],
            ],
          ),
        );
      },
    );

    temp.dispose();

    if (action == null || !mounted) return; // cancelled or widget disposed
    final removing = action == '__remove__';
    p.controller.text = removing ? '' : action.trim();

    setState(() => _isSaving = true);
    final ok = await _persistProfile();
    if (!mounted) return;
    setState(() => _isSaving = false);
    if (ok) {
      AppSnackbar.success(
          context, '${p.label} ${removing ? 'removed' : 'saved'}.');
    }
  }

  /// Normalizes [raw] to a launchable URL and opens it in an external app.
  Future<void> _openExternalLink(String raw) async {
    var url = raw.trim();
    if (url.isEmpty) return;
    if (!url.startsWith('http://') && !url.startsWith('https://')) {
      url = 'https://$url';
    }
    final uri = Uri.tryParse(url);
    if (uri != null && await canLaunchUrl(uri)) {
      await launchUrl(uri, mode: LaunchMode.externalApplication);
    } else if (mounted) {
      AppSnackbar.error(context, 'Could not open the link.');
    }
  }
}

/// One stat shown in the Dashboard Summary tiles.
class _Stat {
  final IconData icon;
  final String value;
  final String label;
  final Color color;
  const _Stat(this.icon, this.value, this.label, this.color);
}

/// Plays a gentle upward fade-in reveal the first time the profile content
/// appears (per the design spec's "upward reveal animation when opening").
class _RevealOnOpen extends StatefulWidget {
  final Widget child;
  const _RevealOnOpen({required this.child});

  @override
  State<_RevealOnOpen> createState() => _RevealOnOpenState();
}

class _RevealOnOpenState extends State<_RevealOnOpen>
    with SingleTickerProviderStateMixin {
  late final AnimationController _c =
      AnimationController(vsync: this, duration: const Duration(milliseconds: 520));
  late final Animation<double> _fade =
      CurvedAnimation(parent: _c, curve: Curves.easeOut);
  late final Animation<Offset> _slide = Tween<Offset>(
    begin: const Offset(0, 0.05),
    end: Offset.zero,
  ).animate(CurvedAnimation(parent: _c, curve: Curves.easeOutCubic));

  @override
  void initState() {
    super.initState();
    _c.forward();
  }

  @override
  void dispose() {
    _c.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return FadeTransition(
      opacity: _fade,
      child: SlideTransition(position: _slide, child: widget.child),
    );
  }
}

/// Describes a social platform shown as an icon in the Social Links section.
/// [controller] is the existing per-field controller that stores its URL.
class _SocialPlatform {
  final String label;
  final IconData icon;
  final Color color;
  final TextEditingController controller;

  const _SocialPlatform(this.label, this.icon, this.color, this.controller);
}

/// Change-password bottom sheet. Owns its own controllers and disposes them in
/// [dispose], so closing the sheet never touches a disposed controller.
/// Pops `true` on success; shows an inline error snackbar on failure.
/// Currently unused: the Change Password tile is hidden. Kept for re-enable.
// ignore: unused_element
class _ChangePasswordSheet extends ConsumerStatefulWidget {
  const _ChangePasswordSheet();

  @override
  ConsumerState<_ChangePasswordSheet> createState() =>
      _ChangePasswordSheetState();
}

class _ChangePasswordSheetState extends ConsumerState<_ChangePasswordSheet> {
  final _formKey = GlobalKey<FormState>();
  final _current = TextEditingController();
  final _new = TextEditingController();
  final _confirm = TextEditingController();
  bool _obCur = true, _obNew = true, _obConf = true, _submitting = false;

  @override
  void dispose() {
    _current.dispose();
    _new.dispose();
    _confirm.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() => _submitting = true);
    try {
      await ref.read(apiClientProvider).post(
        ApiEndpoints.changePassword,
        data: {'current_password': _current.text, 'new_password': _new.text},
      );
      if (!mounted) return;
      Navigator.of(context).pop(true);
    } catch (e) {
      if (!mounted) return;
      setState(() => _submitting = false);
      final msg = e is AppException ? e.message : 'Could not change password.';
      AppSnackbar.error(context, humanizeAuthError(msg));
    }
  }

  Widget _field(TextEditingController c, String label, bool obscure,
      VoidCallback toggle, String? Function(String?) validator) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: TextFormField(
        controller: c,
        obscureText: obscure,
        validator: validator,
        decoration: InputDecoration(
          labelText: label,
          prefixIcon: const Icon(Icons.lock_outline, size: 20),
          suffixIcon: IconButton(
            icon: Icon(obscure ? Icons.visibility_outlined : Icons.visibility),
            onPressed: toggle,
          ),
          border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: EdgeInsets.fromLTRB(
          24, 8, 24, 24 + MediaQuery.of(context).viewInsets.bottom),
      child: Form(
        key: _formKey,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Row(
              children: [
                const Icon(Icons.password_outlined, color: AppTheme.primary),
                const SizedBox(width: 12),
                Text('Change Password',
                    style: Theme.of(context)
                        .textTheme
                        .titleLarge
                        ?.copyWith(fontWeight: FontWeight.bold)),
              ],
            ),
            const SizedBox(height: 16),
            _field(_current, 'Current password', _obCur,
                () => setState(() => _obCur = !_obCur),
                (v) => (v == null || v.isEmpty) ? 'Required' : null),
            _field(_new, 'New password', _obNew,
                () => setState(() => _obNew = !_obNew), (v) {
              if (v == null || v.isEmpty) return 'Required';
              if (!_passwordRule.hasMatch(v)) {
                return '8+ chars, with upper, lower & a number';
              }
              if (v == _current.text) return 'Must differ from current';
              return null;
            }),
            _field(_confirm, 'Confirm new password', _obConf,
                () => setState(() => _obConf = !_obConf),
                (v) => v != _new.text ? 'Passwords do not match' : null),
            const SizedBox(height: 8),
            ElevatedButton(
              onPressed: _submitting ? null : _submit,
              style: ElevatedButton.styleFrom(
                padding: const EdgeInsets.symmetric(vertical: 16),
                shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(12)),
              ),
              child: _submitting
                  ? const SizedBox(
                      height: 20,
                      width: 20,
                      child: CircularProgressIndicator(
                          strokeWidth: 2, color: Colors.white))
                  : const Text('Update password'),
            ),
          ],
        ),
      ),
    );
  }
}
