// lib/core/storage/secure_storage.dart
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import '../constants/storage_keys.dart';

class SecureStorage {
  // SINGLE source of truth for secure-storage configuration. Both the auth
  // write path (login/register) and the read path (AuthInterceptor via
  // secureStorageProvider) MUST use this exact instance — on Android these
  // options pick a specific backend, and any mismatch makes the interceptor
  // read null and send no Authorization header (every protected call 401s).
  static const AndroidOptions _androidOptions = AndroidOptions(
    encryptedSharedPreferences: true,
  );
  static const IOSOptions _iosOptions = IOSOptions(
    accessibility: KeychainAccessibility.first_unlock,
  );

  /// The shared, correctly-configured storage. Use this everywhere a raw
  /// FlutterSecureStorage is needed so the config can never drift.
  static const FlutterSecureStorage raw = FlutterSecureStorage(
    aOptions: _androidOptions,
    iOptions: _iosOptions,
  );

  final FlutterSecureStorage _storage;

  SecureStorage() : _storage = raw;

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
