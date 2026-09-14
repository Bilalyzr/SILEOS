// lib/features/auth/data/repositories/auth_repository_impl.dart
import 'package:dartz/dartz.dart';
import 'package:flutter/foundation.dart';
import 'package:firebase_auth/firebase_auth.dart' hide User;
import '../../../../config/app_config.dart';
import '../../../../core/errors/exceptions.dart';
import '../../../../core/errors/failures.dart';
import '../../../../core/storage/secure_storage.dart';
import '../../domain/entities/google_auth_result.dart';
import '../../domain/entities/user.dart';
import '../../domain/repositories/auth_repository.dart';
import '../datasources/auth_remote_datasource.dart';
import '../models/user_model.dart';

class AuthRepositoryImpl implements AuthRepository {
  final AuthRemoteDataSource remoteDataSource;
  final SecureStorage secureStorage;

  AuthRepositoryImpl({
    required this.remoteDataSource,
    required this.secureStorage,
  });

  @override
  Future<Either<Failure, User>> login({
    required String email,
    required String password,
  }) async {
    // Firebase-first: validate the password against Firebase Authentication —
    // the credential source of truth — so passwords changed via Firebase's
    // "reset password" email take effect for login. On success we exchange the
    // Firebase ID token for a backend session at /auth/google (reusing the
    // existing Google path, which issues our JWTs for an existing user).
    //
    // If Firebase rejects the credentials (wrong password) OR the account is
    // not yet mirrored into Firebase (older accounts), we fall back to the
    // backend /auth/login, which also backfills Firebase on success.
    if (AppConfig.firebaseAvailable) {
      final viaFirebase = await _loginViaFirebase(email: email, password: password);
      if (viaFirebase != null) return viaFirebase;
    }
    return _loginViaBackend(email: email, password: password);
  }

  /// Firebase-first login. Returns the resolved [Either] on success, or `null`
  /// to signal "fall back to backend login" — Firebase rejected the credentials,
  /// the account isn't in Firebase, or the token exchange didn't yield a backend
  /// session. Never throws.
  Future<Either<Failure, User>?> _loginViaFirebase({
    required String email,
    required String password,
  }) async {
    try {
      final cred = await FirebaseAuth.instance.signInWithEmailAndPassword(
        email: email.trim(),
        password: password,
      );
      final idToken = await cred.user?.getIdToken();
      // The app's real session is the backend JWT, not the Firebase session.
      await FirebaseAuth.instance.signOut();
      if (idToken == null) return null;

      final response = await remoteDataSource.googleLogin(firebaseToken: idToken);
      // new_user == true → exists in Firebase but not the backend (rare); let
      // the backend fallback surface the proper error.
      if (response['new_user'] == true || response['access_token'] == null) {
        return null;
      }
      await secureStorage.saveTokens(
        accessToken: response['access_token'],
        refreshToken: response['refresh_token'],
      );
      return Right(UserModel.fromAuthResponse(response).toEntity());
    } on FirebaseAuthException {
      // wrong-password / user-not-found / invalid-credential → fall back.
      return null;
    } catch (_) {
      // Token exchange or any other error → fall back to backend login.
      return null;
    }
  }

  /// Backend email/password login. Also backfills the account into Firebase on
  /// success so future logins can go through the Firebase-first path.
  Future<Either<Failure, User>> _loginViaBackend({
    required String email,
    required String password,
  }) async {
    try {
      final response = await remoteDataSource.login(email: email, password: password);

      // Save tokens
      await secureStorage.saveTokens(
        accessToken: response['access_token'],
        refreshToken: response['refresh_token'],
      );

      // Backfill existing accounts into Firebase: on a successful login we
      // have the plaintext password, so mirror it so pre-existing users (who
      // registered before Firebase sync existed) also show up in Firebase
      // Authentication. Idempotent + best-effort: never blocks login.
      await _mirrorToFirebase(email: email, password: password);

      final userModel = UserModel.fromAuthResponse(response);
      return Right(userModel.toEntity());
    } on ServerException catch (e) {
      return Left(Failure.server(message: e.message, statusCode: e.statusCode));
    } on NetworkException catch (e) {
      return Left(Failure.network(message: e.message));
    } on UnauthorizedException catch (e) {
      return Left(Failure.unauthorized(message: e.message));
    } on ForbiddenException catch (e) {
      // Surfaces the backend's "verify your email" / "pending approval" detail.
      return Left(Failure.forbidden(message: e.message));
    } on ValidationException catch (e) {
      return Left(Failure.validation(message: e.message));
    } catch (e) {
      return Left(Failure.unknown(message: e.toString()));
    }
  }

  @override
  Future<Either<Failure, User>> register({
    required String email,
    required String password,
    required String firstName,
    required String lastName,
    String? phone,
    String userType = 'student',
  }) async {
    try {
      final response = await remoteDataSource.register(
        email: email,
        password: password,
        firstName: firstName,
        lastName: lastName,
        phone: phone,
        userType: userType,
      );

      // Mirror the account into Firebase Authentication so it appears in the
      // Firebase console. Done client-side (no service-account key needed).
      // Best-effort: registration already succeeded on the backend, so a
      // Firebase hiccup must NOT fail the whole registration.
      await _mirrorToFirebase(email: email, password: password);

      // Register returns top-level user fields only — NO tokens and no nested
      // 'user' key ({id, email, username, display_name, role, status, message,
      // requires_verification}). No tokens, so the user is NOT logged in here.
      //
      // requires_verification == false means AUTO_VERIFY made the account
      // active already → the UI can send the user straight to login. We carry
      // that signal on isActive (true = ready to sign in). Default to needing
      // verification when the backend is old and omits the field.
      final requiresVerification =
          response['requires_verification'] as bool? ?? true;
      final userModel = UserModel(
        id: response['id'].toString(),
        email: response['email'] as String? ?? email,
        firstName: firstName,
        lastName: lastName,
        role: response['role'] as String? ?? userType,
        phone: phone,
        isActive: !requiresVerification,
      );
      return Right(userModel.toEntity());
    } on ServerException catch (e) {
      // Backend rejected the register (e.g. 400 "email already exists"). Do NOT
      // mirror to Firebase here — creating a Firebase identity for a rejected
      // registration looks like "the account was created" while the popup says
      // it already exists. Pre-existing accounts get backfilled into Firebase
      // on their next successful LOGIN instead (see login()).
      return Left(Failure.server(message: e.message, statusCode: e.statusCode));
    } on NetworkException catch (e) {
      return Left(Failure.network(message: e.message));
    } on ValidationException catch (e) {
      return Left(Failure.validation(message: e.message));
    } catch (e) {
      return Left(Failure.unknown(message: e.toString()));
    }
  }

  @override
  Future<Either<Failure, void>> logout() async {
    try {
      await remoteDataSource.logout();
      await secureStorage.clearAuthData();
      return const Right(null);
    } catch (e) {
      await secureStorage.clearAuthData(); // Clear local data even if API call fails
      return const Right(null);
    }
  }

  @override
  Future<Either<Failure, User>> getCurrentUser() async {
    try {
      final user = await remoteDataSource.getCurrentUser();
      return Right(user.toEntity());
    } on ServerException catch (e) {
      return Left(Failure.server(message: e.message, statusCode: e.statusCode));
    } on UnauthorizedException catch (e) {
      await secureStorage.clearAuthData();
      return Left(Failure.unauthorized(message: e.message));
    } catch (e) {
      return Left(Failure.unknown(message: e.toString()));
    }
  }

  @override
  Future<Either<Failure, void>> refreshToken() async {
    try {
      final tokens = await remoteDataSource.refreshToken();
      await secureStorage.saveTokens(
        accessToken: tokens['access_token'],
        refreshToken: tokens['refresh_token'],
      );
      return const Right(null);
    } catch (e) {
      await secureStorage.clearAuthData();
      return Left(Failure.unknown(message: 'Failed to refresh token'));
    }
  }

  @override
  Future<Either<Failure, bool>> isLoggedIn() async {
    final token = await secureStorage.getAccessToken();
    return Right(token != null);
  }

  /// Create the matching user in Firebase Authentication so registered
  /// accounts show up under Firebase → Authentication → Users.
  ///
  /// Best-effort and never throws: the backend account is the source of truth,
  /// so any Firebase error (already exists, network, Firebase not configured)
  /// is logged and swallowed. We sign back out of Firebase afterward because
  /// the app's real session is the backend JWT, not the Firebase session that
  /// createUserWithEmailAndPassword would otherwise leave behind.
  Future<void> _mirrorToFirebase({
    required String email,
    required String password,
  }) async {
    if (!AppConfig.firebaseAvailable) return;
    try {
      await FirebaseAuth.instance.createUserWithEmailAndPassword(
        email: email,
        password: password,
      );
      await FirebaseAuth.instance.signOut();
    } on FirebaseAuthException catch (e) {
      // 'email-already-in-use' is fine — the Firebase user already exists.
      if (e.code != 'email-already-in-use' && kDebugMode) {
        debugPrint('[register] Firebase mirror failed: ${e.code} ${e.message}');
      }
    } catch (e) {
      if (kDebugMode) debugPrint('[register] Firebase mirror error: $e');
    }
  }

  Failure _mapException(Object e) {
    if (e is NetworkException) return Failure.network(message: e.message);
    if (e is UnauthorizedException) {
      return Failure.unauthorized(message: e.message);
    }
    if (e is ForbiddenException) return Failure.forbidden(message: e.message);
    if (e is NotFoundException) return Failure.notFound(message: e.message);
    if (e is ValidationException) {
      return Failure.validation(message: e.message, fieldErrors: e.fieldErrors);
    }
    if (e is ServerException) {
      return Failure.server(message: e.message, statusCode: e.statusCode);
    }
    return Failure.unknown(message: e.toString());
  }

  Future<Either<Failure, String>> _messageCall(
    Future<Map<String, dynamic>> Function() call, {
    required String fallbackMessage,
  }) async {
    try {
      final response = await call();
      return Right(response['message'] as String? ?? fallbackMessage);
    } catch (e) {
      return Left(_mapException(e));
    }
  }

  @override
  Future<Either<Failure, String>> forgotPassword({required String email}) async {
    const genericOk =
        'If an account exists for that email, a password reset link has been '
        'sent. Please check your inbox (and spam folder).';

    // Send the reset email via Firebase Authentication: reliable delivery with
    // no SMTP. The link opens Firebase's hosted reset page where the user sets
    // a new password, which then works for login (see login() — Firebase-first).
    if (!AppConfig.firebaseAvailable) {
      // Firebase not configured on this build — fall back to the backend flow.
      if (kDebugMode) {
        debugPrint('[forgotPassword] firebaseAvailable=false → backend SMTP '
            'fallback (no Firebase mail will be sent)');
      }
      return _messageCall(
        () => remoteDataSource.forgotPassword(email: email),
        fallbackMessage: genericOk,
      );
    }
    try {
      if (kDebugMode) debugPrint('[forgotPassword] sending Firebase reset email');
      await FirebaseAuth.instance.sendPasswordResetEmail(email: email.trim());
      if (kDebugMode) debugPrint('[forgotPassword] Firebase reset email OK');
      return const Right(genericOk);
    } on FirebaseAuthException catch (e) {
      if (kDebugMode) {
        debugPrint('[forgotPassword] FirebaseAuthException: ${e.code} — ${e.message}');
      }
      switch (e.code) {
        case 'user-not-found':
          // Don't reveal whether the account exists — return generic success.
          return const Right(genericOk);
        case 'invalid-email':
          return Left(
              Failure.validation(message: 'Please enter a valid email address.'));
        case 'too-many-requests':
          return Left(Failure.unknown(
              message: 'Too many attempts. Please try again in a few minutes.'));
        case 'network-request-failed':
          return Left(Failure.network(
              message: 'Network error. Check your connection and try again.'));
        default:
          return Left(Failure.unknown(
              message: e.message ?? 'Could not send the reset email.'));
      }
    } catch (e) {
      if (kDebugMode) debugPrint('[forgotPassword] unexpected error: $e');
      return Left(Failure.unknown(message: e.toString()));
    }
  }

  @override
  Future<Either<Failure, String>> resetPassword({
    required String token,
    required String newPassword,
  }) {
    return _messageCall(
      () => remoteDataSource.resetPassword(
        token: token,
        newPassword: newPassword,
      ),
      fallbackMessage: 'Password reset successfully',
    );
  }

  @override
  Future<Either<Failure, String>> verifyEmail({required String token}) {
    return _messageCall(
      () => remoteDataSource.verifyEmail(token: token),
      fallbackMessage: 'Email verified successfully.',
    );
  }

  @override
  Future<Either<Failure, String>> resendVerification({required String email}) {
    return _messageCall(
      () => remoteDataSource.resendVerification(email: email),
      fallbackMessage:
          'If the account exists and needs verification, a new email has been sent.',
    );
  }

  @override
  Future<Either<Failure, GoogleAuthResult>> loginWithGoogle({
    required String firebaseToken,
  }) async {
    try {
      final response =
          await remoteDataSource.googleLogin(firebaseToken: firebaseToken);

      if (response['new_user'] == true) {
        return Right(GoogleAuthResult.needsRole(
          email: response['email'] as String? ?? '',
          name: response['name'] as String? ?? '',
          picture: response['picture'] as String? ?? '',
          // Backend echoes the verified token back for the /complete step.
          firebaseToken: response['token'] as String? ?? firebaseToken,
        ));
      }

      await secureStorage.saveTokens(
        accessToken: response['access_token'],
        refreshToken: response['refresh_token'],
      );
      final userModel = UserModel.fromAuthResponse(response);
      return Right(GoogleAuthResult.signedIn(userModel.toEntity()));
    } catch (e) {
      return Left(_mapException(e));
    }
  }

  @override
  Future<Either<Failure, User>> completeGoogleSignIn({
    required String firebaseToken,
    required String role,
  }) async {
    try {
      final response = await remoteDataSource.googleComplete(
        firebaseToken: firebaseToken,
        role: role,
      );

      await secureStorage.saveTokens(
        accessToken: response['access_token'],
        refreshToken: response['refresh_token'],
      );
      final userModel = UserModel.fromAuthResponse(response);
      return Right(userModel.toEntity());
    } catch (e) {
      return Left(_mapException(e));
    }
  }
}
