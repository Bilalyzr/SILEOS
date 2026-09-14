import 'package:dartz/dartz.dart';
import '../../../../core/errors/failures.dart';
import '../entities/google_auth_result.dart';
import '../entities/user.dart';

abstract class AuthRepository {
  Future<Either<Failure, User>> login({
    required String email,
    required String password,
  });

  Future<Either<Failure, User>> register({
    required String email,
    required String password,
    required String firstName,
    required String lastName,
    String? phone,
    String userType = 'student',
  });

  Future<Either<Failure, void>> logout();
  Future<Either<Failure, User>> getCurrentUser();
  Future<Either<Failure, void>> refreshToken();
  Future<Either<Failure, bool>> isLoggedIn();

  /// All four return the backend's confirmation message.
  Future<Either<Failure, String>> forgotPassword({required String email});
  Future<Either<Failure, String>> resetPassword({
    required String token,
    required String newPassword,
  });
  Future<Either<Failure, String>> verifyEmail({required String token});
  Future<Either<Failure, String>> resendVerification({required String email});

  Future<Either<Failure, GoogleAuthResult>> loginWithGoogle({
    required String firebaseToken,
  });
  Future<Either<Failure, User>> completeGoogleSignIn({
    required String firebaseToken,
    required String role,
  });
}
