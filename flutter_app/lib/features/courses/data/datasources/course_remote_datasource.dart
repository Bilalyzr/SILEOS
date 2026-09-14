import 'package:dio/dio.dart';
import '../../../../core/network/api_client.dart';
import '../../../../core/constants/api_endpoints.dart';
import '../../../../core/errors/exceptions.dart';
import '../models/course_model.dart';
import '../models/lesson_model.dart';

abstract class CourseRemoteDataSource {
  Future<PaginatedCoursesModel> getCourses({
    int page = 1,
    int pageSize = 20,
    String? category,
    String? search,
    String? level,
    String? priceType,
    String? sortBy,
  });

  Future<CourseModel> getCourseById(String id);

  Future<LessonModel> getLessonById(String id);

  /// Exchange a Bunny.net video GUID for a (possibly signed) HLS playback URL.
  /// When [preview] is true, the public preview endpoint is used (no
  /// enrollment required); otherwise the enrollment-gated endpoint is used.
  Future<String?> getBunnyPlaybackUrl(String videoId, {bool preview = false});

  Future<void> completeLesson({
    required int courseId,
    required int lessonId,
  });

  Future<Map<String, dynamic>?> getCertificateForCourse(int courseId);

  Future<void> enroll(int courseId, {String? couponCode});

  Future<Map<String, dynamic>> createPaymentOrder(int courseId, {String? couponCode});

  Future<void> verifyPayment(Map<String, dynamic> paymentData);

  /// Validates a coupon against a course + amount. Returns the raw backend
  /// response ({valid, message, discount_amount, final_amount, ...}).
  Future<Map<String, dynamic>> validateCoupon({
    required String code,
    required int courseId,
    required double totalAmount,
  });
}

class CourseRemoteDataSourceImpl implements CourseRemoteDataSource {
  final ApiClient apiClient;

  CourseRemoteDataSourceImpl({required this.apiClient});

  @override
  Future<PaginatedCoursesModel> getCourses({
    int page = 1,
    int pageSize = 20,
    String? category,
    String? search,
    String? level,
    String? priceType,
    String? sortBy,
  }) async {
    try {
      // Trailing slash is required: the backend runs with redirect_slashes=False
      // and only registers GET at "/api/v1/courses/" (without it the API returns 405).
      final response = await apiClient.get(
        '/api/v1/courses/',
        queryParameters: {
          'page': page,
          'page_size': pageSize,
          if (category != null) 'category': category,
          if (search != null) 'search': search,
          if (level != null) 'level': level,
          if (priceType != null) 'price_type': priceType,
          if (sortBy != null) 'sort': sortBy == 'newest' ? 'latest' : sortBy,
        },
      );

      if (response.statusCode == 200) {
        // Some backends return the array directly, others wrap in { 'courses': [...] }
        final Map<String, dynamic> data = response.data is Map ? response.data : {'courses': response.data};
        if (!data.containsKey('total')) {
           // Provide defaults if pagination metadata is missing
           data['total'] = (data['courses'] as List).length;
           data['page'] = page;
           data['page_size'] = pageSize;
           data['total_pages'] = 1;
        }
        return PaginatedCoursesModel.fromJson(data);
      } else {
        throw ServerException(
          'Failed to load courses',
          statusCode: response.statusCode,
        );
      }
    } on DioException catch (e) {
      throw AppExceptionFromDio.fromDioError(e);
    }
  }

  @override
  Future<CourseModel> getCourseById(String id) async {
    try {
      // Ensure path is clean
      final response = await apiClient.get('/api/v1/courses/$id');

      if (response.statusCode == 200) {
        // The detail payload embeds lessons without `course_id` / `order`,
        // both of which LessonModel requires. Inject them so parsing doesn't
        // throw ("type 'Null' is not a subtype of type 'num'").
        final data = response.data;
        if (data is Map && data['lessons'] is List) {
          final lessons = data['lessons'] as List;
          for (var i = 0; i < lessons.length; i++) {
            final lesson = lessons[i];
            if (lesson is Map) {
              lesson['course_id'] ??= data['id'];
              lesson['order'] ??= i + 1;
            }
          }
        }
        return CourseModel.fromJson(Map<String, dynamic>.from(data as Map));
      } else {
        throw ServerException(
          'Failed to load course details',
          statusCode: response.statusCode,
        );
      }
    } on DioException catch (e) {
      throw AppExceptionFromDio.fromDioError(e);
    }
  }

  @override
  Future<LessonModel> getLessonById(String id) async {
    try {
      final response = await apiClient.get('/api/v1/lessons/$id');

      if (response.statusCode == 200) {
        return LessonModel.fromJson(response.data);
      } else {
        throw ServerException(
          'Failed to load lesson details',
          statusCode: response.statusCode,
        );
      }
    } on DioException catch (e) {
      throw AppExceptionFromDio.fromDioError(e);
    }
  }

  @override
  Future<String?> getBunnyPlaybackUrl(String videoId,
      {bool preview = false}) async {
    try {
      final response = await apiClient.get(preview
          ? ApiEndpoints.bunnyPreviewPlayback(videoId)
          : ApiEndpoints.bunnyPlayback(videoId));

      if (response.statusCode == 200) {
        return response.data['hls_url'] as String?;
      } else {
        throw ServerException(
          'Failed to load video playback URL',
          statusCode: response.statusCode,
        );
      }
    } on DioException catch (e) {
      throw AppExceptionFromDio.fromDioError(e);
    }
  }

  @override
  Future<void> completeLesson({
    required int courseId,
    required int lessonId,
  }) async {
    try {
      final response = await apiClient.post(
        '/api/v1/courses/$courseId/lessons/$lessonId/complete',
      );

      if (response.statusCode != 200) {
        throw ServerException(
          response.data['detail'] ?? 'Failed to mark lesson as complete',
          statusCode: response.statusCode,
        );
      }
    } on DioException catch (e) {
      throw AppExceptionFromDio.fromDioError(e);
    }
  }

  @override
  Future<Map<String, dynamic>?> getCertificateForCourse(int courseId) async {
    try {
      final response = await apiClient.get('/api/v1/certificates/course/$courseId');
      if (response.statusCode == 200) {
        return response.data as Map<String, dynamic>;
      }
      return null;
    } on DioException catch (e) {
      if (e.response?.statusCode == 404) return null;
      throw AppExceptionFromDio.fromDioError(e);
    }
  }

  @override
  Future<void> enroll(int courseId, {String? couponCode}) async {
    try {
      final response = await apiClient.post(
        '/api/v1/courses/$courseId/enroll',
        data: {
          if (couponCode != null) 'coupon_code': couponCode,
        },
      );

      if (response.statusCode != 200) {
        throw ServerException(
          response.data['detail'] ?? 'Failed to enroll in the course',
          statusCode: response.statusCode,
        );
      }
    } on DioException catch (e) {
      throw AppExceptionFromDio.fromDioError(e);
    }
  }

  @override
  Future<Map<String, dynamic>> createPaymentOrder(int courseId, {String? couponCode}) async {
    try {
      final response = await apiClient.post(
        '/api/v1/payments/create-order',
        data: {
          'course_id': courseId,
          if (couponCode != null) 'coupon_code': couponCode,
        },
      );

      if (response.statusCode == 200) {
        return response.data as Map<String, dynamic>;
      } else {
        throw ServerException(
          response.data['detail'] ?? 'Failed to create payment order',
          statusCode: response.statusCode,
        );
      }
    } on DioException catch (e) {
      throw AppExceptionFromDio.fromDioError(e);
    }
  }

  @override
  Future<void> verifyPayment(Map<String, dynamic> paymentData) async {
    try {
      final response = await apiClient.post(
        '/api/v1/payments/verify',
        data: paymentData,
      );

      if (response.statusCode != 200) {
        throw ServerException(
          response.data['detail'] ?? 'Payment verification failed',
          statusCode: response.statusCode,
        );
      }
    } on DioException catch (e) {
      throw AppExceptionFromDio.fromDioError(e);
    }
  }

  @override
  Future<Map<String, dynamic>> validateCoupon({
    required String code,
    required int courseId,
    required double totalAmount,
  }) async {
    try {
      final response = await apiClient.post(
        '/api/v1/coupons/validate',
        data: {
          'code': code,
          'course_ids': [courseId],
          'total_amount': totalAmount,
        },
      );

      if (response.statusCode == 200) {
        return response.data as Map<String, dynamic>;
      } else {
        throw ServerException(
          response.data['detail'] ?? 'Failed to validate coupon',
          statusCode: response.statusCode,
        );
      }
    } on DioException catch (e) {
      throw AppExceptionFromDio.fromDioError(e);
    }
  }
}
