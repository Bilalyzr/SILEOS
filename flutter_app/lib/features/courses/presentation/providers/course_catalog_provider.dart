import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/errors/failures.dart';
import '../../../../core/utils/failure_logger.dart';
import '../../domain/entities/course.dart';
import 'course_filter_providers.dart';
import 'course_provider.dart';

/// Number of courses fetched per request.
const int kCourseCatalogPageSize = 10;

/// Everything the catalog list needs to render, in one immutable value.
///
/// [courses] accumulates every page loaded so far for the current filters.
class CourseCatalogState {
  const CourseCatalogState({
    required this.courses,
    required this.total,
    required this.page,
    required this.totalPages,
    this.isLoadingMore = false,
    this.loadMoreError,
  });

  final List<Course> courses;

  /// Total number of courses matching the current filters on the server — not
  /// the number currently loaded. Pages beyond [courses] are not fetched yet.
  final int total;

  /// Highest page number successfully loaded.
  final int page;
  final int totalPages;

  /// True while a `loadMore` request is in flight. Kept in the data state rather
  /// than as an AsyncLoading so the already-loaded list stays on screen.
  final bool isLoadingMore;

  /// Set when the most recent `loadMore` failed. The loaded list is still valid,
  /// so this surfaces inline instead of replacing the page with an error view.
  final String? loadMoreError;

  bool get hasMore => page < totalPages;

  CourseCatalogState copyWith({
    List<Course>? courses,
    int? total,
    int? page,
    int? totalPages,
    bool? isLoadingMore,
    String? loadMoreError,
  }) {
    return CourseCatalogState(
      courses: courses ?? this.courses,
      total: total ?? this.total,
      page: page ?? this.page,
      totalPages: totalPages ?? this.totalPages,
      isLoadingMore: isLoadingMore ?? this.isLoadingMore,
      // Not `??` — passing null must be able to clear a previous error.
      loadMoreError: loadMoreError,
    );
  }
}

/// Owns the catalog's paginated list.
///
/// Filtering and sorting are delegated to the backend: applying them client-side
/// would only ever filter the pages already loaded, so a `beginner` filter would
/// hide most matches until the user had paged through the entire catalog.
///
/// [build] re-runs whenever [courseCatalogFiltersProvider] changes, which resets
/// the list to page 1 for free.
class CourseCatalogNotifier extends AutoDisposeAsyncNotifier<CourseCatalogState> {
  /// Riverpod 2.x has no `ref.mounted`, and touching `state` after disposal
  /// throws. Tracked manually so an in-flight `loadMore` can bail out.
  bool _disposed = false;

  @override
  Future<CourseCatalogState> build() async {
    _disposed = false;
    ref.onDispose(() => _disposed = true);

    final filters = ref.watch(courseCatalogFiltersProvider);
    return _fetchPage(1, filters);
  }

  Future<CourseCatalogState> _fetchPage(
    int page,
    CourseCatalogFilters filters,
  ) async {
    final result = await ref.read(getCoursesUseCaseProvider).call(
          page: page,
          pageSize: kCourseCatalogPageSize,
          category: filters.category,
          search: filters.search,
          level: filters.level,
          priceType: filters.priceType,
          sortBy: filters.sortBy,
        );

    return result.fold(
      (failure) {
        logFailure('courses page=$page', failure);
        throw failure;
      },
      (paginated) => CourseCatalogState(
        courses: paginated.courses,
        total: paginated.total,
        page: paginated.page,
        totalPages: paginated.totalPages,
      ),
    );
  }

  /// Appends the next page to the current list.
  ///
  /// Deliberately does not set an AsyncLoading state — that would tear the
  /// loaded list off screen and replace it with a skeleton on every tap.
  Future<void> loadMore() async {
    final current = state.valueOrNull;
    if (current == null || current.isLoadingMore || !current.hasMore) return;

    state = AsyncData(current.copyWith(isLoadingMore: true));

    final filters = ref.read(courseCatalogFiltersProvider);
    final nextPage = current.page + 1;
    final result = await ref.read(getCoursesUseCaseProvider).call(
          page: nextPage,
          pageSize: kCourseCatalogPageSize,
          category: filters.category,
          search: filters.search,
          level: filters.level,
          priceType: filters.priceType,
          sortBy: filters.sortBy,
        );

    if (_disposed) return;

    // A filter change mid-flight rebuilds the notifier and resets the list to
    // page 1, so this response now belongs to a query the user has moved on
    // from. Comparing filters (not just page numbers) is what makes this safe:
    // page 2 of "beginner" must never be appended to page 1 of "advanced".
    if (ref.read(courseCatalogFiltersProvider) != filters) return;

    final latest = state.valueOrNull;
    if (latest == null || latest.page != current.page) return;

    result.fold(
      (failure) {
        logFailure('courses loadMore page=$nextPage', failure);
        state = AsyncData(
          latest.copyWith(
            isLoadingMore: false,
            loadMoreError: _messageFor(failure),
          ),
        );
      },
      (paginated) {
        state = AsyncData(
          latest.copyWith(
            courses: [...latest.courses, ...paginated.courses],
            total: paginated.total,
            page: paginated.page,
            totalPages: paginated.totalPages,
            isLoadingMore: false,
          ),
        );
      },
    );
  }

  /// Discards every loaded page and refetches page 1 for the current filters.
  Future<void> refresh() async {
    final filters = ref.read(courseCatalogFiltersProvider);
    state = const AsyncLoading<CourseCatalogState>().copyWithPrevious(state);
    state = await AsyncValue.guard(() => _fetchPage(1, filters));
  }

  /// Short, user-facing text for the inline "load more" failure. The full
  /// diagnostic goes to logcat via [logFailure].
  String _messageFor(Failure failure) {
    return failure.when(
      server: (message, _) => message,
      network: (_) => 'No connection. Check your network and try again.',
      cache: (message) => message,
      unauthorized: (_) => 'Your session expired. Please sign in again.',
      forbidden: (_) => 'You do not have access to these courses.',
      notFound: (_) => 'Could not find more courses.',
      validation: (message, _) => message,
      unknown: (_) => 'Something went wrong loading more courses.',
    );
  }
}

final courseCatalogProvider =
    AsyncNotifierProvider.autoDispose<CourseCatalogNotifier, CourseCatalogState>(
  CourseCatalogNotifier.new,
);
