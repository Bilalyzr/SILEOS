import 'package:flutter/foundation.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';
import '../../../../core/network/network_provider.dart';
import '../../../../core/utils/failure_logger.dart';
import '../../data/datasources/course_remote_datasource.dart';
import '../../data/repositories/course_repository_impl.dart';
import '../../data/models/course_model.dart';
import '../../domain/entities/course.dart';
import '../../domain/entities/lesson.dart';
import '../../domain/entities/certificate.dart';
import '../../domain/repositories/course_repository.dart';
import '../../domain/usecases/course_usecases.dart';

part 'course_provider.g.dart';

@riverpod
CourseRemoteDataSource courseRemoteDataSource(CourseRemoteDataSourceRef ref) {
  return CourseRemoteDataSourceImpl(
    apiClient: ref.watch(apiClientProvider),
  );
}

@riverpod
CourseRepository courseRepository(CourseRepositoryRef ref) {
  return CourseRepositoryImpl(
    remoteDataSource: ref.watch(courseRemoteDataSourceProvider),
  );
}

@riverpod
GetCoursesUseCase getCoursesUseCase(GetCoursesUseCaseRef ref) {
  return GetCoursesUseCase(ref.watch(courseRepositoryProvider));
}

@riverpod
GetCourseByIdUseCase getCourseByIdUseCase(GetCourseByIdUseCaseRef ref) {
  return GetCourseByIdUseCase(ref.watch(courseRepositoryProvider));
}

@riverpod
GetLessonByIdUseCase getLessonByIdUseCase(GetLessonByIdUseCaseRef ref) {
  return GetLessonByIdUseCase(ref.watch(courseRepositoryProvider));
}

@riverpod
CompleteLessonUseCase completeLessonUseCase(CompleteLessonUseCaseRef ref) {
  return CompleteLessonUseCase(ref.watch(courseRepositoryProvider));
}

@riverpod
GetCertificateForCourseUseCase getCertificateForCourseUseCase(GetCertificateForCourseUseCaseRef ref) {
  return GetCertificateForCourseUseCase(ref.watch(courseRepositoryProvider));
}

@riverpod
Future<PaginatedCourses> courses(
  CoursesRef ref, {
  int page = 1,
  int pageSize = 20,
  String? category,
  String? search,
}) async {
  final result = await ref.watch(getCoursesUseCaseProvider).call(
        page: page,
        pageSize: pageSize,
        category: category,
        search: search,
      );

  return result.fold(
    (failure) {
      logFailure(
        'courses page=$page'
        '${category != null ? ' category=$category' : ''}'
        '${search != null ? ' search=$search' : ''}',
        failure,
      );
      throw failure;
    },
    (paginated) => paginated,
  );
}

@riverpod
Future<List<Course>> myCourses(MyCoursesRef ref) async {
  final client = ref.watch(apiClientProvider);
  try {
    final response = await client.get('/api/v1/users/my-courses');
    
    if (response.statusCode == 200) {
      final List<dynamic> data = response.data is List ? response.data : (response.data['courses'] ?? []);
      return data.map((json) {
        try {
          return CourseModel.fromJson(json as Map<String, dynamic>).toEntity();
        } catch (e) {
          if (kDebugMode) debugPrint('Error mapping my-course: $e');
          // If mapping fails, try to return a partial course or skip
          rethrow;
        }
      }).toList();
    } else {
      throw Exception('Failed to load enrolled courses');
    }
  } catch (e) {
    // If it's a 401, return empty list (not logged in) or let it throw
    rethrow;
  }
}

@riverpod
Future<Course> courseById(CourseByIdRef ref, String id) async {
  final result = await ref.watch(getCourseByIdUseCaseProvider).call(id);

  return result.fold(
    (failure) {
      logFailure('course detail id=$id', failure);
      throw failure;
    },
    (course) => course,
  );
}

@riverpod
Future<Lesson> lessonById(LessonByIdRef ref, String id) async {
  final result = await ref.watch(getLessonByIdUseCaseProvider).call(id);

  return result.fold(
    (failure) => throw failure,
    (lesson) => lesson,
  );
}

@riverpod
Future<Certificate?> certificateForCourse(CertificateForCourseRef ref, int courseId) async {
  final result = await ref.watch(getCertificateForCourseUseCaseProvider).call(courseId);

  return result.fold(
    (failure) => throw failure,
    (certificate) => certificate,
  );
}

@riverpod
Future<Map<String, dynamic>> courseReviews(CourseReviewsRef ref, String courseId) async {
  final client = ref.watch(apiClientProvider);
  final response = await client.get('/api/v1/courses/$courseId/reviews');
  if (response.statusCode == 200) {
    return response.data as Map<String, dynamic>;
  } else {
    throw Exception('Failed to load reviews');
  }
}

