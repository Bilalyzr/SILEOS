/// Revenue for one calendar month, as returned by GET /api/v1/admin/revenue-monthly.
class MonthlyRevenuePoint {
  const MonthlyRevenuePoint({
    required this.month,
    required this.label,
    required this.fullLabel,
    required this.revenue,
    required this.courses,
    required this.internships,
  });

  /// "YYYY-MM".
  final String month;

  /// Short axis label, e.g. "Jul".
  final String label;

  /// Unambiguous label including the year, e.g. "Jul 2026".
  final String fullLabel;

  /// courses + internships.
  final double revenue;
  final double courses;
  final double internships;

  /// Parsed defensively: a malformed or missing field must not take down the
  /// whole dashboard, and money is never invented — absent means zero.
  factory MonthlyRevenuePoint.fromJson(Map<String, dynamic> json) {
    return MonthlyRevenuePoint(
      month: json['month'] as String? ?? '',
      label: json['label'] as String? ?? '',
      fullLabel: json['full_label'] as String? ?? json['label'] as String? ?? '',
      revenue: (json['revenue'] as num?)?.toDouble() ?? 0,
      courses: (json['courses'] as num?)?.toDouble() ?? 0,
      internships: (json['internships'] as num?)?.toDouble() ?? 0,
    );
  }
}

/// The admin Monthly Revenue payload: one point per calendar month, oldest
/// first, ending with the current (partial) month.
class MonthlyRevenue {
  const MonthlyRevenue({
    required this.currency,
    required this.total,
    required this.points,
    this.currentMonth,
    this.previousMonth,
    this.changePct,
  });

  final String currency;

  /// Sum of [points] — revenue across the whole window, not just this month.
  final double total;

  final List<MonthlyRevenuePoint> points;

  final MonthlyRevenuePoint? currentMonth;
  final MonthlyRevenuePoint? previousMonth;

  /// Percent change of [currentMonth] against [previousMonth].
  ///
  /// Null when there is no prior revenue to compare against — that is
  /// "undefined", not 0%, and the UI must not render it as flat.
  final double? changePct;

  /// True when every month in the window is zero. Distinguishes "no revenue
  /// yet" from "revenue we failed to load", which must read differently.
  bool get isEmpty => points.every((p) => p.revenue == 0);

  double get maxRevenue =>
      points.isEmpty ? 0 : points.map((p) => p.revenue).reduce((a, b) => a > b ? a : b);

  factory MonthlyRevenue.fromJson(Map<String, dynamic> json) {
    final rawPoints = (json['points'] as List?) ?? const [];
    final current = json['current_month'];
    final previous = json['previous_month'];

    return MonthlyRevenue(
      currency: json['currency'] as String? ?? 'INR',
      total: (json['total'] as num?)?.toDouble() ?? 0,
      points: rawPoints
          .whereType<Map>()
          .map((p) => MonthlyRevenuePoint.fromJson(Map<String, dynamic>.from(p)))
          .toList(),
      currentMonth: current is Map
          ? MonthlyRevenuePoint.fromJson(Map<String, dynamic>.from(current))
          : null,
      previousMonth: previous is Map
          ? MonthlyRevenuePoint.fromJson(Map<String, dynamic>.from(previous))
          : null,
      changePct: (json['change_pct'] as num?)?.toDouble(),
    );
  }
}
