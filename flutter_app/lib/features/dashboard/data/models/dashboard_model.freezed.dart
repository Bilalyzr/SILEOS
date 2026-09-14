// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint
// ignore_for_file: unused_element, deprecated_member_use, deprecated_member_use_from_same_package, use_function_type_syntax_for_parameters, unnecessary_const, avoid_init_to_null, invalid_override_different_default_values_named, prefer_expression_function_bodies, annotate_overrides, invalid_annotation_target, unnecessary_question_mark

part of 'dashboard_model.dart';

// **************************************************************************
// FreezedGenerator
// **************************************************************************

T _$identity<T>(T value) => value;

final _privateConstructorUsedError = UnsupportedError(
    'It seems like you constructed your class using `MyClass._()`. This constructor is only meant to be used by freezed and you are not supposed to need it nor use it.\nPlease check the documentation here for more information: https://github.com/rrousselGit/freezed#adding-getters-and-methods-to-our-models');

DashboardModel _$DashboardModelFromJson(Map<String, dynamic> json) {
  return _DashboardModel.fromJson(json);
}

/// @nodoc
mixin _$DashboardModel {
  DashboardStatsModel get stats => throw _privateConstructorUsedError;
  @JsonKey(name: 'enrolled_courses')
  List<DashboardCourseModel> get enrolledCourses =>
      throw _privateConstructorUsedError;
  @JsonKey(name: 'recent_activity')
  List<RecentActivityModel> get recentActivity =>
      throw _privateConstructorUsedError;
  List<StudentInternshipModel> get internships =>
      throw _privateConstructorUsedError;
  @JsonKey(name: 'weekly_goal')
  WeeklyGoalModel? get weeklyGoal => throw _privateConstructorUsedError;

  /// Serializes this DashboardModel to a JSON map.
  Map<String, dynamic> toJson() => throw _privateConstructorUsedError;

  /// Create a copy of DashboardModel
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  $DashboardModelCopyWith<DashboardModel> get copyWith =>
      throw _privateConstructorUsedError;
}

/// @nodoc
abstract class $DashboardModelCopyWith<$Res> {
  factory $DashboardModelCopyWith(
          DashboardModel value, $Res Function(DashboardModel) then) =
      _$DashboardModelCopyWithImpl<$Res, DashboardModel>;
  @useResult
  $Res call(
      {DashboardStatsModel stats,
      @JsonKey(name: 'enrolled_courses')
      List<DashboardCourseModel> enrolledCourses,
      @JsonKey(name: 'recent_activity')
      List<RecentActivityModel> recentActivity,
      List<StudentInternshipModel> internships,
      @JsonKey(name: 'weekly_goal') WeeklyGoalModel? weeklyGoal});

  $DashboardStatsModelCopyWith<$Res> get stats;
  $WeeklyGoalModelCopyWith<$Res>? get weeklyGoal;
}

/// @nodoc
class _$DashboardModelCopyWithImpl<$Res, $Val extends DashboardModel>
    implements $DashboardModelCopyWith<$Res> {
  _$DashboardModelCopyWithImpl(this._value, this._then);

  // ignore: unused_field
  final $Val _value;
  // ignore: unused_field
  final $Res Function($Val) _then;

  /// Create a copy of DashboardModel
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? stats = null,
    Object? enrolledCourses = null,
    Object? recentActivity = null,
    Object? internships = null,
    Object? weeklyGoal = freezed,
  }) {
    return _then(_value.copyWith(
      stats: null == stats
          ? _value.stats
          : stats // ignore: cast_nullable_to_non_nullable
              as DashboardStatsModel,
      enrolledCourses: null == enrolledCourses
          ? _value.enrolledCourses
          : enrolledCourses // ignore: cast_nullable_to_non_nullable
              as List<DashboardCourseModel>,
      recentActivity: null == recentActivity
          ? _value.recentActivity
          : recentActivity // ignore: cast_nullable_to_non_nullable
              as List<RecentActivityModel>,
      internships: null == internships
          ? _value.internships
          : internships // ignore: cast_nullable_to_non_nullable
              as List<StudentInternshipModel>,
      weeklyGoal: freezed == weeklyGoal
          ? _value.weeklyGoal
          : weeklyGoal // ignore: cast_nullable_to_non_nullable
              as WeeklyGoalModel?,
    ) as $Val);
  }

  /// Create a copy of DashboardModel
  /// with the given fields replaced by the non-null parameter values.
  @override
  @pragma('vm:prefer-inline')
  $DashboardStatsModelCopyWith<$Res> get stats {
    return $DashboardStatsModelCopyWith<$Res>(_value.stats, (value) {
      return _then(_value.copyWith(stats: value) as $Val);
    });
  }

  /// Create a copy of DashboardModel
  /// with the given fields replaced by the non-null parameter values.
  @override
  @pragma('vm:prefer-inline')
  $WeeklyGoalModelCopyWith<$Res>? get weeklyGoal {
    if (_value.weeklyGoal == null) {
      return null;
    }

    return $WeeklyGoalModelCopyWith<$Res>(_value.weeklyGoal!, (value) {
      return _then(_value.copyWith(weeklyGoal: value) as $Val);
    });
  }
}

/// @nodoc
abstract class _$$DashboardModelImplCopyWith<$Res>
    implements $DashboardModelCopyWith<$Res> {
  factory _$$DashboardModelImplCopyWith(_$DashboardModelImpl value,
          $Res Function(_$DashboardModelImpl) then) =
      __$$DashboardModelImplCopyWithImpl<$Res>;
  @override
  @useResult
  $Res call(
      {DashboardStatsModel stats,
      @JsonKey(name: 'enrolled_courses')
      List<DashboardCourseModel> enrolledCourses,
      @JsonKey(name: 'recent_activity')
      List<RecentActivityModel> recentActivity,
      List<StudentInternshipModel> internships,
      @JsonKey(name: 'weekly_goal') WeeklyGoalModel? weeklyGoal});

  @override
  $DashboardStatsModelCopyWith<$Res> get stats;
  @override
  $WeeklyGoalModelCopyWith<$Res>? get weeklyGoal;
}

/// @nodoc
class __$$DashboardModelImplCopyWithImpl<$Res>
    extends _$DashboardModelCopyWithImpl<$Res, _$DashboardModelImpl>
    implements _$$DashboardModelImplCopyWith<$Res> {
  __$$DashboardModelImplCopyWithImpl(
      _$DashboardModelImpl _value, $Res Function(_$DashboardModelImpl) _then)
      : super(_value, _then);

  /// Create a copy of DashboardModel
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? stats = null,
    Object? enrolledCourses = null,
    Object? recentActivity = null,
    Object? internships = null,
    Object? weeklyGoal = freezed,
  }) {
    return _then(_$DashboardModelImpl(
      stats: null == stats
          ? _value.stats
          : stats // ignore: cast_nullable_to_non_nullable
              as DashboardStatsModel,
      enrolledCourses: null == enrolledCourses
          ? _value._enrolledCourses
          : enrolledCourses // ignore: cast_nullable_to_non_nullable
              as List<DashboardCourseModel>,
      recentActivity: null == recentActivity
          ? _value._recentActivity
          : recentActivity // ignore: cast_nullable_to_non_nullable
              as List<RecentActivityModel>,
      internships: null == internships
          ? _value._internships
          : internships // ignore: cast_nullable_to_non_nullable
              as List<StudentInternshipModel>,
      weeklyGoal: freezed == weeklyGoal
          ? _value.weeklyGoal
          : weeklyGoal // ignore: cast_nullable_to_non_nullable
              as WeeklyGoalModel?,
    ));
  }
}

/// @nodoc
@JsonSerializable()
class _$DashboardModelImpl extends _DashboardModel {
  const _$DashboardModelImpl(
      {required this.stats,
      @JsonKey(name: 'enrolled_courses')
      required final List<DashboardCourseModel> enrolledCourses,
      @JsonKey(name: 'recent_activity')
      required final List<RecentActivityModel> recentActivity,
      final List<StudentInternshipModel> internships = const [],
      @JsonKey(name: 'weekly_goal') this.weeklyGoal})
      : _enrolledCourses = enrolledCourses,
        _recentActivity = recentActivity,
        _internships = internships,
        super._();

  factory _$DashboardModelImpl.fromJson(Map<String, dynamic> json) =>
      _$$DashboardModelImplFromJson(json);

  @override
  final DashboardStatsModel stats;
  final List<DashboardCourseModel> _enrolledCourses;
  @override
  @JsonKey(name: 'enrolled_courses')
  List<DashboardCourseModel> get enrolledCourses {
    if (_enrolledCourses is EqualUnmodifiableListView) return _enrolledCourses;
    // ignore: implicit_dynamic_type
    return EqualUnmodifiableListView(_enrolledCourses);
  }

  final List<RecentActivityModel> _recentActivity;
  @override
  @JsonKey(name: 'recent_activity')
  List<RecentActivityModel> get recentActivity {
    if (_recentActivity is EqualUnmodifiableListView) return _recentActivity;
    // ignore: implicit_dynamic_type
    return EqualUnmodifiableListView(_recentActivity);
  }

  final List<StudentInternshipModel> _internships;
  @override
  @JsonKey()
  List<StudentInternshipModel> get internships {
    if (_internships is EqualUnmodifiableListView) return _internships;
    // ignore: implicit_dynamic_type
    return EqualUnmodifiableListView(_internships);
  }

  @override
  @JsonKey(name: 'weekly_goal')
  final WeeklyGoalModel? weeklyGoal;

  @override
  String toString() {
    return 'DashboardModel(stats: $stats, enrolledCourses: $enrolledCourses, recentActivity: $recentActivity, internships: $internships, weeklyGoal: $weeklyGoal)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$DashboardModelImpl &&
            (identical(other.stats, stats) || other.stats == stats) &&
            const DeepCollectionEquality()
                .equals(other._enrolledCourses, _enrolledCourses) &&
            const DeepCollectionEquality()
                .equals(other._recentActivity, _recentActivity) &&
            const DeepCollectionEquality()
                .equals(other._internships, _internships) &&
            (identical(other.weeklyGoal, weeklyGoal) ||
                other.weeklyGoal == weeklyGoal));
  }

  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  int get hashCode => Object.hash(
      runtimeType,
      stats,
      const DeepCollectionEquality().hash(_enrolledCourses),
      const DeepCollectionEquality().hash(_recentActivity),
      const DeepCollectionEquality().hash(_internships),
      weeklyGoal);

  /// Create a copy of DashboardModel
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  @pragma('vm:prefer-inline')
  _$$DashboardModelImplCopyWith<_$DashboardModelImpl> get copyWith =>
      __$$DashboardModelImplCopyWithImpl<_$DashboardModelImpl>(
          this, _$identity);

  @override
  Map<String, dynamic> toJson() {
    return _$$DashboardModelImplToJson(
      this,
    );
  }
}

abstract class _DashboardModel extends DashboardModel {
  const factory _DashboardModel(
          {required final DashboardStatsModel stats,
          @JsonKey(name: 'enrolled_courses')
          required final List<DashboardCourseModel> enrolledCourses,
          @JsonKey(name: 'recent_activity')
          required final List<RecentActivityModel> recentActivity,
          final List<StudentInternshipModel> internships,
          @JsonKey(name: 'weekly_goal') final WeeklyGoalModel? weeklyGoal}) =
      _$DashboardModelImpl;
  const _DashboardModel._() : super._();

  factory _DashboardModel.fromJson(Map<String, dynamic> json) =
      _$DashboardModelImpl.fromJson;

  @override
  DashboardStatsModel get stats;
  @override
  @JsonKey(name: 'enrolled_courses')
  List<DashboardCourseModel> get enrolledCourses;
  @override
  @JsonKey(name: 'recent_activity')
  List<RecentActivityModel> get recentActivity;
  @override
  List<StudentInternshipModel> get internships;
  @override
  @JsonKey(name: 'weekly_goal')
  WeeklyGoalModel? get weeklyGoal;

  /// Create a copy of DashboardModel
  /// with the given fields replaced by the non-null parameter values.
  @override
  @JsonKey(includeFromJson: false, includeToJson: false)
  _$$DashboardModelImplCopyWith<_$DashboardModelImpl> get copyWith =>
      throw _privateConstructorUsedError;
}

DashboardCourseModel _$DashboardCourseModelFromJson(Map<String, dynamic> json) {
  return _DashboardCourseModel.fromJson(json);
}

/// @nodoc
mixin _$DashboardCourseModel {
  int get id => throw _privateConstructorUsedError;
  String get title => throw _privateConstructorUsedError;
  String get thumbnail => throw _privateConstructorUsedError;
  double get progress => throw _privateConstructorUsedError;
  @JsonKey(name: 'totalLessons')
  int get totalLessons => throw _privateConstructorUsedError;
  @JsonKey(name: 'completedLessons')
  int get completedLessons => throw _privateConstructorUsedError;
  String get instructor => throw _privateConstructorUsedError;
  double get rating => throw _privateConstructorUsedError;
  @JsonKey(name: 'nextLesson')
  String get nextLesson => throw _privateConstructorUsedError;
  @JsonKey(name: 'enrollment_status')
  String get enrollmentStatus => throw _privateConstructorUsedError;

  /// Serializes this DashboardCourseModel to a JSON map.
  Map<String, dynamic> toJson() => throw _privateConstructorUsedError;

  /// Create a copy of DashboardCourseModel
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  $DashboardCourseModelCopyWith<DashboardCourseModel> get copyWith =>
      throw _privateConstructorUsedError;
}

/// @nodoc
abstract class $DashboardCourseModelCopyWith<$Res> {
  factory $DashboardCourseModelCopyWith(DashboardCourseModel value,
          $Res Function(DashboardCourseModel) then) =
      _$DashboardCourseModelCopyWithImpl<$Res, DashboardCourseModel>;
  @useResult
  $Res call(
      {int id,
      String title,
      String thumbnail,
      double progress,
      @JsonKey(name: 'totalLessons') int totalLessons,
      @JsonKey(name: 'completedLessons') int completedLessons,
      String instructor,
      double rating,
      @JsonKey(name: 'nextLesson') String nextLesson,
      @JsonKey(name: 'enrollment_status') String enrollmentStatus});
}

/// @nodoc
class _$DashboardCourseModelCopyWithImpl<$Res,
        $Val extends DashboardCourseModel>
    implements $DashboardCourseModelCopyWith<$Res> {
  _$DashboardCourseModelCopyWithImpl(this._value, this._then);

  // ignore: unused_field
  final $Val _value;
  // ignore: unused_field
  final $Res Function($Val) _then;

  /// Create a copy of DashboardCourseModel
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? id = null,
    Object? title = null,
    Object? thumbnail = null,
    Object? progress = null,
    Object? totalLessons = null,
    Object? completedLessons = null,
    Object? instructor = null,
    Object? rating = null,
    Object? nextLesson = null,
    Object? enrollmentStatus = null,
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
      thumbnail: null == thumbnail
          ? _value.thumbnail
          : thumbnail // ignore: cast_nullable_to_non_nullable
              as String,
      progress: null == progress
          ? _value.progress
          : progress // ignore: cast_nullable_to_non_nullable
              as double,
      totalLessons: null == totalLessons
          ? _value.totalLessons
          : totalLessons // ignore: cast_nullable_to_non_nullable
              as int,
      completedLessons: null == completedLessons
          ? _value.completedLessons
          : completedLessons // ignore: cast_nullable_to_non_nullable
              as int,
      instructor: null == instructor
          ? _value.instructor
          : instructor // ignore: cast_nullable_to_non_nullable
              as String,
      rating: null == rating
          ? _value.rating
          : rating // ignore: cast_nullable_to_non_nullable
              as double,
      nextLesson: null == nextLesson
          ? _value.nextLesson
          : nextLesson // ignore: cast_nullable_to_non_nullable
              as String,
      enrollmentStatus: null == enrollmentStatus
          ? _value.enrollmentStatus
          : enrollmentStatus // ignore: cast_nullable_to_non_nullable
              as String,
    ) as $Val);
  }
}

/// @nodoc
abstract class _$$DashboardCourseModelImplCopyWith<$Res>
    implements $DashboardCourseModelCopyWith<$Res> {
  factory _$$DashboardCourseModelImplCopyWith(_$DashboardCourseModelImpl value,
          $Res Function(_$DashboardCourseModelImpl) then) =
      __$$DashboardCourseModelImplCopyWithImpl<$Res>;
  @override
  @useResult
  $Res call(
      {int id,
      String title,
      String thumbnail,
      double progress,
      @JsonKey(name: 'totalLessons') int totalLessons,
      @JsonKey(name: 'completedLessons') int completedLessons,
      String instructor,
      double rating,
      @JsonKey(name: 'nextLesson') String nextLesson,
      @JsonKey(name: 'enrollment_status') String enrollmentStatus});
}

/// @nodoc
class __$$DashboardCourseModelImplCopyWithImpl<$Res>
    extends _$DashboardCourseModelCopyWithImpl<$Res, _$DashboardCourseModelImpl>
    implements _$$DashboardCourseModelImplCopyWith<$Res> {
  __$$DashboardCourseModelImplCopyWithImpl(_$DashboardCourseModelImpl _value,
      $Res Function(_$DashboardCourseModelImpl) _then)
      : super(_value, _then);

  /// Create a copy of DashboardCourseModel
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? id = null,
    Object? title = null,
    Object? thumbnail = null,
    Object? progress = null,
    Object? totalLessons = null,
    Object? completedLessons = null,
    Object? instructor = null,
    Object? rating = null,
    Object? nextLesson = null,
    Object? enrollmentStatus = null,
  }) {
    return _then(_$DashboardCourseModelImpl(
      id: null == id
          ? _value.id
          : id // ignore: cast_nullable_to_non_nullable
              as int,
      title: null == title
          ? _value.title
          : title // ignore: cast_nullable_to_non_nullable
              as String,
      thumbnail: null == thumbnail
          ? _value.thumbnail
          : thumbnail // ignore: cast_nullable_to_non_nullable
              as String,
      progress: null == progress
          ? _value.progress
          : progress // ignore: cast_nullable_to_non_nullable
              as double,
      totalLessons: null == totalLessons
          ? _value.totalLessons
          : totalLessons // ignore: cast_nullable_to_non_nullable
              as int,
      completedLessons: null == completedLessons
          ? _value.completedLessons
          : completedLessons // ignore: cast_nullable_to_non_nullable
              as int,
      instructor: null == instructor
          ? _value.instructor
          : instructor // ignore: cast_nullable_to_non_nullable
              as String,
      rating: null == rating
          ? _value.rating
          : rating // ignore: cast_nullable_to_non_nullable
              as double,
      nextLesson: null == nextLesson
          ? _value.nextLesson
          : nextLesson // ignore: cast_nullable_to_non_nullable
              as String,
      enrollmentStatus: null == enrollmentStatus
          ? _value.enrollmentStatus
          : enrollmentStatus // ignore: cast_nullable_to_non_nullable
              as String,
    ));
  }
}

/// @nodoc
@JsonSerializable()
class _$DashboardCourseModelImpl extends _DashboardCourseModel {
  const _$DashboardCourseModelImpl(
      {required this.id,
      required this.title,
      required this.thumbnail,
      required this.progress,
      @JsonKey(name: 'totalLessons') required this.totalLessons,
      @JsonKey(name: 'completedLessons') required this.completedLessons,
      required this.instructor,
      required this.rating,
      @JsonKey(name: 'nextLesson') required this.nextLesson,
      @JsonKey(name: 'enrollment_status') required this.enrollmentStatus})
      : super._();

  factory _$DashboardCourseModelImpl.fromJson(Map<String, dynamic> json) =>
      _$$DashboardCourseModelImplFromJson(json);

  @override
  final int id;
  @override
  final String title;
  @override
  final String thumbnail;
  @override
  final double progress;
  @override
  @JsonKey(name: 'totalLessons')
  final int totalLessons;
  @override
  @JsonKey(name: 'completedLessons')
  final int completedLessons;
  @override
  final String instructor;
  @override
  final double rating;
  @override
  @JsonKey(name: 'nextLesson')
  final String nextLesson;
  @override
  @JsonKey(name: 'enrollment_status')
  final String enrollmentStatus;

  @override
  String toString() {
    return 'DashboardCourseModel(id: $id, title: $title, thumbnail: $thumbnail, progress: $progress, totalLessons: $totalLessons, completedLessons: $completedLessons, instructor: $instructor, rating: $rating, nextLesson: $nextLesson, enrollmentStatus: $enrollmentStatus)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$DashboardCourseModelImpl &&
            (identical(other.id, id) || other.id == id) &&
            (identical(other.title, title) || other.title == title) &&
            (identical(other.thumbnail, thumbnail) ||
                other.thumbnail == thumbnail) &&
            (identical(other.progress, progress) ||
                other.progress == progress) &&
            (identical(other.totalLessons, totalLessons) ||
                other.totalLessons == totalLessons) &&
            (identical(other.completedLessons, completedLessons) ||
                other.completedLessons == completedLessons) &&
            (identical(other.instructor, instructor) ||
                other.instructor == instructor) &&
            (identical(other.rating, rating) || other.rating == rating) &&
            (identical(other.nextLesson, nextLesson) ||
                other.nextLesson == nextLesson) &&
            (identical(other.enrollmentStatus, enrollmentStatus) ||
                other.enrollmentStatus == enrollmentStatus));
  }

  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  int get hashCode => Object.hash(
      runtimeType,
      id,
      title,
      thumbnail,
      progress,
      totalLessons,
      completedLessons,
      instructor,
      rating,
      nextLesson,
      enrollmentStatus);

  /// Create a copy of DashboardCourseModel
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  @pragma('vm:prefer-inline')
  _$$DashboardCourseModelImplCopyWith<_$DashboardCourseModelImpl>
      get copyWith =>
          __$$DashboardCourseModelImplCopyWithImpl<_$DashboardCourseModelImpl>(
              this, _$identity);

  @override
  Map<String, dynamic> toJson() {
    return _$$DashboardCourseModelImplToJson(
      this,
    );
  }
}

abstract class _DashboardCourseModel extends DashboardCourseModel {
  const factory _DashboardCourseModel(
      {required final int id,
      required final String title,
      required final String thumbnail,
      required final double progress,
      @JsonKey(name: 'totalLessons') required final int totalLessons,
      @JsonKey(name: 'completedLessons') required final int completedLessons,
      required final String instructor,
      required final double rating,
      @JsonKey(name: 'nextLesson') required final String nextLesson,
      @JsonKey(name: 'enrollment_status')
      required final String enrollmentStatus}) = _$DashboardCourseModelImpl;
  const _DashboardCourseModel._() : super._();

  factory _DashboardCourseModel.fromJson(Map<String, dynamic> json) =
      _$DashboardCourseModelImpl.fromJson;

  @override
  int get id;
  @override
  String get title;
  @override
  String get thumbnail;
  @override
  double get progress;
  @override
  @JsonKey(name: 'totalLessons')
  int get totalLessons;
  @override
  @JsonKey(name: 'completedLessons')
  int get completedLessons;
  @override
  String get instructor;
  @override
  double get rating;
  @override
  @JsonKey(name: 'nextLesson')
  String get nextLesson;
  @override
  @JsonKey(name: 'enrollment_status')
  String get enrollmentStatus;

  /// Create a copy of DashboardCourseModel
  /// with the given fields replaced by the non-null parameter values.
  @override
  @JsonKey(includeFromJson: false, includeToJson: false)
  _$$DashboardCourseModelImplCopyWith<_$DashboardCourseModelImpl>
      get copyWith => throw _privateConstructorUsedError;
}

DashboardStatsModel _$DashboardStatsModelFromJson(Map<String, dynamic> json) {
  return _DashboardStatsModel.fromJson(json);
}

/// @nodoc
mixin _$DashboardStatsModel {
  @JsonKey(name: 'enrolled_courses')
  int get enrolledCourses => throw _privateConstructorUsedError;
  @JsonKey(name: 'completed_courses')
  int get completedCourses => throw _privateConstructorUsedError;
  @JsonKey(name: 'total_hours')
  int get totalHours => throw _privateConstructorUsedError;
  int get certificates => throw _privateConstructorUsedError;

  /// Serializes this DashboardStatsModel to a JSON map.
  Map<String, dynamic> toJson() => throw _privateConstructorUsedError;

  /// Create a copy of DashboardStatsModel
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  $DashboardStatsModelCopyWith<DashboardStatsModel> get copyWith =>
      throw _privateConstructorUsedError;
}

/// @nodoc
abstract class $DashboardStatsModelCopyWith<$Res> {
  factory $DashboardStatsModelCopyWith(
          DashboardStatsModel value, $Res Function(DashboardStatsModel) then) =
      _$DashboardStatsModelCopyWithImpl<$Res, DashboardStatsModel>;
  @useResult
  $Res call(
      {@JsonKey(name: 'enrolled_courses') int enrolledCourses,
      @JsonKey(name: 'completed_courses') int completedCourses,
      @JsonKey(name: 'total_hours') int totalHours,
      int certificates});
}

/// @nodoc
class _$DashboardStatsModelCopyWithImpl<$Res, $Val extends DashboardStatsModel>
    implements $DashboardStatsModelCopyWith<$Res> {
  _$DashboardStatsModelCopyWithImpl(this._value, this._then);

  // ignore: unused_field
  final $Val _value;
  // ignore: unused_field
  final $Res Function($Val) _then;

  /// Create a copy of DashboardStatsModel
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? enrolledCourses = null,
    Object? completedCourses = null,
    Object? totalHours = null,
    Object? certificates = null,
  }) {
    return _then(_value.copyWith(
      enrolledCourses: null == enrolledCourses
          ? _value.enrolledCourses
          : enrolledCourses // ignore: cast_nullable_to_non_nullable
              as int,
      completedCourses: null == completedCourses
          ? _value.completedCourses
          : completedCourses // ignore: cast_nullable_to_non_nullable
              as int,
      totalHours: null == totalHours
          ? _value.totalHours
          : totalHours // ignore: cast_nullable_to_non_nullable
              as int,
      certificates: null == certificates
          ? _value.certificates
          : certificates // ignore: cast_nullable_to_non_nullable
              as int,
    ) as $Val);
  }
}

/// @nodoc
abstract class _$$DashboardStatsModelImplCopyWith<$Res>
    implements $DashboardStatsModelCopyWith<$Res> {
  factory _$$DashboardStatsModelImplCopyWith(_$DashboardStatsModelImpl value,
          $Res Function(_$DashboardStatsModelImpl) then) =
      __$$DashboardStatsModelImplCopyWithImpl<$Res>;
  @override
  @useResult
  $Res call(
      {@JsonKey(name: 'enrolled_courses') int enrolledCourses,
      @JsonKey(name: 'completed_courses') int completedCourses,
      @JsonKey(name: 'total_hours') int totalHours,
      int certificates});
}

/// @nodoc
class __$$DashboardStatsModelImplCopyWithImpl<$Res>
    extends _$DashboardStatsModelCopyWithImpl<$Res, _$DashboardStatsModelImpl>
    implements _$$DashboardStatsModelImplCopyWith<$Res> {
  __$$DashboardStatsModelImplCopyWithImpl(_$DashboardStatsModelImpl _value,
      $Res Function(_$DashboardStatsModelImpl) _then)
      : super(_value, _then);

  /// Create a copy of DashboardStatsModel
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? enrolledCourses = null,
    Object? completedCourses = null,
    Object? totalHours = null,
    Object? certificates = null,
  }) {
    return _then(_$DashboardStatsModelImpl(
      enrolledCourses: null == enrolledCourses
          ? _value.enrolledCourses
          : enrolledCourses // ignore: cast_nullable_to_non_nullable
              as int,
      completedCourses: null == completedCourses
          ? _value.completedCourses
          : completedCourses // ignore: cast_nullable_to_non_nullable
              as int,
      totalHours: null == totalHours
          ? _value.totalHours
          : totalHours // ignore: cast_nullable_to_non_nullable
              as int,
      certificates: null == certificates
          ? _value.certificates
          : certificates // ignore: cast_nullable_to_non_nullable
              as int,
    ));
  }
}

/// @nodoc
@JsonSerializable()
class _$DashboardStatsModelImpl extends _DashboardStatsModel {
  const _$DashboardStatsModelImpl(
      {@JsonKey(name: 'enrolled_courses') required this.enrolledCourses,
      @JsonKey(name: 'completed_courses') required this.completedCourses,
      @JsonKey(name: 'total_hours') required this.totalHours,
      required this.certificates})
      : super._();

  factory _$DashboardStatsModelImpl.fromJson(Map<String, dynamic> json) =>
      _$$DashboardStatsModelImplFromJson(json);

  @override
  @JsonKey(name: 'enrolled_courses')
  final int enrolledCourses;
  @override
  @JsonKey(name: 'completed_courses')
  final int completedCourses;
  @override
  @JsonKey(name: 'total_hours')
  final int totalHours;
  @override
  final int certificates;

  @override
  String toString() {
    return 'DashboardStatsModel(enrolledCourses: $enrolledCourses, completedCourses: $completedCourses, totalHours: $totalHours, certificates: $certificates)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$DashboardStatsModelImpl &&
            (identical(other.enrolledCourses, enrolledCourses) ||
                other.enrolledCourses == enrolledCourses) &&
            (identical(other.completedCourses, completedCourses) ||
                other.completedCourses == completedCourses) &&
            (identical(other.totalHours, totalHours) ||
                other.totalHours == totalHours) &&
            (identical(other.certificates, certificates) ||
                other.certificates == certificates));
  }

  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  int get hashCode => Object.hash(
      runtimeType, enrolledCourses, completedCourses, totalHours, certificates);

  /// Create a copy of DashboardStatsModel
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  @pragma('vm:prefer-inline')
  _$$DashboardStatsModelImplCopyWith<_$DashboardStatsModelImpl> get copyWith =>
      __$$DashboardStatsModelImplCopyWithImpl<_$DashboardStatsModelImpl>(
          this, _$identity);

  @override
  Map<String, dynamic> toJson() {
    return _$$DashboardStatsModelImplToJson(
      this,
    );
  }
}

abstract class _DashboardStatsModel extends DashboardStatsModel {
  const factory _DashboardStatsModel(
      {@JsonKey(name: 'enrolled_courses') required final int enrolledCourses,
      @JsonKey(name: 'completed_courses') required final int completedCourses,
      @JsonKey(name: 'total_hours') required final int totalHours,
      required final int certificates}) = _$DashboardStatsModelImpl;
  const _DashboardStatsModel._() : super._();

  factory _DashboardStatsModel.fromJson(Map<String, dynamic> json) =
      _$DashboardStatsModelImpl.fromJson;

  @override
  @JsonKey(name: 'enrolled_courses')
  int get enrolledCourses;
  @override
  @JsonKey(name: 'completed_courses')
  int get completedCourses;
  @override
  @JsonKey(name: 'total_hours')
  int get totalHours;
  @override
  int get certificates;

  /// Create a copy of DashboardStatsModel
  /// with the given fields replaced by the non-null parameter values.
  @override
  @JsonKey(includeFromJson: false, includeToJson: false)
  _$$DashboardStatsModelImplCopyWith<_$DashboardStatsModelImpl> get copyWith =>
      throw _privateConstructorUsedError;
}

RecentActivityModel _$RecentActivityModelFromJson(Map<String, dynamic> json) {
  return _RecentActivityModel.fromJson(json);
}

/// @nodoc
mixin _$RecentActivityModel {
  String get type => throw _privateConstructorUsedError;
  String get action => throw _privateConstructorUsedError;
  String get title => throw _privateConstructorUsedError;
  String get course => throw _privateConstructorUsedError;
  String get description => throw _privateConstructorUsedError;
  String get timestamp => throw _privateConstructorUsedError;
  String get time => throw _privateConstructorUsedError;

  /// Serializes this RecentActivityModel to a JSON map.
  Map<String, dynamic> toJson() => throw _privateConstructorUsedError;

  /// Create a copy of RecentActivityModel
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  $RecentActivityModelCopyWith<RecentActivityModel> get copyWith =>
      throw _privateConstructorUsedError;
}

/// @nodoc
abstract class $RecentActivityModelCopyWith<$Res> {
  factory $RecentActivityModelCopyWith(
          RecentActivityModel value, $Res Function(RecentActivityModel) then) =
      _$RecentActivityModelCopyWithImpl<$Res, RecentActivityModel>;
  @useResult
  $Res call(
      {String type,
      String action,
      String title,
      String course,
      String description,
      String timestamp,
      String time});
}

/// @nodoc
class _$RecentActivityModelCopyWithImpl<$Res, $Val extends RecentActivityModel>
    implements $RecentActivityModelCopyWith<$Res> {
  _$RecentActivityModelCopyWithImpl(this._value, this._then);

  // ignore: unused_field
  final $Val _value;
  // ignore: unused_field
  final $Res Function($Val) _then;

  /// Create a copy of RecentActivityModel
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? type = null,
    Object? action = null,
    Object? title = null,
    Object? course = null,
    Object? description = null,
    Object? timestamp = null,
    Object? time = null,
  }) {
    return _then(_value.copyWith(
      type: null == type
          ? _value.type
          : type // ignore: cast_nullable_to_non_nullable
              as String,
      action: null == action
          ? _value.action
          : action // ignore: cast_nullable_to_non_nullable
              as String,
      title: null == title
          ? _value.title
          : title // ignore: cast_nullable_to_non_nullable
              as String,
      course: null == course
          ? _value.course
          : course // ignore: cast_nullable_to_non_nullable
              as String,
      description: null == description
          ? _value.description
          : description // ignore: cast_nullable_to_non_nullable
              as String,
      timestamp: null == timestamp
          ? _value.timestamp
          : timestamp // ignore: cast_nullable_to_non_nullable
              as String,
      time: null == time
          ? _value.time
          : time // ignore: cast_nullable_to_non_nullable
              as String,
    ) as $Val);
  }
}

/// @nodoc
abstract class _$$RecentActivityModelImplCopyWith<$Res>
    implements $RecentActivityModelCopyWith<$Res> {
  factory _$$RecentActivityModelImplCopyWith(_$RecentActivityModelImpl value,
          $Res Function(_$RecentActivityModelImpl) then) =
      __$$RecentActivityModelImplCopyWithImpl<$Res>;
  @override
  @useResult
  $Res call(
      {String type,
      String action,
      String title,
      String course,
      String description,
      String timestamp,
      String time});
}

/// @nodoc
class __$$RecentActivityModelImplCopyWithImpl<$Res>
    extends _$RecentActivityModelCopyWithImpl<$Res, _$RecentActivityModelImpl>
    implements _$$RecentActivityModelImplCopyWith<$Res> {
  __$$RecentActivityModelImplCopyWithImpl(_$RecentActivityModelImpl _value,
      $Res Function(_$RecentActivityModelImpl) _then)
      : super(_value, _then);

  /// Create a copy of RecentActivityModel
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? type = null,
    Object? action = null,
    Object? title = null,
    Object? course = null,
    Object? description = null,
    Object? timestamp = null,
    Object? time = null,
  }) {
    return _then(_$RecentActivityModelImpl(
      type: null == type
          ? _value.type
          : type // ignore: cast_nullable_to_non_nullable
              as String,
      action: null == action
          ? _value.action
          : action // ignore: cast_nullable_to_non_nullable
              as String,
      title: null == title
          ? _value.title
          : title // ignore: cast_nullable_to_non_nullable
              as String,
      course: null == course
          ? _value.course
          : course // ignore: cast_nullable_to_non_nullable
              as String,
      description: null == description
          ? _value.description
          : description // ignore: cast_nullable_to_non_nullable
              as String,
      timestamp: null == timestamp
          ? _value.timestamp
          : timestamp // ignore: cast_nullable_to_non_nullable
              as String,
      time: null == time
          ? _value.time
          : time // ignore: cast_nullable_to_non_nullable
              as String,
    ));
  }
}

/// @nodoc
@JsonSerializable()
class _$RecentActivityModelImpl extends _RecentActivityModel {
  const _$RecentActivityModelImpl(
      {required this.type,
      required this.action,
      required this.title,
      required this.course,
      required this.description,
      required this.timestamp,
      required this.time})
      : super._();

  factory _$RecentActivityModelImpl.fromJson(Map<String, dynamic> json) =>
      _$$RecentActivityModelImplFromJson(json);

  @override
  final String type;
  @override
  final String action;
  @override
  final String title;
  @override
  final String course;
  @override
  final String description;
  @override
  final String timestamp;
  @override
  final String time;

  @override
  String toString() {
    return 'RecentActivityModel(type: $type, action: $action, title: $title, course: $course, description: $description, timestamp: $timestamp, time: $time)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$RecentActivityModelImpl &&
            (identical(other.type, type) || other.type == type) &&
            (identical(other.action, action) || other.action == action) &&
            (identical(other.title, title) || other.title == title) &&
            (identical(other.course, course) || other.course == course) &&
            (identical(other.description, description) ||
                other.description == description) &&
            (identical(other.timestamp, timestamp) ||
                other.timestamp == timestamp) &&
            (identical(other.time, time) || other.time == time));
  }

  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  int get hashCode => Object.hash(
      runtimeType, type, action, title, course, description, timestamp, time);

  /// Create a copy of RecentActivityModel
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  @pragma('vm:prefer-inline')
  _$$RecentActivityModelImplCopyWith<_$RecentActivityModelImpl> get copyWith =>
      __$$RecentActivityModelImplCopyWithImpl<_$RecentActivityModelImpl>(
          this, _$identity);

  @override
  Map<String, dynamic> toJson() {
    return _$$RecentActivityModelImplToJson(
      this,
    );
  }
}

abstract class _RecentActivityModel extends RecentActivityModel {
  const factory _RecentActivityModel(
      {required final String type,
      required final String action,
      required final String title,
      required final String course,
      required final String description,
      required final String timestamp,
      required final String time}) = _$RecentActivityModelImpl;
  const _RecentActivityModel._() : super._();

  factory _RecentActivityModel.fromJson(Map<String, dynamic> json) =
      _$RecentActivityModelImpl.fromJson;

  @override
  String get type;
  @override
  String get action;
  @override
  String get title;
  @override
  String get course;
  @override
  String get description;
  @override
  String get timestamp;
  @override
  String get time;

  /// Create a copy of RecentActivityModel
  /// with the given fields replaced by the non-null parameter values.
  @override
  @JsonKey(includeFromJson: false, includeToJson: false)
  _$$RecentActivityModelImplCopyWith<_$RecentActivityModelImpl> get copyWith =>
      throw _privateConstructorUsedError;
}

StudentInternshipModel _$StudentInternshipModelFromJson(
    Map<String, dynamic> json) {
  return _StudentInternshipModel.fromJson(json);
}

/// @nodoc
mixin _$StudentInternshipModel {
  int get id => throw _privateConstructorUsedError;
  String get title => throw _privateConstructorUsedError;
  @JsonKey(name: 'voucher_code')
  String get voucherCode => throw _privateConstructorUsedError;
  String get status => throw _privateConstructorUsedError;
  @JsonKey(name: 'redeemed_course_title')
  String? get redeemedCourseTitle => throw _privateConstructorUsedError;
  @JsonKey(name: 'attendance_days')
  int get attendanceDays => throw _privateConstructorUsedError;
  @JsonKey(name: 'hired_company')
  String? get hiredCompany => throw _privateConstructorUsedError;
  @JsonKey(name: 'created_at')
  String? get createdAt => throw _privateConstructorUsedError;

  /// Serializes this StudentInternshipModel to a JSON map.
  Map<String, dynamic> toJson() => throw _privateConstructorUsedError;

  /// Create a copy of StudentInternshipModel
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  $StudentInternshipModelCopyWith<StudentInternshipModel> get copyWith =>
      throw _privateConstructorUsedError;
}

/// @nodoc
abstract class $StudentInternshipModelCopyWith<$Res> {
  factory $StudentInternshipModelCopyWith(StudentInternshipModel value,
          $Res Function(StudentInternshipModel) then) =
      _$StudentInternshipModelCopyWithImpl<$Res, StudentInternshipModel>;
  @useResult
  $Res call(
      {int id,
      String title,
      @JsonKey(name: 'voucher_code') String voucherCode,
      String status,
      @JsonKey(name: 'redeemed_course_title') String? redeemedCourseTitle,
      @JsonKey(name: 'attendance_days') int attendanceDays,
      @JsonKey(name: 'hired_company') String? hiredCompany,
      @JsonKey(name: 'created_at') String? createdAt});
}

/// @nodoc
class _$StudentInternshipModelCopyWithImpl<$Res,
        $Val extends StudentInternshipModel>
    implements $StudentInternshipModelCopyWith<$Res> {
  _$StudentInternshipModelCopyWithImpl(this._value, this._then);

  // ignore: unused_field
  final $Val _value;
  // ignore: unused_field
  final $Res Function($Val) _then;

  /// Create a copy of StudentInternshipModel
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? id = null,
    Object? title = null,
    Object? voucherCode = null,
    Object? status = null,
    Object? redeemedCourseTitle = freezed,
    Object? attendanceDays = null,
    Object? hiredCompany = freezed,
    Object? createdAt = freezed,
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
      voucherCode: null == voucherCode
          ? _value.voucherCode
          : voucherCode // ignore: cast_nullable_to_non_nullable
              as String,
      status: null == status
          ? _value.status
          : status // ignore: cast_nullable_to_non_nullable
              as String,
      redeemedCourseTitle: freezed == redeemedCourseTitle
          ? _value.redeemedCourseTitle
          : redeemedCourseTitle // ignore: cast_nullable_to_non_nullable
              as String?,
      attendanceDays: null == attendanceDays
          ? _value.attendanceDays
          : attendanceDays // ignore: cast_nullable_to_non_nullable
              as int,
      hiredCompany: freezed == hiredCompany
          ? _value.hiredCompany
          : hiredCompany // ignore: cast_nullable_to_non_nullable
              as String?,
      createdAt: freezed == createdAt
          ? _value.createdAt
          : createdAt // ignore: cast_nullable_to_non_nullable
              as String?,
    ) as $Val);
  }
}

/// @nodoc
abstract class _$$StudentInternshipModelImplCopyWith<$Res>
    implements $StudentInternshipModelCopyWith<$Res> {
  factory _$$StudentInternshipModelImplCopyWith(
          _$StudentInternshipModelImpl value,
          $Res Function(_$StudentInternshipModelImpl) then) =
      __$$StudentInternshipModelImplCopyWithImpl<$Res>;
  @override
  @useResult
  $Res call(
      {int id,
      String title,
      @JsonKey(name: 'voucher_code') String voucherCode,
      String status,
      @JsonKey(name: 'redeemed_course_title') String? redeemedCourseTitle,
      @JsonKey(name: 'attendance_days') int attendanceDays,
      @JsonKey(name: 'hired_company') String? hiredCompany,
      @JsonKey(name: 'created_at') String? createdAt});
}

/// @nodoc
class __$$StudentInternshipModelImplCopyWithImpl<$Res>
    extends _$StudentInternshipModelCopyWithImpl<$Res,
        _$StudentInternshipModelImpl>
    implements _$$StudentInternshipModelImplCopyWith<$Res> {
  __$$StudentInternshipModelImplCopyWithImpl(
      _$StudentInternshipModelImpl _value,
      $Res Function(_$StudentInternshipModelImpl) _then)
      : super(_value, _then);

  /// Create a copy of StudentInternshipModel
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? id = null,
    Object? title = null,
    Object? voucherCode = null,
    Object? status = null,
    Object? redeemedCourseTitle = freezed,
    Object? attendanceDays = null,
    Object? hiredCompany = freezed,
    Object? createdAt = freezed,
  }) {
    return _then(_$StudentInternshipModelImpl(
      id: null == id
          ? _value.id
          : id // ignore: cast_nullable_to_non_nullable
              as int,
      title: null == title
          ? _value.title
          : title // ignore: cast_nullable_to_non_nullable
              as String,
      voucherCode: null == voucherCode
          ? _value.voucherCode
          : voucherCode // ignore: cast_nullable_to_non_nullable
              as String,
      status: null == status
          ? _value.status
          : status // ignore: cast_nullable_to_non_nullable
              as String,
      redeemedCourseTitle: freezed == redeemedCourseTitle
          ? _value.redeemedCourseTitle
          : redeemedCourseTitle // ignore: cast_nullable_to_non_nullable
              as String?,
      attendanceDays: null == attendanceDays
          ? _value.attendanceDays
          : attendanceDays // ignore: cast_nullable_to_non_nullable
              as int,
      hiredCompany: freezed == hiredCompany
          ? _value.hiredCompany
          : hiredCompany // ignore: cast_nullable_to_non_nullable
              as String?,
      createdAt: freezed == createdAt
          ? _value.createdAt
          : createdAt // ignore: cast_nullable_to_non_nullable
              as String?,
    ));
  }
}

/// @nodoc
@JsonSerializable()
class _$StudentInternshipModelImpl extends _StudentInternshipModel {
  const _$StudentInternshipModelImpl(
      {required this.id,
      required this.title,
      @JsonKey(name: 'voucher_code') required this.voucherCode,
      required this.status,
      @JsonKey(name: 'redeemed_course_title') this.redeemedCourseTitle,
      @JsonKey(name: 'attendance_days') required this.attendanceDays,
      @JsonKey(name: 'hired_company') this.hiredCompany,
      @JsonKey(name: 'created_at') this.createdAt})
      : super._();

  factory _$StudentInternshipModelImpl.fromJson(Map<String, dynamic> json) =>
      _$$StudentInternshipModelImplFromJson(json);

  @override
  final int id;
  @override
  final String title;
  @override
  @JsonKey(name: 'voucher_code')
  final String voucherCode;
  @override
  final String status;
  @override
  @JsonKey(name: 'redeemed_course_title')
  final String? redeemedCourseTitle;
  @override
  @JsonKey(name: 'attendance_days')
  final int attendanceDays;
  @override
  @JsonKey(name: 'hired_company')
  final String? hiredCompany;
  @override
  @JsonKey(name: 'created_at')
  final String? createdAt;

  @override
  String toString() {
    return 'StudentInternshipModel(id: $id, title: $title, voucherCode: $voucherCode, status: $status, redeemedCourseTitle: $redeemedCourseTitle, attendanceDays: $attendanceDays, hiredCompany: $hiredCompany, createdAt: $createdAt)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$StudentInternshipModelImpl &&
            (identical(other.id, id) || other.id == id) &&
            (identical(other.title, title) || other.title == title) &&
            (identical(other.voucherCode, voucherCode) ||
                other.voucherCode == voucherCode) &&
            (identical(other.status, status) || other.status == status) &&
            (identical(other.redeemedCourseTitle, redeemedCourseTitle) ||
                other.redeemedCourseTitle == redeemedCourseTitle) &&
            (identical(other.attendanceDays, attendanceDays) ||
                other.attendanceDays == attendanceDays) &&
            (identical(other.hiredCompany, hiredCompany) ||
                other.hiredCompany == hiredCompany) &&
            (identical(other.createdAt, createdAt) ||
                other.createdAt == createdAt));
  }

  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  int get hashCode => Object.hash(runtimeType, id, title, voucherCode, status,
      redeemedCourseTitle, attendanceDays, hiredCompany, createdAt);

  /// Create a copy of StudentInternshipModel
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  @pragma('vm:prefer-inline')
  _$$StudentInternshipModelImplCopyWith<_$StudentInternshipModelImpl>
      get copyWith => __$$StudentInternshipModelImplCopyWithImpl<
          _$StudentInternshipModelImpl>(this, _$identity);

  @override
  Map<String, dynamic> toJson() {
    return _$$StudentInternshipModelImplToJson(
      this,
    );
  }
}

abstract class _StudentInternshipModel extends StudentInternshipModel {
  const factory _StudentInternshipModel(
      {required final int id,
      required final String title,
      @JsonKey(name: 'voucher_code') required final String voucherCode,
      required final String status,
      @JsonKey(name: 'redeemed_course_title') final String? redeemedCourseTitle,
      @JsonKey(name: 'attendance_days') required final int attendanceDays,
      @JsonKey(name: 'hired_company') final String? hiredCompany,
      @JsonKey(name: 'created_at')
      final String? createdAt}) = _$StudentInternshipModelImpl;
  const _StudentInternshipModel._() : super._();

  factory _StudentInternshipModel.fromJson(Map<String, dynamic> json) =
      _$StudentInternshipModelImpl.fromJson;

  @override
  int get id;
  @override
  String get title;
  @override
  @JsonKey(name: 'voucher_code')
  String get voucherCode;
  @override
  String get status;
  @override
  @JsonKey(name: 'redeemed_course_title')
  String? get redeemedCourseTitle;
  @override
  @JsonKey(name: 'attendance_days')
  int get attendanceDays;
  @override
  @JsonKey(name: 'hired_company')
  String? get hiredCompany;
  @override
  @JsonKey(name: 'created_at')
  String? get createdAt;

  /// Create a copy of StudentInternshipModel
  /// with the given fields replaced by the non-null parameter values.
  @override
  @JsonKey(includeFromJson: false, includeToJson: false)
  _$$StudentInternshipModelImplCopyWith<_$StudentInternshipModelImpl>
      get copyWith => throw _privateConstructorUsedError;
}

WeeklyGoalModel _$WeeklyGoalModelFromJson(Map<String, dynamic> json) {
  return _WeeklyGoalModel.fromJson(json);
}

/// @nodoc
mixin _$WeeklyGoalModel {
  @JsonKey(name: 'goal_hours')
  int get goalHours => throw _privateConstructorUsedError;
  @JsonKey(name: 'completed_hours')
  double get completedHours => throw _privateConstructorUsedError;
  @JsonKey(name: 'progress_percentage')
  int get progressPercentage => throw _privateConstructorUsedError;
  @JsonKey(name: 'lessons_completed')
  int get lessonsCompleted => throw _privateConstructorUsedError;

  /// Serializes this WeeklyGoalModel to a JSON map.
  Map<String, dynamic> toJson() => throw _privateConstructorUsedError;

  /// Create a copy of WeeklyGoalModel
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  $WeeklyGoalModelCopyWith<WeeklyGoalModel> get copyWith =>
      throw _privateConstructorUsedError;
}

/// @nodoc
abstract class $WeeklyGoalModelCopyWith<$Res> {
  factory $WeeklyGoalModelCopyWith(
          WeeklyGoalModel value, $Res Function(WeeklyGoalModel) then) =
      _$WeeklyGoalModelCopyWithImpl<$Res, WeeklyGoalModel>;
  @useResult
  $Res call(
      {@JsonKey(name: 'goal_hours') int goalHours,
      @JsonKey(name: 'completed_hours') double completedHours,
      @JsonKey(name: 'progress_percentage') int progressPercentage,
      @JsonKey(name: 'lessons_completed') int lessonsCompleted});
}

/// @nodoc
class _$WeeklyGoalModelCopyWithImpl<$Res, $Val extends WeeklyGoalModel>
    implements $WeeklyGoalModelCopyWith<$Res> {
  _$WeeklyGoalModelCopyWithImpl(this._value, this._then);

  // ignore: unused_field
  final $Val _value;
  // ignore: unused_field
  final $Res Function($Val) _then;

  /// Create a copy of WeeklyGoalModel
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? goalHours = null,
    Object? completedHours = null,
    Object? progressPercentage = null,
    Object? lessonsCompleted = null,
  }) {
    return _then(_value.copyWith(
      goalHours: null == goalHours
          ? _value.goalHours
          : goalHours // ignore: cast_nullable_to_non_nullable
              as int,
      completedHours: null == completedHours
          ? _value.completedHours
          : completedHours // ignore: cast_nullable_to_non_nullable
              as double,
      progressPercentage: null == progressPercentage
          ? _value.progressPercentage
          : progressPercentage // ignore: cast_nullable_to_non_nullable
              as int,
      lessonsCompleted: null == lessonsCompleted
          ? _value.lessonsCompleted
          : lessonsCompleted // ignore: cast_nullable_to_non_nullable
              as int,
    ) as $Val);
  }
}

/// @nodoc
abstract class _$$WeeklyGoalModelImplCopyWith<$Res>
    implements $WeeklyGoalModelCopyWith<$Res> {
  factory _$$WeeklyGoalModelImplCopyWith(_$WeeklyGoalModelImpl value,
          $Res Function(_$WeeklyGoalModelImpl) then) =
      __$$WeeklyGoalModelImplCopyWithImpl<$Res>;
  @override
  @useResult
  $Res call(
      {@JsonKey(name: 'goal_hours') int goalHours,
      @JsonKey(name: 'completed_hours') double completedHours,
      @JsonKey(name: 'progress_percentage') int progressPercentage,
      @JsonKey(name: 'lessons_completed') int lessonsCompleted});
}

/// @nodoc
class __$$WeeklyGoalModelImplCopyWithImpl<$Res>
    extends _$WeeklyGoalModelCopyWithImpl<$Res, _$WeeklyGoalModelImpl>
    implements _$$WeeklyGoalModelImplCopyWith<$Res> {
  __$$WeeklyGoalModelImplCopyWithImpl(
      _$WeeklyGoalModelImpl _value, $Res Function(_$WeeklyGoalModelImpl) _then)
      : super(_value, _then);

  /// Create a copy of WeeklyGoalModel
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? goalHours = null,
    Object? completedHours = null,
    Object? progressPercentage = null,
    Object? lessonsCompleted = null,
  }) {
    return _then(_$WeeklyGoalModelImpl(
      goalHours: null == goalHours
          ? _value.goalHours
          : goalHours // ignore: cast_nullable_to_non_nullable
              as int,
      completedHours: null == completedHours
          ? _value.completedHours
          : completedHours // ignore: cast_nullable_to_non_nullable
              as double,
      progressPercentage: null == progressPercentage
          ? _value.progressPercentage
          : progressPercentage // ignore: cast_nullable_to_non_nullable
              as int,
      lessonsCompleted: null == lessonsCompleted
          ? _value.lessonsCompleted
          : lessonsCompleted // ignore: cast_nullable_to_non_nullable
              as int,
    ));
  }
}

/// @nodoc
@JsonSerializable()
class _$WeeklyGoalModelImpl extends _WeeklyGoalModel {
  const _$WeeklyGoalModelImpl(
      {@JsonKey(name: 'goal_hours') required this.goalHours,
      @JsonKey(name: 'completed_hours') required this.completedHours,
      @JsonKey(name: 'progress_percentage') required this.progressPercentage,
      @JsonKey(name: 'lessons_completed') required this.lessonsCompleted})
      : super._();

  factory _$WeeklyGoalModelImpl.fromJson(Map<String, dynamic> json) =>
      _$$WeeklyGoalModelImplFromJson(json);

  @override
  @JsonKey(name: 'goal_hours')
  final int goalHours;
  @override
  @JsonKey(name: 'completed_hours')
  final double completedHours;
  @override
  @JsonKey(name: 'progress_percentage')
  final int progressPercentage;
  @override
  @JsonKey(name: 'lessons_completed')
  final int lessonsCompleted;

  @override
  String toString() {
    return 'WeeklyGoalModel(goalHours: $goalHours, completedHours: $completedHours, progressPercentage: $progressPercentage, lessonsCompleted: $lessonsCompleted)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$WeeklyGoalModelImpl &&
            (identical(other.goalHours, goalHours) ||
                other.goalHours == goalHours) &&
            (identical(other.completedHours, completedHours) ||
                other.completedHours == completedHours) &&
            (identical(other.progressPercentage, progressPercentage) ||
                other.progressPercentage == progressPercentage) &&
            (identical(other.lessonsCompleted, lessonsCompleted) ||
                other.lessonsCompleted == lessonsCompleted));
  }

  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  int get hashCode => Object.hash(runtimeType, goalHours, completedHours,
      progressPercentage, lessonsCompleted);

  /// Create a copy of WeeklyGoalModel
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  @pragma('vm:prefer-inline')
  _$$WeeklyGoalModelImplCopyWith<_$WeeklyGoalModelImpl> get copyWith =>
      __$$WeeklyGoalModelImplCopyWithImpl<_$WeeklyGoalModelImpl>(
          this, _$identity);

  @override
  Map<String, dynamic> toJson() {
    return _$$WeeklyGoalModelImplToJson(
      this,
    );
  }
}

abstract class _WeeklyGoalModel extends WeeklyGoalModel {
  const factory _WeeklyGoalModel(
      {@JsonKey(name: 'goal_hours') required final int goalHours,
      @JsonKey(name: 'completed_hours') required final double completedHours,
      @JsonKey(name: 'progress_percentage')
      required final int progressPercentage,
      @JsonKey(name: 'lessons_completed')
      required final int lessonsCompleted}) = _$WeeklyGoalModelImpl;
  const _WeeklyGoalModel._() : super._();

  factory _WeeklyGoalModel.fromJson(Map<String, dynamic> json) =
      _$WeeklyGoalModelImpl.fromJson;

  @override
  @JsonKey(name: 'goal_hours')
  int get goalHours;
  @override
  @JsonKey(name: 'completed_hours')
  double get completedHours;
  @override
  @JsonKey(name: 'progress_percentage')
  int get progressPercentage;
  @override
  @JsonKey(name: 'lessons_completed')
  int get lessonsCompleted;

  /// Create a copy of WeeklyGoalModel
  /// with the given fields replaced by the non-null parameter values.
  @override
  @JsonKey(includeFromJson: false, includeToJson: false)
  _$$WeeklyGoalModelImplCopyWith<_$WeeklyGoalModelImpl> get copyWith =>
      throw _privateConstructorUsedError;
}
