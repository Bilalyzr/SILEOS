import 'dart:io';
import 'package:dio/dio.dart';
import '../../../../core/network/api_client.dart';
import '../../../../core/errors/exceptions.dart';
import '../models/assignment_model.dart';

abstract class AssignmentRemoteDataSource {
  Future<AssignmentModel> getAssignment(int id);
  Future<AssignmentSubmissionModel> submitAssignment({
    required int assignmentId,
    required String content,
    File? file,
  });
}

class AssignmentRemoteDataSourceImpl implements AssignmentRemoteDataSource {
  final ApiClient apiClient;

  AssignmentRemoteDataSourceImpl({required this.apiClient});

  @override
  Future<AssignmentModel> getAssignment(int id) async {
    try {
      final response = await apiClient.get('/api/v1/assignments/$id');
      if (response.statusCode == 200) {
        return AssignmentModel.fromJson(response.data);
      } else {
        throw ServerException('Failed to load assignment');
      }
    } on DioException catch (e) {
      throw AppExceptionFromDio.fromDioError(e);
    }
  }

  @override
  Future<AssignmentSubmissionModel> submitAssignment({
    required int assignmentId,
    required String content,
    File? file,
  }) async {
    try {
      final formData = FormData.fromMap({
        'content': content,
        if (file != null)
          'file': await MultipartFile.fromFile(
            file.path,
            filename: file.path.split('/').last,
          ),
      });

      final response = await apiClient.post(
        '/api/v1/assignments/$assignmentId/submit',
        data: formData,
      );

      if (response.statusCode == 200 || response.statusCode == 201) {
        return AssignmentSubmissionModel.fromJson(response.data);
      } else {
        throw ServerException('Failed to submit assignment');
      }
    } on DioException catch (e) {
      throw AppExceptionFromDio.fromDioError(e);
    }
  }
}
