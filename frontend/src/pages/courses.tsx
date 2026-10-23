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
  ArrowUpRight,
} from "lucide-react";
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
import {
  SymphoButton,
  SymphoCtaBanner,
  SymphoPageHero,
} from "@/components/sympho/SymphoSystem";

const levels = [
  { value: "beginner", label: "Beginner" },
  { value: "intermediate", label: "Intermediate" },
  { value: "advanced", label: "Advanced" },
];

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
  const [categories, setCategories] = React.useState<
    { id: string; name: string; count: number }[]
  >([]);
  const [viewMode, setViewMode] = React.useState<"grid" | "list">("grid");
  const [isFilterOpen, setIsFilterOpen] = React.useState(false);
  const [localSearchQuery, setLocalSearchQuery] = React.useState(
    searchParams.get("search") || ""
  );

  // API State
  const [apiCourses, setApiCourses] = React.useState<Course[]>([]);
  const [isLoadingCourses, setIsLoadingCourses] = React.useState(true);
  const [apiError, setApiError] = React.useState<string | null>(null);
  const [currentPage, setCurrentPage] = React.useState(1);
  const [totalPages, setTotalPages] = React.useState(1);
  const [totalItems, setTotalItems] = React.useState(0);
  const pageSize = 12;

  const { filters, setFilters } = useCourseStore();

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

  React.useEffect(() => {
    let current = true;
    const fetchCourses = async () => {
      try {
        setIsLoadingCourses(true);
        setApiError(null);

        const params = new URLSearchParams();
        params.append("page", currentPage.toString());
        params.append("page_size", pageSize.toString());

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

        const response = await api.get(`/courses/?${params.toString()}`);
        if (!current) return;
        const data = response.data;
        const coursesArray = data.courses || [];
        setTotalPages(data.total_pages || 1);
        setTotalItems(data.total || 0);

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
          lesson_count: course.stats?.lessons ?? 0,
          created_at: course.created_at,
          updated_at: course.updated_at,
        }));
        setApiCourses(courses);
      } catch (error) {
        if (!current) return;
        console.error("Failed to fetch courses:", error);
        setApiError(
          error instanceof Error ? error.message : "Failed to load courses"
        );
        setApiCourses([]);
        setTotalPages(1);
        setTotalItems(0);
      } finally {
        if (current) setIsLoadingCourses(false);
      }
    };

    fetchCourses();
    return () => {
      current = false;
    };
  }, [currentPage, filters]);

  React.useEffect(() => {
    api
      .get("/courses/?page_size=100")
      .then((res) => {
        const courses = res.data?.courses || res.data || [];
        const catMap: Record<string, { name: string; count: number }> = {};
        courses.forEach((c: any) => {
          if (!c.category) return;
          const id = c.category.trim().toLowerCase().replace(/\s+/g, "-");
          if (!catMap[id]) catMap[id] = { name: c.category.trim(), count: 0 };
          catMap[id].count += 1;
        });
        setCategories(
          Object.entries(catMap).map(([id, { name, count }]) => ({
            id,
            name,
            count,
          }))
        );
      })
      .catch(() => {});
  }, []);

  React.useEffect(() => {
    const urlFilters = {
      search: searchParams.get("search") || "",
      category: searchParams.get("category") || "",
      level: searchParams.get("level") || "",
      price_type: searchParams.get("price_type") || "",
      course_type: searchParams.get("course_type") || "",
      sort: searchParams.get("sort") || "latest",
    };
    setFilters(urlFilters);
    setCurrentPage(1);
  }, [searchParams, setFilters]);

  const handleFilterChange = (key: string, value: string) => {
    const newParams = new URLSearchParams(searchParams);
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

  const activeFiltersCount = (
    ["search", "category", "level", "price_type"] as const
  ).filter((key) => filters[key] && filters[key] !== "all").length;

  return (
    <div className="sympho-scope min-h-screen bg-limestone-100 text-ink-900">
      <SymphoPageHero
        index="SI—CRS"
        eyebrow="Explore / Courses & Cohorts"
        title="Find your next engineering or academic mastery track"
        lede="Build practical capabilities through expert-led cohorts, interactive simulation labs, and structured assessments across the Tamil Knowledge Triad."
        drawingCode="SHEET SI—CRS · SCALE 1:100"
        badge={`${totalItems || 0} Active Programs`}
        specs={[
          { label: "Catalog Size", value: `${totalItems || "40+"} Courses` },
          { label: "Disciplines", value: `${categories.length || 6} Tracks` },
          { label: "Pedagogy", value: "Triad + Labs" },
          { label: "Credential", value: "Cryptographic ID" },
        ]}
        primaryAction={
          <SymphoButton to="/labs" variant="on-dark" arrow>
            Explore learning labs
          </SymphoButton>
        }
        secondaryAction={
          <SymphoButton to="/bundles" variant="outline-dark">
            Course bundles
          </SymphoButton>
        }
      />

      <div className="container-page py-12 lg:py-16">
        <StudentLiveClasses />

        {/* Architectural Filter & Search Ledger Bar */}
        <div className="sheet-frame mb-10 rounded-lg border border-ink-900/15 bg-limestone-50 p-6 shadow-plate">
          {/* Course Type Triad Tabs */}
          <div className="mb-6 flex flex-wrap items-center justify-between gap-4 border-b border-ink-900/10 pb-5">
            <div className="flex items-center gap-3">
              <span className="font-mono text-label text-copper-600">
                01 · TAXONOMY FILTER
              </span>
              <span className="hidden text-xs text-ink-500 sm:inline">
                Filter by Tamil Knowledge Triad dimension
              </span>
            </div>
            <div
              role="group"
              aria-label="Course type"
              className="flex flex-wrap gap-2"
            >
              {[
                {
                  value: "all",
                  label: "All courses",
                  description: "Every learning format",
                },
                ...courseTypes,
              ].map((type) => {
                const isSelected =
                  (searchParams.get("course_type") || "all") === type.value;
                return (
                  <button
                    key={type.value}
                    type="button"
                    title={type.description}
                    aria-pressed={isSelected}
                    onClick={() => handleFilterChange("course_type", type.value)}
                    className={`rounded-pill border px-4 py-1.5 font-mono text-xs uppercase tracking-wider transition-colors ${
                      isSelected
                        ? "border-ink-900 bg-ink-900 text-limestone-50"
                        : "border-ink-900/20 bg-limestone-100/70 text-ink-700 hover:border-ink-900"
                    }`}
                  >
                    {type.label}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Search + Sort + View Controls */}
          <div className="flex flex-col gap-4 lg:flex-row lg:items-center">
            <form onSubmit={handleSearch} className="flex-1">
              <div className="relative">
                <Search className="pointer-events-none absolute top-1/2 left-4 size-4 -translate-y-1/2 text-ink-500" />
                <input
                  type="search"
                  placeholder="Search courses..."
                  value={localSearchQuery}
                  onChange={(e) => setLocalSearchQuery(e.target.value)}
                  className="field-input pl-11 pr-10"
                />
                {localSearchQuery && (
                  <button
                    type="button"
                    onClick={() => setLocalSearchQuery("")}
                    className="absolute top-1/2 right-3 -translate-y-1/2 text-ink-400 hover:text-ink-900"
                  >
                    <X className="size-4" />
                  </button>
                )}
              </div>
            </form>

            {/* Mobile Filter Drawer Trigger */}
            <Dialog.Root open={isFilterOpen} onOpenChange={setIsFilterOpen}>
              <Dialog.Trigger asChild>
                <button
                  type="button"
                  className="inline-flex min-h-[3rem] items-center justify-center gap-2 rounded border border-ink-900/20 bg-limestone-100 px-4 text-sm font-medium text-ink-900 lg:hidden"
                >
                  <SlidersHorizontal className="size-4" />
                  <span>Filters</span>
                  {activeFiltersCount > 0 && (
                    <span className="rounded-pill bg-copper-500 px-2 py-0.5 font-mono text-xs text-limestone-50">
                      {activeFiltersCount}
                    </span>
                  )}
                </button>
              </Dialog.Trigger>

              <Dialog.Portal>
                <Dialog.Overlay className="fixed inset-0 z-50 bg-ink-950/60 backdrop-blur-sm" />
                <Dialog.Content className="sympho-scope fixed top-0 right-0 z-50 h-full w-full overflow-y-auto bg-limestone-50 p-6 text-ink-900 shadow-lift sm:w-80">
                  <div className="mb-6 flex items-center justify-between border-b border-ink-900/10 pb-4">
                    <Dialog.Title className="font-display text-xl font-normal">
                      Filter Courses
                    </Dialog.Title>
                    <Dialog.Close asChild>
                      <button
                        type="button"
                        className="rounded-pill border border-ink-900/20 p-2 text-ink-700 hover:text-ink-900"
                      >
                        <X className="size-4" />
                      </button>
                    </Dialog.Close>
                  </div>

                  <FilterContent
                    filters={filters}
                    categories={categories}
                    onFilterChange={handleFilterChange}
                    onClearFilters={clearFilters}
                  />
                </Dialog.Content>
              </Dialog.Portal>
            </Dialog.Root>

            <FilterDropdown
              placeholder="Sort"
              options={sortOptions}
              value={filters.sort || "latest"}
              onChange={(value) => handleFilterChange("sort", value)}
            />

            <div className="inline-flex items-center rounded border border-ink-900/20 bg-limestone-100 p-1">
              <button
                type="button"
                aria-label="Grid view"
                onClick={() => setViewMode("grid")}
                className={`rounded px-3 py-1.5 transition-colors ${
                  viewMode === "grid"
                    ? "bg-ink-900 text-limestone-50"
                    : "text-ink-600 hover:text-ink-900"
                }`}
              >
                <Grid className="size-4" />
              </button>
              <button
                type="button"
                aria-label="List view"
                onClick={() => setViewMode("list")}
                className={`rounded px-3 py-1.5 transition-colors ${
                  viewMode === "list"
                    ? "bg-ink-900 text-limestone-50"
                    : "text-ink-600 hover:text-ink-900"
                }`}
              >
                <List className="size-4" />
              </button>
            </div>
          </div>

          {/* Active Filter Pills */}
          {activeFiltersCount > 0 && (
            <div className="mt-4 flex flex-wrap items-center gap-2 border-t border-ink-900/10 pt-4">
              <span className="font-mono text-label text-ink-500">
                Active filters:
              </span>
              {filters.search && (
                <span className="inline-flex items-center gap-1.5 rounded-pill border border-ink-900/20 bg-limestone-100 px-3 py-1 text-xs text-ink-900">
                  Search: {filters.search}
                  <button
                    type="button"
                    onClick={() => handleFilterChange("search", "")}
                    className="hover:text-copper-600"
                  >
                    <X className="size-3" />
                  </button>
                </span>
              )}
              {filters.category && (
                <span className="inline-flex items-center gap-1.5 rounded-pill border border-ink-900/20 bg-limestone-100 px-3 py-1 text-xs text-ink-900">
                  Category:{" "}
                  {categories.find((c) => c.id === filters.category)?.name ||
                    filters.category}
                  <button
                    type="button"
                    onClick={() => handleFilterChange("category", "")}
                    className="hover:text-copper-600"
                  >
                    <X className="size-3" />
                  </button>
                </span>
              )}
              {filters.level && (
                <span className="inline-flex items-center gap-1.5 rounded-pill border border-ink-900/20 bg-limestone-100 px-3 py-1 text-xs text-ink-900">
                  Level:{" "}
                  {levels.find((l) => l.value === filters.level)?.label ||
                    filters.level}
                  <button
                    type="button"
                    onClick={() => handleFilterChange("level", "")}
                    className="hover:text-copper-600"
                  >
                    <X className="size-3" />
                  </button>
                </span>
              )}
            </div>
          )}
        </div>

        {/* Main 12-Col Layout: Sidebar + Results */}
        <div className="grid grid-cols-1 gap-10 lg:grid-cols-12">
          <aside className="hidden lg:col-span-3 lg:block">
            <div className="sheet-frame sticky top-24 rounded-lg border border-ink-900/15 bg-limestone-50 p-6">
              <div className="mb-5 flex items-center justify-between border-b border-ink-900/10 pb-3">
                <h2 className="font-display text-xl font-normal text-ink-900">
                  Filter courses
                </h2>
                <span className="font-mono text-label text-copper-600">
                  SPEC
                </span>
              </div>
              <FilterContent
                filters={filters}
                categories={categories}
                onFilterChange={handleFilterChange}
                onClearFilters={clearFilters}
              />
            </div>
          </aside>

          <div className="lg:col-span-9">
            {/* Cross-sell Banners */}
            {(hasMemberships || hasBundles) && (
              <div className="mb-8 grid grid-cols-1 gap-4 sm:grid-cols-2">
                {hasMemberships && (
                  <Link
                    to="/membership"
                    className="group flex items-center justify-between rounded-lg border border-ink-900/15 bg-limestone-50 p-4 transition-colors hover:border-copper-500"
                  >
                    <span className="flex items-center gap-3 text-sm font-medium text-ink-900">
                      <Sparkles className="size-4 text-copper-500" />
                      <span>Get every course with a Membership</span>
                    </span>
                    <ArrowUpRight className="size-4 text-copper-600 transition-transform group-hover:translate-x-0.5 group-hover:-translate-y-0.5" />
                  </Link>
                )}
                {hasBundles && (
                  <Link
                    to="/bundles"
                    className="group flex items-center justify-between rounded-lg border border-ink-900/15 bg-limestone-50 p-4 transition-colors hover:border-copper-500"
                  >
                    <span className="flex items-center gap-3 text-sm font-medium text-ink-900">
                      <PackageOpen className="size-4 text-copper-500" />
                      <span>Save with curated Course Bundles</span>
                    </span>
                    <ArrowUpRight className="size-4 text-copper-600 transition-transform group-hover:translate-x-0.5 group-hover:-translate-y-0.5" />
                  </Link>
                )}
              </div>
            )}

            {/* Results Counter Bar */}
            <div className="mb-6 flex items-center justify-between border-b border-ink-900/10 pb-4">
              <p className="font-mono text-xs uppercase tracking-wider text-ink-600">
                {isLoadingCourses ? (
                  "Loading courses…"
                ) : (
                  <>
                    <strong className="text-ink-900">{totalItems}</strong>{" "}
                    course{totalItems === 1 ? "" : "s"} found
                  </>
                )}
              </p>
              {apiError && (
                <p className="text-sm text-copper-600">
                  Couldn&apos;t load courses: {apiError}
                </p>
              )}
            </div>

            {/* Course Grid / List */}
            {isLoadingCourses ? (
              <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 xl:grid-cols-3">
                {Array.from({ length: 6 }).map((_, i) => (
                  <div
                    key={i}
                    className="animate-pulse rounded-lg border border-ink-900/10 bg-limestone-50 p-5"
                  >
                    <div className="mb-4 aspect-video rounded bg-limestone-200" />
                    <div className="mb-2 h-4 rounded bg-limestone-200" />
                    <div className="mb-4 h-4 w-3/4 rounded bg-limestone-200" />
                    <div className="flex items-center justify-between">
                      <div className="h-3 w-20 rounded bg-limestone-200" />
                      <div className="h-8 w-20 rounded bg-limestone-200" />
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div
                className={
                  viewMode === "grid"
                    ? "grid grid-cols-1 gap-6 sm:grid-cols-2 xl:grid-cols-3"
                    : "space-y-6"
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
              <div className="sheet-frame rounded-lg border border-ink-900/15 bg-limestone-50 py-16 text-center">
                <div className="mx-auto mb-5 grid size-16 place-items-center rounded-pill border border-ink-900/15 bg-limestone-100 text-copper-600">
                  <Search className="size-7" />
                </div>
                <h3 className="font-display text-2xl font-normal text-ink-900">
                  No courses match this specification
                </h3>
                <p className="mx-auto mt-2 max-w-md text-sm text-ink-600">
                  Try adjusting your search criteria or clearing active filters
                  to view all available programs.
                </p>
                <div className="mt-6">
                  <SymphoButton onClick={clearFilters} variant="primary">
                    Clear Filters
                  </SymphoButton>
                </div>
              </div>
            )}

            {/* Pagination */}
            {!isLoadingCourses && totalPages > 1 && (
              <div className="mt-12">
                <Pagination
                  currentPage={currentPage}
                  totalPages={totalPages}
                  totalItems={totalItems}
                  pageSize={pageSize}
                  onPageChange={(page) => setCurrentPage(page)}
                  showPageInfo={true}
                />
              </div>
            )}
          </div>
        </div>
      </div>

      <SymphoCtaBanner
        eyebrow="Need a Guided Learning Path?"
        title="Unsure which engineering or STEM track fits your goals?"
        description="Explore our multi-course mastery bundles or try a browser-native learning lab before committing to a full cohort."
        primaryText="Explore course bundles"
        primaryTo="/bundles"
        secondaryText="Try interactive labs"
        secondaryTo="/labs"
      />
      <OfferTimerWidget />
    </div>
  );
};

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
        <button
          type="button"
          className="inline-flex min-h-[3rem] w-44 items-center justify-between rounded border border-ink-900/20 bg-limestone-50 px-4 text-sm text-ink-900 hover:border-ink-900/40"
        >
          <span className="truncate">
            {value
              ? (() => {
                  const option = options.find(
                    (opt) => ("value" in opt ? opt.value : opt.id) === value
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
        </button>
      </Select.Trigger>

      <Select.Portal>
        <Select.Content
          className="sympho-scope min-w-[180px] max-h-[300px] overflow-hidden rounded-lg border border-ink-900/15 bg-limestone-50 p-1 text-ink-900 shadow-plate"
          style={{ zIndex: 9999 }}
          position="popper"
          sideOffset={5}
          align="start"
        >
          <Select.Viewport className="p-1">
            <Select.Item
              value="all"
              className="cursor-pointer rounded px-3 py-2 text-sm hover:bg-limestone-200/70"
            >
              <Select.ItemText>All {placeholder}</Select.ItemText>
            </Select.Item>
            {options.map((option) => (
              <Select.Item
                key={"value" in option ? option.value : option.id}
                value={"value" in option ? option.value : option.id}
                className="cursor-pointer rounded px-3 py-2 text-sm hover:bg-limestone-200/70"
              >
                <Select.ItemText>
                  {"label" in option ? option.label : option.name}
                  {"count" in option && option.count && (
                    <span className="ml-1 text-ink-500">({option.count})</span>
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
      <div>
        <h3 className="font-mono text-label text-ink-600 mb-3">Categories</h3>
        <div className="space-y-2">
          {categories.map((category) => (
            <label
              key={category.id}
              className="flex cursor-pointer items-center text-sm text-ink-800 hover:text-copper-600"
            >
              <input
                type="radio"
                name="category"
                value={category.id}
                checked={filters.category === category.id}
                onChange={(e) => onFilterChange("category", e.target.value)}
                className="mr-2.5 accent-copper-600"
              />
              <span>
                {category.name}{" "}
                <span className="font-mono text-xs text-ink-400">
                  ({category.count})
                </span>
              </span>
            </label>
          ))}
        </div>
      </div>

      <div className="border-t border-ink-900/10 pt-5">
        <h3 className="font-mono text-label text-ink-600 mb-3">
          Learning format
        </h3>
        <div className="space-y-2">
          {courseTypes.map((type) => (
            <label
              key={type.value}
              className="flex cursor-pointer items-center text-sm text-ink-800 hover:text-copper-600"
            >
              <input
                type="radio"
                name="course_type"
                className="mr-2.5 accent-copper-600"
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

      <div className="border-t border-ink-900/10 pt-5">
        <h3 className="font-mono text-label text-ink-600 mb-3">Level</h3>
        <div className="space-y-2">
          {levels.map((level) => (
            <label
              key={level.value}
              className="flex cursor-pointer items-center text-sm text-ink-800 hover:text-copper-600"
            >
              <input
                type="radio"
                name="level"
                value={level.value}
                checked={filters.level === level.value}
                onChange={(e) => onFilterChange("level", e.target.value)}
                className="mr-2.5 accent-copper-600"
              />
              <span>{level.label}</span>
            </label>
          ))}
        </div>
      </div>

      <div className="border-t border-ink-900/10 pt-5">
        <h3 className="font-mono text-label text-ink-600 mb-3">Price</h3>
        <div className="space-y-2">
          {priceTypes.map((price) => (
            <label
              key={price.value}
              className="flex cursor-pointer items-center text-sm text-ink-800 hover:text-copper-600"
            >
              <input
                type="radio"
                name="price_type"
                value={price.value}
                checked={filters.price_type === price.value}
                onChange={(e) => onFilterChange("price_type", e.target.value)}
                className="mr-2.5 accent-copper-600"
              />
              <span>{price.label}</span>
            </label>
          ))}
        </div>
      </div>

      <button
        type="button"
        onClick={onClearFilters}
        className="w-full rounded-pill border border-ink-900/25 py-2.5 font-mono text-xs uppercase tracking-wider text-ink-800 transition-colors hover:border-ink-900 hover:bg-ink-900 hover:text-limestone-50"
      >
        Clear All Filters
      </button>
    </div>
  );
};
