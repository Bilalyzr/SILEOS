import 'package:dartz/dartz.dart';
import '../../../../core/errors/failures.dart';
import '../entities/user.dart';
import '../repositories/auth_repository.dart';

class RegisterUseCase {
  final AuthRepository repository;

  RegisterUseCase(this.repository);

  Future<Either<Failure, User>> call({
    required String email,
    required String password,
    required String firstName,
    required String lastName,
    String? phone,
    String userType = 'student',
  }) {
    return repository.register(
      email: email,
      password: password,
      firstName: firstName,
      lastName: lastName,
      phone: phone,
      userType: userType,
    );
  }
}
