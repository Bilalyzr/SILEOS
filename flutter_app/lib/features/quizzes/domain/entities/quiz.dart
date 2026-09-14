import 'package:freezed_annotation/freezed_annotation.dart';

part 'quiz.freezed.dart';

@freezed
class Quiz with _$Quiz {
  const factory Quiz({
    required String id,
    required String title,
    String? description,
    required int timeLimit,
    required int passingGrade,
    required int maxAttempts,
    required List<QuizQuestion> questions,
  }) = _Quiz;
}

@freezed
class QuizQuestion with _$QuizQuestion {
  const factory QuizQuestion({
    required String id,
    required String title,
    String? description,
    required String type,
    required double points,
    required List<QuizAnswerOption> options,
  }) = _QuizQuestion;
}

@freezed
class QuizAnswerOption with _$QuizAnswerOption {
  const factory QuizAnswerOption({
    required String id,
    required String title,
    @Default(false) bool isCorrect,
  }) = _QuizAnswerOption;
}

@freezed
class QuizAttempt with _$QuizAttempt {
  const factory QuizAttempt({
    required String id,
    required String quizId,
    required String userId,
    required String status,
    required int totalQuestions,
    required int answeredQuestions,
    required double totalMarks,
    required double earnedMarks,
    DateTime? startedAt,
    DateTime? endedAt,
  }) = _QuizAttempt;
}
