import 'package:freezed_annotation/freezed_annotation.dart';
import '../../domain/entities/lesson.dart';

part 'lesson_model.freezed.dart';
part 'lesson_model.g.dart';

@freezed
class LessonModel with _$LessonModel {
  const factory LessonModel({
    required int id,
    required String title,
    String? content,
    @JsonKey(name: 'video_url') String? videoUrl,
    @JsonKey(name: 'youtube_url') String? youtubeUrl,
    @JsonKey(name: 'video_duration') int? duration,
    @JsonKey(name: 'is_preview') @Default(false) bool isPreview,
    required int order,
    @JsonKey(name: 'course_id') required int courseId,
  }) = _LessonModel;

  const LessonModel._();

  factory LessonModel.fromJson(Map<String, dynamic> json) =>
      _$LessonModelFromJson(json);

  Lesson toEntity() {
    return Lesson(
      id: id.toString(),
      title: title,
      content: content,
      videoUrl: videoUrl,
      youtubeUrl: youtubeUrl,
      duration: duration,
      isPreview: isPreview,
      order: order,
      courseId: courseId.toString(),
    );
  }
}

@freezed
class QuizModel with _$QuizModel {
  const factory QuizModel({
    required int id,
    required String title,
    @JsonKey(name: 'questions_count') required int questionsCount,
    @JsonKey(name: 'time_limit') int? timeLimit,
  }) = _QuizModel;

  const QuizModel._();

  factory QuizModel.fromJson(Map<String, dynamic> json) =>
      _$QuizModelFromJson(json);

  Quiz toEntity() {
    return Quiz(
      id: id.toString(),
      title: title,
      questionsCount: questionsCount,
      timeLimit: timeLimit,
    );
  }
}

@freezed
class AssignmentModel with _$AssignmentModel {
  const factory AssignmentModel({
    required int id,
    required String title,
    String? description,
    @JsonKey(name: 'total_points') required int totalPoints,
  }) = _AssignmentModel;

  const AssignmentModel._();

  factory AssignmentModel.fromJson(Map<String, dynamic> json) =>
      _$AssignmentModelFromJson(json);

  Assignment toEntity() {
    return Assignment(
      id: id.toString(),
      title: title,
      description: description,
      totalPoints: totalPoints,
    );
  }
}
