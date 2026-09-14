import 'package:flutter_test/flutter_test.dart';
import 'package:mockito/mockito.dart';
import 'package:mockito/annotations.dart';
import 'package:dartz/dartz.dart';
import 'package:sashalms/core/errors/exceptions.dart';
import 'package:sashalms/core/errors/failures.dart';
import 'package:sashalms/core/storage/secure_storage.dart';
import 'package:sashalms/features/auth/data/datasources/auth_remote_datasource.dart';
import 'package:sashalms/features/auth/data/repositories/auth_repository_impl.dart';
import 'package:sashalms/features/auth/data/models/user_model.dart';
import 'package:sashalms/features/auth/domain/entities/user.dart';

@GenerateNiceMocks([MockSpec<AuthRemoteDataSource>(), MockSpec<SecureStorage>()])
import 'auth_repository_test.mocks.dart';

void main() {
  late AuthRepositoryImpl repository;
  late MockAuthRemoteDataSource mockRemoteDataSource;
  late MockSecureStorage mockSecureStorage;

  setUp(() {
    mockRemoteDataSource = MockAuthRemoteDataSource();
    mockSecureStorage = MockSecureStorage();
    repository = AuthRepositoryImpl(
      remoteDataSource: mockRemoteDataSource,
      secureStorage: mockSecureStorage,
    );
  });

  group('login', () {
    const tEmail = 'test@example.com';
    const tPassword = 'password123';
    final tUserResponse = {
      'access_token': 'access_token',
      'refresh_token': 'refresh_token',
      'user': {
        'id': 1,
        'email': tEmail,
        'role': 'student',
      },
      'profile': {
        'first_name': 'Test',
        'last_name': 'User',
      }
    };
    final tUserModel = UserModel.fromAuthResponse(tUserResponse);
    final tUser = tUserModel.toEntity();

    test('should return remote data when the call to remote data source is successful', () async {
      // arrange
      when(mockRemoteDataSource.login(email: anyNamed('email'), password: anyNamed('password')))
          .thenAnswer((_) async => tUserResponse);
      when(mockSecureStorage.saveTokens(
        accessToken: anyNamed('accessToken'),
        refreshToken: anyNamed('refreshToken'),
      )).thenAnswer((_) async => Future.value());

      // act
      final result = await repository.login(email: tEmail, password: tPassword);

      // assert
      verify(mockRemoteDataSource.login(email: tEmail, password: tPassword));
      verify(mockSecureStorage.saveTokens(accessToken: 'access_token', refreshToken: 'refresh_token'));
      expect(result, equals(Right(tUser)));
    });

    test('should return ServerFailure when the call to remote data source is unsuccessful', () async {
      // arrange
      when(mockRemoteDataSource.login(email: anyNamed('email'), password: anyNamed('password')))
          .thenThrow(ServerException('Invalid credentials', statusCode: 401));

      // act
      final result = await repository.login(email: tEmail, password: tPassword);

      // assert
      verify(mockRemoteDataSource.login(email: tEmail, password: tPassword));
      verifyZeroInteractions(mockSecureStorage);
      expect(result, equals(Left(Failure.server(message: 'Invalid credentials', statusCode: 401))));
    });
  });
}
