import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sashalms/config/theme.dart';
import 'package:sashalms/config/design_tokens.dart';
import '../../domain/entities/course.dart';
import '../providers/course_provider.dart';
import '../providers/course_filter_providers.dart';
import '../widgets/course_card.dart';
import '../../../../shared/widgets/common/error_display.dart';
import '../../../../shared/widgets/common/launching_soon.dart';
import '../../../../shared/widgets/common/skeleton_loader.dart';

class AllCoursesPage extends ConsumerStatefulWidget {
  const AllCoursesPage({super.key});

  @override
  ConsumerState<AllCoursesPage> createState() => _AllCoursesPageState();
}

class _AllCoursesPageState extends ConsumerState<AllCoursesPage> {
  int _currentPage = 1;
  final int _pageSize = 10;
  List<Course> _accumulatedCourses = [];
  bool _isLoadingMore = false;
  bool _hasMore = true;
  int _totalCourses = 0;

  // Selected filters
  String? _selectedLevel;
  String? _selectedPriceType; // 'free', 'paid'
  String? _selectedSortBy; // 'newest', 'popular', 'rating', 'price_asc', 'price_desc'

  final _searchController = TextEditingController();

  @override
  void initState() {
    super.initState();
    // Synchronize search query controller with provider
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final query = ref.read(catalogSearchQueryProvider);
      if (query != null) {
        _searchController.text = query;
      }
    });
  }

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  void _resetPagination() {
    setState(() {
      _currentPage = 1;
      _accumulatedCourses = [];
      _hasMore = true;
    });
  }

  void _clearAllFilters() {
    _searchController.clear();
    ref.read(catalogSearchQueryProvider.notifier).state = null;
    ref.read(selectedCategoryProvider.notifier).state = null;
    setState(() {
      _selectedLevel = null;
      _selectedPriceType = null;
      _selectedSortBy = null;
      _currentPage = 1;
      _accumulatedCourses = [];
      _hasMore = true;
    });
  }

  @override
  Widget build(BuildContext context) {
    ref.listen(selectedCategoryProvider, (previous, next) {
      if (previous != next) {
        _resetPagination();
      }
    });
    ref.listen(catalogSearchQueryProvider, (previous, next) {
      if (previous != next) {
        _resetPagination();
      }
    });

    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;

    final selectedCategory = ref.watch(selectedCategoryProvider);
    final searchQuery = ref.watch(catalogSearchQueryProvider);

    // Watch the paginated courses future provider
    final coursesAsync = ref.watch(coursesProvider(
      page: _currentPage,
      pageSize: _pageSize,
      category: selectedCategory,
      search: searchQuery,
    ));

    final muted = isDark ? AppTheme.mutedDark : AppTheme.mutedLight;

    return Scaffold(
      backgroundColor: isDark ? AppTheme.backgroundDark : AppNeutrals.slate50,
      appBar: AppBar(
        title: const Text('All Courses'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            tooltip: 'Clear Filters',
            onPressed: _clearAllFilters,
          ),
        ],
      ),
      body: Column(
        children: [
          // Header / Search & Filters Bar
          Container(
            padding: const EdgeInsets.fromLTRB(20, 8, 20, 16),
            decoration: BoxDecoration(
              color: isDark ? AppTheme.backgroundDark : Colors.white,
              border: Border(
                bottom: BorderSide(
                  color: isDark ? AppTheme.borderDark : AppTheme.borderLight,
                ),
              ),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Text(
                  'Explore courses',
                  style: theme.textTheme.headlineSmall?.copyWith(
                    fontWeight: FontWeight.w700,
                    letterSpacing: -0.4,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  'Learn from expert instructors at your own pace',
                  style: theme.textTheme.bodyMedium?.copyWith(color: muted),
                ),
                const SizedBox(height: 16),
                // Search field
                TextField(
                  controller: _searchController,
                  decoration: InputDecoration(
                    hintText: 'Search courses...',
                    prefixIcon: const Icon(Icons.search, size: 20),
                    suffixIcon: _searchController.text.isNotEmpty
                        ? IconButton(
                            icon: const Icon(Icons.clear, size: 18),
                            onPressed: () {
                              _searchController.clear();
                              ref.read(catalogSearchQueryProvider.notifier).state = null;
                              _resetPagination();
                            },
                          )
                        : null,
                    contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
                    border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                  ),
                  onChanged: (val) {
                    ref.read(catalogSearchQueryProvider.notifier).state = val.isEmpty ? null : val;
                    _resetPagination();
                  },
                ),
                const SizedBox(height: 12),

                // Filters selectors row
                SingleChildScrollView(
                  scrollDirection: Axis.horizontal,
                  child: Row(
                    children: [
                      // Category Filter Badge
                      if (selectedCategory != null)
                        Padding(
                          padding: const EdgeInsets.only(right: 8.0),
                          child: Chip(
                            label: Text(selectedCategory.toUpperCase()),
                            onDeleted: () {
                              ref.read(selectedCategoryProvider.notifier).state = null;
                              _resetPagination();
                            },
                            deleteIcon: const Icon(Icons.close, size: 14),
                          ),
                        ),

                      // Level Filter
                      _buildFilterDropdown(
                        value: _selectedLevel,
                        hint: 'Level',
                        items: ['beginner', 'intermediate', 'advanced'],
                        onChanged: (val) {
                          setState(() {
                            _selectedLevel = val;
                          });
                          _resetPagination();
                        },
                      ),
                      const SizedBox(width: 8),

                      // Price Filter
                      _buildFilterDropdown(
                        value: _selectedPriceType,
                        hint: 'Price',
                        items: ['free', 'paid'],
                        onChanged: (val) {
                          setState(() {
                            _selectedPriceType = val;
                          });
                          _resetPagination();
                        },
                      ),
                      const SizedBox(width: 8),

                      // Sort By Filter
                      _buildFilterDropdown(
                        value: _selectedSortBy,
                        hint: 'Sort By',
                        items: ['newest', 'popular', 'rating', 'price_asc', 'price_desc'],
                        onChanged: (val) {
                          setState(() {
                            _selectedSortBy = val;
                          });
                          _resetPagination();
                        },
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),

          // Catalog Content list
          Expanded(
            child: coursesAsync.when(
              data: (paginatedData) {
                // On page 1 always replace the accumulated list, so a
                // provider refresh (pull-to-refresh, retry) shows fresh data
                // instead of the previously accumulated stale list.
                if (_currentPage == 1) {
                  _accumulatedCourses = List.from(paginatedData.courses);
                  _totalCourses = paginatedData.total;
                  _hasMore = _currentPage < paginatedData.totalPages;
                }

                // Client-side filtering fallback for Level, PriceType & Sorting
                List<Course> displayCourses = List.from(_accumulatedCourses);
                
                if (_selectedLevel != null) {
                  displayCourses = displayCourses
                      .where((c) => c.level.toLowerCase() == _selectedLevel)
                      .toList();
                }

                if (_selectedPriceType != null) {
                  if (_selectedPriceType == 'free') {
                    displayCourses = displayCourses.where((c) => c.price == 0).toList();
                  } else {
                    displayCourses = displayCourses.where((c) => c.price > 0).toList();
                  }
                }

                if (_selectedSortBy != null) {
                  switch (_selectedSortBy) {
                    case 'newest':
                      displayCourses.sort((a, b) => b.createdAt.compareTo(a.createdAt));
                      break;
                    case 'popular':
                      displayCourses.sort((a, b) => b.stats.students.compareTo(a.stats.students));
                      break;
                    case 'rating':
                      displayCourses.sort((a, b) => b.rating.compareTo(a.rating));
                      break;
                    case 'price_asc':
                      displayCourses.sort((a, b) => a.price.compareTo(b.price));
                      break;
                    case 'price_desc':
                      displayCourses.sort((a, b) => b.price.compareTo(a.price));
                      break;
                  }
                }

                 if (displayCourses.isEmpty) {
                  return const LaunchingSoonWidget();
                }

                return Column(
                  children: [
                    // Statistics line
                    Padding(
                      padding: const EdgeInsets.fromLTRB(20, 14, 20, 6),
                      child: Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          Text(
                            'Showing ${displayCourses.length} of $_totalCourses courses',
                            style: theme.textTheme.bodySmall?.copyWith(color: muted),
                          ),
                          if (selectedCategory != null ||
                              searchQuery != null ||
                              _selectedLevel != null ||
                              _selectedPriceType != null ||
                              _selectedSortBy != null)
                            GestureDetector(
                              onTap: _clearAllFilters,
                              child: const Text(
                                'Clear Filters',
                                style: TextStyle(
                                  color: AppTheme.primary,
                                  fontSize: 12,
                                  fontWeight: FontWeight.bold,
                                ),
                              ),
                            )
                        ],
                      ),
                    ),

                    Expanded(
                      child: RefreshIndicator(
                        onRefresh: () async {
                          _resetPagination();
                          ref.invalidate(coursesProvider);
                          await ref.read(coursesProvider(
                            page: 1,
                            pageSize: _pageSize,
                            category: selectedCategory,
                            search: searchQuery,
                          ).future);
                        },
                        child: ListView.builder(
                        physics: const AlwaysScrollableScrollPhysics(),
                        padding: const EdgeInsets.fromLTRB(20, 6, 20, 24),
                        itemCount: displayCourses.length + (_hasMore ? 1 : 0),
                        itemBuilder: (context, index) {
                          if (index == displayCourses.length) {
                            // "Load More" indicator button
                            return Padding(
                              padding: const EdgeInsets.symmetric(vertical: 24),
                              child: _isLoadingMore
                                  ? const Center(child: CircularProgressIndicator())
                                  : Center(
                                      child: OutlinedButton(
                                        onPressed: () => _loadNextPage(selectedCategory, searchQuery),
                                        style: OutlinedButton.styleFrom(
                                          padding: const EdgeInsets.symmetric(horizontal: 32, vertical: 12),
                                          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                                        ),
                                        child: const Text('Load More Courses'),
                                      ),
                                    ),
                            );
                          }

                          return Padding(
                            padding: const EdgeInsets.only(bottom: 16),
                            child: CourseCard(course: displayCourses[index]),
                          );
                        },
                        ),
                      ),
                    ),
                  ],
                );
              },
              loading: () => const SkeletonList(itemCount: 2),
              error: (error, stack) => ErrorDisplay(
                message: error.toString(),
                onRetry: () => ref.refresh(coursesProvider(
                  page: _currentPage,
                  pageSize: _pageSize,
                  category: selectedCategory,
                  search: searchQuery,
                )),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Future<void> _loadNextPage(String? category, String? search) async {
    if (_isLoadingMore) return;
    setState(() {
      _isLoadingMore = true;
    });

    final nextPage = _currentPage + 1;
    final repository = ref.read(courseRepositoryProvider);
    final result = await repository.getCourses(
      page: nextPage,
      pageSize: _pageSize,
      category: category,
      search: search,
    );

    result.fold(
      (failure) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Failed to load more: ${failure.toString()}')),
        );
      },
      (paginated) {
        setState(() {
          _currentPage = nextPage;
          _accumulatedCourses.addAll(paginated.courses);
          _hasMore = _currentPage < paginated.totalPages;
        });
      },
    );

    setState(() {
      _isLoadingMore = false;
    });
  }

  Widget _buildFilterDropdown({
    required String? value,
    required String hint,
    required List<String> items,
    required ValueChanged<String?> onChanged,
  }) {
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 2),
      decoration: BoxDecoration(
        color: isDark ? AppTheme.surfaceDark : Colors.white,
        borderRadius: BorderRadius.circular(AppRadius.md),
        border: Border.all(
          color: isDark ? AppTheme.borderDark : AppTheme.borderLight,
        ),
      ),
      child: DropdownButtonHideUnderline(
        child: DropdownButton<String>(
          value: value,
          hint: Text(
            hint,
            style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600),
          ),
          onChanged: onChanged,
          icon: const Icon(Icons.arrow_drop_down, size: 18),
          style: theme.textTheme.bodyMedium?.copyWith(fontSize: 12),
          dropdownColor: isDark ? AppTheme.surfaceDark : Colors.white,
          items: [
            DropdownMenuItem<String>(
              value: null,
              child: Text('All ${hint}s'),
            ),
            ...items.map(
              (item) => DropdownMenuItem<String>(
                value: item,
                child: Text(item.toUpperCase()),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
