# Known issues

## `flutter analyze` reports 17 errors in two unwired files

`flutter analyze` fails on two files added in commit `fa53d48`
("sasha web : courses and coupon code payment updates and intregration"):

- `lib/features/courses/presentation/providers/course_catalog_provider.dart`
- `lib/features/dashboard/presentation/widgets/admin_monthly_revenue_section.dart`

They reference symbols that were never committed:

| Missing symbol | Expected in | Status |
|---|---|---|
| `CourseCatalogFilters`, `courseCatalogFiltersProvider` (with `level` / `priceType` / `sortBy`) | `course_filter_providers.dart` | That file exists but only defines `scaffoldTabProvider`, `selectedCategoryProvider`, `catalogSearchQueryProvider` |
| `RoleDashboardCard` | `role_dashboard_common.dart` | That file defines `RoleDashboardHero`, `RoleDashboardSectionTitle`, `RoleDashboardListCard` — no `RoleDashboardCard` |
| `adminRevenueMonthlyProvider` | `dashboard_provider.dart` | Not defined anywhere |

`lib/features/dashboard/domain/entities/monthly_revenue.dart` and
`lib/shared/widgets/common/safe_model_viewer.dart` came in with the same commit
and are also currently unreferenced.

### Does this break the app?

**No.** Nothing imports either file, so Dart tree-shakes them out —
`flutter build apk/appbundle --release` succeeds and the shipped app is
unaffected. Only the static analyzer walks every file under `lib/`, which is why
`flutter analyze` reports errors that the compiler never hits.

### Fix

The author of `fa53d48` needs to commit the missing definitions (the filters
model/provider, the `RoleDashboardCard` widget, and the revenue provider), or
remove the two unwired files if the feature was abandoned.

Do **not** "fix" this by adding the files to `analysis_options.yaml` excludes —
that hides the breakage from the next person who tries to wire the catalog or
admin-revenue feature up.
