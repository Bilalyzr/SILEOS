// lib/features/auth/presentation/providers/auth_provider.dart
import 'dart:async';
import 'dart:convert';
import 'package:riverpod_annotation/riverpod_annotation.dart';
import '../../domain/entities/user.dart';
import '../../domain/usecases/login_usecase.dart';
import '../../domain/usecases/register_usecase.dart';
import '../../domain/usecases/logout_usecase.dart';
import '../../domain/repositories/auth_repository.dart';
import '../../../../config/app_config.dart';
import '../../../../core/auth/session_events.dart';
import '../../../../core/errors/failures.dart';
import '../../../../core/storage/secure_storage.dart';
import '../../../../core/constants/storage_keys.dart';
import '../../../../core/network/network_provider.dart';
import '../../data/datasources/auth_remote_datasource.dart';
import '../../data/repositories/auth_repository_impl.dart';
import '../../data/services/google_signin_service.dart';
import 'auth_state.dart';

part 'auth_provider.g.dart';

@riverpod
AuthRemoteDataSource authRemoteDataSource(AuthRemoteDataSourceRef ref) {
  return AuthRemoteDataSourceImpl(
    apiClient: ref.watch(apiClientProvider),
  );
}

@riverpod
AuthRepository authRepository(AuthRepositoryRef ref) {
  return AuthRepositoryImpl(
    remoteDataSource: ref.watch(authRemoteDataSourceProvider),
    secureStorage: SecureStorage(),
  );
}

@riverpod
GoogleSignInService googleSignInService(GoogleSignInServiceRef ref) {
  return GoogleSignInService();
}

@riverpod
LoginUseCase loginUseCase(LoginUseCaseRef ref) {
  return LoginUseCase(ref.watch(authRepositoryProvider));
}

@riverpod
RegisterUseCase registerUseCase(RegisterUseCaseRef ref) {
  return RegisterUseCase(ref.watch(authRepositoryProvider));
}

@riverpod
LogoutUseCase logoutUseCase(LogoutUseCaseRef ref) {
  return LogoutUseCase(ref.watch(authRepositoryProvider));
}

@riverpod
class Auth extends _$Auth {
  late final SecureStorage _secureStorage;

  @override
  AuthState build() {
    _secureStorage = SecureStorage();

    // The network layer bumps this counter when the refresh token is gone or
    // rejected (tokens are already cleared at that point).
    ref.listen<int>(sessionExpiredProvider, (previous, next) {
      if (previous != null && next != previous) {
        state = const AuthState.unauthenticated(
          message: 'Your session has expired. Please sign in again.',
        );
      }
    });

    // Don't call _checkAuthStatus in build - it causes issues with GoRouter redirect
    return const AuthState.initial();
  }

  String _failureMessage(Failure error) {
    return error.when(
      server: (message, _) => message,
      network: (message) => message,
      cache: (message) => message,
      unauthorized: (message) => message ?? 'Unauthorized',
      forbidden: (message) => message ?? 'Forbidden',
      notFound: (message) => message ?? 'Not found',
      validation: (message, _) => message,
      unknown: (message) => message ?? 'An error occurred',
    );
  }

  Future<void> checkAuthStatus() async {
    final token = await _secureStorage.getAccessToken();
    if (token == null) {
      state = const AuthState.unauthenticated();
      return;
    }

    // Optimistic restore: a stored token + a cached user means we log straight
    // back in (instant, and survives a flaky network on startup), then validate
    // in the background. A genuinely expired session is caught by the refresh
    // interceptor, which clears the tokens and bumps sessionExpired (handled in
    // build()) → the user is returned to login. This is what keeps people
    // signed in across restarts instead of re-logging in every time.
    final cached = await _readCachedUser();
    if (cached != null) {
      state = AuthState.authenticated(cached);
      unawaited(_refreshUserInBackground());
      return;
    }

    // No cached user (e.g. first launch after updating the app): validate now.
    final result = await ref.read(authRepositoryProvider).getCurrentUser();
    await result.fold(
      (error) async => state = const AuthState.unauthenticated(),
      (user) async {
        await _cacheUser(user);
        state = AuthState.authenticated(user);
      },
    );
  }

  /// Updates the signed-in user's avatar everywhere it's read from the auth
  /// state (home app bar, user-menu sheet) after a successful upload. `/auth/me`
  /// does not return the profile photo, so `checkAuthStatus()` can't pick up a
  /// new avatar — the uploaded path is pushed into the auth user directly and
  /// re-cached so it survives the next restart.
  Future<void> updateAvatarUrl(String? avatarUrl) async {
    await state.maybeWhen(
      authenticated: (user) async {
        final updated = user.copyWith(avatarUrl: avatarUrl);
        await _cacheUser(updated);
        state = AuthState.authenticated(updated);
      },
      orElse: () async {},
    );
  }

  /// Refreshes the cached user in the background. Never force-logs-out on a
  /// network/server error — we keep the optimistic session. A real auth failure
  /// is handled by the refresh interceptor → sessionExpired → unauthenticated.
  Future<void> _refreshUserInBackground() async {
    final result = await ref.read(authRepositoryProvider).getCurrentUser();
    result.fold(
      (error) {},
      (user) {
        _cacheUser(user);
        state.maybeWhen(
          authenticated: (_) => state = AuthState.authenticated(user),
          orElse: () {},
        );
      },
    );
  }

  // ----- Cached-user persistence -------------------------------------------
  // Keeps a lightweight copy of the signed-in user so the app can restore the
  // session offline / instantly on the next launch.
  Future<void> _cacheUser(User user) async {
    await _secureStorage.write(
      StorageKeys.userData,
      jsonEncode({
        'id': user.id,
        'email': user.email,
        'firstName': user.firstName,
        'lastName': user.lastName,
        'role': user.role,
        'avatarUrl': user.avatarUrl,
        'phone': user.phone,
        'isActive': user.isActive,
        'createdAt': user.createdAt?.toIso8601String(),
      }),
    );
  }

  Future<User?> _readCachedUser() async {
    final raw = await _secureStorage.read(StorageKeys.userData);
    if (raw == null || raw.isEmpty) return null;
    try {
      final m = jsonDecode(raw) as Map<String, dynamic>;
      return User(
        id: m['id'] as String,
        email: m['email'] as String,
        firstName: (m['firstName'] as String?) ?? '',
        lastName: (m['lastName'] as String?) ?? '',
        role: (m['role'] as String?) ?? 'student',
        avatarUrl: m['avatarUrl'] as String?,
        phone: m['phone'] as String?,
        isActive: m['isActive'] as bool?,
        createdAt: m['createdAt'] != null
            ? DateTime.tryParse(m['createdAt'] as String)
            : null,
      );
    } catch (_) {
      return null;
    }
  }

  Future<void> _clearCachedUser() async {
    await _secureStorage.delete(StorageKeys.userData);
  }

  Future<void> login({
    required String email,
    required String password,
  }) async {
    state = const AuthState.loading();

    final result = await ref.read(loginUseCaseProvider).call(
          email: email,
          password: password,
        );

    result.fold(
      (error) => state = AuthState.error(_failureMessage(error)),
      (user) {
        _cacheUser(user);
        state = AuthState.authenticated(user);
      },
    );
  }

  Future<void> register({
    required String email,
    required String password,
    required String firstName,
    required String lastName,
    String? phone,
    String userType = 'student',
  }) async {
    state = const AuthState.loading();

    final result = await ref.read(registerUseCaseProvider).call(
          email: email,
          password: password,
          firstName: firstName,
          lastName: lastName,
          phone: phone,
          userType: userType,
        );

    result.fold(
      (error) {
        // Email already registered (backend 400) is not a hard error — the
        // account exists, so guide the user to sign in instead of showing a
        // scary failure popup. The register form routes `unauthenticated`
        // (with a message) to the login screen.
        final alreadyExists = error.maybeWhen(
          server: (message, statusCode) =>
              statusCode == 400 && message.toLowerCase().contains('already'),
          orElse: () => false,
        );
        if (alreadyExists) {
          state = const AuthState.unauthenticated(
            message: 'This email is already registered. Please sign in.',
          );
        } else {
          state = AuthState.error(_failureMessage(error));
        }
      },
      (user) {
        // No tokens are issued on register. If the account is already active
        // (AUTO_VERIFY_EMAIL — isActive == true), there's nothing to verify, so
        // send the user straight to login. Otherwise it must verify its email.
        if (user.isActive == true) {
          state = const AuthState.unauthenticated(
            message: 'Registration successful! You can now sign in.',
          );
        } else {
          state = AuthState.registrationSuccess(
            email: user.email,
            message:
                'Registration successful! Check your inbox to verify your email.',
          );
        }
      },
    );
  }

  /// Full Google flow: Google picker → Firebase ID token → backend.
  /// Existing account signs straight in; a new account moves to
  /// [AuthState.googleRoleSelection] so the UI can ask for a role.
  Future<void> loginWithGoogle() async {
    if (!AppConfig.firebaseAvailable) {
      state = const AuthState.error(
        'Google Sign-In is not configured yet. Please use email and password.',
      );
      return;
    }

    state = const AuthState.loading();
    try {
      final firebaseToken =
          await ref.read(googleSignInServiceProvider).getFirebaseIdToken();
      if (firebaseToken == null) {
        // User dismissed the account picker.
        state = const AuthState.unauthenticated();
        return;
      }

      final result = await ref
          .read(authRepositoryProvider)
          .loginWithGoogle(firebaseToken: firebaseToken);

      result.fold(
        (error) => state = AuthState.error(_failureMessage(error)),
        (googleResult) => googleResult.when(
          signedIn: (user) {
            _cacheUser(user);
            state = AuthState.authenticated(user);
          },
          needsRole: (email, name, picture, token) =>
              state = AuthState.googleRoleSelection(
            email: email,
            name: name,
            picture: picture,
            firebaseToken: token,
          ),
        ),
      );
    } catch (e) {
      state = AuthState.error('Google sign-in failed: $e');
    }
  }

  Future<void> completeGoogleSignIn({
    required String firebaseToken,
    required String role,
  }) async {
    state = const AuthState.loading();

    final result = await ref.read(authRepositoryProvider).completeGoogleSignIn(
          firebaseToken: firebaseToken,
          role: role,
        );

    result.fold(
      (error) => state = AuthState.error(_failureMessage(error)),
      (user) {
        _cacheUser(user);
        state = AuthState.authenticated(user);
      },
    );
  }

  Future<void> logout() async {
    state = const AuthState.loading();
    await ref.read(logoutUseCaseProvider).call();
    // Also drop the Google/Firebase session so the account picker shows again
    // next time. Best-effort: never block logout on it.
    try {
      await ref.read(googleSignInServiceProvider).signOut();
    } catch (_) {}
    await _clearCachedUser();
    state = const AuthState.unauthenticated();
  }

  /// Clears the one-time notice carried by [AuthState.unauthenticated]
  /// after the UI has shown it.
  void consumeMessage() {
    state.maybeWhen(
      unauthenticated: (message) {
        if (message != null) state = const AuthState.unauthenticated();
      },
      orElse: () {},
    );
  }

  void clearError() {
    final isCurrentlyError = state.maybeWhen(
      error: (_) => true,
      orElse: () => false,
    );
    if (isCurrentlyError) {
      state = const AuthState.initial();
    }
  }
}
