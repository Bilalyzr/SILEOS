// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint
// ignore_for_file: unused_element, deprecated_member_use, deprecated_member_use_from_same_package, use_function_type_syntax_for_parameters, unnecessary_const, avoid_init_to_null, invalid_override_different_default_values_named, prefer_expression_function_bodies, annotate_overrides, invalid_annotation_target, unnecessary_question_mark

part of 'quiz_model.dart';

// **************************************************************************
// FreezedGenerator
// **************************************************************************

T _$identity<T>(T value) => value;

final _privateConstructorUsedError = UnsupportedError(
    'It seems like you constructed your class using `MyClass._()`. This constructor is only meant to be used by freezed and you are not supposed to need it nor use it.\nPlease check the documentation here for more information: https://github.com/rrousselGit/freezed#adding-getters-and-methods-to-our-models');

QuizModel _$QuizModelFromJson(Map<String, dynamic> json) {
  return _QuizModel.fromJson(json);
}

/// @nodoc
mixin _$QuizModel {
  int get id => throw _privateConstructorUsedError;
  String get title => throw _privateConstructorUsedError;
  String? get description => throw _privateConstructorUsedError;
  @JsonKey(name: 'timeLimit')
  int get timeLimit => throw _privateConstructorUsedError;
  @JsonKey(name: 'passingScore')
  int get passingScore => throw _privateConstructorUsedError;
  @JsonKey(name: 'maxAttempts')
  int get maxAttempts => throw _privateConstructorUsedError;
  List<QuizQuestionModel> get questions => throw _privateConstructorUsedError;

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
      String? description,
      @JsonKey(name: 'timeLimit') int timeLimit,
      @JsonKey(name: 'passingScore') int passingScore,
      @JsonKey(name: 'maxAttempts') int maxAttempts,
      List<QuizQuestionModel> questions});
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
    Object? description = freezed,
    Object? timeLimit = null,
    Object? passingScore = null,
    Object? maxAttempts = null,
    Object? questions = null,
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
      timeLimit: null == timeLimit
          ? _value.timeLimit
          : timeLimit // ignore: cast_nullable_to_non_nullable
              as int,
      passingScore: null == passingScore
          ? _value.passingScore
          : passingScore // ignore: cast_nullable_to_non_nullable
              as int,
      maxAttempts: null == maxAttempts
          ? _value.maxAttempts
          : maxAttempts // ignore: cast_nullable_to_non_nullable
              as int,
      questions: null == questions
          ? _value.questions
          : questions // ignore: cast_nullable_to_non_nullable
              as List<QuizQuestionModel>,
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
      String? description,
      @JsonKey(name: 'timeLimit') int timeLimit,
      @JsonKey(name: 'passingScore') int passingScore,
      @JsonKey(name: 'maxAttempts') int maxAttempts,
      List<QuizQuestionModel> questions});
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
    Object? description = freezed,
    Object? timeLimit = null,
    Object? passingScore = null,
    Object? maxAttempts = null,
    Object? questions = null,
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
      description: freezed == description
          ? _value.description
          : description // ignore: cast_nullable_to_non_nullable
              as String?,
      timeLimit: null == timeLimit
          ? _value.timeLimit
          : timeLimit // ignore: cast_nullable_to_non_nullable
              as int,
      passingScore: null == passingScore
          ? _value.passingScore
          : passingScore // ignore: cast_nullable_to_non_nullable
              as int,
      maxAttempts: null == maxAttempts
          ? _value.maxAttempts
          : maxAttempts // ignore: cast_nullable_to_non_nullable
              as int,
      questions: null == questions
          ? _value._questions
          : questions // ignore: cast_nullable_to_non_nullable
              as List<QuizQuestionModel>,
    ));
  }
}

/// @nodoc
@JsonSerializable()
class _$QuizModelImpl extends _QuizModel {
  const _$QuizModelImpl(
      {required this.id,
      required this.title,
      this.description,
      @JsonKey(name: 'timeLimit') required this.timeLimit,
      @JsonKey(name: 'passingScore') required this.passingScore,
      @JsonKey(name: 'maxAttempts') required this.maxAttempts,
      final List<QuizQuestionModel> questions = const []})
      : _questions = questions,
        super._();

  factory _$QuizModelImpl.fromJson(Map<String, dynamic> json) =>
      _$$QuizModelImplFromJson(json);

  @override
  final int id;
  @override
  final String title;
  @override
  final String? description;
  @override
  @JsonKey(name: 'timeLimit')
  final int timeLimit;
  @override
  @JsonKey(name: 'passingScore')
  final int passingScore;
  @override
  @JsonKey(name: 'maxAttempts')
  final int maxAttempts;
  final List<QuizQuestionModel> _questions;
  @override
  @JsonKey()
  List<QuizQuestionModel> get questions {
    if (_questions is EqualUnmodifiableListView) return _questions;
    // ignore: implicit_dynamic_type
    return EqualUnmodifiableListView(_questions);
  }

  @override
  String toString() {
    return 'QuizModel(id: $id, title: $title, description: $description, timeLimit: $timeLimit, passingScore: $passingScore, maxAttempts: $maxAttempts, questions: $questions)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$QuizModelImpl &&
            (identical(other.id, id) || other.id == id) &&
            (identical(other.title, title) || other.title == title) &&
            (identical(other.description, description) ||
                other.description == description) &&
            (identical(other.timeLimit, timeLimit) ||
                other.timeLimit == timeLimit) &&
            (identical(other.passingScore, passingScore) ||
                other.passingScore == passingScore) &&
            (identical(other.maxAttempts, maxAttempts) ||
                other.maxAttempts == maxAttempts) &&
            const DeepCollectionEquality()
                .equals(other._questions, _questions));
  }

  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  int get hashCode => Object.hash(
      runtimeType,
      id,
      title,
      description,
      timeLimit,
      passingScore,
      maxAttempts,
      const DeepCollectionEquality().hash(_questions));

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
      final String? description,
      @JsonKey(name: 'timeLimit') required final int timeLimit,
      @JsonKey(name: 'passingScore') required final int passingScore,
      @JsonKey(name: 'maxAttempts') required final int maxAttempts,
      final List<QuizQuestionModel> questions}) = _$QuizModelImpl;
  const _QuizModel._() : super._();

  factory _QuizModel.fromJson(Map<String, dynamic> json) =
      _$QuizModelImpl.fromJson;

  @override
  int get id;
  @override
  String get title;
  @override
  String? get description;
  @override
  @JsonKey(name: 'timeLimit')
  int get timeLimit;
  @override
  @JsonKey(name: 'passingScore')
  int get passingScore;
  @override
  @JsonKey(name: 'maxAttempts')
  int get maxAttempts;
  @override
  List<QuizQuestionModel> get questions;

  /// Create a copy of QuizModel
  /// with the given fields replaced by the non-null parameter values.
  @override
  @JsonKey(includeFromJson: false, includeToJson: false)
  _$$QuizModelImplCopyWith<_$QuizModelImpl> get copyWith =>
      throw _privateConstructorUsedError;
}

QuizQuestionModel _$QuizQuestionModelFromJson(Map<String, dynamic> json) {
  return _QuizQuestionModel.fromJson(json);
}

/// @nodoc
mixin _$QuizQuestionModel {
  String get id => throw _privateConstructorUsedError;
  String get type => throw _privateConstructorUsedError;
  String get question => throw _privateConstructorUsedError;
  double get points => throw _privateConstructorUsedError;
  String? get explanation => throw _privateConstructorUsedError;
  String? get imageUrl => throw _privateConstructorUsedError;
  List<String> get options => throw _privateConstructorUsedError;
  dynamic get correctAnswer => throw _privateConstructorUsedError;

  /// Serializes this QuizQuestionModel to a JSON map.
  Map<String, dynamic> toJson() => throw _privateConstructorUsedError;

  /// Create a copy of QuizQuestionModel
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  $QuizQuestionModelCopyWith<QuizQuestionModel> get copyWith =>
      throw _privateConstructorUsedError;
}

/// @nodoc
abstract class $QuizQuestionModelCopyWith<$Res> {
  factory $QuizQuestionModelCopyWith(
          QuizQuestionModel value, $Res Function(QuizQuestionModel) then) =
      _$QuizQuestionModelCopyWithImpl<$Res, QuizQuestionModel>;
  @useResult
  $Res call(
      {String id,
      String type,
      String question,
      double points,
      String? explanation,
      String? imageUrl,
      List<String> options,
      dynamic correctAnswer});
}

/// @nodoc
class _$QuizQuestionModelCopyWithImpl<$Res, $Val extends QuizQuestionModel>
    implements $QuizQuestionModelCopyWith<$Res> {
  _$QuizQuestionModelCopyWithImpl(this._value, this._then);

  // ignore: unused_field
  final $Val _value;
  // ignore: unused_field
  final $Res Function($Val) _then;

  /// Create a copy of QuizQuestionModel
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? id = null,
    Object? type = null,
    Object? question = null,
    Object? points = null,
    Object? explanation = freezed,
    Object? imageUrl = freezed,
    Object? options = null,
    Object? correctAnswer = freezed,
  }) {
    return _then(_value.copyWith(
      id: null == id
          ? _value.id
          : id // ignore: cast_nullable_to_non_nullable
              as String,
      type: null == type
          ? _value.type
          : type // ignore: cast_nullable_to_non_nullable
              as String,
      question: null == question
          ? _value.question
          : question // ignore: cast_nullable_to_non_nullable
              as String,
      points: null == points
          ? _value.points
          : points // ignore: cast_nullable_to_non_nullable
              as double,
      explanation: freezed == explanation
          ? _value.explanation
          : explanation // ignore: cast_nullable_to_non_nullable
              as String?,
      imageUrl: freezed == imageUrl
          ? _value.imageUrl
          : imageUrl // ignore: cast_nullable_to_non_nullable
              as String?,
      options: null == options
          ? _value.options
          : options // ignore: cast_nullable_to_non_nullable
              as List<String>,
      correctAnswer: freezed == correctAnswer
          ? _value.correctAnswer
          : correctAnswer // ignore: cast_nullable_to_non_nullable
              as dynamic,
    ) as $Val);
  }
}

/// @nodoc
abstract class _$$QuizQuestionModelImplCopyWith<$Res>
    implements $QuizQuestionModelCopyWith<$Res> {
  factory _$$QuizQuestionModelImplCopyWith(_$QuizQuestionModelImpl value,
          $Res Function(_$QuizQuestionModelImpl) then) =
      __$$QuizQuestionModelImplCopyWithImpl<$Res>;
  @override
  @useResult
  $Res call(
      {String id,
      String type,
      String question,
      double points,
      String? explanation,
      String? imageUrl,
      List<String> options,
      dynamic correctAnswer});
}

/// @nodoc
class __$$QuizQuestionModelImplCopyWithImpl<$Res>
    extends _$QuizQuestionModelCopyWithImpl<$Res, _$QuizQuestionModelImpl>
    implements _$$QuizQuestionModelImplCopyWith<$Res> {
  __$$QuizQuestionModelImplCopyWithImpl(_$QuizQuestionModelImpl _value,
      $Res Function(_$QuizQuestionModelImpl) _then)
      : super(_value, _then);

  /// Create a copy of QuizQuestionModel
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? id = null,
    Object? type = null,
    Object? question = null,
    Object? points = null,
    Object? explanation = freezed,
    Object? imageUrl = freezed,
    Object? options = null,
    Object? correctAnswer = freezed,
  }) {
    return _then(_$QuizQuestionModelImpl(
      id: null == id
          ? _value.id
          : id // ignore: cast_nullable_to_non_nullable
              as String,
      type: null == type
          ? _value.type
          : type // ignore: cast_nullable_to_non_nullable
              as String,
      question: null == question
          ? _value.question
          : question // ignore: cast_nullable_to_non_nullable
              as String,
      points: null == points
          ? _value.points
          : points // ignore: cast_nullable_to_non_nullable
              as double,
      explanation: freezed == explanation
          ? _value.explanation
          : explanation // ignore: cast_nullable_to_non_nullable
              as String?,
      imageUrl: freezed == imageUrl
          ? _value.imageUrl
          : imageUrl // ignore: cast_nullable_to_non_nullable
              as String?,
      options: null == options
          ? _value._options
          : options // ignore: cast_nullable_to_non_nullable
              as List<String>,
      correctAnswer: freezed == correctAnswer
          ? _value.correctAnswer
          : correctAnswer // ignore: cast_nullable_to_non_nullable
              as dynamic,
    ));
  }
}

/// @nodoc
@JsonSerializable()
class _$QuizQuestionModelImpl extends _QuizQuestionModel {
  const _$QuizQuestionModelImpl(
      {required this.id,
      required this.type,
      required this.question,
      required this.points,
      this.explanation,
      this.imageUrl,
      final List<String> options = const [],
      this.correctAnswer})
      : _options = options,
        super._();

  factory _$QuizQuestionModelImpl.fromJson(Map<String, dynamic> json) =>
      _$$QuizQuestionModelImplFromJson(json);

  @override
  final String id;
  @override
  final String type;
  @override
  final String question;
  @override
  final double points;
  @override
  final String? explanation;
  @override
  final String? imageUrl;
  final List<String> _options;
  @override
  @JsonKey()
  List<String> get options {
    if (_options is EqualUnmodifiableListView) return _options;
    // ignore: implicit_dynamic_type
    return EqualUnmodifiableListView(_options);
  }

  @override
  final dynamic correctAnswer;

  @override
  String toString() {
    return 'QuizQuestionModel(id: $id, type: $type, question: $question, points: $points, explanation: $explanation, imageUrl: $imageUrl, options: $options, correctAnswer: $correctAnswer)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$QuizQuestionModelImpl &&
            (identical(other.id, id) || other.id == id) &&
            (identical(other.type, type) || other.type == type) &&
            (identical(other.question, question) ||
                other.question == question) &&
            (identical(other.points, points) || other.points == points) &&
            (identical(other.explanation, explanation) ||
                other.explanation == explanation) &&
            (identical(other.imageUrl, imageUrl) ||
                other.imageUrl == imageUrl) &&
            const DeepCollectionEquality().equals(other._options, _options) &&
            const DeepCollectionEquality()
                .equals(other.correctAnswer, correctAnswer));
  }

  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  int get hashCode => Object.hash(
      runtimeType,
      id,
      type,
      question,
      points,
      explanation,
      imageUrl,
      const DeepCollectionEquality().hash(_options),
      const DeepCollectionEquality().hash(correctAnswer));

  /// Create a copy of QuizQuestionModel
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  @pragma('vm:prefer-inline')
  _$$QuizQuestionModelImplCopyWith<_$QuizQuestionModelImpl> get copyWith =>
      __$$QuizQuestionModelImplCopyWithImpl<_$QuizQuestionModelImpl>(
          this, _$identity);

  @override
  Map<String, dynamic> toJson() {
    return _$$QuizQuestionModelImplToJson(
      this,
    );
  }
}

abstract class _QuizQuestionModel extends QuizQuestionModel {
  const factory _QuizQuestionModel(
      {required final String id,
      required final String type,
      required final String question,
      required final double points,
      final String? explanation,
      final String? imageUrl,
      final List<String> options,
      final dynamic correctAnswer}) = _$QuizQuestionModelImpl;
  const _QuizQuestionModel._() : super._();

  factory _QuizQuestionModel.fromJson(Map<String, dynamic> json) =
      _$QuizQuestionModelImpl.fromJson;

  @override
  String get id;
  @override
  String get type;
  @override
  String get question;
  @override
  double get points;
  @override
  String? get explanation;
  @override
  String? get imageUrl;
  @override
  List<String> get options;
  @override
  dynamic get correctAnswer;

  /// Create a copy of QuizQuestionModel
  /// with the given fields replaced by the non-null parameter values.
  @override
  @JsonKey(includeFromJson: false, includeToJson: false)
  _$$QuizQuestionModelImplCopyWith<_$QuizQuestionModelImpl> get copyWith =>
      throw _privateConstructorUsedError;
}

QuizAttemptModel _$QuizAttemptModelFromJson(Map<String, dynamic> json) {
  return _QuizAttemptModel.fromJson(json);
}

/// @nodoc
mixin _$QuizAttemptModel {
  @JsonKey(name: 'attempt_id')
  int? get attemptId => throw _privateConstructorUsedError;
  @JsonKey(name: 'quiz_id')
  int? get quizId => throw _privateConstructorUsedError;
  @JsonKey(name: 'total_marks')
  double? get totalMarks => throw _privateConstructorUsedError;
  @JsonKey(name: 'earned_marks')
  double? get earnedMarks => throw _privateConstructorUsedError;
  double? get percentage => throw _privateConstructorUsedError;
  bool? get passed => throw _privateConstructorUsedError;
  @JsonKey(name: 'passing_grade')
  int? get passingGrade => throw _privateConstructorUsedError;

  /// Serializes this QuizAttemptModel to a JSON map.
  Map<String, dynamic> toJson() => throw _privateConstructorUsedError;

  /// Create a copy of QuizAttemptModel
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  $QuizAttemptModelCopyWith<QuizAttemptModel> get copyWith =>
      throw _privateConstructorUsedError;
}

/// @nodoc
abstract class $QuizAttemptModelCopyWith<$Res> {
  factory $QuizAttemptModelCopyWith(
          QuizAttemptModel value, $Res Function(QuizAttemptModel) then) =
      _$QuizAttemptModelCopyWithImpl<$Res, QuizAttemptModel>;
  @useResult
  $Res call(
      {@JsonKey(name: 'attempt_id') int? attemptId,
      @JsonKey(name: 'quiz_id') int? quizId,
      @JsonKey(name: 'total_marks') double? totalMarks,
      @JsonKey(name: 'earned_marks') double? earnedMarks,
      double? percentage,
      bool? passed,
      @JsonKey(name: 'passing_grade') int? passingGrade});
}

/// @nodoc
class _$QuizAttemptModelCopyWithImpl<$Res, $Val extends QuizAttemptModel>
    implements $QuizAttemptModelCopyWith<$Res> {
  _$QuizAttemptModelCopyWithImpl(this._value, this._then);

  // ignore: unused_field
  final $Val _value;
  // ignore: unused_field
  final $Res Function($Val) _then;

  /// Create a copy of QuizAttemptModel
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? attemptId = freezed,
    Object? quizId = freezed,
    Object? totalMarks = freezed,
    Object? earnedMarks = freezed,
    Object? percentage = freezed,
    Object? passed = freezed,
    Object? passingGrade = freezed,
  }) {
    return _then(_value.copyWith(
      attemptId: freezed == attemptId
          ? _value.attemptId
          : attemptId // ignore: cast_nullable_to_non_nullable
              as int?,
      quizId: freezed == quizId
          ? _value.quizId
          : quizId // ignore: cast_nullable_to_non_nullable
              as int?,
      totalMarks: freezed == totalMarks
          ? _value.totalMarks
          : totalMarks // ignore: cast_nullable_to_non_nullable
              as double?,
      earnedMarks: freezed == earnedMarks
          ? _value.earnedMarks
          : earnedMarks // ignore: cast_nullable_to_non_nullable
              as double?,
      percentage: freezed == percentage
          ? _value.percentage
          : percentage // ignore: cast_nullable_to_non_nullable
              as double?,
      passed: freezed == passed
          ? _value.passed
          : passed // ignore: cast_nullable_to_non_nullable
              as bool?,
      passingGrade: freezed == passingGrade
          ? _value.passingGrade
          : passingGrade // ignore: cast_nullable_to_non_nullable
              as int?,
    ) as $Val);
  }
}

/// @nodoc
abstract class _$$QuizAttemptModelImplCopyWith<$Res>
    implements $QuizAttemptModelCopyWith<$Res> {
  factory _$$QuizAttemptModelImplCopyWith(_$QuizAttemptModelImpl value,
          $Res Function(_$QuizAttemptModelImpl) then) =
      __$$QuizAttemptModelImplCopyWithImpl<$Res>;
  @override
  @useResult
  $Res call(
      {@JsonKey(name: 'attempt_id') int? attemptId,
      @JsonKey(name: 'quiz_id') int? quizId,
      @JsonKey(name: 'total_marks') double? totalMarks,
      @JsonKey(name: 'earned_marks') double? earnedMarks,
      double? percentage,
      bool? passed,
      @JsonKey(name: 'passing_grade') int? passingGrade});
}

/// @nodoc
class __$$QuizAttemptModelImplCopyWithImpl<$Res>
    extends _$QuizAttemptModelCopyWithImpl<$Res, _$QuizAttemptModelImpl>
    implements _$$QuizAttemptModelImplCopyWith<$Res> {
  __$$QuizAttemptModelImplCopyWithImpl(_$QuizAttemptModelImpl _value,
      $Res Function(_$QuizAttemptModelImpl) _then)
      : super(_value, _then);

  /// Create a copy of QuizAttemptModel
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? attemptId = freezed,
    Object? quizId = freezed,
    Object? totalMarks = freezed,
    Object? earnedMarks = freezed,
    Object? percentage = freezed,
    Object? passed = freezed,
    Object? passingGrade = freezed,
  }) {
    return _then(_$QuizAttemptModelImpl(
      attemptId: freezed == attemptId
          ? _value.attemptId
          : attemptId // ignore: cast_nullable_to_non_nullable
              as int?,
      quizId: freezed == quizId
          ? _value.quizId
          : quizId // ignore: cast_nullable_to_non_nullable
              as int?,
      totalMarks: freezed == totalMarks
          ? _value.totalMarks
          : totalMarks // ignore: cast_nullable_to_non_nullable
              as double?,
      earnedMarks: freezed == earnedMarks
          ? _value.earnedMarks
          : earnedMarks // ignore: cast_nullable_to_non_nullable
              as double?,
      percentage: freezed == percentage
          ? _value.percentage
          : percentage // ignore: cast_nullable_to_non_nullable
              as double?,
      passed: freezed == passed
          ? _value.passed
          : passed // ignore: cast_nullable_to_non_nullable
              as bool?,
      passingGrade: freezed == passingGrade
          ? _value.passingGrade
          : passingGrade // ignore: cast_nullable_to_non_nullable
              as int?,
    ));
  }
}

/// @nodoc
@JsonSerializable()
class _$QuizAttemptModelImpl implements _QuizAttemptModel {
  const _$QuizAttemptModelImpl(
      {@JsonKey(name: 'attempt_id') this.attemptId,
      @JsonKey(name: 'quiz_id') this.quizId,
      @JsonKey(name: 'total_marks') this.totalMarks,
      @JsonKey(name: 'earned_marks') this.earnedMarks,
      this.percentage,
      this.passed,
      @JsonKey(name: 'passing_grade') this.passingGrade});

  factory _$QuizAttemptModelImpl.fromJson(Map<String, dynamic> json) =>
      _$$QuizAttemptModelImplFromJson(json);

  @override
  @JsonKey(name: 'attempt_id')
  final int? attemptId;
  @override
  @JsonKey(name: 'quiz_id')
  final int? quizId;
  @override
  @JsonKey(name: 'total_marks')
  final double? totalMarks;
  @override
  @JsonKey(name: 'earned_marks')
  final double? earnedMarks;
  @override
  final double? percentage;
  @override
  final bool? passed;
  @override
  @JsonKey(name: 'passing_grade')
  final int? passingGrade;

  @override
  String toString() {
    return 'QuizAttemptModel(attemptId: $attemptId, quizId: $quizId, totalMarks: $totalMarks, earnedMarks: $earnedMarks, percentage: $percentage, passed: $passed, passingGrade: $passingGrade)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$QuizAttemptModelImpl &&
            (identical(other.attemptId, attemptId) ||
                other.attemptId == attemptId) &&
            (identical(other.quizId, quizId) || other.quizId == quizId) &&
            (identical(other.totalMarks, totalMarks) ||
                other.totalMarks == totalMarks) &&
            (identical(other.earnedMarks, earnedMarks) ||
                other.earnedMarks == earnedMarks) &&
            (identical(other.percentage, percentage) ||
                other.percentage == percentage) &&
            (identical(other.passed, passed) || other.passed == passed) &&
            (identical(other.passingGrade, passingGrade) ||
                other.passingGrade == passingGrade));
  }

  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  int get hashCode => Object.hash(runtimeType, attemptId, quizId, totalMarks,
      earnedMarks, percentage, passed, passingGrade);

  /// Create a copy of QuizAttemptModel
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  @pragma('vm:prefer-inline')
  _$$QuizAttemptModelImplCopyWith<_$QuizAttemptModelImpl> get copyWith =>
      __$$QuizAttemptModelImplCopyWithImpl<_$QuizAttemptModelImpl>(
          this, _$identity);

  @override
  Map<String, dynamic> toJson() {
    return _$$QuizAttemptModelImplToJson(
      this,
    );
  }
}

abstract class _QuizAttemptModel implements QuizAttemptModel {
  const factory _QuizAttemptModel(
          {@JsonKey(name: 'attempt_id') final int? attemptId,
          @JsonKey(name: 'quiz_id') final int? quizId,
          @JsonKey(name: 'total_marks') final double? totalMarks,
          @JsonKey(name: 'earned_marks') final double? earnedMarks,
          final double? percentage,
          final bool? passed,
          @JsonKey(name: 'passing_grade') final int? passingGrade}) =
      _$QuizAttemptModelImpl;

  factory _QuizAttemptModel.fromJson(Map<String, dynamic> json) =
      _$QuizAttemptModelImpl.fromJson;

  @override
  @JsonKey(name: 'attempt_id')
  int? get attemptId;
  @override
  @JsonKey(name: 'quiz_id')
  int? get quizId;
  @override
  @JsonKey(name: 'total_marks')
  double? get totalMarks;
  @override
  @JsonKey(name: 'earned_marks')
  double? get earnedMarks;
  @override
  double? get percentage;
  @override
  bool? get passed;
  @override
  @JsonKey(name: 'passing_grade')
  int? get passingGrade;

  /// Create a copy of QuizAttemptModel
  /// with the given fields replaced by the non-null parameter values.
  @override
  @JsonKey(includeFromJson: false, includeToJson: false)
  _$$QuizAttemptModelImplCopyWith<_$QuizAttemptModelImpl> get copyWith =>
      throw _privateConstructorUsedError;
}
