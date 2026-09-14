// lib/features/live_classes/data/live_class_api.dart
import 'package:dio/dio.dart';
import '../../../core/network/api_client.dart';
import '../../../core/constants/api_endpoints.dart';
import '../../../core/errors/exceptions.dart';
import 'models/live_class_model.dart';

/// Thin dio-backed data source for /api/v1/live/*. Mirrors
/// CourseRemoteDataSource / AssignmentRemoteDataSource conventions: try/catch
/// DioException -> AppExceptionFromDio, status-code check on success.
abstract class LiveClassApi {
  Future<List<LiveClassModel>> getClasses({String scope = 'upcoming'});

  Future<LiveClassModel> getClassById(int id);

  Future<List<LiveClassModel>> getLiveNow();

  Future<LiveClassJoinTokenModel> joinToken(int classId);

  Future<void> heartbeat(int classId);

  Future<LiveClassRecordingPlaybackModel?> getRecordingPlayback(int classId);
}

class LiveClassApiImpl implements LiveClassApi {
  final ApiClient apiClient;

  LiveClassApiImpl({required this.apiClient});

  @override
  Future<List<LiveClassModel>> getClasses({String scope = 'upcoming'}) async {
    try {
      final response = await apiClient.get(
        ApiEndpoints.liveClasses,
        queryParameters: {'scope': scope},
      );

      if (response.statusCode == 200) {
        // Backend returns {items: [...], server_ts}. Each item does not
        // repeat server_ts in list responses today, but LiveClassModel makes
        // server_ts required — inject it from the envelope if a row omits it
        // so parsing never throws on the list endpoint.
        final data = response.data as Map<String, dynamic>;
        final serverTs = data['server_ts'] as String?;
        final items = (data['items'] as List? ?? []);
        return items.map((raw) {
          final item = Map<String, dynamic>.from(raw as Map);
          item['server_ts'] ??= serverTs ?? DateTime.now().toUtc().toIso8601String();
          return LiveClassModel.fromJson(item);
        }).toList();
      }
      throw ServerException('Failed to load live classes', statusCode: response.statusCode);
    } on DioException catch (e) {
      throw AppExceptionFromDio.fromDioError(e);
    }
  }

  @override
  Future<LiveClassModel> getClassById(int id) async {
    try {
      final response = await apiClient.get(ApiEndpoints.liveClassDetail(id));
      if (response.statusCode == 200) {
        return LiveClassModel.fromJson(response.data as Map<String, dynamic>);
      }
      throw ServerException('Failed to load class details', statusCode: response.statusCode);
    } on DioException catch (e) {
      throw AppExceptionFromDio.fromDioError(e);
    }
  }

  @override
  Future<List<LiveClassModel>> getLiveNow() async {
    try {
      final response = await apiClient.get(ApiEndpoints.liveNow);
      if (response.statusCode == 200) {
        final data = response.data;
        final items = data is Map ? (data['items'] as List? ?? []) : (data as List);
        final serverTs = data is Map ? data['server_ts'] as String? : null;
        return items.map((raw) {
          final item = Map<String, dynamic>.from(raw as Map);
          item['server_ts'] ??= serverTs ?? DateTime.now().toUtc().toIso8601String();
          return LiveClassModel.fromJson(item);
        }).toList();
      }
      throw ServerException('Failed to load live-now classes', statusCode: response.statusCode);
    } on DioException catch (e) {
      throw AppExceptionFromDio.fromDioError(e);
    }
  }

  @override
  Future<LiveClassJoinTokenModel> joinToken(int classId) async {
    try {
      final response = await apiClient.post(ApiEndpoints.liveClassJoinToken(classId));
      if (response.statusCode == 200) {
        return LiveClassJoinTokenModel.fromJson(response.data as Map<String, dynamic>);
      }
      throw ServerException(
        (response.data is Map ? response.data['detail']?.toString() : null) ??
            'Failed to get join token',
        statusCode: response.statusCode,
      );
    } on DioException catch (e) {
      throw AppExceptionFromDio.fromDioError(e);
    }
  }

  @override
  Future<void> heartbeat(int classId) async {
    try {
      final response = await apiClient.post(
        ApiEndpoints.liveClassHeartbeat(classId),
        data: {'client_ts': DateTime.now().toUtc().toIso8601String()},
      );
      if (response.statusCode != 200) {
        throw ServerException('Heartbeat failed', statusCode: response.statusCode);
      }
    } on DioException catch (e) {
      throw AppExceptionFromDio.fromDioError(e);
    }
  }

  @override
  Future<LiveClassRecordingPlaybackModel?> getRecordingPlayback(int classId) async {
    try {
      final response = await apiClient.get(ApiEndpoints.liveClassRecordingPlayback(classId));
      if (response.statusCode == 200) {
        return LiveClassRecordingPlaybackModel.fromJson(response.data as Map<String, dynamic>);
      }
      return null;
    } on DioException catch (e) {
      // 503 = recording not configured, 404 = not available yet — both are
      // "no playback right now", not an app error.
      final code = e.response?.statusCode;
      if (code == 503 || code == 404) return null;
      throw AppExceptionFromDio.fromDioError(e);
    }
  }
}
