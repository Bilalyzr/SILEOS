// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint
// ignore_for_file: unused_element, deprecated_member_use, deprecated_member_use_from_same_package, use_function_type_syntax_for_parameters, unnecessary_const, avoid_init_to_null, invalid_override_different_default_values_named, prefer_expression_function_bodies, annotate_overrides, invalid_annotation_target, unnecessary_question_mark

part of 'lesson_model.dart';

// **************************************************************************
// FreezedGenerator
// **************************************************************************

T _$identity<T>(T value) => value;

final _privateConstructorUsedError = UnsupportedError(
    'It seems like you constructed your class using `MyClass._()`. This constructor is only meant to be used by freezed and you are not supposed to need it nor use it.\nPlease check the documentation here for more information: https://github.com/rrousselGit/freezed#adding-getters-and-methods-to-our-models');

LessonModel _$LessonModelFromJson(Map<String, dynamic> json) {
  return _LessonModel.fromJson(json);
}

/// @nodoc
mixin _$LessonModel {
  int get id => throw _privateConstructorUsedError;
  String get title => throw _privateConstructorUsedError;
  String? get content => throw _privateConstructorUsedError;
  @JsonKey(name: 'video_url')
  String? get videoUrl => throw _privateConstructorUsedError;
  @JsonKey(name: 'youtube_url')
  String? get youtubeUrl => throw _privateConstructorUsedError;
  @JsonKey(name: 'video_duration')
  int? get duration => throw _privateConstructorUsedError;
  @JsonKey(name: 'is_preview')
  bool get isPreview => throw _privateConstructorUsedError;
  int get order => throw _privateConstructorUsedError;
  @JsonKey(name: 'course_id')
  int get courseId => throw _privateConstructorUsedError;

  /// Serializes this LessonModel to a JSON map.
  Map<String, dynamic> toJson() => throw _privateConstructorUsedError;

  /// Create a copy of LessonModel
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  $LessonModelCopyWith<LessonModel> get copyWith =>
      throw _privateConstructorUsedError;
}

/// @nodoc
abstract class $LessonModelCopyWith<$Res> {
  factory $LessonModelCopyWith(
          LessonModel value, $Res Function(LessonModel) then) =
      _$LessonModelCopyWithImpl<$Res, LessonModel>;
  @useResult
  $Res call(
      {int id,
      String title,
      String? content,
      @JsonKey(name: 'video_url') String? videoUrl,
      @JsonKey(name: 'youtube_url') String? youtubeUrl,
      @JsonKey(name: 'video_duration') int? duration,
      @JsonKey(name: 'is_preview') bool isPreview,
      int order,
      @JsonKey(name: 'course_id') int courseId});
}

/// @nodoc
class _$LessonModelCopyWithImpl<$Res, $Val extends LessonModel>
    implements $LessonModelCopyWith<$Res> {
  _$LessonModelCopyWithImpl(this._value, this._then);

  // ignore: unused_field
  final $Val _value;
  // ignore: unused_field
  final $Res Function($Val) _then;

  /// Create a copy of LessonModel
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? id = null,
    Object? title = null,
    Object? content = freezed,
    Object? videoUrl = freezed,
    Object? youtubeUrl = freezed,
    Object? duration = freezed,
    Object? isPreview = null,
    Object? order = null,
    Object? courseId = null,
  }) {
    return _then(_value.copyWith(
      id: null == id
          ? _value.id
          : id // ignore: cast_nullable_to_non_nullable
              as int,
      title: null == title
          ? _value.title
          : title // ignore: cast_nullable_to_non_nullable
              as String,
      content: freezed == content
          ? _value.content
          : content // ignore: cast_nullable_to_non_nullable
              as String?,
      videoUrl: freezed == videoUrl
          ? _value.videoUrl
          : videoUrl // ignore: cast_nullable_to_non_nullable
              as String?,
      youtubeUrl: freezed == youtubeUrl
          ? _value.youtubeUrl
          : youtubeUrl // ignore: cast_nullable_to_non_nullable
              as String?,
      duration: freezed == duration
          ? _value.duration
          : duration // ignore: cast_nullable_to_non_nullable
              as int?,
      isPreview: null == isPreview
          ? _value.isPreview
          : isPreview // ignore: cast_nullable_to_non_nullable
              as bool,
      order: null == order
          ? _value.order
          : order // ignore: cast_nullable_to_non_nullable
              as int,
      courseId: null == courseId
          ? _value.courseId
          : courseId // ignore: cast_nullable_to_non_nullable
              as int,
    ) as $Val);
  }
}

/// @nodoc
abstract class _$$LessonModelImplCopyWith<$Res>
    implements $LessonModelCopyWith<$Res> {
  factory _$$LessonModelImplCopyWith(
          _$LessonModelImpl value, $Res Function(_$LessonModelImpl) then) =
      __$$LessonModelImplCopyWithImpl<$Res>;
  @override
  @useResult
  $Res call(
      {int id,
      String title,
      String? content,
      @JsonKey(name: 'video_url') String? videoUrl,
      @JsonKey(name: 'youtube_url') String? youtubeUrl,
      @JsonKey(name: 'video_duration') int? duration,
      @JsonKey(name: 'is_preview') bool isPreview,
      int order,
      @JsonKey(name: 'course_id') int courseId});
}

/// @nodoc
class __$$LessonModelImplCopyWithImpl<$Res>
    extends _$LessonModelCopyWithImpl<$Res, _$LessonModelImpl>
    implements _$$LessonModelImplCopyWith<$Res> {
  __$$LessonModelImplCopyWithImpl(
      _$LessonModelImpl _value, $Res Function(_$LessonModelImpl) _then)
      : super(_value, _then);

  /// Create a copy of LessonModel
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? id = null,
    Object? title = null,
    Object? content = freezed,
    Object? videoUrl = freezed,
    Object? youtubeUrl = freezed,
    Object? duration = freezed,
    Object? isPreview = null,
    Object? order = null,
    Object? courseId = null,
  }) {
    return _then(_$LessonModelImpl(
      id: null == id
          ? _value.id
          : id // ignore: cast_nullable_to_non_nullable
              as int,
      title: null == title
          ? _value.title
          : title // ignore: cast_nullable_to_non_nullable
              as String,
      content: freezed == content
          ? _value.content
          : content // ignore: cast_nullable_to_non_nullable
              as String?,
      videoUrl: freezed == videoUrl
          ? _value.videoUrl
          : videoUrl // ignore: cast_nullable_to_non_nullable
              as String?,
      youtubeUrl: freezed == youtubeUrl
          ? _value.youtubeUrl
          : youtubeUrl // ignore: cast_nullable_to_non_nullable
              as String?,
      duration: freezed == duration
          ? _value.duration
          : duration // ignore: cast_nullable_to_non_nullable
              as int?,
      isPreview: null == isPreview
          ? _value.isPreview
          : isPreview // ignore: cast_nullable_to_non_nullable
              as bool,
      order: null == order
          ? _value.order
          : order // ignore: cast_nullable_to_non_nullable
              as int,
      courseId: null == courseId
          ? _value.courseId
          : courseId // ignore: cast_nullable_to_non_nullable
              as int,
    ));
  }
}

/// @nodoc
@JsonSerializable()
class _$LessonModelImpl extends _LessonModel {
  const _$LessonModelImpl(
      {required this.id,
      required this.title,
      this.content,
      @JsonKey(name: 'video_url') this.videoUrl,
      @JsonKey(name: 'youtube_url') this.youtubeUrl,
      @JsonKey(name: 'video_duration') this.duration,
      @JsonKey(name: 'is_preview') this.isPreview = false,
      required this.order,
      @JsonKey(name: 'course_id') required this.courseId})
      : super._();

  factory _$LessonModelImpl.fromJson(Map<String, dynamic> json) =>
      _$$LessonModelImplFromJson(json);

  @override
  final int id;
  @override
  final String title;
  @override
  final String? content;
  @override
  @JsonKey(name: 'video_url')
  final String? videoUrl;
  @override
  @JsonKey(name: 'youtube_url')
  final String? youtubeUrl;
  @override
  @JsonKey(name: 'video_duration')
  final int? duration;
  @override
  @JsonKey(name: 'is_preview')
  final bool isPreview;
  @override
  final int order;
  @override
  @JsonKey(name: 'course_id')
  final int courseId;

  @override
  String toString() {
    return 'LessonModel(id: $id, title: $title, content: $content, videoUrl: $videoUrl, youtubeUrl: $youtubeUrl, duration: $duration, isPreview: $isPreview, order: $order, courseId: $courseId)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$LessonModelImpl &&
            (identical(other.id, id) || other.id == id) &&
            (identical(other.title, title) || other.title == title) &&
            (identical(other.content, content) || other.content == content) &&
            (identical(other.videoUrl, videoUrl) ||
                other.videoUrl == videoUrl) &&
            (identical(other.youtubeUrl, youtubeUrl) ||
                other.youtubeUrl == youtubeUrl) &&
            (identical(other.duration, duration) ||
                other.duration == duration) &&
            (identical(other.isPreview, isPreview) ||
                other.isPreview == isPreview) &&
            (identical(other.order, order) || other.order == order) &&
            (identical(other.courseId, courseId) ||
                other.courseId == courseId));
  }

  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  int get hashCode => Object.hash(runtimeType, id, title, content, videoUrl,
      youtubeUrl, duration, isPreview, order, courseId);

  /// Create a copy of LessonModel
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  @pragma('vm:prefer-inline')
  _$$LessonModelImplCopyWith<_$LessonModelImpl> get copyWith =>
      __$$LessonModelImplCopyWithImpl<_$LessonModelImpl>(this, _$identity);

  @override
  Map<String, dynamic> toJson() {
    return _$$LessonModelImplToJson(
      this,
    );
  }
}

abstract class _LessonModel extends LessonModel {
  const factory _LessonModel(
          {required final int id,
          required final String title,
          final String? content,
          @JsonKey(name: 'video_url') final String? videoUrl,
          @JsonKey(name: 'youtube_url') final String? youtubeUrl,
          @JsonKey(name: 'video_duration') final int? duration,
          @JsonKey(name: 'is_preview') final bool isPreview,
          required final int order,
          @JsonKey(name: 'course_id') required final int courseId}) =
      _$LessonModelImpl;
  const _LessonModel._() : super._();

  factory _LessonModel.fromJson(Map<String, dynamic> json) =
      _$LessonModelImpl.fromJson;

  @override
  int get id;
  @override
  String get title;
  @override
  String? get content;
  @override
  @JsonKey(name: 'video_url')
  String? get videoUrl;
  @override
  @JsonKey(name: 'youtube_url')
  String? get youtubeUrl;
  @override
  @JsonKey(name: 'video_duration')
  int? get duration;
  @override
  @JsonKey(name: 'is_preview')
  bool get isPreview;
  @override
  int get order;
  @override
  @JsonKey(name: 'course_id')
  int get courseId;

  /// Create a copy of LessonModel
  /// with the given fields replaced by the non-null parameter values.
  @override
  @JsonKey(includeFromJson: false, includeToJson: false)
  _$$LessonModelImplCopyWith<_$LessonModelImpl> get copyWith =>
      throw _privateConstructorUsedError;
}

QuizModel _$QuizModelFromJson(Map<String, dynamic> json) {
  return _QuizModel.fromJson(json);
}

/// @nodoc
mixin _$QuizModel {
  int get id => throw _privateConstructorUsedError;
  String get title => throw _privateConstructorUsedError;
  @JsonKey(name: 'questions_count')
  int get questionsCount => throw _privateConstructorUsedError;
  @JsonKey(name: 'time_limit')
  int? get timeLimit => throw _privateConstructorUsedError;

  /// Serializes this QuizModel to a JSON map.
  Map<String, dynamic> toJson() => throw _privateConstructorUsedError;

  /// Create a copy of QuizModel
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  $QuizModelCopyWith<QuizModel> get copyWith =>
      throw _privateConstructorUsedError;
}

/// @nodoc
abstract class $QuizModelCopyWith<$Res> {
  factory $QuizModelCopyWith(QuizModel value, $Res Function(QuizModel) then) =
      _$QuizModelCopyWithImpl<$Res, QuizModel>;
  @useResult
  $Res call(
      {int id,
      String title,
      @JsonKey(name: 'questions_count') int questionsCount,
      @JsonKey(name: 'time_limit') int? timeLimit});
}

/// @nodoc
class _$QuizModelCopyWithImpl<$Res, $Val extends QuizModel>
    implements $QuizModelCopyWith<$Res> {
  _$QuizModelCopyWithImpl(this._value, this._then);

  // ignore: unused_field
  final $Val _value;
  // ignore: unused_field
  final $Res Function($Val) _then;

  /// Create a copy of QuizModel
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? id = null,
    Object? title = null,
    Object? questionsCount = null,
    Object? timeLimit = freezed,
  }) {
    return _then(_value.copyWith(
      id: null == id
          ? _value.id
          : id // ignore: cast_nullable_to_non_nullable
              as int,
      title: null == title
          ? _value.title
          : title // ignore: cast_nullable_to_non_nullable
              as String,
      questionsCount: null == questionsCount
          ? _value.questionsCount
          : questionsCount // ignore: cast_nullable_to_non_nullable
              as int,
      timeLimit: freezed == timeLimit
          ? _value.timeLimit
          : timeLimit // ignore: cast_nullable_to_non_nullable
              as int?,
    ) as $Val);
  }
}

/// @nodoc
abstract class _$$QuizModelImplCopyWith<$Res>
    implements $QuizModelCopyWith<$Res> {
  factory _$$QuizModelImplCopyWith(
          _$QuizModelImpl value, $Res Function(_$QuizModelImpl) then) =
      __$$QuizModelImplCopyWithImpl<$Res>;
  @override
  @useResult
  $Res call(
      {int id,
      String title,
      @JsonKey(name: 'questions_count') int questionsCount,
      @JsonKey(name: 'time_limit') int? timeLimit});
}

/// @nodoc
class __$$QuizModelImplCopyWithImpl<$Res>
    extends _$QuizModelCopyWithImpl<$Res, _$QuizModelImpl>
    implements _$$QuizModelImplCopyWith<$Res> {
  __$$QuizModelImplCopyWithImpl(
      _$QuizModelImpl _value, $Res Function(_$QuizModelImpl) _then)
      : super(_value, _then);

  /// Create a copy of QuizModel
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? id = null,
    Object? title = null,
    Object? questionsCount = null,
    Object? timeLimit = freezed,
  }) {
    return _then(_$QuizModelImpl(
      id: null == id
          ? _value.id
          : id // ignore: cast_nullable_to_non_nullable
              as int,
      title: null == title
          ? _value.title
          : title // ignore: cast_nullable_to_non_nullable
              as String,
      questionsCount: null == questionsCount
          ? _value.questionsCount
          : questionsCount // ignore: cast_nullable_to_non_nullable
              as int,
      timeLimit: freezed == timeLimit
          ? _value.timeLimit
          : timeLimit // ignore: cast_nullable_to_non_nullable
              as int?,
    ));
  }
}

/// @nodoc
@JsonSerializable()
class _$QuizModelImpl extends _QuizModel {
  const _$QuizModelImpl(
      {required this.id,
      required this.title,
      @JsonKey(name: 'questions_count') required this.questionsCount,
      @JsonKey(name: 'time_limit') this.timeLimit})
      : super._();

  factory _$QuizModelImpl.fromJson(Map<String, dynamic> json) =>
      _$$QuizModelImplFromJson(json);

  @override
  final int id;
  @override
  final String title;
  @override
  @JsonKey(name: 'questions_count')
  final int questionsCount;
  @override
  @JsonKey(name: 'time_limit')
  final int? timeLimit;

  @override
  String toString() {
    return 'QuizModel(id: $id, title: $title, questionsCount: $questionsCount, timeLimit: $timeLimit)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$QuizModelImpl &&
            (identical(other.id, id) || other.id == id) &&
            (identical(other.title, title) || other.title == title) &&
            (identical(other.questionsCount, questionsCount) ||
                other.questionsCount == questionsCount) &&
            (identical(other.timeLimit, timeLimit) ||
                other.timeLimit == timeLimit));
  }

  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  int get hashCode =>
      Object.hash(runtimeType, id, title, questionsCount, timeLimit);

  /// Create a copy of QuizModel
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  @pragma('vm:prefer-inline')
  _$$QuizModelImplCopyWith<_$QuizModelImpl> get copyWith =>
      __$$QuizModelImplCopyWithImpl<_$QuizModelImpl>(this, _$identity);

  @override
  Map<String, dynamic> toJson() {
    return _$$QuizModelImplToJson(
      this,
    );
  }
}

abstract class _QuizModel extends QuizModel {
  const factory _QuizModel(
      {required final int id,
      required final String title,
      @JsonKey(name: 'questions_count') required final int questionsCount,
      @JsonKey(name: 'time_limit') final int? timeLimit}) = _$QuizModelImpl;
  const _QuizModel._() : super._();

  factory _QuizModel.fromJson(Map<String, dynamic> json) =
      _$QuizModelImpl.fromJson;

  @override
  int get id;
  @override
  String get title;
  @override
  @JsonKey(name: 'questions_count')
  int get questionsCount;
  @override
  @JsonKey(name: 'time_limit')
  int? get timeLimit;

  /// Create a copy of QuizModel
  /// with the given fields replaced by the non-null parameter values.
  @override
  @JsonKey(includeFromJson: false, includeToJson: false)
  _$$QuizModelImplCopyWith<_$QuizModelImpl> get copyWith =>
      throw _privateConstructorUsedError;
}

AssignmentModel _$AssignmentModelFromJson(Map<String, dynamic> json) {
  return _AssignmentModel.fromJson(json);
}

/// @nodoc
mixin _$AssignmentModel {
  int get id => throw _privateConstructorUsedError;
  String get title => throw _privateConstructorUsedError;
  String? get description => throw _privateConstructorUsedError;
  @JsonKey(name: 'total_points')
  int get totalPoints => throw _privateConstructorUsedError;

  /// Serializes this AssignmentModel to a JSON map.
  Map<String, dynamic> toJson() => throw _privateConstructorUsedError;

  /// Create a copy of AssignmentModel
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  $AssignmentModelCopyWith<AssignmentModel> get copyWith =>
      throw _privateConstructorUsedError;
}

/// @nodoc
abstract class $AssignmentModelCopyWith<$Res> {
  factory $AssignmentModelCopyWith(
          AssignmentModel value, $Res Function(AssignmentModel) then) =
      _$AssignmentModelCopyWithImpl<$Res, AssignmentModel>;
  @useResult
  $Res call(
      {int id,
      String title,
      String? description,
      @JsonKey(name: 'total_points') int totalPoints});
}

/// @nodoc
class _$AssignmentModelCopyWithImpl<$Res, $Val extends AssignmentModel>
    implements $AssignmentModelCopyWith<$Res> {
  _$AssignmentModelCopyWithImpl(this._value, this._then);

  // ignore: unused_field
  final $Val _value;
  // ignore: unused_field
  final $Res Function($Val) _then;

  /// Create a copy of AssignmentModel
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? id = null,
    Object? title = null,
    Object? description = freezed,
    Object? totalPoints = null,
  }) {
    return _then(_value.copyWith(
      id: null == id
          ? _value.id
          : id // ignore: cast_nullable_to_non_nullable
              as int,
      title: null == title
          ? _value.title
          : title // ignore: cast_nullable_to_non_nullable
              as String,
      description: freezed == description
          ? _value.description
          : description // ignore: cast_nullable_to_non_nullable
              as String?,
      totalPoints: null == totalPoints
          ? _value.totalPoints
          : totalPoints // ignore: cast_nullable_to_non_nullable
              as int,
    ) as $Val);
  }
}

/// @nodoc
abstract class _$$AssignmentModelImplCopyWith<$Res>
    implements $AssignmentModelCopyWith<$Res> {
  factory _$$AssignmentModelImplCopyWith(_$AssignmentModelImpl value,
          $Res Function(_$AssignmentModelImpl) then) =
      __$$AssignmentModelImplCopyWithImpl<$Res>;
  @override
  @useResult
  $Res call(
      {int id,
      String title,
      String? description,
      @JsonKey(name: 'total_points') int totalPoints});
}

/// @nodoc
class __$$AssignmentModelImplCopyWithImpl<$Res>
    extends _$AssignmentModelCopyWithImpl<$Res, _$AssignmentModelImpl>
    implements _$$AssignmentModelImplCopyWith<$Res> {
  __$$AssignmentModelImplCopyWithImpl(
      _$AssignmentModelImpl _value, $Res Function(_$AssignmentModelImpl) _then)
      : super(_value, _then);

  /// Create a copy of AssignmentModel
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? id = null,
    Object? title = null,
    Object? description = freezed,
    Object? totalPoints = null,
  }) {
    return _then(_$AssignmentModelImpl(
      id: null == id
          ? _value.id
          : id // ignore: cast_nullable_to_non_nullable
              as int,
      title: null == title
          ? _value.title
          : title // ignore: cast_nullable_to_non_nullable
              as String,
      description: freezed == description
          ? _value.description
          : description // ignore: cast_nullable_to_non_nullable
              as String?,
      totalPoints: null == totalPoints
          ? _value.totalPoints
          : totalPoints // ignore: cast_nullable_to_non_nullable
              as int,
    ));
  }
}

/// @nodoc
@JsonSerializable()
class _$AssignmentModelImpl extends _AssignmentModel {
  const _$AssignmentModelImpl(
      {required this.id,
      required this.title,
      this.description,
      @JsonKey(name: 'total_points') required this.totalPoints})
      : super._();

  factory _$AssignmentModelImpl.fromJson(Map<String, dynamic> json) =>
      _$$AssignmentModelImplFromJson(json);

  @override
  final int id;
  @override
  final String title;
  @override
  final String? description;
  @override
  @JsonKey(name: 'total_points')
  final int totalPoints;

  @override
  String toString() {
    return 'AssignmentModel(id: $id, title: $title, description: $description, totalPoints: $totalPoints)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$AssignmentModelImpl &&
            (identical(other.id, id) || other.id == id) &&
            (identical(other.title, title) || other.title == title) &&
            (identical(other.description, description) ||
                other.description == description) &&
            (identical(other.totalPoints, totalPoints) ||
                other.totalPoints == totalPoints));
  }

  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  int get hashCode =>
      Object.hash(runtimeType, id, title, description, totalPoints);

  /// Create a copy of AssignmentModel
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  @pragma('vm:prefer-inline')
  _$$AssignmentModelImplCopyWith<_$AssignmentModelImpl> get copyWith =>
      __$$AssignmentModelImplCopyWithImpl<_$AssignmentModelImpl>(
          this, _$identity);

  @override
  Map<String, dynamic> toJson() {
    return _$$AssignmentModelImplToJson(
      this,
    );
  }
}

abstract class _AssignmentModel extends AssignmentModel {
  const factory _AssignmentModel(
          {required final int id,
          required final String title,
          final String? description,
          @JsonKey(name: 'total_points') required final int totalPoints}) =
      _$AssignmentModelImpl;
  const _AssignmentModel._() : super._();

  factory _AssignmentModel.fromJson(Map<String, dynamic> json) =
      _$AssignmentModelImpl.fromJson;

  @override
  int get id;
  @override
  String get title;
  @override
  String? get description;
  @override
  @JsonKey(name: 'total_points')
  int get totalPoints;

  /// Create a copy of AssignmentModel
  /// with the given fields replaced by the non-null parameter values.
  @override
  @JsonKey(includeFromJson: false, includeToJson: false)
  _$$AssignmentModelImplCopyWith<_$AssignmentModelImpl> get copyWith =>
      throw _privateConstructorUsedError;
}
