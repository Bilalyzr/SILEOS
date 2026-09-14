// lib/config/theme_mode_provider.dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../core/storage/prefs_storage.dart';

/// App-wide theme mode (system / light / dark), persisted via SharedPreferences
/// under [StorageKeys.theme]. Driven from the Settings → Appearance section and
/// read by [MaterialApp.themeMode] in main.dart.
final themeModeProvider =
    StateNotifierProvider<ThemeModeNotifier, ThemeMode>((ref) {
  return ThemeModeNotifier()..load();
});

class ThemeModeNotifier extends StateNotifier<ThemeMode> {
  ThemeModeNotifier() : super(ThemeMode.system);

  final PrefsStorage _prefs = PrefsStorage();

  Future<void> load() async {
    state = _fromString(await _prefs.getTheme());
  }

  Future<void> setThemeMode(ThemeMode mode) async {
    state = mode;
    await _prefs.setTheme(_toString(mode));
  }

  static ThemeMode _fromString(String? value) {
    switch (value) {
      case 'light':
        return ThemeMode.light;
      case 'dark':
        return ThemeMode.dark;
      default:
        return ThemeMode.system;
    }
  }

  static String _toString(ThemeMode mode) {
    switch (mode) {
      case ThemeMode.light:
        return 'light';
      case ThemeMode.dark:
        return 'dark';
      case ThemeMode.system:
        return 'system';
    }
  }
}
