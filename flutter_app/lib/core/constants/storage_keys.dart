/// Storage key constants for local data persistence.
class StorageKeys {
  // Auth tokens
  static const String accessToken = 'access_token';
  static const String refreshToken = 'refresh_token';
  static const String tokenExpiry = 'token_expiry';

  // User data
  static const String userId = 'user_id';
  static const String userData = 'user_data';
  static const String userRole = 'user_role';
  static const String isLoggedIn = 'is_logged_in';

  // FCM/Push notifications
  static const String fcmToken = 'fcm_token';
  static const String fcmTokenSent = 'fcm_token_sent';

  // App preferences
  static const String language = 'language';
  static const String theme = 'theme';
  static const String onboardingCompleted = 'onboarding_completed';
  static const String selectedLanguageCode = 'selected_language_code';

  // Course progress cache
  static const String courseProgressCache = 'course_progress_cache';
  static const String lessonProgressCache = 'lesson_progress_cache';

  // Quiz state
  static const String quizDraftAnswers = 'quiz_draft_answers';

  // Downloaded content (for offline mode)
  static const String downloadedLessons = 'downloaded_lessons';

  // Shopping cart
  static const String cart = 'cart';

  // Wishlist
  static const String wishlist = 'wishlist';

  // Company portal
  static const String selectedCompanyId = 'selected_company_id';
  static const String internshipDraft = 'internship_draft';

  // Analytics tracking
  static const String analyticsUserId = 'analytics_user_id';
  static const String lastSessionStart = 'last_session_start';

  // Cache timestamps
  static const String coursesCacheTimestamp = 'courses_cache_timestamp';
  static const String profileCacheTimestamp = 'profile_cache_timestamp';
}
