import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Monotonic counter bumped whenever the session is force-expired
/// (refresh token missing/invalid). Leaf provider with no dependencies so the
/// network layer can signal the auth layer without a circular dependency.
class SessionExpiry extends Notifier<int> {
  @override
  int build() => 0;

  void expire() => state++;
}

final sessionExpiredProvider =
    NotifierProvider<SessionExpiry, int>(SessionExpiry.new);
