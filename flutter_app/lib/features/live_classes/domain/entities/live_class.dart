// lib/features/live_classes/domain/entities/live_class.dart
import 'package:freezed_annotation/freezed_annotation.dart';

part 'live_class.freezed.dart';

/// Mirrors backend `LiveClassStatus` (app/models/live_class.py). Stored by
/// NAME on the wire (repo convention) — see LiveClassModel.fromJson for the
/// string->enum mapping and its `unknown` fallback.
enum LiveClassStatus { scheduled, live, ended, cancelled, unknown }

/// Mirrors backend `RecordingStatus`.
enum RecordingStatus { none, requested, processing, available, failed, unknown }

@freezed
class LiveClassSettings with _$LiveClassSettings {
  const factory LiveClassSettings({
    @Default(true) bool lobbyEnabled,
    @Default(true) bool startMuted,
    @Default(true) bool allowChat,
    @Default(true) bool allowShare,
    @Default(false) bool record,
    @Default(60) int attendanceThresholdPct,
  }) = _LiveClassSettings;
}

/// Domain entity for a live class, matching backend `LiveClassOut` (see
/// docs/superpowers/plans/2026-09-02-live-classes.md, Task 9 binding).
@freezed
class LiveClass with _$LiveClass {
  const factory LiveClass({
    required int id,
    required int courseId,
    int? lessonId,
    required int instructorId,
    required String title,
    String? description,
    required DateTime scheduledStart,
    required DateTime scheduledEnd,
    required String timezone,
    required LiveClassStatus status,
    required String roomName,
    DateTime? startedAt,
    DateTime? endedAt,
    @Default(0) int liveParticipants,
    String? recordingVideoId,
    required RecordingStatus recordingStatus,
    required LiveClassSettings settings,
    required DateTime serverTs,
    @Default(false) bool canStart,
    DateTime? joinOpensAt,
  }) = _LiveClass;

  const LiveClass._();

  /// Countdown target used by ClassCountdown-equivalent widgets: time until
  /// the join window opens (students) or the class start (instructor/live).
  DateTime get countdownTarget => joinOpensAt ?? scheduledStart;

  bool get isLive => status == LiveClassStatus.live;
  bool get isEnded => status == LiveClassStatus.ended;
  bool get isCancelled => status == LiveClassStatus.cancelled;
  bool get hasRecording =>
      recordingStatus == RecordingStatus.available && recordingVideoId != null;
}

/// Mirrors backend `JoinTokenOut`.
@freezed
class LiveClassJoinToken with _$LiveClassJoinToken {
  const factory LiveClassJoinToken({
    required LiveClass classSummary,
    required String roomName,
    required String jitsiUrl,
    required String jwt,
    required int expiresIn,
  }) = _LiveClassJoinToken;
}
