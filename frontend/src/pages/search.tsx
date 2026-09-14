import { useState, useEffect, useCallback } from "react";
import { useSearchParams } from "react-router-dom";
import { Search, Filter, Loader2, SearchX } from "lucide-react";
import { CourseCard } from "@/components/course/course-card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { api } from "@/api/axios";
import { Course } from "@/types";

interface SearchFilters {
  level: string;
  price: string;
  sort: string;
}

const levels = ["Beginner", "Intermediate", "Advanced"];
// Value maps to the backend `price_type` query param.
const prices = [
  { label: "Free", value: "free" },
  { label: "Paid", value: "paid" },
];
const sortOptions = [
  { value: "latest", label: "Newest First" },
  { value: "popular", label: "Most Popular" },
  { value: "rating", label: "Sort by Rating" },
  { value: "price-low", label: "Price: Low to High" },
  { value: "price-high", label: "Price: High to Low" },
];

// Convert the backend course list payload to the local `Course` shape the
// CourseCard expects. Mirrors the mapping used on the /courses catalog page so
// the two stay consistent.
function mapApiCourse(course: any): Course {
  return {
    id: course.id,
    post_title: course.title,
    post_excerpt: course.description,
    post_content: course.description || "",
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
      id: course.instructor?.id,
      display_name: course.instructor?.name || "Instructor",
      user_email: "",
      user_login: (course.instructor?.name || "instructor").toLowerCase(),
      user_nicename: (course.instructor?.name || "instructor").toLowerCase(),
      user_registered: course.created_at,
      user_status: 0,
      is_active: true,
      is_verified: true,
      created_at: course.created_at,
      updated_at: course.updated_at,
      last_login: course.updated_at,
      profile: {
        profile_photo: course.instructor?.avatar || "",
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
            slug: String(course.category).toLowerCase(),
            description: "",
            created_at: course.created_at,
          },
        ]
      : [],
    slug: course.slug || "",
    lessons: Array.from({ length: course.stats?.lessons || 0 }) as any,
    created_at: course.created_at,
    updated_at: course.updated_at,
  } as unknown as Course;
}

export function SearchPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [searchTerm, setSearchTerm] = useState(searchParams.get("q") || "");
  const [showFilters, setShowFilters] = useState(false);
  const [filters, setFilters] = useState<SearchFilters>({
    level: searchParams.get("level") || "",
    price: searchParams.get("price") || "",
    sort: searchParams.get("sort") || "latest",
  });

  const [results, setResults] = useState<Course[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Fetch real courses from the backend catalog endpoint. All filters map to
  // query params the /courses/ endpoint actually supports (search, level,
  // price_type, sort) — no client-side mock data.
  const runSearch = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams();
      params.append("page", "1");
      params.append("page_size", "24");
      if (searchTerm.trim()) params.append("search", searchTerm.trim());
      if (filters.level) params.append("level", filters.level);
      if (filters.price) params.append("price_type", filters.price);
      if (filters.sort) params.append("sort", filters.sort);

      const res = await api.get(`/courses/?${params.toString()}`);
      const data = res.data;
      const list = (data?.courses || []).map(mapApiCourse);
      setResults(list);
      setTotal(data?.total ?? list.length);
    } catch (err) {
      console.error("Course search failed:", err);
      setError("Could not load search results. Please try again.");
      setResults([]);
      setTotal(0);
    } finally {
      setLoading(false);
    }
  }, [searchTerm, filters]);

  // Debounce so typing doesn't fire a request per keystroke.
  useEffect(() => {
    const t = setTimeout(runSearch, 300);
    return () => clearTimeout(t);
  }, [runSearch]);

  const handleSearch = (term: string) => {
    setSearchTerm(term);
    const newParams = new URLSearchParams(searchParams);
    if (term) newParams.set("q", term);
    else newParams.delete("q");
    setSearchParams(newParams);
  };

  const handleFilterChange = (
    filterType: keyof SearchFilters,
    value: string,
  ) => {
    const newFilters = { ...filters, [filterType]: value };
    setFilters(newFilters);

    const newParams = new URLSearchParams(searchParams);
    if (value && !(filterType === "sort" && value === "latest"))
      newParams.set(filterType, value);
    else newParams.delete(filterType);
    setSearchParams(newParams);
  };

  const clearFilters = () => {
    setFilters({ level: "", price: "", sort: "latest" });
    setSearchParams(new URLSearchParams(searchTerm ? { q: searchTerm } : {}));
  };

  const activeFiltersCount = [filters.level, filters.price].filter(
    Boolean,
  ).length;

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Search Header */}
        <div className="mb-8">
          <div className="flex items-center space-x-4 mb-4">
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-400" />
              <input
                type="text"
                placeholder="Search for courses..."
                value={searchTerm}
                onChange={(e) => handleSearch(e.target.value)}
                className="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>
            <Button
              variant="outline"
              onClick={() => setShowFilters(!showFilters)}
              className="flex items-center space-x-2"
            >
              <Filter className="h-4 w-4" />
              <span>Filters</span>
              {activeFiltersCount > 0 && (
                <Badge className="ml-1 bg-blue-600">{activeFiltersCount}</Badge>
              )}
            </Button>
          </div>

          {/* Search Info */}
          <div className="flex items-center justify-between">
            <p className="text-gray-600">
              {loading
                ? "Searching…"
                : `${total} result${total === 1 ? "" : "s"} found`}
              {searchTerm && (
                <span>
                  {" "}
                  for "<strong>{searchTerm}</strong>"
                </span>
              )}
            </p>
            <select
              value={filters.sort}
              onChange={(e) => handleFilterChange("sort", e.target.value)}
              className="border border-gray-300 rounded-lg px-3 py-2 text-sm"
            >
              {sortOptions.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="flex gap-8">
          {/* Filters Sidebar */}
          <div
            className={`${showFilters ? "block" : "hidden"} lg:block w-80 flex-shrink-0`}
          >
            <div
              className="bg-white rounded-lg p-6 shadow-sm sticky top-8"
              data-glass="work"
            >
              <div className="flex items-center justify-between mb-6">
                <h3 className="text-lg font-semibold text-gray-900">Filters</h3>
                {activeFiltersCount > 0 && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={clearFilters}
                    className="text-xs"
                  >
                    Clear All
                  </Button>
                )}
              </div>

              <div className="space-y-6">
                {/* Level */}
                <div>
                  <h4 className="font-medium text-gray-900 mb-3">Level</h4>
                  <div className="space-y-2">
                    {levels.map((level) => (
                      <label key={level} className="flex items-center">
                        <input
                          type="radio"
                          name="level"
                          value={level}
                          checked={filters.level === level}
                          onChange={(e) =>
                            handleFilterChange("level", e.target.value)
                          }
                          className="mr-2"
                        />
                        <span className="text-sm text-gray-700">{level}</span>
                      </label>
                    ))}
                  </div>
                </div>

                {/* Price */}
                <div>
                  <h4 className="font-medium text-gray-900 mb-3">Price</h4>
                  <div className="space-y-2">
                    {prices.map((price) => (
                      <label key={price.value} className="flex items-center">
                        <input
                          type="radio"
                          name="price"
                          value={price.value}
                          checked={filters.price === price.value}
                          onChange={(e) =>
                            handleFilterChange("price", e.target.value)
                          }
                          className="mr-2"
                        />
                        <span className="text-sm text-gray-700">
                          {price.label}
                        </span>
                      </label>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Search Results */}
          <div className="flex-1">
            {/* Active Filters */}
            {activeFiltersCount > 0 && (
              <div className="mb-6">
                <div className="flex items-center space-x-2 mb-2">
                  <span className="text-sm font-medium text-gray-700">
                    Active Filters:
                  </span>
                </div>
                <div className="flex flex-wrap gap-2">
                  {(["level", "price"] as const).map(
                    (key) =>
                      filters[key] && (
                        <Badge
                          key={key}
                          variant="secondary"
                          className="cursor-pointer hover:bg-gray-200"
                          onClick={() => handleFilterChange(key, "")}
                        >
                          {key}: {filters[key]} ×
                        </Badge>
                      ),
                  )}
                </div>
              </div>
            )}

            {/* States */}
            {loading ? (
              <div className="flex flex-col items-center justify-center py-24 text-gray-500">
                <Loader2 className="h-8 w-8 animate-spin mb-3" />
                <p>Searching courses…</p>
              </div>
            ) : error ? (
              <div className="flex flex-col items-center justify-center py-24 text-center">
                <SearchX className="h-10 w-10 text-gray-400 mb-3" />
                <p className="text-gray-700 font-medium">{error}</p>
                <Button variant="outline" className="mt-4" onClick={runSearch}>
                  Retry
                </Button>
              </div>
            ) : results.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-24 text-center">
                <SearchX className="h-10 w-10 text-gray-400 mb-3" />
                <p className="text-gray-900 font-semibold">No courses found</p>
                <p className="text-gray-500 mt-1">
                  {searchTerm
                    ? `We couldn't find any courses matching "${searchTerm}".`
                    : "Try searching for a topic or adjusting your filters."}
                </p>
              </div>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-6">
                {results.map((course) => (
                  <CourseCard key={course.id} course={course} />
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
