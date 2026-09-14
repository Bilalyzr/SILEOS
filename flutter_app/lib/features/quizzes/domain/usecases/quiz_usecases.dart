import 'package:dartz/dartz.dart';
import '../../../../core/errors/failures.dart';
import '../entities/quiz.dart';
import '../repositories/quiz_repository.dart';

class GetQuizUseCase {
  final QuizRepository repository;

  GetQuizUseCase(this.repository);

  Future<Either<Failure, Quiz>> call({
    required int courseId,
    required int quizId,
  }) {
    return repository.getQuiz(courseId: courseId, quizId: quizId);
  }
}

class StartQuizAttemptUseCase {
  final QuizRepository repository;

  StartQuizAttemptUseCase(this.repository);

  Future<Either<Failure, int>> call(int quizId) {
    return repository.startQuizAttempt(quizId);
  }
}

class SubmitQuizAttemptUseCase {
  final QuizRepository repository;

  SubmitQuizAttemptUseCase(this.repository);

  Future<Either<Failure, Map<String, dynamic>>> call({
    required int attemptId,
    required Map<String, dynamic> answers,
  }) {
    return repository.submitQuizAttempt(
      attemptId: attemptId,
      answers: answers,
    );
  }
}
