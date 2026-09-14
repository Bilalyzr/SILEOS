// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'lesson_model.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

_$LessonModelImpl _$$LessonModelImplFromJson(Map<String, dynamic> json) =>
    _$LessonModelImpl(
      id: (json['id'] as num).toInt(),
      title: json['title'] as String,
      content: json['content'] as String?,
      videoUrl: json['video_url'] as String?,
      youtubeUrl: json['youtube_url'] as String?,
      duration: (json['video_duration'] as num?)?.toInt(),
      isPreview: json['is_preview'] as bool? ?? false,
      order: (json['order'] as num).toInt(),
      courseId: (json['course_id'] as num).toInt(),
    );

Map<String, dynamic> _$$LessonModelImplToJson(_$LessonModelImpl instance) =>
    <String, dynamic>{
      'id': instance.id,
      'title': instance.title,
      'content': instance.content,
      'video_url': instance.videoUrl,
      'youtube_url': instance.youtubeUrl,
      'video_duration': instance.duration,
      'is_preview': instance.isPreview,
      'order': instance.order,
      'course_id': instance.courseId,
    };

_$QuizModelImpl _$$QuizModelImplFromJson(Map<String, dynamic> json) =>
    _$QuizModelImpl(
      id: (json['id'] as num).toInt(),
      title: json['title'] as String,
      questionsCount: (json['questions_count'] as num).toInt(),
      timeLimit: (json['time_limit'] as num?)?.toInt(),
    );

Map<String, dynamic> _$$QuizModelImplToJson(_$QuizModelImpl instance) =>
    <String, dynamic>{
      'id': instance.id,
      'title': instance.title,
      'questions_count': instance.questionsCount,
      'time_limit': instance.timeLimit,
    };

_$AssignmentModelImpl _$$AssignmentModelImplFromJson(
        Map<String, dynamic> json) =>
    _$AssignmentModelImpl(
      id: (json['id'] as num).toInt(),
      title: json['title'] as String,
      description: json['description'] as String?,
      totalPoints: (json['total_points'] as num).toInt(),
    );

Map<String, dynamic> _$$AssignmentModelImplToJson(
        _$AssignmentModelImpl instance) =>
    <String, dynamic>{
      'id': instance.id,
      'title': instance.title,
      'description': instance.description,
      'total_points': instance.totalPoints,
    };
