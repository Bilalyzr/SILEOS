import { PageBanner } from "@/components/design-system/PageBanner";
import * as React from "react";
import { useSearchParams, Link } from "react-router-dom";
import {
  Search,
  Grid,
  List,
  SlidersHorizontal,
  X,
  Sparkles,
  PackageOpen,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { CourseCard } from "@/components/course/course-card";
import { Pagination } from "@/components/ui/pagination";
import * as Select from "@radix-ui/react-select";
import * as Dialog from "@radix-ui/react-dialog";
import { useCourseStore } from "@/store/course";
import { Course } from "@/types";
import { api } from "@/api/axios";
import { OfferTimerWidget } from "@/components/promotional/OfferTimerWidget";
import { fetchMembershipPlans } from "@/api/membership";
import { fetchBundles } from "@/api/bundle";
import { StudentLiveClasses } from "@/components/live/StudentLiveClasses";
import { verticalFromHostname } from "@/config/businessVerticals";

// Function to convert API course to local Course interface

// Categories loaded dynamically from API below

const levels = [
  { value: "beginner", label: "Beginner" },
  { value: "intermediate", label: "Intermediate" },
  { value: "advanced", label: "Advanced" },
];

// v2.0 §3 "type as an implicit filter": learners filter 3D / tuition / skills without any tag.
const courseTypes = [
  { value: "meiporul", label: "Meiporul", description: "3D & AR lessons" },
  {
    value: "seyappaduporul",
    label: "Seyappaduporul",
    description: "Live tuition",
  },
  { value: "utporul", label: "Utporul", description: "Skills & exams" },
];

const priceTypes = [
  { value: "all", label: "All Courses" },
  { value: "free", label: "Free" },
  { value: "paid", label: "Paid" },
];

const sortOptions = [
  { value: "latest", label: "Latest" },
  { value: "popular", label: "Most Popular" },
  { value: "rating", label: "Highest Rated" },
  { value: "price-low", label: "Price: Low to High" },
  { value: "price-high", label: "Price: High to Low" },
];

export const CoursesPage = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const hostVertical =
    typeof window === "undefined"
      ? null
      : verticalFromHostname(window.location.hostname);
  const [categories, setCategories] = React.useState<
    { id: string; name: string; count: number }[]
  >([]);
  const [viewMode, setViewMode] = React.useState<"grid" | "list">("grid");
  const [isFilterOpen, setIsFilterOpen] = React.useState(false);
  const [localSearchQuery, setLocalSearchQuery] = React.useState(
    searchParams.get("search") || "",
  );

  // API State
  const [apiCourses, setApiCourses] = React.useState<Course[]>([]);
  const [isLoadingCourses, setIsLoadingCourses] = React.useState(true);
  const [apiError, setApiError] = React.useState<string | null>(null);
  const [currentPage, setCurrentPage] = React.useState(1);
  const [totalPages, setTotalPages] = React.useState(1);
  const [totalItems, setTotalItems] = React.useState(0);
  const pageSize = 12; // Courses per page

  const { filters, setFilters } = useCourseStore();

  // Promo strip state — membership/bundles links only show when the
  // corresponding catalog is non-empty. Never blocks the course grid.
  const [hasMemberships, setHasMemberships] = React.useState(false);
  const [hasBundles, setHasBundles] = React.useState(false);

  React.useEffect(() => {
    (async () => {
      try {
        const plans = await fetchMembershipPlans();
        setHasMemberships(Array.isArray(plans) && plans.length > 0);
      } catch {
        setHasMemberships(false);
      }
    })();
    (async () => {
      try {
        const bundles = await fetchBundles();
        setHasBundles(Array.isArray(bundles) && bundles.length > 0);
      } catch {
        setHasBundles(false);
      }
    })();
  }, []);

  // Fetch courses from API
  React.useEffect(() => {
    let current = true;
    const fetchCourses = async () => {
      try {
        setIsLoadingCourses(true);
        setApiError(null);

        // Build query parameters from filters
        const params = new URLSearchParams();
        params.append("page", currentPage.toString());
        params.append("page_size", pageSize.toString());

        // Add filter parameters if they exist
        // "all" is the Select's clear-this-filter sentinel — it is never a real
        // column value, so it must never reach the backend.
        const isSet = (v?: string): v is string => Boolean(v) && v !== "all";
        if (isSet(filters.search)) params.append("search", filters.search);
        if (isSet(filters.category))
          params.append("category", filters.category);
        if (isSet(filters.level)) params.append("level", filters.level);
        if (isSet(filters.price_type))
          params.append("price_type", filters.price_type);
        if (isSet((filters as any).course_type))
          params.append("course_type", (filters as any).course_type);
        if (isSet(filters.sort)) params.append("sort", filters.sort);

        // Use axios which automatically handles auth tokens
        const response = await api.get(`/courses/?${params.toString()}`);
        if (!current) return;
        const data = response.data;
        // API now returns paginated response
        const coursesArray = data.courses || [];
        setTotalPages(data.total_pages || 1);
        setTotalItems(data.total || 0);

        // Convert API response to local format
        // Note: API returns simplified structure, so we need to adapt
        const courses = coursesArray.map((course: any) => ({
          id: course.id,
          slug: course.slug || "",
          post_title: course.title,
          post_excerpt: course.description,
          post_content: course.description,
          course_price: course.price,
          course_sale_price: course.sale_price || 0,
          course_price_type: course.price > 0 ? "paid" : "free",
          course_level: course.level,
          course_duration: `${course.stats?.duration || 0} minutes`,
          // Leave empty when the API has no image so CourseCard can fall back to
          // the bundled artwork; a placeholder URL here would always win.
          course_thumbnail: course.featured_image || "",
          course_intro_video: "",
          average_rating: course.rating || 0,
          total_reviews: 0,
          total_enrollments: course.stats?.students || 0,
          is_enrolled: course.is_enrolled || false,
          instructor: {
            id: course.instructor.id,
            display_name: course.instructor.name,
            user_email: "",
            user_login: course.instructor.name.toLowerCase(),
            user_nicename: course.instructor.name.toLowerCase(),
            user_registered: course.created_at,
            user_status: 0,
            is_active: true,
            is_verified: true,
            created_at: course.created_at,
            updated_at: course.updated_at,
            last_login: course.updated_at,
            profile: {
              profile_photo:
                course.instructor.avatar || "/api/placeholder/150/150",
              bio: "",
              qualifications: [],
              experience_years: 0,
            },
          },
          categories: course.category
            ? [
                {
                  id: 1,
                  name: course.category,
                  slug: course.category.toLowerCase(),
                  description: "",
                  created_at: course.created_at,
                },
              ]
            : [],
          lessons: [],
          // The list endpoint omits the lessons array but returns the count in
          // `stats.lessons`; CourseCard reads `lesson_count` (falling back to
          // lessons.length), so surface the real count here.
          lesson_count: course.stats?.lessons ?? 0,
          created_at: course.created_at,
          updated_at: course.updated_at,
        }));
        setApiCourses(courses);
      } catch (error) {
        if (!current) return;
        console.error("Failed to fetch courses:", error);
        setApiError(
          error instanceof Error ? error.message : "Failed to load courses",
        );
        // Show nothing rather than sample data — placeholder courses on the
        // public catalog read as real listings and can't be enrolled in.
        setApiCourses([]);
        setTotalPages(1);
        setTotalItems(0);
      } finally {
        if (current) setIsLoadingCourses(false);
      }
    };

    fetchCourses();
    return () => { current = false; };
  }, [currentPage, filters]);

  // Build the category dropdown from the whole catalog rather than the current
  // page: the backend param is page_size, so `limit=100` was ignored and this
  // only ever saw the first 20 courses. Categories don't change as the user
  // filters, so this runs once.
  React.useEffect(() => {
    api
      .get("/courses/?page_size=100")
      .then((res) => {
        const courses = res.data?.courses || res.data || [];
        const catMap: Record<string, { name: string; count: number }> = {};
        courses.forEach((c: any) => {
          if (!c.category) return;
          // id is the slug the backend matches on; name keeps the casing the
          // instructor actually typed.
          const id = c.category.trim().toLowerCase().replace(/\s+/g, "-");
          if (!catMap[id]) catMap[id] = { name: c.category.trim(), count: 0 };
          catMap[id].count += 1;
        });
        setCategories(
          Object.entries(catMap).map(([id, { name, count }]) => ({
            id,
            name,
            count,
          })),
        );
      })
      .catch(() => {});
  }, []);

  // Initialize filters from URL params
  React.useEffect(() => {
    const urlFilters = {
      search: searchParams.get("search") || "",
      category: searchParams.get("category") || "",
      level: searchParams.get("level") || "",
      price_type: searchParams.get("price_type") || "",
      // A product subdomain is a real catalog boundary, not just a branded
      // home page. An explicit query remains useful on the root domain.
      course_type: searchParams.get("course_type") || hostVertical || "",
      sort: searchParams.get("sort") || "latest",
    };
    setFilters(urlFilters);
    // Any filter change invalidates the current page. Staying on page 4 while
    // narrowing the results to 2 pages returned an empty grid, which reads as
    // "the filter is broken".
    setCurrentPage(1);
  }, [hostVertical, searchParams, setFilters]);

  const handleFilterChange = (key: string, value: string) => {
    const newParams = new URLSearchParams(searchParams);
    // "all" is the dropdown's clear-this-filter sentinel, not a column value.
    if (value && value !== "all") {
      newParams.set(key, value);
    } else {
      newParams.delete(key);
    }
    setSearchParams(newParams);
  };

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    handleFilterChange("search", localSearchQuery);
  };

  const clearFilters = () => {
    setSearchParams({});
    setLocalSearchQuery("");
  };

  // Count only the filters the user can actually see and clear. `filters` also
  // holds sort/page/per_page, which always have truthy defaults and inflated
  // this count by 3 — making the badge wrong and "Clear Filters" always visible.
  const activeFiltersCount = (
    ["search", "category", "level", "price_type"] as const
  ).filter((key) => filters[key] && filters[key] !== "all").length;

  return (
    <div className="rd-catalog-page">
      <div className="rd-route-heading">
        <PageBanner
          eyebrow="Explore / Courses"
          title="Find your next course"
          description="Build practical skills with expert-led courses, live classes and interactive learning."
          share
          shareTitle="Find your next course on SashaInfinity"
          shareDescription="Explore expert-led courses, live classes and interactive learning."
          actions={
            <Link to="/labs" className="rd-text-link">
              Explore learning labs
            </Link>
          }
        />
      </div>
      <div className="container-custom pb-12 rd-catalog-grid">
        <aside className="rd-catalog-filters">
          <h2>Filter courses</h2>
          <FilterContent
            filters={filters}
            categories={categories}
            onFilterChange={handleFilterChange}
            onClearFilters={clearFilters}
          />
        </aside>
        <div className="rd-catalog-results">
          <StudentLiveClasses />
          {/* Search and Filters Bar (floats over the hero) */}
          <div className="rd-catalog-controls">
            <div
              className="astra-course-type-filter"
              role="group"
              aria-label="Course type"
            >
              {[
                {
                  value: "all",
                  label: "All courses",
                  description: "Every learning format",
                },
                ...courseTypes,
              ].map((type) => (
                <button
                  key={type.value}
                  type="button"
                  title={type.description}
                  aria-pressed={
                    (searchParams.get("course_type") || "all") === type.value
                  }
                  onClick={() => handleFilterChange("course_type", type.value)}
                >
                  {type.label}
                </button>
              ))}
            </div>
            <div className="flex flex-col lg:flex-row gap-4">
              {/* Search */}
              <form onSubmit={handleSearch} className="flex-1">
                <div className="relative">
                  <Search className="absolute left-4 top-1/2 transform -translate-y-1/2 text-neutral-400 w-5 h-5" />
                  <Input
                    type="search"
                    placeholder="Search courses..."
                    value={localSearchQuery}
                    onChange={(e) => setLocalSearchQuery(e.target.value)}
                    className="pl-12 pr-12 h-12 sm:h-10"
                  />
                  {localSearchQuery && (
                    <button
                      type="button"
                      onClick={() => setLocalSearchQuery("")}
                      className="absolute right-3 top-1/2 transform -translate-y-1/2 text-neutral-400 hover:text-neutral-600"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  )}
                </div>
              </form>

              {/* Filter Toggle (Mobile) */}
              <Dialog.Root open={isFilterOpen} onOpenChange={setIsFilterOpen}>
                <Dialog.Trigger asChild>
                  <Button variant="outline" className="lg:hidden min-h-[44px]">
                    <SlidersHorizontal className="w-4 h-4 mr-2" />
                    Filters
                    {activeFiltersCount > 0 && (
                      <Badge variant="default" className="ml-2">
                        {activeFiltersCount}
                      </Badge>
                    )}
                  </Button>
                </Dialog.Trigger>

                <Dialog.Portal>
                  <Dialog.Overlay className="fixed inset-0 bg-black/50 z-overlay" />
                  <Dialog.Content className="fixed top-0 right-0 h-full w-full sm:w-80 bg-white shadow-xl z-dialog p-6 overflow-y-auto">
                    <div className="flex items-center justify-between mb-6">
                      <Dialog.Title className="text-lg font-semibold">
                        Filters
                      </Dialog.Title>
                      <Dialog.Close asChild>
                        <Button variant="ghost" size="icon">
                          <X className="w-4 h-4" />
                        </Button>
                      </Dialog.Close>
                    </div>

                    {/* Mobile Filter Content */}
                    <FilterContent
                      filters={filters}
                      categories={categories}
                      onFilterChange={handleFilterChange}
                      onClearFilters={clearFilters}
                    />
                  </Dialog.Content>
                </Dialog.Portal>
              </Dialog.Root>

              {/* Desktop filters live in the side panel. */}
              <FilterDropdown
                placeholder="Sort"
                options={sortOptions}
                value={filters.sort || "latest"}
                onChange={(value) => handleFilterChange("sort", value)}
              />

              {/* View Mode Toggle */}
              <div className="flex items-center border border-neutral-200 rounded-xl p-1 bg-neutral-50">
                <Button
                  variant={viewMode === "grid" ? "default" : "ghost"}
                  size="sm"
                  onClick={() => setViewMode("grid")}
                >
                  <Grid className="w-4 h-4" />
                </Button>
                <Button
                  variant={viewMode === "list" ? "default" : "ghost"}
                  size="sm"
                  onClick={() => setViewMode("list")}
                >
                  <List className="w-4 h-4" />
                </Button>
              </div>
            </div>

            {/* Active Filters */}
            {activeFiltersCount > 0 && (
              <div className="flex flex-wrap items-center gap-2 mt-4 pt-4 border-t border-neutral-200">
                <span className="text-sm text-neutral-600 w-full sm:w-auto mb-1 sm:mb-0">
                  Active filters:
                </span>
                {filters.search && (
                  <Badge variant="outline">
                    Search: {filters.search}
                    <button
                      onClick={() => handleFilterChange("search", "")}
                      className="ml-1 hover:text-danger-600"
                    >
                      <X className="w-3 h-3" />
                    </button>
                  </Badge>
                )}
                {filters.category && (
                  <Badge variant="outline">
                    Category:{" "}
                    {categories.find((c) => c.id === filters.category)?.name}
                    <button
                      onClick={() => handleFilterChange("category", "")}
                      className="ml-1 hover:text-danger-600"
                    >
                      <X className="w-3 h-3" />
                    </button>
                  </Badge>
                )}
                {filters.level && (
                  <Badge variant="outline">
                    Level:{" "}
                    {levels.find((l) => l.value === filters.level)?.label}
                    <button
                      onClick={() => handleFilterChange("level", "")}
                      className="ml-1 hover:text-danger-600"
                    >
                      <X className="w-3 h-3" />
                    </button>
                  </Badge>
                )}
              </div>
            )}
          </div>

          {/* Promo strip — membership / bundles cross-sell */}
          {(hasMemberships || hasBundles) && (
            <div className="flex flex-col sm:flex-row gap-3 mb-6">
              {hasMemberships && (
                <Link
                  to="/membership"
                  className="flex-1 flex items-center gap-3 rounded-xl border border-primary-100 bg-primary-50 px-4 py-3 text-sm font-semibold text-primary-700 hover:bg-primary-100 transition-colors"
                >
                  <Sparkles className="w-4 h-4 shrink-0" />
                  <span>Get every course with a Membership →</span>
                </Link>
              )}
              {hasBundles && (
                <Link
                  to="/bundles"
                  className="flex-1 flex items-center gap-3 rounded-xl border border-secondary-100 bg-secondary-50 px-4 py-3 text-sm font-semibold text-secondary-700 hover:bg-secondary-100 transition-colors"
                >
                  <PackageOpen className="w-4 h-4 shrink-0" />
                  <span>Save with Course Bundles →</span>
                </Link>
              )}
            </div>
          )}

          {/* Results */}
          <div className="flex justify-between items-center mb-6">
            <p className="text-neutral-700">
              {isLoadingCourses ? (
                "Loading courses…"
              ) : (
                <>
                  <span className="font-bold text-secondary-900">
                    {totalItems}
                  </span>{" "}
                  <span className="text-neutral-500">
                    course{totalItems === 1 ? "" : "s"} found
                  </span>
                </>
              )}
            </p>
            {apiError && (
              <p className="text-danger-600 text-sm">
                Couldn't load courses: {apiError}
              </p>
            )}
          </div>

          {/* Course Grid/List */}
          {isLoadingCourses ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-6">
              {Array.from({ length: 6 }).map((_, i) => (
                <div
                  key={i}
                  className="bg-white rounded-2xl border border-neutral-100 shadow-soft p-4 animate-pulse"
                  data-glass="content"
                >
                  <div className="aspect-video bg-neutral-200 rounded-xl mb-4"></div>
                  <div className="h-4 bg-neutral-200 rounded mb-2"></div>
                  <div className="h-4 bg-neutral-200 rounded w-3/4 mb-4"></div>
                  <div className="flex items-center justify-between">
                    <div className="h-3 w-20 bg-neutral-200 rounded"></div>
                    <div className="h-8 w-20 bg-neutral-200 rounded-lg"></div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div
              className={
                viewMode === "grid"
                  ? "grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-6"
                  : "space-y-4 sm:space-y-6"
              }
            >
              {apiCourses.map((course) => (
                <CourseCard
                  key={course.id}
                  course={course}
                  variant={viewMode === "list" ? "compact" : "default"}
                />
              ))}
            </div>
          )}

          {/* Empty State */}
          {!isLoadingCourses && apiCourses.length === 0 && (
            <div className="text-center py-16">
              <div className="w-24 h-24 bg-primary-50 ring-8 ring-primary-50/40 rounded-full flex items-center justify-center mx-auto mb-6">
                <Search className="w-12 h-12 text-primary-500" />
              </div>
              <h3 className="text-xl font-heading font-bold text-secondary-900 mb-2">
                No courses found
              </h3>
              <p className="text-neutral-600 mb-6">
                Try adjusting your search criteria or browse our available
                categories
              </p>
              <Button onClick={clearFilters}>Clear Filters</Button>
            </div>
          )}

          {/* Pagination */}
          {!isLoadingCourses && totalPages > 1 && (
            <Pagination
              currentPage={currentPage}
              totalPages={totalPages}
              totalItems={totalItems}
              pageSize={pageSize}
              onPageChange={(page) => setCurrentPage(page)}
              showPageInfo={true}
            />
          )}
        </div>

        {/* 🇮🇳 Static corner offer timer — keeps the 50% OFF countdown pinned
          to the bottom-right; renders null once the offer deadline passes. */}
      </div>
      <OfferTimerWidget />
    </div>
  );
};

// Filter Components
interface FilterDropdownProps {
  placeholder: string;
  options: Array<
    | { value: string; label: string }
    | { id: string; name: string; count?: number }
  >;
  value: string;
  onChange: (value: string) => void;
}

const FilterDropdown: React.FC<FilterDropdownProps> = ({
  placeholder,
  options,
  value,
  onChange,
}) => {
  return (
    <Select.Root value={value} onValueChange={onChange}>
      <Select.Trigger asChild>
        <Button variant="outline" className="w-32 justify-between">
          <span className="truncate">
            {value
              ? (() => {
                  const option = options.find(
                    (opt) => ("value" in opt ? opt.value : opt.id) === value,
                  );
                  return option
                    ? "label" in option
                      ? option.label
                      : option.name
                    : placeholder;
                })()
              : placeholder}
          </span>
          <Select.Icon />
        </Button>
      </Select.Trigger>

      <Select.Portal>
        <Select.Content
          className="bg-white border border-neutral-200 rounded-lg shadow-lg p-1 overflow-hidden min-w-[150px] max-h-[300px] z-popover"
          position="popper"
          sideOffset={5}
          align="start"
        >
          <Select.Viewport className="p-1">
            <Select.Item
              value="all"
              className="px-3 py-2 hover:bg-neutral-100 rounded cursor-pointer"
            >
              <Select.ItemText>All {placeholder}</Select.ItemText>
            </Select.Item>
            {options.map((option) => (
              <Select.Item
                key={"value" in option ? option.value : option.id}
                value={"value" in option ? option.value : option.id}
                className="px-3 py-2 hover:bg-neutral-100 rounded cursor-pointer"
              >
                <Select.ItemText>
                  {"label" in option ? option.label : option.name}
                  {"count" in option && option.count && (
                    <span className="text-neutral-500 ml-1">
                      ({option.count})
                    </span>
                  )}
                </Select.ItemText>
              </Select.Item>
            ))}
          </Select.Viewport>
        </Select.Content>
      </Select.Portal>
    </Select.Root>
  );
};

interface FilterContentProps {
  filters: any;
  categories: { id: string; name: string; count: number }[];
  onFilterChange: (key: string, value: string) => void;
  onClearFilters: () => void;
}

const FilterContent: React.FC<FilterContentProps> = ({
  filters,
  categories,
  onFilterChange,
  onClearFilters,
}) => {
  return (
    <div className="space-y-6">
      {/* Categories */}
      <div>
        <h3 className="font-semibold text-neutral-900 mb-3">Categories</h3>
        <div className="space-y-2">
          {categories.map((category) => (
            <label key={category.id} className="flex items-center">
              <input
                type="radio"
                name="category"
                value={category.id}
                checked={filters.category === category.id}
                onChange={(e) => onFilterChange("category", e.target.value)}
                className="mr-2"
              />
              <span className="text-sm">
                {category.name} ({category.count})
              </span>
            </label>
          ))}
        </div>
      </div>

      {/* Level */}
      <div>
        <h3 className="font-semibold text-neutral-900 mb-3">Learning format</h3>
        <div className="space-y-2">
          {courseTypes.map((type) => (
            <label key={type.value} className="flex items-center text-sm">
              <input
                type="radio"
                name="course_type"
                className="mr-2"
                value={type.value}
                checked={(filters as any).course_type === type.value}
                onChange={(e) =>
                  onFilterChange("course_type" as any, e.target.value)
                }
              />
              {type.label}
            </label>
          ))}
        </div>
      </div>
      <div>
        <h3 className="font-semibold text-neutral-900 mb-3">Level</h3>
        <div className="space-y-2">
          {levels.map((level) => (
            <label key={level.value} className="flex items-center">
              <input
                type="radio"
                name="level"
                value={level.value}
                checked={filters.level === level.value}
                onChange={(e) => onFilterChange("level", e.target.value)}
                className="mr-2"
              />
              <span className="text-sm">{level.label}</span>
            </label>
          ))}
        </div>
      </div>

      {/* Price */}
      <div>
        <h3 className="font-semibold text-neutral-900 mb-3">Price</h3>
        <div className="space-y-2">
          {priceTypes.map((price) => (
            <label key={price.value} className="flex items-center">
              <input
                type="radio"
                name="price_type"
                value={price.value}
                checked={filters.price_type === price.value}
                onChange={(e) => onFilterChange("price_type", e.target.value)}
                className="mr-2"
              />
              <span className="text-sm">{price.label}</span>
            </label>
          ))}
        </div>
      </div>

      <Button onClick={onClearFilters} variant="outline" className="w-full">
        Clear All Filters
      </Button>
    </div>
  );
};
