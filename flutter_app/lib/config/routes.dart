// lib/config/routes.dart
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../features/auth/presentation/providers/auth_provider.dart';
import '../features/auth/presentation/providers/auth_state.dart';
import '../features/auth/presentation/providers/onboarding_provider.dart';
import '../features/auth/presentation/providers/pending_role_selection.dart';
import '../features/auth/presentation/pages/splash_page.dart';
import '../features/auth/presentation/pages/login_page.dart';
import '../features/auth/presentation/pages/get_started_page.dart';
import '../features/auth/presentation/pages/register_page.dart';
import '../features/auth/presentation/pages/forgot_password_page.dart';
import '../features/auth/presentation/pages/reset_password_page.dart';
import '../features/auth/presentation/pages/verify_email_page.dart';
import '../features/auth/presentation/pages/role_selection_page.dart';
import '../features/home/presentation/pages/main_scaffold.dart';
import '../features/courses/presentation/pages/course_detail_page.dart';
import '../features/courses/presentation/pages/lesson_page.dart';
import '../features/quizzes/presentation/pages/quiz_taking_page.dart';
import '../features/assignments/presentation/pages/assignment_page.dart';
import '../features/profile/presentation/pages/public_profile_page.dart';
import '../features/admin/presentation/pages/admin_scaffold.dart';
import '../features/live_classes/presentation/live_class_list_screen.dart';
import '../features/live_classes/presentation/live_class_detail_screen.dart';
import '../features/live_classes/presentation/join_live_class_screen.dart';
import '../features/learning/learning_workspace.dart';
import '../features/learning/recording_reader.dart';

/// Bridge between Riverpod state changes and GoRouter's refreshListenable
class _GoRouterRefresh extends ChangeNotifier {
  _GoRouterRefresh(ProviderContainer container) {
    // Listen to auth provider changes
    container.listen<AuthState>(
      authProvider,
      (_, __) => notifyListeners(),
    );
    // Listen to pending role selection changes
    container.listen<Map<String, String>?>(
      pendingRoleSelectionProvider,
      (_, __) => notifyListeners(),
    );
  }
}

final routerProvider = Provider<GoRouter>((ref) {
  final refresh = _GoRouterRefresh(ref.container);

  return GoRouter(
    initialLocation: '/splash',
    refreshListenable: refresh,
    redirect: (context, state) {
      final loc = state.matchedLocation;
      final authState = ref.read(authProvider);
      final pendingRole = ref.read(pendingRoleSelectionProvider);

      const authPages = {
        '/login',
        '/get-started',
        '/register',
        '/forgot-password',
        '/reset-password',
        '/verify-email',
        '/role-selection',
      };
      final isAuthPage = authPages.contains(loc);
      final isSplash = loc == '/splash';

      final isAuth = authState.maybeWhen(
        authenticated: (_) => true,
        orElse: () => false,
      );
      final isInitial = authState.maybeWhen(
        initial: () => true,
        orElse: () => false,
      );

      // Pending role selection: redirect to role-selection page with data
      if (pendingRole != null && loc != '/role-selection') {
        final data = pendingRole!;
        final params = {
          'email': data['email']!,
          'name': data['name']!,
          'picture': data['picture']!,
          'token': data['token']!,
        };
        return Uri(path: '/role-selection', queryParameters: params).toString();
      }

      // Startup: the stored-token check hasn't run yet. Sit on the splash
      // screen, which kicks off checkAuthStatus(); this redirect re-runs once
      // the auth state resolves to authenticated / unauthenticated.
      if (isInitial) {
        // Let a cold-start email-verification deep link through so it isn't
        // swallowed by the splash redirect; everything else waits on splash.
        if (loc == '/verify-email') return null;
        return isSplash ? null : '/splash';
      }

      // Logged in: keep the user out of the splash / login / register screens.
      if (isAuth) {
        // Extract user to check admin role
        final user = authState.maybeWhen(authenticated: (u) => u, orElse: () => null);
        final isAdmin = user?.isAdmin ?? false;

        if (isSplash || loc == '/login' || loc == '/register' || loc == '/role-selection') {
          return isAdmin ? '/admin' : '/';
        }
        // Admin users should stay on admin pages; non-admin users stay off them.
        if (isAdmin && loc != '/admin' && !loc.startsWith('/admin/')) {
          return '/admin';
        }
        if (!isAdmin && loc.startsWith('/admin')) {
          return '/';
        }
        return null;
      }

      // Not authenticated: the whole app is gated behind login. Allow only the
      // auth screens — and the public profile (/u/<username>), a shareable,
      // read-only page that must open for anyone, signed in or not.
      if (isAuthPage) return null;
      if (loc.startsWith('/u/')) return null;
      // First-ever open lands on the Get Started onboarding; afterwards (flag
      // persisted) unauthenticated users go straight to Login.
      final onboardingDone = ref.read(onboardingCompletedProvider);
      return onboardingDone ? '/login' : '/get-started';
    },
    routes: [
      GoRoute(
        path: '/splash',
        pageBuilder: (context, state) => const MaterialPage(child: SplashPage()),
      ),
      GoRoute(
        path: '/login',
        pageBuilder: (context, state) => const MaterialPage(child: LoginPage()),
      ),
      GoRoute(
        path: '/get-started',
        pageBuilder: (context, state) =>
            const MaterialPage(child: GetStartedPage()),
      ),
      GoRoute(
        path: '/register',
        pageBuilder: (context, state) => MaterialPage(
          child: RegisterPage(initialRole: state.uri.queryParameters['role']),
        ),
      ),
      GoRoute(
        path: '/forgot-password',
        pageBuilder: (context, state) =>
            const MaterialPage(child: ForgotPasswordPage()),
      ),
      GoRoute(
        path: '/reset-password',
        pageBuilder: (context, state) => MaterialPage(
          child: ResetPasswordPage(token: state.uri.queryParameters['token']),
        ),
      ),
      GoRoute(
        path: '/verify-email',
        pageBuilder: (context, state) => MaterialPage(
          child: VerifyEmailPage(
            email: state.uri.queryParameters['email'],
            token: state.uri.queryParameters['token'],
          ),
        ),
      ),
      GoRoute(
        path: '/role-selection',
        pageBuilder: (context, state) => MaterialPage(
          child: RoleSelectionPage(
            email: state.uri.queryParameters['email'] ?? '',
            name: state.uri.queryParameters['name'] ?? '',
            picture: state.uri.queryParameters['picture'] ?? '',
            token: state.uri.queryParameters['token'] ?? '',
          ),
        ),
      ),
      GoRoute(
        path: '/admin',
        pageBuilder: (context, state) => const MaterialPage(child: AdminScaffold()),
      ),
      GoRoute(
        path: '/',
        pageBuilder: (context, state) => const MaterialPage(child: MainScaffold()),
        routes: [
          GoRoute(path: 'learning', builder: (context, state) => const LearningWorkspace()),
          GoRoute(path: 'recordings/:id', builder: (context, state) {
            final id = int.tryParse(state.pathParameters['id'] ?? '');
            return id == null || id <= 0 ? const _InvalidLiveClassIdPage() : RecordingReaderPage(classId: id);
          }),
          GoRoute(
            path: 'courses/:id',
            pageBuilder: (context, state) {
              final id = state.pathParameters['id']!;
              return MaterialPage(child: CourseDetailPage(courseId: id));
            },
          ),
          GoRoute(
            path: 'lessons/:id',
            pageBuilder: (context, state) {
              final id = state.pathParameters['id']!;
              return MaterialPage(child: LessonPage(lessonId: id));
            },
          ),
          GoRoute(
            path: 'courses/:courseId/quizzes/:quizId',
            pageBuilder: (context, state) {
              final courseId = int.parse(state.pathParameters['courseId']!);
              final quizId = int.parse(state.pathParameters['quizId']!);
              return MaterialPage(
                child: QuizTakingPage(courseId: courseId, quizId: quizId),
              );
            },
          ),
          GoRoute(
            path: 'assignment/:id',
            pageBuilder: (context, state) {
              final id = int.parse(state.pathParameters['id']!);
              return MaterialPage(child: AssignmentPage(assignmentId: id));
            },
          ),
          GoRoute(
            path: 'u/:username',
            pageBuilder: (context, state) => MaterialPage(
              child:
                  PublicProfilePage(username: state.pathParameters['username']!),
            ),
          ),
          GoRoute(
            path: 'live-classes',
            pageBuilder: (context, state) =>
                const MaterialPage(child: LiveClassListScreen()),
          ),
          GoRoute(
            path: 'live-classes/:id',
            pageBuilder: (context, state) {
              // tryParse, not parse: this id can arrive from an external
              // deep link (FCM push / notification tap), so a malformed or
              // tampered value must not throw inside the pageBuilder — it
              // falls back to an inline error with a way back to the list.
              final id = int.tryParse(state.pathParameters['id'] ?? '');
              if (id == null) {
                return const MaterialPage(
                  child: _InvalidLiveClassIdPage(),
                );
              }
              return MaterialPage(child: LiveClassDetailScreen(classId: id));
            },
          ),
          GoRoute(
            path: 'live-classes/:id/join',
            pageBuilder: (context, state) {
              final id = int.tryParse(state.pathParameters['id'] ?? '');
              if (id == null) {
                return const MaterialPage(
                  child: _InvalidLiveClassIdPage(),
                );
              }
              return MaterialPage(child: JoinLiveClassScreen(classId: id));
            },
          ),
        ],
      ),
    ],
    errorPageBuilder: (context, state) => MaterialPage(
      child: Scaffold(
        body: Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const Icon(Icons.error_outline, size: 64),
              const SizedBox(height: 16),
              Text('Page not found: ${state.uri}'),
              const SizedBox(height: 16),
              ElevatedButton(
                onPressed: () => context.go('/'),
                child: const Text('Go Home'),
              ),
            ],
          ),
        ),
      ),
    ),
  );
});

/// Shown instead of throwing when a `live-classes/:id` deep link (e.g. from
/// an FCM push) carries a non-numeric or missing id. Mirrors the router's
/// own errorPageBuilder look, but routes back to the live-classes list
/// rather than the app root.
class _InvalidLiveClassIdPage extends StatelessWidget {
  const _InvalidLiveClassIdPage();

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.error_outline, size: 64),
            const SizedBox(height: 16),
            const Text('This live class link looks invalid.'),
            const SizedBox(height: 16),
            ElevatedButton(
              onPressed: () => context.go('/live-classes'),
              child: const Text('Go to Live Classes'),
            ),
          ],
        ),
      ),
    );
  }
}
