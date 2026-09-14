// lib/features/auth/presentation/providers/auth_state.dart
import 'package:freezed_annotation/freezed_annotation.dart';
import '../../domain/entities/user.dart';

part 'auth_state.freezed.dart';

@freezed
class AuthState with _$AuthState {
  const factory AuthState.initial() = _Initial;
  const factory AuthState.loading() = _Loading;
  const factory AuthState.authenticated(User user) = _Authenticated;

  /// [message] carries a one-time notice (e.g. "session expired") that the
  /// login page shows and then clears via [Auth.consumeMessage].
  const factory AuthState.unauthenticated({String? message}) =
      _Unauthenticated;

  /// Register succeeded but the account is unverified — no tokens were issued.
  /// UI navigates to the verify-email screen.
  const factory AuthState.registrationSuccess({
    required String email,
    required String message,
  }) = _RegistrationSuccess;

  /// Google sign-in hit a brand-new account: the backend wants a role before
  /// creating the user (POST /auth/google/complete).
  const factory AuthState.googleRoleSelection({
    required String email,
    required String name,
    required String picture,
    required String firebaseToken,
  }) = _GoogleRoleSelection;

  const factory AuthState.error(String message) = _Error;
}
