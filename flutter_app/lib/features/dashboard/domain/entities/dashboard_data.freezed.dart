// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint
// ignore_for_file: unused_element, deprecated_member_use, deprecated_member_use_from_same_package, use_function_type_syntax_for_parameters, unnecessary_const, avoid_init_to_null, invalid_override_different_default_values_named, prefer_expression_function_bodies, annotate_overrides, invalid_annotation_target, unnecessary_question_mark

part of 'dashboard_data.dart';

// **************************************************************************
// FreezedGenerator
// **************************************************************************

T _$identity<T>(T value) => value;

final _privateConstructorUsedError = UnsupportedError(
    'It seems like you constructed your class using `MyClass._()`. This constructor is only meant to be used by freezed and you are not supposed to need it nor use it.\nPlease check the documentation here for more information: https://github.com/rrousselGit/freezed#adding-getters-and-methods-to-our-models');

/// @nodoc
mixin _$DashboardData {
  DashboardStats get stats => throw _privateConstructorUsedError;
  List<DashboardCourse> get enrolledCourses =>
      throw _privateConstructorUsedError;
  List<RecentActivity> get recentActivity => throw _privateConstructorUsedError;
  List<StudentInternship> get internships => throw _privateConstructorUsedError;
  WeeklyGoal? get weeklyGoal => throw _privateConstructorUsedError;

  /// Create a copy of DashboardData
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  $DashboardDataCopyWith<DashboardData> get copyWith =>
      throw _privateConstructorUsedError;
}

/// @nodoc
abstract class $DashboardDataCopyWith<$Res> {
  factory $DashboardDataCopyWith(
          DashboardData value, $Res Function(DashboardData) then) =
      _$DashboardDataCopyWithImpl<$Res, DashboardData>;
  @useResult
  $Res call(
      {DashboardStats stats,
      List<DashboardCourse> enrolledCourses,
      List<RecentActivity> recentActivity,
      List<StudentInternship> internships,
      WeeklyGoal? weeklyGoal});

  $DashboardStatsCopyWith<$Res> get stats;
  $WeeklyGoalCopyWith<$Res>? get weeklyGoal;
}

/// @nodoc
class _$DashboardDataCopyWithImpl<$Res, $Val extends DashboardData>
    implements $DashboardDataCopyWith<$Res> {
  _$DashboardDataCopyWithImpl(this._value, this._then);

  // ignore: unused_field
  final $Val _value;
  // ignore: unused_field
  final $Res Function($Val) _then;

  /// Create a copy of DashboardData
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
              as DashboardStats,
      enrolledCourses: null == enrolledCourses
          ? _value.enrolledCourses
          : enrolledCourses // ignore: cast_nullable_to_non_nullable
              as List<DashboardCourse>,
      recentActivity: null == recentActivity
          ? _value.recentActivity
          : recentActivity // ignore: cast_nullable_to_non_nullable
              as List<RecentActivity>,
      internships: null == internships
          ? _value.internships
          : internships // ignore: cast_nullable_to_non_nullable
              as List<StudentInternship>,
      weeklyGoal: freezed == weeklyGoal
          ? _value.weeklyGoal
          : weeklyGoal // ignore: cast_nullable_to_non_nullable
              as WeeklyGoal?,
    ) as $Val);
  }

  /// Create a copy of DashboardData
  /// with the given fields replaced by the non-null parameter values.
  @override
  @pragma('vm:prefer-inline')
  $DashboardStatsCopyWith<$Res> get stats {
    return $DashboardStatsCopyWith<$Res>(_value.stats, (value) {
      return _then(_value.copyWith(stats: value) as $Val);
    });
  }

  /// Create a copy of DashboardData
  /// with the given fields replaced by the non-null parameter values.
  @override
  @pragma('vm:prefer-inline')
  $WeeklyGoalCopyWith<$Res>? get weeklyGoal {
    if (_value.weeklyGoal == null) {
      return null;
    }

    return $WeeklyGoalCopyWith<$Res>(_value.weeklyGoal!, (value) {
      return _then(_value.copyWith(weeklyGoal: value) as $Val);
    });
  }
}

/// @nodoc
abstract class _$$DashboardDataImplCopyWith<$Res>
    implements $DashboardDataCopyWith<$Res> {
  factory _$$DashboardDataImplCopyWith(
          _$DashboardDataImpl value, $Res Function(_$DashboardDataImpl) then) =
      __$$DashboardDataImplCopyWithImpl<$Res>;
  @override
  @useResult
  $Res call(
      {DashboardStats stats,
      List<DashboardCourse> enrolledCourses,
      List<RecentActivity> recentActivity,
      List<StudentInternship> internships,
      WeeklyGoal? weeklyGoal});

  @override
  $DashboardStatsCopyWith<$Res> get stats;
  @override
  $WeeklyGoalCopyWith<$Res>? get weeklyGoal;
}

/// @nodoc
class __$$DashboardDataImplCopyWithImpl<$Res>
    extends _$DashboardDataCopyWithImpl<$Res, _$DashboardDataImpl>
    implements _$$DashboardDataImplCopyWith<$Res> {
  __$$DashboardDataImplCopyWithImpl(
      _$DashboardDataImpl _value, $Res Function(_$DashboardDataImpl) _then)
      : super(_value, _then);

  /// Create a copy of DashboardData
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
    return _then(_$DashboardDataImpl(
      stats: null == stats
          ? _value.stats
          : stats // ignore: cast_nullable_to_non_nullable
              as DashboardStats,
      enrolledCourses: null == enrolledCourses
          ? _value._enrolledCourses
          : enrolledCourses // ignore: cast_nullable_to_non_nullable
              as List<DashboardCourse>,
      recentActivity: null == recentActivity
          ? _value._recentActivity
          : recentActivity // ignore: cast_nullable_to_non_nullable
              as List<RecentActivity>,
      internships: null == internships
          ? _value._internships
          : internships // ignore: cast_nullable_to_non_nullable
              as List<StudentInternship>,
      weeklyGoal: freezed == weeklyGoal
          ? _value.weeklyGoal
          : weeklyGoal // ignore: cast_nullable_to_non_nullable
              as WeeklyGoal?,
    ));
  }
}

/// @nodoc

class _$DashboardDataImpl implements _DashboardData {
  const _$DashboardDataImpl(
      {required this.stats,
      required final List<DashboardCourse> enrolledCourses,
      required final List<RecentActivity> recentActivity,
      final List<StudentInternship> internships = const [],
      this.weeklyGoal})
      : _enrolledCourses = enrolledCourses,
        _recentActivity = recentActivity,
        _internships = internships;

  @override
  final DashboardStats stats;
  final List<DashboardCourse> _enrolledCourses;
  @override
  List<DashboardCourse> get enrolledCourses {
    if (_enrolledCourses is EqualUnmodifiableListView) return _enrolledCourses;
    // ignore: implicit_dynamic_type
    return EqualUnmodifiableListView(_enrolledCourses);
  }

  final List<RecentActivity> _recentActivity;
  @override
  List<RecentActivity> get recentActivity {
    if (_recentActivity is EqualUnmodifiableListView) return _recentActivity;
    // ignore: implicit_dynamic_type
    return EqualUnmodifiableListView(_recentActivity);
  }

  final List<StudentInternship> _internships;
  @override
  @JsonKey()
  List<StudentInternship> get internships {
    if (_internships is EqualUnmodifiableListView) return _internships;
    // ignore: implicit_dynamic_type
    return EqualUnmodifiableListView(_internships);
  }

  @override
  final WeeklyGoal? weeklyGoal;

  @override
  String toString() {
    return 'DashboardData(stats: $stats, enrolledCourses: $enrolledCourses, recentActivity: $recentActivity, internships: $internships, weeklyGoal: $weeklyGoal)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$DashboardDataImpl &&
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

  @override
  int get hashCode => Object.hash(
      runtimeType,
      stats,
      const DeepCollectionEquality().hash(_enrolledCourses),
      const DeepCollectionEquality().hash(_recentActivity),
      const DeepCollectionEquality().hash(_internships),
      weeklyGoal);

  /// Create a copy of DashboardData
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  @pragma('vm:prefer-inline')
  _$$DashboardDataImplCopyWith<_$DashboardDataImpl> get copyWith =>
      __$$DashboardDataImplCopyWithImpl<_$DashboardDataImpl>(this, _$identity);
}

abstract class _DashboardData implements DashboardData {
  const factory _DashboardData(
      {required final DashboardStats stats,
      required final List<DashboardCourse> enrolledCourses,
      required final List<RecentActivity> recentActivity,
      final List<StudentInternship> internships,
      final WeeklyGoal? weeklyGoal}) = _$DashboardDataImpl;

  @override
  DashboardStats get stats;
  @override
  List<DashboardCourse> get enrolledCourses;
  @override
  List<RecentActivity> get recentActivity;
  @override
  List<StudentInternship> get internships;
  @override
  WeeklyGoal? get weeklyGoal;

  /// Create a copy of DashboardData
  /// with the given fields replaced by the non-null parameter values.
  @override
  @JsonKey(includeFromJson: false, includeToJson: false)
  _$$DashboardDataImplCopyWith<_$DashboardDataImpl> get copyWith =>
      throw _privateConstructorUsedError;
}

/// @nodoc
mixin _$DashboardCourse {
  String get id => throw _privateConstructorUsedError;
  String get title => throw _privateConstructorUsedError;
  String get thumbnail => throw _privateConstructorUsedError;
  double get progress => throw _privateConstructorUsedError;
  int get totalLessons => throw _privateConstructorUsedError;
  int get completedLessons => throw _privateConstructorUsedError;
  String get instructorName => throw _privateConstructorUsedError;
  double get rating => throw _privateConstructorUsedError;
  String get nextLesson => throw _privateConstructorUsedError;
  String get enrollmentStatus => throw _privateConstructorUsedError;

  /// Create a copy of DashboardCourse
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  $DashboardCourseCopyWith<DashboardCourse> get copyWith =>
      throw _privateConstructorUsedError;
}

/// @nodoc
abstract class $DashboardCourseCopyWith<$Res> {
  factory $DashboardCourseCopyWith(
          DashboardCourse value, $Res Function(DashboardCourse) then) =
      _$DashboardCourseCopyWithImpl<$Res, DashboardCourse>;
  @useResult
  $Res call(
      {String id,
      String title,
      String thumbnail,
      double progress,
      int totalLessons,
      int completedLessons,
      String instructorName,
      double rating,
      String nextLesson,
      String enrollmentStatus});
}

/// @nodoc
class _$DashboardCourseCopyWithImpl<$Res, $Val extends DashboardCourse>
    implements $DashboardCourseCopyWith<$Res> {
  _$DashboardCourseCopyWithImpl(this._value, this._then);

  // ignore: unused_field
  final $Val _value;
  // ignore: unused_field
  final $Res Function($Val) _then;

  /// Create a copy of DashboardCourse
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
    Object? instructorName = null,
    Object? rating = null,
    Object? nextLesson = null,
    Object? enrollmentStatus = null,
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
      instructorName: null == instructorName
          ? _value.instructorName
          : instructorName // ignore: cast_nullable_to_non_nullable
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
abstract class _$$DashboardCourseImplCopyWith<$Res>
    implements $DashboardCourseCopyWith<$Res> {
  factory _$$DashboardCourseImplCopyWith(_$DashboardCourseImpl value,
          $Res Function(_$DashboardCourseImpl) then) =
      __$$DashboardCourseImplCopyWithImpl<$Res>;
  @override
  @useResult
  $Res call(
      {String id,
      String title,
      String thumbnail,
      double progress,
      int totalLessons,
      int completedLessons,
      String instructorName,
      double rating,
      String nextLesson,
      String enrollmentStatus});
}

/// @nodoc
class __$$DashboardCourseImplCopyWithImpl<$Res>
    extends _$DashboardCourseCopyWithImpl<$Res, _$DashboardCourseImpl>
    implements _$$DashboardCourseImplCopyWith<$Res> {
  __$$DashboardCourseImplCopyWithImpl(
      _$DashboardCourseImpl _value, $Res Function(_$DashboardCourseImpl) _then)
      : super(_value, _then);

  /// Create a copy of DashboardCourse
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
    Object? instructorName = null,
    Object? rating = null,
    Object? nextLesson = null,
    Object? enrollmentStatus = null,
  }) {
    return _then(_$DashboardCourseImpl(
      id: null == id
          ? _value.id
          : id // ignore: cast_nullable_to_non_nullable
              as String,
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
      instructorName: null == instructorName
          ? _value.instructorName
          : instructorName // ignore: cast_nullable_to_non_nullable
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

class _$DashboardCourseImpl implements _DashboardCourse {
  const _$DashboardCourseImpl(
      {required this.id,
      required this.title,
      required this.thumbnail,
      required this.progress,
      required this.totalLessons,
      required this.completedLessons,
      required this.instructorName,
      required this.rating,
      required this.nextLesson,
      required this.enrollmentStatus});

  @override
  final String id;
  @override
  final String title;
  @override
  final String thumbnail;
  @override
  final double progress;
  @override
  final int totalLessons;
  @override
  final int completedLessons;
  @override
  final String instructorName;
  @override
  final double rating;
  @override
  final String nextLesson;
  @override
  final String enrollmentStatus;

  @override
  String toString() {
    return 'DashboardCourse(id: $id, title: $title, thumbnail: $thumbnail, progress: $progress, totalLessons: $totalLessons, completedLessons: $completedLessons, instructorName: $instructorName, rating: $rating, nextLesson: $nextLesson, enrollmentStatus: $enrollmentStatus)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$DashboardCourseImpl &&
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
            (identical(other.instructorName, instructorName) ||
                other.instructorName == instructorName) &&
            (identical(other.rating, rating) || other.rating == rating) &&
            (identical(other.nextLesson, nextLesson) ||
                other.nextLesson == nextLesson) &&
            (identical(other.enrollmentStatus, enrollmentStatus) ||
                other.enrollmentStatus == enrollmentStatus));
  }

  @override
  int get hashCode => Object.hash(
      runtimeType,
      id,
      title,
      thumbnail,
      progress,
      totalLessons,
      completedLessons,
      instructorName,
      rating,
      nextLesson,
      enrollmentStatus);

  /// Create a copy of DashboardCourse
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  @pragma('vm:prefer-inline')
  _$$DashboardCourseImplCopyWith<_$DashboardCourseImpl> get copyWith =>
      __$$DashboardCourseImplCopyWithImpl<_$DashboardCourseImpl>(
          this, _$identity);
}

abstract class _DashboardCourse implements DashboardCourse {
  const factory _DashboardCourse(
      {required final String id,
      required final String title,
      required final String thumbnail,
      required final double progress,
      required final int totalLessons,
      required final int completedLessons,
      required final String instructorName,
      required final double rating,
      required final String nextLesson,
      required final String enrollmentStatus}) = _$DashboardCourseImpl;

  @override
  String get id;
  @override
  String get title;
  @override
  String get thumbnail;
  @override
  double get progress;
  @override
  int get totalLessons;
  @override
  int get completedLessons;
  @override
  String get instructorName;
  @override
  double get rating;
  @override
  String get nextLesson;
  @override
  String get enrollmentStatus;

  /// Create a copy of DashboardCourse
  /// with the given fields replaced by the non-null parameter values.
  @override
  @JsonKey(includeFromJson: false, includeToJson: false)
  _$$DashboardCourseImplCopyWith<_$DashboardCourseImpl> get copyWith =>
      throw _privateConstructorUsedError;
}

/// @nodoc
mixin _$DashboardStats {
  int get enrolledCourses => throw _privateConstructorUsedError;
  int get completedCourses => throw _privateConstructorUsedError;
  int get totalHours => throw _privateConstructorUsedError;
  int get certificates => throw _privateConstructorUsedError;

  /// Create a copy of DashboardStats
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  $DashboardStatsCopyWith<DashboardStats> get copyWith =>
      throw _privateConstructorUsedError;
}

/// @nodoc
abstract class $DashboardStatsCopyWith<$Res> {
  factory $DashboardStatsCopyWith(
          DashboardStats value, $Res Function(DashboardStats) then) =
      _$DashboardStatsCopyWithImpl<$Res, DashboardStats>;
  @useResult
  $Res call(
      {int enrolledCourses,
      int completedCourses,
      int totalHours,
      int certificates});
}

/// @nodoc
class _$DashboardStatsCopyWithImpl<$Res, $Val extends DashboardStats>
    implements $DashboardStatsCopyWith<$Res> {
  _$DashboardStatsCopyWithImpl(this._value, this._then);

  // ignore: unused_field
  final $Val _value;
  // ignore: unused_field
  final $Res Function($Val) _then;

  /// Create a copy of DashboardStats
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
abstract class _$$DashboardStatsImplCopyWith<$Res>
    implements $DashboardStatsCopyWith<$Res> {
  factory _$$DashboardStatsImplCopyWith(_$DashboardStatsImpl value,
          $Res Function(_$DashboardStatsImpl) then) =
      __$$DashboardStatsImplCopyWithImpl<$Res>;
  @override
  @useResult
  $Res call(
      {int enrolledCourses,
      int completedCourses,
      int totalHours,
      int certificates});
}

/// @nodoc
class __$$DashboardStatsImplCopyWithImpl<$Res>
    extends _$DashboardStatsCopyWithImpl<$Res, _$DashboardStatsImpl>
    implements _$$DashboardStatsImplCopyWith<$Res> {
  __$$DashboardStatsImplCopyWithImpl(
      _$DashboardStatsImpl _value, $Res Function(_$DashboardStatsImpl) _then)
      : super(_value, _then);

  /// Create a copy of DashboardStats
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? enrolledCourses = null,
    Object? completedCourses = null,
    Object? totalHours = null,
    Object? certificates = null,
  }) {
    return _then(_$DashboardStatsImpl(
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

class _$DashboardStatsImpl implements _DashboardStats {
  const _$DashboardStatsImpl(
      {required this.enrolledCourses,
      required this.completedCourses,
      required this.totalHours,
      required this.certificates});

  @override
  final int enrolledCourses;
  @override
  final int completedCourses;
  @override
  final int totalHours;
  @override
  final int certificates;

  @override
  String toString() {
    return 'DashboardStats(enrolledCourses: $enrolledCourses, completedCourses: $completedCourses, totalHours: $totalHours, certificates: $certificates)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$DashboardStatsImpl &&
            (identical(other.enrolledCourses, enrolledCourses) ||
                other.enrolledCourses == enrolledCourses) &&
            (identical(other.completedCourses, completedCourses) ||
                other.completedCourses == completedCourses) &&
            (identical(other.totalHours, totalHours) ||
                other.totalHours == totalHours) &&
            (identical(other.certificates, certificates) ||
                other.certificates == certificates));
  }

  @override
  int get hashCode => Object.hash(
      runtimeType, enrolledCourses, completedCourses, totalHours, certificates);

  /// Create a copy of DashboardStats
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  @pragma('vm:prefer-inline')
  _$$DashboardStatsImplCopyWith<_$DashboardStatsImpl> get copyWith =>
      __$$DashboardStatsImplCopyWithImpl<_$DashboardStatsImpl>(
          this, _$identity);
}

abstract class _DashboardStats implements DashboardStats {
  const factory _DashboardStats(
      {required final int enrolledCourses,
      required final int completedCourses,
      required final int totalHours,
      required final int certificates}) = _$DashboardStatsImpl;

  @override
  int get enrolledCourses;
  @override
  int get completedCourses;
  @override
  int get totalHours;
  @override
  int get certificates;

  /// Create a copy of DashboardStats
  /// with the given fields replaced by the non-null parameter values.
  @override
  @JsonKey(includeFromJson: false, includeToJson: false)
  _$$DashboardStatsImplCopyWith<_$DashboardStatsImpl> get copyWith =>
      throw _privateConstructorUsedError;
}

/// @nodoc
mixin _$RecentActivity {
  String get type => throw _privateConstructorUsedError;
  String get action => throw _privateConstructorUsedError;
  String get title => throw _privateConstructorUsedError;
  String get course => throw _privateConstructorUsedError;
  String get description => throw _privateConstructorUsedError;
  String get timestamp => throw _privateConstructorUsedError;
  String get time => throw _privateConstructorUsedError;

  /// Create a copy of RecentActivity
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  $RecentActivityCopyWith<RecentActivity> get copyWith =>
      throw _privateConstructorUsedError;
}

/// @nodoc
abstract class $RecentActivityCopyWith<$Res> {
  factory $RecentActivityCopyWith(
          RecentActivity value, $Res Function(RecentActivity) then) =
      _$RecentActivityCopyWithImpl<$Res, RecentActivity>;
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
class _$RecentActivityCopyWithImpl<$Res, $Val extends RecentActivity>
    implements $RecentActivityCopyWith<$Res> {
  _$RecentActivityCopyWithImpl(this._value, this._then);

  // ignore: unused_field
  final $Val _value;
  // ignore: unused_field
  final $Res Function($Val) _then;

  /// Create a copy of RecentActivity
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
abstract class _$$RecentActivityImplCopyWith<$Res>
    implements $RecentActivityCopyWith<$Res> {
  factory _$$RecentActivityImplCopyWith(_$RecentActivityImpl value,
          $Res Function(_$RecentActivityImpl) then) =
      __$$RecentActivityImplCopyWithImpl<$Res>;
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
class __$$RecentActivityImplCopyWithImpl<$Res>
    extends _$RecentActivityCopyWithImpl<$Res, _$RecentActivityImpl>
    implements _$$RecentActivityImplCopyWith<$Res> {
  __$$RecentActivityImplCopyWithImpl(
      _$RecentActivityImpl _value, $Res Function(_$RecentActivityImpl) _then)
      : super(_value, _then);

  /// Create a copy of RecentActivity
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
    return _then(_$RecentActivityImpl(
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

class _$RecentActivityImpl implements _RecentActivity {
  const _$RecentActivityImpl(
      {required this.type,
      required this.action,
      required this.title,
      required this.course,
      required this.description,
      required this.timestamp,
      required this.time});

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
    return 'RecentActivity(type: $type, action: $action, title: $title, course: $course, description: $description, timestamp: $timestamp, time: $time)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$RecentActivityImpl &&
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

  @override
  int get hashCode => Object.hash(
      runtimeType, type, action, title, course, description, timestamp, time);

  /// Create a copy of RecentActivity
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  @pragma('vm:prefer-inline')
  _$$RecentActivityImplCopyWith<_$RecentActivityImpl> get copyWith =>
      __$$RecentActivityImplCopyWithImpl<_$RecentActivityImpl>(
          this, _$identity);
}

abstract class _RecentActivity implements RecentActivity {
  const factory _RecentActivity(
      {required final String type,
      required final String action,
      required final String title,
      required final String course,
      required final String description,
      required final String timestamp,
      required final String time}) = _$RecentActivityImpl;

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

  /// Create a copy of RecentActivity
  /// with the given fields replaced by the non-null parameter values.
  @override
  @JsonKey(includeFromJson: false, includeToJson: false)
  _$$RecentActivityImplCopyWith<_$RecentActivityImpl> get copyWith =>
      throw _privateConstructorUsedError;
}

/// @nodoc
mixin _$StudentInternship {
  int get id => throw _privateConstructorUsedError;
  String get title => throw _privateConstructorUsedError;
  String get voucherCode => throw _privateConstructorUsedError;
  String get status => throw _privateConstructorUsedError;
  String? get redeemedCourseTitle => throw _privateConstructorUsedError;
  int get attendanceDays => throw _privateConstructorUsedError;
  String? get hiredCompany => throw _privateConstructorUsedError;
  String? get createdAt => throw _privateConstructorUsedError;

  /// Create a copy of StudentInternship
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  $StudentInternshipCopyWith<StudentInternship> get copyWith =>
      throw _privateConstructorUsedError;
}

/// @nodoc
abstract class $StudentInternshipCopyWith<$Res> {
  factory $StudentInternshipCopyWith(
          StudentInternship value, $Res Function(StudentInternship) then) =
      _$StudentInternshipCopyWithImpl<$Res, StudentInternship>;
  @useResult
  $Res call(
      {int id,
      String title,
      String voucherCode,
      String status,
      String? redeemedCourseTitle,
      int attendanceDays,
      String? hiredCompany,
      String? createdAt});
}

/// @nodoc
class _$StudentInternshipCopyWithImpl<$Res, $Val extends StudentInternship>
    implements $StudentInternshipCopyWith<$Res> {
  _$StudentInternshipCopyWithImpl(this._value, this._then);

  // ignore: unused_field
  final $Val _value;
  // ignore: unused_field
  final $Res Function($Val) _then;

  /// Create a copy of StudentInternship
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
abstract class _$$StudentInternshipImplCopyWith<$Res>
    implements $StudentInternshipCopyWith<$Res> {
  factory _$$StudentInternshipImplCopyWith(_$StudentInternshipImpl value,
          $Res Function(_$StudentInternshipImpl) then) =
      __$$StudentInternshipImplCopyWithImpl<$Res>;
  @override
  @useResult
  $Res call(
      {int id,
      String title,
      String voucherCode,
      String status,
      String? redeemedCourseTitle,
      int attendanceDays,
      String? hiredCompany,
      String? createdAt});
}

/// @nodoc
class __$$StudentInternshipImplCopyWithImpl<$Res>
    extends _$StudentInternshipCopyWithImpl<$Res, _$StudentInternshipImpl>
    implements _$$StudentInternshipImplCopyWith<$Res> {
  __$$StudentInternshipImplCopyWithImpl(_$StudentInternshipImpl _value,
      $Res Function(_$StudentInternshipImpl) _then)
      : super(_value, _then);

  /// Create a copy of StudentInternship
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
    return _then(_$StudentInternshipImpl(
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

class _$StudentInternshipImpl implements _StudentInternship {
  const _$StudentInternshipImpl(
      {required this.id,
      required this.title,
      required this.voucherCode,
      required this.status,
      this.redeemedCourseTitle,
      required this.attendanceDays,
      this.hiredCompany,
      this.createdAt});

  @override
  final int id;
  @override
  final String title;
  @override
  final String voucherCode;
  @override
  final String status;
  @override
  final String? redeemedCourseTitle;
  @override
  final int attendanceDays;
  @override
  final String? hiredCompany;
  @override
  final String? createdAt;

  @override
  String toString() {
    return 'StudentInternship(id: $id, title: $title, voucherCode: $voucherCode, status: $status, redeemedCourseTitle: $redeemedCourseTitle, attendanceDays: $attendanceDays, hiredCompany: $hiredCompany, createdAt: $createdAt)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$StudentInternshipImpl &&
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

  @override
  int get hashCode => Object.hash(runtimeType, id, title, voucherCode, status,
      redeemedCourseTitle, attendanceDays, hiredCompany, createdAt);

  /// Create a copy of StudentInternship
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  @pragma('vm:prefer-inline')
  _$$StudentInternshipImplCopyWith<_$StudentInternshipImpl> get copyWith =>
      __$$StudentInternshipImplCopyWithImpl<_$StudentInternshipImpl>(
          this, _$identity);
}

abstract class _StudentInternship implements StudentInternship {
  const factory _StudentInternship(
      {required final int id,
      required final String title,
      required final String voucherCode,
      required final String status,
      final String? redeemedCourseTitle,
      required final int attendanceDays,
      final String? hiredCompany,
      final String? createdAt}) = _$StudentInternshipImpl;

  @override
  int get id;
  @override
  String get title;
  @override
  String get voucherCode;
  @override
  String get status;
  @override
  String? get redeemedCourseTitle;
  @override
  int get attendanceDays;
  @override
  String? get hiredCompany;
  @override
  String? get createdAt;

  /// Create a copy of StudentInternship
  /// with the given fields replaced by the non-null parameter values.
  @override
  @JsonKey(includeFromJson: false, includeToJson: false)
  _$$StudentInternshipImplCopyWith<_$StudentInternshipImpl> get copyWith =>
      throw _privateConstructorUsedError;
}

/// @nodoc
mixin _$WeeklyGoal {
  int get goalHours => throw _privateConstructorUsedError;
  double get completedHours => throw _privateConstructorUsedError;
  int get progressPercentage => throw _privateConstructorUsedError;
  int get lessonsCompleted => throw _privateConstructorUsedError;

  /// Create a copy of WeeklyGoal
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  $WeeklyGoalCopyWith<WeeklyGoal> get copyWith =>
      throw _privateConstructorUsedError;
}

/// @nodoc
abstract class $WeeklyGoalCopyWith<$Res> {
  factory $WeeklyGoalCopyWith(
          WeeklyGoal value, $Res Function(WeeklyGoal) then) =
      _$WeeklyGoalCopyWithImpl<$Res, WeeklyGoal>;
  @useResult
  $Res call(
      {int goalHours,
      double completedHours,
      int progressPercentage,
      int lessonsCompleted});
}

/// @nodoc
class _$WeeklyGoalCopyWithImpl<$Res, $Val extends WeeklyGoal>
    implements $WeeklyGoalCopyWith<$Res> {
  _$WeeklyGoalCopyWithImpl(this._value, this._then);

  // ignore: unused_field
  final $Val _value;
  // ignore: unused_field
  final $Res Function($Val) _then;

  /// Create a copy of WeeklyGoal
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
abstract class _$$WeeklyGoalImplCopyWith<$Res>
    implements $WeeklyGoalCopyWith<$Res> {
  factory _$$WeeklyGoalImplCopyWith(
          _$WeeklyGoalImpl value, $Res Function(_$WeeklyGoalImpl) then) =
      __$$WeeklyGoalImplCopyWithImpl<$Res>;
  @override
  @useResult
  $Res call(
      {int goalHours,
      double completedHours,
      int progressPercentage,
      int lessonsCompleted});
}

/// @nodoc
class __$$WeeklyGoalImplCopyWithImpl<$Res>
    extends _$WeeklyGoalCopyWithImpl<$Res, _$WeeklyGoalImpl>
    implements _$$WeeklyGoalImplCopyWith<$Res> {
  __$$WeeklyGoalImplCopyWithImpl(
      _$WeeklyGoalImpl _value, $Res Function(_$WeeklyGoalImpl) _then)
      : super(_value, _then);

  /// Create a copy of WeeklyGoal
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? goalHours = null,
    Object? completedHours = null,
    Object? progressPercentage = null,
    Object? lessonsCompleted = null,
  }) {
    return _then(_$WeeklyGoalImpl(
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

class _$WeeklyGoalImpl implements _WeeklyGoal {
  const _$WeeklyGoalImpl(
      {required this.goalHours,
      required this.completedHours,
      required this.progressPercentage,
      required this.lessonsCompleted});

  @override
  final int goalHours;
  @override
  final double completedHours;
  @override
  final int progressPercentage;
  @override
  final int lessonsCompleted;

  @override
  String toString() {
    return 'WeeklyGoal(goalHours: $goalHours, completedHours: $completedHours, progressPercentage: $progressPercentage, lessonsCompleted: $lessonsCompleted)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$WeeklyGoalImpl &&
            (identical(other.goalHours, goalHours) ||
                other.goalHours == goalHours) &&
            (identical(other.completedHours, completedHours) ||
                other.completedHours == completedHours) &&
            (identical(other.progressPercentage, progressPercentage) ||
                other.progressPercentage == progressPercentage) &&
            (identical(other.lessonsCompleted, lessonsCompleted) ||
                other.lessonsCompleted == lessonsCompleted));
  }

  @override
  int get hashCode => Object.hash(runtimeType, goalHours, completedHours,
      progressPercentage, lessonsCompleted);

  /// Create a copy of WeeklyGoal
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  @pragma('vm:prefer-inline')
  _$$WeeklyGoalImplCopyWith<_$WeeklyGoalImpl> get copyWith =>
      __$$WeeklyGoalImplCopyWithImpl<_$WeeklyGoalImpl>(this, _$identity);
}

abstract class _WeeklyGoal implements WeeklyGoal {
  const factory _WeeklyGoal(
      {required final int goalHours,
      required final double completedHours,
      required final int progressPercentage,
      required final int lessonsCompleted}) = _$WeeklyGoalImpl;

  @override
  int get goalHours;
  @override
  double get completedHours;
  @override
  int get progressPercentage;
  @override
  int get lessonsCompleted;

  /// Create a copy of WeeklyGoal
  /// with the given fields replaced by the non-null parameter values.
  @override
  @JsonKey(includeFromJson: false, includeToJson: false)
  _$$WeeklyGoalImplCopyWith<_$WeeklyGoalImpl> get copyWith =>
      throw _privateConstructorUsedError;
}
