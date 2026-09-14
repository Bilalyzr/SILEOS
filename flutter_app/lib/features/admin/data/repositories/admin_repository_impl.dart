// lib/features/admin/data/repositories/admin_repository_impl.dart
import 'package:dartz/dartz.dart';
import '../../../../core/errors/exceptions.dart';
import '../../../../core/errors/failures.dart';
import '../../domain/repositories/admin_repository.dart';
import '../datasources/admin_remote_datasource.dart';

class AdminRepositoryImpl implements AdminRepository {
  final AdminRemoteDataSource remoteDataSource;

  AdminRepositoryImpl({required this.remoteDataSource});

  @override
  Future<Either<Failure, Map<String, dynamic>>> getStats(
      {String period = '30d'}) async {
    try {
      final data = await remoteDataSource.getStats(period: period);
      return Right(data);
    } on ServerException catch (e) {
      return Left(Failure.server(message: e.message, statusCode: e.statusCode));
    } on NetworkException catch (e) {
      return Left(Failure.network(message: e.message));
    } catch (e) {
      return Left(Failure.unknown(message: e.toString()));
    }
  }

  @override
  Future<Either<Failure, AdminUserListResult>> getUsers({
    String? role,
    String? status,
    String? search,
    int skip = 0,
    int limit = 50,
  }) async {
    try {
      final result = await remoteDataSource.getUsers(
        role: role,
        status: status,
        search: search,
        skip: skip,
        limit: limit,
      );
      return Right(AdminUserListResult(
        users: result.users,
        totalCount: result.totalCount,
      ));
    } on ServerException catch (e) {
      return Left(Failure.server(message: e.message, statusCode: e.statusCode));
    } on NetworkException catch (e) {
      return Left(Failure.network(message: e.message));
    } catch (e) {
      return Left(Failure.unknown(message: e.toString()));
    }
  }

  @override
  Future<Either<Failure, Map<String, dynamic>>> getUserDetail(
      int userId) async {
    try {
      final data = await remoteDataSource.getUserDetail(userId);
      return Right(data);
    } on ServerException catch (e) {
      return Left(Failure.server(message: e.message, statusCode: e.statusCode));
    } on NetworkException catch (e) {
      return Left(Failure.network(message: e.message));
    } catch (e) {
      return Left(Failure.unknown(message: e.toString()));
    }
  }

  @override
  Future<Either<Failure, void>> updateUserStatus(
      int userId, String status) async {
    try {
      await remoteDataSource.updateUserStatus(userId, status);
      return const Right(null);
    } on ServerException catch (e) {
      return Left(Failure.server(message: e.message, statusCode: e.statusCode));
    } on NetworkException catch (e) {
      return Left(Failure.network(message: e.message));
    } catch (e) {
      return Left(Failure.unknown(message: e.toString()));
    }
  }

  @override
  Future<Either<Failure, void>> deleteUser(int userId) async {
    try {
      await remoteDataSource.deleteUser(userId);
      return const Right(null);
    } on ServerException catch (e) {
      return Left(Failure.server(message: e.message, statusCode: e.statusCode));
    } on NetworkException catch (e) {
      return Left(Failure.network(message: e.message));
    } catch (e) {
      return Left(Failure.unknown(message: e.toString()));
    }
  }

  @override
  Future<Either<Failure, List<Map<String, dynamic>>>> getCourses({
    String? status,
    int? instructorId,
    int skip = 0,
    int limit = 50,
  }) async {
    try {
      final data = await remoteDataSource.getCourses(
        status: status,
        instructorId: instructorId,
        skip: skip,
        limit: limit,
      );
      return Right(data);
    } on ServerException catch (e) {
      return Left(Failure.server(message: e.message, statusCode: e.statusCode));
    } on NetworkException catch (e) {
      return Left(Failure.network(message: e.message));
    } catch (e) {
      return Left(Failure.unknown(message: e.toString()));
    }
  }

  @override
  Future<Either<Failure, void>> updateCourseStatus(
      int courseId, String status) async {
    try {
      await remoteDataSource.updateCourseStatus(courseId, status);
      return const Right(null);
    } on ServerException catch (e) {
      return Left(Failure.server(message: e.message, statusCode: e.statusCode));
    } on NetworkException catch (e) {
      return Left(Failure.network(message: e.message));
    } catch (e) {
      return Left(Failure.unknown(message: e.toString()));
    }
  }

  @override
  Future<Either<Failure, List<Map<String, dynamic>>>>
      getInstructorApplications({String status = 'pending'}) async {
    try {
      final data = await remoteDataSource.getInstructorApplications(status: status);
      return Right(data);
    } on ServerException catch (e) {
      return Left(Failure.server(message: e.message, statusCode: e.statusCode));
    } on NetworkException catch (e) {
      return Left(Failure.network(message: e.message));
    } catch (e) {
      return Left(Failure.unknown(message: e.toString()));
    }
  }

  @override
  Future<Either<Failure, void>> processInstructorApplication(
      int applicationId, String action) async {
    try {
      await remoteDataSource.processInstructorApplication(applicationId, action);
      return const Right(null);
    } on ServerException catch (e) {
      return Left(Failure.server(message: e.message, statusCode: e.statusCode));
    } on NetworkException catch (e) {
      return Left(Failure.network(message: e.message));
    } catch (e) {
      return Left(Failure.unknown(message: e.toString()));
    }
  }

  @override
  Future<Either<Failure, List<Map<String, dynamic>>>> getOrders({
    String? status,
    int skip = 0,
    int limit = 50,
  }) async {
    try {
      final data = await remoteDataSource.getOrders(
        status: status,
        skip: skip,
        limit: limit,
      );
      return Right(data);
    } on ServerException catch (e) {
      return Left(Failure.server(message: e.message, statusCode: e.statusCode));
    } on NetworkException catch (e) {
      return Left(Failure.network(message: e.message));
    } catch (e) {
      return Left(Failure.unknown(message: e.toString()));
    }
  }
}
