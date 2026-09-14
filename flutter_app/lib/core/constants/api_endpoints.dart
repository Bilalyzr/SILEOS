/// API endpoint constants for the Sasha LMS backend.
class ApiEndpoints {
  // Base URLs
  //
  // M-04 (live-classes audit, 2026-09): the dev flavor previously fell back
  // to baseUrlProd whenever API_BASE_URL/API_URL were not passed, so a plain
  // `flutter run` (no --dart-define) silently hit production. The Android
  // emulator's host-loopback alias (10.0.2.2) is now the default instead —
  // it only resolves inside the emulator, so it fails loudly/obviously on a
  // real device rather than quietly talking to prod. Override for a
  // physical device or a non-default emulator host with:
  //   flutter run --dart-define=API_URL=http://10.0.0.5:8000      (whole base URL)
  //   flutter run --dart-define=API_BASE_URL=http://10.0.0.5:8000 (this getter only)
  static String get baseUrlDev {
    const fromEnv = String.fromEnvironment('API_BASE_URL');
    if (fromEnv.isNotEmpty) return fromEnv;
    return 'http://10.0.2.2:8000';
  }
  static const String baseUrlStaging = 'https://staging.sashainfinity.com';
  static const String baseUrlProd = 'https://sashainfinity.com';

  // Auth endpoints (prefix: /api/v1/auth)
  static const String login = '/api/v1/auth/login';
  static const String register = '/api/v1/auth/register';
  static const String registerInstructor = '/api/v1/auth/register-instructor';
  static const String logout = '/api/v1/auth/logout';
  static const String refreshToken = '/api/v1/auth/refresh';
  static const String me = '/api/v1/auth/me';
  static const String checkEmail = '/api/v1/auth/check-email';
  static const String verifyEmail = '/api/v1/auth/verify-email';
  static const String resendVerification = '/api/v1/auth/resend-verification';
  static const String forgotPassword = '/api/v1/auth/forgot-password';
  static const String resetPassword = '/api/v1/auth/reset-password';
  static const String changePassword = '/api/v1/auth/change-password';
  static const String googleAuth = '/api/v1/auth/google';
  static const String googleComplete = '/api/v1/auth/google/complete';
  static const String linkedinAuth = '/api/v1/auth/linkedin';

  // Courses endpoints (prefix: /api/v1/courses)
  static const String courses = '/api/v1/courses';
  static const String myCourses = '/api/v1/courses/my-courses';
  static const String courseDetail = '/api/v1/courses';
  static String completeLesson(int courseId, int lessonId) => 
      '/api/v1/courses/$courseId/lessons/$lessonId/complete';
  static const String courseLessons = '/api/v1/courses';
  static const String courseProgress = '/api/v1/courses';
  static const String courseReviews = '/api/v1/courses';
  static const String enroll = '/api/v1/courses';
  static const String purchase = '/api/v1/courses';

  // Quizzes endpoints (prefix: /api/v1)
  static const String quizzes = '/api/v1/quizzes';
  static String quizStart(int quizId) => '/api/v1/quizzes/$quizId/start';
  static String quizSubmitAttempt(int attemptId) => '/api/v1/quiz-attempts/$attemptId/submit';
  static String quizAttemptResults(int attemptId) => '/api/v1/quiz-attempts/$attemptId/results';
  static String quizAttemptsCount(int courseId, int quizId) => 
      '/api/v1/courses/$courseId/quizzes/$quizId/attempts-count';

  // Assignments endpoints (prefix: /api/v1)
  static const String assignments = '/api/v1/assignments';
  static const String assignmentSubmit = '/api/v1/assignments';

  // Lessons endpoints (prefix: /api/v1/lessons)
  static const String lessons = '/api/v1/lessons';
  static const String lessonContent = '/api/v1/lessons';

  // Attendance endpoints (prefix: /api/v1/attendance)
  static const String attendance = '/api/v1/attendance';

  // Progress endpoints (prefix: /api/v1/progress)
  static const String progress = '/api/v1/progress';

  // Payments endpoints (prefix: /api/v1/payments)
  static const String createOrder = '/api/v1/payments/create-order';
  static const String verifyPayment = '/api/v1/payments/verify';

  // Orders endpoints (prefix: /api/v1/orders)
  static const String orders = '/api/v1/orders';

  // Profile/User endpoints (prefix: /api/v1/users)
  static const String profile = '/api/v1/users';

  // Upload endpoints (prefix: /api/v1/upload)
  static const String uploadImage = '/api/v1/upload/image';
  static const String uploadAvatar = '/api/v1/uploads/image';
  static const String uploadVideo = '/api/v1/upload/video';
  static const String uploadDocument = '/api/v1/upload/document';
  static const String deleteFile = '/api/v1/upload/file';
  static const String fileInfo = '/api/v1/upload/info';

  // Certificates endpoints (prefix: /api/v1/certificates)
  static const String certificates = '/api/v1/certificates';
  static const String verifyCertificate = '/api/v1/certificates/verify';

  // Dashboard endpoints (prefix: /api/v1/dashboard)
  static const String dashboard = '/api/v1/dashboard';

  // Wishlist endpoints (prefix: /api/v1/wishlist)
  static const String wishlist = '/api/v1/wishlist';

  // Blog endpoints (prefix: /api/v1/blog)
  static const String blog = '/api/v1/blog';

  // Coupons endpoints (prefix: /api/v1/coupons)
  static const String coupons = '/api/v1/coupons';
  static const String validateCoupon = '/api/v1/coupons/validate';

  // Video endpoints
  static const String videoExtract = '/api/v1/extract';
  static const String videoStream = '/api/v1/stream';
  static const String videoEmbed = '/api/v1/embed';
  static const String youtubeEmbed = '/api/v1/youtube';
  static const String player = '/api/v1/video';
  static const String bunny = '/api/v1/bunny';
  // Bunny.net Stream: exchange a stored video GUID for a (possibly signed,
  // short-lived) HLS playback URL, or check its processing status.
  static String bunnyPlayback(String videoId) =>
      '/api/v1/bunny/video/$videoId/playback';
  // Public signed URL for preview content (course intro / preview lessons) —
  // no enrollment required.
  static String bunnyPreviewPlayback(String videoId) =>
      '/api/v1/bunny/video/$videoId/preview-playback';
  static String bunnyStatus(String videoId) =>
      '/api/v1/bunny/video/$videoId/status';

  // Company Portal endpoints
  static const String companies = '/api/v1/companies';
  static const String companyDashboard = '/api/v1/companies';
  static const String internships = '/api/v1/internships';
  static const String internshipsAdmin = '/api/v1/admin/internships';
  static const String internshipsSpoc = '/api/v1/spoc';
  static const String internshipsPublic = '/api/v1/internships';
  static const String workLogs = '/api/v1/student/work-logs';
  static const String announcements = '/api/v1/student/announcements';
  static const String candidates = '/api/v1/candidates';
  static const String cohorts = '/api/v1/cohorts';

  // Analytics endpoints (prefix: /api/v1/analytics)
  static const String analytics = '/api/v1/analytics';

  // Admin endpoints (prefix: /api/v1/admin)
  static const String admin = '/api/v1/admin';
  static const String adminStats = '/api/v1/admin/stats';
  static const String adminUsers = '/api/v1/admin/users';
  static String adminUserDetail(int userId) => '/api/v1/admin/users/$userId';
  static String adminUserStatus(int userId) =>
      '/api/v1/admin/users/$userId/status';
  static const String adminCourses = '/api/v1/admin/courses';
  static String adminCourseStatus(int courseId) =>
      '/api/v1/admin/courses/$courseId/status';
  static const String adminInstructorApplications =
      '/api/v1/admin/instructor-applications';
  static String adminInstructorApplicationAction(int id) =>
      '/api/v1/admin/instructor-applications/$id';
  static const String adminOrders = '/api/v1/admin/orders';
  static const String adminEnrollments = '/api/v1/admin/enrollments';

  // Instructor reviews endpoints (prefix: /api/v1/instructor-reviews)
  static const String instructorReviews = '/api/v1/instructor-reviews';

  // Checkout endpoints (prefix: /api/v1/checkout)
  static const String checkout = '/api/v1/checkout';

  // Live Classes endpoints (prefix: /api/v1/live) — see
  // docs/superpowers/plans/2026-09-02-live-classes.md and the backend
  // routers under app/routers/live_class_*.py.
  static const String liveClasses = '/api/v1/live/classes';
  static String liveClassDetail(int id) => '/api/v1/live/classes/$id';
  static String liveClassJoinToken(int id) => '/api/v1/live/classes/$id/join-token';
  static String liveClassHeartbeat(int id) => '/api/v1/live/classes/$id/heartbeat';
  static String liveClassRecordingPlayback(int id) =>
      '/api/v1/live/classes/$id/recording-playback';
  static const String liveNow = '/api/v1/live/live-now';
}
