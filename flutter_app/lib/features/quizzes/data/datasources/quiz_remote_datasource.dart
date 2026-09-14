import 'package:dio/dio.dart';
import '../../../../core/network/api_client.dart';
import '../../../../core/errors/exceptions.dart';
import '../models/quiz_model.dart';

abstract class QuizRemoteDataSource {
  Future<QuizModel> getQuiz({
    required int courseId,
    required int quizId,
  });

  Future<Map<String, dynamic>> submitQuiz({
    required int courseId,
    required int quizId,
    required Map<String, dynamic> answers,
  });

  Future<Map<String, dynamic>> startQuizAttempt(int quizId);
  
  Future<Map<String, dynamic>> submitQuizAttempt({
    required int attemptId,
    required Map<String, dynamic> answers,
  });
}

class QuizRemoteDataSourceImpl implements QuizRemoteDataSource {
  final ApiClient apiClient;

  QuizRemoteDataSourceImpl({required this.apiClient});

  @override
  Future<QuizModel> getQuiz({
    required int courseId,
    required int quizId,
  }) async {
    try {
      final response = await apiClient.get('/api/v1/courses/$courseId/quizzes/$quizId');

      if (response.statusCode == 200) {
        return QuizModel.fromJson(response.data);
      } else {
        throw ServerException(
          'Failed to load quiz',
          statusCode: response.statusCode,
        );
      }
    } on DioException catch (e) {
      throw AppExceptionFromDio.fromDioError(e);
    }
  }

  @override
  Future<Map<String, dynamic>> submitQuiz({
    required int courseId,
    required int quizId,
    required Map<String, dynamic> answers,
  }) async {
    try {
      final response = await apiClient.post(
        '/api/v1/courses/$courseId/quizzes/$quizId/submit',
        data: {'answers': answers},
      );

      if (response.statusCode == 200) {
        return response.data;
      } else {
        throw ServerException(
          'Failed to submit quiz',
          statusCode: response.statusCode,
        );
      }
    } on DioException catch (e) {
      throw AppExceptionFromDio.fromDioError(e);
    }
  }

  @override
  Future<Map<String, dynamic>> startQuizAttempt(int quizId) async {
    try {
      final response = await apiClient.post('/api/v1/quizzes/$quizId/start');
      if (response.statusCode == 200 || response.statusCode == 201) {
        return response.data;
      } else {
        throw ServerException('Failed to start quiz attempt');
      }
    } on DioException catch (e) {
      throw AppExceptionFromDio.fromDioError(e);
    }
  }

  @override
  Future<Map<String, dynamic>> submitQuizAttempt({
    required int attemptId,
    required Map<String, dynamic> answers,
  }) async {
    try {
      final response = await apiClient.post(
        '/api/v1/quiz-attempts/$attemptId/submit',
        data: {'answers': answers},
      );
      if (response.statusCode == 200) {
        return response.data;
      } else {
        throw ServerException('Failed to submit quiz attempt');
      }
    } on DioException catch (e) {
      throw AppExceptionFromDio.fromDioError(e);
    }
  }
}
