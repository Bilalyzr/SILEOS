import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';
import '../../config/app_config.dart';
import '../auth/session_events.dart';
import '../storage/cache_storage.dart';
import '../storage/secure_storage.dart';
import 'api_client.dart';
import 'interceptors.dart';

part 'network_provider.g.dart';

@riverpod
FlutterSecureStorage secureStorage(SecureStorageRef ref) {
  // Return the SAME shared instance the login/register flow writes through,
  // so the read path (AuthInterceptor) can never drift from the write path.
  // See SecureStorage.raw for why this matters on Android.
  return SecureStorage.raw;
}

@riverpod
CacheStorage cacheStorage(CacheStorageRef ref) {
  // Assuming CacheStorage was initialized in main() and is a singleton or we just return a new instance (since it wraps Hive box which is cached)
  return CacheStorage();
}

@riverpod
ApiClient apiClient(ApiClientRef ref) {
  final secureStorage = ref.watch(secureStorageProvider);
  final cache = ref.watch(cacheStorageProvider);
  
  final client = ApiClient(
    baseUrl: AppConfig.apiBaseUrl,
    cacheStorage: cache,
  );
  
  // Add auth interceptors
  client.dio.interceptors.addAll([
    TrailingSlashInterceptor(),
    AuthInterceptor(secureStorage),
    RefreshTokenInterceptor(
      secureStorage: secureStorage,
      dio: client.dio,
      onLogout: () async {
        // Session is unrecoverable (no/invalid refresh token): clear all
        // stored credentials and notify the auth layer.
        await secureStorage.deleteAll();
        ref.read(sessionExpiredProvider.notifier).expire();
      },
    ),
  ]);
  
  return client;
}
