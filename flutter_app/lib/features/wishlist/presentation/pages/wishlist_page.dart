import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sashalms/core/network/network_provider.dart';
import 'package:sashalms/shared/widgets/common/error_display.dart';
import 'package:sashalms/shared/widgets/common/launching_soon.dart';
import 'package:sashalms/shared/widgets/common/skeleton_loader.dart';
import 'package:sashalms/features/courses/data/models/course_model.dart';
import 'package:sashalms/features/courses/domain/entities/course.dart';
import 'package:sashalms/features/courses/presentation/widgets/course_card.dart';

// Wishlist responses vary by backend: the data may be a bare list, or the rows
// may be wrapped in an object ({items|results|data|wishlist|courses: [...]}).
List<dynamic> _wishlistRows(dynamic body) {
  if (body is List) return body;
  if (body is Map) {
    for (final key in const ['items', 'results', 'data', 'wishlist', 'courses']) {
      final v = body[key];
      if (v is List) return v;
    }
  }
  return const [];
}

final wishlistProvider = FutureProvider<List<Course>>((ref) async {
  final client = ref.watch(apiClientProvider);
  final response = await client.get('/api/v1/wishlist/');

  // Parse defensively: each row may be a course or a {course: {...}} join row,
  // and a single malformed course shouldn't blank out the whole page.
  final courses = <Course>[];
  for (final row in _wishlistRows(response.data)) {
    if (row is! Map) continue;
    final courseJson = row['course'] ?? row;
    if (courseJson is! Map) continue;
    try {
      courses.add(CourseModel.fromJson(Map<String, dynamic>.from(courseJson)).toEntity());
    } catch (_) {
      // Skip rows whose course payload doesn't match the full course schema.
    }
  }
  return courses;
});

class WishlistPage extends ConsumerWidget {
  const WishlistPage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final wishlistAsync = ref.watch(wishlistProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('My Wishlist'),
      ),
      body: wishlistAsync.when(
        data: (courses) {
          if (courses.isEmpty) {
            return const LaunchingSoonWidget();
          }

          return ListView.builder(
            padding: const EdgeInsets.all(24),
            itemCount: courses.length,
            itemBuilder: (context, index) {
              return Padding(
                padding: const EdgeInsets.only(bottom: 16),
                child: CourseCard(course: courses[index]),
              );
            },
          );
        },
        loading: () => const SkeletonList(itemCount: 2),
        error: (err, stack) => ErrorDisplay(
          message: err.toString(),
          onRetry: () => ref.refresh(wishlistProvider),
        ),
      ),
    );
  }
}
