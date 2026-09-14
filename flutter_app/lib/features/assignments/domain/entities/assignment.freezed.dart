// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint
// ignore_for_file: unused_element, deprecated_member_use, deprecated_member_use_from_same_package, use_function_type_syntax_for_parameters, unnecessary_const, avoid_init_to_null, invalid_override_different_default_values_named, prefer_expression_function_bodies, annotate_overrides, invalid_annotation_target, unnecessary_question_mark

part of 'assignment.dart';

// **************************************************************************
// FreezedGenerator
// **************************************************************************

T _$identity<T>(T value) => value;

final _privateConstructorUsedError = UnsupportedError(
    'It seems like you constructed your class using `MyClass._()`. This constructor is only meant to be used by freezed and you are not supposed to need it nor use it.\nPlease check the documentation here for more information: https://github.com/rrousselGit/freezed#adding-getters-and-methods-to-our-models');

/// @nodoc
mixin _$Assignment {
  String get id => throw _privateConstructorUsedError;
  String get title => throw _privateConstructorUsedError;
  String? get description => throw _privateConstructorUsedError;
  int get totalPoints => throw _privateConstructorUsedError;
  DateTime get createdAt => throw _privateConstructorUsedError;
  String? get fileUrl => throw _privateConstructorUsedError;
  bool get isSubmitted => throw _privateConstructorUsedError;
  AssignmentSubmission? get submission => throw _privateConstructorUsedError;

  /// Create a copy of Assignment
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  $AssignmentCopyWith<Assignment> get copyWith =>
      throw _privateConstructorUsedError;
}

/// @nodoc
abstract class $AssignmentCopyWith<$Res> {
  factory $AssignmentCopyWith(
          Assignment value, $Res Function(Assignment) then) =
      _$AssignmentCopyWithImpl<$Res, Assignment>;
  @useResult
  $Res call(
      {String id,
      String title,
      String? description,
      int totalPoints,
      DateTime createdAt,
      String? fileUrl,
      bool isSubmitted,
      AssignmentSubmission? submission});

  $AssignmentSubmissionCopyWith<$Res>? get submission;
}

/// @nodoc
class _$AssignmentCopyWithImpl<$Res, $Val extends Assignment>
    implements $AssignmentCopyWith<$Res> {
  _$AssignmentCopyWithImpl(this._value, this._then);

  // ignore: unused_field
  final $Val _value;
  // ignore: unused_field
  final $Res Function($Val) _then;

  /// Create a copy of Assignment
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
              as String,
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
              as DateTime,
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
              as AssignmentSubmission?,
    ) as $Val);
  }

  /// Create a copy of Assignment
  /// with the given fields replaced by the non-null parameter values.
  @override
  @pragma('vm:prefer-inline')
  $AssignmentSubmissionCopyWith<$Res>? get submission {
    if (_value.submission == null) {
      return null;
    }

    return $AssignmentSubmissionCopyWith<$Res>(_value.submission!, (value) {
      return _then(_value.copyWith(submission: value) as $Val);
    });
  }
}

/// @nodoc
abstract class _$$AssignmentImplCopyWith<$Res>
    implements $AssignmentCopyWith<$Res> {
  factory _$$AssignmentImplCopyWith(
          _$AssignmentImpl value, $Res Function(_$AssignmentImpl) then) =
      __$$AssignmentImplCopyWithImpl<$Res>;
  @override
  @useResult
  $Res call(
      {String id,
      String title,
      String? description,
      int totalPoints,
      DateTime createdAt,
      String? fileUrl,
      bool isSubmitted,
      AssignmentSubmission? submission});

  @override
  $AssignmentSubmissionCopyWith<$Res>? get submission;
}

/// @nodoc
class __$$AssignmentImplCopyWithImpl<$Res>
    extends _$AssignmentCopyWithImpl<$Res, _$AssignmentImpl>
    implements _$$AssignmentImplCopyWith<$Res> {
  __$$AssignmentImplCopyWithImpl(
      _$AssignmentImpl _value, $Res Function(_$AssignmentImpl) _then)
      : super(_value, _then);

  /// Create a copy of Assignment
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
    return _then(_$AssignmentImpl(
      id: null == id
          ? _value.id
          : id // ignore: cast_nullable_to_non_nullable
              as String,
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
              as DateTime,
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
              as AssignmentSubmission?,
    ));
  }
}

/// @nodoc

class _$AssignmentImpl implements _Assignment {
  const _$AssignmentImpl(
      {required this.id,
      required this.title,
      this.description,
      required this.totalPoints,
      required this.createdAt,
      this.fileUrl,
      this.isSubmitted = false,
      this.submission});

  @override
  final String id;
  @override
  final String title;
  @override
  final String? description;
  @override
  final int totalPoints;
  @override
  final DateTime createdAt;
  @override
  final String? fileUrl;
  @override
  @JsonKey()
  final bool isSubmitted;
  @override
  final AssignmentSubmission? submission;

  @override
  String toString() {
    return 'Assignment(id: $id, title: $title, description: $description, totalPoints: $totalPoints, createdAt: $createdAt, fileUrl: $fileUrl, isSubmitted: $isSubmitted, submission: $submission)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$AssignmentImpl &&
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

  @override
  int get hashCode => Object.hash(runtimeType, id, title, description,
      totalPoints, createdAt, fileUrl, isSubmitted, submission);

  /// Create a copy of Assignment
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  @pragma('vm:prefer-inline')
  _$$AssignmentImplCopyWith<_$AssignmentImpl> get copyWith =>
      __$$AssignmentImplCopyWithImpl<_$AssignmentImpl>(this, _$identity);
}

abstract class _Assignment implements Assignment {
  const factory _Assignment(
      {required final String id,
      required final String title,
      final String? description,
      required final int totalPoints,
      required final DateTime createdAt,
      final String? fileUrl,
      final bool isSubmitted,
      final AssignmentSubmission? submission}) = _$AssignmentImpl;

  @override
  String get id;
  @override
  String get title;
  @override
  String? get description;
  @override
  int get totalPoints;
  @override
  DateTime get createdAt;
  @override
  String? get fileUrl;
  @override
  bool get isSubmitted;
  @override
  AssignmentSubmission? get submission;

  /// Create a copy of Assignment
  /// with the given fields replaced by the non-null parameter values.
  @override
  @JsonKey(includeFromJson: false, includeToJson: false)
  _$$AssignmentImplCopyWith<_$AssignmentImpl> get copyWith =>
      throw _privateConstructorUsedError;
}

/// @nodoc
mixin _$AssignmentSubmission {
  String get id => throw _privateConstructorUsedError;
  String get assignmentId => throw _privateConstructorUsedError;
  String get userId => throw _privateConstructorUsedError;
  String get content => throw _privateConstructorUsedError;
  String? get fileUrl => throw _privateConstructorUsedError;
  double? get grade => throw _privateConstructorUsedError;
  String? get feedback => throw _privateConstructorUsedError;
  DateTime get submittedAt => throw _privateConstructorUsedError;

  /// Create a copy of AssignmentSubmission
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  $AssignmentSubmissionCopyWith<AssignmentSubmission> get copyWith =>
      throw _privateConstructorUsedError;
}

/// @nodoc
abstract class $AssignmentSubmissionCopyWith<$Res> {
  factory $AssignmentSubmissionCopyWith(AssignmentSubmission value,
          $Res Function(AssignmentSubmission) then) =
      _$AssignmentSubmissionCopyWithImpl<$Res, AssignmentSubmission>;
  @useResult
  $Res call(
      {String id,
      String assignmentId,
      String userId,
      String content,
      String? fileUrl,
      double? grade,
      String? feedback,
      DateTime submittedAt});
}

/// @nodoc
class _$AssignmentSubmissionCopyWithImpl<$Res,
        $Val extends AssignmentSubmission>
    implements $AssignmentSubmissionCopyWith<$Res> {
  _$AssignmentSubmissionCopyWithImpl(this._value, this._then);

  // ignore: unused_field
  final $Val _value;
  // ignore: unused_field
  final $Res Function($Val) _then;

  /// Create a copy of AssignmentSubmission
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
              as String,
      assignmentId: null == assignmentId
          ? _value.assignmentId
          : assignmentId // ignore: cast_nullable_to_non_nullable
              as String,
      userId: null == userId
          ? _value.userId
          : userId // ignore: cast_nullable_to_non_nullable
              as String,
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
              as DateTime,
    ) as $Val);
  }
}

/// @nodoc
abstract class _$$AssignmentSubmissionImplCopyWith<$Res>
    implements $AssignmentSubmissionCopyWith<$Res> {
  factory _$$AssignmentSubmissionImplCopyWith(_$AssignmentSubmissionImpl value,
          $Res Function(_$AssignmentSubmissionImpl) then) =
      __$$AssignmentSubmissionImplCopyWithImpl<$Res>;
  @override
  @useResult
  $Res call(
      {String id,
      String assignmentId,
      String userId,
      String content,
      String? fileUrl,
      double? grade,
      String? feedback,
      DateTime submittedAt});
}

/// @nodoc
class __$$AssignmentSubmissionImplCopyWithImpl<$Res>
    extends _$AssignmentSubmissionCopyWithImpl<$Res, _$AssignmentSubmissionImpl>
    implements _$$AssignmentSubmissionImplCopyWith<$Res> {
  __$$AssignmentSubmissionImplCopyWithImpl(_$AssignmentSubmissionImpl _value,
      $Res Function(_$AssignmentSubmissionImpl) _then)
      : super(_value, _then);

  /// Create a copy of AssignmentSubmission
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
    return _then(_$AssignmentSubmissionImpl(
      id: null == id
          ? _value.id
          : id // ignore: cast_nullable_to_non_nullable
              as String,
      assignmentId: null == assignmentId
          ? _value.assignmentId
          : assignmentId // ignore: cast_nullable_to_non_nullable
              as String,
      userId: null == userId
          ? _value.userId
          : userId // ignore: cast_nullable_to_non_nullable
              as String,
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
              as DateTime,
    ));
  }
}

/// @nodoc

class _$AssignmentSubmissionImpl implements _AssignmentSubmission {
  const _$AssignmentSubmissionImpl(
      {required this.id,
      required this.assignmentId,
      required this.userId,
      required this.content,
      this.fileUrl,
      this.grade,
      this.feedback,
      required this.submittedAt});

  @override
  final String id;
  @override
  final String assignmentId;
  @override
  final String userId;
  @override
  final String content;
  @override
  final String? fileUrl;
  @override
  final double? grade;
  @override
  final String? feedback;
  @override
  final DateTime submittedAt;

  @override
  String toString() {
    return 'AssignmentSubmission(id: $id, assignmentId: $assignmentId, userId: $userId, content: $content, fileUrl: $fileUrl, grade: $grade, feedback: $feedback, submittedAt: $submittedAt)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$AssignmentSubmissionImpl &&
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

  @override
  int get hashCode => Object.hash(runtimeType, id, assignmentId, userId,
      content, fileUrl, grade, feedback, submittedAt);

  /// Create a copy of AssignmentSubmission
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  @pragma('vm:prefer-inline')
  _$$AssignmentSubmissionImplCopyWith<_$AssignmentSubmissionImpl>
      get copyWith =>
          __$$AssignmentSubmissionImplCopyWithImpl<_$AssignmentSubmissionImpl>(
              this, _$identity);
}

abstract class _AssignmentSubmission implements AssignmentSubmission {
  const factory _AssignmentSubmission(
      {required final String id,
      required final String assignmentId,
      required final String userId,
      required final String content,
      final String? fileUrl,
      final double? grade,
      final String? feedback,
      required final DateTime submittedAt}) = _$AssignmentSubmissionImpl;

  @override
  String get id;
  @override
  String get assignmentId;
  @override
  String get userId;
  @override
  String get content;
  @override
  String? get fileUrl;
  @override
  double? get grade;
  @override
  String? get feedback;
  @override
  DateTime get submittedAt;

  /// Create a copy of AssignmentSubmission
  /// with the given fields replaced by the non-null parameter values.
  @override
  @JsonKey(includeFromJson: false, includeToJson: false)
  _$$AssignmentSubmissionImplCopyWith<_$AssignmentSubmissionImpl>
      get copyWith => throw _privateConstructorUsedError;
}
