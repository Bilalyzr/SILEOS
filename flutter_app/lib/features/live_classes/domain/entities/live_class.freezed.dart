// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint
// ignore_for_file: unused_element, deprecated_member_use, deprecated_member_use_from_same_package, use_function_type_syntax_for_parameters, unnecessary_const, avoid_init_to_null, invalid_override_different_default_values_named, prefer_expression_function_bodies, annotate_overrides, invalid_annotation_target, unnecessary_question_mark

part of 'live_class.dart';

// **************************************************************************
// FreezedGenerator
// **************************************************************************

T _$identity<T>(T value) => value;

final _privateConstructorUsedError = UnsupportedError(
    'It seems like you constructed your class using `MyClass._()`. This constructor is only meant to be used by freezed and you are not supposed to need it nor use it.\nPlease check the documentation here for more information: https://github.com/rrousselGit/freezed#adding-getters-and-methods-to-our-models');

/// @nodoc
mixin _$LiveClassSettings {
  bool get lobbyEnabled => throw _privateConstructorUsedError;
  bool get startMuted => throw _privateConstructorUsedError;
  bool get allowChat => throw _privateConstructorUsedError;
  bool get allowShare => throw _privateConstructorUsedError;
  bool get record => throw _privateConstructorUsedError;
  int get attendanceThresholdPct => throw _privateConstructorUsedError;

  /// Create a copy of LiveClassSettings
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  $LiveClassSettingsCopyWith<LiveClassSettings> get copyWith =>
      throw _privateConstructorUsedError;
}

/// @nodoc
abstract class $LiveClassSettingsCopyWith<$Res> {
  factory $LiveClassSettingsCopyWith(
          LiveClassSettings value, $Res Function(LiveClassSettings) then) =
      _$LiveClassSettingsCopyWithImpl<$Res, LiveClassSettings>;
  @useResult
  $Res call(
      {bool lobbyEnabled,
      bool startMuted,
      bool allowChat,
      bool allowShare,
      bool record,
      int attendanceThresholdPct});
}

/// @nodoc
class _$LiveClassSettingsCopyWithImpl<$Res, $Val extends LiveClassSettings>
    implements $LiveClassSettingsCopyWith<$Res> {
  _$LiveClassSettingsCopyWithImpl(this._value, this._then);

  // ignore: unused_field
  final $Val _value;
  // ignore: unused_field
  final $Res Function($Val) _then;

  /// Create a copy of LiveClassSettings
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
abstract class _$$LiveClassSettingsImplCopyWith<$Res>
    implements $LiveClassSettingsCopyWith<$Res> {
  factory _$$LiveClassSettingsImplCopyWith(_$LiveClassSettingsImpl value,
          $Res Function(_$LiveClassSettingsImpl) then) =
      __$$LiveClassSettingsImplCopyWithImpl<$Res>;
  @override
  @useResult
  $Res call(
      {bool lobbyEnabled,
      bool startMuted,
      bool allowChat,
      bool allowShare,
      bool record,
      int attendanceThresholdPct});
}

/// @nodoc
class __$$LiveClassSettingsImplCopyWithImpl<$Res>
    extends _$LiveClassSettingsCopyWithImpl<$Res, _$LiveClassSettingsImpl>
    implements _$$LiveClassSettingsImplCopyWith<$Res> {
  __$$LiveClassSettingsImplCopyWithImpl(_$LiveClassSettingsImpl _value,
      $Res Function(_$LiveClassSettingsImpl) _then)
      : super(_value, _then);

  /// Create a copy of LiveClassSettings
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
    return _then(_$LiveClassSettingsImpl(
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

class _$LiveClassSettingsImpl implements _LiveClassSettings {
  const _$LiveClassSettingsImpl(
      {this.lobbyEnabled = true,
      this.startMuted = true,
      this.allowChat = true,
      this.allowShare = true,
      this.record = false,
      this.attendanceThresholdPct = 60});

  @override
  @JsonKey()
  final bool lobbyEnabled;
  @override
  @JsonKey()
  final bool startMuted;
  @override
  @JsonKey()
  final bool allowChat;
  @override
  @JsonKey()
  final bool allowShare;
  @override
  @JsonKey()
  final bool record;
  @override
  @JsonKey()
  final int attendanceThresholdPct;

  @override
  String toString() {
    return 'LiveClassSettings(lobbyEnabled: $lobbyEnabled, startMuted: $startMuted, allowChat: $allowChat, allowShare: $allowShare, record: $record, attendanceThresholdPct: $attendanceThresholdPct)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$LiveClassSettingsImpl &&
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

  @override
  int get hashCode => Object.hash(runtimeType, lobbyEnabled, startMuted,
      allowChat, allowShare, record, attendanceThresholdPct);

  /// Create a copy of LiveClassSettings
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  @pragma('vm:prefer-inline')
  _$$LiveClassSettingsImplCopyWith<_$LiveClassSettingsImpl> get copyWith =>
      __$$LiveClassSettingsImplCopyWithImpl<_$LiveClassSettingsImpl>(
          this, _$identity);
}

abstract class _LiveClassSettings implements LiveClassSettings {
  const factory _LiveClassSettings(
      {final bool lobbyEnabled,
      final bool startMuted,
      final bool allowChat,
      final bool allowShare,
      final bool record,
      final int attendanceThresholdPct}) = _$LiveClassSettingsImpl;

  @override
  bool get lobbyEnabled;
  @override
  bool get startMuted;
  @override
  bool get allowChat;
  @override
  bool get allowShare;
  @override
  bool get record;
  @override
  int get attendanceThresholdPct;

  /// Create a copy of LiveClassSettings
  /// with the given fields replaced by the non-null parameter values.
  @override
  @JsonKey(includeFromJson: false, includeToJson: false)
  _$$LiveClassSettingsImplCopyWith<_$LiveClassSettingsImpl> get copyWith =>
      throw _privateConstructorUsedError;
}

/// @nodoc
mixin _$LiveClass {
  int get id => throw _privateConstructorUsedError;
  int get courseId => throw _privateConstructorUsedError;
  int? get lessonId => throw _privateConstructorUsedError;
  int get instructorId => throw _privateConstructorUsedError;
  String get title => throw _privateConstructorUsedError;
  String? get description => throw _privateConstructorUsedError;
  DateTime get scheduledStart => throw _privateConstructorUsedError;
  DateTime get scheduledEnd => throw _privateConstructorUsedError;
  String get timezone => throw _privateConstructorUsedError;
  LiveClassStatus get status => throw _privateConstructorUsedError;
  String get roomName => throw _privateConstructorUsedError;
  DateTime? get startedAt => throw _privateConstructorUsedError;
  DateTime? get endedAt => throw _privateConstructorUsedError;
  int get liveParticipants => throw _privateConstructorUsedError;
  String? get recordingVideoId => throw _privateConstructorUsedError;
  RecordingStatus get recordingStatus => throw _privateConstructorUsedError;
  LiveClassSettings get settings => throw _privateConstructorUsedError;
  DateTime get serverTs => throw _privateConstructorUsedError;
  bool get canStart => throw _privateConstructorUsedError;
  DateTime? get joinOpensAt => throw _privateConstructorUsedError;

  /// Create a copy of LiveClass
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  $LiveClassCopyWith<LiveClass> get copyWith =>
      throw _privateConstructorUsedError;
}

/// @nodoc
abstract class $LiveClassCopyWith<$Res> {
  factory $LiveClassCopyWith(LiveClass value, $Res Function(LiveClass) then) =
      _$LiveClassCopyWithImpl<$Res, LiveClass>;
  @useResult
  $Res call(
      {int id,
      int courseId,
      int? lessonId,
      int instructorId,
      String title,
      String? description,
      DateTime scheduledStart,
      DateTime scheduledEnd,
      String timezone,
      LiveClassStatus status,
      String roomName,
      DateTime? startedAt,
      DateTime? endedAt,
      int liveParticipants,
      String? recordingVideoId,
      RecordingStatus recordingStatus,
      LiveClassSettings settings,
      DateTime serverTs,
      bool canStart,
      DateTime? joinOpensAt});

  $LiveClassSettingsCopyWith<$Res> get settings;
}

/// @nodoc
class _$LiveClassCopyWithImpl<$Res, $Val extends LiveClass>
    implements $LiveClassCopyWith<$Res> {
  _$LiveClassCopyWithImpl(this._value, this._then);

  // ignore: unused_field
  final $Val _value;
  // ignore: unused_field
  final $Res Function($Val) _then;

  /// Create a copy of LiveClass
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
              as DateTime,
      scheduledEnd: null == scheduledEnd
          ? _value.scheduledEnd
          : scheduledEnd // ignore: cast_nullable_to_non_nullable
              as DateTime,
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
              as DateTime?,
      endedAt: freezed == endedAt
          ? _value.endedAt
          : endedAt // ignore: cast_nullable_to_non_nullable
              as DateTime?,
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
              as LiveClassSettings,
      serverTs: null == serverTs
          ? _value.serverTs
          : serverTs // ignore: cast_nullable_to_non_nullable
              as DateTime,
      canStart: null == canStart
          ? _value.canStart
          : canStart // ignore: cast_nullable_to_non_nullable
              as bool,
      joinOpensAt: freezed == joinOpensAt
          ? _value.joinOpensAt
          : joinOpensAt // ignore: cast_nullable_to_non_nullable
              as DateTime?,
    ) as $Val);
  }

  /// Create a copy of LiveClass
  /// with the given fields replaced by the non-null parameter values.
  @override
  @pragma('vm:prefer-inline')
  $LiveClassSettingsCopyWith<$Res> get settings {
    return $LiveClassSettingsCopyWith<$Res>(_value.settings, (value) {
      return _then(_value.copyWith(settings: value) as $Val);
    });
  }
}

/// @nodoc
abstract class _$$LiveClassImplCopyWith<$Res>
    implements $LiveClassCopyWith<$Res> {
  factory _$$LiveClassImplCopyWith(
          _$LiveClassImpl value, $Res Function(_$LiveClassImpl) then) =
      __$$LiveClassImplCopyWithImpl<$Res>;
  @override
  @useResult
  $Res call(
      {int id,
      int courseId,
      int? lessonId,
      int instructorId,
      String title,
      String? description,
      DateTime scheduledStart,
      DateTime scheduledEnd,
      String timezone,
      LiveClassStatus status,
      String roomName,
      DateTime? startedAt,
      DateTime? endedAt,
      int liveParticipants,
      String? recordingVideoId,
      RecordingStatus recordingStatus,
      LiveClassSettings settings,
      DateTime serverTs,
      bool canStart,
      DateTime? joinOpensAt});

  @override
  $LiveClassSettingsCopyWith<$Res> get settings;
}

/// @nodoc
class __$$LiveClassImplCopyWithImpl<$Res>
    extends _$LiveClassCopyWithImpl<$Res, _$LiveClassImpl>
    implements _$$LiveClassImplCopyWith<$Res> {
  __$$LiveClassImplCopyWithImpl(
      _$LiveClassImpl _value, $Res Function(_$LiveClassImpl) _then)
      : super(_value, _then);

  /// Create a copy of LiveClass
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
    return _then(_$LiveClassImpl(
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
              as DateTime,
      scheduledEnd: null == scheduledEnd
          ? _value.scheduledEnd
          : scheduledEnd // ignore: cast_nullable_to_non_nullable
              as DateTime,
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
              as DateTime?,
      endedAt: freezed == endedAt
          ? _value.endedAt
          : endedAt // ignore: cast_nullable_to_non_nullable
              as DateTime?,
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
              as LiveClassSettings,
      serverTs: null == serverTs
          ? _value.serverTs
          : serverTs // ignore: cast_nullable_to_non_nullable
              as DateTime,
      canStart: null == canStart
          ? _value.canStart
          : canStart // ignore: cast_nullable_to_non_nullable
              as bool,
      joinOpensAt: freezed == joinOpensAt
          ? _value.joinOpensAt
          : joinOpensAt // ignore: cast_nullable_to_non_nullable
              as DateTime?,
    ));
  }
}

/// @nodoc

class _$LiveClassImpl extends _LiveClass {
  const _$LiveClassImpl(
      {required this.id,
      required this.courseId,
      this.lessonId,
      required this.instructorId,
      required this.title,
      this.description,
      required this.scheduledStart,
      required this.scheduledEnd,
      required this.timezone,
      required this.status,
      required this.roomName,
      this.startedAt,
      this.endedAt,
      this.liveParticipants = 0,
      this.recordingVideoId,
      required this.recordingStatus,
      required this.settings,
      required this.serverTs,
      this.canStart = false,
      this.joinOpensAt})
      : super._();

  @override
  final int id;
  @override
  final int courseId;
  @override
  final int? lessonId;
  @override
  final int instructorId;
  @override
  final String title;
  @override
  final String? description;
  @override
  final DateTime scheduledStart;
  @override
  final DateTime scheduledEnd;
  @override
  final String timezone;
  @override
  final LiveClassStatus status;
  @override
  final String roomName;
  @override
  final DateTime? startedAt;
  @override
  final DateTime? endedAt;
  @override
  @JsonKey()
  final int liveParticipants;
  @override
  final String? recordingVideoId;
  @override
  final RecordingStatus recordingStatus;
  @override
  final LiveClassSettings settings;
  @override
  final DateTime serverTs;
  @override
  @JsonKey()
  final bool canStart;
  @override
  final DateTime? joinOpensAt;

  @override
  String toString() {
    return 'LiveClass(id: $id, courseId: $courseId, lessonId: $lessonId, instructorId: $instructorId, title: $title, description: $description, scheduledStart: $scheduledStart, scheduledEnd: $scheduledEnd, timezone: $timezone, status: $status, roomName: $roomName, startedAt: $startedAt, endedAt: $endedAt, liveParticipants: $liveParticipants, recordingVideoId: $recordingVideoId, recordingStatus: $recordingStatus, settings: $settings, serverTs: $serverTs, canStart: $canStart, joinOpensAt: $joinOpensAt)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$LiveClassImpl &&
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

  /// Create a copy of LiveClass
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  @pragma('vm:prefer-inline')
  _$$LiveClassImplCopyWith<_$LiveClassImpl> get copyWith =>
      __$$LiveClassImplCopyWithImpl<_$LiveClassImpl>(this, _$identity);
}

abstract class _LiveClass extends LiveClass {
  const factory _LiveClass(
      {required final int id,
      required final int courseId,
      final int? lessonId,
      required final int instructorId,
      required final String title,
      final String? description,
      required final DateTime scheduledStart,
      required final DateTime scheduledEnd,
      required final String timezone,
      required final LiveClassStatus status,
      required final String roomName,
      final DateTime? startedAt,
      final DateTime? endedAt,
      final int liveParticipants,
      final String? recordingVideoId,
      required final RecordingStatus recordingStatus,
      required final LiveClassSettings settings,
      required final DateTime serverTs,
      final bool canStart,
      final DateTime? joinOpensAt}) = _$LiveClassImpl;
  const _LiveClass._() : super._();

  @override
  int get id;
  @override
  int get courseId;
  @override
  int? get lessonId;
  @override
  int get instructorId;
  @override
  String get title;
  @override
  String? get description;
  @override
  DateTime get scheduledStart;
  @override
  DateTime get scheduledEnd;
  @override
  String get timezone;
  @override
  LiveClassStatus get status;
  @override
  String get roomName;
  @override
  DateTime? get startedAt;
  @override
  DateTime? get endedAt;
  @override
  int get liveParticipants;
  @override
  String? get recordingVideoId;
  @override
  RecordingStatus get recordingStatus;
  @override
  LiveClassSettings get settings;
  @override
  DateTime get serverTs;
  @override
  bool get canStart;
  @override
  DateTime? get joinOpensAt;

  /// Create a copy of LiveClass
  /// with the given fields replaced by the non-null parameter values.
  @override
  @JsonKey(includeFromJson: false, includeToJson: false)
  _$$LiveClassImplCopyWith<_$LiveClassImpl> get copyWith =>
      throw _privateConstructorUsedError;
}

/// @nodoc
mixin _$LiveClassJoinToken {
  LiveClass get classSummary => throw _privateConstructorUsedError;
  String get roomName => throw _privateConstructorUsedError;
  String get jitsiUrl => throw _privateConstructorUsedError;
  String get jwt => throw _privateConstructorUsedError;
  int get expiresIn => throw _privateConstructorUsedError;

  /// Create a copy of LiveClassJoinToken
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  $LiveClassJoinTokenCopyWith<LiveClassJoinToken> get copyWith =>
      throw _privateConstructorUsedError;
}

/// @nodoc
abstract class $LiveClassJoinTokenCopyWith<$Res> {
  factory $LiveClassJoinTokenCopyWith(
          LiveClassJoinToken value, $Res Function(LiveClassJoinToken) then) =
      _$LiveClassJoinTokenCopyWithImpl<$Res, LiveClassJoinToken>;
  @useResult
  $Res call(
      {LiveClass classSummary,
      String roomName,
      String jitsiUrl,
      String jwt,
      int expiresIn});

  $LiveClassCopyWith<$Res> get classSummary;
}

/// @nodoc
class _$LiveClassJoinTokenCopyWithImpl<$Res, $Val extends LiveClassJoinToken>
    implements $LiveClassJoinTokenCopyWith<$Res> {
  _$LiveClassJoinTokenCopyWithImpl(this._value, this._then);

  // ignore: unused_field
  final $Val _value;
  // ignore: unused_field
  final $Res Function($Val) _then;

  /// Create a copy of LiveClassJoinToken
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
              as LiveClass,
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

  /// Create a copy of LiveClassJoinToken
  /// with the given fields replaced by the non-null parameter values.
  @override
  @pragma('vm:prefer-inline')
  $LiveClassCopyWith<$Res> get classSummary {
    return $LiveClassCopyWith<$Res>(_value.classSummary, (value) {
      return _then(_value.copyWith(classSummary: value) as $Val);
    });
  }
}

/// @nodoc
abstract class _$$LiveClassJoinTokenImplCopyWith<$Res>
    implements $LiveClassJoinTokenCopyWith<$Res> {
  factory _$$LiveClassJoinTokenImplCopyWith(_$LiveClassJoinTokenImpl value,
          $Res Function(_$LiveClassJoinTokenImpl) then) =
      __$$LiveClassJoinTokenImplCopyWithImpl<$Res>;
  @override
  @useResult
  $Res call(
      {LiveClass classSummary,
      String roomName,
      String jitsiUrl,
      String jwt,
      int expiresIn});

  @override
  $LiveClassCopyWith<$Res> get classSummary;
}

/// @nodoc
class __$$LiveClassJoinTokenImplCopyWithImpl<$Res>
    extends _$LiveClassJoinTokenCopyWithImpl<$Res, _$LiveClassJoinTokenImpl>
    implements _$$LiveClassJoinTokenImplCopyWith<$Res> {
  __$$LiveClassJoinTokenImplCopyWithImpl(_$LiveClassJoinTokenImpl _value,
      $Res Function(_$LiveClassJoinTokenImpl) _then)
      : super(_value, _then);

  /// Create a copy of LiveClassJoinToken
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
    return _then(_$LiveClassJoinTokenImpl(
      classSummary: null == classSummary
          ? _value.classSummary
          : classSummary // ignore: cast_nullable_to_non_nullable
              as LiveClass,
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

class _$LiveClassJoinTokenImpl implements _LiveClassJoinToken {
  const _$LiveClassJoinTokenImpl(
      {required this.classSummary,
      required this.roomName,
      required this.jitsiUrl,
      required this.jwt,
      required this.expiresIn});

  @override
  final LiveClass classSummary;
  @override
  final String roomName;
  @override
  final String jitsiUrl;
  @override
  final String jwt;
  @override
  final int expiresIn;

  @override
  String toString() {
    return 'LiveClassJoinToken(classSummary: $classSummary, roomName: $roomName, jitsiUrl: $jitsiUrl, jwt: $jwt, expiresIn: $expiresIn)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$LiveClassJoinTokenImpl &&
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

  @override
  int get hashCode => Object.hash(
      runtimeType, classSummary, roomName, jitsiUrl, jwt, expiresIn);

  /// Create a copy of LiveClassJoinToken
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  @pragma('vm:prefer-inline')
  _$$LiveClassJoinTokenImplCopyWith<_$LiveClassJoinTokenImpl> get copyWith =>
      __$$LiveClassJoinTokenImplCopyWithImpl<_$LiveClassJoinTokenImpl>(
          this, _$identity);
}

abstract class _LiveClassJoinToken implements LiveClassJoinToken {
  const factory _LiveClassJoinToken(
      {required final LiveClass classSummary,
      required final String roomName,
      required final String jitsiUrl,
      required final String jwt,
      required final int expiresIn}) = _$LiveClassJoinTokenImpl;

  @override
  LiveClass get classSummary;
  @override
  String get roomName;
  @override
  String get jitsiUrl;
  @override
  String get jwt;
  @override
  int get expiresIn;

  /// Create a copy of LiveClassJoinToken
  /// with the given fields replaced by the non-null parameter values.
  @override
  @JsonKey(includeFromJson: false, includeToJson: false)
  _$$LiveClassJoinTokenImplCopyWith<_$LiveClassJoinTokenImpl> get copyWith =>
      throw _privateConstructorUsedError;
}
