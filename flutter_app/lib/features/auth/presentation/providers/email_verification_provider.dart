// lib/features/auth/presentation/providers/email_verification_provider.dart
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';
import 'auth_provider.dart';

part 'email_verification_provider.g.dart';

/// Drives the verify-email screen and the inline "resend verification"
/// action on the login form.
/// State: `AsyncData(null)` = idle, `AsyncData(message)` = success message,
/// `AsyncError` = failure to show inline.
@riverpod
class EmailVerification extends _$EmailVerification {
  @override
  AsyncValue<String?> build() => const AsyncData(null);

  Future<bool> resend(String email) async {
    state = const AsyncLoading();
    final result = await ref
        .read(authRepositoryProvider)
        .resendVerification(email: email);
    return result.fold(
      (failure) {
        state = AsyncError(
          failure.maybeWhen(
            network: (message) => message,
            orElse: () => 'Could not resend the email. Please try again.',
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

  Future<bool> verify(String token) async {
    state = const AsyncLoading();
    final result =
        await ref.read(authRepositoryProvider).verifyEmail(token: token);
    return result.fold(
      (failure) {
        state = AsyncError(
          failure.maybeWhen(
            server: (message, _) => message,
            network: (message) => message,
            orElse: () => 'Verification failed. Please try again.',
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
