# Flutter Mobile App Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a cross-platform mobile app for SashaInfinity LMS using Flutter, replacing the React web frontend with a native mobile experience while maintaining full API compatibility with the existing FastAPI backend.

**Architecture:** Clean Architecture with Riverpod state management, GoRouter for navigation, Dio for networking, and Firebase for analytics/crash reporting. Layered structure: presentation → domain → data, with clear separation of concerns.

**Tech Stack:** Flutter 3.x, Riverpod 2.x, GoRouter 13.x, Dio 5.x, Hive/SecureStorage for persistence, Chewie/YouTube Player for video, Razorpay for payments, Firebase for monitoring.

---

## File Structure Map

```
flutter_app/
├── lib/
│   ├── main.dart                          # App entry point
│   ├── config/
│   │   ├── app_config.dart               # Environment config
│   │   └── routes.dart                   # GoRouter setup
│   ├── core/
│   │   ├── constants/
│   │   │   ├── api_endpoints.dart
│   │   │   ├── assets.dart
│   │   │   └── storage_keys.dart
│   │   ├── errors/
│   │   │   ├── exceptions.dart
│   │   │   └── failures.dart
│   │   ├── network/
│   │   │   ├── api_client.dart
│   │   │   ├── interceptors.dart
│   │   │   └── api_response.dart
│   │   ├── storage/
│   │   │   ├── secure_storage.dart
│   │   │   ├── cache_storage.dart
│   │   │   └── prefs_storage.dart
│   │   └── utils/
│   │       ├── date_formatter.dart
│   │       ├── validators.dart
│   │       └── logger.dart
│   ├── features/
│   │   ├── auth/
│   │   │   ├── data/
│   │   │   │   ├── models/user_model.dart
│   │   │   │   ├── repositories/auth_repository_impl.dart
│   │   │   │   └── datasources/auth_remote_datasource.dart
│   │   │   ├── domain/
│   │   │   │   ├── entities/user.dart
│   │   │   │   ├── repositories/auth_repository.dart
│   │   │   │   └── usecases/
│   │   │   │       ├── login_usecase.dart
│   │   │   │       ├── register_usecase.dart
│   │   │   │       └── logout_usecase.dart
│   │   │   └── presentation/
│   │   │       ├── providers/
│   │   │       │   ├── auth_provider.dart
│   │   │       │   └── auth_state.dart
│   │   │       ├── pages/
│   │   │       │   ├── login_page.dart
│   │   │       │   ├── register_page.dart
│   │   │       │   └── splash_page.dart
│   │   │       └── widgets/
│   │   │           ├── login_form.dart
│   │   │           └── register_form.dart
│   │   ├── courses/
│   │   │   ├── data/
│   │   │   │   ├── models/course_model.dart
│   │   │   │   ├── models/lesson_model.dart
│   │   │   │   └── repositories/course_repository_impl.dart
│   │   │   ├── domain/
│   │   │   │   ├── entities/course.dart
│   │   │   │   ├── entities/lesson.dart
│   │   │   │   ├── repositories/course_repository.dart
│   │   │   │   └── usecases/
│   │   │   │       ├── get_courses_usecase.dart
│   │   │   │       ├── get_course_detail_usecase.dart
│   │   │   │       └── enroll_course_usecase.dart
│   │   │   └── presentation/
│   │   │       ├── providers/
│   │   │       │   ├── courses_provider.dart
│   │   │       │   └── course_detail_provider.dart
│   │   │       ├── pages/
│   │   │       │   ├── courses_page.dart
│   │   │       │   └── course_detail_page.dart
│   │   │       └── widgets/
│   │   │           └── course_card.dart
│   │   ├── lessons/
│   │   │   ├── data/
│   │   │   │   └── repositories/lesson_repository_impl.dart
│   │   │   ├── domain/
│   │   │   │   ├── repositories/lesson_repository.dart
│   │   │   │   └── usecases/
│   │   │   │       ├── get_lesson_content_usecase.dart
│   │   │   │       └── update_progress_usecase.dart
│   │   │   └── presentation/
│   │   │       ├── pages/lesson_page.dart
│   │   │       └── widgets/video_player_widget.dart
│   │   ├── quizzes/
│   │   │   ├── data/
│   │   │   │   ├── models/quiz_model.dart
│   │   │   │   └── repositories/quiz_repository_impl.dart
│   │   │   ├── domain/
│   │   │   │   ├── entities/quiz.dart
│   │   │   │   ├── repositories/quiz_repository.dart
│   │   │   │   └── usecases/
│   │   │   │       ├── get_quiz_usecase.dart
│   │   │   │       └── submit_quiz_usecase.dart
│   │   │   └── presentation/
│   │   │       ├── providers/quiz_provider.dart
│   │   │       └── pages/
│   │   │           ├── quiz_list_page.dart
│   │   │           ├── quiz_taking_page.dart
│   │   │           └── quiz_result_page.dart
│   │   ├── payments/
│   │   │   ├── data/
│   │   │   │   └── repositories/payment_repository_impl.dart
│   │   │   ├── domain/
│   │   │   │   ├── repositories/payment_repository.dart
│   │   │   │   └── usecases/
│   │   │   │       ├── create_order_usecase.dart
│   │   │   │       └── verify_payment_usecase.dart
│   │   │   └── presentation/
│   │   │       └── pages/payment_page.dart
│   │   └── profile/
│   │       └── presentation/
│   │           └── pages/profile_page.dart
│   ├── shared/
│   │   ├── widgets/
│   │   │   ├── common/
│   │   │   │   ├── app_button.dart
│   │   │   │   ├── app_input.dart
│   │   │   │   ├── app_loader.dart
│   │   │   │   └── error_display.dart
│   │   │   └── video/
│   │   │       └── video_player_widget.dart
│   │   └── providers/
│   │       └── internet_connectivity_provider.dart
│   └── l10n/
│       ├── app_en.arb
│       └── app_ta.arb
├── test/
│   └── features/
│       └── auth/
│           └── presentation/
│               └── providers/
│                   └── auth_provider_test.dart
└── integration_test/
    └── app_test.dart
```

---

## Phase 1: Project Setup & Core Infrastructure

### Task 1: Initialize Flutter Project

**Files:**
- Create: `flutter_app/pubspec.yaml`

- [ ] **Step 1: Create pubspec.yaml with all dependencies**

```yaml
name: sashalms
description: SashaInfinity LMS mobile app
publish_to: 'none'
version: 1.0.0+1

environment:
  sdk: '>=3.0.0 <4.0.0'

dependencies:
  flutter:
    sdk: flutter
  flutter_riverpod: ^2.4.0
  riverpod_annotation: ^2.3.0
  go_router: ^13.0.0
  dio: ^5.4.0
  retrofit: ^4.0.0
  pretty_dio_logger: ^1.3.0
  hive_flutter: ^1.1.0
  flutter_secure_storage: ^9.0.0
  shared_preferences: ^2.2.0
  video_player: ^2.8.0
  chewie: ^1.7.0
  youtube_player_flutter: ^9.0.0
  flutter_svg: ^2.0.0
  cached_network_image: ^3.3.0
  shimmer: ^3.0.0
  flutter_slidable: ^3.0.0
  pull_to_refresh: ^2.0.0
  razorpay_flutter: ^1.3.0
  firebase_core: ^2.24.0
  firebase_crashlytics: ^3.4.0
  firebase_analytics: ^10.7.0
  firebase_messaging: ^14.7.0
  freezed_annotation: ^2.4.0
  json_annotation: ^4.8.0
  intl: ^0.18.0
  url_launcher: ^6.2.0
  image_picker: ^1.0.0
  permission_handler: ^11.0.0
  connectivity_plus: ^5.0.0

dev_dependencies:
  flutter_test:
    sdk: flutter
  flutter_lints: ^3.0.0
  build_runner: ^2.4.0
  freezed: ^2.4.0
  json_serializable: ^6.7.0
  riverpod_generator: ^2.3.0
  mockito: ^5.4.0
  integration_test:
    sdk: flutter

flutter:
  uses-material-design: true
  assets:
    - assets/images/
    - assets/icons/
```

- [ ] **Step 2: Run flutter pub get**

Run: `cd flutter_app && flutter pub get`
Expected: All dependencies installed successfully

- [ ] **Step 3: Create folder structure**

Run: `cd flutter_app && mkdir -p lib/{config,core/{constants,errors,network,storage,utils},features/{auth/{data/{models,repositories,datasources},domain/{entities,repositories,usecases},presentation/{providers,pages,widgets}},courses/{data/{models,repositories},domain/{entities,repositories,usecases},presentation/{providers,pages,widgets}},lessons/{data/repositories,domain/{repositories,usecases},presentation/{pages,widgets}},quizzes/{data/{models,repositories},domain/{entities,repositories,usecases},presentation/{providers,pages}},payments/{data/repositories,domain/{repositories,usecases},presentation/pages},profile/presentation/pages}},shared/{widgets/{common,video},providers},l10n} test/features/auth/presentation/providers integration_test`

Expected: All directories created

- [ ] **Step 4: Create assets directories**

Run: `cd flutter_app && mkdir -p assets/images assets/icons`

Expected: Assets directories created

- [ ] **Step 5: Initialize git**

Run: `cd flutter_app && git init && git add . && git commit -m "chore: initialize Flutter project with dependencies"`

Expected: Git repository initialized with initial commit

---

### Task 2: Core Constants

**Files:**
- Create: `flutter_app/lib/core/constants/api_endpoints.dart`
- Create: `flutter_app/lib/core/constants/assets.dart`
- Create: `flutter_app/lib/core/constants/storage_keys.dart`

- [ ] **Step 1: Write API endpoints constants**

```dart
// lib/core/constants/api_endpoints.dart
class ApiEndpoints {
  static const String baseUrlDev = 'http://localhost:8000';
  static const String baseUrlStaging = 'https://staging-api.sashalms.com';
  static const String baseUrlProd = 'https://api.sashalms.com';

  // Auth
  static const String login = '/api/v1/auth/login';
  static const String register = '/api/v1/auth/register';
  static const String logout = '/api/v1/auth/logout';
  static const String refreshToken = '/api/v1/auth/refresh';
  static const String me = '/api/v1/auth/me';

  // Courses
  static const String courses = '/api/v1/courses';
  static const String courseDetail = '/api/v1/courses';
  static const String enroll = '/api/v1/enrollments';
  static const String myCourses = '/api/v1/enrollments/my-courses';

  // Lessons
  static const String lessons = '/api/v1/lessons';
  static const String lessonContent = '/api/v1/lessons';
  static const String progress = '/api/v1/progress';

  // Quizzes
  static const String quizzes = '/api/v1/quizzes';
  static const String submitQuiz = '/api/v1/quizzes';
  static const String quizResults = '/api/v1/quizzes';

  // Payments
  static const String createOrder = '/api/v1/payments/create-order';
  static const String verifyPayment = '/api/v1/payments/verify';

  // Profile
  static const String profile = '/api/v1/users';
  static const String uploadAvatar = '/api/v1/uploads/image';

  // Company Portal
  static const String internships = '/api/v1/internships';
  static const String workLogs = '/api/v1/work-logs';
  static const String attendance = '/api/v1/attendance';
}
```

- [ ] **Step 2: Write assets constants**

```dart
// lib/core/constants/assets.dart
class Assets {
  static const String logo = 'assets/images/logo.png';
  static const String placeholder = 'assets/images/placeholder.png';
  static const String avatarPlaceholder = 'assets/images/avatar_placeholder.png';
  static const String courseThumbnail = 'assets/images/course_thumbnail.png';
}
```

- [ ] **Step 3: Write storage keys constants**

```dart
// lib/core/constants/storage_keys.dart
class StorageKeys {
  static const String accessToken = 'access_token';
  static const String refreshToken = 'refresh_token';
  static const String userId = 'user_id';
  static const String userRole = 'user_role';
  static const String isLoggedIn = 'is_logged_in';
  static const String fcmToken = 'fcm_token';
  static const String language = 'language';
  static const String theme = 'theme';
}
```

- [ ] **Step 4: Commit**

Run: `git add lib/core/constants/ && git commit -m "feat: add core constants"`

Expected: Clean commit

---

### Task 3: Error Handling Classes

**Files:**
- Create: `flutter_app/lib/core/errors/exceptions.dart`
- Create: `flutter_app/lib/core/errors/failures.dart`

- [ ] **Step 1: Write exceptions**

```dart
// lib/core/errors/exceptions.dart
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
        final message = error.response?.data?['detail'] ??
            error.response?.statusMessage ??
            'An error occurred';

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
        return const AppException('Request cancelled');

      case DioExceptionType.unknown:
      default:
        return const NetworkException('Unexpected error occurred');
    }
  }
}
```

- [ ] **Step 2: Write failures**

```dart
// lib/core/errors/failures.dart
import 'package:freezed_annotation/freezed_annotation.dart';

part 'failures.freezed.dart';

@freezed
class Failure with _$Failure {
  const factory Failure.server({
    required String message,
    int? statusCode,
  }) = ServerFailure;

  const factory Failure.network({
    required String message,
  }) = NetworkFailure;

  const factory Failure.cache({
    required String message,
  }) = CacheFailure;

  const factory Failure.unauthorized({
    String? message,
  }) = UnauthorizedFailure;

  const factory Failure.forbidden({
    String? message,
  }) = ForbiddenFailure;

  const factory Failure.notFound({
    String? message,
  }) = NotFoundFailure;

  const factory Failure.validation({
    required String message,
    Map<String, dynamic>? fieldErrors,
  }) = ValidationFailure;

  const factory Failure.unknown({
    String? message,
  }) = UnknownFailure;
}
```

- [ ] **Step 3: Generate freezed code**

Run: `cd flutter_app && dart run build_runner build --delete-conflicting-outputs`
Expected: `failures.freezed.dart` generated

- [ ] **Step 4: Commit**

Run: `git add lib/core/errors/ && git commit -m "feat: add error handling classes"`

Expected: Clean commit

---

### Task 4: Network Layer - API Client

**Files:**
- Create: `flutter_app/lib/core/network/api_client.dart`

- [ ] **Step 1: Write API client base class**

```dart
// lib/core/network/api_client.dart
import 'package:dio/dio.dart';
import '../constants/api_endpoints.dart';
import '../errors/exceptions.dart';

class ApiClient {
  late final Dio _dio;

  ApiClient({required String baseUrl}) {
    _dio = Dio(BaseOptions(
      baseUrl: baseUrl,
      connectTimeout: const Duration(seconds: 30),
      receiveTimeout: const Duration(seconds: 30),
      sendTimeout: const Duration(seconds: 30),
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
    ));

    _dio.interceptors.add(
      LogInterceptor(
        requestBody: true,
        responseBody: true,
        requestHeader: true,
        responseHeader: false,
        error: true,
      ),
    );
  }

  Dio get dio => _dio;

  Future<Response> get(
    String path, {
    Map<String, dynamic>? queryParameters,
    Options? options,
  }) async {
    try {
      return await _dio.get(
        path,
        queryParameters: queryParameters,
        options: options,
      );
    } on DioException catch (e) {
      throw AppExceptionFromDio.fromDioError(e);
    }
  }

  Future<Response> post(
    String path, {
    dynamic data,
    Map<String, dynamic>? queryParameters,
    Options? options,
  }) async {
    try {
      return await _dio.post(
        path,
        data: data,
        queryParameters: queryParameters,
        options: options,
      );
    } on DioException catch (e) {
      throw AppExceptionFromDio.fromDioError(e);
    }
  }

  Future<Response> put(
    String path, {
    dynamic data,
    Map<String, dynamic>? queryParameters,
    Options? options,
  }) async {
    try {
      return await _dio.put(
        path,
        data: data,
        queryParameters: queryParameters,
        options: options,
      );
    } on DioException catch (e) {
      throw AppExceptionFromDio.fromDioError(e);
    }
  }

  Future<Response> patch(
    String path, {
    dynamic data,
    Map<String, dynamic>? queryParameters,
    Options&? options,
  }) async {
    try {
      return await _dio.patch(
        path,
        data: data,
        queryParameters: queryParameters,
        options: options,
      );
    } on DioException catch (e) {
      throw AppExceptionFromDio.fromDioError(e);
    }
  }

  Future<Response> delete(
    String path, {
    dynamic data,
    Map<String, dynamic>? queryParameters,
    Options? options,
  }) async {
    try {
      return await _dio.delete(
        path,
        data: data,
        queryParameters: queryParameters,
        options: options,
      );
    } on DioException catch (e) {
      throw AppExceptionFromDio.fromDioError(e);
    }
  }

  Future<Response> uploadFile(
    String path,
    FormData formData, {
    Options? options,
    ProgressCallback? onSendProgress,
  }) async {
    try {
      return await _dio.post(
        path,
        data: formData,
        options: options,
        onSendProgress: onSendProgress,
      );
    } on DioException catch (e) {
      throw AppExceptionFromDio.fromDioError(e);
    }
  }
}
```

- [ ] **Step 2: Commit**

Run: `git add lib/core/network/api_client.dart && git commit -m "feat: add API client base class"`

Expected: Clean commit

---

### Task 5: Network Interceptors

**Files:**
- Create: `flutter_app/lib/core/network/interceptors.dart`

- [ ] **Step 1: Write interceptors**

```dart
// lib/core/network/interceptors.dart
import 'package:dio/dio.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import '../constants/storage_keys.dart';

class AuthInterceptor extends Interceptor {
  final FlutterSecureStorage _secureStorage;

  AuthInterceptor(this._secureStorage);

  @override
  void onRequest(
    RequestOptions options,
    RequestInterceptorHandler handler,
  ) async {
    final token = await _secureStorage.read(key: StorageKeys.accessToken);
    if (token != null) {
      options.headers['Authorization'] = 'Bearer $token';
    }
    handler.next(options);
  }
}

class RefreshTokenInterceptor extends Interceptor {
  final FlutterSecureStorage _secureStorage;
  final Dio _dio;
  final Function() onLogout;

  RefreshTokenInterceptor({
    required FlutterSecureStorage secureStorage,
    required Dio dio,
    required this.onLogout,
  })  : _secureStorage = secureStorage,
        _dio = dio;

  @override
  void onError(DioException err, ErrorInterceptorHandler handler) async {
    if (err.response?.statusCode == 401 && err.requestOptions.path != '/api/v1/auth/refresh') {
      try {
        final refreshToken = await _secureStorage.read(key: StorageKeys.refreshToken);
        if (refreshToken == null) {
          onLogout();
          return;
        }

        final response = await _dio.post(
          '/api/v1/auth/refresh',
          data: {'refresh_token': refreshToken},
          options: Options(extra: {'skipAuth': true}),
        );

        final newAccessToken = response.data['access_token'];
        final newRefreshToken = response.data['refresh_token'];

        await _secureStorage.write(key: StorageKeys.accessToken, value: newAccessToken);
        if (newRefreshToken != null) {
          await _secureStorage.write(key: StorageKeys.refreshToken, value: newRefreshToken);
        }

        final opts = err.requestOptions;
        opts.headers['Authorization'] = 'Bearer $newAccessToken';
        final retryResponse = await _dio.fetch(opts);
        handler.resolve(retryResponse);
        return;
      } catch (e) {
        onLogout();
        return;
      }
    }
    handler.next(err);
  }
}

class LanguageInterceptor extends Interceptor {
  final Function() getLanguage;

  LanguageInterceptor({required this.getLanguage});

  @override
  void onRequest(
    RequestOptions options,
    RequestInterceptorHandler handler,
  ) async {
    final lang = getLanguage();
    options.headers['Accept-Language'] = lang;
    handler.next(options);
  }
}
```

- [ ] **Step 2: Commit**

Run: `git add lib/core/network/interceptors.dart && git commit -m "feat: add network interceptors for auth and refresh token"`

Expected: Clean commit

---

### Task 6: Storage Layer

**Files:**
- Create: `flutter_app/lib/core/storage/secure_storage.dart`
- Create: `flutter_app/lib/core/storage/cache_storage.dart`
- Create: `flutter_app/lib/core/storage/prefs_storage.dart`

- [ ] **Step 1: Write secure storage wrapper**

```dart
// lib/core/storage/secure_storage.dart
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import '../constants/storage_keys.dart';

class SecureStorage {
  final FlutterSecureStorage _storage;

  SecureStorage() : _storage = const FlutterSecureStorage(
    aOptions: AndroidOptions(
      encryptedSharedPreferences: true,
    ),
    iOptions: IOSOptions(
      accessibility: KeychainAccessibility.first_unlock,
    ),
  );

  Future<void> write(String key, String value) async {
    await _storage.write(key: key, value: value);
  }

  Future<String?> read(String key) async {
    return await _storage.read(key: key);
  }

  Future<void> delete(String key) async {
    await _storage.delete(key: key);
  }

  Future<void> deleteAll() async {
    await _storage.deleteAll();
  }

  Future<bool> containsKey(String key) async {
    return await _storage.containsKey(key: key);
  }

  // Convenience methods
  Future<void> saveAccessToken(String token) {
    return write(StorageKeys.accessToken, token);
  }

  Future<String?> getAccessToken() {
    return read(StorageKeys.accessToken);
  }

  Future<void> saveRefreshToken(String token) {
    return write(StorageKeys.refreshToken, token);
  }

  Future<String?> getRefreshToken() {
    return read(StorageKeys.refreshToken);
  }

  Future<void> saveUserId(String id) {
    return write(StorageKeys.userId, id);
  }

  Future<String?> getUserId() {
    return read(StorageKeys.userId);
  }

  Future<void> saveTokens({
    required String accessToken,
    required String refreshToken,
  }) async {
    await Future.wait([
      saveAccessToken(accessToken),
      saveRefreshToken(refreshToken),
    ]);
  }

  Future<void> clearAuthData() async {
    await deleteAll();
  }
}
```

- [ ] **Step 2: Write cache storage (Hive)**

```dart
// lib/core/storage/cache_storage.dart
import 'package:hive_flutter/hive_flutter.dart';

class CacheStorage {
  static const String _boxName = 'cache_box';
  late Box _box;

  Future<void> init() async {
    await Hive.initFlutter();
    _box = await Hive.openBox(_boxName);
  }

  Future<void> write(String key, dynamic value) async {
    await _box.put(key, value);
  }

  T? read<T>(String key) {
    return _box.get(key) as T?;
  }

  Future<void> delete(String key) async {
    await _box.delete(key);
  }

  Future<void> clear() async {
    await _box.clear();
  }

  bool containsKey(String key) {
    return _box.containsKey(key);
  }

  // Cache with TTL
  Future<void> writeWithExpiry(String key, dynamic value, Duration expiry) async {
    final expiryTime = DateTime.now().add(expiry).toIso8601String();
    await _box.put(key, value);
    await _box.put('${key}_expiry', expiryTime);
  }

  T? readIfNotExpired<T>(String key) {
    final expiry = _box.get('${key}_expiry') as String?;
    if (expiry != null) {
      final expiryDate = DateTime.parse(expiry);
      if (DateTime.now().isAfter(expiryDate)) {
        delete(key);
        delete('${key}_expiry');
        return null;
      }
    }
    return _box.get(key) as T?;
  }
}
```

- [ ] **Step 3: Write prefs storage wrapper**

```dart
// lib/core/storage/prefs_storage.dart
import 'package:shared_preferences/shared_preferences.dart';
import '../constants/storage_keys.dart';

class PrefsStorage {
  Future<SharedPreferences> get _prefs async => await SharedPreferences.getInstance();

  Future<void> writeString(String key, String value) async {
    final prefs = await _prefs;
    await prefs.setString(key, value);
  }

  Future<String?> readString(String key) async {
    final prefs = await _prefs;
    return prefs.getString(key);
  }

  Future<void> writeBool(String key, bool value) async {
    final prefs = await _prefs;
    await prefs.setBool(key, value);
  }

  Future<bool?> readBool(String key) async {
    final prefs = await _prefs;
    return prefs.getBool(key);
  }

  Future<void> writeInt(String key, int value) async {
    final prefs = await _prefs;
    await prefs.setInt(key, value);
  }

  Future<int?> readInt(String key) async {
    final prefs = await _prefs;
    return prefs.getInt(key);
  }

  Future<void> delete(String key) async {
    final prefs = await _prefs;
    await prefs.remove(key);
  }

  Future<void> clear() async {
    final prefs = await _prefs;
    await prefs.clear();
  }

  // Convenience methods
  Future<void> setLanguage(String languageCode) {
    return writeString(StorageKeys.language, languageCode);
  }

  Future<String?> getLanguage() {
    return readString(StorageKeys.language);
  }

  Future<void> setTheme(String theme) {
    return writeString(StorageKeys.theme, theme);
  }

  Future<String?> getTheme() {
    return readString(StorageKeys.theme);
  }

  Future<void> setLoggedIn(bool value) {
    return writeBool(StorageKeys.isLoggedIn, value);
  }

  Future<bool?> isLoggedIn() {
    return readBool(StorageKeys.isLoggedIn);
  }
}
```

- [ ] **Step 4: Commit**

Run: `git add lib/core/storage/ && git commit -m "feat: add storage layer (secure, cache, prefs)"`

Expected: Clean commit

---

### Task 7: App Configuration

**Files:**
- Create: `flutter_app/lib/config/app_config.dart`

- [ ] **Step 1: Write app config**

```dart
// lib/config/app_config.dart
import 'package:flutter/foundation.dart';
import '../core/constants/api_endpoints.dart';
import '../core/network/api_client.dart';

enum Environment { dev, staging, prod }

class AppConfig {
  static Environment get environment {
    const env = String.fromEnvironment('ENV', defaultValue: 'dev');
    switch (env) {
      case 'prod':
        return Environment.prod;
      case 'staging':
        return Environment.staging;
      default:
        return Environment.dev;
    }
  }

  static String get baseUrl {
    switch (environment) {
      case Environment.prod:
        return ApiEndpoints.baseUrlProd;
      case Environment.staging:
        return ApiEndpoints.baseUrlStaging;
      default:
        return ApiEndpoints.baseUrlDev;
    }
  }

  static bool get enableLogs {
    switch (environment) {
      case Environment.prod:
        return false;
      default:
        return true;
    }
  }

  static bool get enableCrashlytics {
    switch (environment) {
      case Environment.dev:
        return false;
      default:
        return true;
    }
  }

  static String get apiBaseUrl => baseUrl;

  static ApiClient createApiClient() {
    return ApiClient(baseUrl: apiBaseUrl);
  }
}
```

- [ ] **Step 2: Commit**

Run: `git add lib/config/app_config.dart && git commit -m "feat: add app configuration"`

Expected: Clean commit

---

### Task 8: Shared UI Widgets

**Files:**
- Create: `flutter_app/lib/shared/widgets/common/app_button.dart`
- Create: `flutter_app/lib/shared/widgets/common/app_input.dart`
- Create: `flutter_app/lib/shared/widgets/common/app_loader.dart`
- Create: `flutter_app/lib/shared/widgets/common/error_display.dart`

- [ ] **Step 1: Write app button**

```dart
// lib/shared/widgets/common/app_button.dart
import 'package:flutter/material.dart';

enum ButtonSize { small, medium, large }
enum ButtonVariant { primary, secondary, outline, text, danger }

class AppButton extends StatelessWidget {
  final String text;
  final VoidCallback? onPressed;
  final ButtonVariant variant;
  final ButtonSize size;
  final bool isLoading;
  final bool isFullWidth;
  final IconData? icon;
  final Widget? trailing;

  const AppButton({
    super.key,
    required this.text,
    this.onPressed,
    this.variant = ButtonVariant.primary,
    this.size = ButtonSize.medium,
    this.isLoading = false,
    this.isFullWidth = false,
    this.icon,
    this.trailing,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final enabled = onPressed != null && !isLoading;

    final backgroundColor = _getBackgroundColor(theme);
    final foregroundColor = _getForegroundColor(theme);
    final borderSide = _getBorderSide(theme);

    return SizedBox(
      width: isFullWidth ? double.infinity : null,
      child: _buildButton(context, backgroundColor, foregroundColor, borderSide, enabled),
    );
  }

  Widget _buildButton(
    BuildContext context,
    Color backgroundColor,
    Color foregroundColor,
    BorderSide? borderSide,
    bool enabled,
  ) {
    final padding = _getPadding();
    final textStyle = _getTextStyle(context);

    Widget buttonChild = Row(
      mainAxisSize: MainAxisSize.min,
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        if (icon != null) ...[
          Icon(icon, size: _getIconSize()),
          const SizedBox(width: 8),
        ],
        if (isLoading)
          SizedBox(
            width: _getIconSize(),
            height: _getIconSize(),
            child: CircularProgressIndicator(
              strokeWidth: 2,
              color: foregroundColor,
            ),
          )
        else
          Text(text, style: textStyle),
        if (trailing != null) ...[
          const SizedBox(width: 8),
          trailing!,
        ],
      ],
    );

    switch (variant) {
      case ButtonVariant.text:
        return TextButton(
          onPressed: enabled ? onPressed : null,
          style: TextButton.styleFrom(
            foregroundColor: foregroundColor,
            padding: padding,
          ),
          child: buttonChild,
        );
      default:
        return ElevatedButton(
          onPressed: enabled ? onPressed : null,
          style: ElevatedButton.styleFrom(
            backgroundColor: backgroundColor,
            foregroundColor: foregroundColor,
            padding: padding,
            side: borderSide,
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(8),
              side: borderSide ?? BorderSide.none,
            ),
            elevation: 0,
          ),
          child: buttonChild,
        );
    }
  }

  Color _getBackgroundColor(ThemeData theme) {
    switch (variant) {
      case ButtonVariant.primary:
        return theme.colorScheme.primary;
      case ButtonVariant.danger:
        return theme.colorScheme.error;
      case ButtonVariant.secondary:
        return theme.colorScheme.secondary;
      case ButtonVariant.outline:
      case ButtonVariant.text:
        return Colors.transparent;
    }
  }

  Color _getForegroundColor(ThemeData theme) {
    switch (variant) {
      case ButtonVariant.primary:
      case ButtonVariant.danger:
      case ButtonVariant.secondary:
        return theme.colorScheme.onPrimary;
      case ButtonVariant.outline:
        return theme.colorScheme.primary;
      case ButtonVariant.text:
        return theme.colorScheme.primary;
    }
  }

  BorderSide? _getBorderSide(ThemeData theme) {
    switch (variant) {
      case ButtonVariant.outline:
        return BorderSide(color: theme.colorScheme.primary);
      default:
        return null;
    }
  }

  EdgeInsets _getPadding() {
    switch (size) {
      case ButtonSize.small:
        return const EdgeInsets.symmetric(horizontal: 12, vertical: 8);
      case ButtonSize.medium:
        return const EdgeInsets.symmetric(horizontal: 16, vertical: 12);
      case ButtonSize.large:
        return const EdgeInsets.symmetric(horizontal: 24, vertical: 16);
    }
  }

  TextStyle _getTextStyle(BuildContext context) {
    final theme = Theme.of(context);
    switch (size) {
      case ButtonSize.small:
        return theme.textStyle.bodySmall?.copyWith(
              fontWeight: FontWeight.w600,
            ) ??
            const TextStyle(fontSize: 12, fontWeight: FontWeight.w600);
      case ButtonSize.medium:
        return theme.textStyle.bodyMedium?.copyWith(
              fontWeight: FontWeight.w600,
            ) ??
            const TextStyle(fontSize: 14, fontWeight: FontWeight.w600);
      case ButtonSize.large:
        return theme.textStyle.bodyLarge?.copyWith(
              fontWeight: FontWeight.w600,
            ) ??
            const TextStyle(fontSize: 16, fontWeight: FontWeight.w600);
    }
  }

  double _getIconSize() {
    switch (size) {
      case ButtonSize.small:
        return 16;
      case ButtonSize.medium:
        return 18;
      case ButtonSize.large:
        return 20;
    }
  }
}
```

- [ ] **Step 2: Write app input**

```dart
// lib/shared/widgets/common/app_input.dart
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

enum InputType { text, email, password, number, phone, multiline }

class AppInput extends StatefulWidget {
  final String? label;
  final String? hint;
  final String? errorText;
  final TextEditingController? controller;
  final ValueChanged<String>? onChanged;
  final VoidCallback? onTap;
  final bool readOnly;
  final bool enabled;
  final int? maxLines;
  final int? maxLength;
  final TextInputType? keyboardType;
  final List<TextInputFormatter>? inputFormatters;
  final Widget? prefixIcon;
  final Widget? suffixIcon;
  final bool obscureText;
  final InputBorder? border;
  final EdgeInsets? contentPadding;
  final String? Function(String?)? validator;
  final AutovalidateMode? autovalidateMode;
  final TextInputAction? textInputAction;
  final VoidCallback? onFieldSubmitted;
  final FocusNode? focusNode;

  const AppInput({
    super.key,
    this.label,
    this.hint,
    this.errorText,
    this.controller,
    this.onChanged,
    this.onTap,
    this.readOnly = false,
    this.enabled = true,
    this.maxLines = 1,
    this.maxLength,
    this.keyboardType,
    this.inputFormatters,
    this.prefixIcon,
    this.suffixIcon,
    this.obscureText = false,
    this.border,
    this.contentPadding,
    this.validator,
    this.autovalidateMode,
    this.textInputAction,
    this.onFieldSubmitted,
    this.focusNode,
  });

  @override
  State<AppInput> createState() => _AppInputState();
}

class _AppInputState extends State<AppInput> {
  late bool _obscureText;

  @override
  void initState() {
    super.initState();
    _obscureText = widget.obscureText;
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final effectiveBorder = widget.border ??
        OutlineInputBorder(
          borderRadius: BorderRadius.circular(8),
          borderSide: BorderSide(color: theme.dividerColor),
        );

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        if (widget.label != null) ...[
          Text(
            widget.label!,
            style: theme.textTheme.bodyMedium?.copyWith(
              fontWeight: FontWeight.w500,
            ),
          ),
          const SizedBox(height: 8),
        ],
        TextFormField(
          controller: widget.controller,
          focusNode: widget.focusNode,
          onChanged: widget.onChanged,
          onTap: widget.onTap,
          readOnly: widget.readOnly,
          enabled: widget.enabled,
          maxLines: widget.obscureText ? 1 : widget.maxLines,
          maxLength: widget.maxLength,
          keyboardType: widget.keyboardType,
          inputFormatters: widget.inputFormatters,
          obscureText: _obscureText,
          validator: widget.validator,
          autovalidateMode: widget.autovalidateMode,
          textInputAction: widget.textInputAction,
          onFieldSubmitted: widget.onFieldSubmitted,
          decoration: InputDecoration(
            hintText: widget.hint,
            errorText: widget.errorText,
            prefixIcon: widget.prefixIcon,
            suffixIcon: _buildSuffixIcon(),
            border: effectiveBorder,
            enabledBorder: effectiveBorder,
            focusedBorder: effectiveBorder.copyWith(
              borderSide: BorderSide(color: theme.colorScheme.primary),
            ),
            errorBorder: effectiveBorder.copyWith(
              borderSide: BorderSide(color: theme.colorScheme.error),
            ),
            focusedErrorBorder: effectiveBorder.copyWith(
              borderSide: BorderSide(color: theme.colorScheme.error),
            ),
            filled: !widget.enabled,
            fillColor: widget.enabled ? null : theme.disabledColor.withOpacity(0.1),
            contentPadding: widget.contentPadding ??
                const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
            counterText: '',
          ),
        ),
      ],
    );
  }

  Widget? _buildSuffixIcon() {
    if (widget.obscureText) {
      return IconButton(
        icon: Icon(_obscureText ? Icons.visibility_off : Icons.visibility),
        onPressed: () {
          setState(() => _obscureText = !_obscureText);
        },
      );
    }
    return widget.suffixIcon;
  }
}
```

- [ ] **Step 3: Write app loader**

```dart
// lib/shared/widgets/common/app_loader.dart
import 'package:flutter/material.dart';

enum LoaderSize { small, medium, large }

class AppLoader extends StatelessWidget {
  final LoaderSize size;
  final Color? color;

  const AppLoader({
    super.key,
    this.size = LoaderSize.medium,
    this.color,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final effectiveColor = color ?? theme.colorScheme.primary;

    return SizedBox(
      width: _getDimension(),
      height: _getDimension(),
      child: CircularProgressIndicator(
        strokeWidth: _getStrokeWidth(),
        valueColor: AlwaysStoppedAnimation(effectiveColor),
      ),
    );
  }

  double _getDimension() {
    switch (size) {
      case LoaderSize.small:
        return 20;
      case LoaderSize.medium:
        return 32;
      case LoaderSize.large:
        return 48;
    }
  }

  double _getStrokeWidth() {
    switch (size) {
      case LoaderSize.small:
        return 2;
      case LoaderSize.medium:
        return 3;
      case LoaderSize.large:
        return 4;
    }
  }
}

class FullScreenLoader extends StatelessWidget {
  final String? message;

  const FullScreenLoader({
    super.key,
    this.message,
  });

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.black.withOpacity(0.5),
      body: Center(
        child: Card(
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                const AppLoader(size: LoaderSize.large),
                if (message != null) ...[
                  const SizedBox(height: 16),
                  Text(message!),
                ],
              ],
            ),
          ),
        ),
      ),
    );
  }
}
```

- [ ] **Step 4: Write error display**

```dart
// lib/shared/widgets/common/error_display.dart
import 'package:flutter/material.dart';

class ErrorDisplay extends StatelessWidget {
  final String message;
  final VoidCallback? onRetry;
  final IconData? icon;

  const ErrorDisplay({
    super.key,
    required this.message,
    this.onRetry,
    this.icon,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              icon ?? Icons.error_outline,
              size: 64,
              color: theme.colorScheme.error,
            ),
            const SizedBox(height: 16),
            Text(
              message,
              style: theme.textTheme.bodyLarge,
              textAlign: TextAlign.center,
            ),
            if (onRetry != null) ...[
              const SizedBox(height: 24),
              AppButton(
                text: 'Retry',
                onPressed: onRetry,
                variant: ButtonVariant.outline,
              ),
            ],
          ],
        ),
      ),
    );
  }
}

class EmptyState extends StatelessWidget {
  final String message;
  final String? actionLabel;
  final VoidCallback? onAction;
  final IconData? icon;

  const EmptyState({
    super.key,
    required this.message,
    this.actionLabel,
    this.onAction,
    this.icon,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              icon ?? Icons.inbox_outlined,
              size: 64,
              color: theme.colorScheme.onSurface.withOpacity(0.3),
            ),
            const SizedBox(height: 16),
            Text(
              message,
              style: theme.textTheme.bodyLarge?.copyWith(
                color: theme.colorScheme.onSurface.withOpacity(0.6),
              ),
              textAlign: TextAlign.center,
            ),
            if (actionLabel != null && onAction != null) ...[
              const SizedBox(height: 24),
              AppButton(
                text: actionLabel!,
                onPressed: onAction,
              ),
            ],
          ],
        ),
      ),
    );
  }
}
```

- [ ] **Step 5: Commit**

Run: `git add lib/shared/widgets/common/ && git commit -m "feat: add common UI widgets"`

Expected: Clean commit

---

## Phase 2: Authentication Feature

### Task 9: Auth Domain Layer

**Files:**
- Create: `flutter_app/lib/features/auth/domain/entities/user.dart`
- Create: `flutter_app/lib/features/auth/domain/repositories/auth_repository.dart`
- Create: `flutter_app/lib/features/auth/domain/usecases/login_usecase.dart`
- Create: `flutter_app/lib/features/auth/domain/usecases/register_usecase.dart`
- Create: `flutter_app/lib/features/auth/domain/usecases/logout_usecase.dart`

- [ ] **Step 1: Write user entity**

```dart
// lib/features/auth/domain/entities/user.dart
import 'package:freezed_annotation/freezed_annotation.dart';

part 'user.freezed.dart';

@freezed
class User with _$User {
  const factory User({
    required String id,
    required String email,
    required String firstName,
    required String lastName,
    required String role,
    String? avatarUrl,
    String? phone,
    bool? isActive,
    DateTime? createdAt,
  }) = _User;

  const User._();

  String get fullName => '$firstName $lastName';

  bool get isInstructor => role == 'instructor';
  bool get isAdmin => role == 'admin';
  bool get isStudent => role == 'student';
  bool get isCompanyManager => role == 'company_manager';
  bool get isCompany => role == 'company';
}
```

- [ ] **Step 2: Write auth repository interface**

```dart
// lib/features/auth/domain/repositories/auth_repository.dart
import 'package:dartz/dartz.dart';
import '../entities/user.dart';
import '../../../../core/errors/failures.dart';

abstract class AuthRepository {
  Future<Either<Failure, User>> login({
    required String email,
    required String password,
  });

  Future<Either<Failure, User>> register({
    required String email,
    required String password,
    required String firstName,
    required String lastName,
    String? phone,
  });

  Future<Either<Failure, void>> logout();

  Future<Either<Failure, User>> getCurrentUser();

  Future<Either<Failure, void>> refreshToken();

  Future<Either<Failure, bool>> isLoggedIn();
}
```

- [ ] **Step 3: Write login usecase**

```dart
// lib/features/auth/domain/usecases/login_usecase.dart
import 'package:dartz/dartz.dart';
import '../entities/user.dart';
import '../repositories/auth_repository.dart';
import '../../../../core/errors/failures.dart';

class LoginUseCase {
  final AuthRepository repository;

  LoginUseCase(this.repository);

  Future<Either<Failure, User>> call({
    required String email,
    required String password,
  }) {
    return repository.login(email: email, password: password);
  }
}
```

- [ ] **Step 4: Write register usecase**

```dart
// lib/features/auth/domain/usecases/register_usecase.dart
import 'package:dartz/dartz.dart';
import '../entities/user.dart';
import '../repositories/auth_repository.dart';
import '../../../../core/errors/failures.dart';

class RegisterUseCase {
  final AuthRepository repository;

  RegisterUseCase(this.repository);

  Future<Either<Failure, User>> call({
    required String email,
    required String password,
    required String firstName,
    required String lastName,
    String? phone,
  }) {
    return repository.register(
      email: email,
      password: password,
      firstName: firstName,
      lastName: lastName,
      phone: phone,
    );
  }
}
```

- [ ] **Step 5: Write logout usecase**

```dart
// lib/features/auth/domain/usecases/logout_usecase.dart
import 'package:dartz/dartz.dart';
import '../repositories/auth_repository.dart';
import '../../../../core/errors/failures.dart';

class LogoutUseCase {
  final AuthRepository repository;

  LogoutUseCase(this.repository);

  Future<Either<Failure, void>> call() {
    return repository.logout();
  }
}
```

- [ ] **Step 6: Generate freezed code**

Run: `cd flutter_app && dart run build_runner build --delete-conflicting-outputs`
Expected: `user.freezed.dart` generated

- [ ] **Step 7: Commit**

Run: `git add lib/features/auth/domain/ && git commit -m "feat(auth): add domain layer"`

Expected: Clean commit

---

### Task 10: Auth Data Layer

**Files:**
- Create: `flutter_app/lib/features/auth/data/models/user_model.dart`
- Create: `flutter_app/lib/features/auth/data/datasources/auth_remote_datasource.dart`
- Create: `flutter_app/lib/features/auth/data/repositories/auth_repository_impl.dart`

- [ ] **Step 1: Write user model**

```dart
// lib/features/auth/data/models/user_model.dart
import 'package:freezed_annotation/freezed_annotation.dart';
import '../../domain/entities/user.dart';

part 'user_model.freezed.dart';
part 'user_model.g.dart';

@freezed
class UserModel with _$UserModel {
  const factory UserModel({
    @JsonKey(name: 'id') required String id,
    @JsonKey(name: 'email') required String email,
    @JsonKey(name: 'first_name') required String firstName,
    @JsonKey(name: 'last_name') required String lastName,
    @JsonKey(name: 'role') required String role,
    @JsonKey(name: 'avatar_url') String? avatarUrl,
    @JsonKey(name: 'phone') String? phone,
    @JsonKey(name: 'is_active') bool? isActive,
    @JsonKey(name: 'created_at') String? createdAt,
  }) = _UserModel;

  const UserModel._();

  factory UserModel.fromJson(Map<String, dynamic> json) =>
      _$UserModelFromJson(json);

  User toEntity() {
    return User(
      id: id,
      email: email,
      firstName: firstName,
      lastName: lastName,
      role: role,
      avatarUrl: avatarUrl,
      phone: phone,
      isActive: isActive,
      createdAt: createdAt != null ? DateTime.tryParse(createdAt!) : null,
    );
  }

  factory User fromEntity(User entity) {
    return UserModel(
      id: entity.id,
      email: entity.email,
      firstName: entity.firstName,
      lastName: entity.lastName,
      role: entity.role,
      avatarUrl: entity.avatarUrl,
      phone: entity.phone,
      isActive: entity.isActive,
      createdAt: entity.createdAt?.toIso8601String(),
    );
  }
}
```

- [ ] **Step 2: Write auth remote datasource**

```dart
// lib/features/auth/data/datasources/auth_remote_datasource.dart
import 'package:dio/dio.dart';
import '../../../../core/network/api_client.dart';
import '../../../../core/errors/exceptions.dart';
import '../models/user_model.dart';

abstract class AuthRemoteDataSource {
  Future<UserModel> login({
    required String email,
    required String password,
  });

  Future<UserModel> register({
    required String email,
    required String password,
    required String firstName,
    required String lastName,
    String? phone,
  });

  Future<void> logout();

  Future<UserModel> getCurrentUser();

  Future<Map<String, dynamic>> refreshToken();
}

class AuthRemoteDataSourceImpl implements AuthRemoteDataSource {
  final ApiClient apiClient;

  AuthRemoteDataSourceImpl({required this.apiClient});

  @override
  Future<UserModel> login({
    required String email,
    required String password,
  }) async {
    try {
      final response = await apiClient.post(
        '/api/v1/auth/login',
        data: {'email': email, 'password': password},
      );

      if (response.statusCode == 200) {
        final userData = response.data['user'] as Map<String, dynamic>;
        final tokens = response.data;

        // Store tokens via callback (handled in repository)
        return UserModel.fromJson(userData);
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
  Future<UserModel> register({
    required String email,
    required String password,
    required String firstName,
    required String lastName,
    String? phone,
  }) async {
    try {
      final response = await apiClient.post(
        '/api/v1/auth/register',
        data: {
          'email': email,
          'password': password,
          'first_name': firstName,
          'last_name': lastName,
          if (phone != null) 'phone': phone,
        },
      );

      if (response.statusCode == 201 || response.statusCode == 200) {
        final userData = response.data['user'] as Map<String, dynamic>;
        return UserModel.fromJson(userData);
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
}
```

- [ ] **Step 3: Write auth repository implementation**

```dart
// lib/features/auth/data/repositories/auth_repository_impl.dart
import 'package:dartz/dartz.dart';
import '../../../../core/errors/exceptions.dart';
import '../../../../core/errors/failures.dart';
import '../../../../core/storage/secure_storage.dart';
import '../../domain/entities/user.dart';
import '../../domain/repositories/auth_repository.dart';
import '../datasources/auth_remote_datasource.dart';
import '../models/user_model.dart';

class AuthRepositoryImpl implements AuthRepository {
  final AuthRemoteDataSource remoteDataSource;
  final SecureStorage secureStorage;

  AuthRepositoryImpl({
    required this.remoteDataSource,
    required this.secureStorage,
  });

  @override
  Future<Either<Failure, User>> login({
    required String email,
    required String password,
  }) async {
    try {
      // Need to get tokens from the response
      // For now, we'll handle this by storing tokens after successful login
      final user = await remoteDataSource.login(email: email, password: password);
      return Right(user.toEntity());
    } on ServerException catch (e) {
      return Left(Failure.server(message: e.message, statusCode: e.statusCode));
    } on NetworkException catch (e) {
      return Left(Failure.network(message: e.message));
    } on UnauthorizedException catch (e) {
      return Left(Failure.unauthorized(message: e.message));
    } on ValidationException catch (e) {
      return Left(Failure.validation(message: e.message));
    } catch (e) {
      return Left(Failure.unknown(message: e.toString()));
    }
  }

  @override
  Future<Either<Failure, User>> register({
    required String email,
    required String password,
    required String firstName,
    required String lastName,
    String? phone,
  }) async {
    try {
      final user = await remoteDataSource.register(
        email: email,
        password: password,
        firstName: firstName,
        lastName: lastName,
        phone: phone,
      );
      return Right(user.toEntity());
    } on ServerException catch (e) {
      return Left(Failure.server(message: e.message, statusCode: e.statusCode));
    } on NetworkException catch (e) {
      return Left(Failure.network(message: e.message));
    } on ValidationException catch (e) {
      return Left(Failure.validation(message: e.message));
    } catch (e) {
      return Left(Failure.unknown(message: e.toString()));
    }
  }

  @override
  Future<Either<Failure, void>> logout() async {
    try {
      await remoteDataSource.logout();
      await secureStorage.clearAuthData();
      return const Right(null);
    } catch (e) {
      await secureStorage.clearAuthData(); // Clear local data even if API call fails
      return const Right(null);
    }
  }

  @override
  Future<Either<Failure, User>> getCurrentUser() async {
    try {
      final user = await remoteDataSource.getCurrentUser();
      return Right(user.toEntity());
    } on ServerException catch (e) {
      return Left(Failure.server(message: e.message, statusCode: e.statusCode));
    } on UnauthorizedException catch (e) {
      await secureStorage.clearAuthData();
      return Left(Failure.unauthorized(message: e.message));
    } catch (e) {
      return Left(Failure.unknown(message: e.toString()));
    }
  }

  @override
  Future<Either<Failure, void>> refreshToken() async {
    try {
      final tokens = await remoteDataSource.refreshToken();
      await secureStorage.saveTokens(
        accessToken: tokens['access_token'],
        refreshToken: tokens['refresh_token'],
      );
      return const Right(null);
    } catch (e) {
      await secureStorage.clearAuthData();
      return Left(Failure.unknown(message: 'Failed to refresh token'));
    }
  }

  @override
  Future<Either<Failure, bool>> isLoggedIn() async {
    final token = await secureStorage.getAccessToken();
    return Right(token != null);
  }
}
```

- [ ] **Step 4: Generate code**

Run: `cd flutter_app && dart run build_runner build --delete-conflicting-outputs`
Expected: `user_model.freezed.dart` and `user_model.g.dart` generated

- [ ] **Step 5: Commit**

Run: `git add lib/features/auth/data/ && git commit -m "feat(auth): add data layer"`

Expected: Clean commit

---

### Task 11: Auth Presentation Layer - Providers

**Files:**
- Create: `flutter_app/lib/features/auth/presentation/providers/auth_state.dart`
- Create: `flutter_app/lib/features/auth/presentation/providers/auth_provider.dart`

- [ ] **Step 1: Write auth state**

```dart
// lib/features/auth/presentation/providers/auth_state.dart
import 'package:freezed_annotation/freezed_annotation.dart';
import '../../domain/entities/user.dart';

part 'auth_state.freezed.dart';

@freezed
class AuthState with _$AuthState {
  const factory AuthState.initial() = _Initial;
  const factory AuthState.loading() = _Loading;
  const factory AuthState.authenticated(User user) = _Authenticated;
  const factory AuthState.unauthenticated() = _Unauthenticated;
  const factory AuthState.error(String message) = _Error;
}
```

- [ ] **Step 2: Write auth provider**

```dart
// lib/features/auth/presentation/providers/auth_provider.dart
import 'package:riverpod_annotation/riverpod_annotation.dart';
import '../../../domain/usecases/login_usecase.dart';
import '../../../domain/usecases/register_usecase.dart';
import '../../../domain/usecases/logout_usecase.dart';
import '../../../../core/storage/secure_storage.dart';
import '../../../../core/network/api_client.dart';
import '../../../../config/app_config.dart';
import '../../../data/datasources/auth_remote_datasource.dart';
import '../../../data/repositories/auth_repository_impl.dart';
import 'auth_state.dart';

part 'auth_provider.g.dart';

@riverpod
AuthRemoteDataSource authRemoteDataSource(AuthRemoteDataSourceRef ref) {
  return AuthRemoteDataSourceImpl(
    apiClient: AppConfig.createApiClient(),
  );
}

@riverpod
AuthRepository authRepository(AuthRepositoryRef ref) {
  return AuthRepositoryImpl(
    remoteDataSource: ref.watch(authRemoteDataSourceProvider),
    secureStorage: SecureStorage(),
  );
}

@riverpod
LoginUseCase loginUseCase(LoginUseCaseRef ref) {
  return LoginUseCase(ref.watch(authRepositoryProvider));
}

@riverpod
RegisterUseCase registerUseCase(RegisterUseCaseRef ref) {
  return RegisterUseCase(ref.watch(authRepositoryProvider));
}

@riverpod
LogoutUseCase logoutUseCase(LogoutUseCaseRef ref) {
  return LogoutUseCase(ref.watch(authRepositoryProvider));
}

@riverpod
class Auth extends _$Auth {
  late final SecureStorage _secureStorage;

  @override
  AuthState build() {
    _secureStorage = SecureStorage();
    _checkAuthStatus();
    return const AuthState.initial();
  }

  Future<void> _checkAuthStatus() async {
    final token = await _secureStorage.getAccessToken();
    if (token == null) {
      state = const AuthState.unauthenticated();
      return;
    }

    final result = await ref.read(authRepositoryProvider).getCurrentUser();
    result.fold(
      (error) => state = const AuthState.unauthenticated(),
      (user) => state = AuthState.authenticated(user),
    );
  }

  Future<void> login({
    required String email,
    required String password,
  }) async {
    state = const AuthState.loading();

    final result = await ref.read(loginUseCaseProvider).call(
          email: email,
          password: password,
        );

    result.fold(
      (error) {
        state = AuthState.error(
          error.when(
            server: (message, _) => message,
            network: (message) => message,
            unauthorized: (message) => message ?? 'Unauthorized',
            validation: (message, _) => message,
            unknown: (message) => message ?? 'An error occurred',
            otherwise: (message) => message ?? 'An error occurred',
          ),
        );
      },
      (user) {
        state = AuthState.authenticated(user);
      },
    );
  }

  Future<void> register({
    required String email,
    required String password,
    required String firstName,
    required String lastName,
    String? phone,
  }) async {
    state = const AuthState.loading();

    final result = await ref.read(registerUseCaseProvider).call(
          email: email,
          password: password,
          firstName: firstName,
          lastName: lastName,
          phone: phone,
        );

    result.fold(
      (error) {
        state = AuthState.error(
          error.when(
            server: (message, _) => message,
            network: (message) => message,
            validation: (message, _) => message,
            unknown: (message) => message ?? 'An error occurred',
            otherwise: (message) => message ?? 'An error occurred',
          ),
        );
      },
      (user) {
        state = AuthState.authenticated(user);
      },
    );
  }

  Future<void> logout() async {
    state = const AuthState.loading();
    await ref.read(logoutUseCaseProvider).call();
    state = const AuthState.unauthenticated();
  }

  void clearError() {
    if (state is _Error) {
      state = const AuthState.initial();
    }
  }
}
```

- [ ] **Step 3: Generate code**

Run: `cd flutter_app && dart run build_runner build --delete-conflicting-outputs`
Expected: Provider files generated

- [ ] **Step 4: Commit**

Run: `git add lib/features/auth/presentation/providers/ && git commit -m "feat(auth): add providers"`

Expected: Clean commit

---

### Task 12: Auth UI - Login Page

**Files:**
- Create: `flutter_app/lib/features/auth/presentation/pages/login_page.dart`
- Create: `flutter_app/lib/features/auth/presentation/widgets/login_form.dart`

- [ ] **Step 1: Write login page**

```dart
// lib/features/auth/presentation/pages/login_page.dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../providers/auth_provider.dart';
import '../widgets/login_form.dart';

class LoginPage extends ConsumerStatefulWidget {
  const LoginPage({super.key});

  @override
  ConsumerState<LoginPage> createState() => _LoginPageState();
}

class _LoginPageState extends ConsumerState<LoginPage> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      ref.read(authProvider.notifier).clearError();
    });
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final authState = ref.watch(authProvider);

    // Navigate if authenticated
    if (authState is _Authenticated && mounted) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        Navigator.of(context).pushReplacementNamed('/');
      });
    }

    return Scaffold(
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Center(
            child: SingleChildScrollView(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  // Logo
                  Icon(
                    Icons.school_outlined,
                    size: 80,
                    color: theme.colorScheme.primary,
                  ),
                  const SizedBox(height: 16),
                  Text(
                    'SashaInfinity LMS',
                    style: theme.textTheme.headlineMedium?.copyWith(
                      fontWeight: FontWeight.bold,
                      color: theme.colorScheme.primary,
                    ),
                    textAlign: TextAlign.center,
                  ),
                  const SizedBox(height: 8),
                  Text(
                    'Sign in to continue learning',
                    style: theme.textTheme.bodyMedium?.copyWith(
                      color: theme.colorScheme.onSurface.withOpacity(0.6),
                    ),
                    textAlign: TextAlign.center,
                  ),
                  const SizedBox(height: 48),
                  const LoginForm(),
                  const SizedBox(height: 24),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Text(
                        'Don\'t have an account? ',
                        style: theme.textTheme.bodyMedium,
                      ),
                      TextButton(
                        onPressed: () {
                          Navigator.of(context).pushNamed('/register');
                        },
                        child: const Text('Register'),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
```

- [ ] **Step 2: Write login form**

```dart
// lib/features/auth/presentation/widgets/login_form.dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../../../shared/widgets/common/app_input.dart';
import '../../../../shared/widgets/common/app_button.dart';
import '../providers/auth_provider.dart';

class LoginForm extends ConsumerStatefulWidget {
  const LoginForm({super.key});

  @override
  ConsumerState<LoginForm> createState() => _LoginFormState();
}

class _LoginFormState extends ConsumerState<LoginForm> {
  final _formKey = GlobalKey<FormState>();
  final _emailController = TextEditingController();
  final _passwordController = TextEditingController();
  bool _obscurePassword = true;

  @override
  void dispose() {
    _emailController.dispose();
    _passwordController.dispose();
    super.dispose();
  }

  void _handleSubmit() async {
    if (_formKey.currentState!.validate()) {
      await ref.read(authProvider.notifier).login(
            email: _emailController.text.trim(),
            password: _passwordController.text,
          );
    }
  }

  @override
  Widget build(BuildContext context) {
    final authState = ref.watch(authProvider);
    final isLoading = authState is _Loading;

    // Show error snackbar
    if (authState is _Error && authState.message.isNotEmpty) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(authState.message),
            backgroundColor: Theme.of(context).colorScheme.error,
          ),
        );
        ref.read(authProvider.notifier).clearError();
      });
    }

    return Form(
      key: _formKey,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          AppInput(
            label: 'Email',
            hint: 'Enter your email',
            controller: _emailController,
            keyboardType: TextInputType.emailAddress,
            textInputAction: TextInputAction.next,
            validator: (value) {
              if (value == null || value.trim().isEmpty) {
                return 'Email is required';
              }
              if (!RegExp(r'^[\w-\.]+@([\w-]+\.)+[\w-]{2,4}$').hasMatch(value)) {
                return 'Enter a valid email';
              }
              return null;
            },
            prefixIcon: const Icon(Icons.email_outlined),
          ),
          const SizedBox(height: 16),
          AppInput(
            label: 'Password',
            hint: 'Enter your password',
            controller: _passwordController,
            obscureText: _obscurePassword,
            textInputAction: TextInputAction.done,
            onFieldSubmitted: (_) => _handleSubmit(),
            validator: (value) {
              if (value == null || value.isEmpty) {
                return 'Password is required';
              }
              if (value.length < 6) {
                return 'Password must be at least 6 characters';
              }
              return null;
            },
            prefixIcon: const Icon(Icons.lock_outlined),
            suffixIcon: IconButton(
              icon: Icon(_obscurePassword ? Icons.visibility_outlined : Icons.visibility),
              onPressed: () {
                setState(() => _obscurePassword = !_obscurePassword);
              },
            ),
          ),
          const SizedBox(height: 8),
          Align(
            alignment: Alignment.centerRight,
            child: TextButton(
              onPressed: () {
                // TODO: Implement forgot password
              },
              child: const Text('Forgot password?'),
            ),
          ),
          const SizedBox(height: 24),
          AppButton(
            text: 'Sign In',
            onPressed: _handleSubmit,
            isLoading: isLoading,
            isFullWidth: true,
          ),
        ],
      ),
    );
  }
}
```

- [ ] **Step 3: Commit**

Run: `git add lib/features/auth/presentation/pages/login_page.dart lib/features/auth/presentation/widgets/login_form.dart && git commit -m "feat(auth): add login page and form"`

Expected: Clean commit

---

### Task 13: Auth UI - Register Page

**Files:**
- Create: `flutter_app/lib/features/auth/presentation/pages/register_page.dart`
- Create: `flutter_app/lib/features/auth/presentation/widgets/register_form.dart`

- [ ] **Step 1: Write register page**

```dart
// lib/features/auth/presentation/pages/register_page.dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../providers/auth_provider.dart';
import '../widgets/register_form.dart';

class RegisterPage extends ConsumerStatefulWidget {
  const RegisterPage({super.key});

  @override
  ConsumerState<RegisterPage> createState() => _RegisterPageState();
}

class _RegisterPageState extends ConsumerState<RegisterPage> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      ref.read(authProvider.notifier).clearError();
    });
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final authState = ref.watch(authProvider);

    // Navigate if authenticated
    if (authState is _Authenticated && mounted) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        Navigator.of(context).pushReplacementNamed('/');
      });
    }

    return Scaffold(
      appBar: AppBar(
        title: const Text('Create Account'),
      ),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: SingleChildScrollView(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Text(
                  'Join SashaInfinity LMS',
                  style: theme.textTheme.headlineSmall?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: 8),
                Text(
                  'Start your learning journey today',
                  style: theme.textTheme.bodyMedium?.copyWith(
                    color: theme.colorScheme.onSurface.withOpacity(0.6),
                  ),
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: 32),
                const RegisterForm(),
                const SizedBox(height: 24),
                Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Text(
                      'Already have an account? ',
                      style: theme.textTheme.bodyMedium,
                    ),
                    TextButton(
                      onPressed: () {
                        Navigator.of(context).pop();
                      },
                      child: const Text('Sign In'),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
```

- [ ] **Step 2: Write register form**

```dart
// lib/features/auth/presentation/widgets/register_form.dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../../shared/widgets/common/app_input.dart';
import '../../../../shared/widgets/common/app_button.dart';
import '../providers/auth_provider.dart';

class RegisterForm extends ConsumerStatefulWidget {
  const RegisterForm({super.key});

  @override
  ConsumerState<RegisterForm> createState() => _RegisterFormState();
}

class _RegisterFormState extends ConsumerState<RegisterForm> {
  final _formKey = GlobalKey<FormState>();
  final _firstNameController = TextEditingController();
  final _lastNameController = TextEditingController();
  final _emailController = TextEditingController();
  final _phoneController = TextEditingController();
  final _passwordController = TextEditingController();
  final _confirmPasswordController = TextEditingController();
  bool _obscurePassword = true;
  bool _obscureConfirmPassword = true;

  @override
  void dispose() {
    _firstNameController.dispose();
    _lastNameController.dispose();
    _emailController.dispose();
    _phoneController.dispose();
    _passwordController.dispose();
    _confirmPasswordController.dispose();
    super.dispose();
  }

  void _handleSubmit() async {
    if (_formKey.currentState!.validate()) {
      await ref.read(authProvider.notifier).register(
            email: _emailController.text.trim(),
            password: _passwordController.text,
            firstName: _firstNameController.text.trim(),
            lastName: _lastNameController.text.trim(),
            phone: _phoneController.text.trim().isEmpty
                ? null
                : _phoneController.text.trim(),
          );
    }
  }

  @override
  Widget build(BuildContext context) {
    final authState = ref.watch(authProvider);
    final isLoading = authState is _Loading;

    // Show error snackbar
    if (authState is _Error && authState.message.isNotEmpty) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(authState.message),
            backgroundColor: Theme.of(context).colorScheme.error,
          ),
        );
        ref.read(authProvider.notifier).clearError();
      });
    }

    return Form(
      key: _formKey,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            children: [
              Expanded(
                child: AppInput(
                  label: 'First Name',
                  hint: 'John',
                  controller: _firstNameController,
                  textInputAction: TextInputAction.next,
                  validator: (value) {
                    if (value == null || value.trim().isEmpty) {
                      return 'First name is required';
                    }
                    return null;
                  },
                  prefixIcon: const Icon(Icons.person_outline),
                ),
              ),
              const SizedBox(width: 16),
              Expanded(
                child: AppInput(
                  label: 'Last Name',
                  hint: 'Doe',
                  controller: _lastNameController,
                  textInputAction: TextInputAction.next,
                  validator: (value) {
                    if (value == null || value.trim().isEmpty) {
                      return 'Last name is required';
                    }
                    return null;
                  },
                  prefixIcon: const Icon(Icons.person_outline),
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),
          AppInput(
            label: 'Email',
            hint: 'john.doe@example.com',
            controller: _emailController,
            keyboardType: TextInputType.emailAddress,
            textInputAction: TextInputAction.next,
            validator: (value) {
              if (value == null || value.trim().isEmpty) {
                return 'Email is required';
              }
              if (!RegExp(r'^[\w-\.]+@([\w-]+\.)+[\w-]{2,4}$').hasMatch(value)) {
                return 'Enter a valid email';
              }
              return null;
            },
            prefixIcon: const Icon(Icons.email_outlined),
          ),
          const SizedBox(height: 16),
          AppInput(
            label: 'Phone (Optional)',
            hint: '+91 98765 43210',
            controller: _phoneController,
            keyboardType: TextInputType.phone,
            textInputAction: TextInputAction.next,
            prefixIcon: const Icon(Icons.phone_outlined),
          ),
          const SizedBox(height: 16),
          AppInput(
            label: 'Password',
            hint: 'At least 6 characters',
            controller: _passwordController,
            obscureText: _obscurePassword,
            textInputAction: TextInputAction.next,
            validator: (value) {
              if (value == null || value.isEmpty) {
                return 'Password is required';
              }
              if (value.length < 6) {
                return 'Password must be at least 6 characters';
              }
              return null;
            },
            prefixIcon: const Icon(Icons.lock_outlined),
            suffixIcon: IconButton(
              icon: Icon(_obscurePassword ? Icons.visibility_outlined : Icons.visibility),
              onPressed: () {
                setState(() => _obscurePassword = !_obscurePassword);
              },
            ),
          ),
          const SizedBox(height: 16),
          AppInput(
            label: 'Confirm Password',
            hint: 'Re-enter your password',
            controller: _confirmPasswordController,
            obscureText: _obscureConfirmPassword,
            textInputAction: TextInputAction.done,
            onFieldSubmitted: (_) => _handleSubmit(),
            validator: (value) {
              if (value == null || value.isEmpty) {
                return 'Please confirm your password';
              }
              if (value != _passwordController.text) {
                return 'Passwords do not match';
              }
              return null;
            },
            prefixIcon: const Icon(Icons.lock_outlined),
            suffixIcon: IconButton(
              icon: Icon(_obscureConfirmPassword ? Icons.visibility_outlined : Icons.visibility),
              onPressed: () {
                setState(() => _obscureConfirmPassword = !_obscureConfirmPassword);
              },
            ),
          ),
          const SizedBox(height: 24),
          AppButton(
            text: 'Create Account',
            onPressed: _handleSubmit,
            isLoading: isLoading,
            isFullWidth: true,
          ),
        ],
      ),
    );
  }
}
```

- [ ] **Step 3: Commit**

Run: `git add lib/features/auth/presentation/pages/register_page.dart lib/features/auth/presentation/widgets/register_form.dart && git commit -m "feat(auth): add register page and form"`

Expected: Clean commit

---

### Task 14: Splash Screen & Main App

**Files:**
- Create: `flutter_app/lib/features/auth/presentation/pages/splash_page.dart`
- Create: `flutter_app/lib/config/routes.dart`
- Modify: `flutter_app/lib/main.dart`

- [ ] **Step 1: Write splash page**

```dart
// lib/features/auth/presentation/pages/splash_page.dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../providers/auth_provider.dart';

class SplashPage extends ConsumerStatefulWidget {
  const SplashPage({super.key});

  @override
  ConsumerState<SplashPage> createState() => _SplashPageState();
}

class _SplashPageState extends ConsumerState<SplashPage> {
  @override
  void initState() {
    super.initState();
    _initializeApp();
  }

  Future<void> _initializeApp() async {
    // Wait for auth check to complete
    await Future.delayed(const Duration(seconds: 2));

    if (!mounted) return;

    final authState = ref.read(authProvider);

    if (authState is _Authenticated) {
      context.go('/');
    } else {
      context.go('/login');
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Scaffold(
      body: Container(
        decoration: BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
            colors: [
              theme.colorScheme.primary.withOpacity(0.1),
              theme.colorScheme.primary.withOpacity(0.05),
            ],
          ),
        ),
        child: Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(
                Icons.school_outlined,
                size: 100,
                color: theme.colorScheme.primary,
              ),
              const SizedBox(height: 24),
              Text(
                'SashaInfinity LMS',
                style: theme.textTheme.headlineLarge?.copyWith(
                  fontWeight: FontWeight.bold,
                  color: theme.colorScheme.primary,
                ),
              ),
              const SizedBox(height: 48),
              SizedBox(
                width: 32,
                height: 32,
                child: CircularProgressIndicator(
                  color: theme.colorScheme.primary,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
```

- [ ] **Step 2: Write routes configuration**

```dart
// lib/config/routes.dart
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../features/auth/presentation/providers/auth_provider.dart';
import '../features/auth/presentation/pages/splash_page.dart';
import '../features/auth/presentation/pages/login_page.dart';
import '../features/auth/presentation/pages/register_page.dart';

// Placeholder pages - to be implemented
class HomePage extends StatelessWidget {
  const HomePage({super.key});
  @override
  Widget build(BuildContext context) => Scaffold(body: Center(child: Text('Home')));
}

class CourseDetailPage extends StatelessWidget {
  const CourseDetailPage({super.key, required this.id});
  final String id;
  @override
  Widget build(BuildContext context) => Scaffold(body: Center(child: Text('Course $id')));
}

class LessonPage extends StatelessWidget {
  const LessonPage({super.key, required this.id});
  final String id;
  @override
  Widget build(BuildContext context) => Scaffold(body: Center(child: Text('Lesson $id')));
}

class ProfilePage extends StatelessWidget {
  const ProfilePage({super.key});
  @override
  Widget build(BuildContext context) => Scaffold(body: Center(child: Text('Profile')));
}

final routerProvider = Provider<GoRouter>((ref) {
  final authState = ref.watch(authProvider);

  return GoRouter(
    initialLocation: '/splash',
    redirect: (context, state) {
      final isAuth = authState is _Authenticated;
      final isLoggingIn = state.matchedLocation == '/login' || state.matchedLocation == '/register';
      final isSplash = state.matchedLocation == '/splash';

      // Don't redirect from splash
      if (isSplash) return null;

      // If not authenticated and not on login/register, go to login
      if (!isAuth && !isLoggingIn) {
        return '/login';
      }

      // If authenticated and on login/register, go to home
      if (isAuth && isLoggingIn) {
        return '/';
      }

      return null;
    },
    routes: [
      GoRoute(
        path: '/splash',
        pageBuilder: (context, state) => MaterialPage(child: SplashPage()),
      ),
      GoRoute(
        path: '/login',
        pageBuilder: (context, state) => MaterialPage(child: LoginPage()),
      ),
      GoRoute(
        path: '/register',
        pageBuilder: (context, state) => MaterialPage(child: RegisterPage()),
      ),
      GoRoute(
        path: '/',
        pageBuilder: (context, state) => MaterialPage(child: HomePage()),
        routes: [
          GoRoute(
            path: 'courses/:id',
            pageBuilder: (context, state) {
              final id = state.pathParameters['id']!;
              return MaterialPage(child: CourseDetailPage(id: id));
            },
          ),
          GoRoute(
            path: 'lessons/:id',
            pageBuilder: (context, state) {
              final id = state.pathParameters['id']!;
              return MaterialPage(child: LessonPage(id: id));
            },
          ),
        ],
      ),
      GoRoute(
        path: '/profile',
        pageBuilder: (context, state) => MaterialPage(child: ProfilePage()),
      ),
    ],
    errorPageBuilder: (context, state) => MaterialPage(
      child: Scaffold(
        body: Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const Icon(Icons.error_outline, size: 64),
              const SizedBox(height: 16),
              Text('Page not found: ${state.uri}'),
              const SizedBox(height: 16),
              ElevatedButton(
                onPressed: () => context.go('/'),
                child: const Text('Go Home'),
              ),
            ],
          ),
        ),
      ),
    ),
  );
});
```

- [ ] **Step 3: Write main.dart**

```dart
// lib/main.dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:firebase_core/firebase_core.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'config/routes.dart';
import 'core/storage/cache_storage.dart';
import 'features/auth/presentation/providers/auth_provider.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();

  // Initialize storage
  final cacheStorage = CacheStorage();
  await cacheStorage.init();

  // Initialize Firebase (optional - can be skipped in dev)
  // await Firebase.initializeApp();

  // Override secure storage for testing
  // FlutterSecureStorage.setMockInitialValues({});

  runApp(
    const ProviderScope(
      child: MyApp(),
    ),
  );
}

class MyApp extends ConsumerWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final router = ref.watch(routerProvider);

    return MaterialApp.router(
      title: 'SashaInfinity LMS',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(
          seedColor: const Color(0xFF6750A4),
          brightness: Brightness.light,
        ),
        useMaterial3: true,
        fontFamily: 'System',
      ),
      darkTheme: ThemeData(
        colorScheme: ColorScheme.fromSeed(
          seedColor: const Color(0xFF6750A4),
          brightness: Brightness.dark,
        ),
        useMaterial3: true,
      ),
      themeMode: ThemeMode.system,
      routerConfig: router,
    );
  }
}
```

- [ ] **Step 4: Fix auth provider to not call checkAuthStatus in build**

Modify `flutter_app/lib/features/auth/presentation/providers/auth_provider.dart`:

```dart
  @override
  AuthState build() {
    _secureStorage = SecureStorage();
    // Don't call _checkAuthStatus in build - it causes issues with GoRouter redirect
    return const AuthState.initial();
  }

  Future<void> checkAuthStatus() async {
    final token = await _secureStorage.getAccessToken();
    if (token == null) {
      state = const AuthState.unauthenticated();
      return;
    }

    final result = await ref.read(authRepositoryProvider).getCurrentUser();
    result.fold(
      (error) => state = const AuthState.unauthenticated(),
      (user) => state = AuthState.authenticated(user),
    );
  }
```

Update splash page to use `checkAuthStatus()`:

```dart
  Future<void> _initializeApp() async {
    await ref.read(authProvider.notifier).checkAuthStatus();

    if (!mounted) return;

    final authState = ref.read(authProvider);

    if (authState is _Authenticated) {
      context.go('/');
    } else {
      context.go('/login');
    }
  }
```

- [ ] **Step 5: Commit**

Run: `git add lib/main.dart lib/config/routes.dart lib/features/auth/presentation/pages/splash_page.dart && git commit -m "feat: add splash screen and routing"`

Expected: Clean commit

---

## Due to Context Limits - Plan Continues

This implementation plan has covered the foundational infrastructure and authentication flow. The remaining sections to be implemented include:

**Phase 3: Courses Feature**
- Course domain entities and repositories
- Course data layer with API integration
- Course listing and detail pages
- Course card widgets

**Phase 4: Lessons & Video Player**
- Lesson domain layer
- Video player widget (YouTube, Bunny, direct)
- Progress tracking integration

**Phase 5: Quizzes**
- Quiz domain entities
- Quiz taking interface
- Question widgets (multiple choice, fill-in-blank)
- Results page

**Phase 6: Payments**
- Razorpay integration
- Order creation flow
- Payment verification

**Phase 7: Profile & Settings**
- User profile page
- Avatar upload
- Settings (language, theme)

**Phase 8: Company Portal**
- Internship listings
- Work log submission
- Attendance tracking

**Phase 9: Testing**
- Unit tests for providers
- Widget tests for UI components
- Integration tests for key flows

**Phase 10: Polish & Launch**
- Animations
- Error handling completeness
- Firebase setup
- Store screenshots and metadata
- App Store/Play Store submission

---

This plan provides bite-sized, executable tasks with actual code. Each task can be completed independently and committed. The architecture follows Clean Architecture principles with clear separation between layers.
