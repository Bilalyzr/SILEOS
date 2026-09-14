import 'package:dio/dio.dart';

abstract class AppException implements Exception {
  final String message;
  final int? statusCode;

  const AppException(this.message, {this.statusCode});

  @override
  String toString() => message;
}

class ServerException extends AppException {
  const ServerException(super.message, {super.statusCode});
}

class NetworkException extends AppException {
  const NetworkException(super.message) : super(statusCode: null);
}

class CacheException extends AppException {
  const CacheException(super.message);
}

class UnauthorizedException extends AppException {
  const UnauthorizedException([String message = 'Unauthorized'])
      : super(message, statusCode: 401);
}

class ForbiddenException extends AppException {
  const ForbiddenException([String message = 'Forbidden'])
      : super(message, statusCode: 403);
}

class NotFoundException extends AppException {
  const NotFoundException([String message = 'Not found'])
      : super(message, statusCode: 404);
}

class ValidationException extends AppException {
  final Map<String, dynamic>? fieldErrors;

  const ValidationException(
    super.message, {
    super.statusCode,
    this.fieldErrors,
  });
}

class AppExceptionFromDio {
  static AppException fromDioError(DioException error) {
    switch (error.type) {
      case DioExceptionType.connectionTimeout:
      case DioExceptionType.sendTimeout:
      case DioExceptionType.receiveTimeout:
        return const NetworkException('Connection timeout');

      case DioExceptionType.connectionError:
        return const NetworkException('No internet connection');

      case DioExceptionType.badResponse:
        final statusCode = error.response?.statusCode;
        // FastAPI usually returns {"detail": "..."} but some endpoints (e.g. the
        // 402 payment-required response) return a structured object as `detail`
        // ({"message": ..., "requires_payment": true}). Coerce to a String so we
        // never hand a Map to ServerException(String message) — doing so threw
        // "_Map is not a subtype of String", collapsing a 402 into Failure.unknown
        // and breaking the paid-course checkout flow.
        final rawDetail = error.response?.data is Map
            ? (error.response?.data as Map)['detail']
            : null;
        final String message = rawDetail is String
            ? rawDetail
            : rawDetail is Map && rawDetail['message'] is String
                ? rawDetail['message'] as String
                : error.response?.statusMessage ?? 'An error occurred';

        switch (statusCode) {
          case 401:
            return UnauthorizedException(message);
          case 403:
            return ForbiddenException(message);
          case 404:
            return NotFoundException(message);
          case 422:
            return ValidationException(
              message,
              fieldErrors: error.response?.data is Map
                  ? Map<String, dynamic>.from(error.response?.data ?? {})
                  : null,
            );
          default:
            return ServerException(message, statusCode: statusCode);
        }

      case DioExceptionType.cancel:
        return const NetworkException('Request cancelled');

      case DioExceptionType.unknown:
      default:
        return const NetworkException('Unexpected error occurred');
    }
  }
}
