import 'package:dio/dio.dart';
import '../storage/cache_storage.dart';

/// Network-first cache: every GET goes to the backend so that content
/// published from the admin panel is reflected immediately on the app.
/// Successful public GET responses are stored, and the stored copy is served
/// only when the network is unreachable (offline fallback).
///
/// Requests carrying an Authorization header are never cached or served from
/// cache: their responses are user-specific (profile, my-courses, is_enrolled
/// flags) and the cache key is only the URL, so serving them could leak one
/// user's data to another after re-login.
class CacheInterceptor extends Interceptor {
  final CacheStorage _cacheStorage;
  final Duration _expiry;

  CacheInterceptor(this._cacheStorage, {Duration expiry = const Duration(hours: 24)})
      : _expiry = expiry;

  @override
  void onResponse(Response response, ResponseInterceptorHandler handler) async {
    final options = response.requestOptions;
    if (options.method.toUpperCase() == 'GET' &&
        response.statusCode == 200 &&
        response.data != null &&
        !_isUserSpecific(options)) {
      if (response.data is Map || response.data is List) {
        await _cacheStorage.writeWithExpiry(
          _getCacheKey(options),
          response.data,
          _expiry,
        );
      }
    }
    handler.next(response);
  }

  @override
  void onError(DioException err, ErrorInterceptorHandler handler) {
    final options = err.requestOptions;
    if (options.method.toUpperCase() == 'GET' &&
        _isNetworkError(err) &&
        !_isUserSpecific(options)) {
      final cached = _cacheStorage.readIfNotExpired<dynamic>(_getCacheKey(options));
      if (cached != null) {
        handler.resolve(Response(
          requestOptions: options,
          data: cached is Map ? Map<String, dynamic>.from(cached) : cached,
          statusCode: 200,
          statusMessage: 'OK (offline cache)',
        ));
        return;
      }
    }
    handler.next(err);
  }

  bool _isNetworkError(DioException err) {
    return err.type == DioExceptionType.connectionTimeout ||
        err.type == DioExceptionType.receiveTimeout ||
        err.type == DioExceptionType.sendTimeout ||
        err.type == DioExceptionType.connectionError;
  }

  bool _isUserSpecific(RequestOptions options) {
    return options.headers.containsKey('Authorization');
  }

  // RequestOptions.uri reflects the final path after TrailingSlashInterceptor
  // rewrites, so read and write keys always agree.
  String _getCacheKey(RequestOptions options) => options.uri.toString();
}
