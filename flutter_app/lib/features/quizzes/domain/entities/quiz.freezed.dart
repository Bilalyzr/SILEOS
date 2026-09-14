// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint
// ignore_for_file: unused_element, deprecated_member_use, deprecated_member_use_from_same_package, use_function_type_syntax_for_parameters, unnecessary_const, avoid_init_to_null, invalid_override_different_default_values_named, prefer_expression_function_bodies, annotate_overrides, invalid_annotation_target, unnecessary_question_mark

part of 'quiz.dart';

// **************************************************************************
// FreezedGenerator
// **************************************************************************

T _$identity<T>(T value) => value;

final _privateConstructorUsedError = UnsupportedError(
    'It seems like you constructed your class using `MyClass._()`. This constructor is only meant to be used by freezed and you are not supposed to need it nor use it.\nPlease check the documentation here for more information: https://github.com/rrousselGit/freezed#adding-getters-and-methods-to-our-models');

/// @nodoc
mixin _$Quiz {
  String get id => throw _privateConstructorUsedError;
  String get title => throw _privateConstructorUsedError;
  String? get description => throw _privateConstructorUsedError;
  int get timeLimit => throw _privateConstructorUsedError;
  int get passingGrade => throw _privateConstructorUsedError;
  int get maxAttempts => throw _privateConstructorUsedError;
  List<QuizQuestion> get questions => throw _privateConstructorUsedError;

  /// Create a copy of Quiz
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  $QuizCopyWith<Quiz> get copyWith => throw _privateConstructorUsedError;
}

/// @nodoc
abstract class $QuizCopyWith<$Res> {
  factory $QuizCopyWith(Quiz value, $Res Function(Quiz) then) =
      _$QuizCopyWithImpl<$Res, Quiz>;
  @useResult
  $Res call(
      {String id,
      String title,
      String? description,
      int timeLimit,
      int passingGrade,
      int maxAttempts,
      List<QuizQuestion> questions});
}

/// @nodoc
class _$QuizCopyWithImpl<$Res, $Val extends Quiz>
    implements $QuizCopyWith<$Res> {
  _$QuizCopyWithImpl(this._value, this._then);

  // ignore: unused_field
  final $Val _value;
  // ignore: unused_field
  final $Res Function($Val) _then;

  /// Create a copy of Quiz
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? id = null,
    Object? title = null,
    Object? description = freezed,
    Object? timeLimit = null,
    Object? passingGrade = null,
    Object? maxAttempts = null,
    Object? questions = null,
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
      timeLimit: null == timeLimit
          ? _value.timeLimit
          : timeLimit // ignore: cast_nullable_to_non_nullable
              as int,
      passingGrade: null == passingGrade
          ? _value.passingGrade
          : passingGrade // ignore: cast_nullable_to_non_nullable
              as int,
      maxAttempts: null == maxAttempts
          ? _value.maxAttempts
          : maxAttempts // ignore: cast_nullable_to_non_nullable
              as int,
      questions: null == questions
          ? _value.questions
          : questions // ignore: cast_nullable_to_non_nullable
              as List<QuizQuestion>,
    ) as $Val);
  }
}

/// @nodoc
abstract class _$$QuizImplCopyWith<$Res> implements $QuizCopyWith<$Res> {
  factory _$$QuizImplCopyWith(
          _$QuizImpl value, $Res Function(_$QuizImpl) then) =
      __$$QuizImplCopyWithImpl<$Res>;
  @override
  @useResult
  $Res call(
      {String id,
      String title,
      String? description,
      int timeLimit,
      int passingGrade,
      int maxAttempts,
      List<QuizQuestion> questions});
}

/// @nodoc
class __$$QuizImplCopyWithImpl<$Res>
    extends _$QuizCopyWithImpl<$Res, _$QuizImpl>
    implements _$$QuizImplCopyWith<$Res> {
  __$$QuizImplCopyWithImpl(_$QuizImpl _value, $Res Function(_$QuizImpl) _then)
      : super(_value, _then);

  /// Create a copy of Quiz
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? id = null,
    Object? title = null,
    Object? description = freezed,
    Object? timeLimit = null,
    Object? passingGrade = null,
    Object? maxAttempts = null,
    Object? questions = null,
  }) {
    return _then(_$QuizImpl(
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
      timeLimit: null == timeLimit
          ? _value.timeLimit
          : timeLimit // ignore: cast_nullable_to_non_nullable
              as int,
      passingGrade: null == passingGrade
          ? _value.passingGrade
          : passingGrade // ignore: cast_nullable_to_non_nullable
              as int,
      maxAttempts: null == maxAttempts
          ? _value.maxAttempts
          : maxAttempts // ignore: cast_nullable_to_non_nullable
              as int,
      questions: null == questions
          ? _value._questions
          : questions // ignore: cast_nullable_to_non_nullable
              as List<QuizQuestion>,
    ));
  }
}

/// @nodoc

class _$QuizImpl implements _Quiz {
  const _$QuizImpl(
      {required this.id,
      required this.title,
      this.description,
      required this.timeLimit,
      required this.passingGrade,
      required this.maxAttempts,
      required final List<QuizQuestion> questions})
      : _questions = questions;

  @override
  final String id;
  @override
  final String title;
  @override
  final String? description;
  @override
  final int timeLimit;
  @override
  final int passingGrade;
  @override
  final int maxAttempts;
  final List<QuizQuestion> _questions;
  @override
  List<QuizQuestion> get questions {
    if (_questions is EqualUnmodifiableListView) return _questions;
    // ignore: implicit_dynamic_type
    return EqualUnmodifiableListView(_questions);
  }

  @override
  String toString() {
    return 'Quiz(id: $id, title: $title, description: $description, timeLimit: $timeLimit, passingGrade: $passingGrade, maxAttempts: $maxAttempts, questions: $questions)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$QuizImpl &&
            (identical(other.id, id) || other.id == id) &&
            (identical(other.title, title) || other.title == title) &&
            (identical(other.description, description) ||
                other.description == description) &&
            (identical(other.timeLimit, timeLimit) ||
                other.timeLimit == timeLimit) &&
            (identical(other.passingGrade, passingGrade) ||
                other.passingGrade == passingGrade) &&
            (identical(other.maxAttempts, maxAttempts) ||
                other.maxAttempts == maxAttempts) &&
            const DeepCollectionEquality()
                .equals(other._questions, _questions));
  }

  @override
  int get hashCode => Object.hash(
      runtimeType,
      id,
      title,
      description,
      timeLimit,
      passingGrade,
      maxAttempts,
      const DeepCollectionEquality().hash(_questions));

  /// Create a copy of Quiz
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  @pragma('vm:prefer-inline')
  _$$QuizImplCopyWith<_$QuizImpl> get copyWith =>
      __$$QuizImplCopyWithImpl<_$QuizImpl>(this, _$identity);
}

abstract class _Quiz implements Quiz {
  const factory _Quiz(
      {required final String id,
      required final String title,
      final String? description,
      required final int timeLimit,
      required final int passingGrade,
      required final int maxAttempts,
      required final List<QuizQuestion> questions}) = _$QuizImpl;

  @override
  String get id;
  @override
  String get title;
  @override
  String? get description;
  @override
  int get timeLimit;
  @override
  int get passingGrade;
  @override
  int get maxAttempts;
  @override
  List<QuizQuestion> get questions;

  /// Create a copy of Quiz
  /// with the given fields replaced by the non-null parameter values.
  @override
  @JsonKey(includeFromJson: false, includeToJson: false)
  _$$QuizImplCopyWith<_$QuizImpl> get copyWith =>
      throw _privateConstructorUsedError;
}

/// @nodoc
mixin _$QuizQuestion {
  String get id => throw _privateConstructorUsedError;
  String get title => throw _privateConstructorUsedError;
  String? get description => throw _privateConstructorUsedError;
  String get type => throw _privateConstructorUsedError;
  double get points => throw _privateConstructorUsedError;
  List<QuizAnswerOption> get options => throw _privateConstructorUsedError;

  /// Create a copy of QuizQuestion
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  $QuizQuestionCopyWith<QuizQuestion> get copyWith =>
      throw _privateConstructorUsedError;
}

/// @nodoc
abstract class $QuizQuestionCopyWith<$Res> {
  factory $QuizQuestionCopyWith(
          QuizQuestion value, $Res Function(QuizQuestion) then) =
      _$QuizQuestionCopyWithImpl<$Res, QuizQuestion>;
  @useResult
  $Res call(
      {String id,
      String title,
      String? description,
      String type,
      double points,
      List<QuizAnswerOption> options});
}

/// @nodoc
class _$QuizQuestionCopyWithImpl<$Res, $Val extends QuizQuestion>
    implements $QuizQuestionCopyWith<$Res> {
  _$QuizQuestionCopyWithImpl(this._value, this._then);

  // ignore: unused_field
  final $Val _value;
  // ignore: unused_field
  final $Res Function($Val) _then;

  /// Create a copy of QuizQuestion
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? id = null,
    Object? title = null,
    Object? description = freezed,
    Object? type = null,
    Object? points = null,
    Object? options = null,
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
      type: null == type
          ? _value.type
          : type // ignore: cast_nullable_to_non_nullable
              as String,
      points: null == points
          ? _value.points
          : points // ignore: cast_nullable_to_non_nullable
              as double,
      options: null == options
          ? _value.options
          : options // ignore: cast_nullable_to_non_nullable
              as List<QuizAnswerOption>,
    ) as $Val);
  }
}

/// @nodoc
abstract class _$$QuizQuestionImplCopyWith<$Res>
    implements $QuizQuestionCopyWith<$Res> {
  factory _$$QuizQuestionImplCopyWith(
          _$QuizQuestionImpl value, $Res Function(_$QuizQuestionImpl) then) =
      __$$QuizQuestionImplCopyWithImpl<$Res>;
  @override
  @useResult
  $Res call(
      {String id,
      String title,
      String? description,
      String type,
      double points,
      List<QuizAnswerOption> options});
}

/// @nodoc
class __$$QuizQuestionImplCopyWithImpl<$Res>
    extends _$QuizQuestionCopyWithImpl<$Res, _$QuizQuestionImpl>
    implements _$$QuizQuestionImplCopyWith<$Res> {
  __$$QuizQuestionImplCopyWithImpl(
      _$QuizQuestionImpl _value, $Res Function(_$QuizQuestionImpl) _then)
      : super(_value, _then);

  /// Create a copy of QuizQuestion
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? id = null,
    Object? title = null,
    Object? description = freezed,
    Object? type = null,
    Object? points = null,
    Object? options = null,
  }) {
    return _then(_$QuizQuestionImpl(
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
      type: null == type
          ? _value.type
          : type // ignore: cast_nullable_to_non_nullable
              as String,
      points: null == points
          ? _value.points
          : points // ignore: cast_nullable_to_non_nullable
              as double,
      options: null == options
          ? _value._options
          : options // ignore: cast_nullable_to_non_nullable
              as List<QuizAnswerOption>,
    ));
  }
}

/// @nodoc

class _$QuizQuestionImpl implements _QuizQuestion {
  const _$QuizQuestionImpl(
      {required this.id,
      required this.title,
      this.description,
      required this.type,
      required this.points,
      required final List<QuizAnswerOption> options})
      : _options = options;

  @override
  final String id;
  @override
  final String title;
  @override
  final String? description;
  @override
  final String type;
  @override
  final double points;
  final List<QuizAnswerOption> _options;
  @override
  List<QuizAnswerOption> get options {
    if (_options is EqualUnmodifiableListView) return _options;
    // ignore: implicit_dynamic_type
    return EqualUnmodifiableListView(_options);
  }

  @override
  String toString() {
    return 'QuizQuestion(id: $id, title: $title, description: $description, type: $type, points: $points, options: $options)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$QuizQuestionImpl &&
            (identical(other.id, id) || other.id == id) &&
            (identical(other.title, title) || other.title == title) &&
            (identical(other.description, description) ||
                other.description == description) &&
            (identical(other.type, type) || other.type == type) &&
            (identical(other.points, points) || other.points == points) &&
            const DeepCollectionEquality().equals(other._options, _options));
  }

  @override
  int get hashCode => Object.hash(runtimeType, id, title, description, type,
      points, const DeepCollectionEquality().hash(_options));

  /// Create a copy of QuizQuestion
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  @pragma('vm:prefer-inline')
  _$$QuizQuestionImplCopyWith<_$QuizQuestionImpl> get copyWith =>
      __$$QuizQuestionImplCopyWithImpl<_$QuizQuestionImpl>(this, _$identity);
}

abstract class _QuizQuestion implements QuizQuestion {
  const factory _QuizQuestion(
      {required final String id,
      required final String title,
      final String? description,
      required final String type,
      required final double points,
      required final List<QuizAnswerOption> options}) = _$QuizQuestionImpl;

  @override
  String get id;
  @override
  String get title;
  @override
  String? get description;
  @override
  String get type;
  @override
  double get points;
  @override
  List<QuizAnswerOption> get options;

  /// Create a copy of QuizQuestion
  /// with the given fields replaced by the non-null parameter values.
  @override
  @JsonKey(includeFromJson: false, includeToJson: false)
  _$$QuizQuestionImplCopyWith<_$QuizQuestionImpl> get copyWith =>
      throw _privateConstructorUsedError;
}

/// @nodoc
mixin _$QuizAnswerOption {
  String get id => throw _privateConstructorUsedError;
  String get title => throw _privateConstructorUsedError;
  bool get isCorrect => throw _privateConstructorUsedError;

  /// Create a copy of QuizAnswerOption
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  $QuizAnswerOptionCopyWith<QuizAnswerOption> get copyWith =>
      throw _privateConstructorUsedError;
}

/// @nodoc
abstract class $QuizAnswerOptionCopyWith<$Res> {
  factory $QuizAnswerOptionCopyWith(
          QuizAnswerOption value, $Res Function(QuizAnswerOption) then) =
      _$QuizAnswerOptionCopyWithImpl<$Res, QuizAnswerOption>;
  @useResult
  $Res call({String id, String title, bool isCorrect});
}

/// @nodoc
class _$QuizAnswerOptionCopyWithImpl<$Res, $Val extends QuizAnswerOption>
    implements $QuizAnswerOptionCopyWith<$Res> {
  _$QuizAnswerOptionCopyWithImpl(this._value, this._then);

  // ignore: unused_field
  final $Val _value;
  // ignore: unused_field
  final $Res Function($Val) _then;

  /// Create a copy of QuizAnswerOption
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? id = null,
    Object? title = null,
    Object? isCorrect = null,
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
      isCorrect: null == isCorrect
          ? _value.isCorrect
          : isCorrect // ignore: cast_nullable_to_non_nullable
              as bool,
    ) as $Val);
  }
}

/// @nodoc
abstract class _$$QuizAnswerOptionImplCopyWith<$Res>
    implements $QuizAnswerOptionCopyWith<$Res> {
  factory _$$QuizAnswerOptionImplCopyWith(_$QuizAnswerOptionImpl value,
          $Res Function(_$QuizAnswerOptionImpl) then) =
      __$$QuizAnswerOptionImplCopyWithImpl<$Res>;
  @override
  @useResult
  $Res call({String id, String title, bool isCorrect});
}

/// @nodoc
class __$$QuizAnswerOptionImplCopyWithImpl<$Res>
    extends _$QuizAnswerOptionCopyWithImpl<$Res, _$QuizAnswerOptionImpl>
    implements _$$QuizAnswerOptionImplCopyWith<$Res> {
  __$$QuizAnswerOptionImplCopyWithImpl(_$QuizAnswerOptionImpl _value,
      $Res Function(_$QuizAnswerOptionImpl) _then)
      : super(_value, _then);

  /// Create a copy of QuizAnswerOption
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? id = null,
    Object? title = null,
    Object? isCorrect = null,
  }) {
    return _then(_$QuizAnswerOptionImpl(
      id: null == id
          ? _value.id
          : id // ignore: cast_nullable_to_non_nullable
              as String,
      title: null == title
          ? _value.title
          : title // ignore: cast_nullable_to_non_nullable
              as String,
      isCorrect: null == isCorrect
          ? _value.isCorrect
          : isCorrect // ignore: cast_nullable_to_non_nullable
              as bool,
    ));
  }
}

/// @nodoc

class _$QuizAnswerOptionImpl implements _QuizAnswerOption {
  const _$QuizAnswerOptionImpl(
      {required this.id, required this.title, this.isCorrect = false});

  @override
  final String id;
  @override
  final String title;
  @override
  @JsonKey()
  final bool isCorrect;

  @override
  String toString() {
    return 'QuizAnswerOption(id: $id, title: $title, isCorrect: $isCorrect)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$QuizAnswerOptionImpl &&
            (identical(other.id, id) || other.id == id) &&
            (identical(other.title, title) || other.title == title) &&
            (identical(other.isCorrect, isCorrect) ||
                other.isCorrect == isCorrect));
  }

  @override
  int get hashCode => Object.hash(runtimeType, id, title, isCorrect);

  /// Create a copy of QuizAnswerOption
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  @pragma('vm:prefer-inline')
  _$$QuizAnswerOptionImplCopyWith<_$QuizAnswerOptionImpl> get copyWith =>
      __$$QuizAnswerOptionImplCopyWithImpl<_$QuizAnswerOptionImpl>(
          this, _$identity);
}

abstract class _QuizAnswerOption implements QuizAnswerOption {
  const factory _QuizAnswerOption(
      {required final String id,
      required final String title,
      final bool isCorrect}) = _$QuizAnswerOptionImpl;

  @override
  String get id;
  @override
  String get title;
  @override
  bool get isCorrect;

  /// Create a copy of QuizAnswerOption
  /// with the given fields replaced by the non-null parameter values.
  @override
  @JsonKey(includeFromJson: false, includeToJson: false)
  _$$QuizAnswerOptionImplCopyWith<_$QuizAnswerOptionImpl> get copyWith =>
      throw _privateConstructorUsedError;
}

/// @nodoc
mixin _$QuizAttempt {
  String get id => throw _privateConstructorUsedError;
  String get quizId => throw _privateConstructorUsedError;
  String get userId => throw _privateConstructorUsedError;
  String get status => throw _privateConstructorUsedError;
  int get totalQuestions => throw _privateConstructorUsedError;
  int get answeredQuestions => throw _privateConstructorUsedError;
  double get totalMarks => throw _privateConstructorUsedError;
  double get earnedMarks => throw _privateConstructorUsedError;
  DateTime? get startedAt => throw _privateConstructorUsedError;
  DateTime? get endedAt => throw _privateConstructorUsedError;

  /// Create a copy of QuizAttempt
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  $QuizAttemptCopyWith<QuizAttempt> get copyWith =>
      throw _privateConstructorUsedError;
}

/// @nodoc
abstract class $QuizAttemptCopyWith<$Res> {
  factory $QuizAttemptCopyWith(
          QuizAttempt value, $Res Function(QuizAttempt) then) =
      _$QuizAttemptCopyWithImpl<$Res, QuizAttempt>;
  @useResult
  $Res call(
      {String id,
      String quizId,
      String userId,
      String status,
      int totalQuestions,
      int answeredQuestions,
      double totalMarks,
      double earnedMarks,
      DateTime? startedAt,
      DateTime? endedAt});
}

/// @nodoc
class _$QuizAttemptCopyWithImpl<$Res, $Val extends QuizAttempt>
    implements $QuizAttemptCopyWith<$Res> {
  _$QuizAttemptCopyWithImpl(this._value, this._then);

  // ignore: unused_field
  final $Val _value;
  // ignore: unused_field
  final $Res Function($Val) _then;

  /// Create a copy of QuizAttempt
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? id = null,
    Object? quizId = null,
    Object? userId = null,
    Object? status = null,
    Object? totalQuestions = null,
    Object? answeredQuestions = null,
    Object? totalMarks = null,
    Object? earnedMarks = null,
    Object? startedAt = freezed,
    Object? endedAt = freezed,
  }) {
    return _then(_value.copyWith(
      id: null == id
          ? _value.id
          : id // ignore: cast_nullable_to_non_nullable
              as String,
      quizId: null == quizId
          ? _value.quizId
          : quizId // ignore: cast_nullable_to_non_nullable
              as String,
      userId: null == userId
          ? _value.userId
          : userId // ignore: cast_nullable_to_non_nullable
              as String,
      status: null == status
          ? _value.status
          : status // ignore: cast_nullable_to_non_nullable
              as String,
      totalQuestions: null == totalQuestions
          ? _value.totalQuestions
          : totalQuestions // ignore: cast_nullable_to_non_nullable
              as int,
      answeredQuestions: null == answeredQuestions
          ? _value.answeredQuestions
          : answeredQuestions // ignore: cast_nullable_to_non_nullable
              as int,
      totalMarks: null == totalMarks
          ? _value.totalMarks
          : totalMarks // ignore: cast_nullable_to_non_nullable
              as double,
      earnedMarks: null == earnedMarks
          ? _value.earnedMarks
          : earnedMarks // ignore: cast_nullable_to_non_nullable
              as double,
      startedAt: freezed == startedAt
          ? _value.startedAt
          : startedAt // ignore: cast_nullable_to_non_nullable
              as DateTime?,
      endedAt: freezed == endedAt
          ? _value.endedAt
          : endedAt // ignore: cast_nullable_to_non_nullable
              as DateTime?,
    ) as $Val);
  }
}

/// @nodoc
abstract class _$$QuizAttemptImplCopyWith<$Res>
    implements $QuizAttemptCopyWith<$Res> {
  factory _$$QuizAttemptImplCopyWith(
          _$QuizAttemptImpl value, $Res Function(_$QuizAttemptImpl) then) =
      __$$QuizAttemptImplCopyWithImpl<$Res>;
  @override
  @useResult
  $Res call(
      {String id,
      String quizId,
      String userId,
      String status,
      int totalQuestions,
      int answeredQuestions,
      double totalMarks,
      double earnedMarks,
      DateTime? startedAt,
      DateTime? endedAt});
}

/// @nodoc
class __$$QuizAttemptImplCopyWithImpl<$Res>
    extends _$QuizAttemptCopyWithImpl<$Res, _$QuizAttemptImpl>
    implements _$$QuizAttemptImplCopyWith<$Res> {
  __$$QuizAttemptImplCopyWithImpl(
      _$QuizAttemptImpl _value, $Res Function(_$QuizAttemptImpl) _then)
      : super(_value, _then);

  /// Create a copy of QuizAttempt
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? id = null,
    Object? quizId = null,
    Object? userId = null,
    Object? status = null,
    Object? totalQuestions = null,
    Object? answeredQuestions = null,
    Object? totalMarks = null,
    Object? earnedMarks = null,
    Object? startedAt = freezed,
    Object? endedAt = freezed,
  }) {
    return _then(_$QuizAttemptImpl(
      id: null == id
          ? _value.id
          : id // ignore: cast_nullable_to_non_nullable
              as String,
      quizId: null == quizId
          ? _value.quizId
          : quizId // ignore: cast_nullable_to_non_nullable
              as String,
      userId: null == userId
          ? _value.userId
          : userId // ignore: cast_nullable_to_non_nullable
              as String,
      status: null == status
          ? _value.status
          : status // ignore: cast_nullable_to_non_nullable
              as String,
      totalQuestions: null == totalQuestions
          ? _value.totalQuestions
          : totalQuestions // ignore: cast_nullable_to_non_nullable
              as int,
      answeredQuestions: null == answeredQuestions
          ? _value.answeredQuestions
          : answeredQuestions // ignore: cast_nullable_to_non_nullable
              as int,
      totalMarks: null == totalMarks
          ? _value.totalMarks
          : totalMarks // ignore: cast_nullable_to_non_nullable
              as double,
      earnedMarks: null == earnedMarks
          ? _value.earnedMarks
          : earnedMarks // ignore: cast_nullable_to_non_nullable
              as double,
      startedAt: freezed == startedAt
          ? _value.startedAt
          : startedAt // ignore: cast_nullable_to_non_nullable
              as DateTime?,
      endedAt: freezed == endedAt
          ? _value.endedAt
          : endedAt // ignore: cast_nullable_to_non_nullable
              as DateTime?,
    ));
  }
}

/// @nodoc

class _$QuizAttemptImpl implements _QuizAttempt {
  const _$QuizAttemptImpl(
      {required this.id,
      required this.quizId,
      required this.userId,
      required this.status,
      required this.totalQuestions,
      required this.answeredQuestions,
      required this.totalMarks,
      required this.earnedMarks,
      this.startedAt,
      this.endedAt});

  @override
  final String id;
  @override
  final String quizId;
  @override
  final String userId;
  @override
  final String status;
  @override
  final int totalQuestions;
  @override
  final int answeredQuestions;
  @override
  final double totalMarks;
  @override
  final double earnedMarks;
  @override
  final DateTime? startedAt;
  @override
  final DateTime? endedAt;

  @override
  String toString() {
    return 'QuizAttempt(id: $id, quizId: $quizId, userId: $userId, status: $status, totalQuestions: $totalQuestions, answeredQuestions: $answeredQuestions, totalMarks: $totalMarks, earnedMarks: $earnedMarks, startedAt: $startedAt, endedAt: $endedAt)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$QuizAttemptImpl &&
            (identical(other.id, id) || other.id == id) &&
            (identical(other.quizId, quizId) || other.quizId == quizId) &&
            (identical(other.userId, userId) || other.userId == userId) &&
            (identical(other.status, status) || other.status == status) &&
            (identical(other.totalQuestions, totalQuestions) ||
                other.totalQuestions == totalQuestions) &&
            (identical(other.answeredQuestions, answeredQuestions) ||
                other.answeredQuestions == answeredQuestions) &&
            (identical(other.totalMarks, totalMarks) ||
                other.totalMarks == totalMarks) &&
            (identical(other.earnedMarks, earnedMarks) ||
                other.earnedMarks == earnedMarks) &&
            (identical(other.startedAt, startedAt) ||
                other.startedAt == startedAt) &&
            (identical(other.endedAt, endedAt) || other.endedAt == endedAt));
  }

  @override
  int get hashCode => Object.hash(
      runtimeType,
      id,
      quizId,
      userId,
      status,
      totalQuestions,
      answeredQuestions,
      totalMarks,
      earnedMarks,
      startedAt,
      endedAt);

  /// Create a copy of QuizAttempt
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  @pragma('vm:prefer-inline')
  _$$QuizAttemptImplCopyWith<_$QuizAttemptImpl> get copyWith =>
      __$$QuizAttemptImplCopyWithImpl<_$QuizAttemptImpl>(this, _$identity);
}

abstract class _QuizAttempt implements QuizAttempt {
  const factory _QuizAttempt(
      {required final String id,
      required final String quizId,
      required final String userId,
      required final String status,
      required final int totalQuestions,
      required final int answeredQuestions,
      required final double totalMarks,
      required final double earnedMarks,
      final DateTime? startedAt,
      final DateTime? endedAt}) = _$QuizAttemptImpl;

  @override
  String get id;
  @override
  String get quizId;
  @override
  String get userId;
  @override
  String get status;
  @override
  int get totalQuestions;
  @override
  int get answeredQuestions;
  @override
  double get totalMarks;
  @override
  double get earnedMarks;
  @override
  DateTime? get startedAt;
  @override
  DateTime? get endedAt;

  /// Create a copy of QuizAttempt
  /// with the given fields replaced by the non-null parameter values.
  @override
  @JsonKey(includeFromJson: false, includeToJson: false)
  _$$QuizAttemptImplCopyWith<_$QuizAttemptImpl> get copyWith =>
      throw _privateConstructorUsedError;
}
