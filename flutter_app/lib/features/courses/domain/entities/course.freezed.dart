// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint
// ignore_for_file: unused_element, deprecated_member_use, deprecated_member_use_from_same_package, use_function_type_syntax_for_parameters, unnecessary_const, avoid_init_to_null, invalid_override_different_default_values_named, prefer_expression_function_bodies, annotate_overrides, invalid_annotation_target, unnecessary_question_mark

part of 'course.dart';

// **************************************************************************
// FreezedGenerator
// **************************************************************************

T _$identity<T>(T value) => value;

final _privateConstructorUsedError = UnsupportedError(
    'It seems like you constructed your class using `MyClass._()`. This constructor is only meant to be used by freezed and you are not supposed to need it nor use it.\nPlease check the documentation here for more information: https://github.com/rrousselGit/freezed#adding-getters-and-methods-to-our-models');

/// @nodoc
mixin _$Course {
  String get id => throw _privateConstructorUsedError;
  String get title => throw _privateConstructorUsedError;
  String get description => throw _privateConstructorUsedError;
  String? get content => throw _privateConstructorUsedError;
  String get featuredImage => throw _privateConstructorUsedError;
  String? get introVideo => throw _privateConstructorUsedError;
  double get price => throw _privateConstructorUsedError;
  double? get salePrice => throw _privateConstructorUsedError;
  String get level => throw _privateConstructorUsedError;
  String get category => throw _privateConstructorUsedError;
  Instructor get instructor => throw _privateConstructorUsedError;
  CourseStats get stats => throw _privateConstructorUsedError;
  double get rating => throw _privateConstructorUsedError;
  bool get isEnrolled => throw _privateConstructorUsedError;
  int get numOfflineWorkshops => throw _privateConstructorUsedError;
  int get numHours => throw _privateConstructorUsedError;
  String? get institution => throw _privateConstructorUsedError;
  DateTime get createdAt => throw _privateConstructorUsedError;
  DateTime get updatedAt => throw _privateConstructorUsedError;
  String? get slug => throw _privateConstructorUsedError;
  List<Lesson> get lessons => throw _privateConstructorUsedError;
  List<Quiz> get quizzes => throw _privateConstructorUsedError;
  List<Assignment> get assignments => throw _privateConstructorUsedError;
  double get progress => throw _privateConstructorUsedError;
  List<String> get requirements => throw _privateConstructorUsedError;
  List<String> get benefits => throw _privateConstructorUsedError;
  List<String> get targetAudience => throw _privateConstructorUsedError;
  List<String> get materialIncludes => throw _privateConstructorUsedError;
  List<String> get tags => throw _privateConstructorUsedError;

  /// Create a copy of Course
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  $CourseCopyWith<Course> get copyWith => throw _privateConstructorUsedError;
}

/// @nodoc
abstract class $CourseCopyWith<$Res> {
  factory $CourseCopyWith(Course value, $Res Function(Course) then) =
      _$CourseCopyWithImpl<$Res, Course>;
  @useResult
  $Res call(
      {String id,
      String title,
      String description,
      String? content,
      String featuredImage,
      String? introVideo,
      double price,
      double? salePrice,
      String level,
      String category,
      Instructor instructor,
      CourseStats stats,
      double rating,
      bool isEnrolled,
      int numOfflineWorkshops,
      int numHours,
      String? institution,
      DateTime createdAt,
      DateTime updatedAt,
      String? slug,
      List<Lesson> lessons,
      List<Quiz> quizzes,
      List<Assignment> assignments,
      double progress,
      List<String> requirements,
      List<String> benefits,
      List<String> targetAudience,
      List<String> materialIncludes,
      List<String> tags});

  $InstructorCopyWith<$Res> get instructor;
  $CourseStatsCopyWith<$Res> get stats;
}

/// @nodoc
class _$CourseCopyWithImpl<$Res, $Val extends Course>
    implements $CourseCopyWith<$Res> {
  _$CourseCopyWithImpl(this._value, this._then);

  // ignore: unused_field
  final $Val _value;
  // ignore: unused_field
  final $Res Function($Val) _then;

  /// Create a copy of Course
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? id = null,
    Object? title = null,
    Object? description = null,
    Object? content = freezed,
    Object? featuredImage = null,
    Object? introVideo = freezed,
    Object? price = null,
    Object? salePrice = freezed,
    Object? level = null,
    Object? category = null,
    Object? instructor = null,
    Object? stats = null,
    Object? rating = null,
    Object? isEnrolled = null,
    Object? numOfflineWorkshops = null,
    Object? numHours = null,
    Object? institution = freezed,
    Object? createdAt = null,
    Object? updatedAt = null,
    Object? slug = freezed,
    Object? lessons = null,
    Object? quizzes = null,
    Object? assignments = null,
    Object? progress = null,
    Object? requirements = null,
    Object? benefits = null,
    Object? targetAudience = null,
    Object? materialIncludes = null,
    Object? tags = null,
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
      description: null == description
          ? _value.description
          : description // ignore: cast_nullable_to_non_nullable
              as String,
      content: freezed == content
          ? _value.content
          : content // ignore: cast_nullable_to_non_nullable
              as String?,
      featuredImage: null == featuredImage
          ? _value.featuredImage
          : featuredImage // ignore: cast_nullable_to_non_nullable
              as String,
      introVideo: freezed == introVideo
          ? _value.introVideo
          : introVideo // ignore: cast_nullable_to_non_nullable
              as String?,
      price: null == price
          ? _value.price
          : price // ignore: cast_nullable_to_non_nullable
              as double,
      salePrice: freezed == salePrice
          ? _value.salePrice
          : salePrice // ignore: cast_nullable_to_non_nullable
              as double?,
      level: null == level
          ? _value.level
          : level // ignore: cast_nullable_to_non_nullable
              as String,
      category: null == category
          ? _value.category
          : category // ignore: cast_nullable_to_non_nullable
              as String,
      instructor: null == instructor
          ? _value.instructor
          : instructor // ignore: cast_nullable_to_non_nullable
              as Instructor,
      stats: null == stats
          ? _value.stats
          : stats // ignore: cast_nullable_to_non_nullable
              as CourseStats,
      rating: null == rating
          ? _value.rating
          : rating // ignore: cast_nullable_to_non_nullable
              as double,
      isEnrolled: null == isEnrolled
          ? _value.isEnrolled
          : isEnrolled // ignore: cast_nullable_to_non_nullable
              as bool,
      numOfflineWorkshops: null == numOfflineWorkshops
          ? _value.numOfflineWorkshops
          : numOfflineWorkshops // ignore: cast_nullable_to_non_nullable
              as int,
      numHours: null == numHours
          ? _value.numHours
          : numHours // ignore: cast_nullable_to_non_nullable
              as int,
      institution: freezed == institution
          ? _value.institution
          : institution // ignore: cast_nullable_to_non_nullable
              as String?,
      createdAt: null == createdAt
          ? _value.createdAt
          : createdAt // ignore: cast_nullable_to_non_nullable
              as DateTime,
      updatedAt: null == updatedAt
          ? _value.updatedAt
          : updatedAt // ignore: cast_nullable_to_non_nullable
              as DateTime,
      slug: freezed == slug
          ? _value.slug
          : slug // ignore: cast_nullable_to_non_nullable
              as String?,
      lessons: null == lessons
          ? _value.lessons
          : lessons // ignore: cast_nullable_to_non_nullable
              as List<Lesson>,
      quizzes: null == quizzes
          ? _value.quizzes
          : quizzes // ignore: cast_nullable_to_non_nullable
              as List<Quiz>,
      assignments: null == assignments
          ? _value.assignments
          : assignments // ignore: cast_nullable_to_non_nullable
              as List<Assignment>,
      progress: null == progress
          ? _value.progress
          : progress // ignore: cast_nullable_to_non_nullable
              as double,
      requirements: null == requirements
          ? _value.requirements
          : requirements // ignore: cast_nullable_to_non_nullable
              as List<String>,
      benefits: null == benefits
          ? _value.benefits
          : benefits // ignore: cast_nullable_to_non_nullable
              as List<String>,
      targetAudience: null == targetAudience
          ? _value.targetAudience
          : targetAudience // ignore: cast_nullable_to_non_nullable
              as List<String>,
      materialIncludes: null == materialIncludes
          ? _value.materialIncludes
          : materialIncludes // ignore: cast_nullable_to_non_nullable
              as List<String>,
      tags: null == tags
          ? _value.tags
          : tags // ignore: cast_nullable_to_non_nullable
              as List<String>,
    ) as $Val);
  }

  /// Create a copy of Course
  /// with the given fields replaced by the non-null parameter values.
  @override
  @pragma('vm:prefer-inline')
  $InstructorCopyWith<$Res> get instructor {
    return $InstructorCopyWith<$Res>(_value.instructor, (value) {
      return _then(_value.copyWith(instructor: value) as $Val);
    });
  }

  /// Create a copy of Course
  /// with the given fields replaced by the non-null parameter values.
  @override
  @pragma('vm:prefer-inline')
  $CourseStatsCopyWith<$Res> get stats {
    return $CourseStatsCopyWith<$Res>(_value.stats, (value) {
      return _then(_value.copyWith(stats: value) as $Val);
    });
  }
}

/// @nodoc
abstract class _$$CourseImplCopyWith<$Res> implements $CourseCopyWith<$Res> {
  factory _$$CourseImplCopyWith(
          _$CourseImpl value, $Res Function(_$CourseImpl) then) =
      __$$CourseImplCopyWithImpl<$Res>;
  @override
  @useResult
  $Res call(
      {String id,
      String title,
      String description,
      String? content,
      String featuredImage,
      String? introVideo,
      double price,
      double? salePrice,
      String level,
      String category,
      Instructor instructor,
      CourseStats stats,
      double rating,
      bool isEnrolled,
      int numOfflineWorkshops,
      int numHours,
      String? institution,
      DateTime createdAt,
      DateTime updatedAt,
      String? slug,
      List<Lesson> lessons,
      List<Quiz> quizzes,
      List<Assignment> assignments,
      double progress,
      List<String> requirements,
      List<String> benefits,
      List<String> targetAudience,
      List<String> materialIncludes,
      List<String> tags});

  @override
  $InstructorCopyWith<$Res> get instructor;
  @override
  $CourseStatsCopyWith<$Res> get stats;
}

/// @nodoc
class __$$CourseImplCopyWithImpl<$Res>
    extends _$CourseCopyWithImpl<$Res, _$CourseImpl>
    implements _$$CourseImplCopyWith<$Res> {
  __$$CourseImplCopyWithImpl(
      _$CourseImpl _value, $Res Function(_$CourseImpl) _then)
      : super(_value, _then);

  /// Create a copy of Course
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? id = null,
    Object? title = null,
    Object? description = null,
    Object? content = freezed,
    Object? featuredImage = null,
    Object? introVideo = freezed,
    Object? price = null,
    Object? salePrice = freezed,
    Object? level = null,
    Object? category = null,
    Object? instructor = null,
    Object? stats = null,
    Object? rating = null,
    Object? isEnrolled = null,
    Object? numOfflineWorkshops = null,
    Object? numHours = null,
    Object? institution = freezed,
    Object? createdAt = null,
    Object? updatedAt = null,
    Object? slug = freezed,
    Object? lessons = null,
    Object? quizzes = null,
    Object? assignments = null,
    Object? progress = null,
    Object? requirements = null,
    Object? benefits = null,
    Object? targetAudience = null,
    Object? materialIncludes = null,
    Object? tags = null,
  }) {
    return _then(_$CourseImpl(
      id: null == id
          ? _value.id
          : id // ignore: cast_nullable_to_non_nullable
              as String,
      title: null == title
          ? _value.title
          : title // ignore: cast_nullable_to_non_nullable
              as String,
      description: null == description
          ? _value.description
          : description // ignore: cast_nullable_to_non_nullable
              as String,
      content: freezed == content
          ? _value.content
          : content // ignore: cast_nullable_to_non_nullable
              as String?,
      featuredImage: null == featuredImage
          ? _value.featuredImage
          : featuredImage // ignore: cast_nullable_to_non_nullable
              as String,
      introVideo: freezed == introVideo
          ? _value.introVideo
          : introVideo // ignore: cast_nullable_to_non_nullable
              as String?,
      price: null == price
          ? _value.price
          : price // ignore: cast_nullable_to_non_nullable
              as double,
      salePrice: freezed == salePrice
          ? _value.salePrice
          : salePrice // ignore: cast_nullable_to_non_nullable
              as double?,
      level: null == level
          ? _value.level
          : level // ignore: cast_nullable_to_non_nullable
              as String,
      category: null == category
          ? _value.category
          : category // ignore: cast_nullable_to_non_nullable
              as String,
      instructor: null == instructor
          ? _value.instructor
          : instructor // ignore: cast_nullable_to_non_nullable
              as Instructor,
      stats: null == stats
          ? _value.stats
          : stats // ignore: cast_nullable_to_non_nullable
              as CourseStats,
      rating: null == rating
          ? _value.rating
          : rating // ignore: cast_nullable_to_non_nullable
              as double,
      isEnrolled: null == isEnrolled
          ? _value.isEnrolled
          : isEnrolled // ignore: cast_nullable_to_non_nullable
              as bool,
      numOfflineWorkshops: null == numOfflineWorkshops
          ? _value.numOfflineWorkshops
          : numOfflineWorkshops // ignore: cast_nullable_to_non_nullable
              as int,
      numHours: null == numHours
          ? _value.numHours
          : numHours // ignore: cast_nullable_to_non_nullable
              as int,
      institution: freezed == institution
          ? _value.institution
          : institution // ignore: cast_nullable_to_non_nullable
              as String?,
      createdAt: null == createdAt
          ? _value.createdAt
          : createdAt // ignore: cast_nullable_to_non_nullable
              as DateTime,
      updatedAt: null == updatedAt
          ? _value.updatedAt
          : updatedAt // ignore: cast_nullable_to_non_nullable
              as DateTime,
      slug: freezed == slug
          ? _value.slug
          : slug // ignore: cast_nullable_to_non_nullable
              as String?,
      lessons: null == lessons
          ? _value._lessons
          : lessons // ignore: cast_nullable_to_non_nullable
              as List<Lesson>,
      quizzes: null == quizzes
          ? _value._quizzes
          : quizzes // ignore: cast_nullable_to_non_nullable
              as List<Quiz>,
      assignments: null == assignments
          ? _value._assignments
          : assignments // ignore: cast_nullable_to_non_nullable
              as List<Assignment>,
      progress: null == progress
          ? _value.progress
          : progress // ignore: cast_nullable_to_non_nullable
              as double,
      requirements: null == requirements
          ? _value._requirements
          : requirements // ignore: cast_nullable_to_non_nullable
              as List<String>,
      benefits: null == benefits
          ? _value._benefits
          : benefits // ignore: cast_nullable_to_non_nullable
              as List<String>,
      targetAudience: null == targetAudience
          ? _value._targetAudience
          : targetAudience // ignore: cast_nullable_to_non_nullable
              as List<String>,
      materialIncludes: null == materialIncludes
          ? _value._materialIncludes
          : materialIncludes // ignore: cast_nullable_to_non_nullable
              as List<String>,
      tags: null == tags
          ? _value._tags
          : tags // ignore: cast_nullable_to_non_nullable
              as List<String>,
    ));
  }
}

/// @nodoc

class _$CourseImpl implements _Course {
  const _$CourseImpl(
      {required this.id,
      required this.title,
      required this.description,
      this.content,
      required this.featuredImage,
      this.introVideo,
      required this.price,
      this.salePrice,
      required this.level,
      required this.category,
      required this.instructor,
      required this.stats,
      required this.rating,
      this.isEnrolled = false,
      this.numOfflineWorkshops = 0,
      this.numHours = 0,
      this.institution,
      required this.createdAt,
      required this.updatedAt,
      this.slug,
      final List<Lesson> lessons = const [],
      final List<Quiz> quizzes = const [],
      final List<Assignment> assignments = const [],
      this.progress = 0,
      final List<String> requirements = const [],
      final List<String> benefits = const [],
      final List<String> targetAudience = const [],
      final List<String> materialIncludes = const [],
      final List<String> tags = const []})
      : _lessons = lessons,
        _quizzes = quizzes,
        _assignments = assignments,
        _requirements = requirements,
        _benefits = benefits,
        _targetAudience = targetAudience,
        _materialIncludes = materialIncludes,
        _tags = tags;

  @override
  final String id;
  @override
  final String title;
  @override
  final String description;
  @override
  final String? content;
  @override
  final String featuredImage;
  @override
  final String? introVideo;
  @override
  final double price;
  @override
  final double? salePrice;
  @override
  final String level;
  @override
  final String category;
  @override
  final Instructor instructor;
  @override
  final CourseStats stats;
  @override
  final double rating;
  @override
  @JsonKey()
  final bool isEnrolled;
  @override
  @JsonKey()
  final int numOfflineWorkshops;
  @override
  @JsonKey()
  final int numHours;
  @override
  final String? institution;
  @override
  final DateTime createdAt;
  @override
  final DateTime updatedAt;
  @override
  final String? slug;
  final List<Lesson> _lessons;
  @override
  @JsonKey()
  List<Lesson> get lessons {
    if (_lessons is EqualUnmodifiableListView) return _lessons;
    // ignore: implicit_dynamic_type
    return EqualUnmodifiableListView(_lessons);
  }

  final List<Quiz> _quizzes;
  @override
  @JsonKey()
  List<Quiz> get quizzes {
    if (_quizzes is EqualUnmodifiableListView) return _quizzes;
    // ignore: implicit_dynamic_type
    return EqualUnmodifiableListView(_quizzes);
  }

  final List<Assignment> _assignments;
  @override
  @JsonKey()
  List<Assignment> get assignments {
    if (_assignments is EqualUnmodifiableListView) return _assignments;
    // ignore: implicit_dynamic_type
    return EqualUnmodifiableListView(_assignments);
  }

  @override
  @JsonKey()
  final double progress;
  final List<String> _requirements;
  @override
  @JsonKey()
  List<String> get requirements {
    if (_requirements is EqualUnmodifiableListView) return _requirements;
    // ignore: implicit_dynamic_type
    return EqualUnmodifiableListView(_requirements);
  }

  final List<String> _benefits;
  @override
  @JsonKey()
  List<String> get benefits {
    if (_benefits is EqualUnmodifiableListView) return _benefits;
    // ignore: implicit_dynamic_type
    return EqualUnmodifiableListView(_benefits);
  }

  final List<String> _targetAudience;
  @override
  @JsonKey()
  List<String> get targetAudience {
    if (_targetAudience is EqualUnmodifiableListView) return _targetAudience;
    // ignore: implicit_dynamic_type
    return EqualUnmodifiableListView(_targetAudience);
  }

  final List<String> _materialIncludes;
  @override
  @JsonKey()
  List<String> get materialIncludes {
    if (_materialIncludes is EqualUnmodifiableListView)
      return _materialIncludes;
    // ignore: implicit_dynamic_type
    return EqualUnmodifiableListView(_materialIncludes);
  }

  final List<String> _tags;
  @override
  @JsonKey()
  List<String> get tags {
    if (_tags is EqualUnmodifiableListView) return _tags;
    // ignore: implicit_dynamic_type
    return EqualUnmodifiableListView(_tags);
  }

  @override
  String toString() {
    return 'Course(id: $id, title: $title, description: $description, content: $content, featuredImage: $featuredImage, introVideo: $introVideo, price: $price, salePrice: $salePrice, level: $level, category: $category, instructor: $instructor, stats: $stats, rating: $rating, isEnrolled: $isEnrolled, numOfflineWorkshops: $numOfflineWorkshops, numHours: $numHours, institution: $institution, createdAt: $createdAt, updatedAt: $updatedAt, slug: $slug, lessons: $lessons, quizzes: $quizzes, assignments: $assignments, progress: $progress, requirements: $requirements, benefits: $benefits, targetAudience: $targetAudience, materialIncludes: $materialIncludes, tags: $tags)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$CourseImpl &&
            (identical(other.id, id) || other.id == id) &&
            (identical(other.title, title) || other.title == title) &&
            (identical(other.description, description) ||
                other.description == description) &&
            (identical(other.content, content) || other.content == content) &&
            (identical(other.featuredImage, featuredImage) ||
                other.featuredImage == featuredImage) &&
            (identical(other.introVideo, introVideo) ||
                other.introVideo == introVideo) &&
            (identical(other.price, price) || other.price == price) &&
            (identical(other.salePrice, salePrice) ||
                other.salePrice == salePrice) &&
            (identical(other.level, level) || other.level == level) &&
            (identical(other.category, category) ||
                other.category == category) &&
            (identical(other.instructor, instructor) ||
                other.instructor == instructor) &&
            (identical(other.stats, stats) || other.stats == stats) &&
            (identical(other.rating, rating) || other.rating == rating) &&
            (identical(other.isEnrolled, isEnrolled) ||
                other.isEnrolled == isEnrolled) &&
            (identical(other.numOfflineWorkshops, numOfflineWorkshops) ||
                other.numOfflineWorkshops == numOfflineWorkshops) &&
            (identical(other.numHours, numHours) ||
                other.numHours == numHours) &&
            (identical(other.institution, institution) ||
                other.institution == institution) &&
            (identical(other.createdAt, createdAt) ||
                other.createdAt == createdAt) &&
            (identical(other.updatedAt, updatedAt) ||
                other.updatedAt == updatedAt) &&
            (identical(other.slug, slug) || other.slug == slug) &&
            const DeepCollectionEquality().equals(other._lessons, _lessons) &&
            const DeepCollectionEquality().equals(other._quizzes, _quizzes) &&
            const DeepCollectionEquality()
                .equals(other._assignments, _assignments) &&
            (identical(other.progress, progress) ||
                other.progress == progress) &&
            const DeepCollectionEquality()
                .equals(other._requirements, _requirements) &&
            const DeepCollectionEquality().equals(other._benefits, _benefits) &&
            const DeepCollectionEquality()
                .equals(other._targetAudience, _targetAudience) &&
            const DeepCollectionEquality()
                .equals(other._materialIncludes, _materialIncludes) &&
            const DeepCollectionEquality().equals(other._tags, _tags));
  }

  @override
  int get hashCode => Object.hashAll([
        runtimeType,
        id,
        title,
        description,
        content,
        featuredImage,
        introVideo,
        price,
        salePrice,
        level,
        category,
        instructor,
        stats,
        rating,
        isEnrolled,
        numOfflineWorkshops,
        numHours,
        institution,
        createdAt,
        updatedAt,
        slug,
        const DeepCollectionEquality().hash(_lessons),
        const DeepCollectionEquality().hash(_quizzes),
        const DeepCollectionEquality().hash(_assignments),
        progress,
        const DeepCollectionEquality().hash(_requirements),
        const DeepCollectionEquality().hash(_benefits),
        const DeepCollectionEquality().hash(_targetAudience),
        const DeepCollectionEquality().hash(_materialIncludes),
        const DeepCollectionEquality().hash(_tags)
      ]);

  /// Create a copy of Course
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  @pragma('vm:prefer-inline')
  _$$CourseImplCopyWith<_$CourseImpl> get copyWith =>
      __$$CourseImplCopyWithImpl<_$CourseImpl>(this, _$identity);
}

abstract class _Course implements Course {
  const factory _Course(
      {required final String id,
      required final String title,
      required final String description,
      final String? content,
      required final String featuredImage,
      final String? introVideo,
      required final double price,
      final double? salePrice,
      required final String level,
      required final String category,
      required final Instructor instructor,
      required final CourseStats stats,
      required final double rating,
      final bool isEnrolled,
      final int numOfflineWorkshops,
      final int numHours,
      final String? institution,
      required final DateTime createdAt,
      required final DateTime updatedAt,
      final String? slug,
      final List<Lesson> lessons,
      final List<Quiz> quizzes,
      final List<Assignment> assignments,
      final double progress,
      final List<String> requirements,
      final List<String> benefits,
      final List<String> targetAudience,
      final List<String> materialIncludes,
      final List<String> tags}) = _$CourseImpl;

  @override
  String get id;
  @override
  String get title;
  @override
  String get description;
  @override
  String? get content;
  @override
  String get featuredImage;
  @override
  String? get introVideo;
  @override
  double get price;
  @override
  double? get salePrice;
  @override
  String get level;
  @override
  String get category;
  @override
  Instructor get instructor;
  @override
  CourseStats get stats;
  @override
  double get rating;
  @override
  bool get isEnrolled;
  @override
  int get numOfflineWorkshops;
  @override
  int get numHours;
  @override
  String? get institution;
  @override
  DateTime get createdAt;
  @override
  DateTime get updatedAt;
  @override
  String? get slug;
  @override
  List<Lesson> get lessons;
  @override
  List<Quiz> get quizzes;
  @override
  List<Assignment> get assignments;
  @override
  double get progress;
  @override
  List<String> get requirements;
  @override
  List<String> get benefits;
  @override
  List<String> get targetAudience;
  @override
  List<String> get materialIncludes;
  @override
  List<String> get tags;

  /// Create a copy of Course
  /// with the given fields replaced by the non-null parameter values.
  @override
  @JsonKey(includeFromJson: false, includeToJson: false)
  _$$CourseImplCopyWith<_$CourseImpl> get copyWith =>
      throw _privateConstructorUsedError;
}

/// @nodoc
mixin _$Instructor {
  String get id => throw _privateConstructorUsedError;
  String get name => throw _privateConstructorUsedError;
  String get avatar => throw _privateConstructorUsedError;

  /// Create a copy of Instructor
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  $InstructorCopyWith<Instructor> get copyWith =>
      throw _privateConstructorUsedError;
}

/// @nodoc
abstract class $InstructorCopyWith<$Res> {
  factory $InstructorCopyWith(
          Instructor value, $Res Function(Instructor) then) =
      _$InstructorCopyWithImpl<$Res, Instructor>;
  @useResult
  $Res call({String id, String name, String avatar});
}

/// @nodoc
class _$InstructorCopyWithImpl<$Res, $Val extends Instructor>
    implements $InstructorCopyWith<$Res> {
  _$InstructorCopyWithImpl(this._value, this._then);

  // ignore: unused_field
  final $Val _value;
  // ignore: unused_field
  final $Res Function($Val) _then;

  /// Create a copy of Instructor
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? id = null,
    Object? name = null,
    Object? avatar = null,
  }) {
    return _then(_value.copyWith(
      id: null == id
          ? _value.id
          : id // ignore: cast_nullable_to_non_nullable
              as String,
      name: null == name
          ? _value.name
          : name // ignore: cast_nullable_to_non_nullable
              as String,
      avatar: null == avatar
          ? _value.avatar
          : avatar // ignore: cast_nullable_to_non_nullable
              as String,
    ) as $Val);
  }
}

/// @nodoc
abstract class _$$InstructorImplCopyWith<$Res>
    implements $InstructorCopyWith<$Res> {
  factory _$$InstructorImplCopyWith(
          _$InstructorImpl value, $Res Function(_$InstructorImpl) then) =
      __$$InstructorImplCopyWithImpl<$Res>;
  @override
  @useResult
  $Res call({String id, String name, String avatar});
}

/// @nodoc
class __$$InstructorImplCopyWithImpl<$Res>
    extends _$InstructorCopyWithImpl<$Res, _$InstructorImpl>
    implements _$$InstructorImplCopyWith<$Res> {
  __$$InstructorImplCopyWithImpl(
      _$InstructorImpl _value, $Res Function(_$InstructorImpl) _then)
      : super(_value, _then);

  /// Create a copy of Instructor
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? id = null,
    Object? name = null,
    Object? avatar = null,
  }) {
    return _then(_$InstructorImpl(
      id: null == id
          ? _value.id
          : id // ignore: cast_nullable_to_non_nullable
              as String,
      name: null == name
          ? _value.name
          : name // ignore: cast_nullable_to_non_nullable
              as String,
      avatar: null == avatar
          ? _value.avatar
          : avatar // ignore: cast_nullable_to_non_nullable
              as String,
    ));
  }
}

/// @nodoc

class _$InstructorImpl implements _Instructor {
  const _$InstructorImpl(
      {required this.id, required this.name, required this.avatar});

  @override
  final String id;
  @override
  final String name;
  @override
  final String avatar;

  @override
  String toString() {
    return 'Instructor(id: $id, name: $name, avatar: $avatar)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$InstructorImpl &&
            (identical(other.id, id) || other.id == id) &&
            (identical(other.name, name) || other.name == name) &&
            (identical(other.avatar, avatar) || other.avatar == avatar));
  }

  @override
  int get hashCode => Object.hash(runtimeType, id, name, avatar);

  /// Create a copy of Instructor
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  @pragma('vm:prefer-inline')
  _$$InstructorImplCopyWith<_$InstructorImpl> get copyWith =>
      __$$InstructorImplCopyWithImpl<_$InstructorImpl>(this, _$identity);
}

abstract class _Instructor implements Instructor {
  const factory _Instructor(
      {required final String id,
      required final String name,
      required final String avatar}) = _$InstructorImpl;

  @override
  String get id;
  @override
  String get name;
  @override
  String get avatar;

  /// Create a copy of Instructor
  /// with the given fields replaced by the non-null parameter values.
  @override
  @JsonKey(includeFromJson: false, includeToJson: false)
  _$$InstructorImplCopyWith<_$InstructorImpl> get copyWith =>
      throw _privateConstructorUsedError;
}

/// @nodoc
mixin _$CourseStats {
  int get lessons => throw _privateConstructorUsedError;
  int get quizzes => throw _privateConstructorUsedError;
  int get duration => throw _privateConstructorUsedError;
  int get students => throw _privateConstructorUsedError;

  /// Create a copy of CourseStats
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  $CourseStatsCopyWith<CourseStats> get copyWith =>
      throw _privateConstructorUsedError;
}

/// @nodoc
abstract class $CourseStatsCopyWith<$Res> {
  factory $CourseStatsCopyWith(
          CourseStats value, $Res Function(CourseStats) then) =
      _$CourseStatsCopyWithImpl<$Res, CourseStats>;
  @useResult
  $Res call({int lessons, int quizzes, int duration, int students});
}

/// @nodoc
class _$CourseStatsCopyWithImpl<$Res, $Val extends CourseStats>
    implements $CourseStatsCopyWith<$Res> {
  _$CourseStatsCopyWithImpl(this._value, this._then);

  // ignore: unused_field
  final $Val _value;
  // ignore: unused_field
  final $Res Function($Val) _then;

  /// Create a copy of CourseStats
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? lessons = null,
    Object? quizzes = null,
    Object? duration = null,
    Object? students = null,
  }) {
    return _then(_value.copyWith(
      lessons: null == lessons
          ? _value.lessons
          : lessons // ignore: cast_nullable_to_non_nullable
              as int,
      quizzes: null == quizzes
          ? _value.quizzes
          : quizzes // ignore: cast_nullable_to_non_nullable
              as int,
      duration: null == duration
          ? _value.duration
          : duration // ignore: cast_nullable_to_non_nullable
              as int,
      students: null == students
          ? _value.students
          : students // ignore: cast_nullable_to_non_nullable
              as int,
    ) as $Val);
  }
}

/// @nodoc
abstract class _$$CourseStatsImplCopyWith<$Res>
    implements $CourseStatsCopyWith<$Res> {
  factory _$$CourseStatsImplCopyWith(
          _$CourseStatsImpl value, $Res Function(_$CourseStatsImpl) then) =
      __$$CourseStatsImplCopyWithImpl<$Res>;
  @override
  @useResult
  $Res call({int lessons, int quizzes, int duration, int students});
}

/// @nodoc
class __$$CourseStatsImplCopyWithImpl<$Res>
    extends _$CourseStatsCopyWithImpl<$Res, _$CourseStatsImpl>
    implements _$$CourseStatsImplCopyWith<$Res> {
  __$$CourseStatsImplCopyWithImpl(
      _$CourseStatsImpl _value, $Res Function(_$CourseStatsImpl) _then)
      : super(_value, _then);

  /// Create a copy of CourseStats
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? lessons = null,
    Object? quizzes = null,
    Object? duration = null,
    Object? students = null,
  }) {
    return _then(_$CourseStatsImpl(
      lessons: null == lessons
          ? _value.lessons
          : lessons // ignore: cast_nullable_to_non_nullable
              as int,
      quizzes: null == quizzes
          ? _value.quizzes
          : quizzes // ignore: cast_nullable_to_non_nullable
              as int,
      duration: null == duration
          ? _value.duration
          : duration // ignore: cast_nullable_to_non_nullable
              as int,
      students: null == students
          ? _value.students
          : students // ignore: cast_nullable_to_non_nullable
              as int,
    ));
  }
}

/// @nodoc

class _$CourseStatsImpl implements _CourseStats {
  const _$CourseStatsImpl(
      {required this.lessons,
      required this.quizzes,
      required this.duration,
      required this.students});

  @override
  final int lessons;
  @override
  final int quizzes;
  @override
  final int duration;
  @override
  final int students;

  @override
  String toString() {
    return 'CourseStats(lessons: $lessons, quizzes: $quizzes, duration: $duration, students: $students)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$CourseStatsImpl &&
            (identical(other.lessons, lessons) || other.lessons == lessons) &&
            (identical(other.quizzes, quizzes) || other.quizzes == quizzes) &&
            (identical(other.duration, duration) ||
                other.duration == duration) &&
            (identical(other.students, students) ||
                other.students == students));
  }

  @override
  int get hashCode =>
      Object.hash(runtimeType, lessons, quizzes, duration, students);

  /// Create a copy of CourseStats
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  @pragma('vm:prefer-inline')
  _$$CourseStatsImplCopyWith<_$CourseStatsImpl> get copyWith =>
      __$$CourseStatsImplCopyWithImpl<_$CourseStatsImpl>(this, _$identity);
}

abstract class _CourseStats implements CourseStats {
  const factory _CourseStats(
      {required final int lessons,
      required final int quizzes,
      required final int duration,
      required final int students}) = _$CourseStatsImpl;

  @override
  int get lessons;
  @override
  int get quizzes;
  @override
  int get duration;
  @override
  int get students;

  /// Create a copy of CourseStats
  /// with the given fields replaced by the non-null parameter values.
  @override
  @JsonKey(includeFromJson: false, includeToJson: false)
  _$$CourseStatsImplCopyWith<_$CourseStatsImpl> get copyWith =>
      throw _privateConstructorUsedError;
}
