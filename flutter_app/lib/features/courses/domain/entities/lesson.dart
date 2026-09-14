import 'package:freezed_annotation/freezed_annotation.dart';

part 'lesson.freezed.dart';

@freezed
class Lesson with _$Lesson {
  const factory Lesson({
    required String id,
    required String title,
    String? content,
    String? videoUrl,
    String? youtubeUrl,
    int? duration,
    @Default(false) bool isPreview,
    required int order,
    required String courseId,
  }) = _Lesson;
}

@freezed
class Quiz with _$Quiz {
  const factory Quiz({
    required String id,
    required String title,
    required int questionsCount,
    int? timeLimit,
  }) = _Quiz;
}

@freezed
class Assignment with _$Assignment {
  const factory Assignment({
    required String id,
    required String title,
    String? description,
    required int totalPoints,
  }) = _Assignment;
}
