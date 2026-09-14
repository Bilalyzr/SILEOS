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
import 'blog_detail_page.dart';

final publicBlogsProvider = FutureProvider<List<dynamic>>((ref) async {
  final client = ref.watch(apiClientProvider);
  final response = await client.get('/api/v1/blog');
  if (response.statusCode == 200) {
    return response.data as List<dynamic>;
  } else {
    throw Exception('Failed to load blogs');
  }
});

class BlogListPage extends ConsumerWidget {
  const BlogListPage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final blogsAsync = ref.watch(publicBlogsProvider);
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Latest News & Blog'),
      ),
      body: blogsAsync.when(
        data: (blogs) {
          if (blogs.isEmpty) {
            return const LaunchingSoonWidget();
          }

          return ListView.builder(
            padding: const EdgeInsets.all(24),
            itemCount: blogs.length,
            itemBuilder: (context, index) {
              final post = blogs[index] as Map<String, dynamic>;
              return _buildBlogCard(context, post, theme, isDark);
            },
          );
        },
        loading: () => const SkeletonList(itemCount: 2),
        error: (err, stack) => ErrorDisplay(
          message: err.toString(),
          onRetry: () => ref.refresh(publicBlogsProvider),
        ),
      ),
    );
  }

  Widget _buildBlogCard(
    BuildContext context,
    Map<String, dynamic> post,
    ThemeData theme,
    bool isDark,
  ) {
    final title = post['title'] ?? 'Untitled';
    final excerpt = post['excerpt'] ?? '';
    final coverImage = post['featured_image'] as String?;
    final date = post['created_at'] ?? '';
    final slug = post['slug'] ?? '';

    return Container(
      margin: const EdgeInsets.only(bottom: 16),
      decoration: BoxDecoration(
        color: isDark ? AppTheme.surfaceDark : Colors.white,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: isDark ? const Color(0xFF273449) : const Color(0xFFEEF2F6)),
        boxShadow: isDark ? null : AppShadows.card,
      ),
      clipBehavior: Clip.antiAlias,
      child: InkWell(
        onTap: () {
          Navigator.push(
            context,
            MaterialPageRoute(
              builder: (context) => BlogDetailPage(slug: slug),
            ),
          );
        },
        borderRadius: BorderRadius.circular(20),
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
                  height: 150,
                  width: double.infinity,
                  fit: BoxFit.cover,
                  errorBuilder: (_, __, ___) => Container(
                    height: 150,
                    color: AppTheme.primary.withOpacity(0.1),
                    child: const Icon(Icons.image, color: AppTheme.primary),
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
                  if (excerpt.isNotEmpty)
                    Text(
                      excerpt,
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      style: theme.textTheme.bodyMedium?.copyWith(
                        color: theme.textTheme.bodyMedium?.color?.withOpacity(0.7),
                      ),
                    ),
                  const SizedBox(height: 12),
                  Text(
                    date,
                    style: theme.textTheme.bodySmall?.copyWith(color: Colors.grey),
                  ),
                ],
              ),
            )
          ],
        ),
      ),
    );
  }
}
