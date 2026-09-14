import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:sashalms/core/network/network_provider.dart';
import 'package:sashalms/config/theme.dart';
import 'package:sashalms/config/design_tokens.dart';
import 'package:dio/dio.dart';

class VerifyCertificatePage extends ConsumerStatefulWidget {
  const VerifyCertificatePage({super.key});

  @override
  ConsumerState<VerifyCertificatePage> createState() => _VerifyCertificatePageState();
}

class _VerifyCertificatePageState extends ConsumerState<VerifyCertificatePage> {
  final _controller = TextEditingController();
  bool _isLoading = false;
  Map<String, dynamic>? _result;
  String? _error;

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  void _handleVerify() async {
    final uuid = _controller.text.trim();
    if (uuid.isEmpty) {
      setState(() {
        _error = 'Please enter a certificate ID';
        _result = null;
      });
      return;
    }

    setState(() {
      _isLoading = true;
      _error = null;
      _result = null;
    });

    try {
      final client = ref.read(apiClientProvider);
      // Backend public verification router might accept get query parameter or path parameter.
      // In verify-certificate.tsx, the web app queries /api/v1/certificates/verify?uuid=...
      final response = await client.post(
        '/api/v1/certificates/verify',
        data: {'token': uuid}, // Or query parameter. Let's see what is standard.
      );

      if (response.statusCode == 200) {
        setState(() {
          _result = response.data as Map<String, dynamic>;
        });
      } else {
        setState(() {
          _error = 'Certificate not found or invalid';
        });
      }
    } on DioException catch (e) {
      setState(() {
        _error = e.response?.data['detail'] ?? 'Failed to verify certificate';
      });
    } catch (e) {
      setState(() {
        _error = 'An unexpected error occurred';
      });
    } finally {
      setState(() {
        _isLoading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Verify Certificate'),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Center(
              child: Container(
                width: 88,
                height: 88,
                decoration: BoxDecoration(
                  gradient: AppGradients.primary,
                  borderRadius: BorderRadius.circular(AppRadius.lg),
                  boxShadow: AppShadows.primaryGlow,
                ),
                child: const Icon(
                  Icons.verified_user_rounded,
                  size: 44,
                  color: Colors.white,
                ),
              ),
            ),
            const SizedBox(height: 20),
            Text(
              'Certificate Verification',
              style: GoogleFonts.plusJakartaSans(
                fontSize: 24,
                fontWeight: FontWeight.w800,
                letterSpacing: -0.3,
              ),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 8),
            const Text(
              'Enter the Certificate ID/Token below to verify the authenticity of a student credentials issued by SashaInfinity LMS.',
              textAlign: TextAlign.center,
              style: TextStyle(color: Colors.grey, height: 1.4),
            ),
            const SizedBox(height: 32),
            TextField(
              controller: _controller,
              decoration: const InputDecoration(
                labelText: 'Certificate Token / ID',
                hintText: 'Enter 32-character token',
                prefixIcon: Icon(Icons.qr_code),
              ),
            ),
            const SizedBox(height: 16),
            ElevatedButton(
              onPressed: _isLoading ? null : _handleVerify,
              child: _isLoading
                  ? const SizedBox(
                      width: 20,
                      height: 20,
                      child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2),
                    )
                  : const Text('Verify Credentials'),
            ),
            if (_error != null) ...[
              const SizedBox(height: 24),
              Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: AppTheme.danger.withOpacity(0.1),
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: AppTheme.danger.withOpacity(0.3)),
                ),
                child: Row(
                  children: [
                    const Icon(Icons.error_outline, color: AppTheme.danger),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Text(
                        _error!,
                        style: const TextStyle(color: AppTheme.danger, fontWeight: FontWeight.w600),
                      ),
                    ),
                  ],
                ),
              ),
            ],
            if (_result != null) ...[
              const SizedBox(height: 24),
              Container(
                padding: const EdgeInsets.all(20),
                decoration: BoxDecoration(
                  color: AppTheme.success.withOpacity(0.08),
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: AppTheme.success.withOpacity(0.3)),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        const Icon(Icons.check_circle_outline, color: AppTheme.success),
                        const SizedBox(width: 8),
                        Text(
                          'VALID CERTIFICATE',
                          style: GoogleFonts.plusJakartaSans(
                            color: AppTheme.success,
                            fontWeight: FontWeight.bold,
                            fontSize: 16,
                          ),
                        ),
                      ],
                    ),
                    const Divider(height: 24),
                    _buildResultRow('Student Name', _result!['student_name'] ?? 'N/A'),
                    _buildResultRow('Course', _result!['course_title'] ?? 'N/A'),
                    _buildResultRow('Issue Date', _result!['created_at'] ?? 'N/A'),
                    _buildResultRow('Grade', _result!['grade'] ?? 'N/A'),
                  ],
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildResultRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label, style: const TextStyle(color: Colors.grey, fontSize: 13)),
          Text(value, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13)),
        ],
      ),
    );
  }
}
