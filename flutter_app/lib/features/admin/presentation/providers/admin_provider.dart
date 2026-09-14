// lib/features/admin/presentation/providers/admin_provider.dart
import 'package:riverpod_annotation/riverpod_annotation.dart';
import '../../../../core/network/network_provider.dart';
import '../../../../core/utils/failure_logger.dart';
import '../../data/datasources/admin_remote_datasource.dart';
import '../../data/repositories/admin_repository_impl.dart';
import '../../domain/repositories/admin_repository.dart';

part 'admin_provider.g.dart';

@riverpod
AdminRemoteDataSource adminRemoteDataSource(AdminRemoteDataSourceRef ref) {
  final apiClient = ref.watch(apiClientProvider);
  return AdminRemoteDataSourceImpl(apiClient: apiClient);
}

@riverpod
AdminRepository adminRepository(AdminRepositoryRef ref) {
  final remoteDataSource = ref.watch(adminRemoteDataSourceProvider);
  return AdminRepositoryImpl(remoteDataSource: remoteDataSource);
}

@riverpod
Future<Map<String, dynamic>> adminStats(
  AdminStatsRef ref, {
  String period = '30d',
}) async {
  final repository = ref.watch(adminRepositoryProvider);
  final result = await repository.getStats(period: period);
  return result.fold(
    (failure) {
      logFailure('admin stats', failure);
      throw failure;
    },
    (data) => data,
  );
}

@riverpod
Future<AdminUserListResult> adminStudents(
  AdminStudentsRef ref, {
  String? status,
  String? search,
  int skip = 0,
}) async {
  final repository = ref.watch(adminRepositoryProvider);
  final result = await repository.getUsers(
    role: 'student',
    status: status,
    search: search,
    skip: skip,
    limit: 50,
  );
  return result.fold(
    (failure) {
      logFailure('admin students', failure);
      throw failure;
    },
    (data) => data,
  );
}

@riverpod
Future<AdminUserListResult> adminInstructors(
  AdminInstructorsRef ref, {
  String? status,
  String? search,
  int skip = 0,
}) async {
  final repository = ref.watch(adminRepositoryProvider);
  final result = await repository.getUsers(
    role: 'instructor',
    status: status,
    search: search,
    skip: skip,
    limit: 50,
  );
  return result.fold(
    (failure) {
      logFailure('admin instructors', failure);
      throw failure;
    },
    (data) => data,
  );
}

@riverpod
Future<List<Map<String, dynamic>>> adminCourses(
  AdminCoursesRef ref, {
  String? status,
  int skip = 0,
}) async {
  final repository = ref.watch(adminRepositoryProvider);
  final result = await repository.getCourses(status: status, skip: skip);
  return result.fold(
    (failure) {
      logFailure('admin courses', failure);
      throw failure;
    },
    (data) => data,
  );
}

@riverpod
Future<List<Map<String, dynamic>>> adminOrders(
  AdminOrdersRef ref, {
  String? status,
  int skip = 0,
}) async {
  final repository = ref.watch(adminRepositoryProvider);
  final result = await repository.getOrders(status: status, skip: skip);
  return result.fold(
    (failure) {
      logFailure('admin orders', failure);
      throw failure;
    },
    (data) => data,
  );
}

@riverpod
Future<List<Map<String, dynamic>>> adminApplications(
  AdminApplicationsRef ref, {
  String status = 'pending',
}) async {
  final repository = ref.watch(adminRepositoryProvider);
  final result = await repository.getInstructorApplications(status: status);
  return result.fold(
    (failure) {
      logFailure('admin applications', failure);
      throw failure;
    },
    (data) => data,
  );
}
