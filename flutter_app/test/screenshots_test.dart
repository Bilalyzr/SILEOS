// test/screenshots_test.dart
//
// Offline screenshot harness for the "Bold & Energetic" redesign.
//
// Renders each screen at phone size with the real app theme and writes a PNG
// into the `screenshots/` folder. No backend, device, or login required — run:
//
//   flutter test test/screenshots_test.dart
//
// Data-driven screens (home feed, dashboard, courses, etc.) render in their
// loading / empty / "sign in" state because there is no live backend here;
// self-contained screens (auth, about, settings, AR gallery, …) render fully.
import 'dart:io';
import 'package:flutter/rendering.dart';
import 'dart:ui' as ui;

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:sashalms/config/theme.dart';

// Screens
import 'package:sashalms/features/auth/presentation/pages/splash_page.dart';
import 'package:sashalms/features/auth/presentation/pages/login_page.dart';
import 'package:sashalms/features/auth/presentation/pages/register_page.dart';
import 'package:sashalms/features/auth/presentation/pages/forgot_password_page.dart';
import 'package:sashalms/features/auth/presentation/pages/reset_password_page.dart';
import 'package:sashalms/features/auth/presentation/pages/verify_email_page.dart';
import 'package:sashalms/features/home/presentation/pages/home_page.dart';
import 'package:sashalms/features/home/presentation/pages/main_scaffold.dart';
import 'package:sashalms/features/dashboard/presentation/pages/dashboard_page.dart';
import 'package:sashalms/features/courses/presentation/pages/all_courses_page.dart';
import 'package:sashalms/features/courses/presentation/pages/course_detail_page.dart';
import 'package:sashalms/features/courses/presentation/pages/lesson_page.dart';
import 'package:sashalms/features/cart/presentation/pages/cart_page.dart';
import 'package:sashalms/features/wishlist/presentation/pages/wishlist_page.dart';
import 'package:sashalms/features/quizzes/presentation/pages/quiz_taking_page.dart';
import 'package:sashalms/features/assignments/presentation/pages/assignment_page.dart';
import 'package:sashalms/features/blog/presentation/pages/blog_list_page.dart';
import 'package:sashalms/features/blog/presentation/pages/blog_detail_page.dart';
import 'package:sashalms/features/internships/presentation/pages/internships_page.dart';
import 'package:sashalms/features/internships/presentation/pages/internship_detail_page.dart';
import 'package:sashalms/features/profile/presentation/pages/profile_page.dart';
import 'package:sashalms/features/profile/presentation/pages/settings_page.dart';
import 'package:sashalms/features/about/presentation/pages/about_page.dart';
import 'package:sashalms/features/certificates/presentation/pages/verify_certificate_page.dart';
import 'package:sashalms/features/companies/presentation/pages/for_companies_page.dart';
import 'package:sashalms/features/ar_gallery/presentation/pages/ar_gallery_page.dart';

/// Logical phone canvas (Pixel-ish). Captured at 2x for crisp PNGs.
const Size _canvas = Size(390, 844);
const double _pixelRatio = 2.0;
const String _outDir = 'screenshots';

/// One screen to capture: a stable file name and a builder for the widget.
class _Shot {
  final String name;
  final Widget Function() build;
  const _Shot(this.name, this.build);
}

final List<_Shot> _shots = [
  // Auth
  _Shot('01_splash', () => const SplashPage()),
  _Shot('02_login', () => const LoginPage()),
  _Shot('03_register', () => const RegisterPage()),
  _Shot('04_forgot_password', () => const ForgotPasswordPage()),
  _Shot('05_reset_password', () => const ResetPasswordPage(token: 'sample-token')),
  _Shot('06_verify_email', () => const VerifyEmailPage(email: 'student@example.com')),
  // Home / nav / dashboard
  _Shot('07_main_scaffold', () => const MainScaffold()),
  _Shot('08_home', () => const HomePage()),
  _Shot('09_dashboard', () => const DashboardPage()),
  // Courses
  _Shot('10_all_courses', () => const AllCoursesPage()),
  _Shot('11_course_detail', () => const CourseDetailPage(courseId: '1')),
  _Shot('12_lesson', () => const LessonPage(lessonId: '1')),
  _Shot('13_cart', () => const CartPage()),
  _Shot('14_wishlist', () => const WishlistPage()),
  // Learning & content
  _Shot('15_quiz', () => const QuizTakingPage(courseId: 1, quizId: 1)),
  _Shot('16_assignment', () => const AssignmentPage(assignmentId: 1)),
  _Shot('17_blog_list', () => const BlogListPage()),
  _Shot('18_blog_detail', () => const BlogDetailPage(slug: 'sample-post')),
  _Shot('19_internships', () => const InternshipsPage()),
  _Shot('20_internship_detail', () => const InternshipDetailPage(slug: 'sample-internship')),
  // Profile & misc
  _Shot('21_profile', () => const ProfilePage()),
  _Shot('22_settings', () => const SettingsPage()),
  _Shot('23_about', () => const AboutPage()),
  _Shot('24_verify_certificate', () => const VerifyCertificatePage()),
  _Shot('25_for_companies', () => const ForCompaniesPage()),
  _Shot('26_ar_gallery', () => const ArGalleryPage()),
];

void main() {
  // No network in tests — fall back to bundled/system fonts instead of fetching
  // Google Fonts (keeps layout/colours faithful; glyphs use a fallback family).
  GoogleFonts.config.allowRuntimeFetching = false;

  setUpAll(() async {
    SharedPreferences.setMockInitialValues({});
    final messenger = TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger;
    messenger.setMockMethodCallHandler(const MethodChannel('plugins.it_nomads.com/flutter_secure_storage'), (call) async => call.method == 'readAll' ? <String, String>{} : null);
    messenger.setMockMethodCallHandler(const MethodChannel('razorpay_flutter'), (call) async => null);
    Directory(_outDir).createSync(recursive: true);
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger.setMockMethodCallHandler(const MethodChannel('plugins.flutter.io/path_provider'), (call) async => Directory.systemTemp.path);
    // Load the same bundled font variants as production before measuring layouts.
    for (final weight in FontWeight.values) {
      for (final style in FontStyle.values) {
        GoogleFonts.inter(fontWeight: weight, fontStyle: style);
        GoogleFonts.plusJakartaSans(fontWeight: weight, fontStyle: style);
      }
    }
    await GoogleFonts.pendingFonts();
  });

  for (final shot in _shots) {
    testWidgets('screenshot ${shot.name}', (tester) async {
      tester.view.physicalSize =
          Size(_canvas.width * _pixelRatio, _canvas.height * _pixelRatio);
      tester.view.devicePixelRatio = _pixelRatio;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);

      final boundaryKey = GlobalKey();

      await tester.pumpWidget(
        ProviderScope(
          child: MaterialApp(
            debugShowCheckedModeBanner: false,
            theme: AppTheme.lightTheme,
            home: RepaintBoundary(
              key: boundaryKey,
              child: shot.build(),
            ),
          ),
        ),
      );

      // Let async providers settle into loading/empty/data state and let any
      // intro animations advance a little. Avoid pumpAndSettle: several screens
      // run repeating timers/animations that never "settle".
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 400));
      await tester.pump(const Duration(milliseconds: 400));

      final boundary = boundaryKey.currentContext!.findRenderObject()
          as RenderRepaintBoundary;
      // Rasterization completes outside the test's fake clock.
      await tester.runAsync(() async {
        final image = await boundary.toImage(pixelRatio: _pixelRatio);
        final bytes = await image.toByteData(format: ui.ImageByteFormat.png);
        image.dispose();
        expect(bytes, isNotNull);
        File('$_outDir/${shot.name}.png').writeAsBytesSync(bytes!.buffer.asUint8List());
      });
      await tester.pumpWidget(const SizedBox.shrink());
    });
  }
}
