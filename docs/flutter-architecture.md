# SashaInfinity LMS - Flutter Mobile App Architecture

Comprehensive architecture guide for rebuilding the React frontend as a Flutter mobile application.

---

## 1. Technology Stack

```yaml
# pubspec.yaml
dependencies:
  flutter:
    sdk: flutter

  # State Management
  flutter_riverpod: ^2.4.0
  riverpod_annotation: ^2.3.0

  # Navigation
  go_router: ^13.0.0

  # Networking
  dio: ^5.4.0
  retrofit: ^4.0.0
  pretty_dio_logger: ^1.3.0

  # Local Storage
  hive_flutter: ^1.1.0
  flutter_secure_storage: ^9.0.0
  shared_preferences: ^2.2.0

  # Video Player
  video_player: ^2.8.0
  chewie: ^1.7.0
  youtube_player_flutter: ^9.0.0

  # UI Components
  flutter_svg: ^2.0.0
  cached_network_image: ^3.3.0
  shimmer: ^3.0.0
  flutter_slidable: ^3.0.0
  pull_to_refresh: ^2.0.0

  # Payments
  razorpay_flutter: ^1.3.0

  # Firebase
  firebase_core: ^2.24.0
  firebase_crashlytics: ^3.4.0
  firebase_analytics: ^10.7.0
  firebase_messaging: ^14.7.0

  # Utilities
  freezed_annotation: ^2.4.0
  json_annotation: ^4.8.0
  intl: ^0.18.0
  url_launcher: ^6.2.0
  image_picker: ^1.0.0
  permission_handler: ^11.0.0

dev_dependencies:
  flutter_test:
    sdk: flutter
  build_runner: ^2.4.0
  freezed: ^2.4.0
  json_serializable: ^6.7.0
  riverpod_generator: ^2.3.0
  mockito: ^5.4.0
  integration_test:
    sdk: flutter
```

---

## 2. Project Structure

```
lib/
├── main.dart                      # App entry point
├── config/
│   ├── app_config.dart           # Environment-based config
│   └── routes.dart               # GoRouter configuration
├── core/
│   ├── constants/
│   │   ├── api_endpoints.dart
│   │   ├── assets.dart
│   │   └── storage_keys.dart
│   ├── errors/
│   │   ├── exceptions.dart
│   │   └── failures.dart
│   ├── network/
│   │   ├── api_client.dart       # Dio wrapper
│   │   ├── interceptors.dart     # Auth, logging, refresh
│   │   └── api_response.dart
│   ├── storage/
│   │   ├── secure_storage.dart   # Tokens, sensitive data
│   │   ├── cache_storage.dart    # Hive for cached data
│   │   └── prefs_storage.dart    # Shared preferences
│   └── utils/
│       ├── date_formatter.dart
│       ├── validators.dart
│       └── logger.dart
├── features/
│   ├── auth/
│   │   ├── data/
│   │   │   ├── models/
│   │   │   ├── repositories/
│   │   │   └── datasources/
│   │   ├── domain/
│   │   │   ├── entities/
│   │   │   ├── repositories/
│   │   │   └── usecases/
│   │   └── presentation/
│   │       ├── providers/
│   │       ├── pages/
│   │       └── widgets/
│   ├── courses/
│   │   └── ... (same structure)
│   ├── lessons/
│   │   └── ...
│   ├── quizzes/
│   │   └── ...
│   ├── payments/
│   │   └── ...
│   ├── company/
│   │   └── ...
│   └── profile/
│       └── ...
├── shared/
│   ├── widgets/
│   │   ├── common/
│   │   │   ├── app_button.dart
│   │   │   ├── app_input.dart
│   │   │   ├── app_loader.dart
│   │   │   └── error_display.dart
│   │   ├── video/
│   │   │   └── video_player_widget.dart
│   │   └── course/
│   │       └── course_card.dart
│   └── providers/
│       └── internet_connectivity.dart
└── l10n/
    └── app_en.arb                 # English strings
    └── app_ta.arb                 # Tamil strings
```

---

## 3. State Management (Riverpod + Code Generation)

```dart
// lib/features/auth/presentation/providers/auth_provider.dart
import 'package:riverpod_annotation/riverpod_annotation.dart';

part 'auth_provider.g.dart';

@riverpod
class Auth extends _$Auth {
  @override
  AuthState build() {
    return const AuthState.initial();
  }

  Future<void> login(String email, String password) async {
    state = const AuthState.loading();
    final result = await ref.read(authRepositoryProvider).login(email, password);
    result.fold(
      (error) => state = AuthState.error(error.message),
      (user) => state = AuthState.authenticated(user),
    );
  }

  Future<void> logout() async {
    await ref.read(authRepositoryProvider).logout();
    state = const AuthState.unauthenticated();
  }

  Future<void> checkAuthStatus() async {
    final token = await ref.read(secureStorageProvider).read('access_token');
    if (token != null) {
      final user = await ref.read(authRepositoryProvider).getCurrentUser();
      user.fold(
        (error) => state = const AuthState.unauthenticated(),
        (userData) => state = AuthState.authenticated(userData),
      );
    }
  }
}

// Freezed state
// lib/features/auth/presentation/providers/auth_state.dart
import 'package:freezed_annotation/freezed_annotation.dart';

part 'auth_state.freezed.dart';

@freezed
class AuthState with _$AuthState {
  const factory AuthState.initial() = _Initial;
  const factory AuthState.loading() = _Loading;
  const factory AuthState.authenticated(User user) = _Authenticated;
  const factory AuthState.unauthenticated() = _Unauthenticated;
  const factory AuthState.error(String message) = _Error;
}
```

---

## 4. Navigation (GoRouter)

```dart
// lib/config/routes.dart
import 'package:go_router/go_router.dart';

final router = GoRouter(
  initialLocation: '/splash',
  redirect: (context, state) {
    final auth = ref.read(authProvider);
    final isAuth = state is _Authenticated;
    final isProtected = _protectedRoutes.contains(state.matchedLocation);

    if (!isAuth && isProtected) return '/login';
    if (isAuth && state.matchedLocation == '/login') return '/';
    return null;
  },
  routes: [
    GoRoute(
      path: '/splash',
      pageBuilder: (context, state) => MaterialPage(child: SplashScreen()),
    ),
    GoRoute(
      path: '/login',
      pageBuilder: (context, state) => MaterialPage(child: LoginPage()),
    ),
    GoRoute(
      path: '/register',
      pageBuilder: (context, state) => MaterialPage(child: RegisterPage()),
    ),
    GoRoute(
      path: '/',
      pageBuilder: (context, state) => MaterialPage(child: HomePage()),
      routes: [
        GoRoute(
          path: 'courses',
          pageBuilder: (context, state) => MaterialPage(child: CoursesPage()),
          routes: [
            GoRoute(
              path: ':id',
              pageBuilder: (context, state) {
                final courseId = state.pathParameters['id']!;
                return MaterialPage(child: CourseDetailPage(courseId: courseId));
              },
            ),
          ],
        ),
        GoRoute(
          path: 'lessons/:id',
          pageBuilder: (context, state) {
            final lessonId = state.pathParameters['id']!;
            return MaterialPage(child: LessonPage(lessonId: lessonId));
          },
        ),
        GoRoute(
          path: 'quiz/:id',
          pageBuilder: (context, state) {
            final quizId = state.pathParameters['id']!;
            return MaterialPage(child: QuizTakingPage(quizId: quizId));
          },
        ),
      ],
    ),
    GoRoute(
      path: '/profile',
      pageBuilder: (context, state) => MaterialPage(child: ProfilePage()),
    ),
    GoRoute(
      path: '/company',
      pageBuilder: (context, state) => MaterialPage(child: CompanyPortalPage()),
    ),
  ],
);

const _protectedRoutes = {
  '/',
  '/courses',
  '/lessons',
  '/quiz',
  '/profile',
  '/company',
};
```

---

## 5. Data Layer & API Integration

```dart
// lib/core/network/api_client.dart
import 'package:dio/dio.dart';

class ApiClient {
  late final Dio _dio;

  ApiClient({required String baseUrl}) {
    _dio = Dio(BaseOptions(
      baseUrl: baseUrl,
      connectTimeout: const Duration(seconds: 30),
      receiveTimeout: const Duration(seconds: 30),
      headers: {'Content-Type': 'application/json'},
    ));

    _dio.interceptors.addAll([
      AuthInterceptor(),
      LoggingInterceptor(),
      RefreshTokenInterceptor(),
      ErrorInterceptor(),
    ]);
  }

  Future<Response> get(String path, {Map<String, dynamic>? queryParameters}) {
    return _dio.get(path, queryParameters: queryParameters);
  }

  Future<Response> post(String path, {dynamic data}) {
    return _dio.post(path, data: data);
  }

  Future<Response> put(String path, {dynamic data}) {
    return _dio.put(path, data: data);
  }

  Future<Response> delete(String path) {
    return _dio.delete(path);
  }

  Future<Response> patch(String path, {dynamic data}) {
    return _dio.patch(path, data: data);
  }

  // Multipart for file uploads
  Future<Response> uploadFile(String path, FormData formData) {
    return _dio.post(path, data: formData);
  }
}

// lib/core/network/interceptors.dart
class AuthInterceptor extends Interceptor {
  @override
  void onRequest(RequestOptions options, RequestInterceptorHandler handler) async {
    final token = await secureStorage.read(key: 'access_token');
    if (token != null) {
      options.headers['Authorization'] = 'Bearer $token';
    }
    handler.next(options);
  }
}

class RefreshTokenInterceptor extends Interceptor {
  @override
  void onError(DioException err, ErrorInterceptorHandler handler) async {
    if (err.response?.statusCode == 401) {
      try {
        final refreshToken = await secureStorage.read(key: 'refresh_token');
        final response = await dio.post('/api/v1/auth/refresh', data: {
          'refresh_token': refreshToken,
        });

        final newAccessToken = response.data['access_token'];
        await secureStorage.write(key: 'access_token', value: newAccessToken);

        // Retry original request
        final opts = err.requestOptions;
        opts.headers['Authorization'] = 'Bearer $newAccessToken';
        final retryResponse = await dio.fetch(opts);
        handler.resolve(retryResponse);
        return;
      } catch (e) {
        // Refresh failed - logout user
        await secureStorage.deleteAll();
        router.push('/login');
      }
    }
    handler.next(err);
  }
}
```

---

## 6. Domain Layer (Clean Architecture)

```dart
// lib/features/courses/domain/entities/course.dart
class Course {
  final String id;
  final String title;
  final String description;
  final String? thumbnailUrl;
  final double price;
  final String instructorName;
  final int durationMinutes;
  final double rating;
  final int enrollmentCount;
  final List<String> categories;

  const Course({
    required this.id,
    required this.title,
    required this.description,
    this.thumbnailUrl,
    required this.price,
    required this.instructorName,
    required this.durationMinutes,
    required this.rating,
    required this.enrollmentCount,
    required this.categories,
  });
}

// lib/features/courses/domain/repositories/course_repository.dart
abstract class CourseRepository {
  Future<Either<Failure, List<Course>>> getCourses({Map<String, dynamic>? filters});
  Future<Either<Failure, Course>> getCourseById(String id);
  Future<Either<Failure, List<Lesson>>> getCourseLessons(String courseId);
  Future<Either<Failure, void>> enrollCourse(String courseId);
}

// lib/features/courses/domain/usecases/get_courses.dart
class GetCoursesUseCase {
  final CourseRepository repository;

  GetCoursesUseCase(this.repository);

  Future<Either<Failure, List<Course>>> call({Map<String, dynamic>? filters}) {
    return repository.getCourses(filters: filters);
  }
}
```

---

## 7. Video Player Integration

```dart
// lib/shared/widgets/video/video_player_widget.dart
class VideoPlayerWidget extends StatefulWidget {
  final String videoUrl;
  final String? videoType; // 'youtube', 'bunny', 'direct'
  final bool autoPlay;
  final VoidCallback? onEnded;

  const VideoPlayerWidget({
    required this.videoUrl,
    this.videoType,
    this.autoPlay = false,
    this.onEnded,
  });

  @override
  State<VideoPlayerWidget> createState() => _VideoPlayerWidgetState();
}

class _VideoPlayerWidgetState extends State<VideoPlayerWidget> {
  VideoPlayerController? _controller;
  ChewieController? _chewieController;
  YoutubePlayerController? _youtubeController;

  @override
  void initState() {
    super.initState();
    _initializePlayer();
  }

  void _initializePlayer() async {
    final type = widget.videoType ?? _detectVideoType(widget.videoUrl);

    switch (type) {
      case 'youtube':
        _youtubeController = YoutubePlayerController(
          initialVideoId: YoutubePlayer.convertUrlToId(widget.videoUrl)!,
          flags: const YoutubePlayerFlags(
            autoPlay: false,
            mute: false,
          ),
        );
        break;

      case 'bunny':
      case 'direct':
        _controller = VideoPlayerController.networkUrl(Uri.parse(widget.videoUrl));
        await _controller!.initialize();
        _chewieController = ChewieController(
          videoPlayerController: _controller!,
          autoPlay: widget.autoPlay,
          looping: false,
          aspectRatio: _controller!.value.aspectRatio,
        );
        break;
    }

    if (mounted) setState(() {});

    // Track progress
    _controller?.addListener(() {
      if (_controller!.value.position >= _controller!.value.duration) {
        widget.onEnded?.call();
      }
    });
  }

  String _detectVideoType(String url) {
    if (url.contains('youtube.com') || url.contains('youtu.be')) return 'youtube';
    if (url.contains('bunny.net')) return 'bunny';
    return 'direct';
  }

  @override
  void dispose() {
    _youtubeController?.close();
    _chewieController?.dispose();
    _controller?.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (_youtubeController != null) {
      return YoutubePlayer(controller: _youtubeController!);
    }

    if (_chewieController != null) {
      return Chewie(controller: _chewieController!);
    }

    return const Center(child: CircularProgressIndicator());
  }
}
```

---

## 8. Quiz Interface

```dart
// lib/features/quizzes/presentation/pages/quiz_taking_page.dart
class QuizTakingPage extends ConsumerStatefulWidget {
  final String quizId;

  const QuizTakingPage({required this.quizId});

  @override
  ConsumerState<QuizTakingPage> createState() => _QuizTakingPageState();
}

class _QuizTakingPageState extends ConsumerState<QuizTakingPage> {
  final PageController _pageController = PageController();
  final Map<String, dynamic> _answers = {};

  @override
  Widget build(BuildContext context) {
    final quizAsync = ref.watch(quizByIdProvider(widget.quizId));

    return quizAsync.when(
      data: (quiz) => Scaffold(
        appBar: AppBar(
          title: Text(quiz.title),
          actions: [
            TextButton(
              onPressed: () => _submitQuiz(quiz),
              child: const Text('Submit'),
            ),
          ],
        ),
        body: Column(
          children: [
            LinearProgressIndicator(value: _calculateProgress(quiz)),
            Expanded(
              child: PageView.builder(
                controller: _pageController,
                itemCount: quiz.questions.length,
                itemBuilder: (context, index) {
                  return QuestionWidget(
                    question: quiz.questions[index],
                    answer: _answers[quiz.questions[index].id],
                    onAnswerChanged: (answer) {
                      setState(() => _answers[quiz.questions[index].id] = answer);
                    },
                  );
                },
              ),
            ),
          ],
        ),
      ),
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (e, s) => ErrorDisplay(message: e.toString()),
    );
  }

  void _submitQuiz(Quiz quiz) async {
    final result = await ref.read(quizRepositoryProvider).submitQuiz(
      quizId: widget.quizId,
      answers: _answers,
    );

    result.fold(
      (error) => showErrorSnackBar(context, error.message),
      (score) => Navigator.pushReplacement(
        context,
        MaterialPageRoute(builder: (_) => QuizResultPage(score: score)),
      ),
    );
  }
}
```

---

## 9. Error Handling & Loading States

```dart
// Global error handler
ErrorHandler {
  APIError (401, 403, 404, 422, 500):
  - 401 Unauthorized → Refresh token, if fails → logout
  - 403 Forbidden → Show "Permission denied" snackbar
  - 404 Not Found → Show "Resource not found" snackbar
  - 422 Validation → Show field-specific errors
  - 500 Server → Show "Something went wrong, please try again"

  NetworkError:
  - Show "No internet connection" banner
  - Auto-retry button

  TimeoutError:
  - Show "Request timeout, retry?"
}

// Loading states
LoadingWidget():
- Shimmer effects for lists
- Circular progress for full-screen
- Disabled buttons with loading spinner

// Empty states
EmptyState(type):
- No courses → "Browse our courses" button
- No enrollments → "Start learning today"
- No quizzes → "No quizzes available yet"
```

---

## 10. Testing Strategy

```dart
// Unit tests
test_utils/
  - mock_api_client.dart
  - mock_storage.dart
  - test_helpers.dart

// Example unit test
// lib/features/auth/tests/login_bloc_test.dart
void main() {
  late LoginBloc bloc;
  late MockAuthRepository mockRepo;

  setUp(() {
    mockRepo = MockAuthRepository();
    bloc = LoginBloc(authRepo: mockRepo);
  });

  tearDown(() => bloc.close());

  test('emits [Loading, Authenticated] on successful login', () {
    when(mockRepo.login('test@example.com', 'password123'))
        .thenAnswer((_) async => mockUser);

    bloc.add(LoginEvent(email: 'test@example.com', password: 'password123'));

    expectLater(
      bloc.stream,
      emitsInOrder([
        LoginState.initial().copyWith(isLoading: true),
        LoginState.initial().copyWith(isAuthenticated: true, user: mockUser),
      ]),
    );
  });
}

// Widget tests
// lib/features/course/tests/course_detail_widget_test.dart
void main() {
  testWidgets('shows course title and description', (tester) async {
    await tester.pumpWidget(
      MaterialApp(
        home: CourseDetailPage(
          course: Course(
            id: '1',
            title: 'Test Course',
            description: 'Test Description',
          ),
        ),
      ),
    );

    expect(find.text('Test Course'), findsOneWidget);
    expect(find.text('Test Description'), findsOneWidget);
  });

  testWidgets('shows loading indicator while fetching', (tester) async {
    whenListen(courseBloc, [CourseState.loading()]);

    await tester.pumpWidget(
      MaterialApp(
        home: Provider.value(
          value: courseBloc,
          child: const CourseDetailPage(courseId: '1'),
        ),
      ),
    );

    expect(find.byType(CircularProgressIndicator), findsOneWidget);
  });
}

// Integration tests
// integration_tests/app_test.dart
void main() {
  testWidgets('full login flow', (tester) async {
    await tester.pumpWidget(MyApp());
    await tester.pumpAndSettle();

    await tester.tap(find.text('Login'));
    await tester.pumpAndSettle();

    await tester.enterText(
      find.byKey(Key('email-field')),
      'test@example.com',
    );
    await tester.enterText(
      find.byKey(Key('password-field')),
      'password123',
    );

    await tester.tap(find.byKey(Key('login-submit')));
    await tester.pumpAndSettle();

    expect(find.text('Welcome'), findsOneWidget);
  });
}
```

---

## 11. Performance Optimization

```dart
// Image optimization
CachedNetworkImage(
  imageUrl: course.thumbnailUrl,
  placeholder: (context, url) => ShimmerWidget(),
  errorWidget: (context, url, error) => ErrorIcon(),
  maxWidthDiskCache: 600,
  memCacheWidth: 300,
)

// List optimization
ListView.builder(
  itemCount: courses.length,
  itemBuilder: (context, index) {
    return CourseCard(course: courses[index]);
  },
  cacheExtent: 2000,
)

// Lazy loading
PaginatedListView<T>(
  fetchFn: (page) => api.getCourses(page),
  builder: (context, item, index) => ItemWidget(item),
  loadingBuilder: () => LoadingSpinner(),
  errorBuilder: (error) => ErrorWidget(error),
)

// Code splitting
import 'package:flutter_deferred_widget/flutter_deferred_widget.dart';

final deferredRoutes = {
  '/settings': () => DeferredWidget(
    loadLibraryAsset,
    () => SettingsPage(),
    placeholder: () => LoadingPage(),
  ),
};
```

---

## 12. Security Considerations

```dart
// Secure storage
final secureStorage = SecureStorage();
await secureStorage.write(key: 'refresh_token', value: token);

// Certificate pinning (production)
SecurityContext context = SecurityContext.defaultContext;
context.setTrustedCertificatesBytes(certBytes);

// API key protection
// Never store API keys in client code
// Use backend proxy for sensitive APIs

// Input sanitization
final sanitizedEmail = email.trim().toLowerCase();
if (!EmailValidator.validate(sanitizedEmail)) {
  throw ValidationException('Invalid email');
}

// Request signing
class SecureApiClient extends BaseClient {
  Future<String> _signRequest(String path, Map<String, dynamic> body) async {
    final token = await secureStorage.read(key: 'access_token');
    final timestamp = DateTime.now().millisecondsSinceEpoch;
    final signature = hmacSha256('$path$timestamp$token', SECRET);
    return signature;
  }
}
```

---

## 13. Deployment Strategy

```dart
// Build configurations
// lib/config/app_config.dart
class AppConfig {
  static const String environment = String.fromEnvironment('ENV', defaultValue: 'dev');

  static ApiConfig get api {
    switch (environment) {
      case 'prod':
        return ApiConfig(
          baseUrl: 'https://api.sashalms.com',
          enableLogs: false,
          enableCrashlytics: true,
        );
      case 'staging':
        return ApiConfig(
          baseUrl: 'https://staging-api.sashalms.com',
          enableLogs: true,
          enableCrashlytics: true,
        );
      default:
        return ApiConfig(
          baseUrl: 'http://localhost:8000',
          enableLogs: true,
          enableCrashlytics: false,
        );
    }
  }
}

// Build commands
flutter build apk --release --dart-define=ENV=prod
flutter build appbundle --release --dart-define=ENV=prod
flutter build ios --release --dart-define=ENV=prod

// Version management
// pubspec.yaml
version: 1.0.0+1

// Auto-increment version script
// scripts/update_version.sh
#!/bin/bash
version=$(grep 'version: ' pubspec.yaml | awk '{print $2}')
build_number=${version#*+}
new_build_number=$((build_number + 1))
sed -i "s/version: .*/version: ${version%+*}+$new_build_number/" pubspec.yaml
```

---

## 14. Monitoring & Analytics

```dart
// Firebase Crashlytics
import 'package:firebase_crashlytics/firebase_crashlytics.dart';

void main() async {
  await Firebase.initializeApp();
  FlutterError.onError = (details) {
    FirebaseCrashlytics.instance.recordError(
      details.exception,
      details.stack,
    );
  };
}

// Custom error tracking
class ErrorTracker {
  static void trackError(dynamic error, StackTrace? stack) {
    FirebaseCrashlytics.instance.recordError(error, stack);
  }

  static void setUserId(String userId) {
    FirebaseCrashlytics.instance.setUserIdentifier(userId);
  }

  static void addCustomKey(String key, dynamic value) {
    FirebaseCrashlytics.instance.setCustomKey(key, value);
  }
}

// Analytics
class AnalyticsService {
  static void logEvent(String name, {Map<String, dynamic>? parameters}) {
    FirebaseAnalytics.instance.logEvent(
      name: name,
      parameters: parameters,
    );
  }

  static void logScreenView(String screenName) {
    FirebaseAnalytics.instance.logScreenView(screenName: screenName);
  }

  static void logLogin(String method) => logEvent('login', parameters: {'method': method});
  static void logCourseEnroll(String courseId) => logEvent('course_enroll', parameters: {'course_id': courseId});
  static void logQuizComplete(String quizId, int score) => logEvent('quiz_complete', parameters: {'quiz_id': quizId, 'score': score});
  static void logPurchase(String orderId, double amount) => logEvent('purchase', parameters: {'order_id': orderId, 'amount': amount});
}

// Performance monitoring
class PerformanceMonitor {
  static Future<T> trace<T>(String name, Future<T> Function() fn) async {
    final trace = FirebasePerformance.instance.newTrace(name);
    await trace.start();
    try {
      return await fn();
    } finally {
      await trace.stop();
    }
  }
}
```

---

## 15. Migration Checklist

### Phase 1: Foundation
☐ Set up Flutter project with Riverpod + GoRouter
☐ Configure environment-based API config
☐ Implement secure storage wrapper
☐ Create base API client with interceptors
☐ Set up Firebase (Crashlytics, Analytics)
☐ Create folder structure per architecture

### Phase 2: Auth
☐ Login/Register screens
☐ Token management (access + refresh)
☐ Auth state persistence
☐ Protected routes
☐ Profile management

### Phase 3: Core Features
☐ Course listing + detail pages
☐ Video player integration
☐ Quiz taking + submission
☐ Progress tracking
☐ Certificate viewing
☐ Payment flow (Razorpay)

### Phase 4: Company Portal
☐ Internship listings
☐ Work log submission
☐ Attendance tracking
☐ Dashboard analytics

### Phase 5: Polish
☐ Animations + transitions
☐ Error handling completeness
☐ Loading states
☐ Offline support
☐ Performance optimization
☐ Testing coverage > 70%

### Phase 6: Launch
☐ Beta testing with real users
☐ Crash fixes
☐ Store screenshots + metadata
☐ App Store submission
☐ Play Store submission
