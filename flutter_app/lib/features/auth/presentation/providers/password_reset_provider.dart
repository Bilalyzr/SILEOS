// lib/features/auth/presentation/providers/password_reset_provider.dart
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';
import 'auth_provider.dart';

part 'password_reset_provider.g.dart';

/// Drives the forgot/reset password screens.
/// State: `AsyncData(null)` = idle, `AsyncData(message)` = success message
/// from the backend, `AsyncError` = failure to show inline.
@riverpod
class PasswordReset extends _$PasswordReset {
  @override
  AsyncValue<String?> build() => const AsyncData(null);

  Future<bool> sendForgotEmail(String email) async {
    state = const AsyncLoading();
    final result = await ref
        .read(authRepositoryProvider)
        .forgotPassword(email: email);
    return result.fold(
      (failure) {
        state = AsyncError(
          failure.maybeWhen(
            network: (message) => message,
            validation: (message, _) => message,
            unknown: (message) =>
                message ?? 'Could not send the reset email. Please try again.',
            orElse: () => 'Could not send the reset email. Please try again.',
          ),
          StackTrace.current,
        );
        return false;
      },
      (message) {
        state = AsyncData(message);
        return true;
      },
    );
  }

  Future<bool> submitReset({
    required String token,
    required String newPassword,
  }) async {
    state = const AsyncLoading();
    final result = await ref
        .read(authRepositoryProvider)
        .resetPassword(token: token, newPassword: newPassword);
    return result.fold(
      (failure) {
        state = AsyncError(
          failure.maybeWhen(
            server: (message, _) => message,
            network: (message) => message,
            validation: (message, _) => message,
            orElse: () => 'Password reset failed. Please try again.',
          ),
          StackTrace.current,
        );
        return false;
      },
      (message) {
        state = AsyncData(message);
        return true;
      },
    );
  }

  void reset() => state = const AsyncData(null);
}
