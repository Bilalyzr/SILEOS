// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'assignment_model.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

_$AssignmentModelImpl _$$AssignmentModelImplFromJson(
        Map<String, dynamic> json) =>
    _$AssignmentModelImpl(
      id: (json['id'] as num).toInt(),
      title: json['title'] as String,
      description: json['description'] as String?,
      totalPoints: (json['total_points'] as num).toInt(),
      createdAt: json['created_at'] as String,
      fileUrl: json['file_url'] as String?,
      isSubmitted: json['is_submitted'] as bool? ?? false,
      submission: json['submission'] == null
          ? null
          : AssignmentSubmissionModel.fromJson(
              json['submission'] as Map<String, dynamic>),
    );

Map<String, dynamic> _$$AssignmentModelImplToJson(
        _$AssignmentModelImpl instance) =>
    <String, dynamic>{
      'id': instance.id,
      'title': instance.title,
      'description': instance.description,
      'total_points': instance.totalPoints,
      'created_at': instance.createdAt,
      'file_url': instance.fileUrl,
      'is_submitted': instance.isSubmitted,
      'submission': instance.submission,
    };

_$AssignmentSubmissionModelImpl _$$AssignmentSubmissionModelImplFromJson(
        Map<String, dynamic> json) =>
    _$AssignmentSubmissionModelImpl(
      id: (json['id'] as num).toInt(),
      assignmentId: (json['assignment_id'] as num).toInt(),
      userId: (json['user_id'] as num).toInt(),
      content: json['content'] as String,
      fileUrl: json['file_url'] as String?,
      grade: (json['grade'] as num?)?.toDouble(),
      feedback: json['feedback'] as String?,
      submittedAt: json['submitted_at'] as String,
    );

Map<String, dynamic> _$$AssignmentSubmissionModelImplToJson(
        _$AssignmentSubmissionModelImpl instance) =>
    <String, dynamic>{
      'id': instance.id,
      'assignment_id': instance.assignmentId,
      'user_id': instance.userId,
      'content': instance.content,
      'file_url': instance.fileUrl,
      'grade': instance.grade,
      'feedback': instance.feedback,
      'submitted_at': instance.submittedAt,
    };
