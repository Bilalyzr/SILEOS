// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'live_class_model.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

_$LiveClassSettingsModelImpl _$$LiveClassSettingsModelImplFromJson(
        Map<String, dynamic> json) =>
    _$LiveClassSettingsModelImpl(
      lobbyEnabled: json['lobby_enabled'] as bool? ?? true,
      startMuted: json['start_muted'] as bool? ?? true,
      allowChat: json['allow_chat'] as bool? ?? true,
      allowShare: json['allow_share'] as bool? ?? true,
      record: json['record'] as bool? ?? false,
      attendanceThresholdPct:
          (json['attendance_threshold_pct'] as num?)?.toInt() ?? 60,
    );

Map<String, dynamic> _$$LiveClassSettingsModelImplToJson(
        _$LiveClassSettingsModelImpl instance) =>
    <String, dynamic>{
      'lobby_enabled': instance.lobbyEnabled,
      'start_muted': instance.startMuted,
      'allow_chat': instance.allowChat,
      'allow_share': instance.allowShare,
      'record': instance.record,
      'attendance_threshold_pct': instance.attendanceThresholdPct,
    };

_$LiveClassModelImpl _$$LiveClassModelImplFromJson(Map<String, dynamic> json) =>
    _$LiveClassModelImpl(
      id: (json['id'] as num).toInt(),
      courseId: (json['course_id'] as num).toInt(),
      lessonId: (json['lesson_id'] as num?)?.toInt(),
      instructorId: (json['instructor_id'] as num).toInt(),
      title: json['title'] as String,
      description: json['description'] as String?,
      scheduledStart: json['scheduled_start'] as String,
      scheduledEnd: json['scheduled_end'] as String,
      timezone: json['timezone'] as String? ?? 'Asia/Kolkata',
      status: json['status'] == null
          ? LiveClassStatus.scheduled
          : _statusFromJson(json['status'] as String?),
      roomName: json['room_name'] as String,
      startedAt: json['started_at'] as String?,
      endedAt: json['ended_at'] as String?,
      liveParticipants: (json['live_participants'] as num?)?.toInt() ?? 0,
      recordingVideoId: json['recording_video_id'] as String?,
      recordingStatus: json['recording_status'] == null
          ? RecordingStatus.none
          : _recordingStatusFromJson(json['recording_status'] as String?),
      settings: json['settings'] == null
          ? const LiveClassSettingsModel()
          : LiveClassSettingsModel.fromJson(
              json['settings'] as Map<String, dynamic>),
      serverTs: json['server_ts'] as String,
      canStart: json['can_start'] as bool? ?? false,
      joinOpensAt: json['join_opens_at'] as String?,
    );

Map<String, dynamic> _$$LiveClassModelImplToJson(
        _$LiveClassModelImpl instance) =>
    <String, dynamic>{
      'id': instance.id,
      'course_id': instance.courseId,
      'lesson_id': instance.lessonId,
      'instructor_id': instance.instructorId,
      'title': instance.title,
      'description': instance.description,
      'scheduled_start': instance.scheduledStart,
      'scheduled_end': instance.scheduledEnd,
      'timezone': instance.timezone,
      'status': _statusToJson(instance.status),
      'room_name': instance.roomName,
      'started_at': instance.startedAt,
      'ended_at': instance.endedAt,
      'live_participants': instance.liveParticipants,
      'recording_video_id': instance.recordingVideoId,
      'recording_status': _recordingStatusToJson(instance.recordingStatus),
      'settings': instance.settings,
      'server_ts': instance.serverTs,
      'can_start': instance.canStart,
      'join_opens_at': instance.joinOpensAt,
    };

_$LiveClassJoinTokenModelImpl _$$LiveClassJoinTokenModelImplFromJson(
        Map<String, dynamic> json) =>
    _$LiveClassJoinTokenModelImpl(
      classSummary: LiveClassModel.fromJson(
          json['class_summary'] as Map<String, dynamic>),
      roomName: json['room_name'] as String,
      jitsiUrl: json['jitsi_url'] as String,
      jwt: json['jwt'] as String,
      expiresIn: (json['expires_in'] as num).toInt(),
    );

Map<String, dynamic> _$$LiveClassJoinTokenModelImplToJson(
        _$LiveClassJoinTokenModelImpl instance) =>
    <String, dynamic>{
      'class_summary': instance.classSummary,
      'room_name': instance.roomName,
      'jitsi_url': instance.jitsiUrl,
      'jwt': instance.jwt,
      'expires_in': instance.expiresIn,
    };

_$LiveClassRecordingPlaybackModelImpl
    _$$LiveClassRecordingPlaybackModelImplFromJson(Map<String, dynamic> json) =>
        _$LiveClassRecordingPlaybackModelImpl(
          videoId: json['video_id'] as String,
          hlsUrl: json['hls_url'] as String,
          signed: json['signed'] as bool? ?? true,
          expiresIn: (json['expires_in'] as num?)?.toInt() ?? 0,
        );

Map<String, dynamic> _$$LiveClassRecordingPlaybackModelImplToJson(
        _$LiveClassRecordingPlaybackModelImpl instance) =>
    <String, dynamic>{
      'video_id': instance.videoId,
      'hls_url': instance.hlsUrl,
      'signed': instance.signed,
      'expires_in': instance.expiresIn,
    };
