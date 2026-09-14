// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint
// ignore_for_file: unused_element, deprecated_member_use, deprecated_member_use_from_same_package, use_function_type_syntax_for_parameters, unnecessary_const, avoid_init_to_null, invalid_override_different_default_values_named, prefer_expression_function_bodies, annotate_overrides, invalid_annotation_target, unnecessary_question_mark

part of 'assignment_model.dart';

// **************************************************************************
// FreezedGenerator
// **************************************************************************

T _$identity<T>(T value) => value;

final _privateConstructorUsedError = UnsupportedError(
    'It seems like you constructed your class using `MyClass._()`. This constructor is only meant to be used by freezed and you are not supposed to need it nor use it.\nPlease check the documentation here for more information: https://github.com/rrousselGit/freezed#adding-getters-and-methods-to-our-models');

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
  @JsonKey(name: 'created_at')
  String get createdAt => throw _privateConstructorUsedError;
  @JsonKey(name: 'file_url')
  String? get fileUrl => throw _privateConstructorUsedError;
  @JsonKey(name: 'is_submitted')
  bool get isSubmitted => throw _privateConstructorUsedError;
  AssignmentSubmissionModel? get submission =>
      throw _privateConstructorUsedError;

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
      @JsonKey(name: 'total_points') int totalPoints,
      @JsonKey(name: 'created_at') String createdAt,
      @JsonKey(name: 'file_url') String? fileUrl,
      @JsonKey(name: 'is_submitted') bool isSubmitted,
      AssignmentSubmissionModel? submission});

  $AssignmentSubmissionModelCopyWith<$Res>? get submission;
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
    Object? createdAt = null,
    Object? fileUrl = freezed,
    Object? isSubmitted = null,
    Object? submission = freezed,
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
      createdAt: null == createdAt
          ? _value.createdAt
          : createdAt // ignore: cast_nullable_to_non_nullable
              as String,
      fileUrl: freezed == fileUrl
          ? _value.fileUrl
          : fileUrl // ignore: cast_nullable_to_non_nullable
              as String?,
      isSubmitted: null == isSubmitted
          ? _value.isSubmitted
          : isSubmitted // ignore: cast_nullable_to_non_nullable
              as bool,
      submission: freezed == submission
          ? _value.submission
          : submission // ignore: cast_nullable_to_non_nullable
              as AssignmentSubmissionModel?,
    ) as $Val);
  }

  /// Create a copy of AssignmentModel
  /// with the given fields replaced by the non-null parameter values.
  @override
  @pragma('vm:prefer-inline')
  $AssignmentSubmissionModelCopyWith<$Res>? get submission {
    if (_value.submission == null) {
      return null;
    }

    return $AssignmentSubmissionModelCopyWith<$Res>(_value.submission!,
        (value) {
      return _then(_value.copyWith(submission: value) as $Val);
    });
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
      @JsonKey(name: 'total_points') int totalPoints,
      @JsonKey(name: 'created_at') String createdAt,
      @JsonKey(name: 'file_url') String? fileUrl,
      @JsonKey(name: 'is_submitted') bool isSubmitted,
      AssignmentSubmissionModel? submission});

  @override
  $AssignmentSubmissionModelCopyWith<$Res>? get submission;
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
    Object? createdAt = null,
    Object? fileUrl = freezed,
    Object? isSubmitted = null,
    Object? submission = freezed,
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
      createdAt: null == createdAt
          ? _value.createdAt
          : createdAt // ignore: cast_nullable_to_non_nullable
              as String,
      fileUrl: freezed == fileUrl
          ? _value.fileUrl
          : fileUrl // ignore: cast_nullable_to_non_nullable
              as String?,
      isSubmitted: null == isSubmitted
          ? _value.isSubmitted
          : isSubmitted // ignore: cast_nullable_to_non_nullable
              as bool,
      submission: freezed == submission
          ? _value.submission
          : submission // ignore: cast_nullable_to_non_nullable
              as AssignmentSubmissionModel?,
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
      @JsonKey(name: 'total_points') required this.totalPoints,
      @JsonKey(name: 'created_at') required this.createdAt,
      @JsonKey(name: 'file_url') this.fileUrl,
      @JsonKey(name: 'is_submitted') this.isSubmitted = false,
      this.submission})
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
  @JsonKey(name: 'created_at')
  final String createdAt;
  @override
  @JsonKey(name: 'file_url')
  final String? fileUrl;
  @override
  @JsonKey(name: 'is_submitted')
  final bool isSubmitted;
  @override
  final AssignmentSubmissionModel? submission;

  @override
  String toString() {
    return 'AssignmentModel(id: $id, title: $title, description: $description, totalPoints: $totalPoints, createdAt: $createdAt, fileUrl: $fileUrl, isSubmitted: $isSubmitted, submission: $submission)';
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
                other.totalPoints == totalPoints) &&
            (identical(other.createdAt, createdAt) ||
                other.createdAt == createdAt) &&
            (identical(other.fileUrl, fileUrl) || other.fileUrl == fileUrl) &&
            (identical(other.isSubmitted, isSubmitted) ||
                other.isSubmitted == isSubmitted) &&
            (identical(other.submission, submission) ||
                other.submission == submission));
  }

  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  int get hashCode => Object.hash(runtimeType, id, title, description,
      totalPoints, createdAt, fileUrl, isSubmitted, submission);

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
      @JsonKey(name: 'total_points') required final int totalPoints,
      @JsonKey(name: 'created_at') required final String createdAt,
      @JsonKey(name: 'file_url') final String? fileUrl,
      @JsonKey(name: 'is_submitted') final bool isSubmitted,
      final AssignmentSubmissionModel? submission}) = _$AssignmentModelImpl;
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
  @override
  @JsonKey(name: 'created_at')
  String get createdAt;
  @override
  @JsonKey(name: 'file_url')
  String? get fileUrl;
  @override
  @JsonKey(name: 'is_submitted')
  bool get isSubmitted;
  @override
  AssignmentSubmissionModel? get submission;

  /// Create a copy of AssignmentModel
  /// with the given fields replaced by the non-null parameter values.
  @override
  @JsonKey(includeFromJson: false, includeToJson: false)
  _$$AssignmentModelImplCopyWith<_$AssignmentModelImpl> get copyWith =>
      throw _privateConstructorUsedError;
}

AssignmentSubmissionModel _$AssignmentSubmissionModelFromJson(
    Map<String, dynamic> json) {
  return _AssignmentSubmissionModel.fromJson(json);
}

/// @nodoc
mixin _$AssignmentSubmissionModel {
  int get id => throw _privateConstructorUsedError;
  @JsonKey(name: 'assignment_id')
  int get assignmentId => throw _privateConstructorUsedError;
  @JsonKey(name: 'user_id')
  int get userId => throw _privateConstructorUsedError;
  String get content => throw _privateConstructorUsedError;
  @JsonKey(name: 'file_url')
  String? get fileUrl => throw _privateConstructorUsedError;
  double? get grade => throw _privateConstructorUsedError;
  String? get feedback => throw _privateConstructorUsedError;
  @JsonKey(name: 'submitted_at')
  String get submittedAt => throw _privateConstructorUsedError;

  /// Serializes this AssignmentSubmissionModel to a JSON map.
  Map<String, dynamic> toJson() => throw _privateConstructorUsedError;

  /// Create a copy of AssignmentSubmissionModel
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  $AssignmentSubmissionModelCopyWith<AssignmentSubmissionModel> get copyWith =>
      throw _privateConstructorUsedError;
}

/// @nodoc
abstract class $AssignmentSubmissionModelCopyWith<$Res> {
  factory $AssignmentSubmissionModelCopyWith(AssignmentSubmissionModel value,
          $Res Function(AssignmentSubmissionModel) then) =
      _$AssignmentSubmissionModelCopyWithImpl<$Res, AssignmentSubmissionModel>;
  @useResult
  $Res call(
      {int id,
      @JsonKey(name: 'assignment_id') int assignmentId,
      @JsonKey(name: 'user_id') int userId,
      String content,
      @JsonKey(name: 'file_url') String? fileUrl,
      double? grade,
      String? feedback,
      @JsonKey(name: 'submitted_at') String submittedAt});
}

/// @nodoc
class _$AssignmentSubmissionModelCopyWithImpl<$Res,
        $Val extends AssignmentSubmissionModel>
    implements $AssignmentSubmissionModelCopyWith<$Res> {
  _$AssignmentSubmissionModelCopyWithImpl(this._value, this._then);

  // ignore: unused_field
  final $Val _value;
  // ignore: unused_field
  final $Res Function($Val) _then;

  /// Create a copy of AssignmentSubmissionModel
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? id = null,
    Object? assignmentId = null,
    Object? userId = null,
    Object? content = null,
    Object? fileUrl = freezed,
    Object? grade = freezed,
    Object? feedback = freezed,
    Object? submittedAt = null,
  }) {
    return _then(_value.copyWith(
      id: null == id
          ? _value.id
          : id // ignore: cast_nullable_to_non_nullable
              as int,
      assignmentId: null == assignmentId
          ? _value.assignmentId
          : assignmentId // ignore: cast_nullable_to_non_nullable
              as int,
      userId: null == userId
          ? _value.userId
          : userId // ignore: cast_nullable_to_non_nullable
              as int,
      content: null == content
          ? _value.content
          : content // ignore: cast_nullable_to_non_nullable
              as String,
      fileUrl: freezed == fileUrl
          ? _value.fileUrl
          : fileUrl // ignore: cast_nullable_to_non_nullable
              as String?,
      grade: freezed == grade
          ? _value.grade
          : grade // ignore: cast_nullable_to_non_nullable
              as double?,
      feedback: freezed == feedback
          ? _value.feedback
          : feedback // ignore: cast_nullable_to_non_nullable
              as String?,
      submittedAt: null == submittedAt
          ? _value.submittedAt
          : submittedAt // ignore: cast_nullable_to_non_nullable
              as String,
    ) as $Val);
  }
}

/// @nodoc
abstract class _$$AssignmentSubmissionModelImplCopyWith<$Res>
    implements $AssignmentSubmissionModelCopyWith<$Res> {
  factory _$$AssignmentSubmissionModelImplCopyWith(
          _$AssignmentSubmissionModelImpl value,
          $Res Function(_$AssignmentSubmissionModelImpl) then) =
      __$$AssignmentSubmissionModelImplCopyWithImpl<$Res>;
  @override
  @useResult
  $Res call(
      {int id,
      @JsonKey(name: 'assignment_id') int assignmentId,
      @JsonKey(name: 'user_id') int userId,
      String content,
      @JsonKey(name: 'file_url') String? fileUrl,
      double? grade,
      String? feedback,
      @JsonKey(name: 'submitted_at') String submittedAt});
}

/// @nodoc
class __$$AssignmentSubmissionModelImplCopyWithImpl<$Res>
    extends _$AssignmentSubmissionModelCopyWithImpl<$Res,
        _$AssignmentSubmissionModelImpl>
    implements _$$AssignmentSubmissionModelImplCopyWith<$Res> {
  __$$AssignmentSubmissionModelImplCopyWithImpl(
      _$AssignmentSubmissionModelImpl _value,
      $Res Function(_$AssignmentSubmissionModelImpl) _then)
      : super(_value, _then);

  /// Create a copy of AssignmentSubmissionModel
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? id = null,
    Object? assignmentId = null,
    Object? userId = null,
    Object? content = null,
    Object? fileUrl = freezed,
    Object? grade = freezed,
    Object? feedback = freezed,
    Object? submittedAt = null,
  }) {
    return _then(_$AssignmentSubmissionModelImpl(
      id: null == id
          ? _value.id
          : id // ignore: cast_nullable_to_non_nullable
              as int,
      assignmentId: null == assignmentId
          ? _value.assignmentId
          : assignmentId // ignore: cast_nullable_to_non_nullable
              as int,
      userId: null == userId
          ? _value.userId
          : userId // ignore: cast_nullable_to_non_nullable
              as int,
      content: null == content
          ? _value.content
          : content // ignore: cast_nullable_to_non_nullable
              as String,
      fileUrl: freezed == fileUrl
          ? _value.fileUrl
          : fileUrl // ignore: cast_nullable_to_non_nullable
              as String?,
      grade: freezed == grade
          ? _value.grade
          : grade // ignore: cast_nullable_to_non_nullable
              as double?,
      feedback: freezed == feedback
          ? _value.feedback
          : feedback // ignore: cast_nullable_to_non_nullable
              as String?,
      submittedAt: null == submittedAt
          ? _value.submittedAt
          : submittedAt // ignore: cast_nullable_to_non_nullable
              as String,
    ));
  }
}

/// @nodoc
@JsonSerializable()
class _$AssignmentSubmissionModelImpl extends _AssignmentSubmissionModel {
  const _$AssignmentSubmissionModelImpl(
      {required this.id,
      @JsonKey(name: 'assignment_id') required this.assignmentId,
      @JsonKey(name: 'user_id') required this.userId,
      required this.content,
      @JsonKey(name: 'file_url') this.fileUrl,
      this.grade,
      this.feedback,
      @JsonKey(name: 'submitted_at') required this.submittedAt})
      : super._();

  factory _$AssignmentSubmissionModelImpl.fromJson(Map<String, dynamic> json) =>
      _$$AssignmentSubmissionModelImplFromJson(json);

  @override
  final int id;
  @override
  @JsonKey(name: 'assignment_id')
  final int assignmentId;
  @override
  @JsonKey(name: 'user_id')
  final int userId;
  @override
  final String content;
  @override
  @JsonKey(name: 'file_url')
  final String? fileUrl;
  @override
  final double? grade;
  @override
  final String? feedback;
  @override
  @JsonKey(name: 'submitted_at')
  final String submittedAt;

  @override
  String toString() {
    return 'AssignmentSubmissionModel(id: $id, assignmentId: $assignmentId, userId: $userId, content: $content, fileUrl: $fileUrl, grade: $grade, feedback: $feedback, submittedAt: $submittedAt)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$AssignmentSubmissionModelImpl &&
            (identical(other.id, id) || other.id == id) &&
            (identical(other.assignmentId, assignmentId) ||
                other.assignmentId == assignmentId) &&
            (identical(other.userId, userId) || other.userId == userId) &&
            (identical(other.content, content) || other.content == content) &&
            (identical(other.fileUrl, fileUrl) || other.fileUrl == fileUrl) &&
            (identical(other.grade, grade) || other.grade == grade) &&
            (identical(other.feedback, feedback) ||
                other.feedback == feedback) &&
            (identical(other.submittedAt, submittedAt) ||
                other.submittedAt == submittedAt));
  }

  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  int get hashCode => Object.hash(runtimeType, id, assignmentId, userId,
      content, fileUrl, grade, feedback, submittedAt);

  /// Create a copy of AssignmentSubmissionModel
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  @pragma('vm:prefer-inline')
  _$$AssignmentSubmissionModelImplCopyWith<_$AssignmentSubmissionModelImpl>
      get copyWith => __$$AssignmentSubmissionModelImplCopyWithImpl<
          _$AssignmentSubmissionModelImpl>(this, _$identity);

  @override
  Map<String, dynamic> toJson() {
    return _$$AssignmentSubmissionModelImplToJson(
      this,
    );
  }
}

abstract class _AssignmentSubmissionModel extends AssignmentSubmissionModel {
  const factory _AssignmentSubmissionModel(
          {required final int id,
          @JsonKey(name: 'assignment_id') required final int assignmentId,
          @JsonKey(name: 'user_id') required final int userId,
          required final String content,
          @JsonKey(name: 'file_url') final String? fileUrl,
          final double? grade,
          final String? feedback,
          @JsonKey(name: 'submitted_at') required final String submittedAt}) =
      _$AssignmentSubmissionModelImpl;
  const _AssignmentSubmissionModel._() : super._();

  factory _AssignmentSubmissionModel.fromJson(Map<String, dynamic> json) =
      _$AssignmentSubmissionModelImpl.fromJson;

  @override
  int get id;
  @override
  @JsonKey(name: 'assignment_id')
  int get assignmentId;
  @override
  @JsonKey(name: 'user_id')
  int get userId;
  @override
  String get content;
  @override
  @JsonKey(name: 'file_url')
  String? get fileUrl;
  @override
  double? get grade;
  @override
  String? get feedback;
  @override
  @JsonKey(name: 'submitted_at')
  String get submittedAt;

  /// Create a copy of AssignmentSubmissionModel
  /// with the given fields replaced by the non-null parameter values.
  @override
  @JsonKey(includeFromJson: false, includeToJson: false)
  _$$AssignmentSubmissionModelImplCopyWith<_$AssignmentSubmissionModelImpl>
      get copyWith => throw _privateConstructorUsedError;
}
