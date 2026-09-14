// lib/core/services/deep_link_service.dart
import 'dart:async';
import 'package:app_links/app_links.dart';
import 'package:flutter/foundation.dart';

/// Listens for incoming deep links (cold-start + while running) and forwards
/// every link to [onLink]. The app uses this to catch the email-verification
/// link — `https://sashainfinity.com/verify-email?token=…` (App / Universal
/// Link) or `sashalms://verify-email?token=…` (custom scheme) — and route the
/// user to the verify screen, which auto-verifies the token.
class DeepLinkService {
  DeepLinkService(this.onLink);

  final void Function(Uri uri) onLink;
  final AppLinks _appLinks = AppLinks();
  StreamSubscription<Uri>? _sub;

  Future<void> init() async {
    // Links that arrive while the app is already running.
    _sub = _appLinks.uriLinkStream.listen(
      onLink,
      onError: (Object e) => debugPrint('DeepLink stream error: $e'),
    );

    // The link that cold-started the app, if any.
    try {
      final initial = await _appLinks.getInitialLink();
      if (initial != null) onLink(initial);
    } catch (e) {
      debugPrint('DeepLink initial error: $e');
    }
  }

  void dispose() => _sub?.cancel();
}
