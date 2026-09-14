// lib/features/auth/data/datasources/auth_remote_datasource.dart
import 'package:dio/dio.dart';
import '../../../../core/constants/api_endpoints.dart';
import '../../../../core/network/api_client.dart';
import '../../../../core/errors/exceptions.dart';
import '../models/user_model.dart';

abstract class AuthRemoteDataSource {
  Future<Map<String, dynamic>> login({
    required String email,
    required String password,
  });

  Future<Map<String, dynamic>> register({
    required String email,
    required String password,
    required String firstName,
    required String lastName,
    String? phone,
    String userType = 'student',
  });

  Future<void> logout();

  Future<UserModel> getCurrentUser();

  Future<Map<String, dynamic>> refreshToken();

  Future<Map<String, dynamic>> forgotPassword({required String email});

  Future<Map<String, dynamic>> resetPassword({
    required String token,
    required String newPassword,
  });

  Future<Map<String, dynamic>> verifyEmail({required String token});

  Future<Map<String, dynamic>> resendVerification({required String email});

  Future<Map<String, dynamic>> googleLogin({required String firebaseToken});

  Future<Map<String, dynamic>> googleComplete({
    required String firebaseToken,
    required String role,
  });

  Future<Map<String, dynamic>> linkedinLogin({required String code});
}

class AuthRemoteDataSourceImpl implements AuthRemoteDataSource {
  final ApiClient apiClient;

  AuthRemoteDataSourceImpl({required this.apiClient});

  @override
  Future<Map<String, dynamic>> login({
    required String email,
    required String password,
  }) async {
    try {
      final response = await apiClient.post(
        '/api/v1/auth/login',
        data: {
          'email': email,
          'password': password,
        },
      );

      if (response.statusCode == 200) {
        return response.data as Map<String, dynamic>;
      } else {
        throw ServerException(
          response.data['detail'] ?? 'Login failed',
          statusCode: response.statusCode,
        );
      }
    } on DioException catch (e) {
      throw AppExceptionFromDio.fromDioError(e);
    }
  }

  @override
  Future<Map<String, dynamic>> register({
    required String email,
    required String password,
    required String firstName,
    required String lastName,
    String? phone,
    String userType = 'student',
  }) async {
    try {
      final response = await apiClient.post(
        '/api/v1/auth/register',
        data: {
          'email': email,
          'password': password,
          'first_name': firstName,
          'last_name': lastName,
          'user_type': userType,
          if (phone != null) 'phone': phone,
        },
      );

      if (response.statusCode == 201 || response.statusCode == 200) {
        return response.data as Map<String, dynamic>;
      } else {
        throw ServerException(
          response.data['detail'] ?? 'Registration failed',
          statusCode: response.statusCode,
        );
      }
    } on DioException catch (e) {
      throw AppExceptionFromDio.fromDioError(e);
    }
  }

  @override
  Future<void> logout() async {
    try {
      await apiClient.post('/api/v1/auth/logout');
    } on DioException catch (e) {
      throw AppExceptionFromDio.fromDioError(e);
    }
  }

  @override
  Future<UserModel> getCurrentUser() async {
    try {
      final response = await apiClient.get('/api/v1/auth/me');

      if (response.statusCode == 200) {
        return UserModel.fromJson(response.data);
      } else {
        throw ServerException(
          'Failed to get user',
          statusCode: response.statusCode,
        );
      }
    } on DioException catch (e) {
      throw AppExceptionFromDio.fromDioError(e);
    }
  }

  @override
  Future<Map<String, dynamic>> refreshToken() async {
    try {
      final response = await apiClient.post('/api/v1/auth/refresh');

      if (response.statusCode == 200) {
        return response.data;
      } else {
        throw ServerException(
          'Failed to refresh token',
          statusCode: response.statusCode,
        );
      }
    } on DioException catch (e) {
      throw AppExceptionFromDio.fromDioError(e);
    }
  }

  Future<Map<String, dynamic>> _postForMessage(
    String path,
    Map<String, dynamic> data,
  ) async {
    try {
      final response = await apiClient.post(path, data: data);
      return response.data as Map<String, dynamic>;
    } on DioException catch (e) {
      throw AppExceptionFromDio.fromDioError(e);
    }
  }

  @override
  Future<Map<String, dynamic>> forgotPassword({required String email}) {
    return _postForMessage(ApiEndpoints.forgotPassword, {'email': email});
  }

  @override
  Future<Map<String, dynamic>> resetPassword({
    required String token,
    required String newPassword,
  }) {
    return _postForMessage(ApiEndpoints.resetPassword, {
      'token': token,
      'newPassword': newPassword,
    });
  }

  @override
  Future<Map<String, dynamic>> verifyEmail({required String token}) {
    return _postForMessage(ApiEndpoints.verifyEmail, {'token': token});
  }

  @override
  Future<Map<String, dynamic>> resendVerification({required String email}) {
    return _postForMessage(ApiEndpoints.resendVerification, {'email': email});
  }

  @override
  Future<Map<String, dynamic>> googleLogin({required String firebaseToken}) {
    return _postForMessage(ApiEndpoints.googleAuth, {'token': firebaseToken});
  }

  @override
  Future<Map<String, dynamic>> googleComplete({
    required String firebaseToken,
    required String role,
  }) {
    return _postForMessage(ApiEndpoints.googleComplete, {
      'google_token': firebaseToken,
      'role': role,
    });
  }

  @override
  Future<Map<String, dynamic>> linkedinLogin({required String code}) {
    return _postForMessage(ApiEndpoints.linkedinAuth, {'code': code});
  }
}
