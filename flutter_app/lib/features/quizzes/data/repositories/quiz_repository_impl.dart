import 'package:dartz/dartz.dart';
import '../../../../core/errors/exceptions.dart';
import '../../../../core/errors/failures.dart';
import '../../domain/entities/quiz.dart';
import '../../domain/repositories/quiz_repository.dart';
import '../datasources/quiz_remote_datasource.dart';

class QuizRepositoryImpl implements QuizRepository {
  final QuizRemoteDataSource remoteDataSource;

  QuizRepositoryImpl({required this.remoteDataSource});

  @override
  Future<Either<Failure, Quiz>> getQuiz({
    required int courseId,
    required int quizId,
  }) async {
    try {
      final model = await remoteDataSource.getQuiz(
        courseId: courseId,
        quizId: quizId,
      );
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
  Future<Either<Failure, Map<String, dynamic>>> submitQuiz({
    required int courseId,
    required int quizId,
    required Map<String, dynamic> answers,
  }) async {
    try {
      final result = await remoteDataSource.submitQuiz(
        courseId: courseId,
        quizId: quizId,
        answers: answers,
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

  @override
  Future<Either<Failure, int>> startQuizAttempt(int quizId) async {
    try {
      final result = await remoteDataSource.startQuizAttempt(quizId);
      return Right(result['attempt_id']);
    } on ServerException catch (e) {
      return Left(Failure.server(message: e.message, statusCode: e.statusCode));
    } catch (e) {
      return Left(Failure.unknown(message: e.toString()));
    }
  }

  @override
  Future<Either<Failure, Map<String, dynamic>>> submitQuizAttempt({
    required int attemptId,
    required Map<String, dynamic> answers,
  }) async {
    try {
      final result = await remoteDataSource.submitQuizAttempt(
        attemptId: attemptId,
        answers: answers,
      );
      return Right(result);
    } on ServerException catch (e) {
      return Left(Failure.server(message: e.message, statusCode: e.statusCode));
    } catch (e) {
      return Left(Failure.unknown(message: e.toString()));
    }
  }
}
