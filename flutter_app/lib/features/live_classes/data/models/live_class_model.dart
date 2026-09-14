// lib/features/live_classes/data/models/live_class_model.dart
//
// JSON mapping for the backend `LiveClassOut` / `JoinTokenOut` schemas
// (app/schemas/live_class.py). Field names mirror the backend exactly via
// @JsonKey — see docs/superpowers/plans/2026-09-02-live-classes.md Task 9.
import 'package:freezed_annotation/freezed_annotation.dart';
import '../../domain/entities/live_class.dart';

part 'live_class_model.freezed.dart';
part 'live_class_model.g.dart';

/// Converts the backend's status string (its Pydantic schema serializes the
/// enum's lowercase `.value`, e.g. "scheduled", "live") into
/// [LiveClassStatus]. The `.toUpperCase()` comparison is defensive
/// case-normalization, not a claim that the wire format is uppercase.
LiveClassStatus _statusFromJson(String? value) {
  switch ((value ?? '').toUpperCase()) {
    case 'SCHEDULED':
      return LiveClassStatus.scheduled;
    case 'LIVE':
      return LiveClassStatus.live;
    case 'ENDED':
      return LiveClassStatus.ended;
    case 'CANCELLED':
      return LiveClassStatus.cancelled;
    default:
      return LiveClassStatus.unknown;
  }
}

String _statusToJson(LiveClassStatus status) => status.name.toUpperCase();

RecordingStatus _recordingStatusFromJson(String? value) {
  switch ((value ?? '').toUpperCase()) {
    case 'NONE':
      return RecordingStatus.none;
    case 'REQUESTED':
      return RecordingStatus.requested;
    case 'PROCESSING':
      return RecordingStatus.processing;
    case 'AVAILABLE':
      return RecordingStatus.available;
    case 'FAILED':
      return RecordingStatus.failed;
    default:
      return RecordingStatus.unknown;
  }
}

String _recordingStatusToJson(RecordingStatus status) => status.name.toUpperCase();

@freezed
class LiveClassSettingsModel with _$LiveClassSettingsModel {
  const factory LiveClassSettingsModel({
    @JsonKey(name: 'lobby_enabled') @Default(true) bool lobbyEnabled,
    @JsonKey(name: 'start_muted') @Default(true) bool startMuted,
    @JsonKey(name: 'allow_chat') @Default(true) bool allowChat,
    @JsonKey(name: 'allow_share') @Default(true) bool allowShare,
    @Default(false) bool record,
    @JsonKey(name: 'attendance_threshold_pct') @Default(60) int attendanceThresholdPct,
  }) = _LiveClassSettingsModel;

  const LiveClassSettingsModel._();

  factory LiveClassSettingsModel.fromJson(Map<String, dynamic> json) =>
      _$LiveClassSettingsModelFromJson(json);

  LiveClassSettings toEntity() => LiveClassSettings(
        lobbyEnabled: lobbyEnabled,
        startMuted: startMuted,
        allowChat: allowChat,
        allowShare: allowShare,
        record: record,
        attendanceThresholdPct: attendanceThresholdPct,
      );
}

/// Mirrors `LiveClassOut` exactly: id, course_id, title, description,
/// scheduled_start/end (ISO Z), timezone, status, room_name,
/// recording_status, recording_video_id, settings, started_at, ended_at,
/// server_ts, can_start, join_opens_at.
@freezed
class LiveClassModel with _$LiveClassModel {
  const factory LiveClassModel({
    required int id,
    @JsonKey(name: 'course_id') required int courseId,
    @JsonKey(name: 'lesson_id') int? lessonId,
    @JsonKey(name: 'instructor_id') required int instructorId,
    required String title,
    String? description,
    @JsonKey(name: 'scheduled_start') required String scheduledStart,
    @JsonKey(name: 'scheduled_end') required String scheduledEnd,
    @Default('Asia/Kolkata') String timezone,
    @JsonKey(name: 'status', fromJson: _statusFromJson, toJson: _statusToJson)
    @Default(LiveClassStatus.scheduled)
    LiveClassStatus status,
    @JsonKey(name: 'room_name') required String roomName,
    @JsonKey(name: 'started_at') String? startedAt,
    @JsonKey(name: 'ended_at') String? endedAt,
    @JsonKey(name: 'live_participants') @Default(0) int liveParticipants,
    @JsonKey(name: 'recording_video_id') String? recordingVideoId,
    @JsonKey(
      name: 'recording_status',
      fromJson: _recordingStatusFromJson,
      toJson: _recordingStatusToJson,
    )
    @Default(RecordingStatus.none)
    RecordingStatus recordingStatus,
    @Default(LiveClassSettingsModel())
    LiveClassSettingsModel settings,
    @JsonKey(name: 'server_ts') required String serverTs,
    @JsonKey(name: 'can_start') @Default(false) bool canStart,
    @JsonKey(name: 'join_opens_at') String? joinOpensAt,
  }) = _LiveClassModel;

  const LiveClassModel._();

  factory LiveClassModel.fromJson(Map<String, dynamic> json) =>
      _$LiveClassModelFromJson(json);

  LiveClass toEntity() => LiveClass(
        id: id,
        courseId: courseId,
        lessonId: lessonId,
        instructorId: instructorId,
        title: title,
        description: description,
        scheduledStart: DateTime.parse(scheduledStart),
        scheduledEnd: DateTime.parse(scheduledEnd),
        timezone: timezone,
        status: status,
        roomName: roomName,
        startedAt: startedAt != null ? DateTime.parse(startedAt!) : null,
        endedAt: endedAt != null ? DateTime.parse(endedAt!) : null,
        liveParticipants: liveParticipants,
        recordingVideoId: recordingVideoId,
        recordingStatus: recordingStatus,
        settings: settings.toEntity(),
        serverTs: DateTime.parse(serverTs),
        canStart: canStart,
        joinOpensAt: joinOpensAt != null ? DateTime.parse(joinOpensAt!) : null,
      );
}

/// Mirrors `JoinTokenOut`: {class_summary, room_name, jitsi_url, jwt,
/// expires_in}.
@freezed
class LiveClassJoinTokenModel with _$LiveClassJoinTokenModel {
  const factory LiveClassJoinTokenModel({
    @JsonKey(name: 'class_summary') required LiveClassModel classSummary,
    @JsonKey(name: 'room_name') required String roomName,
    @JsonKey(name: 'jitsi_url') required String jitsiUrl,
    required String jwt,
    @JsonKey(name: 'expires_in') required int expiresIn,
  }) = _LiveClassJoinTokenModel;

  const LiveClassJoinTokenModel._();

  factory LiveClassJoinTokenModel.fromJson(Map<String, dynamic> json) =>
      _$LiveClassJoinTokenModelFromJson(json);

  LiveClassJoinToken toEntity() => LiveClassJoinToken(
        classSummary: classSummary.toEntity(),
        roomName: roomName,
        jitsiUrl: jitsiUrl,
        jwt: jwt,
        expiresIn: expiresIn,
      );
}

/// Mirrors `GET /classes/{id}/recording-playback` ->
/// {video_id, hls_url, signed, expires_in}.
@freezed
class LiveClassRecordingPlaybackModel with _$LiveClassRecordingPlaybackModel {
  const factory LiveClassRecordingPlaybackModel({
    @JsonKey(name: 'video_id') required String videoId,
    @JsonKey(name: 'hls_url') required String hlsUrl,
    @Default(true) bool signed,
    @JsonKey(name: 'expires_in') @Default(0) int expiresIn,
  }) = _LiveClassRecordingPlaybackModel;

  factory LiveClassRecordingPlaybackModel.fromJson(Map<String, dynamic> json) =>
      _$LiveClassRecordingPlaybackModelFromJson(json);
}
