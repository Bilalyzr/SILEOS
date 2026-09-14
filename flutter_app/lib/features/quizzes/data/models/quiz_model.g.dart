// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'quiz_model.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

_$QuizModelImpl _$$QuizModelImplFromJson(Map<String, dynamic> json) =>
    _$QuizModelImpl(
      id: (json['id'] as num).toInt(),
      title: json['title'] as String,
      description: json['description'] as String?,
      timeLimit: (json['timeLimit'] as num).toInt(),
      passingScore: (json['passingScore'] as num).toInt(),
      maxAttempts: (json['maxAttempts'] as num).toInt(),
      questions: (json['questions'] as List<dynamic>?)
              ?.map(
                  (e) => QuizQuestionModel.fromJson(e as Map<String, dynamic>))
              .toList() ??
          const [],
    );

Map<String, dynamic> _$$QuizModelImplToJson(_$QuizModelImpl instance) =>
    <String, dynamic>{
      'id': instance.id,
      'title': instance.title,
      'description': instance.description,
      'timeLimit': instance.timeLimit,
      'passingScore': instance.passingScore,
      'maxAttempts': instance.maxAttempts,
      'questions': instance.questions,
    };

_$QuizQuestionModelImpl _$$QuizQuestionModelImplFromJson(
        Map<String, dynamic> json) =>
    _$QuizQuestionModelImpl(
      id: json['id'] as String,
      type: json['type'] as String,
      question: json['question'] as String,
      points: (json['points'] as num).toDouble(),
      explanation: json['explanation'] as String?,
      imageUrl: json['imageUrl'] as String?,
      options: (json['options'] as List<dynamic>?)
              ?.map((e) => e as String)
              .toList() ??
          const [],
      correctAnswer: json['correctAnswer'],
    );

Map<String, dynamic> _$$QuizQuestionModelImplToJson(
        _$QuizQuestionModelImpl instance) =>
    <String, dynamic>{
      'id': instance.id,
      'type': instance.type,
      'question': instance.question,
      'points': instance.points,
      'explanation': instance.explanation,
      'imageUrl': instance.imageUrl,
      'options': instance.options,
      'correctAnswer': instance.correctAnswer,
    };

_$QuizAttemptModelImpl _$$QuizAttemptModelImplFromJson(
        Map<String, dynamic> json) =>
    _$QuizAttemptModelImpl(
      attemptId: (json['attempt_id'] as num?)?.toInt(),
      quizId: (json['quiz_id'] as num?)?.toInt(),
      totalMarks: (json['total_marks'] as num?)?.toDouble(),
      earnedMarks: (json['earned_marks'] as num?)?.toDouble(),
      percentage: (json['percentage'] as num?)?.toDouble(),
      passed: json['passed'] as bool?,
      passingGrade: (json['passing_grade'] as num?)?.toInt(),
    );

Map<String, dynamic> _$$QuizAttemptModelImplToJson(
        _$QuizAttemptModelImpl instance) =>
    <String, dynamic>{
      'attempt_id': instance.attemptId,
      'quiz_id': instance.quizId,
      'total_marks': instance.totalMarks,
      'earned_marks': instance.earnedMarks,
      'percentage': instance.percentage,
      'passed': instance.passed,
      'passing_grade': instance.passingGrade,
    };
