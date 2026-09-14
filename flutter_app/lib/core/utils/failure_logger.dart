// lib/core/utils/failure_logger.dart
import 'package:flutter/foundation.dart';
import '../../config/app_config.dart';
import '../errors/failures.dart';

/// Prints a Failure to logcat with the PROBLEM (what failed) and the most
/// likely CAUSE (why), so device logs are diagnosable without a debugger.
/// Output appears in logcat under the "flutter" tag.
void logFailure(String context, Failure failure) {
  final problem = failure.when(
    server: (message, statusCode) =>
        'Backend returned an error${statusCode != null ? ' (HTTP $statusCode)' : ''}: $message',
    network: (message) => 'Network error: $message',
    cache: (message) => 'Cache error: $message',
    unauthorized: (message) => 'Unauthorized (401): ${message ?? ''}',
    forbidden: (message) => 'Forbidden (403): ${message ?? ''}',
    notFound: (message) => 'Not found (404): ${message ?? ''}',
    validation: (message, _) => 'Validation error (422): $message',
    unknown: (message) => 'Unknown error: ${message ?? ''}',
  );

  final cause = failure.when(
    server: (message, statusCode) => statusCode != null && statusCode >= 500
        ? 'The backend crashed handling this request — check `docker-compose logs backend`.'
        : 'The backend rejected the request — check the path (trailing slash!), query params and payload.',
    network: (message) {
      final m = message.toLowerCase();
      if (m.contains('timeout')) {
        return 'The server at ${AppConfig.apiBaseUrl} did not respond. Likely causes, in order: '
            '(1) Windows Firewall blocking inbound port 8000 on the PC, '
            '(2) wrong API_URL / the PC\'s LAN IP changed (run ipconfig), '
            '(3) backend not running (docker-compose ps), '
            '(4) Wi-Fi access point client isolation blocking phone→PC traffic.';
      }
      if (m.contains('internet')) {
        return 'The device has no network connectivity — check Wi-Fi/mobile data.';
      }
      return 'Request could not reach ${AppConfig.apiBaseUrl}.';
    },
    cache: (_) => 'Local Hive cache read/write failed.',
    unauthorized: (_) =>
        'Access token missing/expired and refresh failed — user must sign in again.',
    forbidden: (_) =>
        'The account lacks permission (e.g. unverified email or unapproved instructor).',
    notFound: (_) =>
        'The resource does not exist or the endpoint path is wrong (trailing slash matters: redirect_slashes=False).',
    validation: (_, fieldErrors) =>
        'The request payload failed backend validation${fieldErrors != null ? ': $fieldErrors' : ''}.',
    unknown: (_) => 'Unhandled exception type — see message above.',
  );

  debugPrint('*** FAILURE [$context] ***');
  debugPrint('PROBLEM: $problem');
  debugPrint('CAUSE:   $cause');
  debugPrint('API base URL: ${AppConfig.apiBaseUrl}');
}
