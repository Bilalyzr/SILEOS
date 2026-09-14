import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'content_sync.dart';

/// Topic every install subscribes to; the backend pushes course-change events
/// here so the catalog/detail refetch without a manual pull-to-refresh.
const String kCourseUpdatesTopic = 'course-updates';

/// Topic every install subscribes to; the backend
/// (app/services/live_reminders.py) publishes `class.reminder` (T-15) and
/// `class.live_broadcast` (go-live) messages here via
/// `messaging.Message(topic="live-classes", ...)`.
const String kLiveClassesTopic = 'live-classes';

@pragma('vm:entry-point')
Future<void> _firebaseMessagingBackgroundHandler(RemoteMessage message) async {
  // If you're going to use other Firebase services in the background, such as Firestore,
  // make sure you call `initializeApp` before using other Firebase services.
  // Runs in a separate isolate: the UI's Riverpod container isn't alive here,
  // so we can't invalidate providers. The app's resume-time refresh (see MyApp)
  // covers content that changed while the app was backgrounded.
  debugPrint('Handling a background message: ${message.messageId}');
}

class FirebaseMessagingService {
  final FirebaseMessaging _firebaseMessaging = FirebaseMessaging.instance;
  final FlutterLocalNotificationsPlugin _localNotificationsPlugin =
      FlutterLocalNotificationsPlugin();

  Future<void> init() async {
    // Request permission
    NotificationSettings settings = await _firebaseMessaging.requestPermission(
      alert: true,
      badge: true,
      provisional: false,
      sound: true,
    );

    if (settings.authorizationStatus == AuthorizationStatus.authorized) {
      debugPrint('User granted permission');
    } else {
      debugPrint('User declined or has not accepted permission');
    }

    // Set up foreground notification presentation options
    await _firebaseMessaging.setForegroundNotificationPresentationOptions(
      alert: true,
      badge: true,
      sound: true,
    );

    // Get FCM Token
    try {
      String? token = await _firebaseMessaging.getToken();
      // Token is a credential — never log it in release. Log only its presence.
      if (kDebugMode) debugPrint('FCM Token acquired: ${token != null}');
      // Here you would typically send this token to your backend
    } catch (e) {
      if (kDebugMode) debugPrint('Failed to get FCM token: $e');
    }

    // Subscribe to broadcast content topics. Best-effort: not supported on web.
    try {
      await _firebaseMessaging.subscribeToTopic(kCourseUpdatesTopic);
    } catch (e) {
      debugPrint('Failed to subscribe to $kCourseUpdatesTopic: $e');
    }
    try {
      await _firebaseMessaging.subscribeToTopic(kLiveClassesTopic);
    } catch (e) {
      debugPrint('Failed to subscribe to $kLiveClassesTopic: $e');
    }

    // Handle background messages
    FirebaseMessaging.onBackgroundMessage(_firebaseMessagingBackgroundHandler);

    // A notification that opened the app, or a data push received while the app
    // was in the foreground/terminated — route any course-change payloads to
    // the content bus so the UI can refetch.
    final initialMessage = await _firebaseMessaging.getInitialMessage();
    if (initialMessage != null) _handleDataPayload(initialMessage.data);
    FirebaseMessaging.onMessageOpenedApp.listen((m) => _handleDataPayload(m.data));

    // Initialize local notifications for foreground display
    const AndroidInitializationSettings initializationSettingsAndroid =
        AndroidInitializationSettings('@mipmap/ic_launcher');
    const DarwinInitializationSettings initializationSettingsIOS =
        DarwinInitializationSettings();
    const InitializationSettings initializationSettings = InitializationSettings(
      android: initializationSettingsAndroid,
      iOS: initializationSettingsIOS,
    );
    await _localNotificationsPlugin.initialize(
      initializationSettings,
    );

    // Create Android Notification Channel
    const AndroidNotificationChannel channel = AndroidNotificationChannel(
      'high_importance_channel', // id
      'High Importance Notifications', // title
      description: 'This channel is used for important notifications.',
      importance: Importance.max,
    );

    await _localNotificationsPlugin
        .resolvePlatformSpecificImplementation<AndroidFlutterLocalNotificationsPlugin>()
        ?.createNotificationChannel(channel);

    // Handle foreground messages
    FirebaseMessaging.onMessage.listen((RemoteMessage message) {
      // Act on any data payload first (e.g. course.updated → live refresh).
      _handleDataPayload(message.data);

      RemoteNotification? notification = message.notification;
      AndroidNotification? android = message.notification?.android;

      if (notification != null && android != null) {
        _localNotificationsPlugin.show(
          notification.hashCode,
          notification.title,
          notification.body,
          NotificationDetails(
            android: AndroidNotificationDetails(
              channel.id,
              channel.name,
              channelDescription: channel.description,
              icon: android.smallIcon,
            ),
          ),
        );
      }
    });
  }

  /// Translates an FCM data payload into a content-bus event. Unknown payloads
  /// are ignored. Values arrive as strings (FCM data is string-only).
  void _handleDataPayload(Map<String, dynamic> data) {
    final type = data['type'];
    if (type == 'course.updated') {
      ContentSyncBus.instance.emitCourse(
        CourseSyncEvent(
          action: (data['action'] ?? 'updated').toString(),
          courseId: data['course_id']?.toString(),
        ),
      );
    } else if (type == 'class.reminder' || type == 'class.live_broadcast') {
      // Live Classes deep link. The backend (app/services/live_reminders.py)
      // sends two distinct data.type values on the `live-classes` topic:
      // "class.reminder" (the T-15-before-start push) and
      // "class.live_broadcast" (the go-live push) — see
      // docs/superpowers/plans/2026-09-02-live-classes.md Task 5/9. Both
      // carry class_id and both mean the same thing to the app: deep-link to
      // the join screen. The root listener in main.dart does that via
      // go_router.
      final classId = data['class_id']?.toString();
      if (classId != null && classId.isNotEmpty) {
        ContentSyncBus.instance.emitLiveClass(LiveClassSyncEvent(classId: classId));
      }
    }
  }
}
