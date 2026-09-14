import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:razorpay_flutter/razorpay_flutter.dart';
import 'package:sashalms/core/network/network_provider.dart';
import 'package:sashalms/config/theme.dart';
import 'package:sashalms/config/design_tokens.dart';
import 'package:sashalms/shared/widgets/common/app_loader.dart';
import 'package:sashalms/shared/widgets/common/error_display.dart';
import 'package:sashalms/shared/widgets/common/app_snackbar.dart';
import 'package:sashalms/features/auth/presentation/providers/auth_provider.dart';

final internshipDetailProvider = FutureProvider.family<Map<String, dynamic>, String>((ref, slug) async {
  final client = ref.watch(apiClientProvider);
  final response = await client.get('/api/v1/internships/$slug');
  if (response.statusCode == 200) {
    return response.data as Map<String, dynamic>;
  } else {
    throw Exception('Failed to load internship details');
  }
});

class InternshipDetailPage extends ConsumerStatefulWidget {
  final String slug;

  const InternshipDetailPage({super.key, required this.slug});

  @override
  ConsumerState<InternshipDetailPage> createState() => _InternshipDetailPageState();
}

class _InternshipDetailPageState extends ConsumerState<InternshipDetailPage> {
  late Razorpay _razorpay;
  bool _isProcessing = false;
  int? _currentInternshipId;

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
    super.dispose();
  }

  void _handlePaymentSuccess(PaymentSuccessResponse response) async {
    if (!mounted || _currentInternshipId == null) return;
    setState(() {
      _isProcessing = true;
    });

    try {
      final client = ref.read(apiClientProvider);
      final verifyResponse = await client.post(
        '/api/v1/internships/purchase/verify',
        data: {
          'razorpay_order_id': response.orderId,
          'razorpay_payment_id': response.paymentId,
          'razorpay_signature': response.signature,
          'internship_id': _currentInternshipId,
        },
      );

      if (!mounted) return;
      setState(() {
        _isProcessing = false;
      });

      if (verifyResponse.statusCode == 200) {
        AppSnackbar.success(context, 'Successfully applied and enrolled in internship!');
        ref.invalidate(internshipDetailProvider(widget.slug));
      } else {
        AppSnackbar.error(context, 'Payment verification failed: ${verifyResponse.data['detail'] ?? 'Unknown error'}');
      }
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _isProcessing = false;
      });
      AppSnackbar.error(context, 'Verification error: ${e.toString()}');
    }
  }

  void _handlePaymentError(PaymentFailureResponse response) {
    if (!mounted) return;
    setState(() {
      _isProcessing = false;
    });
    final msg = response.message ?? 'Payment failed';
    AppSnackbar.error(context, msg);
  }

  void _handleExternalWallet(ExternalWalletResponse response) {
    // Optional external wallet handler
  }

  Future<void> _startPurchase(int internshipId, double price, String title) async {
    final authState = ref.read(authProvider);
    final user = authState.maybeWhen(authenticated: (u) => u, orElse: () => null);

    if (user == null) {
      AppSnackbar.error(context, 'Please log in to apply for internships.');
      return;
    }

    setState(() {
      _isProcessing = true;
      _currentInternshipId = internshipId;
    });

    try {
      final client = ref.read(apiClientProvider);
      final response = await client.post('/api/v1/internships/$internshipId/purchase');

      if (!mounted) return;
      if (response.statusCode == 200) {
        final orderData = response.data as Map<String, dynamic>;
        final options = {
          'key': orderData['key_id'],
          'amount': orderData['amount'],
          'name': 'SashaInfinity LMS',
          'description': 'Internship: $title',
          'order_id': orderData['order_id'],
          'prefill': {
            'name': user.fullName,
            'email': user.email,
            if (user.phone != null) 'contact': user.phone,
          },
          'theme': {'color': '#f97316'}
        };
        _razorpay.open(options);
      } else {
        setState(() {
          _isProcessing = false;
        });
        AppSnackbar.error(context, 'Failed to create order: ${response.data['detail'] ?? 'Unknown error'}');
      }
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _isProcessing = false;
      });
      AppSnackbar.error(context, 'Failed to initiate purchase: ${e.toString()}');
    }
  }

  @override
  Widget build(BuildContext context) {
    final detailAsync = ref.watch(internshipDetailProvider(widget.slug));
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Internship Details'),
      ),
      body: Stack(
        children: [
          detailAsync.when(
            data: (data) {
              final id = data['id'] as int;
              final title = data['title'] ?? 'Untitled';
              final description = data['description'] ?? 'No description provided.';
              final coverImage = data['cover_image'] as String?;
              final price = data['price'] ?? 0.0;
              final spoc = data['spoc_name'] ?? 'Admin';

              return SingleChildScrollView(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    if (coverImage != null && coverImage.isNotEmpty)
                      Image.network(
                        coverImage,
                        height: 200,
                        width: double.infinity,
                        fit: BoxFit.cover,
                        errorBuilder: (_, __, ___) => Container(
                          height: 200,
                          color: AppTheme.secondary.withOpacity(0.1),
                          child: const Icon(Icons.work_outline, size: 60, color: AppTheme.primary),
                        ),
                      ),
                    Padding(
                      padding: const EdgeInsets.all(24),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            title,
                            style: GoogleFonts.plusJakartaSans(
                              fontSize: 26,
                              fontWeight: FontWeight.w800,
                              letterSpacing: -0.5,
                            ),
                          ),
                          const SizedBox(height: 12),
                          Row(
                            children: [
                              const Icon(Icons.person_outline, size: 18, color: AppTheme.primary),
                              const SizedBox(width: 8),
                              Text(
                                'Coordinator (SPOC): $spoc',
                                style: theme.textTheme.titleSmall,
                              ),
                            ],
                          ),
                          const Divider(height: 32),
                          Text(
                            'About the Program',
                            style: GoogleFonts.plusJakartaSans(
                              fontSize: 18,
                              fontWeight: FontWeight.bold,
                              color: AppTheme.primary,
                            ),
                          ),
                          const SizedBox(height: 8),
                          Text(
                            description,
                            style: theme.textTheme.bodyLarge?.copyWith(height: 1.5),
                          ),
                          const SizedBox(height: 40),
                          Container(
                            padding: const EdgeInsets.all(16),
                            decoration: BoxDecoration(
                              color: isDark ? AppTheme.surfaceDark : Colors.white,
                              borderRadius: BorderRadius.circular(18),
                              border: Border.all(color: isDark ? const Color(0xFF273449) : const Color(0xFFEEF2F6)),
                              boxShadow: isDark ? null : AppShadows.card,
                            ),
                            child: Row(
                              mainAxisAlignment: MainAxisAlignment.spaceBetween,
                              children: [
                                Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    const Text('Program Fee', style: TextStyle(fontSize: 12, color: Colors.grey)),
                                    const SizedBox(height: 4),
                                    Text(
                                      price > 0 ? '₹${price.toStringAsFixed(0)}' : 'Free',
                                      style: GoogleFonts.plusJakartaSans(
                                        fontSize: 20,
                                        fontWeight: FontWeight.bold,
                                        color: AppTheme.primary,
                                      ),
                                    ),
                                  ],
                                ),
                                ElevatedButton(
                                  onPressed: _isProcessing
                                      ? null
                                      : () => _startPurchase(id, price, title),
                                  child: const Text('Apply Now'),
                                ),
                              ],
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              );
            },
            loading: () => const BrandedLoader(),
            error: (err, stack) => ErrorDisplay(
              message: err.toString(),
              onRetry: () => ref.refresh(internshipDetailProvider(widget.slug)),
            ),
          ),
          if (_isProcessing)
            Positioned.fill(
              child: Container(
                color: Colors.black26,
                child: const Center(
                  child: CircularProgressIndicator(),
                ),
              ),
            ),
        ],
      ),
    );
  }
}
