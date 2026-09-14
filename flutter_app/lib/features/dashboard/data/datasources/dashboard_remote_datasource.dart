import 'package:dio/dio.dart';
import '../../../../core/network/api_client.dart';
import '../../../../core/errors/exceptions.dart';
import '../models/dashboard_model.dart';

abstract class DashboardRemoteDataSource {
  Future<DashboardModel> getStudentDashboard();
  Future<Map<String, dynamic>> getInstructorDashboard();
  Future<Map<String, dynamic>> getAdminDashboard();
}

class DashboardRemoteDataSourceImpl implements DashboardRemoteDataSource {
  final ApiClient apiClient;

  DashboardRemoteDataSourceImpl({required this.apiClient});

  @override
  Future<DashboardModel> getStudentDashboard() async {
    try {
      final response = await apiClient.get('/api/v1/dashboard/student');

      if (response.statusCode == 200) {
        return DashboardModel.fromJson(response.data);
      } else {
        throw ServerException(
          'Failed to load dashboard',
          statusCode: response.statusCode,
        );
      }
    } on DioException catch (e) {
      throw AppExceptionFromDio.fromDioError(e);
    }
  }

  @override
  Future<Map<String, dynamic>> getInstructorDashboard() async {
     try {
      final response = await apiClient.get('/api/v1/dashboard/instructor');

      if (response.statusCode == 200) {
        return response.data as Map<String, dynamic>;
      } else {
        throw ServerException(
          'Failed to load instructor dashboard',
          statusCode: response.statusCode,
        );
      }
    } on DioException catch (e) {
      throw AppExceptionFromDio.fromDioError(e);
    }
  }

  @override
  Future<Map<String, dynamic>> getAdminDashboard() async {
    try {
      final response = await apiClient.get('/api/v1/dashboard/admin');

      if (response.statusCode == 200) {
        return response.data as Map<String, dynamic>;
      } else {
        throw ServerException(
          'Failed to load admin dashboard',
          statusCode: response.statusCode,
        );
      }
    } on DioException catch (e) {
      throw AppExceptionFromDio.fromDioError(e);
    }
  }
}
