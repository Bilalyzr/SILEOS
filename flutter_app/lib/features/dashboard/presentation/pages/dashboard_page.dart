import 'dart:math' as math;
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:go_router/go_router.dart';
import '../../../auth/presentation/providers/auth_provider.dart';
import '../../../auth/presentation/providers/auth_state.dart';
import '../../../auth/domain/entities/user.dart';
import '../providers/dashboard_provider.dart';
import 'student_report_page.dart';
import 'continue_learning_page.dart';
import '../widgets/admin_dashboard_view.dart';
import '../widgets/instructor_dashboard_view.dart';
import '../../domain/entities/dashboard_data.dart';
import '../../../courses/presentation/providers/course_filter_providers.dart';
import '../../../internships/presentation/pages/internships_page.dart';
import '../../../internships/presentation/pages/internship_detail_page.dart';
import '../../../wishlist/presentation/pages/wishlist_page.dart';
import '../../../ar_gallery/presentation/pages/ar_gallery_page.dart';
import '../../../../shared/widgets/common/error_display.dart';
import '../../../../shared/widgets/common/skeleton_loader.dart';
import '../../../../shared/widgets/common/warm_glow_background.dart';

// ── Palette — calm & neat ───────────────────────────────────────────────────
// A light, airy surface with a single warm brand accent. No bright gradient
// header — the greeting sits on the page background; orange is used sparingly.
const Color _bg = Color(0xFFF6F5F4); // warm off-white
const Color _surface = Color(0xFFFFFFFF);
const Color _border = Color(0x0F1E293B); // ~0.06 hairline
const Color _ink = Color(0xFF1E293B); // slate-800
const Color _textSecondary = Color(0xFF64748B); // slate-500
const Color _textTertiary = Color(0xFF94A3B8); // slate-400

// Brand accent + soft tinted families used only for small surfaces / icons.
const Color _accent = Color(0xFFEA580C); // orange-600
const Color _orange = Color(0xFFEA580C);
const Color _orangeLight = Color(0xFFFFF1E7);
const Color _teal = Color(0xFF0D9488);
const Color _tealLight = Color(0xFFD8FBF3);
const Color _violet = Color(0xFF7C3AED);
const Color _violetLight = Color(0xFFF1E9FE);
const Color _amber = Color(0xFFB45309);
const Color _amberLight = Color(0xFFFEF3C7);
const Color _green = Color(0xFF15803D);
const Color _greenLight = Color(0xFFDCFCE7);

class DashboardPage extends ConsumerWidget {
  const DashboardPage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final authState = ref.watch(authProvider);
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;

    ref.listen<AuthState>(authProvider, (previous, next) {
      final prevUser = previous?.maybeWhen(authenticated: (u) => u.id, orElse: () => null);
      final nextUser = next.maybeWhen(authenticated: (u) => u.id, orElse: () => null);
      if (prevUser != nextUser) {
        ref.invalidate(studentDashboardProvider);
        ref.invalidate(instructorDashboardProvider);
        ref.invalidate(adminDashboardProvider);
      }
    });

    final user = authState.maybeWhen(authenticated: (u) => u, orElse: () => null);
    final isAuth = user != null;

    if (!isAuth) {
      return Scaffold(
        appBar: AppBar(title: Text('Learning Dashboard', style: GoogleFonts.inter(fontWeight: FontWeight.bold))),
        body: Center(
          child: Padding(
            padding: const EdgeInsets.all(32.0),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Icon(Icons.lock_outline, size: 80, color: _accent.withOpacity(0.5)),
                const SizedBox(height: 24),
                Text('Login Required', style: GoogleFonts.inter(fontSize: 24, fontWeight: FontWeight.bold)),
                const SizedBox(height: 12),
                Text('Please sign in to view your personalized dashboard, track progress, and access your courses.', textAlign: TextAlign.center, style: GoogleFonts.inter(color: Colors.grey)),
                const SizedBox(height: 32),
                ElevatedButton(
                  onPressed: () => context.go('/login'),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: _accent,
                    foregroundColor: Colors.white,
                    padding: const EdgeInsets.symmetric(horizontal: 48, vertical: 16),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                  ),
                  child: const Text('Sign In'),
                ),
              ],
            ),
          ),
        ),
      );
    }

    if (user.isInstructor) return const InstructorDashboardView();
    if (user.isAdmin) return const AdminDashboardView();
    if (user.isCompany || user.isCompanyManager) {
      return Scaffold(
        appBar: AppBar(title: Text('Company Dashboard', style: GoogleFonts.inter(fontWeight: FontWeight.bold))),
        body: Center(
          child: Padding(
            padding: const EdgeInsets.all(32.0),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Icon(Icons.business_outlined, size: 80, color: _accent.withOpacity(0.5)),
                const SizedBox(height: 24),
                Text('Company portal is web-only', style: GoogleFonts.inter(fontSize: 20, fontWeight: FontWeight.bold), textAlign: TextAlign.center),
                const SizedBox(height: 12),
                Text('Please use sashainfinity.com on a browser to manage internships, work logs and announcements.', textAlign: TextAlign.center, style: GoogleFonts.inter(color: Colors.grey)),
              ],
            ),
          ),
        ),
      );
    }

    final dashboardAsync = ref.watch(studentDashboardProvider);
    // Page base now comes from WarmGlowBackground; the Scaffold is transparent.
    final surfaceColor = isDark ? const Color(0xFF1E293B) : _surface;
    final textColor = isDark ? Colors.white : _ink;

    return WarmGlowBackground(
      child: Scaffold(
      backgroundColor: Colors.transparent,
      body: dashboardAsync.when(
        data: (data) {
          Widget section(int index, List<Widget> children) => _FadeSlideIn(
                delayMs: 60 * index,
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: children),
              );

          return RefreshIndicator(
            onRefresh: () => ref.refresh(studentDashboardProvider.future),
            color: _accent,
            child: Stack(
              children: [
                // Subtle, slow drifting shapes behind everything.
                const Positioned.fill(child: _FloatingShapes()),
                CustomScrollView(
                  physics: const AlwaysScrollableScrollPhysics(),
                  slivers: [
                    SliverToBoxAdapter(child: _Header(user: user, textColor: textColor)),
                    SliverToBoxAdapter(
                      child: _FadeSlideIn(
                        delayMs: 40,
                        child: _ProgressCard(goal: data.weeklyGoal, surfaceColor: surfaceColor, isDark: isDark),
                      ),
                    ),
                    const SliverToBoxAdapter(child: SizedBox(height: 26)),
                    SliverToBoxAdapter(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          // Featured: Continue learning leads the dashboard.
                          section(1, [
                            _sectionHeader('Continue learning', 'Show all', () {
                              Navigator.push(
                                context,
                                MaterialPageRoute(
                                  builder: (_) => const ContinueLearningPage(),
                                ),
                              );
                            }),
                            _buildContinueLearning(context, data.enrolledCourses, surfaceColor, isDark),
                          ]),
                          const SizedBox(height: 28),
                          section(2, [
                            _sectionHeader('Dashboard summary', 'Full report', () {
                              Navigator.push(
                                context,
                                MaterialPageRoute(
                                  builder: (_) => StudentReportPage(data: data),
                                ),
                              );
                            }),
                            _buildSummaryPie(data, surfaceColor, isDark),
                          ]),
                          const SizedBox(height: 28),
                          // Quick actions sit just below the dashboard summary.
                          section(3, [
                            _sectionHeader('Quick actions', '', () {}),
                            _buildQuickActions(context, ref, surfaceColor, isDark),
                          ]),
                          const SizedBox(height: 28),
                          section(4, [
                            _sectionHeader('Open internships', 'Browse all', () {
                              Navigator.push(context, MaterialPageRoute(builder: (_) => const InternshipsPage()));
                            }),
                            _buildInternships(context, data.internships, ref, surfaceColor, isDark),
                          ]),
                          const SizedBox(height: 28),
                          section(5, [
                            _sectionHeader('Recent activity', '', () {}),
                            _buildRecentActivity(data.recentActivity, surfaceColor, isDark),
                          ]),
                          const SizedBox(height: 96), // room for the floating tutor
                        ],
                      ),
                    ),
                  ],
                ),
              ],
            ),
          );
        },
        loading: () => _buildSkeleton(context, isDark),
        error: (err, stack) => ErrorDisplay(
          message: 'Error loading dashboard: $err',
          onRetry: () => ref.refresh(studentDashboardProvider),
        ),
      ),
      ),
    );
  }

  // ── Section header ──────────────────────────────────────────────────────
  Widget _sectionHeader(String title, String actionLabel, VoidCallback onTap) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(20, 0, 20, 14),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(title, style: GoogleFonts.plusJakartaSans(fontSize: 19, fontWeight: FontWeight.w700, letterSpacing: -0.3, color: _ink)),
          if (actionLabel.isNotEmpty)
            _Pressable(
              onTap: onTap,
              scale: 0.92,
              child: Row(
                children: [
                  Text(actionLabel, style: GoogleFonts.inter(fontSize: 12.5, fontWeight: FontWeight.w600, color: _accent)),
                  const SizedBox(width: 2),
                  const Icon(Icons.chevron_right_rounded, size: 16, color: _accent),
                ],
              ),
            ),
        ],
      ),
    );
  }

  // ── Dashboard summary (interactive 3D pie breakdown) ──────────────────────
  // Replaces the old 2×2 stat-tile grid with an infographic-style extruded pie
  // (see issues/design.jpg). Slices act as buttons: tapping one explodes it out
  // and reveals a detail panel that drills into the live course/internship data.
  Widget _buildSummaryPie(DashboardData data, Color surfaceColor, bool isDark) =>
      _DashboardSummary(data: data, surfaceColor: surfaceColor, isDark: isDark);

  // ── Quick actions (navigation shortcuts) ─────────────────────────────────
  Widget _buildQuickActions(BuildContext context, WidgetRef ref, Color surfaceColor, bool isDark) {
    final actions = <_QuickAction>[
      _QuickAction(Icons.menu_book_rounded, 'Browse\ncourses', _orange, _orangeLight,
          () => ref.read(scaffoldTabProvider.notifier).state = 1),
      _QuickAction(Icons.favorite_border_rounded, 'My\nwishlist', _violet, _violetLight,
          () => Navigator.push(context, MaterialPageRoute(builder: (_) => const WishlistPage()))),
      _QuickAction(Icons.view_in_ar_rounded, 'AR\ngallery', _teal, _tealLight,
          () => Navigator.push(context, MaterialPageRoute(builder: (_) => const ArGalleryPage()))),
    ];
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16),
      child: Row(
        children: [
          for (int i = 0; i < actions.length; i++) ...[
            Expanded(child: _QuickActionTile(action: actions[i], surfaceColor: surfaceColor, isDark: isDark)),
            if (i != actions.length - 1) const SizedBox(width: 12),
          ],
        ],
      ),
    );
  }

  // ── Continue learning (horizontal carousel) ──────────────────────────────
  Widget _buildContinueLearning(BuildContext context, List<DashboardCourse> courses, Color surfaceColor, bool isDark) {
    if (courses.isEmpty) {
      return Padding(
        padding: const EdgeInsets.symmetric(horizontal: 20),
        child: Container(
          width: double.infinity,
          padding: const EdgeInsets.symmetric(vertical: 28, horizontal: 18),
          decoration: BoxDecoration(
            color: surfaceColor,
            borderRadius: BorderRadius.circular(20),
            border: Border.all(color: isDark ? Colors.white10 : _border),
          ),
          child: Column(
            children: [
              Icon(Icons.auto_stories_outlined, size: 34, color: _textTertiary),
              const SizedBox(height: 10),
              Text("You haven't enrolled in any courses yet.", textAlign: TextAlign.center, style: GoogleFonts.inter(fontSize: 13, color: _textSecondary)),
            ],
          ),
        ),
      );
    }

    final items = courses.take(5).toList();
    // Full-width cards: each card spans the page content width (screen minus the
    // 20px side padding) so it reads as a full, edge-to-edge card. The list
    // still pages horizontally between courses (snapping one card at a time).
    final cardW = MediaQuery.of(context).size.width - 40;
    return SizedBox(
      height: 208,
      child: ListView.separated(
        scrollDirection: Axis.horizontal,
        padding: const EdgeInsets.symmetric(horizontal: 20),
        physics: const PageScrollPhysics(),
        itemCount: items.length,
        separatorBuilder: (_, __) => const SizedBox(width: 12),
        itemBuilder: (context, i) => _CourseCard(
          course: items[i],
          width: cardW,
          surfaceColor: surfaceColor,
          isDark: isDark,
          onResume: () => context.push('/courses/${items[i].id}'),
        ),
      ),
    );
  }

  // ── Internships ───────────────────────────────────────────────────────────
  Widget _buildInternships(BuildContext context, List<StudentInternship> studentInternships, WidgetRef ref, Color surfaceColor, bool isDark) {
    void openInternships() => Navigator.push(
          context,
          MaterialPageRoute(builder: (_) => const InternshipsPage()),
        );

    final publicAsync = ref.watch(publicInternshipsProvider);
    final publicList = publicAsync.valueOrNull ?? <dynamic>[];

    // If no data from either source, show placeholder
    if (studentInternships.isEmpty && publicList.isEmpty) {
      return Padding(
        padding: const EdgeInsets.symmetric(horizontal: 20),
        child: Container(
          width: double.infinity,
          padding: const EdgeInsets.symmetric(vertical: 28, horizontal: 18),
          decoration: BoxDecoration(
            color: surfaceColor,
            borderRadius: BorderRadius.circular(20),
            border: Border.all(color: isDark ? Colors.white10 : _border),
          ),
          child: Column(
            children: [
              Icon(Icons.work_outline, size: 34, color: _textTertiary),
              const SizedBox(height: 10),
              Text('No internships available yet.', textAlign: TextAlign.center, style: GoogleFonts.inter(fontSize: 13, color: _textSecondary)),
            ],
          ),
        ),
      );
    }

    final cards = <Widget>[];

    // Student's own internships first
    for (final si in studentInternships) {
      final statusLower = si.status.toLowerCase();
      final bool isActive = statusLower == 'active' || statusLower == 'in_progress';
      final bool isCompleted = statusLower == 'completed';
      cards.add(
        _InternCard(
          surfaceColor: surfaceColor,
          isDark: isDark,
          onTap: openInternships,
          icon: Icons.work_outline_rounded,
          iconColor: isActive ? _green : isCompleted ? _violet : _amber,
          title: si.title,
          subtitle: si.hiredCompany != null ? '${si.hiredCompany} · ${si.status}' : si.status,
          statusText: si.status,
          statusBg: isActive ? _greenLight : isCompleted ? _violetLight : _amberLight,
          statusColor: isActive ? _green : isCompleted ? _violet : _amber,
        ),
      );
    }

    // Public internship listings (up to 3)
    final publicSlice = publicList.take(3);
    for (final item in publicSlice) {
      final String slug = item['slug'] as String? ?? '';
      cards.add(
        _InternCard(
          surfaceColor: surfaceColor,
          isDark: isDark,
          onTap: slug.isNotEmpty
              ? () => Navigator.push(context, MaterialPageRoute(
                    builder: (_) => InternshipDetailPage(slug: slug)))
              : openInternships,
          icon: Icons.business_center_outlined,
          iconColor: _teal,
          title: item['title'] as String? ?? 'Untitled',
          subtitle: 'SPOC: ${item['spoc_name'] as String? ?? 'SashaInfinity'}',
          statusText: 'Open',
          statusBg: _greenLight,
          statusColor: _green,
        ),
      );
    }

    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 20),
      child: Column(children: cards),
    );
  }

  // ── Recent activity (timeline) ────────────────────────────────────────────
  Widget _buildRecentActivity(List<RecentActivity> activities, Color surfaceColor, bool isDark) {
    final items = [
      _Activity(_orange, Icons.play_circle_fill_rounded, 'Watched: REST API design patterns', 'Full Stack Development', '2h ago'),
      _Activity(_green, Icons.workspace_premium_rounded, 'Earned Web Foundations certificate', 'Completed with distinction', 'Yesterday'),
      _Activity(_violet, Icons.send_rounded, 'Applied — Frontend Intern at SashaInfinity', 'Application under review', '3 days ago'),
      // Blog section removed per design spec — kept here (commented) in case it returns.
      // _Activity(_amber, Icons.article_rounded, 'Read: Future of EdTech in India', 'SashaInfinity Blog', '5 days ago'),
    ];
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 20),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
        decoration: BoxDecoration(
          color: surfaceColor,
          borderRadius: BorderRadius.circular(20),
          border: Border.all(color: isDark ? Colors.white10 : _border),
          boxShadow: isDark ? null : [BoxShadow(color: _ink.withOpacity(0.04), blurRadius: 14, offset: const Offset(0, 5))],
        ),
        child: Column(
          children: [
            for (int i = 0; i < items.length; i++)
              _ActivityItem(activity: items[i], isLast: i == items.length - 1, isDark: isDark),
          ],
        ),
      ),
    );
  }

  Widget _buildSkeleton(BuildContext context, bool isDark) {
    return const SingleChildScrollView(
      padding: EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(height: 40),
          SkeletonLoader(width: 220, height: 34, borderRadius: 8),
          SizedBox(height: 10),
          SkeletonLoader(width: 140, height: 24, borderRadius: 8),
          SizedBox(height: 24),
          SkeletonLoader(width: double.infinity, height: 150, borderRadius: 22),
          SizedBox(height: 24),
          SkeletonLoader(width: double.infinity, height: 180, borderRadius: 20),
        ],
      ),
    );
  }
}

// ── Header (calm, no bright gradient) ───────────────────────────────────────
// "Good Morning" reads as the H1 in ink; the user's name is the H2 in the brand
// accent. Sits directly on the page background — no notifications, no avatar.
class _Header extends StatelessWidget {
  final User user;
  final Color textColor;
  const _Header({required this.user, required this.textColor});

  @override
  Widget build(BuildContext context) {
    final firstName = user.fullName.split(' ').first;
    return SafeArea(
      bottom: false,
      child: Padding(
        padding: const EdgeInsets.fromLTRB(20, 20, 20, 14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // H1 greeting (ink) + H2 name (brand accent). Emoji removed per spec.
            Text('Good Morning,',
                style: GoogleFonts.plusJakartaSans(
                    fontSize: 36, fontWeight: FontWeight.w700, letterSpacing: -0.8, height: 1.05, color: textColor)),
            const SizedBox(height: 2),
            Text(firstName,
                style: GoogleFonts.plusJakartaSans(
                    fontSize: 26, fontWeight: FontWeight.w600, letterSpacing: -0.4, color: _accent)),
          ],
        ),
      ),
    );
  }
}

// ── Progress card (clean, light) ────────────────────────────────────────────
class _ProgressCard extends StatelessWidget {
  final WeeklyGoal? goal;
  final Color surfaceColor;
  final bool isDark;
  const _ProgressCard({this.goal, required this.surfaceColor, required this.isDark});

  @override
  Widget build(BuildContext context) {
    final pct = (goal?.progressPercentage ?? 60).clamp(0, 100) / 100.0;
    final done = goal?.completedHours ?? 7.5;
    final target = goal?.goalHours ?? 12;
    final lessons = goal?.lessonsCompleted ?? 8;
    final ink = isDark ? Colors.white : _ink;

    return Padding(
      padding: const EdgeInsets.fromLTRB(20, 4, 20, 0),
      child: Container(
        padding: const EdgeInsets.all(18),
        decoration: BoxDecoration(
          color: surfaceColor,
          borderRadius: BorderRadius.circular(22),
          border: Border.all(color: isDark ? Colors.white10 : _border),
          boxShadow: isDark ? null : [BoxShadow(color: _ink.withOpacity(0.05), blurRadius: 18, offset: const Offset(0, 8))],
        ),
        child: Column(
          children: [
            Row(
              children: [
                _ProgressRing(progress: pct, size: 66, stroke: 7, color: _accent, trackColor: _accent.withOpacity(0.12), textColor: ink),
                const SizedBox(width: 16),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          const Icon(Icons.flag_rounded, size: 18, color: _accent),
                          const SizedBox(width: 6),
                          Text('Weekly progress',
                              style: GoogleFonts.plusJakartaSans(fontSize: 16, fontWeight: FontWeight.w700, color: ink)),
                        ],
                      ),
                      const SizedBox(height: 4),
                      Text('${_fmt(done)} of $target hrs learned this week',
                          style: GoogleFonts.inter(fontSize: 12.5, color: _textSecondary)),
                    ],
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            Divider(height: 1, color: isDark ? Colors.white10 : _border),
            const SizedBox(height: 14),
            Row(
              children: [
                _miniStat(Icons.menu_book_rounded, '$lessons', 'Lessons', ink),
                _miniDivider(isDark),
                _miniStat(Icons.schedule_rounded, _fmt(done), 'Hours', ink),
                _miniDivider(isDark),
                _miniStat(Icons.flag_circle_rounded, '$target', 'Goal', ink),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _miniStat(IconData icon, String value, String label, Color ink) => Expanded(
        child: Column(
          children: [
            Icon(icon, color: _accent, size: 19),
            const SizedBox(height: 5),
            Text(value, style: GoogleFonts.plusJakartaSans(fontSize: 16, fontWeight: FontWeight.w800, height: 1, color: ink)),
            const SizedBox(height: 2),
            Text(label, style: GoogleFonts.inter(fontSize: 10.5, color: _textSecondary)),
          ],
        ),
      );

  Widget _miniDivider(bool isDark) => Container(width: 1, height: 30, color: isDark ? Colors.white10 : _border);

  static String _fmt(double v) => v == v.roundToDouble() ? v.toInt().toString() : v.toStringAsFixed(1);
}

// White circular progress ring with a centered percentage; colours are themeable.
class _ProgressRing extends StatelessWidget {
  final double progress;
  final double size;
  final double stroke;
  final Color color;
  final Color trackColor;
  final Color? textColor;
  const _ProgressRing({
    required this.progress,
    required this.size,
    required this.stroke,
    this.color = Colors.white,
    this.trackColor = const Color(0x40FFFFFF),
    this.textColor,
  });

  @override
  Widget build(BuildContext context) {
    return TweenAnimationBuilder<double>(
      tween: Tween(begin: 0, end: progress),
      duration: const Duration(milliseconds: 1100),
      curve: Curves.easeOutCubic,
      builder: (_, v, __) => SizedBox(
        width: size,
        height: size,
        child: CustomPaint(
          painter: _RingPainter(progress: v, stroke: stroke, color: color, trackColor: trackColor),
          child: Center(
            child: Text('${(v * 100).round()}%',
                style: GoogleFonts.plusJakartaSans(fontSize: size * 0.24, fontWeight: FontWeight.w800, color: textColor ?? Colors.white)),
          ),
        ),
      ),
    );
  }
}

class _RingPainter extends CustomPainter {
  final double progress;
  final double stroke;
  final Color color;
  final Color trackColor;
  _RingPainter({required this.progress, required this.stroke, required this.color, required this.trackColor});

  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height / 2);
    final radius = (size.width - stroke) / 2;
    final track = Paint()
      ..color = trackColor
      ..style = PaintingStyle.stroke
      ..strokeWidth = stroke
      ..strokeCap = StrokeCap.round;
    final arc = Paint()
      ..color = color
      ..style = PaintingStyle.stroke
      ..strokeWidth = stroke
      ..strokeCap = StrokeCap.round;
    canvas.drawCircle(center, radius, track);
    canvas.drawArc(Rect.fromCircle(center: center, radius: radius), -math.pi / 2, 2 * math.pi * progress, false, arc);
  }

  @override
  bool shouldRepaint(_RingPainter old) => old.progress != progress || old.color != color;
}

// ── Press-scale wrapper ─────────────────────────────────────────────────────
class _Pressable extends StatefulWidget {
  final Widget child;
  final VoidCallback? onTap;
  final double scale;
  const _Pressable({required this.child, this.onTap, this.scale = 0.96});

  @override
  State<_Pressable> createState() => _PressableState();
}

class _PressableState extends State<_Pressable> {
  bool _down = false;
  void _set(bool v) {
    if (_down != v) setState(() => _down = v);
  }

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: widget.onTap,
      onTapDown: (_) => _set(true),
      onTapUp: (_) => _set(false),
      onTapCancel: () => _set(false),
      behavior: HitTestBehavior.opaque,
      child: AnimatedScale(
        scale: _down ? widget.scale : 1.0,
        duration: const Duration(milliseconds: 130),
        curve: Curves.easeOut,
        child: widget.child,
      ),
    );
  }
}

// ── Entrance animation ──────────────────────────────────────────────────────
class _FadeSlideIn extends StatefulWidget {
  final Widget child;
  final int delayMs;
  const _FadeSlideIn({required this.child, this.delayMs = 0});

  @override
  State<_FadeSlideIn> createState() => _FadeSlideInState();
}

class _FadeSlideInState extends State<_FadeSlideIn> with SingleTickerProviderStateMixin {
  late final AnimationController _controller = AnimationController(vsync: this, duration: const Duration(milliseconds: 500));
  late final Animation<double> _fade = CurvedAnimation(parent: _controller, curve: Curves.easeOut);
  late final Animation<Offset> _slide = Tween<Offset>(begin: const Offset(0, 0.08), end: Offset.zero).animate(CurvedAnimation(parent: _controller, curve: Curves.easeOutCubic));

  @override
  void initState() {
    super.initState();
    Future.delayed(Duration(milliseconds: widget.delayMs), () {
      if (mounted) _controller.forward();
    });
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return FadeTransition(opacity: _fade, child: SlideTransition(position: _slide, child: widget.child));
  }
}

// ── Pie segment model ───────────────────────────────────────────────────────
// `fraction` is a FIXED, decorative slice size — the pie just shows four uneven
// wedges (it is NOT driven by the numbers). `value`/`detail` carry the real,
// live numbers, which are shown in the callout cards. `corner` says which card
// the slice's leader arrow points to (0=TL, 1=TR, 2=BR, 3=BL).
class _PieSeg {
  final String label;
  final int value; // real number → shown in the callout card
  final double fraction; // fixed slice size (decorative, uneven)
  final Color color;
  final IconData icon;
  final String detail; // e.g. "3 active"
  final int corner;
  const _PieSeg({
    required this.label,
    required this.value,
    required this.fraction,
    required this.color,
    required this.icon,
    required this.detail,
    required this.corner,
  });
}

const double _twoPi = 2 * math.pi;

// Is angle `theta` inside the arc that starts at `start` and sweeps `sweep`?
bool _inArc(double theta, double start, double sweep) {
  var d = (theta - start) % _twoPi;
  if (d < 0) d += _twoPi;
  return d <= sweep + 1e-6;
}

// Shared geometry for the pie, so the painter and the hit-tester agree exactly.
class _PieGeom {
  final double cx, cy, rx, ry, depth;
  const _PieGeom(this.cx, this.cy, this.rx, this.ry, this.depth);

  factory _PieGeom.of(Size size) {
    const pad = 6.0;
    final depth = size.height * 0.14;
    final rx = math.min(size.width / 2 - pad, (size.height - depth) / 2 - pad);
    final ry = rx * 0.62;
    final usedH = 2 * ry + depth;
    final cx = size.width / 2;
    final cy = (size.height - usedH) / 2 + ry;
    return _PieGeom(cx, cy, rx, ry, depth);
  }
}

// ── Dashboard summary — interactive 3D pie + tappable legend + detail panel ──
class _DashboardSummary extends ConsumerStatefulWidget {
  final DashboardData data;
  final Color surfaceColor;
  final bool isDark;
  const _DashboardSummary({required this.data, required this.surfaceColor, required this.isDark});

  @override
  ConsumerState<_DashboardSummary> createState() => _DashboardSummaryState();
}

class _DashboardSummaryState extends ConsumerState<_DashboardSummary> {
  int? _selected;

  // Slices listed in DRAW order (clockwise from the top). Fractions are fixed &
  // uneven (decorative); each carries its real `value` + the corner its arrow
  // points to. Corners: 0=TL, 1=TR, 2=BR, 3=BL.
  List<_PieSeg> _buildSegments() {
    final stats = widget.data.stats;
    final inProgress = (stats.enrolledCourses - stats.completedCourses).clamp(0, 1 << 30).toInt();
    final completed = stats.completedCourses;
    final certificates = stats.certificates;
    final internships = widget.data.internships.length;
    return <_PieSeg>[
      _PieSeg(
          label: 'In progress',
          value: inProgress,
          fraction: 0.40,
          color: const Color(0xFFFFB22E),
          icon: Icons.play_circle_fill_rounded,
          detail: inProgress == 1 ? 'course active' : 'courses active',
          corner: 1),
      _PieSeg(
          label: 'Internships',
          value: internships,
          fraction: 0.20,
          color: const Color(0xFFFF6B4A),
          icon: Icons.business_center_rounded,
          detail: internships == 1 ? 'open role' : 'open roles',
          corner: 2),
      _PieSeg(
          label: 'Certificates',
          value: certificates,
          fraction: 0.15,
          color: const Color(0xFFA855F7),
          icon: Icons.workspace_premium_rounded,
          detail: 'earned',
          corner: 3),
      _PieSeg(
          label: 'Completed',
          value: completed,
          fraction: 0.25,
          color: const Color(0xFF5B7CFA),
          icon: Icons.check_circle_rounded,
          detail: 'courses done',
          corner: 0),
    ];
  }

  void _select(int i) {
    setState(() => _selected = _selected == i ? null : i);
  }

  // Drill into the live data behind a section (tapped from its card).
  void _openDetail(int i) {
    switch (i) {
      case 0: // In progress
      case 3: // Completed
        ref.read(scaffoldTabProvider.notifier).state = 1; // Courses tab
        break;
      case 1: // Internships
        Navigator.push(context, MaterialPageRoute(builder: (_) => const InternshipsPage()));
        break;
      case 2: // Certificates
        Navigator.push(context, MaterialPageRoute(builder: (_) => StudentReportPage(data: widget.data)));
        break;
    }
  }

  @override
  Widget build(BuildContext context) {
    final segments = _buildSegments();
    final isDark = widget.isDark;

    const stackH = 352.0;
    const pieW = 196.0;
    const pieH = 178.0;
    const cardH = 80.0;

    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 20),
      child: Container(
        width: double.infinity,
        padding: const EdgeInsets.fromLTRB(16, 18, 16, 14),
        decoration: BoxDecoration(
          color: widget.surfaceColor,
          borderRadius: BorderRadius.circular(20),
          border: Border.all(color: isDark ? Colors.white10 : _border),
          boxShadow: isDark ? null : [BoxShadow(color: _ink.withOpacity(0.05), blurRadius: 16, offset: const Offset(0, 7))],
        ),
        child: Column(
          children: [
            LayoutBuilder(
              builder: (context, constraints) {
                final w = constraints.maxWidth;
                final cardW = (w - 16) / 2;
                return SizedBox(
                  height: stackH,
                  child: Stack(
                    children: [
                      // Leader arrows pointing from each slice out to its card.
                      Positioned.fill(
                        child: CustomPaint(
                          painter: _ConnectorsPainter(
                            segments: segments,
                            selectedIndex: _selected,
                            pieW: pieW,
                            pieH: pieH,
                            cardW: cardW,
                            cardH: cardH,
                            isDark: isDark,
                          ),
                        ),
                      ),
                      // The interactive 3D pie, centred.
                      Align(
                        alignment: Alignment.center,
                        child: SizedBox(
                          width: pieW,
                          height: pieH,
                          child: _Pie3DChart(
                            segments: segments,
                            isDark: isDark,
                            selectedIndex: _selected,
                            onTapSlice: _select,
                          ),
                        ),
                      ),
                      // Four callout cards in the corners.
                      for (int i = 0; i < segments.length; i++)
                        _positionedCard(segments[i], i, cardW, cardH, stackH),
                    ],
                  ),
                );
              },
            ),
            const SizedBox(height: 6),
            Text(
              _selected == null ? 'Tap a slice to highlight · tap a card to open' : 'Tap the card to open',
              textAlign: TextAlign.center,
              style: GoogleFonts.inter(fontSize: 10.5, fontWeight: FontWeight.w500, color: _textTertiary),
            ),
          ],
        ),
      ),
    );
  }

  Widget _positionedCard(_PieSeg seg, int index, double cardW, double cardH, double stackH) {
    final card = _CalloutCard(
      seg: seg,
      isDark: widget.isDark,
      surfaceColor: widget.surfaceColor,
      selected: _selected == index,
      onTap: () {
        setState(() => _selected = index);
        _openDetail(index);
      },
    );
    switch (seg.corner) {
      case 0: // TL
        return Positioned(top: 0, left: 0, width: cardW, height: cardH, child: card);
      case 1: // TR
        return Positioned(top: 0, right: 0, width: cardW, height: cardH, child: card);
      case 2: // BR
        return Positioned(bottom: 0, right: 0, width: cardW, height: cardH, child: card);
      default: // 3 → BL
        return Positioned(bottom: 0, left: 0, width: cardW, height: cardH, child: card);
    }
  }
}

// ── Callout card (one of the four corners — shows the real number) ───────────
class _CalloutCard extends StatelessWidget {
  final _PieSeg seg;
  final bool isDark;
  final Color surfaceColor;
  final bool selected;
  final VoidCallback onTap;
  const _CalloutCard({required this.seg, required this.isDark, required this.surfaceColor, required this.selected, required this.onTap});

  @override
  Widget build(BuildContext context) {
    final ink = isDark ? Colors.white : _ink;
    return _Pressable(
      onTap: onTap,
      scale: 0.96,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 200),
        padding: const EdgeInsets.fromLTRB(10, 9, 8, 9),
        decoration: BoxDecoration(
          color: selected ? Color.alphaBlend(seg.color.withOpacity(isDark ? 0.20 : 0.08), surfaceColor) : surfaceColor,
          borderRadius: BorderRadius.circular(15),
          border: Border.all(color: selected ? seg.color.withOpacity(0.55) : (isDark ? Colors.white10 : _border)),
          boxShadow: isDark ? null : [BoxShadow(color: _ink.withOpacity(0.05), blurRadius: 12, offset: const Offset(0, 5))],
        ),
        child: Row(
          children: [
            Container(
              width: 32,
              height: 32,
              decoration: BoxDecoration(color: seg.color, borderRadius: BorderRadius.circular(10)),
              child: Icon(seg.icon, color: Colors.white, size: 17),
            ),
            const SizedBox(width: 9),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Text('${seg.value}',
                      style: GoogleFonts.plusJakartaSans(fontSize: 21, fontWeight: FontWeight.w800, height: 1, letterSpacing: -0.5, color: ink)),
                  const SizedBox(height: 2),
                  Text(seg.label,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: GoogleFonts.inter(fontSize: 11, fontWeight: FontWeight.w700, height: 1.1, color: ink)),
                  Text(seg.detail,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: GoogleFonts.inter(fontSize: 9.5, color: _textTertiary)),
                ],
              ),
            ),
            Icon(Icons.north_east_rounded, size: 15, color: seg.color),
          ],
        ),
      ),
    );
  }
}

// ── Leader arrows: pie slice → its callout card ──────────────────────────────
class _ConnectorsPainter extends CustomPainter {
  final List<_PieSeg> segments;
  final int? selectedIndex;
  final double pieW, pieH, cardW, cardH;
  final bool isDark;
  _ConnectorsPainter({
    required this.segments,
    required this.selectedIndex,
    required this.pieW,
    required this.pieH,
    required this.cardW,
    required this.cardH,
    required this.isDark,
  });

  void _arrow(Canvas c, Offset from, Offset to, Paint p) {
    c.drawLine(from, to, p);
    final ang = math.atan2(to.dy - from.dy, to.dx - from.dx);
    const ah = 7.0;
    c.drawLine(to, Offset(to.dx - ah * math.cos(ang - 0.5), to.dy - ah * math.sin(ang - 0.5)), p);
    c.drawLine(to, Offset(to.dx - ah * math.cos(ang + 0.5), to.dy - ah * math.sin(ang + 0.5)), p);
  }

  @override
  void paint(Canvas canvas, Size size) {
    final g = _PieGeom.of(Size(pieW, pieH));
    final boxOrigin = Offset((size.width - pieW) / 2, (size.height - pieH) / 2);
    final center = boxOrigin + Offset(g.cx, g.cy);

    // Anchor in the gap just outside each card, so the arrowhead stays visible
    // (cards are drawn on top) and clearly points at its card.
    Offset cardAnchor(int corner) {
      switch (corner) {
        case 0: // TL → just below the card
          return Offset(cardW * 0.72, cardH + 7);
        case 1: // TR → just below
          return Offset(size.width - cardW * 0.72, cardH + 7);
        case 2: // BR → just above
          return Offset(size.width - cardW * 0.72, size.height - cardH - 7);
        default: // 3 BL → just above
          return Offset(cardW * 0.72, size.height - cardH - 7);
      }
    }

    // Each arrow leaves the pie along a fixed diagonal toward its corner card,
    // so all four are symmetric (evenly aligned) regardless of slice size.
    double cornerAngle(int corner) {
      switch (corner) {
        case 0: // TL → up-left
          return -3 * math.pi / 4;
        case 1: // TR → up-right
          return -math.pi / 4;
        case 2: // BR → down-right
          return math.pi / 4;
        default: // 3 BL → down-left
          return 3 * math.pi / 4;
      }
    }

    for (int i = 0; i < segments.length; i++) {
      final seg = segments[i];
      final sel = selectedIndex == i;
      final a = cornerAngle(seg.corner);
      final edge = center + Offset(g.rx * math.cos(a) * 1.04, g.ry * math.sin(a) * 1.04 + g.depth * 0.4);
      final anchor = cardAnchor(seg.corner);

      final paint = Paint()
        ..color = sel ? seg.color : seg.color.withOpacity(0.45)
        ..strokeWidth = sel ? 2.4 : 1.5
        ..strokeCap = StrokeCap.round
        ..style = PaintingStyle.stroke;
      _arrow(canvas, edge, anchor, paint);
      // Small dot at the slice end.
      canvas.drawCircle(edge, sel ? 3.2 : 2.4, Paint()..color = sel ? seg.color : seg.color.withOpacity(0.55));
    }
  }

  @override
  bool shouldRepaint(_ConnectorsPainter old) =>
      old.selectedIndex != selectedIndex || old.cardW != cardW || old.isDark != isDark;
}

// ── Interactive 3D pie chart ─────────────────────────────────────────────────
// An extruded, tilted pie matching the reference infographic. Hand-painted so we
// can render real depth (the side walls) — fl_chart only does flat 2D pies. Each
// slice is a button: tap to explode it out (and the parent reveals its detail).
class _Pie3DChart extends StatefulWidget {
  final List<_PieSeg> segments;
  final bool isDark;
  final int? selectedIndex;
  final ValueChanged<int> onTapSlice;
  const _Pie3DChart({
    required this.segments,
    required this.isDark,
    required this.selectedIndex,
    required this.onTapSlice,
  });

  @override
  State<_Pie3DChart> createState() => _Pie3DChartState();
}

class _Pie3DChartState extends State<_Pie3DChart> with TickerProviderStateMixin {
  late final AnimationController _reveal = AnimationController(vsync: this, duration: const Duration(milliseconds: 1100))..forward();
  late final AnimationController _explode = AnimationController(vsync: this, duration: const Duration(milliseconds: 280));
  Size _size = Size.zero;

  @override
  void didUpdateWidget(covariant _Pie3DChart old) {
    super.didUpdateWidget(old);
    if (old.selectedIndex != widget.selectedIndex) {
      if (widget.selectedIndex != null) {
        _explode.forward(from: 0);
      } else {
        _explode.reverse();
      }
    }
  }

  @override
  void dispose() {
    _reveal.dispose();
    _explode.dispose();
    super.dispose();
  }

  // Map a tap to the slice under it (top face + the extruded front wall).
  void _handleTap(Offset local) {
    if (_size == Size.zero) return;
    final g = _PieGeom.of(_size);
    double start = -math.pi / 2;
    final ranges = <List<double>>[]; // [start, sweep]
    for (final seg in widget.segments) {
      final sweep = seg.fraction * _twoPi;
      ranges.add([start, sweep]);
      start += sweep;
    }
    // Probe the tap point and a copy lifted by `depth` (so taps on the side wall
    // resolve to the slice that owns that part of the rim).
    for (final probe in [local, local.translate(0, -g.depth)]) {
      final nx = (probe.dx - g.cx) / g.rx;
      final ny = (probe.dy - g.cy) / g.ry;
      if (nx * nx + ny * ny <= 1.0) {
        final th = math.atan2(ny, nx);
        for (int i = 0; i < ranges.length; i++) {
          if (ranges[i][1] > 0 && _inArc(th, ranges[i][0], ranges[i][1])) {
            widget.onTapSlice(i);
            return;
          }
        }
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        _size = Size(constraints.maxWidth, constraints.maxHeight);
        return GestureDetector(
          behavior: HitTestBehavior.opaque,
          onTapUp: (d) => _handleTap(d.localPosition),
          child: AnimatedBuilder(
            animation: Listenable.merge([_reveal, _explode]),
            builder: (_, __) => CustomPaint(
              size: Size.infinite,
              painter: _Pie3DPainter(
                segments: widget.segments,
                t: Curves.easeOutCubic.transform(_reveal.value),
                isDark: widget.isDark,
                selectedIndex: widget.selectedIndex,
                explode: Curves.easeOutBack.transform(_explode.value).clamp(0.0, 1.0),
              ),
            ),
          ),
        );
      },
    );
  }
}

class _Slice {
  final _PieSeg seg;
  final int index;
  final double start;
  final double sweep;
  _Slice(this.seg, this.index, this.start, this.sweep);
}

class _Pie3DPainter extends CustomPainter {
  final List<_PieSeg> segments;
  final double t; // 0..1 reveal animation
  final bool isDark;
  final int? selectedIndex;
  final double explode; // 0..1 pop-out of the selected slice
  _Pie3DPainter({
    required this.segments,
    required this.t,
    required this.isDark,
    required this.selectedIndex,
    required this.explode,
  });

  static const double _pop = 16.0; // max pixels a selected slice pops out

  Color _darken(Color c, [double f = 0.62]) =>
      Color.fromARGB(c.alpha, (c.red * f).round(), (c.green * f).round(), (c.blue * f).round());

  @override
  void paint(Canvas canvas, Size size) {
    final g = _PieGeom.of(size);
    final cx = g.cx, cy = g.cy, rx = g.rx, ry = g.ry, depth = g.depth;
    final rect = Rect.fromCenter(center: Offset(cx, cy), width: 2 * rx, height: 2 * ry);

    // Soft contact shadow grounding the pie.
    if (!isDark) {
      canvas.drawOval(
        Rect.fromCenter(center: Offset(cx, cy + depth + 4), width: 2 * rx * 0.92, height: 2 * ry * 0.5),
        Paint()
          ..color = Colors.black.withOpacity(0.10)
          ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 12),
      );
    }

    // Build animated slices from the FIXED fractions, top → clockwise.
    final slices = <_Slice>[];
    double start = -math.pi / 2;
    for (int i = 0; i < segments.length; i++) {
      final sweep = segments[i].fraction * _twoPi * t;
      slices.add(_Slice(segments[i], i, start, sweep));
      start += sweep;
    }

    // Per-slice pop-out offset (selected slice slides along its mid-angle).
    Offset offsetFor(_Slice s) {
      if (selectedIndex != s.index || explode <= 0) return Offset.zero;
      final full = segments[s.index].fraction * _twoPi;
      final mid = s.start + full / 2;
      return Offset(_pop * explode * math.cos(mid), _pop * explode * math.sin(mid) * (ry / rx));
    }

    Offset top(double th, Offset off) => Offset(cx + rx * math.cos(th) + off.dx, cy + ry * math.sin(th) + off.dy);

    // 1) Side walls — only the front-facing half of the rim (lower edge, sinθ>0).
    const wallSteps = 220;
    final wallPaint = Paint()..style = PaintingStyle.fill;
    for (int i = 0; i < wallSteps; i++) {
      final th0 = math.pi * i / wallSteps;
      final th1 = math.pi * (i + 1) / wallSteps;
      final mid = (th0 + th1) / 2;
      _Slice? owner;
      for (final s in slices) {
        if (s.sweep > 0 && _inArc(mid, s.start, s.sweep)) {
          owner = s;
          break;
        }
      }
      if (owner == null) continue;
      final off = offsetFor(owner);
      final a = top(th0, off), b = top(th1, off);
      final wall = Path()
        ..moveTo(a.dx, a.dy)
        ..lineTo(b.dx, b.dy)
        ..lineTo(b.dx, b.dy + depth)
        ..lineTo(a.dx, a.dy + depth)
        ..close();
      wallPaint.color = _darken(owner.seg.color);
      canvas.drawPath(wall, wallPaint);
    }

    // 2) Top faces (selected slice drawn last so it sits above its neighbours).
    final ordered = [...slices]..sort((a, b) => (a.index == selectedIndex ? 1 : 0).compareTo(b.index == selectedIndex ? 1 : 0));
    for (final s in ordered) {
      if (s.sweep <= 0) continue;
      final r = selectedIndex == s.index && explode > 0 ? rect.shift(offsetFor(s)) : rect;
      canvas.drawArc(r, s.start, s.sweep, true, Paint()
        ..color = s.seg.color
        ..style = PaintingStyle.fill);
      canvas.drawArc(r, s.start, s.sweep, true, Paint()
        ..color = Colors.white.withOpacity(0.55)
        ..style = PaintingStyle.stroke
        ..strokeWidth = 1.4);
    }
    // No on-slice percentage labels — the real numbers live in the callout cards.
  }

  @override
  bool shouldRepaint(_Pie3DPainter old) =>
      old.t != t || old.isDark != isDark || old.selectedIndex != selectedIndex || old.explode != explode;
}

// ── Course card (carousel item) ─────────────────────────────────────────────
class _CourseCard extends StatelessWidget {
  final DashboardCourse course;
  final Color surfaceColor;
  final bool isDark;
  final VoidCallback onResume;
  final double width;

  const _CourseCard({required this.course, required this.surfaceColor, required this.isDark, required this.onResume, this.width = 280.0});

  @override
  Widget build(BuildContext context) {
    Color tagBg = _orangeLight, tagCol = _orange;
    IconData tagIcon = Icons.code_rounded;
    String tagText = 'Tech';
    final t = course.title.toLowerCase();
    if (t.contains('full stack') || t.contains('web')) {
      tagBg = _orangeLight; tagCol = _orange; tagIcon = Icons.code_rounded; tagText = 'Full stack';
    } else if (t.contains('ai') || t.contains('machine')) {
      tagBg = _violetLight; tagCol = _violet; tagIcon = Icons.psychology_rounded; tagText = 'AI / ML';
    } else if (t.contains('cloud') || t.contains('devops')) {
      tagBg = _tealLight; tagCol = _teal; tagIcon = Icons.cloud_queue_rounded; tagText = 'Cloud';
    }

    final lessonsLeft = (course.totalLessons - course.completedLessons).clamp(0, course.totalLessons);

    return _Pressable(
      onTap: onResume,
      child: Container(
        width: width,
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: surfaceColor,
          borderRadius: BorderRadius.circular(20),
          border: Border.all(color: isDark ? Colors.white10 : _border),
          boxShadow: isDark ? null : [BoxShadow(color: _ink.withOpacity(0.05), blurRadius: 14, offset: const Offset(0, 6))],
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 4),
                  decoration: BoxDecoration(color: tagBg, borderRadius: BorderRadius.circular(20)),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(tagIcon, size: 11, color: tagCol),
                      const SizedBox(width: 4),
                      Text(tagText, style: GoogleFonts.inter(fontSize: 11, fontWeight: FontWeight.w600, color: tagCol)),
                    ],
                  ),
                ),
                const Spacer(),
                _MiniRing(progress: (course.progress / 100).clamp(0, 1).toDouble(), color: tagCol),
              ],
            ),
            const SizedBox(height: 12),
            // Reserve two lines for the title so the instructor and progress
            // rows line up across every card in the carousel, no matter whether
            // a title wraps to one line or two.
            SizedBox(
              height: 38,
              child: Text(course.title, maxLines: 2, overflow: TextOverflow.ellipsis, style: GoogleFonts.inter(fontSize: 14.5, fontWeight: FontWeight.w600, height: 1.3, color: isDark ? Colors.white : _ink)),
            ),
            const SizedBox(height: 5),
            Row(
              children: [
                Icon(Icons.account_circle_outlined, size: 14, color: _textSecondary),
                const SizedBox(width: 4),
                Expanded(child: Text(course.instructorName, maxLines: 1, overflow: TextOverflow.ellipsis, style: GoogleFonts.inter(fontSize: 12, color: _textSecondary))),
              ],
            ),
            const Spacer(),
            Row(
              children: [
                Icon(Icons.check_circle_outline_rounded, size: 13, color: _textTertiary),
                const SizedBox(width: 4),
                Text('${course.completedLessons}/${course.totalLessons} lessons', style: GoogleFonts.inter(fontSize: 11, color: _textTertiary)),
                const Spacer(),
                Text('$lessonsLeft left', style: GoogleFonts.inter(fontSize: 11, color: _textTertiary)),
              ],
            ),
            const SizedBox(height: 12),
            Container(
              width: double.infinity,
              padding: const EdgeInsets.symmetric(vertical: 10),
              decoration: BoxDecoration(color: tagCol, borderRadius: BorderRadius.circular(12)),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  const Icon(Icons.play_arrow_rounded, size: 16, color: Colors.white),
                  const SizedBox(width: 5),
                  Text('Resume lesson', style: GoogleFonts.inter(fontSize: 12.5, fontWeight: FontWeight.w700, color: Colors.white)),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _MiniRing extends StatelessWidget {
  final double progress;
  final Color color;
  const _MiniRing({required this.progress, required this.color});

  @override
  Widget build(BuildContext context) {
    return TweenAnimationBuilder<double>(
      tween: Tween(begin: 0, end: progress),
      duration: const Duration(milliseconds: 1000),
      curve: Curves.easeOutCubic,
      builder: (_, v, __) => SizedBox(
        width: 38,
        height: 38,
        child: CustomPaint(
          painter: _RingPainter(progress: v, stroke: 4, color: color, trackColor: color.withOpacity(0.15)),
          child: Center(child: Text('${(v * 100).round()}', style: GoogleFonts.inter(fontSize: 10.5, fontWeight: FontWeight.w700, color: color))),
        ),
      ),
    );
  }
}

// ── Internship card (neat, modern) ──────────────────────────────────────────
class _InternCard extends StatelessWidget {
  final Color surfaceColor;
  final bool isDark;
  final IconData icon;
  final Color iconColor;
  final String title;
  final String subtitle;
  final String statusText;
  final Color statusBg;
  final Color statusColor;
  final bool borderStatus;
  final VoidCallback? onTap;

  const _InternCard({required this.surfaceColor, required this.isDark, required this.icon, required this.iconColor, required this.title, required this.subtitle, required this.statusText, required this.statusBg, required this.statusColor, this.borderStatus = false, this.onTap});

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      behavior: HitTestBehavior.opaque,
      child: Container(
      margin: const EdgeInsets.only(bottom: 12),
      decoration: BoxDecoration(
        color: surfaceColor,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: isDark ? Colors.white10 : _border),
        boxShadow: isDark ? null : [BoxShadow(color: _ink.withOpacity(0.05), blurRadius: 16, offset: const Offset(0, 7))],
      ),
      clipBehavior: Clip.antiAlias,
      child: IntrinsicHeight(
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Container(width: 5, color: iconColor),
            Expanded(
              child: Padding(
                padding: const EdgeInsets.fromLTRB(13, 13, 12, 13),
                child: Row(
                  children: [
                    Container(
                      width: 48,
                      height: 48,
                      decoration: BoxDecoration(
                        // Vibrant gradient tile + white glyph (matches the
                        // callout cards) so each role reads colourful and lively
                        // instead of a flat pale tint.
                        gradient: LinearGradient(
                          begin: Alignment.topLeft,
                          end: Alignment.bottomRight,
                          colors: [
                            iconColor,
                            Color.alphaBlend(Colors.white.withOpacity(0.28), iconColor),
                          ],
                        ),
                        borderRadius: BorderRadius.circular(14),
                        boxShadow: [BoxShadow(color: iconColor.withOpacity(0.34), blurRadius: 10, offset: const Offset(0, 4))],
                      ),
                      child: Icon(icon, color: Colors.white, size: 24),
                    ),
                    const SizedBox(width: 13),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Text(title, style: GoogleFonts.inter(fontSize: 14.5, fontWeight: FontWeight.w600, color: isDark ? Colors.white : _ink), maxLines: 1, overflow: TextOverflow.ellipsis),
                          const SizedBox(height: 3),
                          Text(subtitle, maxLines: 1, overflow: TextOverflow.ellipsis, style: GoogleFonts.inter(fontSize: 11.5, color: _textSecondary)),
                          const SizedBox(height: 8),
                          Container(
                            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                            decoration: BoxDecoration(
                              color: statusBg,
                              borderRadius: BorderRadius.circular(20),
                              border: borderStatus ? Border.all(color: isDark ? Colors.white12 : _border) : null,
                            ),
                            child: Text(statusText.toUpperCase(), style: GoogleFonts.inter(fontSize: 9.5, fontWeight: FontWeight.w700, letterSpacing: 0.5, color: statusColor)),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(width: 6),
                    Icon(Icons.chevron_right_rounded, size: 20, color: _textTertiary),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
      ),
    );
  }
}

// ── Recent activity timeline ────────────────────────────────────────────────
class _Activity {
  final Color color;
  final IconData icon;
  final String title;
  final String subtitle;
  final String time;
  const _Activity(this.color, this.icon, this.title, this.subtitle, this.time);
}

class _ActivityItem extends StatelessWidget {
  final _Activity activity;
  final bool isLast;
  final bool isDark;

  const _ActivityItem({required this.activity, required this.isLast, required this.isDark});

  @override
  Widget build(BuildContext context) {
    return IntrinsicHeight(
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Column(
            children: [
              Container(
                width: 34,
                height: 34,
                decoration: BoxDecoration(color: activity.color.withOpacity(0.12), shape: BoxShape.circle),
                child: Icon(activity.icon, size: 17, color: activity.color),
              ),
              if (!isLast)
                Expanded(child: Container(width: 2, margin: const EdgeInsets.symmetric(vertical: 4), color: isDark ? Colors.white10 : _border)),
            ],
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Padding(
              padding: EdgeInsets.only(top: 2, bottom: isLast ? 12 : 18),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Expanded(child: Text(activity.title, style: GoogleFonts.inter(fontSize: 13, fontWeight: FontWeight.w600, height: 1.35, color: isDark ? Colors.white : _ink))),
                      const SizedBox(width: 8),
                      Text(activity.time, style: GoogleFonts.inter(fontSize: 11, color: _textTertiary)),
                    ],
                  ),
                  const SizedBox(height: 2),
                  Text(activity.subtitle, style: GoogleFonts.inter(fontSize: 11.5, color: _textSecondary)),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

// ── Quick action tile ───────────────────────────────────────────────────────
class _QuickAction {
  final IconData icon;
  final String label;
  final Color color;
  final Color bg;
  final VoidCallback onTap;
  const _QuickAction(this.icon, this.label, this.color, this.bg, this.onTap);
}

class _QuickActionTile extends StatelessWidget {
  final _QuickAction action;
  final Color surfaceColor;
  final bool isDark;
  const _QuickActionTile({required this.action, required this.surfaceColor, required this.isDark});

  @override
  Widget build(BuildContext context) {
    return _Pressable(
      onTap: action.onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 14, horizontal: 8),
        decoration: BoxDecoration(
          color: surfaceColor,
          borderRadius: BorderRadius.circular(18),
          border: Border.all(color: isDark ? Colors.white10 : _border),
          boxShadow: isDark ? null : [BoxShadow(color: _ink.withOpacity(0.04), blurRadius: 12, offset: const Offset(0, 4))],
        ),
        child: Column(
          children: [
            Container(
              width: 42,
              height: 42,
              decoration: BoxDecoration(
                color: isDark ? action.color.withOpacity(0.22) : action.bg,
                borderRadius: BorderRadius.circular(13),
              ),
              child: Icon(action.icon, color: action.color, size: 21),
            ),
            const SizedBox(height: 9),
            Text(
              action.label,
              textAlign: TextAlign.center,
              style: GoogleFonts.inter(
                fontSize: 11.5,
                height: 1.15,
                fontWeight: FontWeight.w600,
                color: isDark ? Colors.white : _ink,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

// ── Floating shapes (gentle background motion) ──────────────────────────────
// A few soft, blurred, low-opacity tinted blobs that drift slowly behind the
// dashboard — adds subtle "video-style" life without distracting.
class _FloatingShapes extends StatefulWidget {
  const _FloatingShapes();

  @override
  State<_FloatingShapes> createState() => _FloatingShapesState();
}

class _FloatingShapesState extends State<_FloatingShapes> with SingleTickerProviderStateMixin {
  late final AnimationController _controller = AnimationController(vsync: this, duration: const Duration(seconds: 20))..repeat();

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return IgnorePointer(child: CustomPaint(painter: _ShapesPainter(_controller), size: Size.infinite));
  }
}

class _ShapesPainter extends CustomPainter {
  final Animation<double> t;
  _ShapesPainter(this.t) : super(repaint: t);

  @override
  void paint(Canvas canvas, Size size) {
    final a = t.value * 2 * math.pi;
    void blob(double fx, double fy, double r, Color color, double phase) {
      final cx = size.width * fx + 16 * math.sin(a + phase);
      final cy = size.height * fy + 22 * math.cos(a * 0.8 + phase);
      canvas.drawCircle(
        Offset(cx, cy),
        r,
        Paint()
          ..color = color
          ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 22),
      );
    }

    blob(0.12, 0.08, 64, _orange.withOpacity(0.05), 0);
    blob(0.88, 0.26, 78, _teal.withOpacity(0.045), 1.2);
    blob(0.20, 0.60, 56, _violet.withOpacity(0.045), 2.1);
    blob(0.84, 0.82, 70, _amber.withOpacity(0.045), 3.0);
  }

  @override
  bool shouldRepaint(_ShapesPainter old) => false;
}
