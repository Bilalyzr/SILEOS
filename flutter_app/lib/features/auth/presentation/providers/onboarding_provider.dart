// lib/features/auth/presentation/providers/onboarding_provider.dart
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../../core/constants/storage_keys.dart';
import '../../../../core/storage/secure_storage.dart';

/// Tracks whether the user has completed the first-launch "Get Started"
/// onboarding. Persisted so the onboarding shows exactly once — on the very
/// first open of the app — and never again.
final onboardingCompletedProvider =
    NotifierProvider<OnboardingNotifier, bool>(OnboardingNotifier.new);

class OnboardingNotifier extends Notifier<bool> {
  final SecureStorage _storage = SecureStorage();

  // Default to `true` (completed) so we never flash the onboarding before the
  // stored flag has been read. The splash loads the real value (via [load])
  // before the auth state resolves, so the redirect always sees the truth.
  @override
  bool build() => true;

  /// Reads the persisted flag. Must run during splash init, before
  /// `checkAuthStatus()` flips the auth state, so the redirect routes a
  /// first-time user to Get Started instead of Login.
  Future<void> load() async {
    final done = await _storage.containsKey(StorageKeys.onboardingCompleted);
    state = done;
  }

  /// Marks onboarding done so Get Started is never shown again.
  Future<void> complete() async {
    await _storage.write(StorageKeys.onboardingCompleted, 'true');
    state = true;
  }
}
