import 'package:freezed_annotation/freezed_annotation.dart';
import '../../domain/entities/course.dart';
import 'lesson_model.dart';

part 'course_model.freezed.dart';
part 'course_model.g.dart';

@freezed
class CourseModel with _$CourseModel {
  const factory CourseModel({
    required int id,
    required String title,
    required String description,
    String? content,
    @JsonKey(name: 'featured_image', defaultValue: '') required String featuredImage,
    @JsonKey(name: 'thumbnail') String? thumbnail,
    @JsonKey(name: 'intro_video') String? introVideo,
    required double price,
    @JsonKey(name: 'sale_price') double? salePrice,
    required String level,
    required String category,
    required InstructorModel instructor,
    required CourseStatsModel stats,
    @Default(0.0) double rating,
    @JsonKey(name: 'is_enrolled') @Default(false) bool isEnrolled,
    @JsonKey(name: 'num_offline_workshops') @Default(0) int numOfflineWorkshops,
    @JsonKey(name: 'num_hours') @Default(0) int numHours,
    String? institution,
    @JsonKey(name: 'created_at') required String createdAt,
    @JsonKey(name: 'updated_at') required String updatedAt,
    String? slug,
    @Default([]) List<LessonModel> lessons,
    @Default([]) List<QuizModel> quizzes,
    @Default([]) List<AssignmentModel> assignments,
    @Default(0.0) double progress,
    @Default([]) List<String> requirements,
    @Default([]) List<String> benefits,
    @JsonKey(name: 'target_audience') @Default([]) List<String> targetAudience,
    @JsonKey(name: 'material_includes') @Default([]) List<String> materialIncludes,
    @Default([]) List<String> tags,
    }) = _CourseModel;

    const CourseModel._();

    factory CourseModel.fromJson(Map<String, dynamic> json) =>
      _$CourseModelFromJson(json);

    Course toEntity() {
    return Course(
      id: id.toString(),
      title: title,
      description: description,
      content: content,
      featuredImage: featuredImage.isNotEmpty ? featuredImage : (thumbnail ?? ''),
      introVideo: introVideo,
      price: price,
      salePrice: salePrice,
      level: level,
      category: category,
      instructor: instructor.toEntity(),
      stats: stats.toEntity(),
      rating: rating,
      isEnrolled: isEnrolled,
      numOfflineWorkshops: numOfflineWorkshops,
      numHours: numHours,
      institution: institution,
      createdAt: DateTime.parse(createdAt),
      updatedAt: DateTime.parse(updatedAt),
      slug: slug,
      lessons: lessons.map((m) => m.toEntity()).toList(),
      quizzes: quizzes.map((m) => m.toEntity()).toList(),
      assignments: assignments.map((m) => m.toEntity()).toList(),
      progress: progress,
      requirements: requirements,
      benefits: benefits,
      targetAudience: targetAudience,
      materialIncludes: materialIncludes,
      tags: tags,
    );
    }
    }

@freezed
class InstructorModel with _$InstructorModel {
  const factory InstructorModel({
    required int id,
    required String name,
    required String avatar,
  }) = _InstructorModel;

  const InstructorModel._();

  factory InstructorModel.fromJson(Map<String, dynamic> json) =>
      _$InstructorModelFromJson(json);

  Instructor toEntity() {
    return Instructor(
      id: id.toString(),
      name: name,
      avatar: avatar,
    );
  }
}

@freezed
class CourseStatsModel with _$CourseStatsModel {
  const factory CourseStatsModel({
    required int lessons,
    required int quizzes,
    required int duration,
    required int students,
  }) = _CourseStatsModel;

  const CourseStatsModel._();

  factory CourseStatsModel.fromJson(Map<String, dynamic> json) =>
      _$CourseStatsModelFromJson(json);

  CourseStats toEntity() {
    return CourseStats(
      lessons: lessons,
      quizzes: quizzes,
      duration: duration,
      students: students,
    );
  }
}

@freezed
class PaginatedCoursesModel with _$PaginatedCoursesModel {
  const factory PaginatedCoursesModel({
    required List<CourseModel> courses,
    required int total,
    required int page,
    @JsonKey(name: 'page_size') required int pageSize,
    @JsonKey(name: 'total_pages') required int totalPages,
  }) = _PaginatedCoursesModel;

  factory PaginatedCoursesModel.fromJson(Map<String, dynamic> json) =>
      _$PaginatedCoursesModelFromJson(json);
}
