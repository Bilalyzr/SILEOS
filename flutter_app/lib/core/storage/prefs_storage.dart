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
