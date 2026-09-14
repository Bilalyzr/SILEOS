// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint
// ignore_for_file: unused_element, deprecated_member_use, deprecated_member_use_from_same_package, use_function_type_syntax_for_parameters, unnecessary_const, avoid_init_to_null, invalid_override_different_default_values_named, prefer_expression_function_bodies, annotate_overrides, invalid_annotation_target, unnecessary_question_mark

part of 'live_class_model.dart';

// **************************************************************************
// FreezedGenerator
// **************************************************************************

T _$identity<T>(T value) => value;

final _privateConstructorUsedError = UnsupportedError(
    'It seems like you constructed your class using `MyClass._()`. This constructor is only meant to be used by freezed and you are not supposed to need it nor use it.\nPlease check the documentation here for more information: https://github.com/rrousselGit/freezed#adding-getters-and-methods-to-our-models');

LiveClassSettingsModel _$LiveClassSettingsModelFromJson(
    Map<String, dynamic> json) {
  return _LiveClassSettingsModel.fromJson(json);
}

/// @nodoc
mixin _$LiveClassSettingsModel {
  @JsonKey(name: 'lobby_enabled')
  bool get lobbyEnabled => throw _privateConstructorUsedError;
  @JsonKey(name: 'start_muted')
  bool get startMuted => throw _privateConstructorUsedError;
  @JsonKey(name: 'allow_chat')
  bool get allowChat => throw _privateConstructorUsedError;
  @JsonKey(name: 'allow_share')
  bool get allowShare => throw _privateConstructorUsedError;
  bool get record => throw _privateConstructorUsedError;
  @JsonKey(name: 'attendance_threshold_pct')
  int get attendanceThresholdPct => throw _privateConstructorUsedError;

  /// Serializes this LiveClassSettingsModel to a JSON map.
  Map<String, dynamic> toJson() => throw _privateConstructorUsedError;

  /// Create a copy of LiveClassSettingsModel
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  $LiveClassSettingsModelCopyWith<LiveClassSettingsModel> get copyWith =>
      throw _privateConstructorUsedError;
}

/// @nodoc
abstract class $LiveClassSettingsModelCopyWith<$Res> {
  factory $LiveClassSettingsModelCopyWith(LiveClassSettingsModel value,
          $Res Function(LiveClassSettingsModel) then) =
      _$LiveClassSettingsModelCopyWithImpl<$Res, LiveClassSettingsModel>;
  @useResult
  $Res call(
      {@JsonKey(name: 'lobby_enabled') bool lobbyEnabled,
      @JsonKey(name: 'start_muted') bool startMuted,
      @JsonKey(name: 'allow_chat') bool allowChat,
      @JsonKey(name: 'allow_share') bool allowShare,
      bool record,
      @JsonKey(name: 'attendance_threshold_pct') int attendanceThresholdPct});
}

/// @nodoc
class _$LiveClassSettingsModelCopyWithImpl<$Res,
        $Val extends LiveClassSettingsModel>
    implements $LiveClassSettingsModelCopyWith<$Res> {
  _$LiveClassSettingsModelCopyWithImpl(this._value, this._then);

  // ignore: unused_field
  final $Val _value;
  // ignore: unused_field
  final $Res Function($Val) _then;

  /// Create a copy of LiveClassSettingsModel
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? lobbyEnabled = null,
    Object? startMuted = null,
    Object? allowChat = null,
    Object? allowShare = null,
    Object? record = null,
    Object? attendanceThresholdPct = null,
  }) {
    return _then(_value.copyWith(
      lobbyEnabled: null == lobbyEnabled
          ? _value.lobbyEnabled
          : lobbyEnabled // ignore: cast_nullable_to_non_nullable
              as bool,
      startMuted: null == startMuted
          ? _value.startMuted
          : startMuted // ignore: cast_nullable_to_non_nullable
              as bool,
      allowChat: null == allowChat
          ? _value.allowChat
          : allowChat // ignore: cast_nullable_to_non_nullable
              as bool,
      allowShare: null == allowShare
          ? _value.allowShare
          : allowShare // ignore: cast_nullable_to_non_nullable
              as bool,
      record: null == record
          ? _value.record
          : record // ignore: cast_nullable_to_non_nullable
              as bool,
      attendanceThresholdPct: null == attendanceThresholdPct
          ? _value.attendanceThresholdPct
          : attendanceThresholdPct // ignore: cast_nullable_to_non_nullable
              as int,
    ) as $Val);
  }
}

/// @nodoc
abstract class _$$LiveClassSettingsModelImplCopyWith<$Res>
    implements $LiveClassSettingsModelCopyWith<$Res> {
  factory _$$LiveClassSettingsModelImplCopyWith(
          _$LiveClassSettingsModelImpl value,
          $Res Function(_$LiveClassSettingsModelImpl) then) =
      __$$LiveClassSettingsModelImplCopyWithImpl<$Res>;
  @override
  @useResult
  $Res call(
      {@JsonKey(name: 'lobby_enabled') bool lobbyEnabled,
      @JsonKey(name: 'start_muted') bool startMuted,
      @JsonKey(name: 'allow_chat') bool allowChat,
      @JsonKey(name: 'allow_share') bool allowShare,
      bool record,
      @JsonKey(name: 'attendance_threshold_pct') int attendanceThresholdPct});
}

/// @nodoc
class __$$LiveClassSettingsModelImplCopyWithImpl<$Res>
    extends _$LiveClassSettingsModelCopyWithImpl<$Res,
        _$LiveClassSettingsModelImpl>
    implements _$$LiveClassSettingsModelImplCopyWith<$Res> {
  __$$LiveClassSettingsModelImplCopyWithImpl(
      _$LiveClassSettingsModelImpl _value,
      $Res Function(_$LiveClassSettingsModelImpl) _then)
      : super(_value, _then);

  /// Create a copy of LiveClassSettingsModel
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? lobbyEnabled = null,
    Object? startMuted = null,
    Object? allowChat = null,
    Object? allowShare = null,
    Object? record = null,
    Object? attendanceThresholdPct = null,
  }) {
    return _then(_$LiveClassSettingsModelImpl(
      lobbyEnabled: null == lobbyEnabled
          ? _value.lobbyEnabled
          : lobbyEnabled // ignore: cast_nullable_to_non_nullable
              as bool,
      startMuted: null == startMuted
          ? _value.startMuted
          : startMuted // ignore: cast_nullable_to_non_nullable
              as bool,
      allowChat: null == allowChat
          ? _value.allowChat
          : allowChat // ignore: cast_nullable_to_non_nullable
              as bool,
      allowShare: null == allowShare
          ? _value.allowShare
          : allowShare // ignore: cast_nullable_to_non_nullable
              as bool,
      record: null == record
          ? _value.record
          : record // ignore: cast_nullable_to_non_nullable
              as bool,
      attendanceThresholdPct: null == attendanceThresholdPct
          ? _value.attendanceThresholdPct
          : attendanceThresholdPct // ignore: cast_nullable_to_non_nullable
              as int,
    ));
  }
}

/// @nodoc
@JsonSerializable()
class _$LiveClassSettingsModelImpl extends _LiveClassSettingsModel {
  const _$LiveClassSettingsModelImpl(
      {@JsonKey(name: 'lobby_enabled') this.lobbyEnabled = true,
      @JsonKey(name: 'start_muted') this.startMuted = true,
      @JsonKey(name: 'allow_chat') this.allowChat = true,
      @JsonKey(name: 'allow_share') this.allowShare = true,
      this.record = false,
      @JsonKey(name: 'attendance_threshold_pct')
      this.attendanceThresholdPct = 60})
      : super._();

  factory _$LiveClassSettingsModelImpl.fromJson(Map<String, dynamic> json) =>
      _$$LiveClassSettingsModelImplFromJson(json);

  @override
  @JsonKey(name: 'lobby_enabled')
  final bool lobbyEnabled;
  @override
  @JsonKey(name: 'start_muted')
  final bool startMuted;
  @override
  @JsonKey(name: 'allow_chat')
  final bool allowChat;
  @override
  @JsonKey(name: 'allow_share')
  final bool allowShare;
  @override
  @JsonKey()
  final bool record;
  @override
  @JsonKey(name: 'attendance_threshold_pct')
  final int attendanceThresholdPct;

  @override
  String toString() {
    return 'LiveClassSettingsModel(lobbyEnabled: $lobbyEnabled, startMuted: $startMuted, allowChat: $allowChat, allowShare: $allowShare, record: $record, attendanceThresholdPct: $attendanceThresholdPct)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$LiveClassSettingsModelImpl &&
            (identical(other.lobbyEnabled, lobbyEnabled) ||
                other.lobbyEnabled == lobbyEnabled) &&
            (identical(other.startMuted, startMuted) ||
                other.startMuted == startMuted) &&
            (identical(other.allowChat, allowChat) ||
                other.allowChat == allowChat) &&
            (identical(other.allowShare, allowShare) ||
                other.allowShare == allowShare) &&
            (identical(other.record, record) || other.record == record) &&
            (identical(other.attendanceThresholdPct, attendanceThresholdPct) ||
                other.attendanceThresholdPct == attendanceThresholdPct));
  }

  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  int get hashCode => Object.hash(runtimeType, lobbyEnabled, startMuted,
      allowChat, allowShare, record, attendanceThresholdPct);

  /// Create a copy of LiveClassSettingsModel
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  @pragma('vm:prefer-inline')
  _$$LiveClassSettingsModelImplCopyWith<_$LiveClassSettingsModelImpl>
      get copyWith => __$$LiveClassSettingsModelImplCopyWithImpl<
          _$LiveClassSettingsModelImpl>(this, _$identity);

  @override
  Map<String, dynamic> toJson() {
    return _$$LiveClassSettingsModelImplToJson(
      this,
    );
  }
}

abstract class _LiveClassSettingsModel extends LiveClassSettingsModel {
  const factory _LiveClassSettingsModel(
      {@JsonKey(name: 'lobby_enabled') final bool lobbyEnabled,
      @JsonKey(name: 'start_muted') final bool startMuted,
      @JsonKey(name: 'allow_chat') final bool allowChat,
      @JsonKey(name: 'allow_share') final bool allowShare,
      final bool record,
      @JsonKey(name: 'attendance_threshold_pct')
      final int attendanceThresholdPct}) = _$LiveClassSettingsModelImpl;
  const _LiveClassSettingsModel._() : super._();

  factory _LiveClassSettingsModel.fromJson(Map<String, dynamic> json) =
      _$LiveClassSettingsModelImpl.fromJson;

  @override
  @JsonKey(name: 'lobby_enabled')
  bool get lobbyEnabled;
  @override
  @JsonKey(name: 'start_muted')
  bool get startMuted;
  @override
  @JsonKey(name: 'allow_chat')
  bool get allowChat;
  @override
  @JsonKey(name: 'allow_share')
  bool get allowShare;
  @override
  bool get record;
  @override
  @JsonKey(name: 'attendance_threshold_pct')
  int get attendanceThresholdPct;

  /// Create a copy of LiveClassSettingsModel
  /// with the given fields replaced by the non-null parameter values.
  @override
  @JsonKey(includeFromJson: false, includeToJson: false)
  _$$LiveClassSettingsModelImplCopyWith<_$LiveClassSettingsModelImpl>
      get copyWith => throw _privateConstructorUsedError;
}

LiveClassModel _$LiveClassModelFromJson(Map<String, dynamic> json) {
  return _LiveClassModel.fromJson(json);
}

/// @nodoc
mixin _$LiveClassModel {
  int get id => throw _privateConstructorUsedError;
  @JsonKey(name: 'course_id')
  int get courseId => throw _privateConstructorUsedError;
  @JsonKey(name: 'lesson_id')
  int? get lessonId => throw _privateConstructorUsedError;
  @JsonKey(name: 'instructor_id')
  int get instructorId => throw _privateConstructorUsedError;
  String get title => throw _privateConstructorUsedError;
  String? get description => throw _privateConstructorUsedError;
  @JsonKey(name: 'scheduled_start')
  String get scheduledStart => throw _privateConstructorUsedError;
  @JsonKey(name: 'scheduled_end')
  String get scheduledEnd => throw _privateConstructorUsedError;
  String get timezone => throw _privateConstructorUsedError;
  @JsonKey(name: 'status', fromJson: _statusFromJson, toJson: _statusToJson)
  LiveClassStatus get status => throw _privateConstructorUsedError;
  @JsonKey(name: 'room_name')
  String get roomName => throw _privateConstructorUsedError;
  @JsonKey(name: 'started_at')
  String? get startedAt => throw _privateConstructorUsedError;
  @JsonKey(name: 'ended_at')
  String? get endedAt => throw _privateConstructorUsedError;
  @JsonKey(name: 'live_participants')
  int get liveParticipants => throw _privateConstructorUsedError;
  @JsonKey(name: 'recording_video_id')
  String? get recordingVideoId => throw _privateConstructorUsedError;
  @JsonKey(
      name: 'recording_status',
      fromJson: _recordingStatusFromJson,
      toJson: _recordingStatusToJson)
  RecordingStatus get recordingStatus => throw _privateConstructorUsedError;
  LiveClassSettingsModel get settings => throw _privateConstructorUsedError;
  @JsonKey(name: 'server_ts')
  String get serverTs => throw _privateConstructorUsedError;
  @JsonKey(name: 'can_start')
  bool get canStart => throw _privateConstructorUsedError;
  @JsonKey(name: 'join_opens_at')
  String? get joinOpensAt => throw _privateConstructorUsedError;

  /// Serializes this LiveClassModel to a JSON map.
  Map<String, dynamic> toJson() => throw _privateConstructorUsedError;

  /// Create a copy of LiveClassModel
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  $LiveClassModelCopyWith<LiveClassModel> get copyWith =>
      throw _privateConstructorUsedError;
}

/// @nodoc
abstract class $LiveClassModelCopyWith<$Res> {
  factory $LiveClassModelCopyWith(
          LiveClassModel value, $Res Function(LiveClassModel) then) =
      _$LiveClassModelCopyWithImpl<$Res, LiveClassModel>;
  @useResult
  $Res call(
      {int id,
      @JsonKey(name: 'course_id') int courseId,
      @JsonKey(name: 'lesson_id') int? lessonId,
      @JsonKey(name: 'instructor_id') int instructorId,
      String title,
      String? description,
      @JsonKey(name: 'scheduled_start') String scheduledStart,
      @JsonKey(name: 'scheduled_end') String scheduledEnd,
      String timezone,
      @JsonKey(name: 'status', fromJson: _statusFromJson, toJson: _statusToJson)
      LiveClassStatus status,
      @JsonKey(name: 'room_name') String roomName,
      @JsonKey(name: 'started_at') String? startedAt,
      @JsonKey(name: 'ended_at') String? endedAt,
      @JsonKey(name: 'live_participants') int liveParticipants,
      @JsonKey(name: 'recording_video_id') String? recordingVideoId,
      @JsonKey(
          name: 'recording_status',
          fromJson: _recordingStatusFromJson,
          toJson: _recordingStatusToJson)
      RecordingStatus recordingStatus,
      LiveClassSettingsModel settings,
      @JsonKey(name: 'server_ts') String serverTs,
      @JsonKey(name: 'can_start') bool canStart,
      @JsonKey(name: 'join_opens_at') String? joinOpensAt});

  $LiveClassSettingsModelCopyWith<$Res> get settings;
}

/// @nodoc
class _$LiveClassModelCopyWithImpl<$Res, $Val extends LiveClassModel>
    implements $LiveClassModelCopyWith<$Res> {
  _$LiveClassModelCopyWithImpl(this._value, this._then);

  // ignore: unused_field
  final $Val _value;
  // ignore: unused_field
  final $Res Function($Val) _then;

  /// Create a copy of LiveClassModel
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? id = null,
    Object? courseId = null,
    Object? lessonId = freezed,
    Object? instructorId = null,
    Object? title = null,
    Object? description = freezed,
    Object? scheduledStart = null,
    Object? scheduledEnd = null,
    Object? timezone = null,
    Object? status = null,
    Object? roomName = null,
    Object? startedAt = freezed,
    Object? endedAt = freezed,
    Object? liveParticipants = null,
    Object? recordingVideoId = freezed,
    Object? recordingStatus = null,
    Object? settings = null,
    Object? serverTs = null,
    Object? canStart = null,
    Object? joinOpensAt = freezed,
  }) {
    return _then(_value.copyWith(
      id: null == id
          ? _value.id
          : id // ignore: cast_nullable_to_non_nullable
              as int,
      courseId: null == courseId
          ? _value.courseId
          : courseId // ignore: cast_nullable_to_non_nullable
              as int,
      lessonId: freezed == lessonId
          ? _value.lessonId
          : lessonId // ignore: cast_nullable_to_non_nullable
              as int?,
      instructorId: null == instructorId
          ? _value.instructorId
          : instructorId // ignore: cast_nullable_to_non_nullable
              as int,
      title: null == title
          ? _value.title
          : title // ignore: cast_nullable_to_non_nullable
              as String,
      description: freezed == description
          ? _value.description
          : description // ignore: cast_nullable_to_non_nullable
              as String?,
      scheduledStart: null == scheduledStart
          ? _value.scheduledStart
          : scheduledStart // ignore: cast_nullable_to_non_nullable
              as String,
      scheduledEnd: null == scheduledEnd
          ? _value.scheduledEnd
          : scheduledEnd // ignore: cast_nullable_to_non_nullable
              as String,
      timezone: null == timezone
          ? _value.timezone
          : timezone // ignore: cast_nullable_to_non_nullable
              as String,
      status: null == status
          ? _value.status
          : status // ignore: cast_nullable_to_non_nullable
              as LiveClassStatus,
      roomName: null == roomName
          ? _value.roomName
          : roomName // ignore: cast_nullable_to_non_nullable
              as String,
      startedAt: freezed == startedAt
          ? _value.startedAt
          : startedAt // ignore: cast_nullable_to_non_nullable
              as String?,
      endedAt: freezed == endedAt
          ? _value.endedAt
          : endedAt // ignore: cast_nullable_to_non_nullable
              as String?,
      liveParticipants: null == liveParticipants
          ? _value.liveParticipants
          : liveParticipants // ignore: cast_nullable_to_non_nullable
              as int,
      recordingVideoId: freezed == recordingVideoId
          ? _value.recordingVideoId
          : recordingVideoId // ignore: cast_nullable_to_non_nullable
              as String?,
      recordingStatus: null == recordingStatus
          ? _value.recordingStatus
          : recordingStatus // ignore: cast_nullable_to_non_nullable
              as RecordingStatus,
      settings: null == settings
          ? _value.settings
          : settings // ignore: cast_nullable_to_non_nullable
              as LiveClassSettingsModel,
      serverTs: null == serverTs
          ? _value.serverTs
          : serverTs // ignore: cast_nullable_to_non_nullable
              as String,
      canStart: null == canStart
          ? _value.canStart
          : canStart // ignore: cast_nullable_to_non_nullable
              as bool,
      joinOpensAt: freezed == joinOpensAt
          ? _value.joinOpensAt
          : joinOpensAt // ignore: cast_nullable_to_non_nullable
              as String?,
    ) as $Val);
  }

  /// Create a copy of LiveClassModel
  /// with the given fields replaced by the non-null parameter values.
  @override
  @pragma('vm:prefer-inline')
  $LiveClassSettingsModelCopyWith<$Res> get settings {
    return $LiveClassSettingsModelCopyWith<$Res>(_value.settings, (value) {
      return _then(_value.copyWith(settings: value) as $Val);
    });
  }
}

/// @nodoc
abstract class _$$LiveClassModelImplCopyWith<$Res>
    implements $LiveClassModelCopyWith<$Res> {
  factory _$$LiveClassModelImplCopyWith(_$LiveClassModelImpl value,
          $Res Function(_$LiveClassModelImpl) then) =
      __$$LiveClassModelImplCopyWithImpl<$Res>;
  @override
  @useResult
  $Res call(
      {int id,
      @JsonKey(name: 'course_id') int courseId,
      @JsonKey(name: 'lesson_id') int? lessonId,
      @JsonKey(name: 'instructor_id') int instructorId,
      String title,
      String? description,
      @JsonKey(name: 'scheduled_start') String scheduledStart,
      @JsonKey(name: 'scheduled_end') String scheduledEnd,
      String timezone,
      @JsonKey(name: 'status', fromJson: _statusFromJson, toJson: _statusToJson)
      LiveClassStatus status,
      @JsonKey(name: 'room_name') String roomName,
      @JsonKey(name: 'started_at') String? startedAt,
      @JsonKey(name: 'ended_at') String? endedAt,
      @JsonKey(name: 'live_participants') int liveParticipants,
      @JsonKey(name: 'recording_video_id') String? recordingVideoId,
      @JsonKey(
          name: 'recording_status',
          fromJson: _recordingStatusFromJson,
          toJson: _recordingStatusToJson)
      RecordingStatus recordingStatus,
      LiveClassSettingsModel settings,
      @JsonKey(name: 'server_ts') String serverTs,
      @JsonKey(name: 'can_start') bool canStart,
      @JsonKey(name: 'join_opens_at') String? joinOpensAt});

  @override
  $LiveClassSettingsModelCopyWith<$Res> get settings;
}

/// @nodoc
class __$$LiveClassModelImplCopyWithImpl<$Res>
    extends _$LiveClassModelCopyWithImpl<$Res, _$LiveClassModelImpl>
    implements _$$LiveClassModelImplCopyWith<$Res> {
  __$$LiveClassModelImplCopyWithImpl(
      _$LiveClassModelImpl _value, $Res Function(_$LiveClassModelImpl) _then)
      : super(_value, _then);

  /// Create a copy of LiveClassModel
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? id = null,
    Object? courseId = null,
    Object? lessonId = freezed,
    Object? instructorId = null,
    Object? title = null,
    Object? description = freezed,
    Object? scheduledStart = null,
    Object? scheduledEnd = null,
    Object? timezone = null,
    Object? status = null,
    Object? roomName = null,
    Object? startedAt = freezed,
    Object? endedAt = freezed,
    Object? liveParticipants = null,
    Object? recordingVideoId = freezed,
    Object? recordingStatus = null,
    Object? settings = null,
    Object? serverTs = null,
    Object? canStart = null,
    Object? joinOpensAt = freezed,
  }) {
    return _then(_$LiveClassModelImpl(
      id: null == id
          ? _value.id
          : id // ignore: cast_nullable_to_non_nullable
              as int,
      courseId: null == courseId
          ? _value.courseId
          : courseId // ignore: cast_nullable_to_non_nullable
              as int,
      lessonId: freezed == lessonId
          ? _value.lessonId
          : lessonId // ignore: cast_nullable_to_non_nullable
              as int?,
      instructorId: null == instructorId
          ? _value.instructorId
          : instructorId // ignore: cast_nullable_to_non_nullable
              as int,
      title: null == title
          ? _value.title
          : title // ignore: cast_nullable_to_non_nullable
              as String,
      description: freezed == description
          ? _value.description
          : description // ignore: cast_nullable_to_non_nullable
              as String?,
      scheduledStart: null == scheduledStart
          ? _value.scheduledStart
          : scheduledStart // ignore: cast_nullable_to_non_nullable
              as String,
      scheduledEnd: null == scheduledEnd
          ? _value.scheduledEnd
          : scheduledEnd // ignore: cast_nullable_to_non_nullable
              as String,
      timezone: null == timezone
          ? _value.timezone
          : timezone // ignore: cast_nullable_to_non_nullable
              as String,
      status: null == status
          ? _value.status
          : status // ignore: cast_nullable_to_non_nullable
              as LiveClassStatus,
      roomName: null == roomName
          ? _value.roomName
          : roomName // ignore: cast_nullable_to_non_nullable
              as String,
      startedAt: freezed == startedAt
          ? _value.startedAt
          : startedAt // ignore: cast_nullable_to_non_nullable
              as String?,
      endedAt: freezed == endedAt
          ? _value.endedAt
          : endedAt // ignore: cast_nullable_to_non_nullable
              as String?,
      liveParticipants: null == liveParticipants
          ? _value.liveParticipants
          : liveParticipants // ignore: cast_nullable_to_non_nullable
              as int,
      recordingVideoId: freezed == recordingVideoId
          ? _value.recordingVideoId
          : recordingVideoId // ignore: cast_nullable_to_non_nullable
              as String?,
      recordingStatus: null == recordingStatus
          ? _value.recordingStatus
          : recordingStatus // ignore: cast_nullable_to_non_nullable
              as RecordingStatus,
      settings: null == settings
          ? _value.settings
          : settings // ignore: cast_nullable_to_non_nullable
              as LiveClassSettingsModel,
      serverTs: null == serverTs
          ? _value.serverTs
          : serverTs // ignore: cast_nullable_to_non_nullable
              as String,
      canStart: null == canStart
          ? _value.canStart
          : canStart // ignore: cast_nullable_to_non_nullable
              as bool,
      joinOpensAt: freezed == joinOpensAt
          ? _value.joinOpensAt
          : joinOpensAt // ignore: cast_nullable_to_non_nullable
              as String?,
    ));
  }
}

/// @nodoc
@JsonSerializable()
class _$LiveClassModelImpl extends _LiveClassModel {
  const _$LiveClassModelImpl(
      {required this.id,
      @JsonKey(name: 'course_id') required this.courseId,
      @JsonKey(name: 'lesson_id') this.lessonId,
      @JsonKey(name: 'instructor_id') required this.instructorId,
      required this.title,
      this.description,
      @JsonKey(name: 'scheduled_start') required this.scheduledStart,
      @JsonKey(name: 'scheduled_end') required this.scheduledEnd,
      this.timezone = 'Asia/Kolkata',
      @JsonKey(name: 'status', fromJson: _statusFromJson, toJson: _statusToJson)
      this.status = LiveClassStatus.scheduled,
      @JsonKey(name: 'room_name') required this.roomName,
      @JsonKey(name: 'started_at') this.startedAt,
      @JsonKey(name: 'ended_at') this.endedAt,
      @JsonKey(name: 'live_participants') this.liveParticipants = 0,
      @JsonKey(name: 'recording_video_id') this.recordingVideoId,
      @JsonKey(
          name: 'recording_status',
          fromJson: _recordingStatusFromJson,
          toJson: _recordingStatusToJson)
      this.recordingStatus = RecordingStatus.none,
      this.settings = const LiveClassSettingsModel(),
      @JsonKey(name: 'server_ts') required this.serverTs,
      @JsonKey(name: 'can_start') this.canStart = false,
      @JsonKey(name: 'join_opens_at') this.joinOpensAt})
      : super._();

  factory _$LiveClassModelImpl.fromJson(Map<String, dynamic> json) =>
      _$$LiveClassModelImplFromJson(json);

  @override
  final int id;
  @override
  @JsonKey(name: 'course_id')
  final int courseId;
  @override
  @JsonKey(name: 'lesson_id')
  final int? lessonId;
  @override
  @JsonKey(name: 'instructor_id')
  final int instructorId;
  @override
  final String title;
  @override
  final String? description;
  @override
  @JsonKey(name: 'scheduled_start')
  final String scheduledStart;
  @override
  @JsonKey(name: 'scheduled_end')
  final String scheduledEnd;
  @override
  @JsonKey()
  final String timezone;
  @override
  @JsonKey(name: 'status', fromJson: _statusFromJson, toJson: _statusToJson)
  final LiveClassStatus status;
  @override
  @JsonKey(name: 'room_name')
  final String roomName;
  @override
  @JsonKey(name: 'started_at')
  final String? startedAt;
  @override
  @JsonKey(name: 'ended_at')
  final String? endedAt;
  @override
  @JsonKey(name: 'live_participants')
  final int liveParticipants;
  @override
  @JsonKey(name: 'recording_video_id')
  final String? recordingVideoId;
  @override
  @JsonKey(
      name: 'recording_status',
      fromJson: _recordingStatusFromJson,
      toJson: _recordingStatusToJson)
  final RecordingStatus recordingStatus;
  @override
  @JsonKey()
  final LiveClassSettingsModel settings;
  @override
  @JsonKey(name: 'server_ts')
  final String serverTs;
  @override
  @JsonKey(name: 'can_start')
  final bool canStart;
  @override
  @JsonKey(name: 'join_opens_at')
  final String? joinOpensAt;

  @override
  String toString() {
    return 'LiveClassModel(id: $id, courseId: $courseId, lessonId: $lessonId, instructorId: $instructorId, title: $title, description: $description, scheduledStart: $scheduledStart, scheduledEnd: $scheduledEnd, timezone: $timezone, status: $status, roomName: $roomName, startedAt: $startedAt, endedAt: $endedAt, liveParticipants: $liveParticipants, recordingVideoId: $recordingVideoId, recordingStatus: $recordingStatus, settings: $settings, serverTs: $serverTs, canStart: $canStart, joinOpensAt: $joinOpensAt)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$LiveClassModelImpl &&
            (identical(other.id, id) || other.id == id) &&
            (identical(other.courseId, courseId) ||
                other.courseId == courseId) &&
            (identical(other.lessonId, lessonId) ||
                other.lessonId == lessonId) &&
            (identical(other.instructorId, instructorId) ||
                other.instructorId == instructorId) &&
            (identical(other.title, title) || other.title == title) &&
            (identical(other.description, description) ||
                other.description == description) &&
            (identical(other.scheduledStart, scheduledStart) ||
                other.scheduledStart == scheduledStart) &&
            (identical(other.scheduledEnd, scheduledEnd) ||
                other.scheduledEnd == scheduledEnd) &&
            (identical(other.timezone, timezone) ||
                other.timezone == timezone) &&
            (identical(other.status, status) || other.status == status) &&
            (identical(other.roomName, roomName) ||
                other.roomName == roomName) &&
            (identical(other.startedAt, startedAt) ||
                other.startedAt == startedAt) &&
            (identical(other.endedAt, endedAt) || other.endedAt == endedAt) &&
            (identical(other.liveParticipants, liveParticipants) ||
                other.liveParticipants == liveParticipants) &&
            (identical(other.recordingVideoId, recordingVideoId) ||
                other.recordingVideoId == recordingVideoId) &&
            (identical(other.recordingStatus, recordingStatus) ||
                other.recordingStatus == recordingStatus) &&
            (identical(other.settings, settings) ||
                other.settings == settings) &&
            (identical(other.serverTs, serverTs) ||
                other.serverTs == serverTs) &&
            (identical(other.canStart, canStart) ||
                other.canStart == canStart) &&
            (identical(other.joinOpensAt, joinOpensAt) ||
                other.joinOpensAt == joinOpensAt));
  }

  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  int get hashCode => Object.hashAll([
        runtimeType,
        id,
        courseId,
        lessonId,
        instructorId,
        title,
        description,
        scheduledStart,
        scheduledEnd,
        timezone,
        status,
        roomName,
        startedAt,
        endedAt,
        liveParticipants,
        recordingVideoId,
        recordingStatus,
        settings,
        serverTs,
        canStart,
        joinOpensAt
      ]);

  /// Create a copy of LiveClassModel
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  @pragma('vm:prefer-inline')
  _$$LiveClassModelImplCopyWith<_$LiveClassModelImpl> get copyWith =>
      __$$LiveClassModelImplCopyWithImpl<_$LiveClassModelImpl>(
          this, _$identity);

  @override
  Map<String, dynamic> toJson() {
    return _$$LiveClassModelImplToJson(
      this,
    );
  }
}

abstract class _LiveClassModel extends LiveClassModel {
  const factory _LiveClassModel(
      {required final int id,
      @JsonKey(name: 'course_id') required final int courseId,
      @JsonKey(name: 'lesson_id') final int? lessonId,
      @JsonKey(name: 'instructor_id') required final int instructorId,
      required final String title,
      final String? description,
      @JsonKey(name: 'scheduled_start') required final String scheduledStart,
      @JsonKey(name: 'scheduled_end') required final String scheduledEnd,
      final String timezone,
      @JsonKey(name: 'status', fromJson: _statusFromJson, toJson: _statusToJson)
      final LiveClassStatus status,
      @JsonKey(name: 'room_name') required final String roomName,
      @JsonKey(name: 'started_at') final String? startedAt,
      @JsonKey(name: 'ended_at') final String? endedAt,
      @JsonKey(name: 'live_participants') final int liveParticipants,
      @JsonKey(name: 'recording_video_id') final String? recordingVideoId,
      @JsonKey(
          name: 'recording_status',
          fromJson: _recordingStatusFromJson,
          toJson: _recordingStatusToJson)
      final RecordingStatus recordingStatus,
      final LiveClassSettingsModel settings,
      @JsonKey(name: 'server_ts') required final String serverTs,
      @JsonKey(name: 'can_start') final bool canStart,
      @JsonKey(name: 'join_opens_at')
      final String? joinOpensAt}) = _$LiveClassModelImpl;
  const _LiveClassModel._() : super._();

  factory _LiveClassModel.fromJson(Map<String, dynamic> json) =
      _$LiveClassModelImpl.fromJson;

  @override
  int get id;
  @override
  @JsonKey(name: 'course_id')
  int get courseId;
  @override
  @JsonKey(name: 'lesson_id')
  int? get lessonId;
  @override
  @JsonKey(name: 'instructor_id')
  int get instructorId;
  @override
  String get title;
  @override
  String? get description;
  @override
  @JsonKey(name: 'scheduled_start')
  String get scheduledStart;
  @override
  @JsonKey(name: 'scheduled_end')
  String get scheduledEnd;
  @override
  String get timezone;
  @override
  @JsonKey(name: 'status', fromJson: _statusFromJson, toJson: _statusToJson)
  LiveClassStatus get status;
  @override
  @JsonKey(name: 'room_name')
  String get roomName;
  @override
  @JsonKey(name: 'started_at')
  String? get startedAt;
  @override
  @JsonKey(name: 'ended_at')
  String? get endedAt;
  @override
  @JsonKey(name: 'live_participants')
  int get liveParticipants;
  @override
  @JsonKey(name: 'recording_video_id')
  String? get recordingVideoId;
  @override
  @JsonKey(
      name: 'recording_status',
      fromJson: _recordingStatusFromJson,
      toJson: _recordingStatusToJson)
  RecordingStatus get recordingStatus;
  @override
  LiveClassSettingsModel get settings;
  @override
  @JsonKey(name: 'server_ts')
  String get serverTs;
  @override
  @JsonKey(name: 'can_start')
  bool get canStart;
  @override
  @JsonKey(name: 'join_opens_at')
  String? get joinOpensAt;

  /// Create a copy of LiveClassModel
  /// with the given fields replaced by the non-null parameter values.
  @override
  @JsonKey(includeFromJson: false, includeToJson: false)
  _$$LiveClassModelImplCopyWith<_$LiveClassModelImpl> get copyWith =>
      throw _privateConstructorUsedError;
}

LiveClassJoinTokenModel _$LiveClassJoinTokenModelFromJson(
    Map<String, dynamic> json) {
  return _LiveClassJoinTokenModel.fromJson(json);
}

/// @nodoc
mixin _$LiveClassJoinTokenModel {
  @JsonKey(name: 'class_summary')
  LiveClassModel get classSummary => throw _privateConstructorUsedError;
  @JsonKey(name: 'room_name')
  String get roomName => throw _privateConstructorUsedError;
  @JsonKey(name: 'jitsi_url')
  String get jitsiUrl => throw _privateConstructorUsedError;
  String get jwt => throw _privateConstructorUsedError;
  @JsonKey(name: 'expires_in')
  int get expiresIn => throw _privateConstructorUsedError;

  /// Serializes this LiveClassJoinTokenModel to a JSON map.
  Map<String, dynamic> toJson() => throw _privateConstructorUsedError;

  /// Create a copy of LiveClassJoinTokenModel
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  $LiveClassJoinTokenModelCopyWith<LiveClassJoinTokenModel> get copyWith =>
      throw _privateConstructorUsedError;
}

/// @nodoc
abstract class $LiveClassJoinTokenModelCopyWith<$Res> {
  factory $LiveClassJoinTokenModelCopyWith(LiveClassJoinTokenModel value,
          $Res Function(LiveClassJoinTokenModel) then) =
      _$LiveClassJoinTokenModelCopyWithImpl<$Res, LiveClassJoinTokenModel>;
  @useResult
  $Res call(
      {@JsonKey(name: 'class_summary') LiveClassModel classSummary,
      @JsonKey(name: 'room_name') String roomName,
      @JsonKey(name: 'jitsi_url') String jitsiUrl,
      String jwt,
      @JsonKey(name: 'expires_in') int expiresIn});

  $LiveClassModelCopyWith<$Res> get classSummary;
}

/// @nodoc
class _$LiveClassJoinTokenModelCopyWithImpl<$Res,
        $Val extends LiveClassJoinTokenModel>
    implements $LiveClassJoinTokenModelCopyWith<$Res> {
  _$LiveClassJoinTokenModelCopyWithImpl(this._value, this._then);

  // ignore: unused_field
  final $Val _value;
  // ignore: unused_field
  final $Res Function($Val) _then;

  /// Create a copy of LiveClassJoinTokenModel
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? classSummary = null,
    Object? roomName = null,
    Object? jitsiUrl = null,
    Object? jwt = null,
    Object? expiresIn = null,
  }) {
    return _then(_value.copyWith(
      classSummary: null == classSummary
          ? _value.classSummary
          : classSummary // ignore: cast_nullable_to_non_nullable
              as LiveClassModel,
      roomName: null == roomName
          ? _value.roomName
          : roomName // ignore: cast_nullable_to_non_nullable
              as String,
      jitsiUrl: null == jitsiUrl
          ? _value.jitsiUrl
          : jitsiUrl // ignore: cast_nullable_to_non_nullable
              as String,
      jwt: null == jwt
          ? _value.jwt
          : jwt // ignore: cast_nullable_to_non_nullable
              as String,
      expiresIn: null == expiresIn
          ? _value.expiresIn
          : expiresIn // ignore: cast_nullable_to_non_nullable
              as int,
    ) as $Val);
  }

  /// Create a copy of LiveClassJoinTokenModel
  /// with the given fields replaced by the non-null parameter values.
  @override
  @pragma('vm:prefer-inline')
  $LiveClassModelCopyWith<$Res> get classSummary {
    return $LiveClassModelCopyWith<$Res>(_value.classSummary, (value) {
      return _then(_value.copyWith(classSummary: value) as $Val);
    });
  }
}

/// @nodoc
abstract class _$$LiveClassJoinTokenModelImplCopyWith<$Res>
    implements $LiveClassJoinTokenModelCopyWith<$Res> {
  factory _$$LiveClassJoinTokenModelImplCopyWith(
          _$LiveClassJoinTokenModelImpl value,
          $Res Function(_$LiveClassJoinTokenModelImpl) then) =
      __$$LiveClassJoinTokenModelImplCopyWithImpl<$Res>;
  @override
  @useResult
  $Res call(
      {@JsonKey(name: 'class_summary') LiveClassModel classSummary,
      @JsonKey(name: 'room_name') String roomName,
      @JsonKey(name: 'jitsi_url') String jitsiUrl,
      String jwt,
      @JsonKey(name: 'expires_in') int expiresIn});

  @override
  $LiveClassModelCopyWith<$Res> get classSummary;
}

/// @nodoc
class __$$LiveClassJoinTokenModelImplCopyWithImpl<$Res>
    extends _$LiveClassJoinTokenModelCopyWithImpl<$Res,
        _$LiveClassJoinTokenModelImpl>
    implements _$$LiveClassJoinTokenModelImplCopyWith<$Res> {
  __$$LiveClassJoinTokenModelImplCopyWithImpl(
      _$LiveClassJoinTokenModelImpl _value,
      $Res Function(_$LiveClassJoinTokenModelImpl) _then)
      : super(_value, _then);

  /// Create a copy of LiveClassJoinTokenModel
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? classSummary = null,
    Object? roomName = null,
    Object? jitsiUrl = null,
    Object? jwt = null,
    Object? expiresIn = null,
  }) {
    return _then(_$LiveClassJoinTokenModelImpl(
      classSummary: null == classSummary
          ? _value.classSummary
          : classSummary // ignore: cast_nullable_to_non_nullable
              as LiveClassModel,
      roomName: null == roomName
          ? _value.roomName
          : roomName // ignore: cast_nullable_to_non_nullable
              as String,
      jitsiUrl: null == jitsiUrl
          ? _value.jitsiUrl
          : jitsiUrl // ignore: cast_nullable_to_non_nullable
              as String,
      jwt: null == jwt
          ? _value.jwt
          : jwt // ignore: cast_nullable_to_non_nullable
              as String,
      expiresIn: null == expiresIn
          ? _value.expiresIn
          : expiresIn // ignore: cast_nullable_to_non_nullable
              as int,
    ));
  }
}

/// @nodoc
@JsonSerializable()
class _$LiveClassJoinTokenModelImpl extends _LiveClassJoinTokenModel {
  const _$LiveClassJoinTokenModelImpl(
      {@JsonKey(name: 'class_summary') required this.classSummary,
      @JsonKey(name: 'room_name') required this.roomName,
      @JsonKey(name: 'jitsi_url') required this.jitsiUrl,
      required this.jwt,
      @JsonKey(name: 'expires_in') required this.expiresIn})
      : super._();

  factory _$LiveClassJoinTokenModelImpl.fromJson(Map<String, dynamic> json) =>
      _$$LiveClassJoinTokenModelImplFromJson(json);

  @override
  @JsonKey(name: 'class_summary')
  final LiveClassModel classSummary;
  @override
  @JsonKey(name: 'room_name')
  final String roomName;
  @override
  @JsonKey(name: 'jitsi_url')
  final String jitsiUrl;
  @override
  final String jwt;
  @override
  @JsonKey(name: 'expires_in')
  final int expiresIn;

  @override
  String toString() {
    return 'LiveClassJoinTokenModel(classSummary: $classSummary, roomName: $roomName, jitsiUrl: $jitsiUrl, jwt: $jwt, expiresIn: $expiresIn)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$LiveClassJoinTokenModelImpl &&
            (identical(other.classSummary, classSummary) ||
                other.classSummary == classSummary) &&
            (identical(other.roomName, roomName) ||
                other.roomName == roomName) &&
            (identical(other.jitsiUrl, jitsiUrl) ||
                other.jitsiUrl == jitsiUrl) &&
            (identical(other.jwt, jwt) || other.jwt == jwt) &&
            (identical(other.expiresIn, expiresIn) ||
                other.expiresIn == expiresIn));
  }

  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  int get hashCode => Object.hash(
      runtimeType, classSummary, roomName, jitsiUrl, jwt, expiresIn);

  /// Create a copy of LiveClassJoinTokenModel
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  @pragma('vm:prefer-inline')
  _$$LiveClassJoinTokenModelImplCopyWith<_$LiveClassJoinTokenModelImpl>
      get copyWith => __$$LiveClassJoinTokenModelImplCopyWithImpl<
          _$LiveClassJoinTokenModelImpl>(this, _$identity);

  @override
  Map<String, dynamic> toJson() {
    return _$$LiveClassJoinTokenModelImplToJson(
      this,
    );
  }
}

abstract class _LiveClassJoinTokenModel extends LiveClassJoinTokenModel {
  const factory _LiveClassJoinTokenModel(
          {@JsonKey(name: 'class_summary')
          required final LiveClassModel classSummary,
          @JsonKey(name: 'room_name') required final String roomName,
          @JsonKey(name: 'jitsi_url') required final String jitsiUrl,
          required final String jwt,
          @JsonKey(name: 'expires_in') required final int expiresIn}) =
      _$LiveClassJoinTokenModelImpl;
  const _LiveClassJoinTokenModel._() : super._();

  factory _LiveClassJoinTokenModel.fromJson(Map<String, dynamic> json) =
      _$LiveClassJoinTokenModelImpl.fromJson;

  @override
  @JsonKey(name: 'class_summary')
  LiveClassModel get classSummary;
  @override
  @JsonKey(name: 'room_name')
  String get roomName;
  @override
  @JsonKey(name: 'jitsi_url')
  String get jitsiUrl;
  @override
  String get jwt;
  @override
  @JsonKey(name: 'expires_in')
  int get expiresIn;

  /// Create a copy of LiveClassJoinTokenModel
  /// with the given fields replaced by the non-null parameter values.
  @override
  @JsonKey(includeFromJson: false, includeToJson: false)
  _$$LiveClassJoinTokenModelImplCopyWith<_$LiveClassJoinTokenModelImpl>
      get copyWith => throw _privateConstructorUsedError;
}

LiveClassRecordingPlaybackModel _$LiveClassRecordingPlaybackModelFromJson(
    Map<String, dynamic> json) {
  return _LiveClassRecordingPlaybackModel.fromJson(json);
}

/// @nodoc
mixin _$LiveClassRecordingPlaybackModel {
  @JsonKey(name: 'video_id')
  String get videoId => throw _privateConstructorUsedError;
  @JsonKey(name: 'hls_url')
  String get hlsUrl => throw _privateConstructorUsedError;
  bool get signed => throw _privateConstructorUsedError;
  @JsonKey(name: 'expires_in')
  int get expiresIn => throw _privateConstructorUsedError;

  /// Serializes this LiveClassRecordingPlaybackModel to a JSON map.
  Map<String, dynamic> toJson() => throw _privateConstructorUsedError;

  /// Create a copy of LiveClassRecordingPlaybackModel
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  $LiveClassRecordingPlaybackModelCopyWith<LiveClassRecordingPlaybackModel>
      get copyWith => throw _privateConstructorUsedError;
}

/// @nodoc
abstract class $LiveClassRecordingPlaybackModelCopyWith<$Res> {
  factory $LiveClassRecordingPlaybackModelCopyWith(
          LiveClassRecordingPlaybackModel value,
          $Res Function(LiveClassRecordingPlaybackModel) then) =
      _$LiveClassRecordingPlaybackModelCopyWithImpl<$Res,
          LiveClassRecordingPlaybackModel>;
  @useResult
  $Res call(
      {@JsonKey(name: 'video_id') String videoId,
      @JsonKey(name: 'hls_url') String hlsUrl,
      bool signed,
      @JsonKey(name: 'expires_in') int expiresIn});
}

/// @nodoc
class _$LiveClassRecordingPlaybackModelCopyWithImpl<$Res,
        $Val extends LiveClassRecordingPlaybackModel>
    implements $LiveClassRecordingPlaybackModelCopyWith<$Res> {
  _$LiveClassRecordingPlaybackModelCopyWithImpl(this._value, this._then);

  // ignore: unused_field
  final $Val _value;
  // ignore: unused_field
  final $Res Function($Val) _then;

  /// Create a copy of LiveClassRecordingPlaybackModel
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? videoId = null,
    Object? hlsUrl = null,
    Object? signed = null,
    Object? expiresIn = null,
  }) {
    return _then(_value.copyWith(
      videoId: null == videoId
          ? _value.videoId
          : videoId // ignore: cast_nullable_to_non_nullable
              as String,
      hlsUrl: null == hlsUrl
          ? _value.hlsUrl
          : hlsUrl // ignore: cast_nullable_to_non_nullable
              as String,
      signed: null == signed
          ? _value.signed
          : signed // ignore: cast_nullable_to_non_nullable
              as bool,
      expiresIn: null == expiresIn
          ? _value.expiresIn
          : expiresIn // ignore: cast_nullable_to_non_nullable
              as int,
    ) as $Val);
  }
}

/// @nodoc
abstract class _$$LiveClassRecordingPlaybackModelImplCopyWith<$Res>
    implements $LiveClassRecordingPlaybackModelCopyWith<$Res> {
  factory _$$LiveClassRecordingPlaybackModelImplCopyWith(
          _$LiveClassRecordingPlaybackModelImpl value,
          $Res Function(_$LiveClassRecordingPlaybackModelImpl) then) =
      __$$LiveClassRecordingPlaybackModelImplCopyWithImpl<$Res>;
  @override
  @useResult
  $Res call(
      {@JsonKey(name: 'video_id') String videoId,
      @JsonKey(name: 'hls_url') String hlsUrl,
      bool signed,
      @JsonKey(name: 'expires_in') int expiresIn});
}

/// @nodoc
class __$$LiveClassRecordingPlaybackModelImplCopyWithImpl<$Res>
    extends _$LiveClassRecordingPlaybackModelCopyWithImpl<$Res,
        _$LiveClassRecordingPlaybackModelImpl>
    implements _$$LiveClassRecordingPlaybackModelImplCopyWith<$Res> {
  __$$LiveClassRecordingPlaybackModelImplCopyWithImpl(
      _$LiveClassRecordingPlaybackModelImpl _value,
      $Res Function(_$LiveClassRecordingPlaybackModelImpl) _then)
      : super(_value, _then);

  /// Create a copy of LiveClassRecordingPlaybackModel
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? videoId = null,
    Object? hlsUrl = null,
    Object? signed = null,
    Object? expiresIn = null,
  }) {
    return _then(_$LiveClassRecordingPlaybackModelImpl(
      videoId: null == videoId
          ? _value.videoId
          : videoId // ignore: cast_nullable_to_non_nullable
              as String,
      hlsUrl: null == hlsUrl
          ? _value.hlsUrl
          : hlsUrl // ignore: cast_nullable_to_non_nullable
              as String,
      signed: null == signed
          ? _value.signed
          : signed // ignore: cast_nullable_to_non_nullable
              as bool,
      expiresIn: null == expiresIn
          ? _value.expiresIn
          : expiresIn // ignore: cast_nullable_to_non_nullable
              as int,
    ));
  }
}

/// @nodoc
@JsonSerializable()
class _$LiveClassRecordingPlaybackModelImpl
    implements _LiveClassRecordingPlaybackModel {
  const _$LiveClassRecordingPlaybackModelImpl(
      {@JsonKey(name: 'video_id') required this.videoId,
      @JsonKey(name: 'hls_url') required this.hlsUrl,
      this.signed = true,
      @JsonKey(name: 'expires_in') this.expiresIn = 0});

  factory _$LiveClassRecordingPlaybackModelImpl.fromJson(
          Map<String, dynamic> json) =>
      _$$LiveClassRecordingPlaybackModelImplFromJson(json);

  @override
  @JsonKey(name: 'video_id')
  final String videoId;
  @override
  @JsonKey(name: 'hls_url')
  final String hlsUrl;
  @override
  @JsonKey()
  final bool signed;
  @override
  @JsonKey(name: 'expires_in')
  final int expiresIn;

  @override
  String toString() {
    return 'LiveClassRecordingPlaybackModel(videoId: $videoId, hlsUrl: $hlsUrl, signed: $signed, expiresIn: $expiresIn)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$LiveClassRecordingPlaybackModelImpl &&
            (identical(other.videoId, videoId) || other.videoId == videoId) &&
            (identical(other.hlsUrl, hlsUrl) || other.hlsUrl == hlsUrl) &&
            (identical(other.signed, signed) || other.signed == signed) &&
            (identical(other.expiresIn, expiresIn) ||
                other.expiresIn == expiresIn));
  }

  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  int get hashCode =>
      Object.hash(runtimeType, videoId, hlsUrl, signed, expiresIn);

  /// Create a copy of LiveClassRecordingPlaybackModel
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  @pragma('vm:prefer-inline')
  _$$LiveClassRecordingPlaybackModelImplCopyWith<
          _$LiveClassRecordingPlaybackModelImpl>
      get copyWith => __$$LiveClassRecordingPlaybackModelImplCopyWithImpl<
          _$LiveClassRecordingPlaybackModelImpl>(this, _$identity);

  @override
  Map<String, dynamic> toJson() {
    return _$$LiveClassRecordingPlaybackModelImplToJson(
      this,
    );
  }
}

abstract class _LiveClassRecordingPlaybackModel
    implements LiveClassRecordingPlaybackModel {
  const factory _LiveClassRecordingPlaybackModel(
          {@JsonKey(name: 'video_id') required final String videoId,
          @JsonKey(name: 'hls_url') required final String hlsUrl,
          final bool signed,
          @JsonKey(name: 'expires_in') final int expiresIn}) =
      _$LiveClassRecordingPlaybackModelImpl;

  factory _LiveClassRecordingPlaybackModel.fromJson(Map<String, dynamic> json) =
      _$LiveClassRecordingPlaybackModelImpl.fromJson;

  @override
  @JsonKey(name: 'video_id')
  String get videoId;
  @override
  @JsonKey(name: 'hls_url')
  String get hlsUrl;
  @override
  bool get signed;
  @override
  @JsonKey(name: 'expires_in')
  int get expiresIn;

  /// Create a copy of LiveClassRecordingPlaybackModel
  /// with the given fields replaced by the non-null parameter values.
  @override
  @JsonKey(includeFromJson: false, includeToJson: false)
  _$$LiveClassRecordingPlaybackModelImplCopyWith<
          _$LiveClassRecordingPlaybackModelImpl>
      get copyWith => throw _privateConstructorUsedError;
}
