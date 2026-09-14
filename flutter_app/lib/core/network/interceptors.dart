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

  /// Single-flight guard: when several requests 401 at once, only ONE refresh
  /// call runs; the rest await this same future. Without it, N concurrent 401s
  /// fire N `/auth/refresh` calls — the backend rotates the refresh token on
  /// each, so all but the first retry fail and the user is logged out.
  Future<String?>? _refreshCall;

  RefreshTokenInterceptor({
    required FlutterSecureStorage secureStorage,
    required Dio dio,
    required this.onLogout,
  })  : _secureStorage = secureStorage,
        _dio = dio;

  /// Credential / public auth endpoints where a 401 means "bad credentials or
  /// input" — NOT "expired access token". Refreshing and retrying these is
  /// pointless and causes an infinite login→refresh→login loop when another
  /// session's refresh token is still valid. (Authenticated endpoints like
  /// /auth/me, /auth/logout, /auth/change-password are intentionally NOT here:
  /// a 401 there really does mean the access token expired → refresh + retry.)
  static const _noRefreshOn401 = <String>[
    '/auth/refresh',
    '/auth/login',
    '/auth/register',
    '/auth/register-instructor',
    '/auth/google',
    '/auth/google/complete',
    '/auth/linkedin',
    '/auth/forgot-password',
    '/auth/reset-password',
    '/auth/verify-email',
    '/auth/resend-verification',
    '/auth/check-email',
  ];

  bool _shouldSkipRefresh(String path) =>
      _noRefreshOn401.any((p) => path.contains(p));

  @override
  void onError(DioException err, ErrorInterceptorHandler handler) async {
    if (err.response?.statusCode == 401 &&
        !_shouldSkipRefresh(err.requestOptions.path)) {
      try {
        final newAccessToken = await _refreshAccessToken();
        if (newAccessToken == null) {
          onLogout();
          handler.reject(err);
          return;
        }

        final opts = err.requestOptions;
        opts.headers['Authorization'] = 'Bearer $newAccessToken';
        final retryResponse = await _dio.fetch(opts);
        handler.resolve(retryResponse);
        return;
      } catch (e) {
        onLogout();
        handler.reject(err);
        return;
      }
    }
    handler.next(err);
  }

  /// Returns a fresh access token, coalescing concurrent callers onto one
  /// in-flight refresh. The slot is cleared on completion so a later token
  /// expiry can refresh again. Returns null when no refresh token is stored.
  ///
  /// The single error path is the future stored in [_refreshCall], which every
  /// caller awaits — so a failed refresh surfaces exactly once (handled by
  /// onError's catch). We must NOT attach a side `whenComplete`/`then` to it:
  /// that creates a second, unawaited future that rethrows the same error with
  /// no listener, which Dart reports as an uncaught zone error.
  Future<String?> _refreshAccessToken() {
    return _refreshCall ??= _doRefresh();
  }

  Future<String?> _doRefresh() async {
    try {
      return await _performRefresh();
    } finally {
      _refreshCall = null;
    }
  }

  Future<String?> _performRefresh() async {
    final refreshToken = await _secureStorage.read(key: StorageKeys.refreshToken);
    if (refreshToken == null) return null;

    final response = await _dio.post(
      '/api/v1/auth/refresh',
      data: {'refresh_token': refreshToken},
      options: Options(extra: {'skipAuth': true}),
    );

    final newAccessToken = response.data['access_token'] as String?;
    final newRefreshToken = response.data['refresh_token'] as String?;
    if (newAccessToken == null) return null;

    await _secureStorage.write(key: StorageKeys.accessToken, value: newAccessToken);
    if (newRefreshToken != null) {
      await _secureStorage.write(key: StorageKeys.refreshToken, value: newRefreshToken);
    }
    return newAccessToken;
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

class TrailingSlashInterceptor extends Interceptor {
  @override
  void onRequest(
    RequestOptions options,
    RequestInterceptorHandler handler,
  ) {
    final path = options.path;
    // Handle both relative and absolute paths
    final uri = Uri.parse(path.startsWith('http') ? path : 'http://localhost$path');
    final cleanPath = uri.path;

    if (cleanPath.isNotEmpty && !cleanPath.endsWith('/')) {
      // Remove /api/v1 prefix for checking
      final checkPath = cleanPath.replaceFirst('/api/v1', '');
      
      // Endpoints that MUST NOT have trailing slashes
      final noSlashEndpoints = [
        '/users/profile', '/users/stats', '/users/avatar',
        '/dashboard/student', '/dashboard/instructor', '/dashboard/admin',
        '/admin/stats', '/admin/courses', '/admin/users', '/templates',
        '/auth/logout', '/auth/refresh', '/auth/me', '/auth/profile',
        '/auth/change-password', '/auth/forgot-password', '/auth/reset-password',
        '/auth/verify-email', '/auth/resend-verification', '/auth/check-email',
        '/auth/roles', '/auth/instructor-profile',
        '/auth/login', '/auth/register', '/auth/register-instructor',
        '/upload/image', '/upload/video', '/upload/document', '/upload/file', '/upload/info',
        '/upload/chunked/init', '/upload/chunked',
        '/courses/publish', '/courses/unpublish', '/courses/featured', '/courses/popular',
        '/courses/search', '/courses/my-courses', '/courses/pending', '/wishlist',
        '/certificates/generate', '/certificates/regenerate', '/certificates/verify',
        '/certificates/download', '/certificates/templates', '/certificates/admin',
        '/admin/internships',
        '/categories', '/tags', '/instructors',
        '/payments', '/quizzes', '/assignments', '/coupons',
        '/stream/extract', '/bunny/video', '/bunny',
        '/analytics', '/internships',
        '/candidates', '/companies', '/cohorts', '/checkout',
        '/admin/spocs', '/admin/companies', '/admin/colleges', '/admin/cohorts',
        '/companies/me',
        '/spoc/my-internships', '/spoc/internships',
        '/internships/my-vouchers', '/internships/purchase'
      ];

      // Endpoints that MUST have trailing slashes
      final trailingSlashEndpoints = [
        '/blog',
        '/courses',
      ];

      final isStaticNoSlash = noSlashEndpoints.any((endpoint) => checkPath == endpoint || checkPath.startsWith('$endpoint/'));

      final isTrailingSlash = trailingSlashEndpoints.any((endpoint) {
        return checkPath == endpoint;
      });

      final isDynamicNoSlash = 
        checkPath.contains('/admin/') ||
        (checkPath.contains('/courses/') && checkPath != '/courses') ||
        (checkPath.contains('/certificates/') && checkPath != '/certificates') ||
        (checkPath.contains('/blog/') && checkPath != '/blog') ||
        checkPath.contains('/users/') ||
        checkPath.contains('/instructor/') ||
        checkPath.contains('/auth/') ||
        checkPath.contains('/upload/') ||
        RegExp(r'/\w+/\d+($|/\w+$)').hasMatch(checkPath) ||
        RegExp(r'/\w+-\w+/\w+').hasMatch(checkPath);

      final isAdminNoSlash = [
        '/admin/stats',
        '/admin/courses',
        '/admin/users',
        '/admin/revenue',
        '/admin/instructor-applications',
        '/admin/enrollments',
        '/admin/categories',
        '/admin/tags',
        '/admin/certificates',
        '/admin/orders'
      ].any((endpoint) => checkPath.endsWith(endpoint));

      bool shouldAddSlash = false;
      if (isTrailingSlash) {
        shouldAddSlash = true;
      } else if (!isStaticNoSlash && !isDynamicNoSlash && !isAdminNoSlash) {
        // Only add slash if it's a base collection endpoint (e.g., /courses, /blog)
        final segments = checkPath.split('/').where((s) => s.isNotEmpty).toList();
        if (segments.length == 1) {
           shouldAddSlash = true;
        }
      }

      if (shouldAddSlash) {
        if (path.contains('?')) {
          final parts = path.split('?');
          if (!parts[0].endsWith('/')) {
            options.path = '${parts[0]}/?${parts[1]}';
          }
        } else if (!path.endsWith('/')) {
          options.path = '$path/';
        }
      }
    }

    super.onRequest(options, handler);
  }
}
