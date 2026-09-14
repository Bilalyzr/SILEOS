import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';
import '../../../../core/network/network_provider.dart';
import '../../domain/entities/monthly_revenue.dart';

final adminRevenueMonthlyProvider =
    FutureProvider.autoDispose.family<MonthlyRevenue, int>((ref, months) async {
  final response = await ref.watch(apiClientProvider).get(
      '/api/v1/admin/revenue-timeseries',
      queryParameters: {'period': '1y'});
  return monthlyRevenueFromDaily(
      Map<String, dynamic>.from(response.data as Map), months);
});

/// Aggregate the existing IST daily order/voucher series, without inventing missing revenue.
MonthlyRevenue monthlyRevenueFromDaily(Map<String, dynamic> data, int months) {
  final daily = (data['points'] as List).cast<Map>();
  final buckets = <String, List<double>>{};
  for (final day in daily) {
    final month = (day['date'] as String).substring(0, 7);
    final sums = buckets.putIfAbsent(month, () => [0, 0]);
    sums[0] += (day['courses'] as num).toDouble();
    sums[1] += (day['internships'] as num).toDouble();
  }
  final keys = buckets.keys.toList()..sort();
  // A rolling year can include part of a thirteenth month. Omit that partial bucket.
  if (keys.length > 12) keys.removeAt(0);
  final selected =
      keys.skip((keys.length - months.clamp(1, 12)).clamp(0, keys.length));
  final points = selected.map((key) {
    final values = buckets[key]!;
    final date = DateTime.parse('$key-01');
    return MonthlyRevenuePoint(
        month: key,
        label: DateFormat('MMM').format(date),
        fullLabel: DateFormat('MMM yyyy').format(date),
        revenue: values[0] + values[1],
        courses: values[0],
        internships: values[1]);
  }).toList();
  final current = points.isEmpty ? null : points.last;
  final previous = points.length < 2 ? null : points[points.length - 2];
  return MonthlyRevenue(
      currency: 'INR',
      total: points.fold<double>(0, (sum, p) => sum + p.revenue),
      points: points,
      currentMonth: current,
      previousMonth: previous,
      changePct: previous == null || previous.revenue == 0 || current == null
          ? null
          : (current.revenue - previous.revenue) / previous.revenue * 100);
}
