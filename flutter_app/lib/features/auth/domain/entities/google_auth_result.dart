import 'package:freezed_annotation/freezed_annotation.dart';
import 'user.dart';

part 'google_auth_result.freezed.dart';

/// Outcome of POST /auth/google: an existing account is signed in directly,
/// a new account must pick a role first (then POST /auth/google/complete).
@freezed
class GoogleAuthResult with _$GoogleAuthResult {
  const factory GoogleAuthResult.signedIn(User user) = _SignedIn;

  const factory GoogleAuthResult.needsRole({
    required String email,
    required String name,
    required String picture,
    required String firebaseToken,
  }) = _NeedsRole;
}
