import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_widget_from_html/flutter_widget_from_html.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:intl/intl.dart';
import 'package:url_launcher/url_launcher.dart';
import 'package:share_plus/share_plus.dart';
import 'package:sashalms/core/network/network_provider.dart';
import 'package:sashalms/config/theme.dart';
import 'package:sashalms/shared/widgets/common/app_loader.dart';
import 'package:sashalms/shared/widgets/common/error_display.dart';

final blogDetailProvider =
    FutureProvider.family<Map<String, dynamic>, String>((ref, slug) async {
  final client = ref.watch(apiClientProvider);
  final response = await client.get('/api/v1/blog/$slug');
  if (response.statusCode == 200) {
    return response.data as Map<String, dynamic>;
  } else {
    throw Exception('Failed to load blog details');
  }
});

class BlogDetailPage extends ConsumerWidget {
  final String slug;

  const BlogDetailPage({super.key, required this.slug});

  /// Formats an ISO date string to e.g. "June 29, 2026"; falls back to the raw
  /// string if it can't be parsed.
  String _formatDate(String raw) {
    if (raw.isEmpty) return '';
    final parsed = DateTime.tryParse(raw);
    if (parsed == null) return raw;
    return DateFormat('MMMM d, y').format(parsed.toLocal());
  }

  /// Rough reading-time estimate from the plain-text length of the HTML body.
  int _readingMinutes(String html) {
    final text = html.replaceAll(RegExp(r'<[^>]*>'), ' ');
    final words = text.trim().split(RegExp(r'\s+')).where((w) => w.isNotEmpty);
    return (words.length / 200).ceil().clamp(1, 99);
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final detailAsync = ref.watch(blogDetailProvider(slug));
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Read Article'),
        actions: [
          IconButton(
            icon: const Icon(Icons.share_outlined),
            tooltip: 'Share Article',
            onPressed: () {
              final shareUrl = 'https://www.sashainfinity.com/blog/$slug';
              Share.share(
                'Check out this article on SashaInfinity:\n$shareUrl',
                subject: 'SashaInfinity Article',
              );
            },
          ),
        ],
      ),
      body: detailAsync.when(
        data: (data) {
          final title = (data['title'] ?? 'Untitled').toString();
          var content = (data['content'] ?? '').toString();
          // If the content is plain text, format newlines to paragraphs
          if (!content.contains('<p>') && !content.contains('</div>') && !content.contains('<br>')) {
            content = content
                .split('\n')
                .map((p) => p.trim().isEmpty ? '' : '<p>$p</p>')
                .join('');
          }
          final coverImage = data['featured_image'] as String?;
          final date = _formatDate((data['created_at'] ?? '').toString());
          final author = (data['author_name'] ?? 'SashaInfinity').toString();
          final category = (data['category'] ?? '').toString();
          final minutes = _readingMinutes(content);

          return SingleChildScrollView(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                if (coverImage != null && coverImage.isNotEmpty)
                  Image.network(
                    coverImage,
                    height: 220,
                    width: double.infinity,
                    fit: BoxFit.cover,
                    errorBuilder: (_, __, ___) => Container(
                      height: 220,
                      color: AppTheme.primary.withValues(alpha: 0.1),
                      child: const Icon(Icons.image,
                          size: 50, color: AppTheme.primary),
                    ),
                  ),
                Padding(
                  padding: const EdgeInsets.fromLTRB(24, 24, 24, 40),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      if (category.isNotEmpty) ...[
                        Container(
                          padding: const EdgeInsets.symmetric(
                              horizontal: 12, vertical: 6),
                          decoration: BoxDecoration(
                            color: AppTheme.primary.withValues(alpha: 0.12),
                            borderRadius: BorderRadius.circular(999),
                          ),
                          child: Text(
                            category.toUpperCase(),
                            style: GoogleFonts.inter(
                              fontSize: 11,
                              fontWeight: FontWeight.w700,
                              letterSpacing: 0.6,
                              color: AppTheme.primaryDark,
                            ),
                          ),
                        ),
                        const SizedBox(height: 16),
                      ],
                      Text(
                        title,
                        style: GoogleFonts.plusJakartaSans(
                          fontSize: 28,
                          fontWeight: FontWeight.w800,
                          letterSpacing: -0.5,
                          height: 1.2,
                        ),
                      ),
                      const SizedBox(height: 16),
                      // Author + date + reading time meta row.
                      Row(
                        children: [
                          CircleAvatar(
                            radius: 16,
                            backgroundColor:
                                AppTheme.primary.withValues(alpha: 0.15),
                            child: Text(
                              author.isNotEmpty ? author[0].toUpperCase() : 'S',
                              style: GoogleFonts.plusJakartaSans(
                                color: AppTheme.primaryDark,
                                fontWeight: FontWeight.w700,
                                fontSize: 14,
                              ),
                            ),
                          ),
                          const SizedBox(width: 10),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  author,
                                  style: GoogleFonts.inter(
                                    fontSize: 13.5,
                                    fontWeight: FontWeight.w600,
                                  ),
                                ),
                                Text(
                                  [
                                    if (date.isNotEmpty) date,
                                    '$minutes min read',
                                  ].join('  ·  '),
                                  style: GoogleFonts.inter(
                                    fontSize: 12,
                                    color: theme.colorScheme.onSurface
                                        .withValues(alpha: 0.55),
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ],
                      ),
                      const Divider(height: 40),
                      // Rendered, structured article body (HTML from the editor).
                      _ArticleBody(html: content, isDark: isDark),
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
          onRetry: () => ref.refresh(blogDetailProvider(slug)),
        ),
      ),
    );
  }
}

/// Renders the article's HTML body with reader-friendly typography: comfortable
/// line height, clear heading scale, styled lists / quotes / code, and tappable
/// links that open externally.
class _ArticleBody extends StatelessWidget {
  final String html;
  final bool isDark;
  const _ArticleBody({required this.html, required this.isDark});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final onSurface = theme.colorScheme.onSurface;

    if (html.trim().isEmpty) {
      return Text(
        'No content available.',
        style: GoogleFonts.inter(
            color: onSurface.withValues(alpha: 0.5), fontSize: 15),
      );
    }

    return HtmlWidget(
      // Wrap in a justified block so the article reads as an evenly-aligned
      // column even when the stored content is plain text (no <p>/<div> tags),
      // in which case the per-tag justify below would never apply.
      '<div style="text-align: justify">$html</div>',
      textStyle: GoogleFonts.inter(
        fontSize: 16.5,
        height: 1.7,
        color: onSurface.withValues(alpha: 0.88),
      ),
      // Per-tag styling so headings, quotes, code and lists read as a real
      // article rather than a wall of text.
      customStylesBuilder: (element) {
        switch (element.localName) {
          case 'h1':
            return {'font-size': '24px', 'font-weight': '800', 'margin': '24px 0 10px', 'text-align': 'left'};
          case 'h2':
            return {'font-size': '21px', 'font-weight': '700', 'margin': '22px 0 8px', 'text-align': 'left'};
          case 'h3':
            return {'font-size': '18px', 'font-weight': '700', 'margin': '18px 0 6px', 'text-align': 'left'};
          // Justify all flowing body text so the article reads as a clean,
          // evenly-aligned column (rich-text editors emit p/div/li/blockquote).
          case 'p':
          case 'div':
            return {'margin': '0 0 20px', 'text-align': 'justify'};
          case 'ul':
          case 'ol':
            return {'margin': '0 0 20px', 'padding-left': '22px', 'text-align': 'justify'};
          case 'li':
            return {'margin': '0 0 8px', 'text-align': 'justify'};
          case 'blockquote':
            return {
              'margin': '16px 0',
              'padding': '8px 16px',
              'border-left': '3px solid #F97316',
              'color': '#64748B',
              'font-style': 'italic',
              'text-align': 'justify',
            };
          case 'a':
            return {'color': '#EA580C', 'text-decoration': 'underline'};
          case 'code':
            return {
              'background-color': isDark ? '#1E293B' : '#F1F5F9',
              'padding': '2px 6px',
              'border-radius': '6px',
              'font-family': 'monospace',
            };
          // Inline images: never overflow the column; rounded, full-width.
          case 'img':
            return {
              'margin': '14px auto',
              'max-width': '100%',
              'border-radius': '12px',
              'display': 'block',
            };
          default:
            return null;
        }
      },
      onTapUrl: (url) async {
        final uri = Uri.tryParse(url);
        if (uri == null) return false;
        if (await canLaunchUrl(uri)) {
          await launchUrl(uri, mode: LaunchMode.externalApplication);
          return true;
        }
        return false;
      },
    );
  }
}
