import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:sashalms/features/courses/presentation/providers/course_filter_providers.dart';
import 'package:sashalms/config/theme.dart';
import 'package:sashalms/config/app_config.dart';
import 'package:sashalms/config/design_tokens.dart';
import 'package:sashalms/core/constants/assets.dart';
import 'package:sashalms/shared/widgets/common/section_header.dart';
import 'package:sashalms/shared/widgets/common/warm_glow_background.dart';
import 'package:sashalms/features/home/presentation/widgets/stagger_testimonials_hero.dart';
import 'package:sashalms/features/internships/presentation/pages/internships_page.dart';
import 'package:sashalms/features/blog/presentation/pages/blog_list_page.dart';
import 'package:sashalms/features/blog/presentation/pages/blog_detail_page.dart';
import 'package:sashalms/features/certificates/presentation/pages/verify_certificate_page.dart';
import 'package:sashalms/features/wishlist/presentation/pages/wishlist_page.dart';
import 'package:sashalms/features/cart/presentation/pages/cart_page.dart';
import 'package:sashalms/features/ar_gallery/presentation/pages/ar_gallery_page.dart';
import 'package:sashalms/features/about/presentation/pages/about_page.dart';
import 'package:sashalms/features/companies/presentation/pages/for_companies_page.dart';
import 'package:sashalms/features/auth/presentation/providers/auth_provider.dart';
import 'package:sashalms/features/dashboard/presentation/providers/dashboard_provider.dart';
import 'package:sashalms/shared/widgets/common/user_menu.dart';
import 'package:sashalms/features/home/presentation/providers/home_instructors_provider.dart';
import 'package:sashalms/features/home/presentation/widgets/instructor_card.dart';

class HomePage extends ConsumerStatefulWidget {
  const HomePage({super.key});

  @override
  ConsumerState<HomePage> createState() => _HomePageState();
}

class _HomePageState extends ConsumerState<HomePage> {
  /// The site navigation menu, opened from the logo area. Sticky app bar +
  /// this sheet give the home page a clear, professional way to reach the
  /// secondary destinations.
  void _showNavMenu(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final items = <(IconData, String, Widget)>[
      (Icons.view_in_ar_rounded, 'AR Gallery', const ArGalleryPage()),
      (Icons.shopping_bag_outlined, 'Shopping', const CartPage()),
      (Icons.favorite_border_rounded, 'My Wishlist', const WishlistPage()),
      (Icons.business_center_outlined, 'For Companies', const ForCompaniesPage()),
      (Icons.article_outlined, 'Blogs', const BlogListPage()),
    ];
    showModalBottomSheet(
      context: context,
      backgroundColor: isDark ? AppTheme.surfaceDark : Colors.white,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(AppRadius.card)),
      ),
      builder: (sheetContext) => SafeArea(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              width: 40,
              height: 4,
              margin: const EdgeInsets.symmetric(vertical: 12),
              decoration: BoxDecoration(
                color: AppNeutrals.slate300,
                borderRadius: BorderRadius.circular(2),
              ),
            ),
            Padding(
              padding: const EdgeInsets.fromLTRB(20, 4, 20, 8),
              child: Row(
                children: [
                  Text('Navigate',
                      style: GoogleFonts.plusJakartaSans(
                          fontSize: 18, fontWeight: FontWeight.w700)),
                ],
              ),
            ),
            for (final item in items)
              ListTile(
                leading: Container(
                  width: 40,
                  height: 40,
                  decoration: BoxDecoration(
                    color: AppTheme.primary.withOpacity(0.10),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Icon(item.$1, color: AppTheme.primary, size: 21),
                ),
                title: Text(item.$2,
                    style: GoogleFonts.inter(
                        fontSize: 15, fontWeight: FontWeight.w600)),
                trailing: const Icon(Icons.chevron_right_rounded),
                onTap: () {
                  Navigator.pop(sheetContext);
                  Navigator.push(context,
                      MaterialPageRoute(builder: (_) => item.$3));
                },
              ),
            const SizedBox(height: 8),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;

    final user = ref.watch(authProvider).maybeWhen(
          authenticated: (u) => u,
          orElse: () => null,
        );
    // Pull real notifications from the student dashboard feed when applicable;
    // other roles (and signed-out states) fall back to default notifications.
    final dashData = (user != null && user.isStudent)
        ? ref.watch(studentDashboardProvider).valueOrNull
        : null;
    final allNotifications = buildDashboardNotifications(dashData);
    // Drop any the user has cleared this session so the bell badge matches the
    // notifications sheet.
    final clearedKeys = ref.watch(notificationsClearedProvider);
    final notifications = allNotifications
        .where((n) => !clearedKeys.contains(n.key))
        .toList(growable: false);
    final unread = notifications.where((n) => n.unread).length;
    final rawAvatar = user?.avatarUrl;
    final hasAvatar = rawAvatar != null && rawAvatar.isNotEmpty;
    // Backend stores a relative path (/uploads/avatars/...); NetworkImage needs
    // an absolute URL, so prefix the API host (same as course art / profile).
    final avatarUrl = hasAvatar
        ? (rawAvatar.startsWith('http')
            ? rawAvatar
            : '${AppConfig.baseUrl}$rawAvatar')
        : null;
    final initials = (user != null && user.firstName.isNotEmpty)
        ? user.firstName.substring(0, 1).toUpperCase()
        : 'S';

    return WarmGlowBackground(
      child: Scaffold(
      backgroundColor: Colors.transparent,
      body: CustomScrollView(
        slivers: [
          // Custom App Bar — scrolls away with the content (not static/sticky)
          // so the page reads edge-to-edge; the logo + nav reappear on scroll up.
          SliverAppBar(
            floating: false,
            pinned: false,
            // Transparent so the warm top-right glow reads behind the bar.
            backgroundColor: Colors.transparent,
            surfaceTintColor: Colors.transparent,
            elevation: 0,
            scrolledUnderElevation: 0,
            // Logo area doubles as the navigation menu entry point.
            title: InkWell(
              borderRadius: BorderRadius.circular(8),
              onTap: () => _showNavMenu(context),
              child: Padding(
                padding: const EdgeInsets.symmetric(vertical: 6, horizontal: 2),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Image.asset(
                      Assets.sashaLogo,
                      height: 36,
                      fit: BoxFit.contain,
                    ),
                    const SizedBox(width: 8),
                    Text(
                      'SashaInfinity',
                      style: GoogleFonts.plusJakartaSans(
                        fontSize: 22,
                        fontWeight: FontWeight.w700,
                        color: isDark ? AppTheme.textDark : AppTheme.secondary,
                      ),
                    ),
                    const SizedBox(width: 4),
                    Icon(Icons.expand_more_rounded,
                        size: 20,
                        color: (isDark ? AppTheme.textDark : AppTheme.secondary)
                            .withOpacity(0.7)),
                  ],
                ),
              ),
            ),
            actions: [
              IconButton(
                icon: Stack(
                  clipBehavior: Clip.none,
                  children: [
                    const Icon(Icons.notifications_outlined),
                    if (unread > 0)
                      Positioned(
                        top: -3,
                        right: -3,
                        child: Container(
                          constraints: const BoxConstraints(minWidth: 15, minHeight: 15),
                          padding: const EdgeInsets.symmetric(horizontal: 3),
                          alignment: Alignment.center,
                          decoration: BoxDecoration(
                            color: const Color(0xFFEF4444),
                            borderRadius: BorderRadius.circular(8),
                            border: Border.all(
                              color: isDark ? AppTheme.backgroundDark : Colors.white,
                              width: 1.5,
                            ),
                          ),
                          child: Text(
                            unread > 9 ? '9+' : '$unread',
                            style: const TextStyle(fontSize: 8, height: 1, fontWeight: FontWeight.w700, color: Colors.white),
                          ),
                        ),
                      ),
                  ],
                ),
                tooltip: 'Notifications',
                onPressed: () => showNotificationsSheet(context, notifications),
              ),
              const SizedBox(width: 8),
              GestureDetector(
                onTap: () => showUserProfileSheet(context, ref),
                child: CircleAvatar(
                  radius: 18,
                  backgroundColor: AppTheme.primary,
                  backgroundImage: hasAvatar ? NetworkImage(avatarUrl!) : null,
                  child: hasAvatar
                      ? null
                      : Text(initials, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
                ),
              ),
              const SizedBox(width: 16),
            ],
          ),
          
          // Hero Header Section — Stagger Testimonials auto-scrolling deck
          // (replaces the previous swipeable AR/VR + Learn-Sasha carousel).
          const SliverToBoxAdapter(
            child: Padding(
              padding: EdgeInsets.only(top: 8, bottom: 4),
              child: StaggerTestimonialsHero(),
            ),
          ),

          // Sasha Velocity Stats Bar — continuous "runner" (auto-scrolling marquee)
          SliverToBoxAdapter(
            child: Padding(
              padding: const EdgeInsets.symmetric(vertical: 24),
              child: _MarqueeStats(
                stepWidth: 180,
                height: 84,
                children: [
                  _buildStatItem('100+', 'AR Models', Icons.layers_outlined, theme, onTap: () => _openArGallery(context)),
                  _buildStatItem('3D', 'Visualization', Icons.view_in_ar_outlined, theme, onTap: () => _openArGallery(context)),
                  _buildStatItem('50+', 'Students', Icons.people_outline, theme),
                  _buildStatItem('98%', 'Satisfaction', Icons.star_border, theme),
                ],
              ),
            ),
          ),

          // Categories Grid Section
          SliverToBoxAdapter(
            child: Padding(
              padding: const EdgeInsets.all(24),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  SectionHeader(
                    title: 'Browse By Tech Stack',
                    actionLabel: 'View All',
                    onAction: () {
                      ref.read(selectedCategoryProvider.notifier).state = null;
                      ref.read(scaffoldTabProvider.notifier).state = 1;
                    },
                  ),
                  const SizedBox(height: 16),
                  GridView.count(
                    shrinkWrap: true,
                    physics: const NeverScrollableScrollPhysics(),
                    crossAxisCount: 3,
                    crossAxisSpacing: 12,
                    childAspectRatio: 0.85,
                    children: [
                      _buildCategoryCard(
                        title: 'Full Stack',
                        count: 'Courses',
                        icon: Icons.code_rounded,
                        colors: [const Color(0xFFF97316), const Color(0xFFEA580C)], // Orange
                        onTap: () => _onCategoryTap(context, 'Full Stack'),
                      ),
                      _buildCategoryCard(
                        title: 'AI',
                        count: 'Courses',
                        icon: Icons.psychology_rounded,
                        colors: [const Color(0xFF0284C7), const Color(0xFF0369A1)], // Blue
                        onTap: () => _onCategoryTap(context, 'AI'),
                      ),
                      _buildCategoryCard(
                        title: 'Analytics',
                        count: 'Courses',
                        icon: Icons.analytics_outlined,
                        colors: [const Color(0xFF0D9488), const Color(0xFF0F766E)], // Teal
                        onTap: () => _onCategoryTap(context, 'Analytics'),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ),

          // Student Services Section
          SliverToBoxAdapter(
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 8),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const SectionHeader(title: 'Student Services'),
                  const SizedBox(height: 16),
                  GridView.count(
                    shrinkWrap: true,
                    physics: const NeverScrollableScrollPhysics(),
                    crossAxisCount: 2,
                    crossAxisSpacing: 12,
                    mainAxisSpacing: 12,
                    childAspectRatio: 2.2,
                    children: [
                      _buildServiceCard(
                        context: context,
                        title: 'Internships',
                        subtitle: 'Opportunities',
                        icon: Icons.work_outline,
                        color: AppTheme.primary,
                        onTap: () => Navigator.push(
                          context,
                          MaterialPageRoute(builder: (context) => const InternshipsPage()),
                        ),
                      ),
                      _buildServiceCard(
                        context: context,
                        title: 'AR Gallery',
                        subtitle: 'Interactive 3D',
                        icon: Icons.view_in_ar_outlined,
                        color: const Color(0xFFF97316),
                        onTap: () => Navigator.push(
                          context,
                          MaterialPageRoute(builder: (context) => const ArGalleryPage()),
                        ),
                      ),
                      _buildServiceCard(
                        context: context,
                        title: 'Latest Blogs',
                        subtitle: 'News & Articles',
                        icon: Icons.menu_book_outlined,
                        color: AppTheme.info,
                        onTap: () => Navigator.push(
                          context,
                          MaterialPageRoute(builder: (context) => const BlogListPage()),
                        ),
                      ),
                      _buildServiceCard(
                        context: context,
                        title: 'Verify Badge',
                        subtitle: 'Verify Credentials',
                        icon: Icons.verified_user_outlined,
                        color: AppTheme.success,
                        onTap: () => Navigator.push(
                          context,
                          MaterialPageRoute(builder: (context) => const VerifyCertificatePage()),
                        ),
                      ),
                      _buildServiceCard(
                        context: context,
                        title: 'My Wishlist',
                        subtitle: 'Saved Courses',
                        icon: Icons.favorite_border,
                        color: AppTheme.danger,
                        onTap: () => Navigator.push(
                          context,
                          MaterialPageRoute(builder: (context) => const WishlistPage()),
                        ),
                      ),
                      _buildServiceCard(
                        context: context,
                        title: 'Shopping Cart',
                        subtitle: 'Checkout',
                        icon: Icons.shopping_cart_outlined,
                        color: AppTheme.secondary,
                        onTap: () => Navigator.push(
                          context,
                          MaterialPageRoute(builder: (context) => const CartPage()),
                        ),
                      ),
                      _buildServiceCard(
                        context: context,
                        title: 'About Us',
                        subtitle: 'Who We Are',
                        icon: Icons.info_outline,
                        color: AppTheme.primary,
                        onTap: () => Navigator.push(
                          context,
                          MaterialPageRoute(builder: (context) => const AboutPage()),
                        ),
                      ),
                      _buildServiceCard(
                        context: context,
                        title: 'For Companies',
                        subtitle: 'Hire Graduates',
                        icon: Icons.business_center_outlined,
                        color: Colors.indigo,
                        onTap: () => Navigator.push(
                          context,
                          MaterialPageRoute(builder: (context) => const ForCompaniesPage()),
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ),

          // What Makes Us Different Section
          SliverToBoxAdapter(
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 8),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const SectionHeader(title: 'What Makes Us Different'),
                  const SizedBox(height: 16),
                  _buildDifferentCard(
                    title: 'Immersive AR/VR Learning',
                    desc: 'Experience mathematics like never before with our cutting-edge Augmented and Virtual Reality modules. Visualize complex concepts in 3D.',
                    icon: Icons.threed_rotation,
                    color: AppTheme.primary,
                    theme: theme,
                  ),
                  const SizedBox(height: 12),
                  _buildDifferentCard(
                    title: 'Personalized Learning Paths',
                    desc: "Our AI-driven platform creates customized learning journeys for each student. Adaptive quizzes and data-driven insights optimize results.",
                    icon: Icons.psychology_outlined,
                    color: AppTheme.info,
                    theme: theme,
                  ),
                  const SizedBox(height: 12),
                  _buildDifferentCard(
                    title: 'Hybrid Tutoring Centers',
                    desc: 'Combining the best of online and offline education. Our hybrid centers in cities provide hands-on guidance with digital tools.',
                    icon: Icons.domain,
                    color: AppTheme.secondary,
                    theme: theme,
                  ),
                ],
              ),
            ),
          ),

          // Our Instructors Section
          SliverToBoxAdapter(
            child: Padding(
              padding: const EdgeInsets.symmetric(vertical: 32),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Padding(
                    padding: EdgeInsets.symmetric(horizontal: 24),
                    child: SectionHeader(title: 'Our Instructors'),
                  ),
                  const SizedBox(height: 16),
                  SizedBox(
                    height: 140,
                    child: ref.watch(homeInstructorsProvider).when(
                      data: (instructors) {
                        if (instructors.isEmpty) return const SizedBox.shrink();
                        return ListView.builder(
                          scrollDirection: Axis.horizontal,
                          padding: const EdgeInsets.symmetric(horizontal: 16),
                          itemCount: instructors.length,
                          itemBuilder: (context, i) {
                            return Padding(
                              padding: const EdgeInsets.only(right: 12),
                              child: InstructorCard(
                                instructor: instructors[i],
                                onTap: () {
                                  final name = instructors[i].name.toLowerCase().replaceAll(' ', '.');
                                  Navigator.pushNamed(context, '/u/$name');
                                },
                              ),
                            );
                          },
                        );
                      },
                      loading: () => ListView.builder(
                        scrollDirection: Axis.horizontal,
                        padding: const EdgeInsets.symmetric(horizontal: 16),
                        itemCount: 6,
                        itemBuilder: (_, __) => const Padding(
                          padding: EdgeInsets.only(right: 12),
                          child: _InstructorSkeleton(),
                        ),
                      ),
                      error: (_, __) => const SizedBox.shrink(),
                    ),
                  ),
                ],
              ),
            ),
          ),

          // Latest News & Blog Section
          SliverToBoxAdapter(
            child: Padding(
              padding: const EdgeInsets.symmetric(vertical: 32),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Padding(
                    padding: EdgeInsets.symmetric(horizontal: 24),
                    child: SectionHeader(title: 'Latest News & Blog'),
                  ),
                  const SizedBox(height: 16),
                  SizedBox(
                    height: 232,
                    // Real blog feed; tapping a card opens the full article.
                    // Falls back to sample cards (which open the blog list) when
                    // the feed is loading, empty, or unavailable.
                    child: ref.watch(publicBlogsProvider).when(
                          data: (blogs) {
                            final posts = blogs.whereType<Map<String, dynamic>>().take(8).toList();
                            if (posts.isEmpty) return _buildStaticBlogList(context, theme);
                            return ListView.builder(
                              scrollDirection: Axis.horizontal,
                              padding: const EdgeInsets.symmetric(horizontal: 16),
                              itemCount: posts.length,
                              itemBuilder: (context, i) {
                                final post = posts[i];
                                final slug = (post['slug'] ?? '').toString();
                                final authorRaw = post['author'];
                                final author = (authorRaw is Map &&
                                        authorRaw['name'] != null)
                                    ? authorRaw['name'].toString()
                                    : 'SashaInfinity';
                                final views = (post['view_count'] is num)
                                    ? (post['view_count'] as num).toInt()
                                    : 0;
                                final comments = (post['comment_count'] is num)
                                    ? (post['comment_count'] as num).toInt()
                                    : 0;
                                final rawDate =
                                    (post['created_at'] ?? post['post_date'] ?? '')
                                        .toString();
                                return _buildBlogCard(
                                  title: (post['title'] ?? 'Untitled').toString(),
                                  date: rawDate.length >= 10
                                      ? rawDate.substring(0, 10)
                                      : rawDate,
                                  category: (post['category'] ?? 'Blog').toString(),
                                  author: author,
                                  views: views,
                                  comments: comments,
                                  theme: theme,
                                  onTap: slug.isEmpty
                                      ? null
                                      : () => Navigator.push(
                                            context,
                                            MaterialPageRoute(builder: (_) => BlogDetailPage(slug: slug)),
                                          ),
                                );
                              },
                            );
                          },
                          loading: () => _buildStaticBlogList(context, theme),
                          error: (_, __) => _buildStaticBlogList(context, theme),
                        ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
      ),
    );
  }

  Widget _buildServiceCard({
    required BuildContext context,
    required String title,
    required String subtitle,
    required IconData icon,
    required Color color,
    required VoidCallback onTap,
  }) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(18),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
        decoration: BoxDecoration(
          color: isDark ? AppTheme.surfaceDark : Colors.white,
          borderRadius: BorderRadius.circular(18),
          border: Border.all(color: isDark ? AppTheme.borderDark : AppTheme.borderLight),
          boxShadow: isDark ? null : AppShadows.soft,
        ),
        child: Row(
          children: [
            Container(
              padding: const EdgeInsets.all(9),
              decoration: BoxDecoration(
                color: color.withOpacity(0.1),
                borderRadius: BorderRadius.circular(11),
              ),
              child: Icon(icon, color: color, size: 22),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Text(
                    title,
                    style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 13),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                  Text(
                    subtitle,
                    style: TextStyle(color: isDark ? AppTheme.mutedDark : AppTheme.mutedLight, fontSize: 10.5),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  void _onCategoryTap(BuildContext context, String category) {
    ref.read(selectedCategoryProvider.notifier).state = category.toLowerCase();
    ref.read(scaffoldTabProvider.notifier).state = 1; // Switch to Catalog tab
  }

  void _openArGallery(BuildContext context) {
    Navigator.push(
      context,
      MaterialPageRoute(builder: (_) => const ArGalleryPage()),
    );
  }

  Widget _buildStatItem(String num, String label, IconData icon, ThemeData theme, {VoidCallback? onTap}) {
    final isDark = theme.brightness == Brightness.dark;
    final tappable = onTap != null;
    return GestureDetector(
      onTap: onTap,
      behavior: HitTestBehavior.opaque,
      child: Container(
        width: 168,
        height: 84,
        margin: const EdgeInsets.only(right: 12),
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
        decoration: BoxDecoration(
          color: isDark ? AppTheme.surfaceDark : Colors.white,
          borderRadius: BorderRadius.circular(18),
          border: Border.all(
            color: tappable
                ? AppTheme.primary.withOpacity(0.45)
                : (isDark ? const Color(0xFF273449) : const Color(0xFFEEF2F6)),
          ),
          boxShadow: isDark ? null : AppShadows.card,
        ),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.center,
          children: [
            Container(
              width: 40,
              height: 40,
              alignment: Alignment.center,
              decoration: BoxDecoration(
                color: AppTheme.primary.withOpacity(0.1),
                borderRadius: BorderRadius.circular(12),
              ),
              child: Icon(icon, color: AppTheme.primary, size: 20),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisAlignment: MainAxisAlignment.center,
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(
                    num,
                    style: GoogleFonts.plusJakartaSans(
                      fontWeight: FontWeight.w800,
                      fontSize: 18,
                      height: 1,
                    ),
                  ),
                  const SizedBox(height: 3),
                  Row(
                    children: [
                      Flexible(
                        child: Text(
                          label,
                          style: theme.textTheme.bodySmall?.copyWith(fontSize: 10.5, height: 1.1),
                          overflow: TextOverflow.ellipsis,
                        ),
                      ),
                      if (tappable) ...[
                        const SizedBox(width: 3),
                        Icon(Icons.arrow_forward_rounded, size: 11, color: AppTheme.primary),
                      ],
                    ],
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildCategoryCard({
    required String title,
    required String count,
    required IconData icon,
    required List<Color> colors,
    required VoidCallback onTap,
  }) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(18),
      child: Container(
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: colors,
          ),
          borderRadius: BorderRadius.circular(18),
          // Subtle neutral lift only — no bright coloured glow (pro DNA).
          boxShadow: AppShadows.soft,
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Container(
              padding: const EdgeInsets.all(8),
              decoration: BoxDecoration(
                color: Colors.white.withOpacity(0.2),
                shape: BoxShape.circle,
              ),
              child: Icon(icon, color: Colors.white, size: 22),
            ),
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: GoogleFonts.plusJakartaSans(
                    color: Colors.white,
                    fontWeight: FontWeight.bold,
                    fontSize: 12,
                  ),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
                const SizedBox(height: 2),
                Text(
                  count,
                  style: const TextStyle(
                    color: Colors.white70,
                    fontSize: 10,
                  ),
                ),
              ],
            )
          ],
        ),
      ),
    );
  }

  Widget _buildDifferentCard({
    required String title,
    required String desc,
    required IconData icon,
    required Color color,
    required ThemeData theme,
  }) {
    final isDark = theme.brightness == Brightness.dark;
    return Container(
      padding: const EdgeInsets.all(AppSpacing.card),
      decoration: BoxDecoration(
        color: isDark ? AppTheme.surfaceDark : Colors.white,
        borderRadius: BorderRadius.circular(AppRadius.lg),
        border: Border.all(color: isDark ? AppTheme.borderDark : AppTheme.borderLight),
        boxShadow: isDark ? null : AppShadows.soft,
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            padding: const EdgeInsets.all(11),
            decoration: BoxDecoration(
              color: color.withOpacity(0.1),
              borderRadius: BorderRadius.circular(12),
            ),
            child: Icon(icon, color: color, size: 24),
          ),
          const SizedBox(width: 16),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: theme.textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold),
                ),
                const SizedBox(height: 6),
                Text(
                  desc,
                  style: theme.textTheme.bodyMedium?.copyWith(
                    color: theme.textTheme.bodyMedium?.color?.withOpacity(0.7),
                    height: 1.4,
                  ),
                ),
              ],
            ),
          )
        ],
      ),
    );
  }

  Widget _buildBlogCard({
    required String title,
    required String date,
    required String category,
    required ThemeData theme,
    String author = 'SashaInfinity',
    int views = 0,
    int comments = 0,
    VoidCallback? onTap,
  }) {
    final isDark = theme.brightness == Brightness.dark;
    final muted = isDark ? AppTheme.mutedDark : AppTheme.mutedLight;
    return GestureDetector(
      onTap: onTap,
      child: Container(
        width: 280,
        margin: const EdgeInsets.only(right: 16),
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: isDark ? AppTheme.surfaceDark : Colors.white,
          borderRadius: BorderRadius.circular(18),
          border: Border.all(color: isDark ? const Color(0xFF273449) : const Color(0xFFEEF2F6)),
          boxShadow: isDark ? null : AppShadows.card,
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                  decoration: BoxDecoration(
                    color: AppTheme.primary.withOpacity(0.1),
                    borderRadius: BorderRadius.circular(4),
                  ),
                  child: Text(
                    category,
                    style: const TextStyle(
                      color: AppTheme.primary,
                      fontSize: 10,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ),
                const SizedBox(height: 10),
                Text(
                  title,
                  style: theme.textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.bold,
                    height: 1.3,
                  ),
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                ),
                const SizedBox(height: 10),
                // Metadata — author, views and comments.
                Row(
                  children: [
                    Icon(Icons.person_outline, size: 14, color: muted),
                    const SizedBox(width: 4),
                    Flexible(
                      child: Text(
                        author,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: theme.textTheme.bodySmall
                            ?.copyWith(color: muted, fontSize: 11.5),
                      ),
                    ),
                    const SizedBox(width: 12),
                    Icon(Icons.visibility_outlined, size: 14, color: muted),
                    const SizedBox(width: 4),
                    Text(
                      _compactCount(views),
                      style: theme.textTheme.bodySmall
                          ?.copyWith(color: muted, fontSize: 11.5),
                    ),
                    const SizedBox(width: 12),
                    Icon(Icons.chat_bubble_outline, size: 13, color: muted),
                    const SizedBox(width: 4),
                    Text(
                      _compactCount(comments),
                      style: theme.textTheme.bodySmall
                          ?.copyWith(color: muted, fontSize: 11.5),
                    ),
                  ],
                ),
              ],
            ),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Flexible(
                  child: Text(
                    date,
                    style: theme.textTheme.bodySmall?.copyWith(color: Colors.grey),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
                if (onTap != null)
                  const Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Text('Read', style: TextStyle(color: AppTheme.primary, fontSize: 12, fontWeight: FontWeight.w600)),
                      Icon(Icons.arrow_forward_rounded, size: 13, color: AppTheme.primary),
                    ],
                  ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  /// Compact a count for the blog meta row (1240 -> "1.2k").
  String _compactCount(int n) {
    if (n >= 1000000) return '${(n / 1000000).toStringAsFixed(1)}M';
    if (n >= 1000) return '${(n / 1000).toStringAsFixed(1)}k';
    return '$n';
  }

  /// Sample cards shown when the live blog feed isn't available; tapping any
  /// opens the full blog list.
  Widget _buildStaticBlogList(BuildContext context, ThemeData theme) {
    void openList() => Navigator.push(
          context,
          MaterialPageRoute(builder: (_) => const BlogListPage()),
        );
    return ListView(
      scrollDirection: Axis.horizontal,
      padding: const EdgeInsets.symmetric(horizontal: 16),
      children: [
        _buildBlogCard(title: 'The Future of Spatial Computing in Classrooms', date: 'June 08, 2026', category: 'AR/VR', author: 'Sasha Team', views: 1240, comments: 18, theme: theme, onTap: openList),
        _buildBlogCard(title: 'How Adaptive AI Helps Students Master Math Faster', date: 'June 05, 2026', category: 'Artificial Intelligence', author: 'Dr. Meena', views: 980, comments: 12, theme: theme, onTap: openList),
        _buildBlogCard(title: 'Bridging the Rural Education Gap with Hybrid Centers', date: 'May 28, 2026', category: 'Education Tech', author: 'Sasha Team', views: 2310, comments: 27, theme: theme, onTap: openList),
      ],
    );
  }
}

/// Continuous auto-scrolling "runner" of stat cards. Renders the cards twice
/// end-to-end and translates the row by exactly one full set on a linear loop,
/// so the wrap is seamless. Hit-testing works through the transform, so the
/// tappable AR cards still respond while moving.
class _MarqueeStats extends StatefulWidget {
  final List<Widget> children;
  final double stepWidth; // per-card advance (card width + trailing gap)
  final double height;

  const _MarqueeStats({
    required this.children,
    required this.stepWidth,
    required this.height,
  });

  @override
  State<_MarqueeStats> createState() => _MarqueeStatsState();
}

class _MarqueeStatsState extends State<_MarqueeStats>
    with SingleTickerProviderStateMixin {
  static const double _pxPerSecond = 42;
  late final AnimationController _controller;
  late final Animation<double> _offset;

  @override
  void initState() {
    super.initState();
    final oneSet = widget.stepWidth * widget.children.length;
    final durationMs = (oneSet / _pxPerSecond * 1000).round();
    _controller = AnimationController(
      vsync: this,
      duration: Duration(milliseconds: durationMs),
    );
    _offset = Tween<double>(begin: 0, end: -oneSet)
        .animate(CurvedAnimation(parent: _controller, curve: Curves.linear))
      ..addStatusListener((status) {
        if (status == AnimationStatus.completed) {
          // Snap to the start: the second copy is now exactly where the first
          // began, so the loop reads as seamless.
          _controller.forward(from: 0);
        }
      });
    _controller.forward();
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  // Hold the marquee still while a finger is down so the (otherwise moving)
  // cards are easy to tap — then resume the scroll on release. Without this the
  // tappable "AR Models" / "Visualization" cards are a moving target.
  void _resume() {
    if (mounted && !_controller.isAnimating) _controller.forward();
  }

  @override
  Widget build(BuildContext context) {
    return Listener(
      onPointerDown: (_) => _controller.stop(),
      onPointerUp: (_) => _resume(),
      onPointerCancel: (_) => _resume(),
      child: ClipRect(
      child: SizedBox(
        height: widget.height,
        child: AnimatedBuilder(
          animation: _offset,
          builder: (_, __) => Transform.translate(
            offset: Offset(_offset.value, 0),
            // Unbounded width so the two card sets lay out at their natural
            // combined width; the outer ClipRect clips the overflow. Without
            // this the Row is given a tight width and throws a layout overflow.
            child: OverflowBox(
              maxWidth: double.infinity,
              alignment: Alignment.centerLeft,
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  ...widget.children,
                  ...widget.children,
                ],
              ),
            ),
          ),
        ),
      ),
      ),
    );
  }
}

/// Skeleton placeholder for the instructor cards while loading.
class _InstructorSkeleton extends StatelessWidget {
  const _InstructorSkeleton();

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return Container(
      width: 110,
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 16),
      decoration: BoxDecoration(
        color: isDark ? AppTheme.surfaceDark : Colors.white,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
          color: isDark ? AppTheme.borderDark : AppTheme.borderLight,
        ),
      ),
      child: Column(
        children: [
          Container(
            width: 64,
            height: 64,
            decoration: BoxDecoration(
              color: isDark ? Colors.white10 : const Color(0xFFE2E8F0),
              shape: BoxShape.circle,
            ),
          ),
          const SizedBox(height: 10),
          Container(
            height: 12,
            width: 70,
            decoration: BoxDecoration(
              color: isDark ? Colors.white10 : const Color(0xFFE2E8F0),
              borderRadius: BorderRadius.circular(6),
            ),
          ),
          const SizedBox(height: 6),
          Container(
            height: 10,
            width: 50,
            decoration: BoxDecoration(
              color: isDark ? Colors.white10 : const Color(0xFFE2E8F0),
              borderRadius: BorderRadius.circular(5),
            ),
          ),
        ],
      ),
    );
  }
}
