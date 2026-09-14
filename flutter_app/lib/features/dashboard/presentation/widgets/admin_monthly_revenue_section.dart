// lib/features/dashboard/presentation/widgets/admin_monthly_revenue_section.dart
import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:intl/intl.dart';

import '../../domain/entities/monthly_revenue.dart';
import '../providers/monthly_revenue_provider.dart';
import 'role_dashboard_common.dart';

const _accent = Color(0xFF1E40AF);
const _internAccent = Color(0xFF0891B2);
const _positive = Color(0xFF059669);
const _negative = Color(0xFFDC2626);

/// Monthly Revenue for the admin dashboard: a summary card for the current
/// month plus a bar chart of the trailing [months] calendar months.
///
/// Revenue figures are only ever rendered from the API. When the request fails
/// the section says so — it never falls back to placeholder numbers, because a
/// plausible-looking wrong revenue figure is worse than a visible error.
class AdminMonthlyRevenueSection extends ConsumerWidget {
  const AdminMonthlyRevenueSection({super.key, this.months = 12});

  final int months;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final revenueAsync = ref.watch(adminRevenueMonthlyProvider(months));

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const RoleDashboardSectionTitle('Monthly Revenue'),
        const SizedBox(height: 12),
        revenueAsync.when(
          data: (revenue) => _RevenueContent(revenue: revenue, months: months),
          loading: () => const RoleDashboardCard(
            child: SizedBox(
              height: 220,
              child: Center(child: CircularProgressIndicator()),
            ),
          ),
          error: (err, _) => RoleDashboardCard(
            child: _RevenueError(
              onRetry: () =>
                  ref.invalidate(adminRevenueMonthlyProvider(months)),
            ),
          ),
        ),
      ],
    );
  }
}

class _RevenueContent extends StatelessWidget {
  const _RevenueContent({required this.revenue, required this.months});

  final MonthlyRevenue revenue;
  final int months;

  @override
  Widget build(BuildContext context) {
    final current = revenue.currentMonth;

    return Column(
      children: [
        RoleDashboardCard(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                current != null ? 'This month · ${current.fullLabel}' : 'This month',
                style: GoogleFonts.plusJakartaSans(
                  fontSize: 12,
                  color: Colors.grey.shade600,
                ),
              ),
              const SizedBox(height: 6),
              Row(
                crossAxisAlignment: CrossAxisAlignment.center,
                children: [
                  Text(
                    _formatCurrency(current?.revenue ?? 0),
                    style: GoogleFonts.plusJakartaSans(
                      fontSize: 28,
                      fontWeight: FontWeight.bold,
                      letterSpacing: -0.5,
                    ),
                  ),
                  const SizedBox(width: 10),
                  _ChangeBadge(changePct: revenue.changePct),
                ],
              ),
              const SizedBox(height: 14),
              const Divider(height: 1),
              const SizedBox(height: 14),
              Row(
                children: [
                  Expanded(
                    child: _Breakdown(
                      label: 'Courses',
                      value: _formatCurrency(current?.courses ?? 0),
                      color: _accent,
                    ),
                  ),
                  Expanded(
                    child: _Breakdown(
                      label: 'Internships',
                      value: _formatCurrency(current?.internships ?? 0),
                      color: _internAccent,
                    ),
                  ),
                  Expanded(
                    child: _Breakdown(
                      label: 'Last $months mo',
                      value: _formatCurrency(revenue.total),
                      color: Colors.grey.shade500,
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
        const SizedBox(height: 12),
        RoleDashboardCard(
          title: 'Revenue by month',
          trailing: Text(
            revenue.currency,
            style: GoogleFonts.plusJakartaSans(
              fontSize: 11,
              color: Colors.grey.shade600,
            ),
          ),
          // An all-zero window still charts: real months with real zeros is an
          // honest flat line, and never an invented curve. Only a genuinely
          // empty payload has nothing to draw.
          child: revenue.points.isEmpty
              ? _emptyChartMessage('No revenue data available yet.')
              : _MonthlyRevenueChart(revenue: revenue),
        ),
      ],
    );
  }

  Widget _emptyChartMessage(String message) {
    return SizedBox(
      height: 120,
      child: Center(
        child: Text(
          message,
          style: GoogleFonts.plusJakartaSans(
            fontSize: 12,
            color: Colors.grey.shade600,
          ),
        ),
      ),
    );
  }
}

class _MonthlyRevenueChart extends StatelessWidget {
  const _MonthlyRevenueChart({required this.revenue});

  final MonthlyRevenue revenue;

  @override
  Widget build(BuildContext context) {
    final points = revenue.points;
    // An all-zero window would give maxY = 0, which makes fl_chart's interval
    // maths divide by zero. Fall back to a nominal axis so the flat line renders.
    final maxRevenue = revenue.maxRevenue;
    final maxY = maxRevenue > 0 ? maxRevenue * 1.2 : 100.0;

    return Column(
      children: [
        SizedBox(
          height: 190,
          child: BarChart(
            BarChartData(
              maxY: maxY,
              alignment: BarChartAlignment.spaceAround,
              gridData: FlGridData(
                show: true,
                drawVerticalLine: false,
                horizontalInterval: maxY / 4,
                getDrawingHorizontalLine: (_) => FlLine(
                  color: Theme.of(context).dividerColor.withValues(alpha: 0.5),
                  strokeWidth: 1,
                ),
              ),
              borderData: FlBorderData(show: false),
              titlesData: FlTitlesData(
                topTitles:
                    const AxisTitles(sideTitles: SideTitles(showTitles: false)),
                rightTitles:
                    const AxisTitles(sideTitles: SideTitles(showTitles: false)),
                leftTitles: AxisTitles(
                  sideTitles: SideTitles(
                    showTitles: true,
                    reservedSize: 44,
                    interval: maxY / 4,
                    getTitlesWidget: (value, _) => Text(
                      _formatCompact(value),
                      style: GoogleFonts.inter(
                        fontSize: 10,
                        color: Colors.grey.shade600,
                      ),
                    ),
                  ),
                ),
                bottomTitles: AxisTitles(
                  sideTitles: SideTitles(
                    showTitles: true,
                    reservedSize: 22,
                    getTitlesWidget: (value, _) {
                      final i = value.toInt();
                      if (i < 0 || i >= points.length) {
                        return const SizedBox.shrink();
                      }
                      // With 12+ bars every label would overlap on a phone.
                      final showEvery = points.length > 8 ? 2 : 1;
                      if (i % showEvery != 0 && i != points.length - 1) {
                        return const SizedBox.shrink();
                      }
                      return Padding(
                        padding: const EdgeInsets.only(top: 4),
                        child: Text(
                          points[i].label,
                          style: GoogleFonts.inter(
                            fontSize: 10,
                            color: Colors.grey.shade600,
                          ),
                        ),
                      );
                    },
                  ),
                ),
              ),
              barTouchData: BarTouchData(
                touchTooltipData: BarTouchTooltipData(
                  getTooltipItem: (group, _, rod, __) {
                    final p = points[group.x];
                    return BarTooltipItem(
                      '${p.fullLabel}\n${_formatCurrency(p.revenue)}',
                      GoogleFonts.inter(
                        fontSize: 12,
                        fontWeight: FontWeight.w700,
                        color: Colors.white,
                      ),
                    );
                  },
                ),
              ),
              barGroups: [
                for (var i = 0; i < points.length; i++)
                  BarChartGroupData(
                    x: i,
                    barRods: [
                      BarChartRodData(
                        toY: points[i].revenue,
                        // The current month is still accruing, so it is drawn
                        // muted — comparing it like a closed month misleads.
                        color: i == points.length - 1
                            ? _accent.withValues(alpha: 0.55)
                            : _accent,
                        width: points.length > 8 ? 10 : 16,
                        borderRadius: const BorderRadius.vertical(
                          top: Radius.circular(4),
                        ),
                        backDrawRodData: BackgroundBarChartRodData(
                          show: true,
                          toY: maxY,
                          color: _accent.withValues(alpha: 0.06),
                        ),
                      ),
                    ],
                  ),
              ],
            ),
          ),
        ),
        const SizedBox(height: 10),
        Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            _LegendDot(color: _accent, label: 'Closed months'),
            const SizedBox(width: 16),
            _LegendDot(
              color: _accent.withValues(alpha: 0.55),
              label: 'Current month (in progress)',
            ),
          ],
        ),
      ],
    );
  }
}

class _LegendDot extends StatelessWidget {
  const _LegendDot({required this.color, required this.label});

  final Color color;
  final String label;

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          width: 8,
          height: 8,
          decoration: BoxDecoration(color: color, shape: BoxShape.circle),
        ),
        const SizedBox(width: 6),
        Text(
          label,
          style: GoogleFonts.inter(fontSize: 10, color: Colors.grey.shade600),
        ),
      ],
    );
  }
}

class _Breakdown extends StatelessWidget {
  const _Breakdown({
    required this.label,
    required this.value,
    required this.color,
  });

  final String label;
  final String value;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Container(
              width: 8,
              height: 8,
              decoration: BoxDecoration(color: color, shape: BoxShape.circle),
            ),
            const SizedBox(width: 6),
            Flexible(
              child: Text(
                label,
                overflow: TextOverflow.ellipsis,
                style: GoogleFonts.plusJakartaSans(
                  fontSize: 11,
                  color: Colors.grey.shade600,
                ),
              ),
            ),
          ],
        ),
        const SizedBox(height: 4),
        Text(
          value,
          style: GoogleFonts.plusJakartaSans(
            fontSize: 14,
            fontWeight: FontWeight.w600,
          ),
        ),
      ],
    );
  }
}

class _ChangeBadge extends StatelessWidget {
  const _ChangeBadge({required this.changePct});

  final double? changePct;

  @override
  Widget build(BuildContext context) {
    // Null means there was no revenue last month to compare against. Showing
    // "0%" there would claim flat performance that the data does not support.
    if (changePct == null) {
      return Text(
        'vs last month —',
        style: GoogleFonts.plusJakartaSans(
          fontSize: 11,
          color: Colors.grey.shade600,
        ),
      );
    }

    final up = changePct! >= 0;
    final color = up ? _positive : _negative;

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(20),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(
            up ? Icons.arrow_upward : Icons.arrow_downward,
            size: 12,
            color: color,
          ),
          const SizedBox(width: 2),
          Text(
            '${changePct!.abs().toStringAsFixed(1)}%',
            style: GoogleFonts.plusJakartaSans(
              fontSize: 11,
              fontWeight: FontWeight.w700,
              color: color,
            ),
          ),
        ],
      ),
    );
  }
}

class _RevenueError extends StatelessWidget {
  const _RevenueError({required this.onRetry});

  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Icon(Icons.show_chart, size: 32, color: Colors.grey.shade400),
        const SizedBox(height: 8),
        Text(
          'Could not load revenue',
          style: GoogleFonts.plusJakartaSans(
            fontSize: 13,
            fontWeight: FontWeight.w600,
          ),
        ),
        const SizedBox(height: 4),
        Text(
          'Revenue figures are unavailable right now.',
          textAlign: TextAlign.center,
          style: GoogleFonts.plusJakartaSans(
            fontSize: 11,
            color: Colors.grey.shade600,
          ),
        ),
        const SizedBox(height: 10),
        OutlinedButton(onPressed: onRetry, child: const Text('Retry')),
      ],
    );
  }
}

final _currencyFormat = NumberFormat.currency(
  locale: 'en_IN',
  symbol: '₹',
  decimalDigits: 0,
);

String _formatCurrency(double value) => _currencyFormat.format(value);

/// Compact axis labels — full rupee amounts do not fit a phone-width y-axis.
String _formatCompact(double value) {
  if (value >= 10000000) return '₹${(value / 10000000).toStringAsFixed(1)}Cr';
  if (value >= 100000) return '₹${(value / 100000).toStringAsFixed(1)}L';
  if (value >= 1000) return '₹${(value / 1000).toStringAsFixed(0)}K';
  return '₹${value.toStringAsFixed(0)}';
}
