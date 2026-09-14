import 'package:dartz/dartz.dart';
import '../../../../core/errors/exceptions.dart';
import '../../../../core/errors/failures.dart';
import '../../domain/entities/dashboard_data.dart';
import '../../domain/repositories/dashboard_repository.dart';
import '../datasources/dashboard_remote_datasource.dart';

class DashboardRepositoryImpl implements DashboardRepository {
  final DashboardRemoteDataSource remoteDataSource;

  DashboardRepositoryImpl({required this.remoteDataSource});

  @override
  Future<Either<Failure, DashboardData>> getStudentDashboard() async {
    try {
      final model = await remoteDataSource.getStudentDashboard();
      return Right(model.toEntity());
    } on ServerException catch (e) {
      return Left(Failure.server(message: e.message, statusCode: e.statusCode));
    } on NetworkException catch (e) {
      return Left(Failure.network(message: e.message));
    } catch (e) {
      return Left(Failure.unknown(message: e.toString()));
    }
  }

  @override
  Future<Either<Failure, Map<String, dynamic>>> getInstructorDashboard() async {
    try {
      final data = await remoteDataSource.getInstructorDashboard();
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
  Future<Either<Failure, Map<String, dynamic>>> getAdminDashboard() async {
    try {
      final data = await remoteDataSource.getAdminDashboard();
      return Right(data);
    } on ServerException catch (e) {
      return Left(Failure.server(message: e.message, statusCode: e.statusCode));
    } on NetworkException catch (e) {
      return Left(Failure.network(message: e.message));
    } on ForbiddenException catch (e) {
      return Left(Failure.forbidden(message: e.message));
    } catch (e) {
      return Left(Failure.unknown(message: e.toString()));
    }
  }
}
