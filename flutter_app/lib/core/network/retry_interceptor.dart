// lib/core/network/retry_interceptor.dart
import 'package:dio/dio.dart';

/// Retries *transient* failures for idempotent GET requests with a short
/// exponential backoff.
///
/// A Cloudflare 502/503/504 usually means the origin was briefly overloaded or
/// restarting; connection/timeout errors are often a flaky network. A quick
/// retry frequently succeeds, so users don't get bounced to an error screen
/// for a momentary blip. Only GETs are retried — POST/PUT/PATCH/DELETE may not
/// be idempotent (payments, "mark complete", uploads), so they are never
/// auto-retried. A persistent 5xx still surfaces after [maxRetries].
class RetryInterceptor extends Interceptor {
  RetryInterceptor(this._dio, {this.maxRetries = 2});

  final Dio _dio;
  final int maxRetries;

  static const Set<int> _retriableStatus = {502, 503, 504};
  static const Set<DioExceptionType> _retriableTypes = {
    DioExceptionType.connectionTimeout,
    DioExceptionType.receiveTimeout,
    DioExceptionType.sendTimeout,
    DioExceptionType.connectionError,
  };

  @override
  Future<void> onError(
    DioException err,
    ErrorInterceptorHandler handler,
  ) async {
    final options = err.requestOptions;
    final isGet = options.method.toUpperCase() == 'GET';
    final status = err.response?.statusCode;
    final isTransient =
        (status != null && _retriableStatus.contains(status)) ||
            _retriableTypes.contains(err.type);

    final attempt = (options.extra['retry_attempt'] as int?) ?? 0;

    if (!isGet || !isTransient || attempt >= maxRetries) {
      return handler.next(err);
    }

    final nextAttempt = attempt + 1;
    // Backoff: 400ms, then 800ms.
    await Future<void>.delayed(Duration(milliseconds: 400 * nextAttempt));

    try {
      options.extra['retry_attempt'] = nextAttempt;
      final response = await _dio.fetch<dynamic>(options);
      return handler.resolve(response);
    } on DioException catch (e) {
      // Let the (incremented) request flow back through onError so it either
      // retries again or finally surfaces once maxRetries is reached.
      return handler.next(e);
    }
  }
}
