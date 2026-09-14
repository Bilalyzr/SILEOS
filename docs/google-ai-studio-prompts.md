# Google AI Studio Prompts for SashaInfinity LMS Flutter App

Use these prompts sequentially with `aistudio.google.com` to build the Flutter app. Copy each prompt, generate code, then paste into your project.

---

## Context Prompt (Use First)

```
You are building a Flutter mobile app for SashaInfinity LMS. Follow these specifications:

PROJECT STRUCTURE:
flutter_app/
├── lib/
│   ├── main.dart
│   ├── config/
│   ├── core/
│   │   ├── constants/
│   │   ├── errors/
│   │   ├── network/
│   │   ├── storage/
│   │   └── utils/
│   ├── features/
│   │   ├── auth/
│   │   ├── courses/
│   │   ├── lessons/
│   │   ├── quizzes/
│   │   ├── payments/
│   │   └── profile/
│   └── shared/

TECH STACK:
- Flutter 3.x
- Riverpod 2.x (state management with code generation)
- GoRouter 13.x (navigation)
- Dio 5.x (networking)
- Hive + FlutterSecureStorage (persistence)
- Chewie + youtube_player_flutter (video)
- Razorpay (payments)

API ENDPOINTS:
Base: https://api.sashalms.com
- POST /api/v1/auth/login
- POST /api/v1/auth/register
- POST /api/v1/auth/logout
- GET /api/v1/auth/me
- GET /api/v1/courses
- GET /api/v1/courses/{id}
- POST /api/v1/enrollments
- GET /api/v1/lessons/{id}
- POST /api/v1/progress
- GET /api/v1/quizzes
- POST /api/v1/quizzes/{id}/submit
- POST /api/v1/payments/create-order
- POST /api/v1/payments/verify

Generate complete, production-ready code with:
- Proper error handling
- Loading states
- Input validation
- Clean Architecture layers
- Freezed for immutable classes
- Riverpod code generation

No placeholders. No "TODO". Complete working code.
```

---

## Prompt 1: Project Initialization

```
Create the pubspec.yaml file for a Flutter 3.x project with these exact dependencies:

flutter_riverpod: ^2.4.0
riverpod_annotation: ^2.3.0
go_router: ^13.0.0
dio: ^5.4.0
retrofit: ^4.0.0
pretty_dio_logger: ^1.3.0
hive_flutter: ^1.1.0
flutter_secure_storage: ^9.0.0
shared_preferences: ^2.2.0
video_player: ^2.8.0
chewie: ^1.7.0
youtube_player_flutter: ^9.0.0
flutter_svg: ^2.0.0
cached_network_image: ^3.3.0
shimmer: ^3.0.0
flutter_slidable: ^3.0.0
pull_to_refresh: ^2.0.0
razorpay_flutter: ^1.3.0
freezed_annotation: ^2.4.0
json_annotation: ^4.8.0
intl: ^0.18.0
url_launcher: ^6.2.0
image_picker: ^1.0.0
permission_handler: ^11.0.0
connectivity_plus: ^5.0.0

dev_dependencies:
  build_runner: ^2.4.0
  freezed: ^2.4.0
  json_serializable: ^6.7.0
  riverpod_generator: ^2.3.0
  mockito: ^5.4.0

Include asset folders for images and icons.
```

---

## Prompt 2: Core Constants

```
Create these constant files in lib/core/constants/:

1. api_endpoints.dart - Define all API endpoint paths for:
   - Base URLs (dev, staging, prod)
   - Auth (login, register, logout, refresh, me)
   - Courses (list, detail, enroll, my courses)
   - Lessons (content, progress)
   - Quizzes (list, submit, results)
   - Payments (create order, verify)
   - Profile and uploads

2. storage_keys.dart - Define storage keys:
   - access_token, refresh_token
   - user_id, user_role
   - is_logged_in, fcm_token
   - language, theme

3. assets.dart - Define asset paths for images

Use static const String. Organize logically.
```

---

## Prompt 3: Error Handling

```
Create error handling in lib/core/errors/:

1. exceptions.dart with these classes extending AppException:
   - ServerException (with statusCode)
   - NetworkException
   - CacheException
   - UnauthorizedException (401)
   - ForbiddenException (403)
   - NotFoundException (404)
   - ValidationException (with fieldErrors map)

   Include AppExceptionFromDio utility to convert DioException to AppException

2. failures.dart using freezed:
   - Failure union type with variants:
     - server (message, statusCode)
     - network (message)
     - cache (message)
     - unauthorized (message?)
     - forbidden (message?)
     - notFound (message?)
     - validation (message, fieldErrors?)
     - unknown (message?)

Generate freezed code. Include part directives.
```

---

## Prompt 4: API Client

```
Create lib/core/network/api_client.dart:

ApiClient class wrapping Dio with:
- Constructor accepting baseUrl
- BaseOptions with 30s timeouts
- Methods: get, post, put, patch, delete, uploadFile
- Each method catches DioException and converts to AppException
- Built-in LogInterceptor

Include interceptors.dart with:
- AuthInterceptor - Adds Bearer token from secure storage
- RefreshTokenInterceptor - Handles 401, refreshes token, retries request
- LanguageInterceptor - Adds Accept-Language header

Use FlutterSecureStorage for token persistence.
```

---

## Prompt 5: Storage Layer

```
Create storage wrappers in lib/core/storage/:

1. secure_storage.dart:
   - Wrapper around FlutterSecureStorage
   - Methods: write, read, delete, deleteAll, containsKey
   - Convenience methods: saveAccessToken, getAccessToken, saveRefreshToken, etc.
   - Use encryptedSharedPreferences on Android

2. cache_storage.dart (Hive):
   - Init method to open box named 'cache_box'
   - Methods: write, read, delete, clear, containsKey
   - writeWithExpiry(key, value, Duration expiry)
   - readIfNotExpired<T>(key) - returns null if expired

3. prefs_storage.dart (SharedPreferences):
   - Methods for String, Bool, Int types
   - Convenience methods: setLanguage, getLanguage, setTheme, getTheme, setLoggedIn, isLoggedIn
```

---

## Prompt 6: App Configuration

```
Create lib/config/app_config.dart:

AppConfig class with:
- Environment enum (dev, staging, prod)
- Static getter for environment from String.fromEnvironment
- baseUrl getter returning correct URL per environment
- enableLogs (false for prod)
- enableCrashlytics (false for dev)
- apiBaseUrl getter
- createApiClient() factory method
```

---

## Prompt 7: Common UI Widgets

```
Create these widgets in lib/shared/widgets/common/:

1. app_button.dart:
   - AppButton widget with variants: primary, secondary, outline, text, danger
   - Sizes: small, medium, large
   - Props: text, onPressed, isLoading, isFullWidth, icon, trailing
   - Use ElevatedButton, TextButton
   - Show spinner when isLoading

2. app_input.dart:
   - AppInput widget wrapping TextFormField
   - Props: label, hint, errorText, controller, onChanged, onTap, readOnly, maxLines
   - keyboardType, inputFormatters, prefixIcon, suffixIcon
   - Auto-show/hide password toggle
   - Border styling with theme colors

3. app_loader.dart:
   - AppLoader with sizes: small, medium, large
   - FullScreenLoader for overlay loading

4. error_display.dart:
   - ErrorDisplay - shows icon, message, retry button
   - EmptyState - shows empty icon, message, action button
```

---

## Prompt 8: Auth Domain Layer

```
Create lib/features/auth/domain/:

1. entities/user.dart using freezed:
   - User entity with: id, email, firstName, lastName, role, avatarUrl, phone, isActive, createdAt
   - Getters: fullName, isInstructor, isAdmin, isStudent, isCompanyManager

2. repositories/auth_repository.dart:
   - Abstract AuthRepository with Either<Failure, T> return types:
     - login({email, password}) -> Either<Failure, User>
     - register({email, password, firstName, lastName, phone}) -> Either<Failure, User>
     - logout() -> Either<Failure, void>
     - getCurrentUser() -> Either<Failure, User>
     - refreshToken() -> Either<Failure, void>
     - isLoggedIn() -> Either<Failure, bool>

3. usecases/:
   - LoginUseCase, RegisterUseCase, LogoutUseCase
   - Each takes repository in constructor, has call method

Use dartz package for Either type.
```

---

## Prompt 9: Auth Data Layer

```
Create lib/features/auth/data/:

1. models/user_model.dart:
   - UserModel with freezed (matches API response)
   - Field names: id, email, first_name, last_name, role, avatar_url, phone, is_active, created_at
   - toEntity() converts to User domain entity
   - Use @JsonKey for snake_case mapping
   - Generate both .freezed.dart and .g.dart

2. datasources/auth_remote_datasource.dart:
   - Abstract AuthRemoteDataSource with same methods as repository but returns UserModel or throws
   - AuthRemoteDataSourceImpl using ApiClient:
     - login() POSTs to /api/v1/auth/login, returns UserModel
     - register() POSTs to /api/v1/auth/register
     - logout() POSTs to /api/v1/auth/logout
     - getCurrentUser() GETs /api/v1/auth/me

3. repositories/auth_repository_impl.dart:
   - Implements AuthRepository
   - Converts Exceptions to Failures using Either
   - Stores tokens via SecureStorage on successful login
   - Clears auth data on logout
```

---

## Prompt 10: Auth Provider (State Management)

```
Create lib/features/auth/presentation/providers/:

1. auth_state.dart using freezed:
   - AuthState: initial(), loading(), authenticated(User), unauthenticated(), error(String)

2. auth_provider.dart using riverpod_annotation:
   - Providers for: AuthRemoteDataSource, AuthRepository, LoginUseCase, RegisterUseCase, LogoutUseCase
   - AuthNotifier class with:
     - build() - initializes SecureStorage
     - checkAuthStatus() - checks token, gets current user
     - login({email, password}) - calls use case, handles result
     - register(...) - calls use case
     - logout() - clears auth data
     - clearError() - resets to initial

   Use @riverpod annotations. Generate .g.dart

Handle all Failure types and convert to error messages.
```

---

## Prompt 11: Login Page & Form

```
Create lib/features/auth/presentation/pages/login_page.dart:

LoginPage with:
- ConsumerStatefulWidget
- Watches authProvider
- Shows logo, title, "Sign in to continue learning"
- Contains LoginForm widget
- "Don't have an account? Register" link
- Navigates to home on successful authentication

Create widgets/login_form.dart:
- Form with email and password fields
- Email validation (required, valid format)
- Password validation (required, min 6 chars)
- Password visibility toggle
- "Forgot password?" link
- Sign In button with loading state
- Shows error snackbar on failure
- Auto-submits on password field done

Use AppInput and AppButton widgets.
```

---

## Prompt 12: Register Page & Form

```
Create lib/features/auth/presentation/pages/register_page.dart:

RegisterPage with:
- AppBar with "Create Account"
- "Join SashaInfinity LMS" heading
- "Start your learning journey today" subtitle
- Contains RegisterForm
- "Already have an account? Sign In" link

Create widgets/register_form.dart:
- Fields: first name, last name, email, phone (optional), password, confirm password
- Split first/last name in one row
- Email validation
- Phone optional
- Password min 6 chars
- Confirm password must match
- Both password fields have visibility toggle
- "Create Account" button with loading
- Error snackbar on failure

Use AppInput and AppButton.
```

---

## Prompt 13: Splash Screen & Routing

```
Create lib/features/auth/presentation/pages/splash_page.dart:

SplashPage with:
- Centered logo and app name
- Loading indicator
- Calls checkAuthStatus() on init
- Navigates to / if authenticated, /login if not
- Gradient background using primary color

Create lib/config/routes.dart:
- GoRouter configuration with redirect logic
- Routes: /splash, /login, /register, /, /courses/:id, /lessons/:id, /profile
- Protected routes check auth state
- Redirect unauthenticated to /login
- Redirect authenticated away from /login, /register
- Error page for 404

Create lib/main.dart:
- main() initializes CacheStorage
- ProviderScope wrapping MaterialApp.router
- routerConfig from routerProvider
- Theme with Material 3
- Dark theme support

Add provider: final routerProvider = Provider<GoRouter>((ref) { ... })
```

---

## Prompt 14: Courses Domain Layer

```
Create lib/features/courses/domain/:

1. entities/course.dart:
   - Course entity: id, title, description, thumbnailUrl, price, instructorName, durationMinutes, rating, enrollmentCount, categories (list)
   - isFree getter

2. entities/lesson.dart:
   - Lesson entity: id, courseId, title, description, videoUrl, videoType (youtube, bunny, direct), duration, order, isPreview, isCompleted

3. repositories/course_repository.dart:
   - Abstract CourseRepository:
     - getCourses({filters, page, limit}) -> Either<Failure, List<Course>>
     - getCourseById(id) -> Either<Failure, Course>
     - getCourseLessons(courseId) -> Either<Failure, List<Lesson>>
     - enrollCourse(courseId) -> Either<Failure, void>
     - getMyCourses() -> Either<Failure, List<Course>>
```

---

## Prompt 15: Courses Data Layer

```
Create lib/features/courses/data/:

1. models/course_model.dart:
   - CourseModel with snake_case fields: id, title, description, thumbnail_url, price, instructor_name, duration_minutes, rating, enrollment_count, categories
   - toEntity() conversion

2. models/lesson_model.dart:
   - LessonModel with: id, course_id, title, description, video_url, video_type, duration, order, is_preview, is_completed
   - toEntity() conversion

3. repositories/course_repository_impl.dart:
   - CourseRepositoryImpl using remote datasource
   - getCourses() calls /api/v1/courses
   - getCourseById() calls /api/v1/courses/{id}
   - getCourseLessons() calls /api/v1/courses/{id}/lessons
   - enrollCourse() POSTs to /api/v1/enrollments
   - getMyCourses() calls /api/v1/enrollments/my-courses

Handle pagination with page and limit query params.
```

---

## Prompt 16: Course List Page

```
Create lib/features/courses/presentation/pages/courses_page.dart:

CoursesPage with:
- AppBar "Browse Courses"
- Search bar at top
- Category filter chips (horizontal scroll)
- Course list using ListView.builder or GridView
- Pull to refresh
- Load more on scroll (pagination)
- Empty state when no courses
- Error display with retry

Create widgets/course_card.dart:
- Card with thumbnail (cached_network_image)
- Course title, instructor name
- Rating with star icon
- Duration and enrollment count
- Price (or "Free" badge)
- Ripple effect, tappable

Use shimmer placeholder while loading.
```

---

## Prompt 17: Course Detail Page

```
Create lib/features/cresentation/pages/course_detail_page.dart:

CourseDetailPage with:
- Course header with thumbnail, title, instructor
- Stats row: rating, duration, students
- Tabs: Overview, Curriculum, Reviews
- Overview tab: description, categories, what you'll learn
- Curriculum tab: list of lessons (expandable)
- Reviews tab: student reviews
- Floating "Enroll Now" button (or "Continue" if enrolled)
- Share button in AppBar

Show lesson list with:
- Lesson number, title, duration
- Lock icon if not enrolled (except preview lessons)
- Checkmark if completed
- Tap to open lesson (if enrolled)

Use TabController for tabs.
```

---

## Prompt 18: Video Player Widget

```
Create lib/shared/widgets/video/video_player_widget.dart:

VideoPlayerWidget with:
- Props: videoUrl, videoType (auto-detect), autoPlay, onEnded
- Support for:
  - YouTube videos (youtube_player_flutter)
  - Bunny CDN videos (video_player + chewie)
  - Direct MP4 (video_player + chewie)
- Auto-detect type from URL
- Chewie controls with:
  - Play/pause
  - Seek bar
  - Volume
  - Fullscreen
  - Playback speed
- Landscape fullscreen
- Save progress to API on pause/complete

YouTube detection: youtube.com, youtu.be URLs
Bunny detection: bunny.net URLs

Handle orientation changes for fullscreen.
```

---

## Prompt 19: Lesson Page

```
Create lib/features/lessons/presentation/pages/lesson_page.dart:

LessonPage with:
- Full-screen video player at top
- Below video: lesson title, description
- "Mark as Complete" button (if not completed)
- Previous/Next lesson navigation
- Auto-play next lesson when current completes
- Progress indicator
- Back button returns to course detail

State management:
- Track current position
- Save progress every 10 seconds
- Mark complete when 90% watched
- Fetch lesson data from API

Auto-rotate to landscape when entering fullscreen video.
```

---

## Prompt 20: Quizzes Domain Layer

```
Create lib/features/quizzes/domain/:

1. entities/quiz.dart:
   - Quiz entity: id, courseId, title, description, timeLimit, passingScore, attemptsRemaining, questions (list)

2. entities/question.dart:
   - Question entity: id, type (multiple_choice, true_false, fill_blank), text, options (list), correctAnswer, explanation

3. entities/quiz_attempt.dart:
   - QuizAttempt entity: id, quizId, userId, score, totalScore, passed, completedAt, answers (map)

4. repositories/quiz_repository.dart:
   - Abstract QuizRepository:
     - getQuiz(quizId) -> Either<Failure, Quiz>
     - getQuizzesByCourse(courseId) -> Either<Failure, List<Quiz>>
     - submitQuiz(quizId, answers) -> Either<Failure, QuizAttempt>
     - getQuizResults(quizId) -> Either<Failure, List<QuizAttempt>>
```

---

## Prompt 21: Quiz Taking Page

```
Create lib/features/quizzes/presentation/pages/quiz_taking_page.dart:

QuizTakingPage with:
- Timer display at top (if timeLimit set)
- Progress: "Question X of Y"
- Question card with:
  - Question text
  - Options (radio buttons for single choice)
  - True/False buttons for boolean type
  - Text input for fill-in-blank
- Navigation: Previous, Next buttons
- Submit button on last question
- Confirmation dialog before submit
- Cannot change answers after submit

State:
- Track answers map: {questionId: answer}
- Current question index
- Time remaining
- Auto-submit when time expires

Use PageView for swipe between questions.
```

---

## Prompt 22: Quiz Result Page

```
Create lib/features/quizzes/presentation/pages/quiz_result_page.dart:

QuizResultPage with:
- Circular progress showing score percentage
- "Passed!" or "Not Passed" message
- Score display: "X / Y points"
- Time taken
- List of questions with:
  - User answer
  - Correct answer
  - ✓ or ✗ indicator
  - Explanation (if available)
- "Retake Quiz" button (if attempts remain)
- "Back to Course" button
- Share result option

Colors:
- Green for correct
- Red for incorrect
- Amber for partially correct
```

---

## Prompt 23: Payments with Razorpay

```
Create lib/features/payments/presentation/pages/payment_page.dart:

PaymentPage with:
- Course summary (thumbnail, title)
- Price display with currency
- Razorpay checkout options:
  - UPI
  - Cards
  - Net Banking
  - Wallets
- "Pay Now" button
- Order creation flow:
  1. Call /api/v1/payments/create-order
  2. Get Razorpay order_id
  3. Open Razorpay checkout
  4. On success: call /api/v1/payments/verify
  5. Show success/error

Razorpay options:
- key: from config
- currency: INR
- name: "SashaInfinity LMS"
- description: course title
- order_id: from backend
- prefill: user email, name, contact

Handle payment success, failure, cancellation.
```

---

## Prompt 24: Profile Page

```
Create lib/features/profile/presentation/pages/profile_page.dart:

ProfilePage with:
- User avatar with edit button
- Name, email display
- Stats cards: courses enrolled, completed, certificates
- Menu items:
  - My Courses
  - Certificates
  - Payment History
  - Settings
  - Help & Support
  - Logout

Avatar upload:
- Use image_picker
- Upload to /api/v1/uploads/image with context=avatar
- Update local state

Settings:
- Language toggle (English/Tamil)
- Theme toggle (Light/Dark/System)
- Notifications toggle

Logout:
- Show confirmation dialog
- Call logout use case
- Navigate to login
```

---

## Prompt 25: Company Portal - Internships

```
Create lib/features/company/presentation/pages/internships_page.dart:

InternshipsPage with:
- List of available internships
- Each card shows:
  - Company logo
  - Position title
  - Location (remote/on-site)
  - Stipend amount
  - Duration
  - "Apply" button
- Filter by status: Applied, In Progress, Completed
- Empty state for no applications

Application form modal:
- Cover letter input
- Resume upload
- Submit application

User role check:
- Only show for students
- Company managers see different view
```

---

## Prompt 26: Company Portal - Work Logs

```
Create lib/features/company/presentation/pages/work_logs_page.dart:

WorkLogsPage with:
- Calendar view showing work days
- Date selector
- Work log form:
  - Date (auto-selected)
  - Hours worked
  - Tasks completed (multi-line)
  - Challenges faced
  - Attachments (optional)
- Submit button
- List of submitted logs with:
  - Date, hours, status (pending, approved, rejected)
  - Manager comment if rejected

API endpoints:
- POST /api/v1/work-logs
- GET /api/v1/work-logs?start_date=&end_date=
- PUT /api/v1/work-logs/{id}

Show weekly hours summary.
```

---

## Prompt 27: Localization (English/Tamil)

```
Create lib/l10n/ files and setup:

1. app_en.arb (English):
```json
{
  "app_name": "SashaInfinity LMS",
  "login": "Sign In",
  "register": "Create Account",
  "email": "Email",
  "password": "Password",
  "courses": "Courses",
  "lessons": "Lessons",
  "quizzes": "Quizzes",
  "profile": "Profile",
  "logout": "Logout",
  "enroll_now": "Enroll Now",
  "start_learning": "Start Learning"
}
```

2. app_ta.arb (Tamil):
```json
{
  "app_name": "சாஷா இன்ஃபினிட்டி LMS",
  "login": "உள்நுழை",
  "register": "கணக்கு உருவாக்கு",
  ...
}
```

3. Setup in main.dart:
   - Add flutter_localizations
   - Create MaterialApp with localizationsDelegates
   - supportedLocales: en, ta
   - Use Locale from PrefsStorage
```

---

## Prompt 28: Firebase Integration

```
Add Firebase services to the app:

1. Create lib/core/services/analytics_service.dart:
   - Firebase Analytics wrapper
   - Methods: logLogin, logCourseEnroll, logQuizComplete, logPurchase
   - Track screen views

2. Create lib/core/services/crashlytics_service.dart:
   - Firebase Crashlytics wrapper
   - Set user identifier on login
   - Log errors with custom keys
   - Handle uncaught errors

3. Setup in main.dart:
   - Initialize Firebase
   - Set Crashlytics error handler
   - Enable in production only

4. Push notifications:
   - FCM token handling
   - Background message handler
   - Notification permission request
```

---

## Prompt 29: Testing - Unit Tests

```
Create unit tests for auth feature:

test/features/auth/presentation/providers/auth_provider_test.dart:

- Mock AuthRepository
- Test initial state
- Test login success emits authenticated state
- Test login failure emits error state
- Test logout emits unauthenticated state
- Test register with valid data
- Test register with invalid email shows error

Use mockito for mocks.
Use when().thenAnswer() for async setup.
Verify state changes with expectLater(stream, emits(...)).
```

---

## Prompt 30: Widget Tests

```
Create widget tests:

test/features/auth/presentation/pages/login_page_test.dart:

- Test login page renders
- Test email input accepts valid email
- Test email rejects invalid format
- Test password min 6 chars validation
- Test password visibility toggle
- Test submit button calls login on valid form
- Test loading state shows spinner
- Test error snackbar shows on failure

test/features/courses/presentation/widgets/course_card_test.dart:

- Test course card renders with data
- Test shows placeholder when no thumbnail
- Test displays price correctly
- Test displays "Free" when price is 0
- Test onTap callback

Use pumpWidget() and pumpAndSettle().
```

---

## Prompt 31: Build Configuration

```
Setup build variants:

1. Create flavors: dev, staging, prod
2. Add --dart-define ENV=dev|staging|prod
3. Update AppConfig to use ENV
4. Create app icons for each flavor
5. Configure app icons with flutter_launcher

Build commands:
- flutter build apk --release --dart-define=ENV=prod
- flutter build appbundle --release --dart-define=ENV=prod
- flutter build ios --release --dart-define=ENV=prod

Version in pubspec.yaml: version: 1.0.0+1
+1 is build number.
```

---

## Prompt 32: Final Polish

```
Add finishing touches:

1. Animations:
   - Page transitions with go_router
   - Hero animations for course cards
   - Staggered list animations
   - Shimmer loading placeholders

2. Connectivity:
   - Show banner when offline
   - Retry failed requests when connection restored
   - Cache API responses for offline viewing

3. Performance:
   - Lazy loading for lists
   - Image caching with cached_network_image
   - Release unused controllers

4. Security:
   - SSL pinning for API calls
   - Root/jailbreak detection
   - Screenshot prevention for quiz pages
   - Certificate pinning config
```

---

## Usage Instructions

1. **Create empty Flutter project:**
   ```bash
   flutter create sashalms
   cd sashalms
   ```

2. **Use prompts sequentially:**
   - Open `aistudio.google.com`
   - Copy Prompt 1 (Context) - this sets up the AI with project knowledge
   - Then copy each subsequent prompt one at a time
   - Generate code, paste into your project
   - Run `flutter pub get` after pubspec.yaml
   - Run `dart run build_runner build --delete-conflicting-outputs` after freezed/riverpod files

3. **Test incrementally:**
   - After each major feature, run `flutter run`
   - Verify functionality before moving on

4. **Debug issues:**
   - If a prompt doesn't work, rephrase with more specific requirements
   - Ask for "complete file content" not snippets
   - Specify "include imports" explicitly

Each prompt builds on the previous. Don't skip prompts.
