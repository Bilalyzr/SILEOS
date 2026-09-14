import 'package:freezed_annotation/freezed_annotation.dart';
import 'lesson.dart';

part 'course.freezed.dart';

@freezed
class Course with _$Course {
  const factory Course({
    required String id,
    required String title,
    required String description,
    String? content,
    required String featuredImage,
    String? introVideo,
    required double price,
    double? salePrice,
    required String level,
    required String category,
    required Instructor instructor,
    required CourseStats stats,
    required double rating,
    @Default(false) bool isEnrolled,
    @Default(0) int numOfflineWorkshops,
    @Default(0) int numHours,
    String? institution,
    required DateTime createdAt,
    required DateTime updatedAt,
    String? slug,
    @Default([]) List<Lesson> lessons,
    @Default([]) List<Quiz> quizzes,
    @Default([]) List<Assignment> assignments,
    @Default(0) double progress,
    @Default([]) List<String> requirements,
    @Default([]) List<String> benefits,
    @Default([]) List<String> targetAudience,
    @Default([]) List<String> materialIncludes,
    @Default([]) List<String> tags,
  }) = _Course;
}

@freezed
class Instructor with _$Instructor {
  const factory Instructor({
    required String id,
    required String name,
    required String avatar,
  }) = _Instructor;
}

@freezed
class CourseStats with _$CourseStats {
  const factory CourseStats({
    required int lessons,
    required int quizzes,
    required int duration,
    required int students,
  }) = _CourseStats;
}

class PaginatedCourses {
  final List<Course> courses;
  final int total;
  final int page;
  final int pageSize;
  final int totalPages;

  const PaginatedCourses({
    required this.courses,
    required this.total,
    required this.page,
    required this.pageSize,
    required this.totalPages,
  });
}
