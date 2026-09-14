import 'dart:io';
import 'package:dartz/dartz.dart';
import '../../../../core/errors/failures.dart';
import '../entities/assignment.dart';

abstract class AssignmentRepository {
  Future<Either<Failure, Assignment>> getAssignment(int id);
  Future<Either<Failure, AssignmentSubmission>> submitAssignment({
    required int assignmentId,
    required String content,
    File? file,
  });
}
