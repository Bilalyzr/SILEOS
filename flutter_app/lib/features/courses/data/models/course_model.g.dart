// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'course_model.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

_$CourseModelImpl _$$CourseModelImplFromJson(Map<String, dynamic> json) =>
    _$CourseModelImpl(
      id: (json['id'] as num).toInt(),
      title: json['title'] as String,
      description: json['description'] as String,
      content: json['content'] as String?,
      featuredImage: json['featured_image'] as String? ?? '',
      thumbnail: json['thumbnail'] as String?,
      introVideo: json['intro_video'] as String?,
      price: (json['price'] as num).toDouble(),
      salePrice: (json['sale_price'] as num?)?.toDouble(),
      level: json['level'] as String,
      category: json['category'] as String,
      instructor:
          InstructorModel.fromJson(json['instructor'] as Map<String, dynamic>),
      stats: CourseStatsModel.fromJson(json['stats'] as Map<String, dynamic>),
      rating: (json['rating'] as num?)?.toDouble() ?? 0.0,
      isEnrolled: json['is_enrolled'] as bool? ?? false,
      numOfflineWorkshops:
          (json['num_offline_workshops'] as num?)?.toInt() ?? 0,
      numHours: (json['num_hours'] as num?)?.toInt() ?? 0,
      institution: json['institution'] as String?,
      createdAt: json['created_at'] as String,
      updatedAt: json['updated_at'] as String,
      slug: json['slug'] as String?,
      lessons: (json['lessons'] as List<dynamic>?)
              ?.map((e) => LessonModel.fromJson(e as Map<String, dynamic>))
              .toList() ??
          const [],
      quizzes: (json['quizzes'] as List<dynamic>?)
              ?.map((e) => QuizModel.fromJson(e as Map<String, dynamic>))
              .toList() ??
          const [],
      assignments: (json['assignments'] as List<dynamic>?)
              ?.map((e) => AssignmentModel.fromJson(e as Map<String, dynamic>))
              .toList() ??
          const [],
      progress: (json['progress'] as num?)?.toDouble() ?? 0.0,
      requirements: (json['requirements'] as List<dynamic>?)
              ?.map((e) => e as String)
              .toList() ??
          const [],
      benefits: (json['benefits'] as List<dynamic>?)
              ?.map((e) => e as String)
              .toList() ??
          const [],
      targetAudience: (json['target_audience'] as List<dynamic>?)
              ?.map((e) => e as String)
              .toList() ??
          const [],
      materialIncludes: (json['material_includes'] as List<dynamic>?)
              ?.map((e) => e as String)
              .toList() ??
          const [],
      tags:
          (json['tags'] as List<dynamic>?)?.map((e) => e as String).toList() ??
              const [],
    );

Map<String, dynamic> _$$CourseModelImplToJson(_$CourseModelImpl instance) =>
    <String, dynamic>{
      'id': instance.id,
      'title': instance.title,
      'description': instance.description,
      'content': instance.content,
      'featured_image': instance.featuredImage,
      'thumbnail': instance.thumbnail,
      'intro_video': instance.introVideo,
      'price': instance.price,
      'sale_price': instance.salePrice,
      'level': instance.level,
      'category': instance.category,
      'instructor': instance.instructor,
      'stats': instance.stats,
      'rating': instance.rating,
      'is_enrolled': instance.isEnrolled,
      'num_offline_workshops': instance.numOfflineWorkshops,
      'num_hours': instance.numHours,
      'institution': instance.institution,
      'created_at': instance.createdAt,
      'updated_at': instance.updatedAt,
      'slug': instance.slug,
      'lessons': instance.lessons,
      'quizzes': instance.quizzes,
      'assignments': instance.assignments,
      'progress': instance.progress,
      'requirements': instance.requirements,
      'benefits': instance.benefits,
      'target_audience': instance.targetAudience,
      'material_includes': instance.materialIncludes,
      'tags': instance.tags,
    };

_$InstructorModelImpl _$$InstructorModelImplFromJson(
        Map<String, dynamic> json) =>
    _$InstructorModelImpl(
      id: (json['id'] as num).toInt(),
      name: json['name'] as String,
      avatar: json['avatar'] as String,
    );

Map<String, dynamic> _$$InstructorModelImplToJson(
        _$InstructorModelImpl instance) =>
    <String, dynamic>{
      'id': instance.id,
      'name': instance.name,
      'avatar': instance.avatar,
    };

_$CourseStatsModelImpl _$$CourseStatsModelImplFromJson(
        Map<String, dynamic> json) =>
    _$CourseStatsModelImpl(
      lessons: (json['lessons'] as num).toInt(),
      quizzes: (json['quizzes'] as num).toInt(),
      duration: (json['duration'] as num).toInt(),
      students: (json['students'] as num).toInt(),
    );

Map<String, dynamic> _$$CourseStatsModelImplToJson(
        _$CourseStatsModelImpl instance) =>
    <String, dynamic>{
      'lessons': instance.lessons,
      'quizzes': instance.quizzes,
      'duration': instance.duration,
      'students': instance.students,
    };

_$PaginatedCoursesModelImpl _$$PaginatedCoursesModelImplFromJson(
        Map<String, dynamic> json) =>
    _$PaginatedCoursesModelImpl(
      courses: (json['courses'] as List<dynamic>)
          .map((e) => CourseModel.fromJson(e as Map<String, dynamic>))
          .toList(),
      total: (json['total'] as num).toInt(),
      page: (json['page'] as num).toInt(),
      pageSize: (json['page_size'] as num).toInt(),
      totalPages: (json['total_pages'] as num).toInt(),
    );

Map<String, dynamic> _$$PaginatedCoursesModelImplToJson(
        _$PaginatedCoursesModelImpl instance) =>
    <String, dynamic>{
      'courses': instance.courses,
      'total': instance.total,
      'page': instance.page,
      'page_size': instance.pageSize,
      'total_pages': instance.totalPages,
    };
