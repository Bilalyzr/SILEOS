// lib/features/admin/data/datasources/admin_remote_datasource.dart
import '../../../../core/constants/api_endpoints.dart';
import '../../../../core/network/api_client.dart';

abstract class AdminRemoteDataSource {
  Future<Map<String, dynamic>> getStats({String period = '30d'});

  /// Returns users list + total count from X-Total-Count header.
  Future<({List<Map<String, dynamic>> users, int totalCount})> getUsers({
    String? role,
    String? status,
    String? search,
    int skip = 0,
    int limit = 50,
  });

  Future<Map<String, dynamic>> getUserDetail(int userId);
  Future<void> updateUserStatus(int userId, String status);
  Future<void> deleteUser(int userId);

  Future<List<Map<String, dynamic>>> getCourses({
    String? status,
    int? instructorId,
    int skip = 0,
    int limit = 50,
  });

  Future<void> updateCourseStatus(int courseId, String status);

  Future<List<Map<String, dynamic>>> getInstructorApplications({
    String status = 'pending',
  });

  Future<void> processInstructorApplication(
      int applicationId, String action);

  Future<List<Map<String, dynamic>>> getOrders({
    String? status,
    int skip = 0,
    int limit = 50,
  });
}

class AdminRemoteDataSourceImpl implements AdminRemoteDataSource {
  final ApiClient apiClient;

  AdminRemoteDataSourceImpl({required this.apiClient});

  @override
  Future<Map<String, dynamic>> getStats({String period = '30d'}) async {
    final response =
        await apiClient.get('${ApiEndpoints.adminStats}?period=$period');
    return response.data as Map<String, dynamic>;
  }

  @override
  Future<({List<Map<String, dynamic>> users, int totalCount})> getUsers({
    String? role,
    String? status,
    String? search,
    int skip = 0,
    int limit = 50,
  }) async {
    final query = <String, dynamic>{};
    if (role != null) query['role'] = role;
    if (status != null) query['status'] = status;
    if (search != null) query['search'] = search;
    query['skip'] = skip;
    query['limit'] = limit;

    final response = await apiClient.get(
      ApiEndpoints.adminUsers,
      queryParameters: query,
    );

    final rawCount = response.headers.value('x-total-count');
    final totalCount = rawCount != null ? int.tryParse(rawCount) ?? 0 : 0;
    final users = (response.data as List?)?.cast<Map<String, dynamic>>() ?? [];

    return (users: users, totalCount: totalCount);
  }

  @override
  Future<Map<String, dynamic>> getUserDetail(int userId) async {
    final response = await apiClient.get(
      ApiEndpoints.adminUserDetail(userId),
    );
    return response.data as Map<String, dynamic>;
  }

  @override
  Future<void> updateUserStatus(int userId, String status) async {
    await apiClient.put(
      '${ApiEndpoints.adminUserStatus(userId)}?status=$status',
    );
  }

  @override
  Future<void> deleteUser(int userId) async {
    await apiClient.delete('/api/v1/admin/users/$userId');
  }

  @override
  Future<List<Map<String, dynamic>>> getCourses({
    String? status,
    int? instructorId,
    int skip = 0,
    int limit = 50,
  }) async {
    final query = <String, dynamic>{};
    if (status != null) query['status'] = status;
    if (instructorId != null) query['instructor_id'] = instructorId;
    query['skip'] = skip;
    query['limit'] = limit;

    final response = await apiClient.get(
      ApiEndpoints.adminCourses,
      queryParameters: query,
    );
    return (response.data as List?)?.cast<Map<String, dynamic>>() ?? [];
  }

  @override
  Future<void> updateCourseStatus(int courseId, String status) async {
    await apiClient.put(
      ApiEndpoints.adminCourseStatus(courseId),
      data: {'status': status},
    );
  }

  @override
  Future<List<Map<String, dynamic>>> getInstructorApplications({
    String status = 'pending',
  }) async {
    final response = await apiClient.get(
      '${ApiEndpoints.adminInstructorApplications}?status=$status',
    );
    return (response.data as List?)?.cast<Map<String, dynamic>>() ?? [];
  }

  @override
  Future<void> processInstructorApplication(
      int applicationId, String action) async {
    await apiClient.put(
      '${ApiEndpoints.adminInstructorApplicationAction(applicationId)}?action=$action',
    );
  }

  @override
  Future<List<Map<String, dynamic>>> getOrders({
    String? status,
    int skip = 0,
    int limit = 50,
  }) async {
    final query = <String, dynamic>{};
    if (status != null) query['status'] = status;
    query['skip'] = skip;
    query['limit'] = limit;

    final response = await apiClient.get(
      ApiEndpoints.adminOrders,
      queryParameters: query,
    );
    return (response.data as List?)?.cast<Map<String, dynamic>>() ?? [];
  }
}
