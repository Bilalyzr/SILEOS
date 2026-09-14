import 'dart:io';
import 'package:dartz/dartz.dart';
import '../../../../core/errors/exceptions.dart';
import '../../../../core/errors/failures.dart';
import '../../domain/entities/assignment.dart';
import '../../domain/repositories/assignment_repository.dart';
import '../datasources/assignment_remote_datasource.dart';

class AssignmentRepositoryImpl implements AssignmentRepository {
  final AssignmentRemoteDataSource remoteDataSource;

  AssignmentRepositoryImpl({required this.remoteDataSource});

  @override
  Future<Either<Failure, Assignment>> getAssignment(int id) async {
    try {
      final model = await remoteDataSource.getAssignment(id);
      return Right(model.toEntity());
    } on ServerException catch (e) {
      return Left(Failure.server(message: e.message, statusCode: e.statusCode));
    } catch (e) {
      return Left(Failure.unknown(message: e.toString()));
    }
  }

  @override
  Future<Either<Failure, AssignmentSubmission>> submitAssignment({
    required int assignmentId,
    required String content,
    File? file,
  }) async {
    try {
      final model = await remoteDataSource.submitAssignment(
        assignmentId: assignmentId,
        content: content,
        file: file,
      );
      return Right(model.toEntity());
    } on ServerException catch (e) {
      return Left(Failure.server(message: e.message, statusCode: e.statusCode));
    } catch (e) {
      return Left(Failure.unknown(message: e.toString()));
    }
  }
}
