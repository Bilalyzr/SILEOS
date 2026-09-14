import 'package:freezed_annotation/freezed_annotation.dart';
import '../../domain/entities/assignment.dart';

part 'assignment_model.freezed.dart';
part 'assignment_model.g.dart';

@freezed
class AssignmentModel with _$AssignmentModel {
  const factory AssignmentModel({
    required int id,
    required String title,
    String? description,
    @JsonKey(name: 'total_points') required int totalPoints,
    @JsonKey(name: 'created_at') required String createdAt,
    @JsonKey(name: 'file_url') String? fileUrl,
    @JsonKey(name: 'is_submitted') @Default(false) bool isSubmitted,
    AssignmentSubmissionModel? submission,
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
      createdAt: DateTime.parse(createdAt),
      fileUrl: fileUrl,
      isSubmitted: isSubmitted,
      submission: submission?.toEntity(),
    );
  }
}

@freezed
class AssignmentSubmissionModel with _$AssignmentSubmissionModel {
  const factory AssignmentSubmissionModel({
    required int id,
    @JsonKey(name: 'assignment_id') required int assignmentId,
    @JsonKey(name: 'user_id') required int userId,
    required String content,
    @JsonKey(name: 'file_url') String? fileUrl,
    double? grade,
    String? feedback,
    @JsonKey(name: 'submitted_at') required String submittedAt,
  }) = _AssignmentSubmissionModel;

  const AssignmentSubmissionModel._();

  factory AssignmentSubmissionModel.fromJson(Map<String, dynamic> json) =>
      _$AssignmentSubmissionModelFromJson(json);

  AssignmentSubmission toEntity() {
    return AssignmentSubmission(
      id: id.toString(),
      assignmentId: assignmentId.toString(),
      userId: userId.toString(),
      content: content,
      fileUrl: fileUrl,
      grade: grade,
      feedback: feedback,
      submittedAt: DateTime.parse(submittedAt),
    );
  }
}
