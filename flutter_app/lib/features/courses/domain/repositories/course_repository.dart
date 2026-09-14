import 'package:dartz/dartz.dart';
import '../../../../core/errors/failures.dart';
import '../entities/course.dart';
import '../entities/lesson.dart';
import '../entities/certificate.dart';

abstract class CourseRepository {
  Future<Either<Failure, PaginatedCourses>> getCourses({
    int page = 1,
    int pageSize = 20,
    String? category,
    String? search,
    String? level,
    String? priceType,
    String? sortBy,
  });

  Future<Either<Failure, Course>> getCourseById(String id);

  Future<Either<Failure, Lesson>> getLessonById(String id);

  Future<Either<Failure, String>> getBunnyPlaybackUrl(String videoId,
      {bool preview = false});

  Future<Either<Failure, void>> completeLesson({
    required int courseId,
    required int lessonId,
  });

  Future<Either<Failure, Certificate?>> getCertificateForCourse(int courseId);

  Future<Either<Failure, void>> enroll(int courseId, {String? couponCode});

  Future<Either<Failure, Map<String, dynamic>>> createPaymentOrder(int courseId, {String? couponCode});

  Future<Either<Failure, void>> verifyPayment(Map<String, dynamic> paymentData);

  Future<Either<Failure, Map<String, dynamic>>> validateCoupon({
    required String code,
    required int courseId,
    required double totalAmount,
  });
}
