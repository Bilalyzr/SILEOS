// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint
// ignore_for_file: unused_element, deprecated_member_use, deprecated_member_use_from_same_package, use_function_type_syntax_for_parameters, unnecessary_const, avoid_init_to_null, invalid_override_different_default_values_named, prefer_expression_function_bodies, annotate_overrides, invalid_annotation_target, unnecessary_question_mark

part of 'course_model.dart';

// **************************************************************************
// FreezedGenerator
// **************************************************************************

T _$identity<T>(T value) => value;

final _privateConstructorUsedError = UnsupportedError(
    'It seems like you constructed your class using `MyClass._()`. This constructor is only meant to be used by freezed and you are not supposed to need it nor use it.\nPlease check the documentation here for more information: https://github.com/rrousselGit/freezed#adding-getters-and-methods-to-our-models');

CourseModel _$CourseModelFromJson(Map<String, dynamic> json) {
  return _CourseModel.fromJson(json);
}

/// @nodoc
mixin _$CourseModel {
  int get id => throw _privateConstructorUsedError;
  String get title => throw _privateConstructorUsedError;
  String get description => throw _privateConstructorUsedError;
  String? get content => throw _privateConstructorUsedError;
  @JsonKey(name: 'featured_image', defaultValue: '')
  String get featuredImage => throw _privateConstructorUsedError;
  @JsonKey(name: 'thumbnail')
  String? get thumbnail => throw _privateConstructorUsedError;
  @JsonKey(name: 'intro_video')
  String? get introVideo => throw _privateConstructorUsedError;
  double get price => throw _privateConstructorUsedError;
  @JsonKey(name: 'sale_price')
  double? get salePrice => throw _privateConstructorUsedError;
  String get level => throw _privateConstructorUsedError;
  String get category => throw _privateConstructorUsedError;
  InstructorModel get instructor => throw _privateConstructorUsedError;
  CourseStatsModel get stats => throw _privateConstructorUsedError;
  double get rating => throw _privateConstructorUsedError;
  @JsonKey(name: 'is_enrolled')
  bool get isEnrolled => throw _privateConstructorUsedError;
  @JsonKey(name: 'num_offline_workshops')
  int get numOfflineWorkshops => throw _privateConstructorUsedError;
  @JsonKey(name: 'num_hours')
  int get numHours => throw _privateConstructorUsedError;
  String? get institution => throw _privateConstructorUsedError;
  @JsonKey(name: 'created_at')
  String get createdAt => throw _privateConstructorUsedError;
  @JsonKey(name: 'updated_at')
  String get updatedAt => throw _privateConstructorUsedError;
  String? get slug => throw _privateConstructorUsedError;
  List<LessonModel> get lessons => throw _privateConstructorUsedError;
  List<QuizModel> get quizzes => throw _privateConstructorUsedError;
  List<AssignmentModel> get assignments => throw _privateConstructorUsedError;
  double get progress => throw _privateConstructorUsedError;
  List<String> get requirements => throw _privateConstructorUsedError;
  List<String> get benefits => throw _privateConstructorUsedError;
  @JsonKey(name: 'target_audience')
  List<String> get targetAudience => throw _privateConstructorUsedError;
  @JsonKey(name: 'material_includes')
  List<String> get materialIncludes => throw _privateConstructorUsedError;
  List<String> get tags => throw _privateConstructorUsedError;

  /// Serializes this CourseModel to a JSON map.
  Map<String, dynamic> toJson() => throw _privateConstructorUsedError;

  /// Create a copy of CourseModel
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  $CourseModelCopyWith<CourseModel> get copyWith =>
      throw _privateConstructorUsedError;
}

/// @nodoc
abstract class $CourseModelCopyWith<$Res> {
  factory $CourseModelCopyWith(
          CourseModel value, $Res Function(CourseModel) then) =
      _$CourseModelCopyWithImpl<$Res, CourseModel>;
  @useResult
  $Res call(
      {int id,
      String title,
      String description,
      String? content,
      @JsonKey(name: 'featured_image', defaultValue: '') String featuredImage,
      @JsonKey(name: 'thumbnail') String? thumbnail,
      @JsonKey(name: 'intro_video') String? introVideo,
      double price,
      @JsonKey(name: 'sale_price') double? salePrice,
      String level,
      String category,
      InstructorModel instructor,
      CourseStatsModel stats,
      double rating,
      @JsonKey(name: 'is_enrolled') bool isEnrolled,
      @JsonKey(name: 'num_offline_workshops') int numOfflineWorkshops,
      @JsonKey(name: 'num_hours') int numHours,
      String? institution,
      @JsonKey(name: 'created_at') String createdAt,
      @JsonKey(name: 'updated_at') String updatedAt,
      String? slug,
      List<LessonModel> lessons,
      List<QuizModel> quizzes,
      List<AssignmentModel> assignments,
      double progress,
      List<String> requirements,
      List<String> benefits,
      @JsonKey(name: 'target_audience') List<String> targetAudience,
      @JsonKey(name: 'material_includes') List<String> materialIncludes,
      List<String> tags});

  $InstructorModelCopyWith<$Res> get instructor;
  $CourseStatsModelCopyWith<$Res> get stats;
}

/// @nodoc
class _$CourseModelCopyWithImpl<$Res, $Val extends CourseModel>
    implements $CourseModelCopyWith<$Res> {
  _$CourseModelCopyWithImpl(this._value, this._then);

  // ignore: unused_field
  final $Val _value;
  // ignore: unused_field
  final $Res Function($Val) _then;

  /// Create a copy of CourseModel
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? id = null,
    Object? title = null,
    Object? description = null,
    Object? content = freezed,
    Object? featuredImage = null,
    Object? thumbnail = freezed,
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
              as int,
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
      thumbnail: freezed == thumbnail
          ? _value.thumbnail
          : thumbnail // ignore: cast_nullable_to_non_nullable
              as String?,
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
              as InstructorModel,
      stats: null == stats
          ? _value.stats
          : stats // ignore: cast_nullable_to_non_nullable
              as CourseStatsModel,
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
              as String,
      updatedAt: null == updatedAt
          ? _value.updatedAt
          : updatedAt // ignore: cast_nullable_to_non_nullable
              as String,
      slug: freezed == slug
          ? _value.slug
          : slug // ignore: cast_nullable_to_non_nullable
              as String?,
      lessons: null == lessons
          ? _value.lessons
          : lessons // ignore: cast_nullable_to_non_nullable
              as List<LessonModel>,
      quizzes: null == quizzes
          ? _value.quizzes
          : quizzes // ignore: cast_nullable_to_non_nullable
              as List<QuizModel>,
      assignments: null == assignments
          ? _value.assignments
          : assignments // ignore: cast_nullable_to_non_nullable
              as List<AssignmentModel>,
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

  /// Create a copy of CourseModel
  /// with the given fields replaced by the non-null parameter values.
  @override
  @pragma('vm:prefer-inline')
  $InstructorModelCopyWith<$Res> get instructor {
    return $InstructorModelCopyWith<$Res>(_value.instructor, (value) {
      return _then(_value.copyWith(instructor: value) as $Val);
    });
  }

  /// Create a copy of CourseModel
  /// with the given fields replaced by the non-null parameter values.
  @override
  @pragma('vm:prefer-inline')
  $CourseStatsModelCopyWith<$Res> get stats {
    return $CourseStatsModelCopyWith<$Res>(_value.stats, (value) {
      return _then(_value.copyWith(stats: value) as $Val);
    });
  }
}

/// @nodoc
abstract class _$$CourseModelImplCopyWith<$Res>
    implements $CourseModelCopyWith<$Res> {
  factory _$$CourseModelImplCopyWith(
          _$CourseModelImpl value, $Res Function(_$CourseModelImpl) then) =
      __$$CourseModelImplCopyWithImpl<$Res>;
  @override
  @useResult
  $Res call(
      {int id,
      String title,
      String description,
      String? content,
      @JsonKey(name: 'featured_image', defaultValue: '') String featuredImage,
      @JsonKey(name: 'thumbnail') String? thumbnail,
      @JsonKey(name: 'intro_video') String? introVideo,
      double price,
      @JsonKey(name: 'sale_price') double? salePrice,
      String level,
      String category,
      InstructorModel instructor,
      CourseStatsModel stats,
      double rating,
      @JsonKey(name: 'is_enrolled') bool isEnrolled,
      @JsonKey(name: 'num_offline_workshops') int numOfflineWorkshops,
      @JsonKey(name: 'num_hours') int numHours,
      String? institution,
      @JsonKey(name: 'created_at') String createdAt,
      @JsonKey(name: 'updated_at') String updatedAt,
      String? slug,
      List<LessonModel> lessons,
      List<QuizModel> quizzes,
      List<AssignmentModel> assignments,
      double progress,
      List<String> requirements,
      List<String> benefits,
      @JsonKey(name: 'target_audience') List<String> targetAudience,
      @JsonKey(name: 'material_includes') List<String> materialIncludes,
      List<String> tags});

  @override
  $InstructorModelCopyWith<$Res> get instructor;
  @override
  $CourseStatsModelCopyWith<$Res> get stats;
}

/// @nodoc
class __$$CourseModelImplCopyWithImpl<$Res>
    extends _$CourseModelCopyWithImpl<$Res, _$CourseModelImpl>
    implements _$$CourseModelImplCopyWith<$Res> {
  __$$CourseModelImplCopyWithImpl(
      _$CourseModelImpl _value, $Res Function(_$CourseModelImpl) _then)
      : super(_value, _then);

  /// Create a copy of CourseModel
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? id = null,
    Object? title = null,
    Object? description = null,
    Object? content = freezed,
    Object? featuredImage = null,
    Object? thumbnail = freezed,
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
    return _then(_$CourseModelImpl(
      id: null == id
          ? _value.id
          : id // ignore: cast_nullable_to_non_nullable
              as int,
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
      thumbnail: freezed == thumbnail
          ? _value.thumbnail
          : thumbnail // ignore: cast_nullable_to_non_nullable
              as String?,
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
              as InstructorModel,
      stats: null == stats
          ? _value.stats
          : stats // ignore: cast_nullable_to_non_nullable
              as CourseStatsModel,
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
              as String,
      updatedAt: null == updatedAt
          ? _value.updatedAt
          : updatedAt // ignore: cast_nullable_to_non_nullable
              as String,
      slug: freezed == slug
          ? _value.slug
          : slug // ignore: cast_nullable_to_non_nullable
              as String?,
      lessons: null == lessons
          ? _value._lessons
          : lessons // ignore: cast_nullable_to_non_nullable
              as List<LessonModel>,
      quizzes: null == quizzes
          ? _value._quizzes
          : quizzes // ignore: cast_nullable_to_non_nullable
              as List<QuizModel>,
      assignments: null == assignments
          ? _value._assignments
          : assignments // ignore: cast_nullable_to_non_nullable
              as List<AssignmentModel>,
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
@JsonSerializable()
class _$CourseModelImpl extends _CourseModel {
  const _$CourseModelImpl(
      {required this.id,
      required this.title,
      required this.description,
      this.content,
      @JsonKey(name: 'featured_image', defaultValue: '')
      required this.featuredImage,
      @JsonKey(name: 'thumbnail') this.thumbnail,
      @JsonKey(name: 'intro_video') this.introVideo,
      required this.price,
      @JsonKey(name: 'sale_price') this.salePrice,
      required this.level,
      required this.category,
      required this.instructor,
      required this.stats,
      this.rating = 0.0,
      @JsonKey(name: 'is_enrolled') this.isEnrolled = false,
      @JsonKey(name: 'num_offline_workshops') this.numOfflineWorkshops = 0,
      @JsonKey(name: 'num_hours') this.numHours = 0,
      this.institution,
      @JsonKey(name: 'created_at') required this.createdAt,
      @JsonKey(name: 'updated_at') required this.updatedAt,
      this.slug,
      final List<LessonModel> lessons = const [],
      final List<QuizModel> quizzes = const [],
      final List<AssignmentModel> assignments = const [],
      this.progress = 0.0,
      final List<String> requirements = const [],
      final List<String> benefits = const [],
      @JsonKey(name: 'target_audience')
      final List<String> targetAudience = const [],
      @JsonKey(name: 'material_includes')
      final List<String> materialIncludes = const [],
      final List<String> tags = const []})
      : _lessons = lessons,
        _quizzes = quizzes,
        _assignments = assignments,
        _requirements = requirements,
        _benefits = benefits,
        _targetAudience = targetAudience,
        _materialIncludes = materialIncludes,
        _tags = tags,
        super._();

  factory _$CourseModelImpl.fromJson(Map<String, dynamic> json) =>
      _$$CourseModelImplFromJson(json);

  @override
  final int id;
  @override
  final String title;
  @override
  final String description;
  @override
  final String? content;
  @override
  @JsonKey(name: 'featured_image', defaultValue: '')
  final String featuredImage;
  @override
  @JsonKey(name: 'thumbnail')
  final String? thumbnail;
  @override
  @JsonKey(name: 'intro_video')
  final String? introVideo;
  @override
  final double price;
  @override
  @JsonKey(name: 'sale_price')
  final double? salePrice;
  @override
  final String level;
  @override
  final String category;
  @override
  final InstructorModel instructor;
  @override
  final CourseStatsModel stats;
  @override
  @JsonKey()
  final double rating;
  @override
  @JsonKey(name: 'is_enrolled')
  final bool isEnrolled;
  @override
  @JsonKey(name: 'num_offline_workshops')
  final int numOfflineWorkshops;
  @override
  @JsonKey(name: 'num_hours')
  final int numHours;
  @override
  final String? institution;
  @override
  @JsonKey(name: 'created_at')
  final String createdAt;
  @override
  @JsonKey(name: 'updated_at')
  final String updatedAt;
  @override
  final String? slug;
  final List<LessonModel> _lessons;
  @override
  @JsonKey()
  List<LessonModel> get lessons {
    if (_lessons is EqualUnmodifiableListView) return _lessons;
    // ignore: implicit_dynamic_type
    return EqualUnmodifiableListView(_lessons);
  }

  final List<QuizModel> _quizzes;
  @override
  @JsonKey()
  List<QuizModel> get quizzes {
    if (_quizzes is EqualUnmodifiableListView) return _quizzes;
    // ignore: implicit_dynamic_type
    return EqualUnmodifiableListView(_quizzes);
  }

  final List<AssignmentModel> _assignments;
  @override
  @JsonKey()
  List<AssignmentModel> get assignments {
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
  @JsonKey(name: 'target_audience')
  List<String> get targetAudience {
    if (_targetAudience is EqualUnmodifiableListView) return _targetAudience;
    // ignore: implicit_dynamic_type
    return EqualUnmodifiableListView(_targetAudience);
  }

  final List<String> _materialIncludes;
  @override
  @JsonKey(name: 'material_includes')
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
    return 'CourseModel(id: $id, title: $title, description: $description, content: $content, featuredImage: $featuredImage, thumbnail: $thumbnail, introVideo: $introVideo, price: $price, salePrice: $salePrice, level: $level, category: $category, instructor: $instructor, stats: $stats, rating: $rating, isEnrolled: $isEnrolled, numOfflineWorkshops: $numOfflineWorkshops, numHours: $numHours, institution: $institution, createdAt: $createdAt, updatedAt: $updatedAt, slug: $slug, lessons: $lessons, quizzes: $quizzes, assignments: $assignments, progress: $progress, requirements: $requirements, benefits: $benefits, targetAudience: $targetAudience, materialIncludes: $materialIncludes, tags: $tags)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$CourseModelImpl &&
            (identical(other.id, id) || other.id == id) &&
            (identical(other.title, title) || other.title == title) &&
            (identical(other.description, description) ||
                other.description == description) &&
            (identical(other.content, content) || other.content == content) &&
            (identical(other.featuredImage, featuredImage) ||
                other.featuredImage == featuredImage) &&
            (identical(other.thumbnail, thumbnail) ||
                other.thumbnail == thumbnail) &&
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

  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  int get hashCode => Object.hashAll([
        runtimeType,
        id,
        title,
        description,
        content,
        featuredImage,
        thumbnail,
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

  /// Create a copy of CourseModel
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  @pragma('vm:prefer-inline')
  _$$CourseModelImplCopyWith<_$CourseModelImpl> get copyWith =>
      __$$CourseModelImplCopyWithImpl<_$CourseModelImpl>(this, _$identity);

  @override
  Map<String, dynamic> toJson() {
    return _$$CourseModelImplToJson(
      this,
    );
  }
}

abstract class _CourseModel extends CourseModel {
  const factory _CourseModel(
      {required final int id,
      required final String title,
      required final String description,
      final String? content,
      @JsonKey(name: 'featured_image', defaultValue: '')
      required final String featuredImage,
      @JsonKey(name: 'thumbnail') final String? thumbnail,
      @JsonKey(name: 'intro_video') final String? introVideo,
      required final double price,
      @JsonKey(name: 'sale_price') final double? salePrice,
      required final String level,
      required final String category,
      required final InstructorModel instructor,
      required final CourseStatsModel stats,
      final double rating,
      @JsonKey(name: 'is_enrolled') final bool isEnrolled,
      @JsonKey(name: 'num_offline_workshops') final int numOfflineWorkshops,
      @JsonKey(name: 'num_hours') final int numHours,
      final String? institution,
      @JsonKey(name: 'created_at') required final String createdAt,
      @JsonKey(name: 'updated_at') required final String updatedAt,
      final String? slug,
      final List<LessonModel> lessons,
      final List<QuizModel> quizzes,
      final List<AssignmentModel> assignments,
      final double progress,
      final List<String> requirements,
      final List<String> benefits,
      @JsonKey(name: 'target_audience') final List<String> targetAudience,
      @JsonKey(name: 'material_includes') final List<String> materialIncludes,
      final List<String> tags}) = _$CourseModelImpl;
  const _CourseModel._() : super._();

  factory _CourseModel.fromJson(Map<String, dynamic> json) =
      _$CourseModelImpl.fromJson;

  @override
  int get id;
  @override
  String get title;
  @override
  String get description;
  @override
  String? get content;
  @override
  @JsonKey(name: 'featured_image', defaultValue: '')
  String get featuredImage;
  @override
  @JsonKey(name: 'thumbnail')
  String? get thumbnail;
  @override
  @JsonKey(name: 'intro_video')
  String? get introVideo;
  @override
  double get price;
  @override
  @JsonKey(name: 'sale_price')
  double? get salePrice;
  @override
  String get level;
  @override
  String get category;
  @override
  InstructorModel get instructor;
  @override
  CourseStatsModel get stats;
  @override
  double get rating;
  @override
  @JsonKey(name: 'is_enrolled')
  bool get isEnrolled;
  @override
  @JsonKey(name: 'num_offline_workshops')
  int get numOfflineWorkshops;
  @override
  @JsonKey(name: 'num_hours')
  int get numHours;
  @override
  String? get institution;
  @override
  @JsonKey(name: 'created_at')
  String get createdAt;
  @override
  @JsonKey(name: 'updated_at')
  String get updatedAt;
  @override
  String? get slug;
  @override
  List<LessonModel> get lessons;
  @override
  List<QuizModel> get quizzes;
  @override
  List<AssignmentModel> get assignments;
  @override
  double get progress;
  @override
  List<String> get requirements;
  @override
  List<String> get benefits;
  @override
  @JsonKey(name: 'target_audience')
  List<String> get targetAudience;
  @override
  @JsonKey(name: 'material_includes')
  List<String> get materialIncludes;
  @override
  List<String> get tags;

  /// Create a copy of CourseModel
  /// with the given fields replaced by the non-null parameter values.
  @override
  @JsonKey(includeFromJson: false, includeToJson: false)
  _$$CourseModelImplCopyWith<_$CourseModelImpl> get copyWith =>
      throw _privateConstructorUsedError;
}

InstructorModel _$InstructorModelFromJson(Map<String, dynamic> json) {
  return _InstructorModel.fromJson(json);
}

/// @nodoc
mixin _$InstructorModel {
  int get id => throw _privateConstructorUsedError;
  String get name => throw _privateConstructorUsedError;
  String get avatar => throw _privateConstructorUsedError;

  /// Serializes this InstructorModel to a JSON map.
  Map<String, dynamic> toJson() => throw _privateConstructorUsedError;

  /// Create a copy of InstructorModel
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  $InstructorModelCopyWith<InstructorModel> get copyWith =>
      throw _privateConstructorUsedError;
}

/// @nodoc
abstract class $InstructorModelCopyWith<$Res> {
  factory $InstructorModelCopyWith(
          InstructorModel value, $Res Function(InstructorModel) then) =
      _$InstructorModelCopyWithImpl<$Res, InstructorModel>;
  @useResult
  $Res call({int id, String name, String avatar});
}

/// @nodoc
class _$InstructorModelCopyWithImpl<$Res, $Val extends InstructorModel>
    implements $InstructorModelCopyWith<$Res> {
  _$InstructorModelCopyWithImpl(this._value, this._then);

  // ignore: unused_field
  final $Val _value;
  // ignore: unused_field
  final $Res Function($Val) _then;

  /// Create a copy of InstructorModel
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
              as int,
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
abstract class _$$InstructorModelImplCopyWith<$Res>
    implements $InstructorModelCopyWith<$Res> {
  factory _$$InstructorModelImplCopyWith(_$InstructorModelImpl value,
          $Res Function(_$InstructorModelImpl) then) =
      __$$InstructorModelImplCopyWithImpl<$Res>;
  @override
  @useResult
  $Res call({int id, String name, String avatar});
}

/// @nodoc
class __$$InstructorModelImplCopyWithImpl<$Res>
    extends _$InstructorModelCopyWithImpl<$Res, _$InstructorModelImpl>
    implements _$$InstructorModelImplCopyWith<$Res> {
  __$$InstructorModelImplCopyWithImpl(
      _$InstructorModelImpl _value, $Res Function(_$InstructorModelImpl) _then)
      : super(_value, _then);

  /// Create a copy of InstructorModel
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? id = null,
    Object? name = null,
    Object? avatar = null,
  }) {
    return _then(_$InstructorModelImpl(
      id: null == id
          ? _value.id
          : id // ignore: cast_nullable_to_non_nullable
              as int,
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
@JsonSerializable()
class _$InstructorModelImpl extends _InstructorModel {
  const _$InstructorModelImpl(
      {required this.id, required this.name, required this.avatar})
      : super._();

  factory _$InstructorModelImpl.fromJson(Map<String, dynamic> json) =>
      _$$InstructorModelImplFromJson(json);

  @override
  final int id;
  @override
  final String name;
  @override
  final String avatar;

  @override
  String toString() {
    return 'InstructorModel(id: $id, name: $name, avatar: $avatar)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$InstructorModelImpl &&
            (identical(other.id, id) || other.id == id) &&
            (identical(other.name, name) || other.name == name) &&
            (identical(other.avatar, avatar) || other.avatar == avatar));
  }

  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  int get hashCode => Object.hash(runtimeType, id, name, avatar);

  /// Create a copy of InstructorModel
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  @pragma('vm:prefer-inline')
  _$$InstructorModelImplCopyWith<_$InstructorModelImpl> get copyWith =>
      __$$InstructorModelImplCopyWithImpl<_$InstructorModelImpl>(
          this, _$identity);

  @override
  Map<String, dynamic> toJson() {
    return _$$InstructorModelImplToJson(
      this,
    );
  }
}

abstract class _InstructorModel extends InstructorModel {
  const factory _InstructorModel(
      {required final int id,
      required final String name,
      required final String avatar}) = _$InstructorModelImpl;
  const _InstructorModel._() : super._();

  factory _InstructorModel.fromJson(Map<String, dynamic> json) =
      _$InstructorModelImpl.fromJson;

  @override
  int get id;
  @override
  String get name;
  @override
  String get avatar;

  /// Create a copy of InstructorModel
  /// with the given fields replaced by the non-null parameter values.
  @override
  @JsonKey(includeFromJson: false, includeToJson: false)
  _$$InstructorModelImplCopyWith<_$InstructorModelImpl> get copyWith =>
      throw _privateConstructorUsedError;
}

CourseStatsModel _$CourseStatsModelFromJson(Map<String, dynamic> json) {
  return _CourseStatsModel.fromJson(json);
}

/// @nodoc
mixin _$CourseStatsModel {
  int get lessons => throw _privateConstructorUsedError;
  int get quizzes => throw _privateConstructorUsedError;
  int get duration => throw _privateConstructorUsedError;
  int get students => throw _privateConstructorUsedError;

  /// Serializes this CourseStatsModel to a JSON map.
  Map<String, dynamic> toJson() => throw _privateConstructorUsedError;

  /// Create a copy of CourseStatsModel
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  $CourseStatsModelCopyWith<CourseStatsModel> get copyWith =>
      throw _privateConstructorUsedError;
}

/// @nodoc
abstract class $CourseStatsModelCopyWith<$Res> {
  factory $CourseStatsModelCopyWith(
          CourseStatsModel value, $Res Function(CourseStatsModel) then) =
      _$CourseStatsModelCopyWithImpl<$Res, CourseStatsModel>;
  @useResult
  $Res call({int lessons, int quizzes, int duration, int students});
}

/// @nodoc
class _$CourseStatsModelCopyWithImpl<$Res, $Val extends CourseStatsModel>
    implements $CourseStatsModelCopyWith<$Res> {
  _$CourseStatsModelCopyWithImpl(this._value, this._then);

  // ignore: unused_field
  final $Val _value;
  // ignore: unused_field
  final $Res Function($Val) _then;

  /// Create a copy of CourseStatsModel
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
abstract class _$$CourseStatsModelImplCopyWith<$Res>
    implements $CourseStatsModelCopyWith<$Res> {
  factory _$$CourseStatsModelImplCopyWith(_$CourseStatsModelImpl value,
          $Res Function(_$CourseStatsModelImpl) then) =
      __$$CourseStatsModelImplCopyWithImpl<$Res>;
  @override
  @useResult
  $Res call({int lessons, int quizzes, int duration, int students});
}

/// @nodoc
class __$$CourseStatsModelImplCopyWithImpl<$Res>
    extends _$CourseStatsModelCopyWithImpl<$Res, _$CourseStatsModelImpl>
    implements _$$CourseStatsModelImplCopyWith<$Res> {
  __$$CourseStatsModelImplCopyWithImpl(_$CourseStatsModelImpl _value,
      $Res Function(_$CourseStatsModelImpl) _then)
      : super(_value, _then);

  /// Create a copy of CourseStatsModel
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? lessons = null,
    Object? quizzes = null,
    Object? duration = null,
    Object? students = null,
  }) {
    return _then(_$CourseStatsModelImpl(
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
@JsonSerializable()
class _$CourseStatsModelImpl extends _CourseStatsModel {
  const _$CourseStatsModelImpl(
      {required this.lessons,
      required this.quizzes,
      required this.duration,
      required this.students})
      : super._();

  factory _$CourseStatsModelImpl.fromJson(Map<String, dynamic> json) =>
      _$$CourseStatsModelImplFromJson(json);

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
    return 'CourseStatsModel(lessons: $lessons, quizzes: $quizzes, duration: $duration, students: $students)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$CourseStatsModelImpl &&
            (identical(other.lessons, lessons) || other.lessons == lessons) &&
            (identical(other.quizzes, quizzes) || other.quizzes == quizzes) &&
            (identical(other.duration, duration) ||
                other.duration == duration) &&
            (identical(other.students, students) ||
                other.students == students));
  }

  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  int get hashCode =>
      Object.hash(runtimeType, lessons, quizzes, duration, students);

  /// Create a copy of CourseStatsModel
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  @pragma('vm:prefer-inline')
  _$$CourseStatsModelImplCopyWith<_$CourseStatsModelImpl> get copyWith =>
      __$$CourseStatsModelImplCopyWithImpl<_$CourseStatsModelImpl>(
          this, _$identity);

  @override
  Map<String, dynamic> toJson() {
    return _$$CourseStatsModelImplToJson(
      this,
    );
  }
}

abstract class _CourseStatsModel extends CourseStatsModel {
  const factory _CourseStatsModel(
      {required final int lessons,
      required final int quizzes,
      required final int duration,
      required final int students}) = _$CourseStatsModelImpl;
  const _CourseStatsModel._() : super._();

  factory _CourseStatsModel.fromJson(Map<String, dynamic> json) =
      _$CourseStatsModelImpl.fromJson;

  @override
  int get lessons;
  @override
  int get quizzes;
  @override
  int get duration;
  @override
  int get students;

  /// Create a copy of CourseStatsModel
  /// with the given fields replaced by the non-null parameter values.
  @override
  @JsonKey(includeFromJson: false, includeToJson: false)
  _$$CourseStatsModelImplCopyWith<_$CourseStatsModelImpl> get copyWith =>
      throw _privateConstructorUsedError;
}

PaginatedCoursesModel _$PaginatedCoursesModelFromJson(
    Map<String, dynamic> json) {
  return _PaginatedCoursesModel.fromJson(json);
}

/// @nodoc
mixin _$PaginatedCoursesModel {
  List<CourseModel> get courses => throw _privateConstructorUsedError;
  int get total => throw _privateConstructorUsedError;
  int get page => throw _privateConstructorUsedError;
  @JsonKey(name: 'page_size')
  int get pageSize => throw _privateConstructorUsedError;
  @JsonKey(name: 'total_pages')
  int get totalPages => throw _privateConstructorUsedError;

  /// Serializes this PaginatedCoursesModel to a JSON map.
  Map<String, dynamic> toJson() => throw _privateConstructorUsedError;

  /// Create a copy of PaginatedCoursesModel
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  $PaginatedCoursesModelCopyWith<PaginatedCoursesModel> get copyWith =>
      throw _privateConstructorUsedError;
}

/// @nodoc
abstract class $PaginatedCoursesModelCopyWith<$Res> {
  factory $PaginatedCoursesModelCopyWith(PaginatedCoursesModel value,
          $Res Function(PaginatedCoursesModel) then) =
      _$PaginatedCoursesModelCopyWithImpl<$Res, PaginatedCoursesModel>;
  @useResult
  $Res call(
      {List<CourseModel> courses,
      int total,
      int page,
      @JsonKey(name: 'page_size') int pageSize,
      @JsonKey(name: 'total_pages') int totalPages});
}

/// @nodoc
class _$PaginatedCoursesModelCopyWithImpl<$Res,
        $Val extends PaginatedCoursesModel>
    implements $PaginatedCoursesModelCopyWith<$Res> {
  _$PaginatedCoursesModelCopyWithImpl(this._value, this._then);

  // ignore: unused_field
  final $Val _value;
  // ignore: unused_field
  final $Res Function($Val) _then;

  /// Create a copy of PaginatedCoursesModel
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? courses = null,
    Object? total = null,
    Object? page = null,
    Object? pageSize = null,
    Object? totalPages = null,
  }) {
    return _then(_value.copyWith(
      courses: null == courses
          ? _value.courses
          : courses // ignore: cast_nullable_to_non_nullable
              as List<CourseModel>,
      total: null == total
          ? _value.total
          : total // ignore: cast_nullable_to_non_nullable
              as int,
      page: null == page
          ? _value.page
          : page // ignore: cast_nullable_to_non_nullable
              as int,
      pageSize: null == pageSize
          ? _value.pageSize
          : pageSize // ignore: cast_nullable_to_non_nullable
              as int,
      totalPages: null == totalPages
          ? _value.totalPages
          : totalPages // ignore: cast_nullable_to_non_nullable
              as int,
    ) as $Val);
  }
}

/// @nodoc
abstract class _$$PaginatedCoursesModelImplCopyWith<$Res>
    implements $PaginatedCoursesModelCopyWith<$Res> {
  factory _$$PaginatedCoursesModelImplCopyWith(
          _$PaginatedCoursesModelImpl value,
          $Res Function(_$PaginatedCoursesModelImpl) then) =
      __$$PaginatedCoursesModelImplCopyWithImpl<$Res>;
  @override
  @useResult
  $Res call(
      {List<CourseModel> courses,
      int total,
      int page,
      @JsonKey(name: 'page_size') int pageSize,
      @JsonKey(name: 'total_pages') int totalPages});
}

/// @nodoc
class __$$PaginatedCoursesModelImplCopyWithImpl<$Res>
    extends _$PaginatedCoursesModelCopyWithImpl<$Res,
        _$PaginatedCoursesModelImpl>
    implements _$$PaginatedCoursesModelImplCopyWith<$Res> {
  __$$PaginatedCoursesModelImplCopyWithImpl(_$PaginatedCoursesModelImpl _value,
      $Res Function(_$PaginatedCoursesModelImpl) _then)
      : super(_value, _then);

  /// Create a copy of PaginatedCoursesModel
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? courses = null,
    Object? total = null,
    Object? page = null,
    Object? pageSize = null,
    Object? totalPages = null,
  }) {
    return _then(_$PaginatedCoursesModelImpl(
      courses: null == courses
          ? _value._courses
          : courses // ignore: cast_nullable_to_non_nullable
              as List<CourseModel>,
      total: null == total
          ? _value.total
          : total // ignore: cast_nullable_to_non_nullable
              as int,
      page: null == page
          ? _value.page
          : page // ignore: cast_nullable_to_non_nullable
              as int,
      pageSize: null == pageSize
          ? _value.pageSize
          : pageSize // ignore: cast_nullable_to_non_nullable
              as int,
      totalPages: null == totalPages
          ? _value.totalPages
          : totalPages // ignore: cast_nullable_to_non_nullable
              as int,
    ));
  }
}

/// @nodoc
@JsonSerializable()
class _$PaginatedCoursesModelImpl implements _PaginatedCoursesModel {
  const _$PaginatedCoursesModelImpl(
      {required final List<CourseModel> courses,
      required this.total,
      required this.page,
      @JsonKey(name: 'page_size') required this.pageSize,
      @JsonKey(name: 'total_pages') required this.totalPages})
      : _courses = courses;

  factory _$PaginatedCoursesModelImpl.fromJson(Map<String, dynamic> json) =>
      _$$PaginatedCoursesModelImplFromJson(json);

  final List<CourseModel> _courses;
  @override
  List<CourseModel> get courses {
    if (_courses is EqualUnmodifiableListView) return _courses;
    // ignore: implicit_dynamic_type
    return EqualUnmodifiableListView(_courses);
  }

  @override
  final int total;
  @override
  final int page;
  @override
  @JsonKey(name: 'page_size')
  final int pageSize;
  @override
  @JsonKey(name: 'total_pages')
  final int totalPages;

  @override
  String toString() {
    return 'PaginatedCoursesModel(courses: $courses, total: $total, page: $page, pageSize: $pageSize, totalPages: $totalPages)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$PaginatedCoursesModelImpl &&
            const DeepCollectionEquality().equals(other._courses, _courses) &&
            (identical(other.total, total) || other.total == total) &&
            (identical(other.page, page) || other.page == page) &&
            (identical(other.pageSize, pageSize) ||
                other.pageSize == pageSize) &&
            (identical(other.totalPages, totalPages) ||
                other.totalPages == totalPages));
  }

  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  int get hashCode => Object.hash(
      runtimeType,
      const DeepCollectionEquality().hash(_courses),
      total,
      page,
      pageSize,
      totalPages);

  /// Create a copy of PaginatedCoursesModel
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  @pragma('vm:prefer-inline')
  _$$PaginatedCoursesModelImplCopyWith<_$PaginatedCoursesModelImpl>
      get copyWith => __$$PaginatedCoursesModelImplCopyWithImpl<
          _$PaginatedCoursesModelImpl>(this, _$identity);

  @override
  Map<String, dynamic> toJson() {
    return _$$PaginatedCoursesModelImplToJson(
      this,
    );
  }
}

abstract class _PaginatedCoursesModel implements PaginatedCoursesModel {
  const factory _PaginatedCoursesModel(
          {required final List<CourseModel> courses,
          required final int total,
          required final int page,
          @JsonKey(name: 'page_size') required final int pageSize,
          @JsonKey(name: 'total_pages') required final int totalPages}) =
      _$PaginatedCoursesModelImpl;

  factory _PaginatedCoursesModel.fromJson(Map<String, dynamic> json) =
      _$PaginatedCoursesModelImpl.fromJson;

  @override
  List<CourseModel> get courses;
  @override
  int get total;
  @override
  int get page;
  @override
  @JsonKey(name: 'page_size')
  int get pageSize;
  @override
  @JsonKey(name: 'total_pages')
  int get totalPages;

  /// Create a copy of PaginatedCoursesModel
  /// with the given fields replaced by the non-null parameter values.
  @override
  @JsonKey(includeFromJson: false, includeToJson: false)
  _$$PaginatedCoursesModelImplCopyWith<_$PaginatedCoursesModelImpl>
      get copyWith => throw _privateConstructorUsedError;
}
