// lib/main.dart
import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:firebase_crashlytics/firebase_crashlytics.dart';
import 'config/app_config.dart';
import 'config/routes.dart';
import 'config/theme.dart';
import 'config/theme_mode_provider.dart';
import 'core/services/content_sync.dart';
import 'core/services/deep_link_service.dart';
import 'features/courses/presentation/providers/course_provider.dart';

void main() {
  // runZonedGuarded captures async errors that escape the Flutter framework.
  // We keep it around for Crashlytics once Firebase is initialized.
  runZonedGuarded<void>(() {
    WidgetsFlutterBinding.ensureInitialized();

    // We no longer await heavy initialization here. It moves to SplashPage
    // so the app can show its first frame (the splash UI) immediately.
    runApp(
      const ProviderScope(
        child: MyApp(),
      ),
    );
  }, (error, stack) {
    // Only report if Firebase was initialized later in the app lifecycle.
    if (AppConfig.enableCrashlytics && AppConfig.firebaseAvailable) {
      FirebaseCrashlytics.instance.recordError(error, stack, fatal: true);
    } else {
      debugPrint('Uncaught zone error: $error\n$stack');
    }
  });
}

class MyApp extends ConsumerStatefulWidget {
  const MyApp({super.key});

  @override
  ConsumerState<MyApp> createState() => _MyAppState();
}

class _MyAppState extends ConsumerState<MyApp> with WidgetsBindingObserver {
  DeepLinkService? _deepLinks;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _deepLinks = DeepLinkService(_handleDeepLink)..init();
  }

  @override
  void dispose() {
    _deepLinks?.dispose();
    WidgetsBinding.instance.removeObserver(this);
    super.dispose();
  }

  /// Routes the email-verification deep link to the verify screen (which
  /// auto-verifies the token). Other links are ignored. Deferred to the next
  /// frame so the router's navigator is ready on cold start.
  void _handleDeepLink(Uri uri) {
    final isVerify = uri.host == 'verify-email' || uri.pathSegments.contains('verify-email');
    if (!isVerify) return;
    final token = uri.queryParameters['token'] ?? '';
    final target = token.isEmpty
        ? '/verify-email'
        : '/verify-email?token=${Uri.encodeQueryComponent(token)}';
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted) ref.read(routerProvider).go(target);
    });
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed) {
      _invalidateCourses();
    }
  }

  void _invalidateCourses({String? courseId}) {
    ref.invalidate(coursesProvider);
    ref.invalidate(myCoursesProvider);
    if (courseId != null) {
      ref.invalidate(courseByIdProvider(courseId));
    }
  }

  @override
  Widget build(BuildContext context) {
    final router = ref.watch(routerProvider);
    final themeMode = ref.watch(themeModeProvider);

    ref.listen(courseSyncProvider, (_, next) {
      final event = next.value;
      if (event != null) {
        _invalidateCourses(courseId: event.courseId);
      }
    });

    // Live Classes: a class.reminder (T-15) or class.live_broadcast (go-live)
    // FCM push navigates straight to the join screen. See
    // core/services/firebase_messaging_service.dart's _handleDataPayload and
    // docs/superpowers/plans/2026-09-02-live-classes.md Task 9.
    ref.listen(liveClassSyncProvider, (_, next) {
      final event = next.value;
      if (event != null) {
        router.push('/live-classes/${event.classId}/join');
      }
    });

    return MaterialApp.router(
      title: 'SashaInfinity LMS',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.lightTheme,
      darkTheme: AppTheme.darkTheme,
      themeMode: themeMode,
      routerConfig: router,
    );
  }
}
