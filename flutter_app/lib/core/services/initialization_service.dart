import 'dart:async';
import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_crashlytics/firebase_crashlytics.dart';
import 'package:flutter/foundation.dart';
import '../../config/app_config.dart';
import '../storage/cache_storage.dart';
import 'firebase_messaging_service.dart';

class InitializationService {
  static bool _initialized = false;

  static Future<void> initialize() async {
    if (_initialized) return;

    // 1. Initialize storage (Hive)
    final cacheStorage = CacheStorage();
    await cacheStorage.init();

    // 2. Initialize Firebase
    try {
      if (Firebase.apps.isEmpty) {
        await Firebase.initializeApp();
        AppConfig.firebaseAvailable = true;

        await _initCrashlytics();

        // FCM registration touches the network; don't block the first frame on it.
        unawaited(FirebaseMessagingService().init());
        debugPrint('Firebase initialized successfully');
      }
    } catch (e) {
      debugPrint('Firebase initialization failed: $e');
    }

    _initialized = true;
  }

  static Future<void> _initCrashlytics() async {
    final enabled = AppConfig.enableCrashlytics;
    await FirebaseCrashlytics.instance.setCrashlyticsCollectionEnabled(enabled);
    if (!enabled) return;

    FlutterError.onError = FirebaseCrashlytics.instance.recordFlutterFatalError;
    PlatformDispatcher.instance.onError = (error, stack) {
      FirebaseCrashlytics.instance.recordError(error, stack, fatal: true);
      return true;
    };
  }
}
