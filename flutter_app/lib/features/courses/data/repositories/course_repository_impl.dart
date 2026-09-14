import 'package:dartz/dartz.dart';
import '../../../../core/errors/exceptions.dart';
import '../../../../core/errors/failures.dart';
import '../../domain/entities/course.dart';
import '../../domain/entities/lesson.dart';
import '../../domain/entities/certificate.dart';
import '../../domain/repositories/course_repository.dart';
import '../datasources/course_remote_datasource.dart';

class CourseRepositoryImpl implements CourseRepository {
  final CourseRemoteDataSource remoteDataSource;

  CourseRepositoryImpl({required this.remoteDataSource});

  @override
  Future<Either<Failure, PaginatedCourses>> getCourses({
    int page = 1,
    int pageSize = 20,
    String? category,
    String? search,
    String? level,
    String? priceType,
    String? sortBy,
  }) async {
    try {
      final paginatedModel = await remoteDataSource.getCourses(
        page: page,
        pageSize: pageSize,
        category: category,
        search: search,
      level: level,
      priceType: priceType,
      sortBy: sortBy,
      );
      final entity = PaginatedCourses(
        courses: paginatedModel.courses.map((m) => m.toEntity()).toList(),
        total: paginatedModel.total,
        page: paginatedModel.page,
        pageSize: paginatedModel.pageSize,
        totalPages: paginatedModel.totalPages,
      );
      return Right(entity);
    } on ServerException catch (e) {
      return Left(Failure.server(message: e.message, statusCode: e.statusCode));
    } on NetworkException catch (e) {
      return Left(Failure.network(message: e.message));
    } catch (e) {
      return Left(Failure.unknown(message: e.toString()));
    }
  }

  @override
  Future<Either<Failure, Course>> getCourseById(String id) async {
    try {
      final model = await remoteDataSource.getCourseById(id);
      return Right(model.toEntity());
    } on ServerException catch (e) {
      return Left(Failure.server(message: e.message, statusCode: e.statusCode));
    } on NetworkException catch (e) {
      return Left(Failure.network(message: e.message));
    } catch (e) {
      return Left(Failure.unknown(message: e.toString()));
    }
  }

  @override
  Future<Either<Failure, Lesson>> getLessonById(String id) async {
    try {
      final model = await remoteDataSource.getLessonById(id);
      return Right(model.toEntity());
    } on ServerException catch (e) {
      return Left(Failure.server(message: e.message, statusCode: e.statusCode));
    } on NetworkException catch (e) {
      return Left(Failure.network(message: e.message));
    } catch (e) {
      return Left(Failure.unknown(message: e.toString()));
    }
  }

  @override
  Future<Either<Failure, String>> getBunnyPlaybackUrl(String videoId,
      {bool preview = false}) async {
    try {
      final url =
          await remoteDataSource.getBunnyPlaybackUrl(videoId, preview: preview);
      if (url == null || url.isEmpty) {
        return const Left(Failure.unknown(message: 'No playback URL returned'));
      }
      return Right(url);
    } on ServerException catch (e) {
      return Left(Failure.server(message: e.message, statusCode: e.statusCode));
    } on NetworkException catch (e) {
      return Left(Failure.network(message: e.message));
    } catch (e) {
      return Left(Failure.unknown(message: e.toString()));
    }
  }

  @override
  Future<Either<Failure, void>> completeLesson({
    required int courseId,
    required int lessonId,
  }) async {
    try {
      await remoteDataSource.completeLesson(
        courseId: courseId,
        lessonId: lessonId,
      );
      return const Right(null);
    } on ServerException catch (e) {
      return Left(Failure.server(message: e.message, statusCode: e.statusCode));
    } on NetworkException catch (e) {
      return Left(Failure.network(message: e.message));
    } catch (e) {
      return Left(Failure.unknown(message: e.toString()));
    }
  }

  @override
  Future<Either<Failure, Certificate?>> getCertificateForCourse(int courseId) async {
    try {
      final data = await remoteDataSource.getCertificateForCourse(courseId);
      if (data == null) return const Right(null);
      
      final certificate = Certificate(
        id: data['id'].toString(),
        courseId: data['course_id'].toString(),
        userId: data['user_id'].toString(),
        certificateUrl: data['certificate_url'] ?? '',
        verificationCode: data['verification_code'] ?? '',
        issuedAt: DateTime.parse(data['issued_at']),
      );
      return Right(certificate);
    } on ServerException catch (e) {
      return Left(Failure.server(message: e.message, statusCode: e.statusCode));
    } on NetworkException catch (e) {
      return Left(Failure.network(message: e.message));
    } catch (e) {
      return Left(Failure.unknown(message: e.toString()));
    }
  }

  @override
  Future<Either<Failure, void>> enroll(int courseId, {String? couponCode}) async {
    try {
      await remoteDataSource.enroll(courseId, couponCode: couponCode);
      return const Right(null);
    } on ServerException catch (e) {
      return Left(Failure.server(message: e.message, statusCode: e.statusCode));
    } on NetworkException catch (e) {
      return Left(Failure.network(message: e.message));
    } catch (e) {
      return Left(Failure.unknown(message: e.toString()));
    }
  }

  @override
  Future<Either<Failure, Map<String, dynamic>>> createPaymentOrder(int courseId, {String? couponCode}) async {
    try {
      final orderData = await remoteDataSource.createPaymentOrder(courseId, couponCode: couponCode);
      return Right(orderData);
    } on ServerException catch (e) {
      return Left(Failure.server(message: e.message, statusCode: e.statusCode));
    } on NetworkException catch (e) {
      return Left(Failure.network(message: e.message));
    } catch (e) {
      return Left(Failure.unknown(message: e.toString()));
    }
  }

  @override
  Future<Either<Failure, void>> verifyPayment(Map<String, dynamic> paymentData) async {
    try {
      await remoteDataSource.verifyPayment(paymentData);
      return const Right(null);
    } on ServerException catch (e) {
      return Left(Failure.server(message: e.message, statusCode: e.statusCode));
    } on NetworkException catch (e) {
      return Left(Failure.network(message: e.message));
    } catch (e) {
      return Left(Failure.unknown(message: e.toString()));
    }
  }

  @override
  Future<Either<Failure, Map<String, dynamic>>> validateCoupon({
    required String code,
    required int courseId,
    required double totalAmount,
  }) async {
    try {
      final result = await remoteDataSource.validateCoupon(
        code: code,
        courseId: courseId,
        totalAmount: totalAmount,
      );
      return Right(result);
    } on ServerException catch (e) {
      return Left(Failure.server(message: e.message, statusCode: e.statusCode));
    } on NetworkException catch (e) {
      return Left(Failure.network(message: e.message));
    } catch (e) {
      return Left(Failure.unknown(message: e.toString()));
    }
  }
}
