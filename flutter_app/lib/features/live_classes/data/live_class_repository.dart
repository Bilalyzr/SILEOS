// lib/features/live_classes/data/live_class_repository.dart
import 'package:dartz/dartz.dart';
import '../../../core/errors/exceptions.dart';
import '../../../core/errors/failures.dart';
import '../domain/entities/live_class.dart';
import '../domain/repositories/live_class_repository.dart';
import 'live_class_api.dart';

/// Mirrors AssignmentRepositoryImpl / CourseRepositoryImpl: catch
/// ServerException/AppException, map into Failure via Either.
class LiveClassRepositoryImpl implements LiveClassRepository {
  final LiveClassApi api;

  LiveClassRepositoryImpl({required this.api});

  @override
  Future<Either<Failure, List<LiveClass>>> getClasses({String scope = 'upcoming'}) async {
    try {
      final models = await api.getClasses(scope: scope);
      return Right(models.map((m) => m.toEntity()).toList());
    } on ServerException catch (e) {
      return Left(Failure.server(message: e.message, statusCode: e.statusCode));
    } on AppException catch (e) {
      return Left(_mapAppException(e));
    } catch (e) {
      return Left(Failure.unknown(message: e.toString()));
    }
  }

  @override
  Future<Either<Failure, LiveClass>> getClassById(int id) async {
    try {
      final model = await api.getClassById(id);
      return Right(model.toEntity());
    } on ServerException catch (e) {
      return Left(Failure.server(message: e.message, statusCode: e.statusCode));
    } on AppException catch (e) {
      return Left(_mapAppException(e));
    } catch (e) {
      return Left(Failure.unknown(message: e.toString()));
    }
  }

  @override
  Future<Either<Failure, List<LiveClass>>> getLiveNow() async {
    try {
      final models = await api.getLiveNow();
      return Right(models.map((m) => m.toEntity()).toList());
    } on ServerException catch (e) {
      return Left(Failure.server(message: e.message, statusCode: e.statusCode));
    } on AppException catch (e) {
      return Left(_mapAppException(e));
    } catch (e) {
      return Left(Failure.unknown(message: e.toString()));
    }
  }

  @override
  Future<Either<Failure, LiveClassJoinToken>> joinToken(int classId) async {
    try {
      final model = await api.joinToken(classId);
      return Right(model.toEntity());
    } on ServerException catch (e) {
      return Left(Failure.server(message: e.message, statusCode: e.statusCode));
    } on AppException catch (e) {
      return Left(_mapAppException(e));
    } catch (e) {
      return Left(Failure.unknown(message: e.toString()));
    }
  }

  @override
  Future<Either<Failure, void>> heartbeat(int classId) async {
    try {
      await api.heartbeat(classId);
      return const Right(null);
    } on ServerException catch (e) {
      return Left(Failure.server(message: e.message, statusCode: e.statusCode));
    } on AppException catch (e) {
      return Left(_mapAppException(e));
    } catch (e) {
      return Left(Failure.unknown(message: e.toString()));
    }
  }

  @override
  Future<Either<Failure, LiveClassRecordingPlayback?>> getRecordingPlayback(int classId) async {
    try {
      final model = await api.getRecordingPlayback(classId);
      if (model == null) return const Right(null);
      return Right(LiveClassRecordingPlayback(
        videoId: model.videoId,
        hlsUrl: model.hlsUrl,
        signed: model.signed,
        expiresIn: model.expiresIn,
      ));
    } on ServerException catch (e) {
      return Left(Failure.server(message: e.message, statusCode: e.statusCode));
    } on AppException catch (e) {
      return Left(_mapAppException(e));
    } catch (e) {
      return Left(Failure.unknown(message: e.toString()));
    }
  }

  Failure _mapAppException(AppException e) {
    if (e is UnauthorizedException) return Failure.unauthorized(message: e.message);
    if (e is ForbiddenException) return Failure.forbidden(message: e.message);
    if (e is NotFoundException) return Failure.notFound(message: e.message);
    if (e is ValidationException) {
      return Failure.validation(message: e.message, fieldErrors: e.fieldErrors);
    }
    if (e is NetworkException) return Failure.network(message: e.message);
    return Failure.unknown(message: e.message);
  }
}
