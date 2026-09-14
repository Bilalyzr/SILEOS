import 'package:freezed_annotation/freezed_annotation.dart';
import '../../domain/entities/dashboard_data.dart';

part 'dashboard_model.freezed.dart';
part 'dashboard_model.g.dart';

@freezed
class DashboardModel with _$DashboardModel {
  const factory DashboardModel({
    required DashboardStatsModel stats,
    @JsonKey(name: 'enrolled_courses') required List<DashboardCourseModel> enrolledCourses,
    @JsonKey(name: 'recent_activity') required List<RecentActivityModel> recentActivity,
    @Default([]) List<StudentInternshipModel> internships,
    @JsonKey(name: 'weekly_goal') WeeklyGoalModel? weeklyGoal,
  }) = _DashboardModel;

  const DashboardModel._();

  factory DashboardModel.fromJson(Map<String, dynamic> json) =>
      _$DashboardModelFromJson(json);

  DashboardData toEntity() {
    return DashboardData(
      stats: stats.toEntity(),
      enrolledCourses: enrolledCourses.map((m) => m.toEntity()).toList(),
      recentActivity: recentActivity.map((m) => m.toEntity()).toList(),
      internships: internships.map((m) => m.toEntity()).toList(),
      weeklyGoal: weeklyGoal?.toEntity(),
    );
  }
}

@freezed
class DashboardCourseModel with _$DashboardCourseModel {
  const factory DashboardCourseModel({
    required int id,
    required String title,
    required String thumbnail,
    required double progress,
    @JsonKey(name: 'totalLessons') required int totalLessons,
    @JsonKey(name: 'completedLessons') required int completedLessons,
    required String instructor,
    required double rating,
    @JsonKey(name: 'nextLesson') required String nextLesson,
    @JsonKey(name: 'enrollment_status') required String enrollmentStatus,
  }) = _DashboardCourseModel;

  const DashboardCourseModel._();

  factory DashboardCourseModel.fromJson(Map<String, dynamic> json) =>
      _$DashboardCourseModelFromJson(json);

  DashboardCourse toEntity() {
    return DashboardCourse(
      id: id.toString(),
      title: title,
      thumbnail: thumbnail,
      progress: progress,
      totalLessons: totalLessons,
      completedLessons: completedLessons,
      instructorName: instructor,
      rating: rating,
      nextLesson: nextLesson,
      enrollmentStatus: enrollmentStatus,
    );
  }
}

@freezed
class DashboardStatsModel with _$DashboardStatsModel {
  const factory DashboardStatsModel({
    @JsonKey(name: 'enrolled_courses') required int enrolledCourses,
    @JsonKey(name: 'completed_courses') required int completedCourses,
    @JsonKey(name: 'total_hours') required int totalHours,
    required int certificates,
  }) = _DashboardStatsModel;

  const DashboardStatsModel._();

  factory DashboardStatsModel.fromJson(Map<String, dynamic> json) =>
      _$DashboardStatsModelFromJson(json);

  DashboardStats toEntity() {
    return DashboardStats(
      enrolledCourses: enrolledCourses,
      completedCourses: completedCourses,
      totalHours: totalHours,
      certificates: certificates,
    );
  }
}

@freezed
class RecentActivityModel with _$RecentActivityModel {
  const factory RecentActivityModel({
    required String type,
    required String action,
    required String title,
    required String course,
    required String description,
    required String timestamp,
    required String time,
  }) = _RecentActivityModel;

  const RecentActivityModel._();

  factory RecentActivityModel.fromJson(Map<String, dynamic> json) =>
      _$RecentActivityModelFromJson(json);

  RecentActivity toEntity() {
    return RecentActivity(
      type: type,
      action: action,
      title: title,
      course: course,
      description: description,
      timestamp: timestamp,
      time: time,
    );
  }
}

@freezed
class StudentInternshipModel with _$StudentInternshipModel {
  const factory StudentInternshipModel({
    required int id,
    required String title,
    @JsonKey(name: 'voucher_code') required String voucherCode,
    required String status,
    @JsonKey(name: 'redeemed_course_title') String? redeemedCourseTitle,
    @JsonKey(name: 'attendance_days') required int attendanceDays,
    @JsonKey(name: 'hired_company') String? hiredCompany,
    @JsonKey(name: 'created_at') String? createdAt,
  }) = _StudentInternshipModel;

  const StudentInternshipModel._();

  factory StudentInternshipModel.fromJson(Map<String, dynamic> json) =>
      _$StudentInternshipModelFromJson(json);

  StudentInternship toEntity() {
    return StudentInternship(
      id: id,
      title: title,
      voucherCode: voucherCode,
      status: status,
      redeemedCourseTitle: redeemedCourseTitle,
      attendanceDays: attendanceDays,
      hiredCompany: hiredCompany,
      createdAt: createdAt,
    );
  }
}

@freezed
class WeeklyGoalModel with _$WeeklyGoalModel {
  const factory WeeklyGoalModel({
    @JsonKey(name: 'goal_hours') required int goalHours,
    @JsonKey(name: 'completed_hours') required double completedHours,
    @JsonKey(name: 'progress_percentage') required int progressPercentage,
    @JsonKey(name: 'lessons_completed') required int lessonsCompleted,
  }) = _WeeklyGoalModel;

  const WeeklyGoalModel._();

  factory WeeklyGoalModel.fromJson(Map<String, dynamic> json) =>
      _$WeeklyGoalModelFromJson(json);

  WeeklyGoal toEntity() {
    return WeeklyGoal(
      goalHours: goalHours,
      completedHours: completedHours,
      progressPercentage: progressPercentage,
      lessonsCompleted: lessonsCompleted,
    );
  }
}
