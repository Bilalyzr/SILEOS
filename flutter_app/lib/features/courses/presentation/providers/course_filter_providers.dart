import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Provider to manage the selected tab index of the main scaffold (0 = Home, 1 = Catalog, 2 = Dashboard, 3 = Profile).
final scaffoldTabProvider = StateProvider<int>((ref) => 0);

/// Provider to manage the selected category filter for the course catalog.
final selectedCategoryProvider = StateProvider<String?>((ref) => null);

/// Provider to manage the search query for the course catalog.
final catalogSearchQueryProvider = StateProvider<String?>((ref) => null);

class CourseCatalogFilters {
  const CourseCatalogFilters({this.category, this.search, this.level, this.priceType, this.sortBy});
  final String? category, search, level, priceType, sortBy;
}
final catalogLevelProvider = StateProvider<String?>((ref) => null);
final catalogPriceTypeProvider = StateProvider<String?>((ref) => null);
final catalogSortProvider = StateProvider<String?>((ref) => null);
final courseCatalogFiltersProvider = Provider<CourseCatalogFilters>((ref) => CourseCatalogFilters(
  category: ref.watch(selectedCategoryProvider), search: ref.watch(catalogSearchQueryProvider),
  level: ref.watch(catalogLevelProvider), priceType: ref.watch(catalogPriceTypeProvider), sortBy: ref.watch(catalogSortProvider),
));
