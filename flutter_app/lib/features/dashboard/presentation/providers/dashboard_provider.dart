import 'package:riverpod_annotation/riverpod_annotation.dart';
import '../../../../core/network/network_provider.dart';
import '../../../../core/utils/failure_logger.dart';
import '../../domain/entities/dashboard_data.dart';
import '../../data/datasources/dashboard_remote_datasource.dart';
import '../../data/repositories/dashboard_repository_impl.dart';
import '../../domain/repositories/dashboard_repository.dart';

part 'dashboard_provider.g.dart';

@riverpod
DashboardRemoteDataSource dashboardRemoteDataSource(DashboardRemoteDataSourceRef ref) {
  final apiClient = ref.watch(apiClientProvider);
  return DashboardRemoteDataSourceImpl(apiClient: apiClient);
}

@riverpod
DashboardRepository dashboardRepository(DashboardRepositoryRef ref) {
  final remoteDataSource = ref.watch(dashboardRemoteDataSourceProvider);
  return DashboardRepositoryImpl(remoteDataSource: remoteDataSource);
}

@riverpod
Future<DashboardData> studentDashboard(StudentDashboardRef ref) async {
  final repository = ref.watch(dashboardRepositoryProvider);
  final result = await repository.getStudentDashboard();

  return result.fold(
    (failure) {
      logFailure('student dashboard', failure);
      throw failure;
    },
    (data) => data,
  );
}

@riverpod
Future<Map<String, dynamic>> instructorDashboard(
    InstructorDashboardRef ref) async {
  final repository = ref.watch(dashboardRepositoryProvider);
  final result = await repository.getInstructorDashboard();

  return result.fold(
    (failure) {
      logFailure('instructor dashboard', failure);
      throw failure;
    },
    (data) => data,
  );
}

@riverpod
Future<Map<String, dynamic>> adminDashboard(AdminDashboardRef ref) async {
  final repository = ref.watch(dashboardRepositoryProvider);
  final result = await repository.getAdminDashboard();

  return result.fold(
    (failure) {
      logFailure('admin dashboard', failure);
      throw failure;
    },
    (data) => data,
  );
}
