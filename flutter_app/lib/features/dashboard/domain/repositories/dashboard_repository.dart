import 'package:dartz/dartz.dart';
import '../../../../core/errors/failures.dart';
import '../entities/dashboard_data.dart';

abstract class DashboardRepository {
  Future<Either<Failure, DashboardData>> getStudentDashboard();
  Future<Either<Failure, Map<String, dynamic>>> getInstructorDashboard();
  Future<Either<Failure, Map<String, dynamic>>> getAdminDashboard();
}
