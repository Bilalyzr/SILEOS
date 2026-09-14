import 'package:freezed_annotation/freezed_annotation.dart';

part 'dashboard_data.freezed.dart';

@freezed
class DashboardData with _$DashboardData {
  const factory DashboardData({
    required DashboardStats stats,
    required List<DashboardCourse> enrolledCourses,
    required List<RecentActivity> recentActivity,
    @Default([]) List<StudentInternship> internships,
    WeeklyGoal? weeklyGoal,
  }) = _DashboardData;
}

@freezed
class DashboardCourse with _$DashboardCourse {
  const factory DashboardCourse({
    required String id,
    required String title,
    required String thumbnail,
    required double progress,
    required int totalLessons,
    required int completedLessons,
    required String instructorName,
    required double rating,
    required String nextLesson,
    required String enrollmentStatus,
  }) = _DashboardCourse;
}

@freezed
class DashboardStats with _$DashboardStats {
  const factory DashboardStats({
    required int enrolledCourses,
    required int completedCourses,
    required int totalHours,
    required int certificates,
  }) = _DashboardStats;
}

@freezed
class RecentActivity with _$RecentActivity {
  const factory RecentActivity({
    required String type,
    required String action,
    required String title,
    required String course,
    required String description,
    required String timestamp,
    required String time,
  }) = _RecentActivity;
}

@freezed
class StudentInternship with _$StudentInternship {
  const factory StudentInternship({
    required int id,
    required String title,
    required String voucherCode,
    required String status,
    String? redeemedCourseTitle,
    required int attendanceDays,
    String? hiredCompany,
    String? createdAt,
  }) = _StudentInternship;
}

@freezed
class WeeklyGoal with _$WeeklyGoal {
  const factory WeeklyGoal({
    required int goalHours,
    required double completedHours,
    required int progressPercentage,
    required int lessonsCompleted,
  }) = _WeeklyGoal;
}
