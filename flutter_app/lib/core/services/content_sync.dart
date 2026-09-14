import 'dart:async';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// A course changed on the backend (admin/instructor edit, publish, unpublish,
/// delete). Delivered to the app via a silent FCM data message on the
/// `course-updates` topic.
class CourseSyncEvent {
  /// updated | published | unpublished | deleted
  final String action;

  /// The affected course id, when the push carries one. Null means "something
  /// changed, refresh the catalog".
  final String? courseId;

  const CourseSyncEvent({required this.action, this.courseId});
}

/// A live-class FCM push — either `class.reminder` (the T-15-before-start
/// push) or `class.live_broadcast` (the go-live push), both sent by the
/// backend (app/services/live_reminders.py) on the `live-classes` topic; see
/// docs/superpowers/plans/2026-09-02-live-classes.md Task 5. Delivered as a
/// silent/data FCM message so the app can deep-link straight to the join
/// screen for that class.
class LiveClassSyncEvent {
  final String classId;
  const LiveClassSyncEvent({required this.classId});
}

/// App-wide bus that the FCM layer writes to and the UI listens on. Keeping it
/// here (not in the widget tree) lets a push invalidate Riverpod providers
/// without coupling the messaging service to any screen.
class ContentSyncBus {
  ContentSyncBus._();
  static final ContentSyncBus instance = ContentSyncBus._();

  final _courseController = StreamController<CourseSyncEvent>.broadcast();
  final _liveClassController = StreamController<LiveClassSyncEvent>.broadcast();

  Stream<CourseSyncEvent> get courseStream => _courseController.stream;
  Stream<LiveClassSyncEvent> get liveClassStream => _liveClassController.stream;

  void emitCourse(CourseSyncEvent event) {
    if (!_courseController.isClosed) {
      _courseController.add(event);
    }
  }

  void emitLiveClass(LiveClassSyncEvent event) {
    if (!_liveClassController.isClosed) {
      _liveClassController.add(event);
    }
  }
}

/// Riverpod view of the course bus. A root listener watches this and invalidates
/// the course providers so the catalog/detail refetch the moment a push lands.
final courseSyncProvider = StreamProvider<CourseSyncEvent>((ref) {
  return ContentSyncBus.instance.courseStream;
});

/// Riverpod view of the live-class bus. A root listener (see MyApp in
/// main.dart) watches this and pushes the user straight to the join screen.
final liveClassSyncProvider = StreamProvider<LiveClassSyncEvent>((ref) {
  return ContentSyncBus.instance.liveClassStream;
});
