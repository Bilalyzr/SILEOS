// lib/features/admin/domain/repositories/admin_repository.dart
import 'package:dartz/dartz.dart';
import '../../../../core/errors/failures.dart';

/// Result wrapper for paginated user list queries.
class AdminUserListResult {
  final List<Map<String, dynamic>> users;
  final int totalCount;
  AdminUserListResult({required this.users, required this.totalCount});
}

abstract class AdminRepository {
  Future<Either<Failure, Map<String, dynamic>>> getStats(
      {String period = '30d'});

  Future<Either<Failure, AdminUserListResult>> getUsers({
    String? role,
    String? status,
    String? search,
    int skip = 0,
    int limit = 50,
  });

  Future<Either<Failure, Map<String, dynamic>>> getUserDetail(int userId);
  Future<Either<Failure, void>> updateUserStatus(int userId, String status);
  Future<Either<Failure, void>> deleteUser(int userId);

  Future<Either<Failure, List<Map<String, dynamic>>>> getCourses({
    String? status,
    int? instructorId,
    int skip = 0,
    int limit = 50,
  });

  Future<Either<Failure, void>> updateCourseStatus(
      int courseId, String status);

  Future<Either<Failure, List<Map<String, dynamic>>>>
      getInstructorApplications({String status = 'pending'});

  Future<Either<Failure, void>> processInstructorApplication(
      int applicationId, String action);

  Future<Either<Failure, List<Map<String, dynamic>>>> getOrders({
    String? status,
    int skip = 0,
    int limit = 50,
  });
}
