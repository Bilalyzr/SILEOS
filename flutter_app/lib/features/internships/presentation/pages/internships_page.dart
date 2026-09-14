import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:sashalms/core/network/network_provider.dart';
import 'package:sashalms/config/theme.dart';
import 'package:sashalms/config/design_tokens.dart';
import 'package:sashalms/shared/widgets/common/app_loader.dart';
import 'package:sashalms/shared/widgets/common/error_display.dart';
import 'package:sashalms/shared/widgets/common/launching_soon.dart';
import 'package:sashalms/shared/widgets/common/skeleton_loader.dart';
import 'internship_detail_page.dart';

final publicInternshipsProvider = FutureProvider<List<dynamic>>((ref) async {
  final client = ref.watch(apiClientProvider);
  final response = await client.get('/api/v1/internships');
  if (response.statusCode == 200) {
    return response.data as List<dynamic>;
  } else {
    throw Exception('Failed to load internships');
  }
});

class InternshipsPage extends ConsumerWidget {
  const InternshipsPage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final internshipsAsync = ref.watch(publicInternshipsProvider);
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Internships Portal'),
      ),
      body: internshipsAsync.when(
        data: (internships) {
          if (internships.isEmpty) {
            return const LaunchingSoonWidget();
          }

          return ListView.builder(
            padding: const EdgeInsets.all(24),
            itemCount: internships.length,
            itemBuilder: (context, index) {
              final item = internships[index] as Map<String, dynamic>;
              return _buildInternshipCard(context, item, theme, isDark);
            },
          );
        },
        loading: () => const SkeletonList(itemCount: 2),
        error: (err, stack) => ErrorDisplay(
          message: err.toString(),
          onRetry: () => ref.refresh(publicInternshipsProvider),
        ),
      ),
    );
  }

  Widget _buildInternshipCard(
    BuildContext context,
    Map<String, dynamic> item,
    ThemeData theme,
    bool isDark,
  ) {
    final coverImage = item['cover_image'] as String?;
    final title = item['title'] ?? 'Untitled';
    final spoc = item['spoc_name'] ?? '';
    final price = item['price'] ?? 0.0;
    final slug = item['slug'] ?? '';

    return Container(
      margin: const EdgeInsets.only(bottom: 16),
      decoration: BoxDecoration(
        color: isDark ? AppTheme.surfaceDark : Colors.white,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: isDark ? const Color(0xFF273449) : const Color(0xFFEEF2F6)),
        boxShadow: isDark ? null : AppShadows.card,
      ),
      clipBehavior: Clip.antiAlias,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          if (coverImage != null && coverImage.isNotEmpty)
            ClipRRect(
              borderRadius: const BorderRadius.only(
                topLeft: Radius.circular(20),
                topRight: Radius.circular(20),
              ),
              child: Image.network(
                coverImage,
                height: 140,
                width: double.infinity,
                fit: BoxFit.cover,
                errorBuilder: (_, __, ___) => Container(
                  height: 140,
                  color: AppTheme.secondary.withOpacity(0.1),
                  child: const Icon(Icons.work_outline, size: 40, color: AppTheme.primary),
                ),
              ),
            ),
          Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: GoogleFonts.plusJakartaSans(
                    fontSize: 18,
                    fontWeight: FontWeight.w800,
                    letterSpacing: -0.3,
                  ),
                ),
                const SizedBox(height: 8),
                Row(
                  children: [
                    const Icon(Icons.person_outline, size: 16, color: AppTheme.primary),
                    const SizedBox(width: 6),
                    Text(
                      'SPOC: $spoc',
                      style: theme.textTheme.bodyMedium?.copyWith(fontSize: 12),
                    ),
                  ],
                ),
                const SizedBox(height: 16),
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text(
                      price > 0 ? '₹${price.toStringAsFixed(0)}' : 'Free',
                      style: GoogleFonts.plusJakartaSans(
                        fontSize: 18,
                        fontWeight: FontWeight.w700,
                        color: AppTheme.primary,
                      ),
                    ),
                    ElevatedButton(
                      style: ElevatedButton.styleFrom(
                        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                      ),
                      onPressed: () {
                        Navigator.push(
                          context,
                          MaterialPageRoute(
                            builder: (context) => InternshipDetailPage(slug: slug),
                          ),
                        );
                      },
                      child: const Text('View Details'),
                    ),
                  ],
                ),
              ],
            ),
          )
        ],
      ),
    );
  }
}
