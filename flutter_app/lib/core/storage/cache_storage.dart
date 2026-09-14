// lib/core/storage/cache_storage.dart
import 'package:hive_flutter/hive_flutter.dart';

class CacheStorage {
  static final CacheStorage _instance = CacheStorage._internal();
  factory CacheStorage() => _instance;
  CacheStorage._internal();

  static const String _boxName = 'cache_box';
  late Box _box;
  bool _initialized = false;

  Future<void> init() async {
    if (_initialized) return;
    await Hive.initFlutter();
    _box = await Hive.openBox(_boxName);
    _initialized = true;
  }

  Future<void> write(String key, dynamic value) async {
    if (!_initialized) throw StateError('CacheStorage not initialized');
    await _box.put(key, value);
  }

  T? read<T>(String key) {
    if (!_initialized) return null;
    return _box.get(key) as T?;
  }

  Future<void> delete(String key) async {
    if (!_initialized) return;
    await _box.delete(key);
  }

  Future<void> clear() async {
    if (!_initialized) return;
    await _box.clear();
  }

  bool containsKey(String key) {
    if (!_initialized) return false;
    return _box.containsKey(key);
  }

  // Cache with TTL
  Future<void> writeWithExpiry(String key, dynamic value, Duration expiry) async {
    if (!_initialized) throw StateError('CacheStorage not initialized');
    final expiryTime = DateTime.now().add(expiry).toIso8601String();
    await _box.put(key, value);
    await _box.put('${key}_expiry', expiryTime);
  }

  T? readIfNotExpired<T>(String key) {
    if (!_initialized) return null;
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
