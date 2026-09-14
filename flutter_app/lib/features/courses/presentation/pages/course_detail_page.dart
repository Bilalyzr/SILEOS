import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:cached_network_image/cached_network_image.dart';
import 'package:go_router/go_router.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:razorpay_flutter/razorpay_flutter.dart';
import '../../../../shared/widgets/video/video_player_widget.dart';
import '../../../../core/utils/bunny_video.dart';
import 'package:sashalms/features/courses/domain/entities/course.dart';
import 'package:sashalms/config/app_config.dart';
import 'package:sashalms/features/courses/domain/entities/lesson.dart';
import '../widgets/next_lesson_card.dart';
import '../providers/course_provider.dart';
import '../providers/course_filter_providers.dart';
import '../providers/video_playback_provider.dart';
import '../../../../shared/widgets/common/app_loader.dart';
import '../../../../shared/widgets/common/error_display.dart';
import '../../../auth/presentation/providers/auth_provider.dart';
import '../../../../config/theme.dart';
import '../../../../config/design_tokens.dart';
import '../../../../shared/widgets/common/app_button.dart';

class CourseDetailPage extends ConsumerStatefulWidget {
  final String courseId;

  const CourseDetailPage({super.key, required this.courseId});

  @override
  ConsumerState<CourseDetailPage> createState() => _CourseDetailPageState();
}

class _CourseDetailPageState extends ConsumerState<CourseDetailPage> {
  late Razorpay _razorpay;
  bool _isEnrolling = false;
  String _couponCode = "";
  final _couponController = TextEditingController();

  // Coupon validation state (set by the Apply button in the checkout sheet).
  bool _couponValidating = false;
  double? _couponDiscount; // amount off, null until a coupon is validated
  String? _couponMessage; // feedback shown under the field
  bool _couponValid = false;
  final ScrollController _scrollController = ScrollController();
  final GlobalKey<State> _videoPlayerKey = GlobalKey<State>();
  Lesson? _activeLesson;

  Lesson? _getNextLesson(Course course, Lesson current) {
    if (course.lessons.isEmpty) return null;
    final sorted = [...course.lessons]
      ..sort((a, b) => a.order.compareTo(b.order));
    final idx = sorted.indexWhere((l) => l.id == current.id);
    if (idx < 0 || idx + 1 >= sorted.length) return null;
    return sorted[idx + 1];
  }

  Future<void> _markLessonAsComplete(String courseId, String lessonId) async {
    final result = await ref.read(completeLessonUseCaseProvider).call(
      courseId: int.parse(courseId),
      lessonId: int.parse(lessonId),
    );
    result.fold(
      (failure) {
        debugPrint('Failed to mark lesson complete: $failure');
      },
      (_) {
        // Refresh the course detail data and learning dashboard to update progress
        ref.invalidate(courseByIdProvider(courseId));
        ref.invalidate(myCoursesProvider);
      },
    );
  }

  @override
  void initState() {
    super.initState();
    _razorpay = Razorpay();
    _razorpay.on(Razorpay.EVENT_PAYMENT_SUCCESS, _handlePaymentSuccess);
    _razorpay.on(Razorpay.EVENT_PAYMENT_ERROR, _handlePaymentError);
    _razorpay.on(Razorpay.EVENT_EXTERNAL_WALLET, _handleExternalWallet);
  }

  @override
  void dispose() {
    _razorpay.clear();
    _couponController.dispose();
    _scrollController.dispose();
    super.dispose();
  }

  void _handlePaymentSuccess(PaymentSuccessResponse response) async {
    if (!mounted) return;
    setState(() {
      _isEnrolling = true;
    });

    final repo = ref.read(courseRepositoryProvider);
    final paymentData = {
      'razorpay_order_id': response.orderId,
      'razorpay_payment_id': response.paymentId,
      'razorpay_signature': response.signature,
      'course_id': int.parse(widget.courseId),
      if (_couponCode.trim().isNotEmpty) 'coupon_code': _couponCode.trim(),
    };

    final result = await repo.verifyPayment(paymentData);
    result.fold(
      (failure) {
        if (!mounted) return;
        setState(() {
          _isEnrolling = false;
        });
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
              failure.when(
                server: (msg, _) => msg,
                network: (msg) => msg,
                cache: (msg) => msg,
                unauthorized: (msg) => msg ?? 'Unauthorized',
                forbidden: (msg) => msg ?? 'Forbidden',
                notFound: (msg) => msg ?? 'Not found',
                validation: (msg, _) => msg,
                unknown: (msg) => msg ?? 'Payment verification failed',
              ),
            ),
          ),
        );
      },
      (_) {
        if (!mounted) return;
        setState(() {
          _isEnrolling = false;
        });
        ref.refresh(courseByIdProvider(widget.courseId));
        ref.refresh(myCoursesProvider);
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Payment verified successfully! You are enrolled.')),
        );
        Navigator.of(context).pop(); // Close checkout sheet
        ref.read(scaffoldTabProvider.notifier).state = 2; // Learning Dashboard / My Courses
        context.go('/');
      },
    );
  }

  void _handlePaymentError(PaymentFailureResponse response) {
    if (kDebugMode) {
      debugPrint('Razorpay error code=${response.code} message=${response.message}');
    }
    if (!mounted) return;
    setState(() {
      _isEnrolling = false;
    });
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text('Payment Failed: ${response.message ?? "User cancelled"}')),
    );
  }

  void _handleExternalWallet(ExternalWalletResponse response) {
    // Handle external wallet integration if needed
  }

  /// The lesson the learner should resume at, inferred from overall progress
  /// (no per-lesson completion flag is available on the entity). Returns the
  /// lesson plus its 1-based position, or null when there are no lessons.
  ({Lesson lesson, int number})? _resumeLesson(Course course) {
    if (course.lessons.isEmpty) return null;
    final sorted = [...course.lessons]
      ..sort((a, b) => a.order.compareTo(b.order));
    var idx = ((course.progress.clamp(0, 100) / 100) * sorted.length).floor();
    if (idx >= sorted.length) idx = sorted.length - 1; // course finished
    return (lesson: sorted[idx], number: idx + 1);
  }

  Future<void> _continueLearning(Course course) async {
    final resume = _resumeLesson(course);
    if (resume != null) {
      setState(() {
        _activeLesson = resume.lesson;
      });
      _scrollController.animateTo(
        0.0,
        duration: const Duration(milliseconds: 300),
        curve: Curves.easeInOut,
      );
    } else {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('No lessons available in this course yet.')),
      );
    }
  }

  Future<void> _startCheckoutFlow(dynamic course) async {
    final userState = ref.read(authProvider);
    final user = userState.maybeWhen(
      authenticated: (u) => u,
      orElse: () => null,
    );

    if (user == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Please login to enroll in this course.')),
      );
      context.push('/login');
      return;
    }

    _couponController.clear();
    _couponCode = "";
    // Reset coupon validation each time the sheet is opened.
    _couponValid = false;
    _couponDiscount = null;
    _couponMessage = null;
    _couponValidating = false;

    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Theme.of(context).brightness == Brightness.dark
          ? AppTheme.surfaceDark
          : Colors.white,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (context) {
        final theme = Theme.of(context);
        final isDark = theme.brightness == Brightness.dark;

        return StatefulBuilder(
          builder: (context, setSheetState) {
            final basePrice = course.salePrice ?? course.price;
            // Subtract a validated coupon discount (clamped at 0).
            final finalPrice = _couponValid && _couponDiscount != null
                ? (basePrice - _couponDiscount!).clamp(0, basePrice).toDouble()
                : basePrice;

            return Padding(
              padding: EdgeInsets.only(
                bottom: MediaQuery.of(context).viewInsets.bottom + 24,
                left: 24,
                right: 24,
                top: 24,
              ),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text(
                        'Checkout Order',
                        style: GoogleFonts.plusJakartaSans(
                          fontWeight: FontWeight.bold,
                          fontSize: 20,
                        ),
                      ),
                      IconButton(
                        icon: const Icon(Icons.close),
                        onPressed: () => Navigator.pop(context),
                      ),
                    ],
                  ),
                  const SizedBox(height: 16),
                  // Course summary row
                  Container(
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: isDark ? const Color(0xFF1E293B) : const Color(0xFFF8FAFC),
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: Row(
                      children: [
                        ClipRRect(
                          borderRadius: BorderRadius.circular(8),
                          child: CachedNetworkImage(
                            imageUrl: course.featuredImage,
                            width: 80,
                            height: 60,
                            fit: BoxFit.cover,
                            errorWidget: (_, __, ___) => Container(
                              width: 80,
                              height: 60,
                              color: AppTheme.primary.withOpacity(0.1),
                              child: const Icon(Icons.school, color: AppTheme.primary),
                            ),
                          ),
                        ),
                        const SizedBox(width: 16),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                course.title,
                                style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13),
                                maxLines: 2,
                                overflow: TextOverflow.ellipsis,
                              ),
                              const SizedBox(height: 4),
                              Text(
                                course.price == 0 ? 'FREE' : '₹${course.salePrice ?? course.price}',
                                style: const TextStyle(
                                  color: AppTheme.primary,
                                  fontWeight: FontWeight.bold,
                                  fontSize: 14,
                                ),
                              ),
                            ],
                          ),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 20),
                  // Coupon input + Apply button
                  Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Expanded(
                        child: TextField(
                          controller: _couponController,
                          textCapitalization: TextCapitalization.characters,
                          enabled: !_couponValid,
                          decoration: InputDecoration(
                            hintText: 'Enter Voucher/Coupon Code',
                            prefixIcon:
                                const Icon(Icons.confirmation_number_outlined),
                            contentPadding: const EdgeInsets.symmetric(
                                horizontal: 16, vertical: 12),
                            border: OutlineInputBorder(
                              borderRadius: BorderRadius.circular(10),
                            ),
                          ),
                          onChanged: (val) {
                            _couponCode = val;
                          },
                        ),
                      ),
                      const SizedBox(width: 8),
                      SizedBox(
                        height: 48,
                        child: _couponValidating
                            ? const Padding(
                                padding: EdgeInsets.symmetric(horizontal: 20),
                                child: Center(
                                  child: SizedBox(
                                    width: 20,
                                    height: 20,
                                    child:
                                        CircularProgressIndicator(strokeWidth: 2),
                                  ),
                                ),
                              )
                            : _couponValid
                                ? OutlinedButton(
                                    onPressed: () {
                                      // Remove the applied coupon.
                                      setSheetState(() {
                                        _couponValid = false;
                                        _couponDiscount = null;
                                        _couponMessage = null;
                                        _couponController.clear();
                                        _couponCode = "";
                                      });
                                    },
                                    child: const Text('Remove'),
                                  )
                                : ElevatedButton(
                                    onPressed: () => _applyCoupon(
                                        course, basePrice, setSheetState),
                                    child: const Text('Apply'),
                                  ),
                      ),
                    ],
                  ),
                  if (_couponMessage != null) ...[
                    const SizedBox(height: 6),
                    Text(
                      _couponMessage!,
                      style: TextStyle(
                        fontSize: 12,
                        color: _couponValid ? AppTheme.success : AppTheme.danger,
                      ),
                    ),
                  ],
                  const SizedBox(height: 20),
                  // Pricing List
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      const Text('Course Price', style: TextStyle(color: Colors.grey)),
                      Text('₹${course.price.toStringAsFixed(0)}'),
                    ],
                  ),
                  if (course.salePrice != null && course.salePrice! < course.price) ...[
                    const SizedBox(height: 8),
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        const Text('Special Discount', style: TextStyle(color: Colors.grey)),
                        Text('-₹${(course.price - course.salePrice!).toStringAsFixed(0)}',
                            style: const TextStyle(color: AppTheme.success)),
                      ],
                    ),
                  ],
                  if (_couponValid && _couponDiscount != null && _couponDiscount! > 0) ...[
                    const SizedBox(height: 8),
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Text('Coupon (${_couponCode.trim().toUpperCase()})',
                            style: const TextStyle(color: Colors.grey)),
                        Text('-₹${_couponDiscount!.toStringAsFixed(0)}',
                            style: const TextStyle(color: AppTheme.success)),
                      ],
                    ),
                  ],
                  const Divider(height: 24),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      const Text('Total Amount', style: TextStyle(fontWeight: FontWeight.bold)),
                      Text(
                        course.price == 0 ? 'FREE' : '₹${finalPrice.toStringAsFixed(0)}',
                        style: const TextStyle(
                          color: AppTheme.primary,
                          fontWeight: FontWeight.bold,
                          fontSize: 18,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 24),
                  if (_isEnrolling)
                    const Center(child: CircularProgressIndicator())
                  else ...[
                    ElevatedButton(
                      onPressed: () async {
                        setSheetState(() {
                          _isEnrolling = true;
                        });
                        await _processCheckout(course, user);
                        setSheetState(() {
                          _isEnrolling = false;
                        });
                      },
                      style: ElevatedButton.styleFrom(
                        padding: const EdgeInsets.symmetric(vertical: 14),
                      ),
                      child: Text(finalPrice == 0 ? 'ENROLL NOW' : 'PAY & ENROLL'),
                    ),
                    // Dev-only shortcut — must NEVER ship in release, or anyone
                    // could enroll in paid courses for free.
                    if (kDebugMode) ...[
                      const SizedBox(height: 8),
                      OutlinedButton(
                        onPressed: () async {
                          setSheetState(() {
                            _isEnrolling = true;
                          });
                          await _simulateSuccess(course);
                          setSheetState(() {
                            _isEnrolling = false;
                          });
                        },
                        style: OutlinedButton.styleFrom(
                          padding: const EdgeInsets.symmetric(vertical: 12),
                        ),
                        child: const Text('Simulate Free Enrollment (Dev Mode)'),
                      ),
                    ],
                  ],
                ],
              ),
            );
          },
        );
      },
    );
  }

  /// Validates the typed coupon against the backend and, on success, records
  /// the discount so the checkout Total updates live. `setSheetState` rebuilds
  /// the bottom sheet (the outer page state doesn't drive it).
  Future<void> _applyCoupon(
    dynamic course,
    double basePrice,
    void Function(void Function()) setSheetState,
  ) async {
    final code = _couponController.text.trim();
    if (code.isEmpty) {
      setSheetState(() {
        _couponMessage = 'Enter a coupon code first.';
        _couponValid = false;
      });
      return;
    }

    setSheetState(() {
      _couponValidating = true;
      _couponMessage = null;
    });

    final result = await ref.read(courseRepositoryProvider).validateCoupon(
          code: code,
          courseId: int.parse(course.id),
          totalAmount: basePrice,
        );

    if (!mounted) return;

    result.fold(
      (failure) {
        setSheetState(() {
          _couponValidating = false;
          _couponValid = false;
          _couponDiscount = null;
          _couponMessage = failure.maybeWhen(
            server: (msg, _) => msg,
            network: (msg) => msg,
            orElse: () => 'Could not validate coupon. Try again.',
          );
        });
      },
      (data) {
        final valid = data['valid'] == true;
        setSheetState(() {
          _couponValidating = false;
          _couponValid = valid;
          _couponCode = code;
          _couponDiscount = valid
              ? (data['discount_amount'] as num?)?.toDouble() ?? 0
              : null;
          _couponMessage = (data['message'] as String?) ??
              (valid ? 'Coupon applied.' : 'Invalid coupon.');
        });
      },
    );
  }

  Future<void> _processCheckout(dynamic course, dynamic user) async {
    final repo = ref.read(courseRepositoryProvider);
    final courseIdInt = int.parse(course.id);
    final trimmedCoupon = _couponCode.trim();

    // 1. If user entered a coupon code or the course is free, try to enroll directly first
    if (trimmedCoupon.isNotEmpty || course.price == 0) {
      final enrollResult = await repo.enroll(
        courseIdInt,
        couponCode: trimmedCoupon.isNotEmpty ? trimmedCoupon : null,
      );

      bool enrollSuccess = false;
      String enrollError = "";

      enrollResult.fold(
        (failure) {
          enrollError = failure.maybeWhen(
            server: (msg, code) => code == 402 ? "payment_required" : msg,
            orElse: () => "Failed to enroll",
          );
        },
        (_) {
          enrollSuccess = true;
        },
      );

      if (enrollSuccess) {
        if (!mounted) return;
        ref.refresh(courseByIdProvider(course.id));
        ref.refresh(myCoursesProvider);
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Enrollment successful! You are now enrolled.')),
        );
        Navigator.of(context).pop(); // Close sheet
        ref.read(scaffoldTabProvider.notifier).state = 2; // Learning Dashboard / My Courses
        context.go('/');
        return;
      }

      // If enrollment failed but not because of payment_required, alert the user and return
      if (enrollError != "payment_required") {
        if (!mounted) return;
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Voucher status: $enrollError')),
        );
        return;
      }
    }

    // 2. Paid Course - Create order
    final orderResult = await repo.createPaymentOrder(
      courseIdInt,
      couponCode: trimmedCoupon.isNotEmpty ? trimmedCoupon : null,
    );

    orderResult.fold(
      (failure) {
        if (!mounted) return;
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Failed to generate order: ${failure.toString()}')),
        );
      },
      (orderData) {
        final options = {
          'key': orderData['key_id'],
          'amount': orderData['amount'],
          'name': 'SashaInfinity LMS',
          'description': course.title,
          'order_id': orderData['order_id'],
          'prefill': {
            'name': user.fullName,
            'email': user.email,
            if (user.phone != null) 'contact': user.phone,
          },
          'theme': {'color': '#f97316'}
        };

        try {
          _razorpay.open(options);
        } catch (e) {
          if (!mounted) return;
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('Razorpay failed to launch: $e')),
          );
        }
      },
    );
  }

  Future<void> _simulateSuccess(dynamic course) async {
    final repo = ref.read(courseRepositoryProvider);
    final courseIdInt = int.parse(course.id);

    // Call free bypass endpoint
    final result = await repo.enroll(courseIdInt);
    result.fold(
      (failure) {
        // If server enforces price check in database and fails (400), we tell them but refresh status
        if (!mounted) return;
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('[SIMULATION] Server enrolled or bypassed for dev testing.')),
        );
      },
      (_) {
        if (!mounted) return;
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Simulation enrollment successful!')),
        );
      },
    );

    if (!mounted) return;
    ref.refresh(courseByIdProvider(course.id));
    ref.refresh(myCoursesProvider);
    Navigator.of(context).pop(); // Close sheet
    ref.read(scaffoldTabProvider.notifier).state = 2; // Learning Dashboard / My Courses
    context.go('/');
  }

  void _showInstructorProfile(BuildContext context, Instructor instructor) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Theme.of(context).brightness == Brightness.dark
          ? AppTheme.surfaceDark
          : Colors.white,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (context) {
        final theme = Theme.of(context);
        final isDark = theme.brightness == Brightness.dark;

        return DraggableScrollableSheet(
          initialChildSize: 0.6,
          minChildSize: 0.4,
          maxChildSize: 0.9,
          expand: false,
          builder: (context, scrollController) {
            return SingleChildScrollView(
              controller: scrollController,
              padding: const EdgeInsets.all(24),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.center,
                children: [
                  Container(
                    width: 40,
                    height: 4,
                    margin: const EdgeInsets.only(bottom: 24),
                    decoration: BoxDecoration(
                      color: Colors.grey.withOpacity(0.3),
                      borderRadius: BorderRadius.circular(2),
                    ),
                  ),
                  CircleAvatar(
                    radius: 56,
                    backgroundColor: AppTheme.primary.withOpacity(0.1),
                    backgroundImage: instructor.avatar.startsWith('http')
                        ? CachedNetworkImageProvider(instructor.avatar)
                        : CachedNetworkImageProvider(
                            '${AppConfig.baseUrl}${instructor.avatar}'),
                    onBackgroundImageError: (_, __) {},
                  ),
                  const SizedBox(height: 16),
                  Text(
                    instructor.name,
                    style: GoogleFonts.plusJakartaSans(
                      fontWeight: FontWeight.bold,
                      fontSize: 24,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    'Professional Instructor',
                    style: theme.textTheme.bodyMedium?.copyWith(
                      color: theme.textTheme.bodyMedium?.color?.withOpacity(0.6),
                    ),
                  ),
                  const SizedBox(height: 24),
                  const Divider(),
                  const SizedBox(height: 24),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceAround,
                    children: [
                      _buildInstructorStat('Courses', '12', Icons.book_outlined),
                      _buildInstructorStat('Students', '1.2k', Icons.people_outline),
                      _buildInstructorStat('Rating', '4.8', Icons.star_outline),
                    ],
                  ),
                  const SizedBox(height: 32),
                  Align(
                    alignment: Alignment.centerLeft,
                    child: Text(
                      'About the Instructor',
                      style: GoogleFonts.plusJakartaSans(
                        fontWeight: FontWeight.w800,
                        fontSize: 19,
                        letterSpacing: -0.3,
                      ),
                    ),
                  ),
                  const SizedBox(height: 12),
                  Text(
                    '${instructor.name} is a seasoned expert in their field with years of practical experience. They are dedicated to helping students master new skills and achieve their professional goals through high-quality, engaging course content.',
                    style: const TextStyle(height: 1.5),
                  ),
                  const SizedBox(height: 32),
                  ElevatedButton(
                    onPressed: () {
                      Navigator.pop(context);
                      // In a real app, this would filter courses by this instructor
                      ref.read(selectedCategoryProvider.notifier).state = null;
                      ref.read(scaffoldTabProvider.notifier).state = 1; // Go to Catalog
                    },
                    style: ElevatedButton.styleFrom(
                      minimumSize: const Size(double.infinity, 50),
                    ),
                    child: const Text('View All Courses by this Instructor'),
                  ),
                  const SizedBox(height: 24),
                ],
              ),
            );
          },
        );
      },
    );
  }

  Widget _buildInstructorStat(String label, String value, IconData icon) {
    return Column(
      children: [
        Icon(icon, color: AppTheme.primary, size: 24),
        const SizedBox(height: 8),
        Text(
          value,
          style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
        ),
        Text(
          label,
          style: const TextStyle(color: Colors.grey, fontSize: 12),
        ),
      ],
    );
  }

  Widget _buildVideoPlayer(Course course, ThemeData theme) {
    if (_activeLesson != null) {
      final lesson = _activeLesson!;
      final next = _getNextLesson(course, lesson);
      final yt = lesson.youtubeUrl;
      final isYoutube = yt != null && yt.isNotEmpty && !BunnyVideo.isBunnyUrl(yt);
      final hasDirectVideo = lesson.videoUrl != null && lesson.videoUrl!.isNotEmpty;
      final videoSource = hasDirectVideo ? lesson.videoUrl : yt;

      if (isYoutube && !hasDirectVideo) {
        return VideoPlayerWidget(
          key: _videoPlayerKey,
          youtubeUrl: yt,
          autoPlay: true,
          videoDuration: lesson.duration,
          nextVideoTitle: next?.title,
          onEnded: () => _markLessonAsComplete(course.id, lesson.id),
          onPlayNext: next != null ? () => setState(() => _activeLesson = next) : null,
        );
      } else {
        return ref.watch(playableVideoUrlProvider(videoSource)).when(
              data: (url) => VideoPlayerWidget(
                key: _videoPlayerKey,
                videoUrl: url,
                autoPlay: true,
                videoDuration: lesson.duration,
                nextVideoTitle: next?.title,
                onEnded: () => _markLessonAsComplete(course.id, lesson.id),
                onPlayNext: next != null ? () => setState(() => _activeLesson = next) : null,
              ),
              loading: () => const AspectRatio(
                aspectRatio: 16 / 9,
                child: ColoredBox(
                  color: Colors.black,
                  child: Center(child: CircularProgressIndicator()),
                ),
              ),
              error: (_, __) => VideoPlayerWidget(
                key: _videoPlayerKey,
                videoUrl: videoSource,
                autoPlay: true,
                videoDuration: lesson.duration,
                nextVideoTitle: next?.title,
                onEnded: () => _markLessonAsComplete(course.id, lesson.id),
                onPlayNext: next != null ? () => setState(() => _activeLesson = next) : null,
              ),
            );
      }
    }

    if (course.introVideo != null && course.introVideo!.isNotEmpty) {
      if (course.introVideo!.contains('youtube.com') ||
          course.introVideo!.contains('youtu.be')) {
        return VideoPlayerWidget(
          key: _videoPlayerKey,
          youtubeUrl: course.introVideo,
          autoPlay: false,
        );
      } else {
        return ref.watch(previewVideoUrlProvider(course.introVideo)).when(
              data: (url) => VideoPlayerWidget(
                key: _videoPlayerKey,
                videoUrl: url,
                autoPlay: false,
                previewMaxSeconds: course.isEnrolled ? null : 10,
              ),
              loading: () => const AspectRatio(
                aspectRatio: 16 / 9,
                child: ColoredBox(
                  color: Colors.black,
                  child: Center(child: CircularProgressIndicator()),
                ),
              ),
              error: (_, __) => VideoPlayerWidget(
                key: _videoPlayerKey,
                videoUrl: course.introVideo!.startsWith('http')
                    ? course.introVideo
                    : null,
                autoPlay: false,
                previewMaxSeconds: course.isEnrolled ? null : 10,
              ),
            );
      }
    }

    return AspectRatio(
      aspectRatio: 16 / 9,
      child: CachedNetworkImage(
        imageUrl: course.featuredImage,
        fit: BoxFit.cover,
        placeholder: (context, url) => const Center(child: CircularProgressIndicator()),
        errorWidget: (context, url, error) => Container(
          color: theme.colorScheme.primary.withOpacity(0.05),
          child: const Icon(Icons.broken_image, size: 64, color: AppTheme.primary),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final courseAsync = ref.watch(courseByIdProvider(widget.courseId));
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;

    final isLandscape = MediaQuery.orientationOf(context) == Orientation.landscape;

    return Scaffold(
      appBar: isLandscape ? null : AppBar(
        title: const Text('Course Details'),
      ),
      body: courseAsync.when(
        data: (course) {
          final videoPlayer = _buildVideoPlayer(course, theme);

          if (isLandscape) {
            return Container(
              color: Colors.black,
              alignment: Alignment.center,
              child: videoPlayer,
            );
          }

          return SingleChildScrollView(
            controller: _scrollController,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                videoPlayer,

                // Up Next Video Card in Queue (shown only if playing a lesson and there's a next one)
                if (_activeLesson != null)
                  Builder(
                    builder: (context) {
                      final next = _getNextLesson(course, _activeLesson!);
                      if (next == null) return const SizedBox.shrink();
                      
                      final sorted = [...course.lessons]
                        ..sort((a, b) => a.order.compareTo(b.order));
                      final nextIndex = sorted.indexWhere((l) => l.id == next.id);
                      
                      return Padding(
                        padding: const EdgeInsets.fromLTRB(24, 16, 24, 0),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Row(
                              children: [
                                Icon(Icons.queue_play_next, size: 16, color: theme.colorScheme.primary),
                                const SizedBox(width: 6),
                                Text(
                                  'UP NEXT IN QUEUE',
                                  style: TextStyle(
                                    fontSize: 11,
                                    fontWeight: FontWeight.bold,
                                    color: theme.colorScheme.primary,
                                    letterSpacing: 1.2,
                                  ),
                                ),
                              ],
                            ),
                            const SizedBox(height: 8),
                            NextLessonCard(
                              lesson: next,
                              lessonNumber: nextIndex >= 0 ? nextIndex + 1 : 1,
                              label: 'Play Next Part',
                              onTap: () {
                                setState(() {
                                  _activeLesson = next;
                                });
                              },
                            ),
                          ],
                        ),
                      );
                    },
                  ),
              Padding(
                padding: const EdgeInsets.all(24.0),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    // Category & Level Badges
                    Row(
                      children: [
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                          decoration: BoxDecoration(
                            color: AppTheme.primary.withOpacity(0.1),
                            borderRadius: BorderRadius.circular(6),
                          ),
                          child: Text(
                            course.category.toUpperCase(),
                            style: const TextStyle(
                              color: AppTheme.primary,
                              fontSize: 10,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                        ),
                        const SizedBox(width: 8),
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                          decoration: BoxDecoration(
                            color: Colors.blue.withOpacity(0.1),
                            borderRadius: BorderRadius.circular(6),
                          ),
                          child: Text(
                            course.level.toUpperCase(),
                            style: const TextStyle(
                              color: Colors.blue,
                              fontSize: 10,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                        ),
                        if (course.institution != null && course.institution!.isNotEmpty) ...[
                          const SizedBox(width: 8),
                          Container(
                            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                            decoration: BoxDecoration(
                              color: Colors.indigo.withOpacity(0.1),
                              borderRadius: BorderRadius.circular(6),
                            ),
                            child: Text(
                              course.institution!.toUpperCase(),
                              style: const TextStyle(
                                color: Colors.indigo,
                                fontSize: 10,
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                          ),
                        ],
                      ],
                    ),
                    const SizedBox(height: 16),
                    // Title
                    Text(
                      course.title,
                      style: GoogleFonts.plusJakartaSans(
                        fontWeight: FontWeight.bold,
                        fontSize: 22,
                        height: 1.3,
                      ),
                    ),
                    const SizedBox(height: 12),
                    // Instructor Profile Row
                    Row(
                      children: [
                        CircleAvatar(
                          backgroundImage: course.instructor.avatar.startsWith('http')
                              ? CachedNetworkImageProvider(course.instructor.avatar)
                              : CachedNetworkImageProvider(
                                  '${AppConfig.baseUrl}${course.instructor.avatar}'),
                          radius: 20,
                          backgroundColor: AppTheme.primary.withOpacity(0.1),
                          onBackgroundImageError: (_, __) {},
                        ),
                        const SizedBox(width: 8),
                        Text(
                          'Created by ${course.instructor.name}',
                          style: theme.textTheme.bodyMedium?.copyWith(
                            color: theme.textTheme.bodyMedium?.color?.withOpacity(0.7),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 24),
                    // Mini course information card — a clean 4-up metric panel.
                    Container(
                      padding: const EdgeInsets.symmetric(vertical: 18),
                      decoration: BoxDecoration(
                        color: isDark ? AppTheme.surfaceDark : Colors.white,
                        borderRadius: BorderRadius.circular(AppRadius.lg),
                        border: Border.all(
                          color: isDark ? AppTheme.borderDark : AppTheme.borderLight,
                        ),
                        boxShadow: isDark ? null : AppShadows.soft,
                      ),
                      child: IntrinsicHeight(
                        child: Row(
                          crossAxisAlignment: CrossAxisAlignment.center,
                          children: [
                            _MetricCell(
                              icon: Icons.play_circle_outline,
                              value: '${course.stats.lessons}',
                              label: 'Lessons',
                            ),
                            _cellDivider(isDark),
                            _MetricCell(
                              icon: Icons.schedule,
                              value: '${course.stats.duration}h',
                              label: 'Duration',
                            ),
                            _cellDivider(isDark),
                            _MetricCell(
                              icon: Icons.people_outline,
                              value: _compact(course.stats.students),
                              label: 'Students',
                            ),
                            _cellDivider(isDark),
                            _MetricCell(
                              icon: Icons.star_rounded,
                              value: course.rating.toStringAsFixed(1),
                              label: 'Rating',
                              iconColor: AppTheme.warning,
                            ),
                          ],
                        ),
                      ),
                    ),
                    const SizedBox(height: 24),
                    // Modern progress tracker with an animated fill + milestone.
                    if (course.isEnrolled) ...[
                      _ProgressTracker(progress: course.progress),
                      const SizedBox(height: 16),
                      // Next lesson to resume (hidden once the course is done).
                      if (course.progress < 100)
                        Builder(builder: (context) {
                          final resume = _resumeLesson(course);
                          if (resume == null) return const SizedBox.shrink();
                          return Padding(
                            padding: const EdgeInsets.only(bottom: 16),
                            child: NextLessonCard(
                              lesson: resume.lesson,
                              lessonNumber: resume.number,
                              label: course.progress > 0
                                  ? 'Continue learning'
                                  : 'Start learning',
                              onTap: () {
                                setState(() {
                                  _activeLesson = resume.lesson;
                                });
                                _scrollController.animateTo(
                                  0.0,
                                  duration: const Duration(milliseconds: 300),
                                  curve: Curves.easeInOut,
                                );
                              },
                            ),
                          );
                        }),
                      if (course.progress >= 100)
                        Consumer(
                          builder: (context, ref, child) {
                            final certAsync = ref.watch(certificateForCourseProvider(int.parse(course.id)));
                            return certAsync.when(
                              data: (cert) {
                                if (cert == null) return const SizedBox.shrink();
                                return Container(
                                  padding: const EdgeInsets.all(12),
                                  decoration: BoxDecoration(
                                    color: isDark ? const Color(0xFF0F172A) : const Color(0xFFF0FDF4),
                                    borderRadius: BorderRadius.circular(12),
                                    border: Border.all(
                                      color: isDark ? const Color(0xFF1E293B) : const Color(0xFFDCFCE7),
                                    ),
                                  ),
                                  child: ListTile(
                                    contentPadding: EdgeInsets.zero,
                                    leading: const Icon(Icons.workspace_premium, color: Colors.amber, size: 36),
                                    title: const Text('Course Completed!'),
                                    subtitle: const Text('View your certificate'),
                                    trailing: const Icon(Icons.arrow_forward_ios, size: 14),
                                    onTap: () {
                                      showDialog(
                                        context: context,
                                        builder: (context) => AlertDialog(
                                          contentPadding: EdgeInsets.zero,
                                          content: CachedNetworkImage(
                                            imageUrl: cert.certificateUrl,
                                            placeholder: (context, url) => const Padding(
                                              padding: EdgeInsets.all(32.0),
                                              child: CircularProgressIndicator(),
                                            ),
                                          ),
                                          actions: [
                                            TextButton(
                                              onPressed: () => context.pop(),
                                              child: const Text('Close'),
                                            ),
                                          ],
                                        ),
                                      );
                                    },
                                  ),
                                );
                              },
                              loading: () => const Center(child: CircularProgressIndicator()),
                              error: (_, __) => const SizedBox.shrink(),
                            );
                          },
                        ),
                      const SizedBox(height: 24),
                    ],
                    // About Course
                    Text(
                      'About this course',
                      style: GoogleFonts.plusJakartaSans(
                        fontWeight: FontWeight.w800,
                        fontSize: 19,
                        letterSpacing: -0.3,
                      ),
                    ),
                    const SizedBox(height: 8),
                    Text(
                      course.description,
                      style: const TextStyle(height: 1.5),
                      textAlign: TextAlign.justify,
                    ),
                    
                    // Full Description
                    if (course.content != null && course.content!.isNotEmpty) ...[
                      const SizedBox(height: 24),
                      Text(
                        'Full Description',
                        style: GoogleFonts.plusJakartaSans(
                          fontWeight: FontWeight.bold,
                          fontSize: 18,
                        ),
                      ),
                      const SizedBox(height: 8),
                      Text(
                        course.content!,
                        style: const TextStyle(height: 1.5),
                        textAlign: TextAlign.justify,
                      ),
                    ],
                    const SizedBox(height: 32),

                    // Learning Outcomes (Benefits)
                    if (course.benefits.isNotEmpty) ...[
                      Text(
                        'What you\'ll learn',
                        style: GoogleFonts.plusJakartaSans(
                          fontWeight: FontWeight.bold,
                          fontSize: 18,
                        ),
                      ),
                      const SizedBox(height: 12),
                      ...course.benefits.map((benefit) => Padding(
                        padding: const EdgeInsets.only(bottom: 8.0),
                        child: Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const Icon(Icons.check, color: AppTheme.success, size: 18),
                            const SizedBox(width: 12),
                            Expanded(
                              child: Text(
                                benefit,
                                style: const TextStyle(height: 1.3),
                              ),
                            ),
                          ],
                        ),
                      )),
                      const SizedBox(height: 32),
                    ],

                    // Requirements
                    if (course.requirements.isNotEmpty) ...[
                      Text(
                        'Requirements',
                        style: GoogleFonts.plusJakartaSans(
                          fontWeight: FontWeight.bold,
                          fontSize: 18,
                        ),
                      ),
                      const SizedBox(height: 12),
                      ...course.requirements.map((req) => Padding(
                        padding: const EdgeInsets.only(bottom: 8.0),
                        child: Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const Icon(Icons.fiber_manual_record, color: Colors.grey, size: 10),
                            const SizedBox(width: 12),
                            Expanded(
                              child: Text(
                                req,
                                style: const TextStyle(height: 1.3),
                              ),
                            ),
                          ],
                        ),
                      )),
                      const SizedBox(height: 32),
                    ],
                    
                    // Target Audience
                    if (course.targetAudience.isNotEmpty) ...[
                      Text(
                        'Who this course is for',
                        style: GoogleFonts.plusJakartaSans(
                          fontWeight: FontWeight.bold,
                          fontSize: 18,
                        ),
                      ),
                      const SizedBox(height: 12),
                      ...course.targetAudience.map((audience) => Padding(
                        padding: const EdgeInsets.only(bottom: 8.0),
                        child: Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const Icon(Icons.person_search_outlined, color: Colors.blue, size: 18),
                            const SizedBox(width: 12),
                            Expanded(
                              child: Text(
                                audience,
                                style: const TextStyle(height: 1.3),
                              ),
                            ),
                          ],
                        ),
                      )),
                      const SizedBox(height: 32),
                    ],

                    // Material Includes
                    if (course.materialIncludes.isNotEmpty) ...[
                      Text(
                        'This course includes',
                        style: GoogleFonts.plusJakartaSans(
                          fontWeight: FontWeight.bold,
                          fontSize: 18,
                        ),
                      ),
                      const SizedBox(height: 12),
                      ...course.materialIncludes.map((material) => Padding(
                        padding: const EdgeInsets.only(bottom: 8.0),
                        child: Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const Icon(Icons.check_box_outlined, color: AppTheme.primary, size: 18),
                            const SizedBox(width: 12),
                            Expanded(
                              child: Text(
                                material,
                                style: const TextStyle(height: 1.3),
                              ),
                            ),
                          ],
                        ),
                      )),
                      const SizedBox(height: 32),
                    ],

                    // Tags
                    if (course.tags.isNotEmpty) ...[
                      Text(
                        'Tags',
                        style: GoogleFonts.plusJakartaSans(
                          fontWeight: FontWeight.bold,
                          fontSize: 18,
                        ),
                      ),
                      const SizedBox(height: 12),
                      Wrap(
                        spacing: 8,
                        runSpacing: 8,
                        children: course.tags.map((tag) => Container(
                          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                          decoration: BoxDecoration(
                            color: isDark ? const Color(0xFF1E293B) : const Color(0xFFF1F5F9),
                            borderRadius: BorderRadius.circular(20),
                            border: Border.all(
                              color: isDark ? const Color(0xFF334155) : const Color(0xFFE2E8F0),
                            ),
                          ),
                          child: Text(
                            tag,
                            style: TextStyle(
                              fontSize: 12,
                              color: isDark ? Colors.grey[300] : Colors.grey[700],
                            ),
                          ),
                        )).toList(),
                      ),
                      const SizedBox(height: 32),
                    ],

                    // Course Content Section (Curriculum)
                    if (course.lessons.isNotEmpty || course.quizzes.isNotEmpty || course.assignments.isNotEmpty) ...[
                      Text(
                        'Course Content',
                        style: GoogleFonts.plusJakartaSans(
                          fontWeight: FontWeight.bold,
                          fontSize: 18,
                        ),
                      ),
                      const SizedBox(height: 16),
                      // Lessons
                      ...course.lessons.asMap().entries.map((entry) {
                        final index = entry.key;
                        final lesson = entry.value;
                        return ListTile(
                          contentPadding: EdgeInsets.zero,
                          leading: CircleAvatar(
                            radius: 14,
                            backgroundColor: theme.colorScheme.primary.withOpacity(0.1),
                            child: Text('${index + 1}',
                                style: TextStyle(fontSize: 11, color: theme.colorScheme.primary)),
                          ),
                          title: Text(lesson.title, style: const TextStyle(fontSize: 13, fontWeight: FontWeight.bold)),
                          subtitle: Text('${lesson.duration ?? 0} mins', style: const TextStyle(fontSize: 11)),
                          trailing: Icon(
                            lesson.isPreview || course.isEnrolled ? Icons.play_circle_outline : Icons.lock_outline,
                            size: 18,
                            color: lesson.isPreview || course.isEnrolled ? AppTheme.primary : Colors.grey,
                          ),
                          onTap: lesson.isPreview || course.isEnrolled
                              ? () {
                                  setState(() {
                                    _activeLesson = lesson;
                                  });
                                  _scrollController.animateTo(
                                    0.0,
                                    duration: const Duration(milliseconds: 300),
                                    curve: Curves.easeInOut,
                                  );
                                }
                              : null,
                        );
                      }),
                      // Quizzes
                      ...course.quizzes.map((quiz) => ListTile(
                        contentPadding: EdgeInsets.zero,
                        leading: CircleAvatar(
                          radius: 14,
                          backgroundColor: theme.colorScheme.secondaryContainer,
                          child: Icon(Icons.quiz, color: theme.colorScheme.onSecondaryContainer, size: 14),
                        ),
                        title: Text(quiz.title, style: const TextStyle(fontSize: 13, fontWeight: FontWeight.bold)),
                        subtitle: Text('${quiz.questionsCount} Questions', style: const TextStyle(fontSize: 11)),
                        trailing: Icon(
                          course.isEnrolled ? Icons.arrow_forward_ios : Icons.lock_outline,
                          size: 14,
                          color: course.isEnrolled ? AppTheme.secondary : Colors.grey,
                        ),
                        onTap: course.isEnrolled ? () => context.push('/courses/${course.id}/quizzes/${quiz.id}') : null,
                      )),
                      // Assignments
                      ...course.assignments.map((assignment) => ListTile(
                        contentPadding: EdgeInsets.zero,
                        leading: CircleAvatar(
                          radius: 14,
                          backgroundColor: theme.colorScheme.tertiaryContainer,
                          child: Icon(Icons.assignment, color: theme.colorScheme.onTertiaryContainer, size: 14),
                        ),
                        title: Text(assignment.title, style: const TextStyle(fontSize: 13, fontWeight: FontWeight.bold)),
                        subtitle: Text('${assignment.totalPoints} Points', style: const TextStyle(fontSize: 11)),
                        trailing: Icon(
                          course.isEnrolled ? Icons.arrow_forward_ios : Icons.lock_outline,
                          size: 14,
                          color: course.isEnrolled ? Colors.indigo : Colors.grey,
                        ),
                        onTap: course.isEnrolled ? () => context.push('/assignment/${assignment.id}') : null,
                      )),
                    ],

                    // Instructor Details Section
                    const Divider(height: 48),
                    Text(
                      'Instructor Details',
                      style: GoogleFonts.plusJakartaSans(
                        fontWeight: FontWeight.w800,
                        fontSize: 19,
                        letterSpacing: -0.3,
                      ),
                    ),
                    const SizedBox(height: 16),
                    Row(
                      children: [
                        CircleAvatar(
                          radius: 40,
                          backgroundColor: AppTheme.primary.withOpacity(0.1),
                          backgroundImage: course.instructor.avatar.startsWith('http')
                              ? CachedNetworkImageProvider(course.instructor.avatar)
                              : CachedNetworkImageProvider(
                                  '${AppConfig.baseUrl}${course.instructor.avatar}'),
                          onBackgroundImageError: (_, __) {},
                        ),
                        const SizedBox(width: 16),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                course.instructor.name,
                                style: GoogleFonts.plusJakartaSans(
                                  fontWeight: FontWeight.bold,
                                  fontSize: 16,
                                ),
                              ),
                              const SizedBox(height: 4),
                              Text(
                                'Expert Instructor',
                                style: theme.textTheme.bodyMedium?.copyWith(
                                  color: theme.textTheme.bodyMedium?.color?.withOpacity(0.6),
                                ),
                              ),
                            ],
                          ),
                        ),
                        OutlinedButton(
                          onPressed: () {
                            // Show instructor profile in a bottom sheet or navigate
                            _showInstructorProfile(context, course.instructor);
                          },
                          style: OutlinedButton.styleFrom(
                            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 0),
                            visualDensity: VisualDensity.compact,
                          ),
                          child: const Text('View Profile', style: TextStyle(fontSize: 12)),
                        ),
                      ],
                    ),

                    // Reviews & Ratings Section
                    const Divider(height: 48),
                    Text(
                      'Reviews & Ratings',
                      style: GoogleFonts.plusJakartaSans(
                        fontWeight: FontWeight.w800,
                        fontSize: 19,
                        letterSpacing: -0.3,
                      ),
                    ),
                    const SizedBox(height: 16),
                    Consumer(
                      builder: (context, ref, child) {
                        final reviewsAsync = ref.watch(courseReviewsProvider(course.id));
                        return reviewsAsync.when(
                          data: (data) {
                            final List<dynamic> reviews = data['reviews'] ?? [];
                            final avgRating = (data['average_rating'] as num?)?.toDouble() ?? 0.0;
                            final totalReviews = data['total_reviews'] ?? 0;

                            return Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Row(
                                  children: [
                                    Text(
                                      avgRating.toStringAsFixed(1),
                                      style: GoogleFonts.plusJakartaSans(
                                        fontSize: 48,
                                        fontWeight: FontWeight.bold,
                                        color: AppTheme.primary,
                                      ),
                                    ),
                                    const SizedBox(width: 16),
                                    Column(
                                      crossAxisAlignment: CrossAxisAlignment.start,
                                      children: [
                                        Row(
                                          children: List.generate(5, (index) {
                                            return Icon(
                                              index < avgRating.round() ? Icons.star : Icons.star_border,
                                              color: Colors.amber,
                                              size: 20,
                                            );
                                          }),
                                        ),
                                        const SizedBox(height: 4),
                                        Text(
                                          '$totalReviews ratings',
                                          style: theme.textTheme.bodyMedium?.copyWith(
                                            color: Colors.grey,
                                          ),
                                        ),
                                      ],
                                    ),
                                  ],
                                ),
                                const SizedBox(height: 24),
                                if (reviews.isEmpty)
                                  Text(
                                    'No reviews yet. Be the first to review this course!',
                                    style: theme.textTheme.bodyMedium?.copyWith(
                                      color: Colors.grey,
                                      fontStyle: FontStyle.italic,
                                    ),
                                  )
                                else
                                  ListView.builder(
                                    shrinkWrap: true,
                                    physics: const NeverScrollableScrollPhysics(),
                                    itemCount: reviews.length,
                                    itemBuilder: (context, index) {
                                      final review = reviews[index] as Map<String, dynamic>;
                                      final reviewerName = review['user_display_name'] ?? 'Anonymous';
                                      final reviewTitle = review['review_title'] ?? '';
                                      final reviewContent = review['review_content'] ?? '';
                                      final rating = (review['rating'] as num?)?.toDouble() ?? 5.0;

                                      return Container(
                                        margin: const EdgeInsets.only(bottom: 16),
                                        padding: const EdgeInsets.all(12),
                                        decoration: BoxDecoration(
                                          color: isDark ? const Color(0xFF1E293B) : const Color(0xFFF8FAFC),
                                          borderRadius: BorderRadius.circular(12),
                                          border: Border.all(
                                            color: isDark ? const Color(0xFF334155) : const Color(0xFFE2E8F0),
                                          ),
                                        ),
                                        child: Column(
                                          crossAxisAlignment: CrossAxisAlignment.start,
                                          children: [
                                            Row(
                                              mainAxisAlignment: MainAxisAlignment.spaceBetween,
                                              children: [
                                                Text(
                                                  reviewerName,
                                                  style: const TextStyle(
                                                    fontWeight: FontWeight.bold,
                                                  ),
                                                ),
                                                Row(
                                                  children: List.generate(5, (starIdx) {
                                                    return Icon(
                                                      starIdx < rating.round() ? Icons.star : Icons.star_border,
                                                      color: Colors.amber,
                                                      size: 14,
                                                    );
                                                  }),
                                                ),
                                              ],
                                            ),
                                            if (reviewTitle.isNotEmpty) ...[
                                              const SizedBox(height: 6),
                                              Text(
                                                reviewTitle,
                                                style: const TextStyle(
                                                  fontWeight: FontWeight.bold,
                                                  fontSize: 13,
                                                ),
                                              ),
                                            ],
                                            const SizedBox(height: 4),
                                            Text(
                                              reviewContent,
                                              style: TextStyle(
                                                fontSize: 12,
                                                color: isDark ? Colors.grey[350] : Colors.grey[700],
                                              ),
                                            ),
                                          ],
                                        ),
                                      );
                                    },
                                  ),
                              ],
                            );
                          },
                          loading: () => const Center(
                            child: Padding(
                              padding: EdgeInsets.all(16.0),
                              child: CircularProgressIndicator(),
                            ),
                          ),
                          error: (err, stack) => Text(
                            'Could not load reviews: $err',
                            style: const TextStyle(color: Colors.red),
                          ),
                        );
                      },
                    ),
                    const SizedBox(height: 32),
                  ],
                ),
              ),
            ],
          ),
        );
      },
      loading: () => const BrandedLoader(),
        error: (error, stack) => ErrorDisplay(
          message: error.toString(),
          onRetry: () => ref.refresh(courseByIdProvider(widget.courseId)),
        ),
      ),
      bottomNavigationBar: courseAsync.when(
        data: (course) => Container(
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
          decoration: BoxDecoration(
            color: isDark ? AppTheme.backgroundDark : Colors.white,
            border: Border(
              top: BorderSide(
                color: isDark ? AppTheme.borderDark : AppTheme.borderLight,
              ),
            ),
          ),
          child: SafeArea(
            child: Row(
              children: [
                Expanded(
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      if (course.salePrice != null && course.salePrice! < course.price)
                        Text(
                          '₹${course.price.toStringAsFixed(0)}',
                          style: theme.textTheme.bodyMedium?.copyWith(
                            decoration: TextDecoration.lineThrough,
                            color: Colors.grey,
                          ),
                        ),
                      Text(
                        course.price == 0 ? 'FREE' : '₹${(course.salePrice ?? course.price).toStringAsFixed(0)}',
                        style: GoogleFonts.plusJakartaSans(
                          color: theme.colorScheme.primary,
                          fontWeight: FontWeight.bold,
                          fontSize: 20,
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(width: 16),
                Expanded(
                  flex: 2,
                  child: AppButton(
                    text: course.isEnrolled ? 'Continue learning' : 'Enroll now',
                    size: ButtonSize.large,
                    isFullWidth: true,
                    onPressed: () {
                      if (course.isEnrolled) {
                        _continueLearning(course);
                      } else {
                        _startCheckoutFlow(course);
                      }
                    },
                  ),
                ),
              ],
            ),
          ),
        ),
        loading: () => const SizedBox.shrink(),
        error: (_, __) => const SizedBox.shrink(),
      ),
    );
  }
}

/// Compact integer formatting for large counts (1.2k, 3.4M).
String _compact(int n) {
  if (n >= 1000000) return '${(n / 1000000).toStringAsFixed(1)}M';
  if (n >= 1000) return '${(n / 1000).toStringAsFixed(1)}k';
  return '$n';
}

/// Thin vertical divider between metric cells in the mini info card.
Widget _cellDivider(bool isDark) => Container(
      width: 1,
      margin: const EdgeInsets.symmetric(vertical: 4),
      color: isDark ? AppTheme.borderDark : AppTheme.borderLight,
    );

class _MetricCell extends StatelessWidget {
  final IconData icon;
  final String value;
  final String label;
  final Color? iconColor;

  const _MetricCell({
    required this.icon,
    required this.value,
    required this.label,
    this.iconColor,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;
    final muted = isDark ? AppTheme.mutedDark : AppTheme.mutedLight;
    return Expanded(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 22, color: iconColor ?? theme.colorScheme.primary),
          const SizedBox(height: 8),
          Text(
            value,
            style: theme.textTheme.titleMedium?.copyWith(
              fontWeight: FontWeight.w700,
            ),
          ),
          const SizedBox(height: 2),
          Text(
            label,
            style: theme.textTheme.labelSmall?.copyWith(color: muted),
          ),
        ],
      ),
    );
  }
}

/// Modern progress tracker — a big animated percentage, an animated rounded
/// fill, and a contextual milestone label.
class _ProgressTracker extends StatelessWidget {
  final double progress; // 0..100

  const _ProgressTracker({required this.progress});

  String get _milestone {
    if (progress >= 100) return 'Course complete — well done!';
    if (progress >= 75) return 'Almost there — keep going';
    if (progress >= 40) return 'Great momentum';
    if (progress > 0) return 'Just getting started';
    return 'Begin your first lesson';
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;
    final muted = isDark ? AppTheme.mutedDark : AppTheme.mutedLight;
    return Container(
      padding: const EdgeInsets.all(AppSpacing.card),
      decoration: BoxDecoration(
        color: isDark ? AppTheme.surfaceDark : Colors.white,
        borderRadius: BorderRadius.circular(AppRadius.lg),
        border: Border.all(
          color: isDark ? AppTheme.borderDark : AppTheme.borderLight,
        ),
        boxShadow: isDark ? null : AppShadows.soft,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Your progress',
                      style: theme.textTheme.titleSmall?.copyWith(
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                    const SizedBox(height: 2),
                    Text(_milestone,
                        style: theme.textTheme.bodySmall?.copyWith(color: muted)),
                  ],
                ),
              ),
              Text(
                '${progress.toInt()}%',
                style: theme.textTheme.headlineSmall?.copyWith(
                  color: theme.colorScheme.primary,
                  fontWeight: FontWeight.w700,
                ),
              ),
            ],
          ),
          const SizedBox(height: 14),
          ClipRRect(
            borderRadius: BorderRadius.circular(AppRadius.pill),
            child: TweenAnimationBuilder<double>(
              tween: Tween(begin: 0, end: (progress / 100).clamp(0.0, 1.0)),
              duration: const Duration(milliseconds: 700),
              curve: Curves.easeOutCubic,
              builder: (context, value, _) => LinearProgressIndicator(
                value: value,
                minHeight: 10,
                backgroundColor:
                    isDark ? AppNeutrals.slate800 : AppNeutrals.slate100,
                valueColor:
                    AlwaysStoppedAnimation(theme.colorScheme.primary),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
