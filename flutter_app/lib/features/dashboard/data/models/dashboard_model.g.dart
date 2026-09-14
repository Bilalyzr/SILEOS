// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'dashboard_model.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

_$DashboardModelImpl _$$DashboardModelImplFromJson(Map<String, dynamic> json) =>
    _$DashboardModelImpl(
      stats:
          DashboardStatsModel.fromJson(json['stats'] as Map<String, dynamic>),
      enrolledCourses: (json['enrolled_courses'] as List<dynamic>)
          .map((e) => DashboardCourseModel.fromJson(e as Map<String, dynamic>))
          .toList(),
      recentActivity: (json['recent_activity'] as List<dynamic>)
          .map((e) => RecentActivityModel.fromJson(e as Map<String, dynamic>))
          .toList(),
      internships: (json['internships'] as List<dynamic>?)
              ?.map((e) =>
                  StudentInternshipModel.fromJson(e as Map<String, dynamic>))
              .toList() ??
          const [],
      weeklyGoal: json['weekly_goal'] == null
          ? null
          : WeeklyGoalModel.fromJson(
              json['weekly_goal'] as Map<String, dynamic>),
    );

Map<String, dynamic> _$$DashboardModelImplToJson(
        _$DashboardModelImpl instance) =>
    <String, dynamic>{
      'stats': instance.stats,
      'enrolled_courses': instance.enrolledCourses,
      'recent_activity': instance.recentActivity,
      'internships': instance.internships,
      'weekly_goal': instance.weeklyGoal,
    };

_$DashboardCourseModelImpl _$$DashboardCourseModelImplFromJson(
        Map<String, dynamic> json) =>
    _$DashboardCourseModelImpl(
      id: (json['id'] as num).toInt(),
      title: json['title'] as String,
      thumbnail: json['thumbnail'] as String,
      progress: (json['progress'] as num).toDouble(),
      totalLessons: (json['totalLessons'] as num).toInt(),
      completedLessons: (json['completedLessons'] as num).toInt(),
      instructor: json['instructor'] as String,
      rating: (json['rating'] as num).toDouble(),
      nextLesson: json['nextLesson'] as String,
      enrollmentStatus: json['enrollment_status'] as String,
    );

Map<String, dynamic> _$$DashboardCourseModelImplToJson(
        _$DashboardCourseModelImpl instance) =>
    <String, dynamic>{
      'id': instance.id,
      'title': instance.title,
      'thumbnail': instance.thumbnail,
      'progress': instance.progress,
      'totalLessons': instance.totalLessons,
      'completedLessons': instance.completedLessons,
      'instructor': instance.instructor,
      'rating': instance.rating,
      'nextLesson': instance.nextLesson,
      'enrollment_status': instance.enrollmentStatus,
    };

_$DashboardStatsModelImpl _$$DashboardStatsModelImplFromJson(
        Map<String, dynamic> json) =>
    _$DashboardStatsModelImpl(
      enrolledCourses: (json['enrolled_courses'] as num).toInt(),
      completedCourses: (json['completed_courses'] as num).toInt(),
      totalHours: (json['total_hours'] as num).toInt(),
      certificates: (json['certificates'] as num).toInt(),
    );

Map<String, dynamic> _$$DashboardStatsModelImplToJson(
        _$DashboardStatsModelImpl instance) =>
    <String, dynamic>{
      'enrolled_courses': instance.enrolledCourses,
      'completed_courses': instance.completedCourses,
      'total_hours': instance.totalHours,
      'certificates': instance.certificates,
    };

_$RecentActivityModelImpl _$$RecentActivityModelImplFromJson(
        Map<String, dynamic> json) =>
    _$RecentActivityModelImpl(
      type: json['type'] as String,
      action: json['action'] as String,
      title: json['title'] as String,
      course: json['course'] as String,
      description: json['description'] as String,
      timestamp: json['timestamp'] as String,
      time: json['time'] as String,
    );

Map<String, dynamic> _$$RecentActivityModelImplToJson(
        _$RecentActivityModelImpl instance) =>
    <String, dynamic>{
      'type': instance.type,
      'action': instance.action,
      'title': instance.title,
      'course': instance.course,
      'description': instance.description,
      'timestamp': instance.timestamp,
      'time': instance.time,
    };

_$StudentInternshipModelImpl _$$StudentInternshipModelImplFromJson(
        Map<String, dynamic> json) =>
    _$StudentInternshipModelImpl(
      id: (json['id'] as num).toInt(),
      title: json['title'] as String,
      voucherCode: json['voucher_code'] as String,
      status: json['status'] as String,
      redeemedCourseTitle: json['redeemed_course_title'] as String?,
      attendanceDays: (json['attendance_days'] as num).toInt(),
      hiredCompany: json['hired_company'] as String?,
      createdAt: json['created_at'] as String?,
    );

Map<String, dynamic> _$$StudentInternshipModelImplToJson(
        _$StudentInternshipModelImpl instance) =>
    <String, dynamic>{
      'id': instance.id,
      'title': instance.title,
      'voucher_code': instance.voucherCode,
      'status': instance.status,
      'redeemed_course_title': instance.redeemedCourseTitle,
      'attendance_days': instance.attendanceDays,
      'hired_company': instance.hiredCompany,
      'created_at': instance.createdAt,
    };

_$WeeklyGoalModelImpl _$$WeeklyGoalModelImplFromJson(
        Map<String, dynamic> json) =>
    _$WeeklyGoalModelImpl(
      goalHours: (json['goal_hours'] as num).toInt(),
      completedHours: (json['completed_hours'] as num).toDouble(),
      progressPercentage: (json['progress_percentage'] as num).toInt(),
      lessonsCompleted: (json['lessons_completed'] as num).toInt(),
    );

Map<String, dynamic> _$$WeeklyGoalModelImplToJson(
        _$WeeklyGoalModelImpl instance) =>
    <String, dynamic>{
      'goal_hours': instance.goalHours,
      'completed_hours': instance.completedHours,
      'progress_percentage': instance.progressPercentage,
      'lessons_completed': instance.lessonsCompleted,
    };
