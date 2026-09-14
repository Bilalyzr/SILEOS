import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sashalms/features/courses/domain/entities/course.dart';
import 'package:sashalms/features/courses/presentation/providers/course_provider.dart';

/// Derives a unique list of instructors from the public courses listing.
/// No dedicated backend endpoint is needed — we extract instructors from
/// the courses already fetched for the catalog.
final homeInstructorsProvider = FutureProvider<List<Instructor>>((ref) async {
  try {
    final paginated = await ref.watch(coursesProvider(page: 1, pageSize: 20).future);
    final seen = <String, Instructor>{};
    for (final course in paginated.courses) {
      final instructor = course.instructor;
      if (instructor.id.isNotEmpty &&
          instructor.name.isNotEmpty &&
          !seen.containsKey(instructor.id)) {
        seen[instructor.id] = instructor;
        if (seen.length >= 10) break; // cap at 10 for the horizontal scroll
      }
    }
    return seen.values.toList();
  } catch (_) {
    return []; // silently hide the section on error
  }
});
