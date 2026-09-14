import 'package:freezed_annotation/freezed_annotation.dart';
import '../../domain/entities/quiz.dart';

part 'quiz_model.freezed.dart';
part 'quiz_model.g.dart';

@freezed
class QuizModel with _$QuizModel {
  const factory QuizModel({
    required int id,
    required String title,
    String? description,
    @JsonKey(name: 'timeLimit') required int timeLimit,
    @JsonKey(name: 'passingScore') required int passingScore,
    @JsonKey(name: 'maxAttempts') required int maxAttempts,
    @Default([]) List<QuizQuestionModel> questions,
  }) = _QuizModel;

  const QuizModel._();

  factory QuizModel.fromJson(Map<String, dynamic> json) =>
      _$QuizModelFromJson(json);

  Quiz toEntity() {
    return Quiz(
      id: id.toString(),
      title: title,
      description: description,
      timeLimit: timeLimit,
      passingGrade: passingScore,
      maxAttempts: maxAttempts,
      questions: questions.map((q) => q.toEntity()).toList(),
    );
  }
}

@freezed
class QuizQuestionModel with _$QuizQuestionModel {
  const factory QuizQuestionModel({
    required String id,
    required String type,
    required String question,
    required double points,
    String? explanation,
    String? imageUrl,
    @Default([]) List<String> options,
    dynamic correctAnswer,
  }) = _QuizQuestionModel;

  const QuizQuestionModel._();

  factory QuizQuestionModel.fromJson(Map<String, dynamic> json) =>
      _$QuizQuestionModelFromJson(json);

  QuizQuestion toEntity() {
    return QuizQuestion(
      id: id,
      title: question,
      description: explanation,
      type: type,
      points: points,
      options: options.asMap().entries.map((e) {
        return QuizAnswerOption(
          id: e.key.toString(),
          title: e.value,
          isCorrect: correctAnswer is int && correctAnswer == e.key,
        );
      }).toList(),
    );
  }
}

@freezed
class QuizAttemptModel with _$QuizAttemptModel {
  const factory QuizAttemptModel({
    @JsonKey(name: 'attempt_id') int? attemptId,
    @JsonKey(name: 'quiz_id') int? quizId,
    @JsonKey(name: 'total_marks') double? totalMarks,
    @JsonKey(name: 'earned_marks') double? earnedMarks,
    double? percentage,
    bool? passed,
    @JsonKey(name: 'passing_grade') int? passingGrade,
  }) = _QuizAttemptModel;

  factory QuizAttemptModel.fromJson(Map<String, dynamic> json) =>
      _$QuizAttemptModelFromJson(json);
}
