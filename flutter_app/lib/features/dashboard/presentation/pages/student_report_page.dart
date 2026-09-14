// lib/features/dashboard/presentation/pages/student_report_page.dart
//
// "Full report" analytics screen for the student dashboard. Opened from the
// "Dashboard summary → Full report" action. Visualizes the student's real
// dashboard data (course completion, per-course progress, weekly learning)
// with fl_chart graphs.
import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import '../../domain/entities/dashboard_data.dart';

// Local palette — kept in sync with the dashboard's calm/neat tokens.
const Color _bg = Color(0xFFF6F5F4);
const Color _surface = Color(0xFFFFFFFF);
const Color _border = Color(0x0F1E293B);
const Color _ink = Color(0xFF1E293B);
const Color _textSecondary = Color(0xFF64748B);
const Color _accent = Color(0xFFEA580C); // orange-600
const Color _teal = Color(0xFF0D9488);
const Color _violet = Color(0xFF7C3AED);
const Color _amber = Color(0xFFB45309);

class StudentReportPage extends StatelessWidget {
  const StudentReportPage({super.key, required this.data});

  final DashboardData data;

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final bg = isDark ? Theme.of(context).colorScheme.surface : _bg;
    final surface = isDark ? const Color(0xFF1E293B) : _surface;
    final ink = isDark ? Colors.white : _ink;

    return Scaffold(
      backgroundColor: bg,
      appBar: AppBar(
        backgroundColor: bg,
        elevation: 0,
        foregroundColor: ink,
        title: Text(
          'Full report',
          style: GoogleFonts.plusJakartaSans(
            fontSize: 19,
            fontWeight: FontWeight.w700,
            color: ink,
          ),
        ),
      ),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(16, 8, 16, 32),
        children: [
          // At-a-glance headline — a plain-language summary of the results.
          _FadeSlideIn(
            delayMs: 0,
            child: Padding(
              padding: const EdgeInsets.fromLTRB(2, 2, 2, 0),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      const Icon(Icons.insights_rounded, size: 16, color: _accent),
                      const SizedBox(width: 6),
                      Text('AT A GLANCE',
                          style: GoogleFonts.inter(
                              fontSize: 11,
                              fontWeight: FontWeight.w700,
                              letterSpacing: 0.8,
                              color: _accent)),
                    ],
                  ),
                  const SizedBox(height: 6),
                  Text(_headline(),
                      style: GoogleFonts.inter(fontSize: 13.5, height: 1.5, color: ink)),
                ],
              ),
            ),
          ),
          const SizedBox(height: 16),
          _FadeSlideIn(delayMs: 80, child: _summaryChips(ink)),
          const SizedBox(height: 20),
          _FadeSlideIn(
            delayMs: 160,
            child: _ReportCard(
              surface: surface,
              isDark: isDark,
              title: 'Course completion',
              subtitle: 'How your enrolled courses break down',
              summary: _completionSummary(),
              child: _completionChart(ink),
            ),
          ),
          const SizedBox(height: 16),
          _FadeSlideIn(
            delayMs: 240,
            child: _ReportCard(
              surface: surface,
              isDark: isDark,
              title: 'Progress by course',
              subtitle: 'Completion % across your enrolled courses',
              summary: _progressSummary(),
              child: _courseProgressChart(ink),
            ),
          ),
          const SizedBox(height: 16),
          _FadeSlideIn(
            delayMs: 320,
            child: _ReportCard(
              surface: surface,
              isDark: isDark,
              title: 'This week',
              subtitle: 'Hours learned against your weekly goal',
              summary: _weeklySummary(),
              child: _weeklyChart(ink),
            ),
          ),
        ],
      ),
    );
  }

  // ── Summary chips ─────────────────────────────────────────────────────────
  Widget _summaryChips(Color ink) {
    final s = data.stats;
    final chips = [
      _Metric('Enrolled', '${s.enrolledCourses}', Icons.menu_book_rounded, _accent),
      _Metric('Completed', '${s.completedCourses}', Icons.verified_rounded, _teal),
      _Metric('Hours', '${s.totalHours}', Icons.schedule_rounded, _violet),
      _Metric('Certificates', '${s.certificates}', Icons.workspace_premium_rounded, _amber),
    ];
    return GridView.count(
      crossAxisCount: 2,
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      crossAxisSpacing: 12,
      mainAxisSpacing: 12,
      childAspectRatio: 2.6,
      children: chips
          .map((m) => Container(
                padding: const EdgeInsets.symmetric(horizontal: 14),
                decoration: BoxDecoration(
                  color: _surface,
                  borderRadius: BorderRadius.circular(16),
                  border: Border.all(color: _border),
                ),
                child: Row(
                  children: [
                    Container(
                      width: 38,
                      height: 38,
                      decoration: BoxDecoration(
                        color: m.color.withValues(alpha: 0.12),
                        shape: BoxShape.circle,
                      ),
                      child: Icon(m.icon, color: m.color, size: 19),
                    ),
                    const SizedBox(width: 10),
                    Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(m.value,
                            style: GoogleFonts.plusJakartaSans(
                                fontSize: 18, fontWeight: FontWeight.w800, height: 1, color: ink)),
                        const SizedBox(height: 2),
                        Text(m.label,
                            style: GoogleFonts.inter(fontSize: 11.5, color: _textSecondary)),
                      ],
                    ),
                  ],
                ),
              ))
          .toList(),
    );
  }

  // ── Completion donut ────────────────────────────────────────────────────--
  Widget _completionChart(Color ink) {
    final courses = data.enrolledCourses;
    if (courses.isEmpty) {
      return _emptyState('No enrolled courses to analyze yet.');
    }
    final completed = courses.where((c) => c.progress >= 100).length;
    final inProgress = courses.where((c) => c.progress > 0 && c.progress < 100).length;
    final notStarted = courses.where((c) => c.progress <= 0).length;

    final segments = <_Segment>[
      _Segment('Completed', completed, _teal),
      _Segment('In progress', inProgress, _accent),
      _Segment('Not started', notStarted, const Color(0xFFCBD5E1)),
    ].where((s) => s.value > 0).toList();

    return Row(
      children: [
        SizedBox(
          width: 140,
          height: 140,
          child: PieChart(
            PieChartData(
              sectionsSpace: 2,
              centerSpaceRadius: 38,
              sections: segments
                  .map((seg) => PieChartSectionData(
                        value: seg.value.toDouble(),
                        color: seg.color,
                        title: '${seg.value}',
                        radius: 30,
                        titleStyle: GoogleFonts.inter(
                            fontSize: 12, fontWeight: FontWeight.w800, color: Colors.white),
                      ))
                  .toList(),
            ),
          ),
        ),
        const SizedBox(width: 20),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: segments
                .map((seg) => Padding(
                      padding: const EdgeInsets.symmetric(vertical: 5),
                      child: Row(
                        children: [
                          Container(
                            width: 12,
                            height: 12,
                            decoration:
                                BoxDecoration(color: seg.color, borderRadius: BorderRadius.circular(3)),
                          ),
                          const SizedBox(width: 8),
                          Expanded(
                            child: Text(seg.label,
                                style: GoogleFonts.inter(fontSize: 13, color: ink)),
                          ),
                          Text('${seg.value}',
                              style: GoogleFonts.plusJakartaSans(
                                  fontSize: 13, fontWeight: FontWeight.w700, color: ink)),
                        ],
                      ),
                    ))
                .toList(),
          ),
        ),
      ],
    );
  }

  // ── Per-course progress bars ──────────────────────────────────────────────
  Widget _courseProgressChart(Color ink) {
    final courses = data.enrolledCourses.take(6).toList();
    if (courses.isEmpty) {
      return _emptyState('No enrolled courses to analyze yet.');
    }

    return Column(
      children: [
        SizedBox(
          height: 180,
          child: BarChart(
            BarChartData(
              maxY: 100,
              alignment: BarChartAlignment.spaceAround,
              gridData: FlGridData(
                show: true,
                drawVerticalLine: false,
                horizontalInterval: 25,
                getDrawingHorizontalLine: (_) =>
                    const FlLine(color: _border, strokeWidth: 1),
              ),
              borderData: FlBorderData(show: false),
              titlesData: FlTitlesData(
                topTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
                rightTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
                leftTitles: AxisTitles(
                  sideTitles: SideTitles(
                    showTitles: true,
                    reservedSize: 32,
                    interval: 25,
                    getTitlesWidget: (value, _) => Text('${value.toInt()}',
                        style: GoogleFonts.inter(fontSize: 10, color: _textSecondary)),
                  ),
                ),
                bottomTitles: AxisTitles(
                  sideTitles: SideTitles(
                    showTitles: true,
                    reservedSize: 22,
                    getTitlesWidget: (value, _) => Text('C${value.toInt() + 1}',
                        style: GoogleFonts.inter(fontSize: 11, color: _textSecondary)),
                  ),
                ),
              ),
              barTouchData: BarTouchData(
                touchTooltipData: BarTouchTooltipData(
                  getTooltipItem: (group, _, rod, __) => BarTooltipItem(
                    '${rod.toY.round()}%',
                    GoogleFonts.inter(
                        fontSize: 12, fontWeight: FontWeight.w700, color: Colors.white),
                  ),
                ),
              ),
              barGroups: [
                for (var i = 0; i < courses.length; i++)
                  BarChartGroupData(
                    x: i,
                    barRods: [
                      BarChartRodData(
                        toY: courses[i].progress.clamp(0, 100).toDouble(),
                        color: _accent,
                        width: 16,
                        borderRadius: const BorderRadius.vertical(top: Radius.circular(5)),
                        backDrawRodData: BackgroundBarChartRodData(
                          show: true,
                          toY: 100,
                          color: _accent.withValues(alpha: 0.08),
                        ),
                      ),
                    ],
                  ),
              ],
            ),
          ),
        ),
        const SizedBox(height: 14),
        // Legend mapping C1, C2 … to course titles + %.
        ...[
          for (var i = 0; i < courses.length; i++)
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 3),
              child: Row(
                children: [
                  Text('C${i + 1}',
                      style: GoogleFonts.plusJakartaSans(
                          fontSize: 12, fontWeight: FontWeight.w700, color: _accent)),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Text(courses[i].title,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: GoogleFonts.inter(fontSize: 12.5, color: ink)),
                  ),
                  Text('${courses[i].progress.round()}%',
                      style: GoogleFonts.inter(
                          fontSize: 12, fontWeight: FontWeight.w600, color: _textSecondary)),
                ],
              ),
            ),
        ],
      ],
    );
  }

  // ── Weekly learned vs goal ────────────────────────────────────────────────
  Widget _weeklyChart(Color ink) {
    final goal = data.weeklyGoal;
    if (goal == null) {
      return _emptyState('No weekly goal set yet.');
    }
    final learned = goal.completedHours;
    final target = goal.goalHours.toDouble();
    final maxY = (learned > target ? learned : target) * 1.2;

    return SizedBox(
      height: 180,
      child: BarChart(
        BarChartData(
          maxY: maxY <= 0 ? 1 : maxY,
          alignment: BarChartAlignment.spaceEvenly,
          gridData: FlGridData(
            show: true,
            drawVerticalLine: false,
            getDrawingHorizontalLine: (_) => const FlLine(color: _border, strokeWidth: 1),
          ),
          borderData: FlBorderData(show: false),
          titlesData: FlTitlesData(
            topTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
            rightTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
            leftTitles: AxisTitles(
              sideTitles: SideTitles(
                showTitles: true,
                reservedSize: 30,
                getTitlesWidget: (value, _) => Text('${value.toInt()}',
                    style: GoogleFonts.inter(fontSize: 10, color: _textSecondary)),
              ),
            ),
            bottomTitles: AxisTitles(
              sideTitles: SideTitles(
                showTitles: true,
                reservedSize: 24,
                getTitlesWidget: (value, _) => Padding(
                  padding: const EdgeInsets.only(top: 6),
                  child: Text(value.toInt() == 0 ? 'Learned' : 'Goal',
                      style: GoogleFonts.inter(fontSize: 12, color: _textSecondary)),
                ),
              ),
            ),
          ),
          barGroups: [
            BarChartGroupData(x: 0, barRods: [
              BarChartRodData(
                toY: learned,
                color: _accent,
                width: 46,
                borderRadius: const BorderRadius.vertical(top: Radius.circular(6)),
              ),
            ]),
            BarChartGroupData(x: 1, barRods: [
              BarChartRodData(
                toY: target,
                color: _teal,
                width: 46,
                borderRadius: const BorderRadius.vertical(top: Radius.circular(6)),
              ),
            ]),
          ],
        ),
      ),
    );
  }

  Widget _emptyState(String message) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 28),
        child: Center(
          child: Text(message,
              style: GoogleFonts.inter(fontSize: 13, color: _textSecondary)),
        ),
      );

  // ── Plain-language result summaries (the "what does this chart say") ─────────
  String _headline() {
    final s = data.stats;
    final certs = s.certificates > 0
        ? '  ·  ${s.certificates} certificate${s.certificates == 1 ? '' : 's'}'
        : '';
    return '${s.completedCourses} of ${s.enrolledCourses} courses completed'
        '$certs  ·  ${s.totalHours} hrs learned';
  }

  String _completionSummary() {
    final courses = data.enrolledCourses;
    if (courses.isEmpty) {
      return 'Enroll in a course to start tracking your completion.';
    }
    final completed = courses.where((c) => c.progress >= 100).length;
    final inProgress =
        courses.where((c) => c.progress > 0 && c.progress < 100).length;
    final pct = (completed / courses.length * 100).round();
    final tail = inProgress > 0 ? ' · $inProgress in progress' : '';
    return '$completed of ${courses.length} courses completed ($pct%)$tail.';
  }

  String _progressSummary() {
    final courses = data.enrolledCourses;
    if (courses.isEmpty) return 'No enrolled courses to measure yet.';
    final avg = (courses.map((c) => c.progress).reduce((a, b) => a + b) /
            courses.length)
        .round();
    final sorted = [...courses]..sort((a, b) => b.progress.compareTo(a.progress));
    final top = sorted.first;
    return 'Average completion $avg% · leading: ${top.title} (${top.progress.round()}%).';
  }

  String _weeklySummary() {
    final goal = data.weeklyGoal;
    if (goal == null) return 'Set a weekly goal to track your learning pace.';
    final pct = goal.goalHours <= 0
        ? 0
        : (goal.completedHours / goal.goalHours * 100).clamp(0, 999).round();
    final remaining =
        (goal.goalHours - goal.completedHours).clamp(0.0, goal.goalHours.toDouble());
    final tail = remaining <= 0
        ? ' · weekly goal reached!'
        : ' · ${_fmtHrs(remaining)} hrs to go';
    return '${_fmtHrs(goal.completedHours)} of ${goal.goalHours} hrs done ($pct% of goal)$tail.';
  }

  static String _fmtHrs(double v) =>
      v == v.roundToDouble() ? v.toInt().toString() : v.toStringAsFixed(1);
}

class _ReportCard extends StatelessWidget {
  const _ReportCard({
    required this.surface,
    required this.isDark,
    required this.title,
    required this.subtitle,
    required this.child,
    this.summary,
  });

  final Color surface;
  final bool isDark;
  final String title;
  final String subtitle;
  final Widget child;
  final String? summary;

  @override
  Widget build(BuildContext context) {
    final ink = isDark ? Colors.white : _ink;
    return Container(
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: surface,
        borderRadius: BorderRadius.circular(22),
        border: Border.all(color: isDark ? Colors.white10 : _border),
        boxShadow: isDark
            ? null
            : [BoxShadow(color: _ink.withValues(alpha: 0.05), blurRadius: 18, offset: const Offset(0, 8))],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(title,
              style: GoogleFonts.plusJakartaSans(
                  fontSize: 16, fontWeight: FontWeight.w700, color: ink)),
          const SizedBox(height: 2),
          Text(subtitle, style: GoogleFonts.inter(fontSize: 12.5, color: _textSecondary)),
          const SizedBox(height: 18),
          child,
          // Plain-language result summary under the chart.
          if (summary != null && summary!.trim().isNotEmpty) ...[
            const SizedBox(height: 16),
            _resultSummaryBox(summary!, isDark),
          ],
        ],
      ),
    );
  }
}

/// Highlighted one-line insight describing what the chart above shows.
Widget _resultSummaryBox(String text, bool isDark) {
  final ink = isDark ? Colors.white : _ink;
  return Container(
    width: double.infinity,
    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
    decoration: BoxDecoration(
      color: _accent.withValues(alpha: isDark ? 0.18 : 0.08),
      borderRadius: BorderRadius.circular(12),
      border: Border.all(color: _accent.withValues(alpha: 0.28)),
    ),
    child: Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Icon(Icons.trending_up_rounded, size: 16, color: _accent),
        const SizedBox(width: 8),
        Expanded(
          child: Text(text,
              style: GoogleFonts.inter(fontSize: 12.5, height: 1.45, color: ink)),
        ),
      ],
    ),
  );
}

class _Metric {
  const _Metric(this.label, this.value, this.icon, this.color);
  final String label;
  final String value;
  final IconData icon;
  final Color color;
}

class _Segment {
  const _Segment(this.label, this.value, this.color);
  final String label;
  final int value;
  final Color color;
}

/// Staggered fade + slide-in entrance for the report's sections, mirroring the
/// dashboard's _FadeSlideIn.
class _FadeSlideIn extends StatefulWidget {
  final Widget child;
  final int delayMs;
  const _FadeSlideIn({required this.child, this.delayMs = 0});

  @override
  State<_FadeSlideIn> createState() => _FadeSlideInState();
}

class _FadeSlideInState extends State<_FadeSlideIn>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller =
      AnimationController(vsync: this, duration: const Duration(milliseconds: 520));
  late final Animation<double> _fade =
      CurvedAnimation(parent: _controller, curve: Curves.easeOut);
  late final Animation<Offset> _slide = Tween<Offset>(
          begin: const Offset(0, 0.06), end: Offset.zero)
      .animate(CurvedAnimation(parent: _controller, curve: Curves.easeOutCubic));

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
  Widget build(BuildContext context) => FadeTransition(
      opacity: _fade,
      child: SlideTransition(position: _slide, child: widget.child));
}
