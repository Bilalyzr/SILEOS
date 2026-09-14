import '../../domain/repositories/course_repository.dart';
import '../entities/lesson.dart';
import '../entities/certificate.dart';

class GetCoursesUseCase {
  final CourseRepository repository;

  GetCoursesUseCase(this.repository);

  Future call({
    int page = 1,
    int pageSize = 20,
    String? category,
    String? search,
    String? level,
    String? priceType,
    String? sortBy,
  }) {
    return repository.getCourses(
      page: page,
      pageSize: pageSize,
      category: category,
      search: search,
      level: level,
      priceType: priceType,
      sortBy: sortBy,
    );
  }
}

class GetCourseByIdUseCase {
  final CourseRepository repository;

  GetCourseByIdUseCase(this.repository);

  Future call(String id) {
    return repository.getCourseById(id);
  }
}

class GetLessonByIdUseCase {
  final CourseRepository repository;

  GetLessonByIdUseCase(this.repository);

  Future call(String id) {
    return repository.getLessonById(id);
  }
}

class GetBunnyPlaybackUrlUseCase {
  final CourseRepository repository;

  GetBunnyPlaybackUrlUseCase(this.repository);

  Future call(String videoId, {bool preview = false}) {
    return repository.getBunnyPlaybackUrl(videoId, preview: preview);
  }
}

class CompleteLessonUseCase {
  final CourseRepository repository;

  CompleteLessonUseCase(this.repository);

  Future call({required int courseId, required int lessonId}) {
    return repository.completeLesson(courseId: courseId, lessonId: lessonId);
  }
}

class GetCertificateForCourseUseCase {
  final CourseRepository repository;

  GetCertificateForCourseUseCase(this.repository);

  Future call(int courseId) {
    return repository.getCertificateForCourse(courseId);
  }
}
