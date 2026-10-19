import * as React from "react";
import { Link, useSearchParams } from "react-router-dom";
import {
  ArrowUpRight,
  Calendar,
  ChevronLeft,
  ChevronRight,
  Eye,
  MessageCircle,
  Search,
  User,
  X,
} from "lucide-react";
import { api } from "@/api/axios";
import {
  SymphoCtaBanner,
  SymphoPageHero,
  SymphoSectionHeader,
} from "@/components/sympho/SymphoSystem";

interface BlogPost {
  id: number;
  title: string;
  slug: string;
  excerpt: string;
  featured_image: string | null;
  status: string;
  category: string | null;
  tags: string | null;
  view_count: number;
  comment_count: number;
  post_date: string;
  post_modified: string;
  author: {
    id: number;
    name: string;
    email: string;
  };
}

const POSTS_PER_PAGE = 6;

export const BlogPage = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const [localSearchQuery, setLocalSearchQuery] = React.useState(
    searchParams.get("search") || "",
  );
  const [blogPosts, setBlogPosts] = React.useState<BlogPost[]>([]);
  const [totalPosts, setTotalPosts] = React.useState(0);
  const [isLoading, setIsLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [categories, setCategories] = React.useState<string[]>([]);

  const pageParam = parseInt(searchParams.get("page") || "1", 10);
  const page = Number.isNaN(pageParam) ? 1 : Math.max(1, pageParam);

  React.useEffect(() => {
    const fetchBlogPosts = async () => {
      try {
        setIsLoading(true);
        setError(null);

        const params = new URLSearchParams();
        if (searchParams.get("search")) {
          params.append("search", searchParams.get("search")!);
        }
        if (searchParams.get("category")) {
          params.append("category", searchParams.get("category")!);
        }
        params.append("skip", String((page - 1) * POSTS_PER_PAGE));
        params.append("limit", String(POSTS_PER_PAGE));

        const response = await api.get(`/blog/?${params.toString()}`);
        const posts: BlogPost[] = response.data;

        const totalHeader = parseInt(response.headers["x-total-count"], 10);
        const total = Number.isNaN(totalHeader) ? posts.length : totalHeader;

        setBlogPosts(posts);
        setTotalPosts(total);

        const lastPage = Math.max(1, Math.ceil(total / POSTS_PER_PAGE));
        if (page > lastPage) {
          const newParams = new URLSearchParams(searchParams);
          newParams.set("page", String(lastPage));
          setSearchParams(newParams);
        }
      } catch (err) {
        console.error("Failed to fetch blog posts:", err);
        setError(
          err instanceof Error ? err.message : "Failed to load blog posts",
        );
        setBlogPosts([]);
        setTotalPosts(0);
      } finally {
        setIsLoading(false);
      }
    };

    fetchBlogPosts();
  }, [searchParams, page, setSearchParams]);

  React.useEffect(() => {
    let cancelled = false;
    api
      .get(`/blog/?limit=100`)
      .then(({ data }) => {
        if (cancelled) return;
        const unique = Array.from(
          new Set((data as BlogPost[]).map((p) => p.category).filter(Boolean)),
        ) as string[];
        setCategories(unique.sort());
      })
      .catch((err) => console.error("Failed to load blog categories:", err));
    return () => {
      cancelled = true;
    };
  }, []);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    const newParams = new URLSearchParams(searchParams);
    if (localSearchQuery) {
      newParams.set("search", localSearchQuery);
    } else {
      newParams.delete("search");
    }
    newParams.delete("page");
    setSearchParams(newParams);
  };

  const handleCategoryFilter = (category: string) => {
    const newParams = new URLSearchParams(searchParams);
    if (category) {
      newParams.set("category", category);
    } else {
      newParams.delete("category");
    }
    newParams.delete("page");
    setSearchParams(newParams);
  };

  const goToPage = (nextPage: number) => {
    const newParams = new URLSearchParams(searchParams);
    if (nextPage <= 1) {
      newParams.delete("page");
    } else {
      newParams.set("page", String(nextPage));
    }
    setSearchParams(newParams);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const clearFilters = () => {
    setSearchParams({});
    setLocalSearchQuery("");
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString("en-US", {
      year: "numeric",
      month: "long",
      day: "numeric",
    });
  };

  const selectedCategory = searchParams.get("category");
  const searchQuery = searchParams.get("search");
  const hasFilters = selectedCategory || searchQuery;
  const totalPages = Math.max(1, Math.ceil(totalPosts / POSTS_PER_PAGE));

  return (
    <div className="sympho-scope rd-screen rd-screen-blog min-h-screen bg-limestone-100 text-ink-900">
      <SymphoPageHero
        index="SI—JRN.01"
        category="FIELD NOTES & DISPATCHES"
        code="EDITORIAL JOURNAL"
        title="Insights, tutorials & architectural notes."
        subtitle="Technical essays, pedagogical research, and engineering dispatches from SashaInfinity faculty on full-stack systems, spatial computing, and classical Tamil scholarship."
        metrics={[
          {
            value: String(totalPosts),
            unit: "dispatches",
            label: "Published Articles",
            code: "JRN—01",
          },
          {
            value: String(categories.length || 1),
            unit: "topics",
            label: "Editorial Verticals",
            code: "JRN—02",
          },
          {
            value: `P.${String(page).padStart(2, "0")}`,
            unit: `/ ${String(totalPages).padStart(2, "0")}`,
            label: "Current Folio",
            code: "JRN—03",
          },
        ]}
      />

      <section className="py-section-sm">
        <div className="mx-auto max-w-[1680px] px-gutter">
          <SymphoSectionHeader
            index="JRN—01"
            category="PUBLICATION INDEX"
            code={
              isLoading
                ? "LOADING..."
                : `${totalPosts} ${totalPosts === 1 ? "POST" : "POSTS"} FOUND`
            }
            title="Editorial Archive"
            subtitle="Search by keyword or filter by subject taxonomy across our published field notes."
          />

          {/* Search and Filter Bar */}
          <div className="mt-8 sheet-frame bg-limestone-50 p-6">
            <div className="flex flex-col gap-4 lg:flex-row lg:items-center">
              <form onSubmit={handleSearch} className="flex-1">
                <div className="relative flex items-center">
                  <Search className="absolute left-4 h-4 w-4 text-copper-500" />
                  <input
                    type="search"
                    placeholder="Search blog posts..."
                    value={localSearchQuery}
                    onChange={(e) => setLocalSearchQuery(e.target.value)}
                    className="h-12 w-full rounded-pill border border-ink-900/15 bg-limestone-100 pl-11 pr-10 font-mono text-xs text-ink-900 placeholder:text-ink-400 focus:border-copper-500 focus:outline-none"
                  />
                  {localSearchQuery && (
                    <button
                      type="button"
                      onClick={() => setLocalSearchQuery("")}
                      className="absolute right-3.5 text-ink-400 hover:text-ink-800"
                    >
                      <X className="h-4 w-4" />
                    </button>
                  )}
                </div>
              </form>

              {categories.length > 0 && (
                <div className="flex flex-wrap gap-2">
                  <button
                    type="button"
                    onClick={() => handleCategoryFilter("")}
                    className={`rounded-pill px-4 py-2 font-mono text-[11px] uppercase tracking-[0.14em] transition-colors ${
                      !selectedCategory
                        ? "bg-ink-900 text-limestone-100"
                        : "border border-ink-900/15 bg-limestone-100 text-ink-700 hover:border-copper-500"
                    }`}
                  >
                    All
                  </button>
                  {categories.map((category) => (
                    <button
                      key={category}
                      type="button"
                      onClick={() => handleCategoryFilter(category)}
                      className={`rounded-pill px-4 py-2 font-mono text-[11px] uppercase tracking-[0.14em] transition-colors ${
                        selectedCategory === category
                          ? "bg-ink-900 text-limestone-100"
                          : "border border-ink-900/15 bg-limestone-100 text-ink-700 hover:border-copper-500"
                      }`}
                    >
                      {category}
                    </button>
                  ))}
                </div>
              )}

              {hasFilters && (
                <button
                  type="button"
                  onClick={clearFilters}
                  className="rounded-pill border border-copper-500/40 bg-copper-500/10 px-4 py-2 font-mono text-[11px] uppercase tracking-[0.14em] text-copper-600 hover:bg-copper-500 hover:text-limestone-50"
                >
                  Clear Filters
                </button>
              )}
            </div>
          </div>

          {/* Results Count & Error */}
          <div className="mt-6 flex items-center justify-between font-mono text-xs uppercase tracking-[0.14em] text-ink-500">
            <p>
              {isLoading
                ? "Loading..."
                : `${totalPosts} ${totalPosts === 1 ? "post" : "posts"} found`}
            </p>
            {error && <p className="text-red-600">Error: {error}</p>}
          </div>

          {/* Blog Posts Grid */}
          <div className="mt-8">
            {isLoading ? (
              <div className="grid gap-8 md:grid-cols-2 lg:grid-cols-3">
                {Array.from({ length: 6 }).map((_, i) => (
                  <div
                    key={i}
                    className="sheet-frame h-96 animate-pulse bg-limestone-50 p-6"
                  />
                ))}
              </div>
            ) : blogPosts.length === 0 ? (
              <div className="sheet-frame mx-auto max-w-2xl bg-limestone-50 p-12 text-center">
                <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full border border-ink-900/15 bg-limestone-100 text-copper-500">
                  <Search className="h-7 w-7" />
                </div>
                <h3 className="mt-4 font-display text-3xl font-light text-ink-900">
                  No blog posts found
                </h3>
                <p className="mx-auto mt-2 max-w-md text-sm text-ink-600">
                  {hasFilters
                    ? "Try adjusting your search criteria or browse all posts"
                    : "Be the first to create a blog post!"}
                </p>
                {hasFilters && (
                  <button
                    type="button"
                    onClick={clearFilters}
                    className="mt-6 rounded-pill bg-ink-900 px-6 py-2.5 font-mono text-xs uppercase tracking-[0.14em] text-limestone-100 hover:bg-copper-500"
                  >
                    Clear Filters
                  </button>
                )}
              </div>
            ) : (
              <div className="grid gap-8 md:grid-cols-2 lg:grid-cols-3">
                {blogPosts.map((post, idx) => (
                  <article
                    key={post.id}
                    className="group sheet-frame flex h-full flex-col overflow-hidden bg-limestone-50 transition-all duration-300 hover:-translate-y-1 hover:border-copper-500/50 hover:shadow-lift"
                  >
                    <Link
                      to={`/blog/${post.slug}`}
                      className="relative block aspect-video overflow-hidden border-b border-ink-900/10 bg-ink-950"
                    >
                      {post.featured_image ? (
                        <img
                          src={post.featured_image}
                          alt={post.title}
                          className="h-full w-full object-cover transition-transform duration-500 group-hover:scale-105"
                        />
                      ) : (
                        <div className="flex h-full w-full items-center justify-center bg-ink-950 blueprint-grid">
                          <span className="font-display text-5xl font-light italic text-copper-400">
                            {post.title.charAt(0)}
                          </span>
                        </div>
                      )}
                      <span className="absolute left-4 top-4 rounded-pill bg-ink-950/85 px-3 py-1 font-mono text-[10px] uppercase tracking-[0.16em] text-limestone-100">
                        DOC—{String(idx + 1 + (page - 1) * POSTS_PER_PAGE).padStart(2, "0")}
                      </span>
                    </Link>

                    <div className="flex flex-1 flex-col p-6">
                      {post.category && (
                        <span className="mb-3 inline-block w-fit rounded-pill border border-copper-500/30 bg-copper-500/10 px-3 py-0.5 font-mono text-[10px] uppercase tracking-[0.14em] text-copper-600">
                          {post.category}
                        </span>
                      )}

                      <Link to={`/blog/${post.slug}`}>
                        <h2 className="line-clamp-2 font-display text-2xl font-light text-ink-900 transition-colors group-hover:text-copper-500">
                          {post.title}
                        </h2>
                      </Link>

                      {post.excerpt && (
                        <p className="mt-3 line-clamp-3 text-sm leading-relaxed text-ink-600">
                          {post.excerpt}
                        </p>
                      )}

                      <div className="mt-auto pt-6">
                        <div className="flex flex-wrap items-center gap-4 border-t border-ink-900/10 pt-4 font-mono text-[11px] text-ink-500">
                          <div className="flex items-center gap-1.5">
                            <User className="h-3.5 w-3.5 text-copper-500" />
                            <span>{post.author.name}</span>
                          </div>
                          <div className="flex items-center gap-1.5">
                            <Calendar className="h-3.5 w-3.5 text-copper-500" />
                            <span>{formatDate(post.post_date)}</span>
                          </div>
                        </div>

                        <div className="mt-3 flex items-center justify-between border-t border-ink-900/10 pt-3 font-mono text-[11px] text-ink-500">
                          <div className="flex items-center gap-4">
                            <span className="inline-flex items-center gap-1">
                              <Eye className="h-3.5 w-3.5" />
                              {post.view_count} views
                            </span>
                            <span className="inline-flex items-center gap-1">
                              <MessageCircle className="h-3.5 w-3.5" />
                              {post.comment_count} comments
                            </span>
                          </div>

                          <Link
                            to={`/blog/${post.slug}`}
                            className="inline-flex items-center gap-1 uppercase tracking-[0.14em] text-copper-500 hover:text-copper-600"
                          >
                            Read more
                            <ArrowUpRight className="h-3.5 w-3.5" />
                          </Link>
                        </div>
                      </div>
                    </div>
                  </article>
                ))}
              </div>
            )}
          </div>

          {!isLoading && totalPages > 1 && (
            <nav
              className="mt-12 flex items-center justify-center gap-4"
              aria-label="Blog pagination"
            >
              <button
                type="button"
                onClick={() => goToPage(page - 1)}
                disabled={page <= 1}
                className="inline-flex items-center gap-2 rounded-pill border border-ink-900/20 bg-limestone-50 px-5 py-2.5 font-mono text-xs uppercase tracking-[0.14em] text-ink-900 hover:border-copper-500 disabled:opacity-40"
              >
                <ChevronLeft className="h-4 w-4" />
                Previous
              </button>
              <span className="font-mono text-xs uppercase tracking-[0.16em] text-ink-600">
                Page {page} of {totalPages}
              </span>
              <button
                type="button"
                onClick={() => goToPage(page + 1)}
                disabled={page >= totalPages}
                className="inline-flex items-center gap-2 rounded-pill border border-ink-900/20 bg-limestone-50 px-5 py-2.5 font-mono text-xs uppercase tracking-[0.14em] text-ink-900 hover:border-copper-500 disabled:opacity-40"
              >
                Next
                <ChevronRight className="h-4 w-4" />
              </button>
            </nav>
          )}
        </div>
      </section>

      <SymphoCtaBanner
        code="SI—JRN // 02"
        eyebrow="APPLIED SCHOLARSHIP"
        title="Ready to put these concepts into practice?"
        description="Move from reading field notes to building inside our interactive 3D Learning Labs and mentor-led studio courses."
        primaryLabel="Explore Courses"
        primaryTo="/courses"
        secondaryLabel="Open Learning Labs"
        secondaryTo="/labs"
      />
    </div>
  );
};
