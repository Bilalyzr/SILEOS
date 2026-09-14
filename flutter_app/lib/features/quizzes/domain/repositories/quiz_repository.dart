import 'package:dartz/dartz.dart';
import '../../../../core/errors/failures.dart';
import '../entities/quiz.dart';

abstract class QuizRepository {
  Future<Either<Failure, Quiz>> getQuiz({
    required int courseId,
    required int quizId,
  });

  Future<Either<Failure, Map<String, dynamic>>> submitQuiz({
    required int courseId,
    required int quizId,
    required Map<String, dynamic> answers,
  });

  Future<Either<Failure, int>> startQuizAttempt(int quizId);

  Future<Either<Failure, Map<String, dynamic>>> submitQuizAttempt({
    required int attemptId,
    required Map<String, dynamic> answers,
  });
}
