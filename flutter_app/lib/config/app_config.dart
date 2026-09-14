// lib/config/app_config.dart
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
    const customBaseUrl = String.fromEnvironment('API_URL');
    if (customBaseUrl.isNotEmpty) {
      return customBaseUrl;
    }

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

  /// LinkedIn login is deferred: the backend hardcodes the OAuth redirect URI
  /// to the web domain and returns no refresh_token, so the mobile flow cannot
  /// work yet. Flip this once deep links (Phase 3) + backend fixes land.
  static const bool enableLinkedInLogin = false;

  /// Bunny.net Stream Library ID
  static const int bunnyLibraryId = 618286;

  /// Optional Bunny Stream access key for the native player. Prefer leaving
  /// this empty and authenticating playback with short-lived signed tokens
  /// (set BUNNY_TOKEN_AUTH_KEY on the backend) rather than shipping the secret
  /// in the app. Provide via `--dart-define=BUNNY_ACCESS_KEY=...` if needed.
  static const String bunnyAccessKey =
      String.fromEnvironment('BUNNY_ACCESS_KEY');

  /// Set from main() after Firebase.initializeApp() succeeds. Google Sign-In
  /// requires it (google-services.json must be present on Android).
  static bool firebaseAvailable = false;

  static String get apiBaseUrl => baseUrl;

  static ApiClient createApiClient() {
    return ApiClient(baseUrl: apiBaseUrl);
  }
}
