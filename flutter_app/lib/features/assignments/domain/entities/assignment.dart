import 'package:freezed_annotation/freezed_annotation.dart';

part 'assignment.freezed.dart';

@freezed
class Assignment with _$Assignment {
  const factory Assignment({
    required String id,
    required String title,
    String? description,
    required int totalPoints,
    required DateTime createdAt,
    String? fileUrl,
    @Default(false) bool isSubmitted,
    AssignmentSubmission? submission,
  }) = _Assignment;
}

@freezed
class AssignmentSubmission with _$AssignmentSubmission {
  const factory AssignmentSubmission({
    required String id,
    required String assignmentId,
    required String userId,
    required String content,
    String? fileUrl,
    double? grade,
    String? feedback,
    required DateTime submittedAt,
  }) = _AssignmentSubmission;
}
