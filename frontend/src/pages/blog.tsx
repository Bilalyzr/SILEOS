import { PageLayout, PageHeader } from "@/components/design-system/PageLayout";
import * as React from "react";
import { Link, useSearchParams } from "react-router-dom";
import {
  Calendar,
  User,
  Eye,
  MessageCircle,
  Search,
  X,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { api } from "@/api/axios";

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

  // Current page lives in the URL (?page=N) so paginated views are shareable
  // and survive back/forward navigation.
  const pageParam = parseInt(searchParams.get("page") || "1", 10);
  const page = Number.isNaN(pageParam) ? 1 : Math.max(1, pageParam);

  // Fetch blog posts from API
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

        // The filtered total rides along as a response header, keeping the
        // body a plain list for every other consumer of this endpoint.
        const totalHeader = parseInt(response.headers["x-total-count"], 10);
        const total = Number.isNaN(totalHeader) ? posts.length : totalHeader;

        setBlogPosts(posts);
        setTotalPosts(total);

        // A ?page= beyond the last page (posts deleted, stale shared link)
        // would render an empty grid — snap back to the last real page.
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

  // The category list is built from an *unfiltered* fetch, once. Deriving it
  // from the filtered response made every other category disappear as soon as
  // one was picked, leaving no way back except "Clear Filters".
  React.useEffect(() => {
    let cancelled = false;
    // limit=100 is the endpoint's maximum page size — the widest category
    // sample it will return in one call.
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
    // A new result set always starts from its first page.
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
    // A new result set always starts from its first page.
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
    <PageLayout
      header={
        <PageHeader>
          <div className="container-custom">
            <h1 className="text-4xl md:text-5xl font-bold mb-4">Blog</h1>
            <p className="text-lg text-primary-50 max-w-2xl">
              Insights, tutorials, and tips from our expert instructors on data
              analytics, Excel, and professional development
            </p>
          </div>
        </PageHeader>
      }
      className="rd-screen rd-screen-blog"
    >
      <div className="container-custom py-12">
        {/* Search and Filter Bar */}
        <div
          className="bg-white rounded-lg shadow-soft p-6 mb-8"
          data-glass="work"
        >
          <div className="flex flex-col lg:flex-row gap-4">
            {/* Search */}
            <form onSubmit={handleSearch} className="flex-1">
              <div className="relative">
                <Search className="absolute left-4 top-1/2 transform -translate-y-1/2 text-neutral-400 w-5 h-5" />
                <Input
                  type="search"
                  placeholder="Search blog posts..."
                  value={localSearchQuery}
                  onChange={(e) => setLocalSearchQuery(e.target.value)}
                  className="pl-12 pr-4 h-12"
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

            {/* Category Filter */}
            {categories.length > 0 && (
              <div className="flex flex-wrap gap-2">
                <Button
                  variant={!selectedCategory ? "default" : "outline"}
                  onClick={() => handleCategoryFilter("")}
                >
                  All
                </Button>
                {categories.map((category) => (
                  <Button
                    key={category}
                    variant={
                      selectedCategory === category ? "default" : "outline"
                    }
                    onClick={() => handleCategoryFilter(category)}
                  >
                    {category}
                  </Button>
                ))}
              </div>
            )}

            {hasFilters && (
              <Button variant="outline" onClick={clearFilters}>
                Clear Filters
              </Button>
            )}
          </div>
        </div>

        {/* Results Count */}
        <div className="mb-6">
          <p className="text-neutral-600">
            {isLoading
              ? "Loading..."
              : `${totalPosts} ${totalPosts === 1 ? "post" : "posts"} found`}
          </p>
          {error && (
            <p className="text-danger-600 text-sm mt-2">Error: {error}</p>
          )}
        </div>

        {/* Blog Posts Grid */}
        {isLoading ? (
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
            {Array.from({ length: 6 }).map((_, i) => (
              <div
                key={i}
                className="bg-white rounded-lg overflow-hidden shadow-soft animate-pulse"
                data-glass="content"
              >
                <div className="aspect-video bg-neutral-200"></div>
                <div className="p-6">
                  <div className="h-4 bg-neutral-200 rounded mb-2"></div>
                  <div className="h-4 bg-neutral-200 rounded w-3/4 mb-4"></div>
                  <div className="h-3 bg-neutral-200 rounded w-1/2"></div>
                </div>
              </div>
            ))}
          </div>
        ) : blogPosts.length === 0 ? (
          <div className="text-center py-16">
            <div className="w-24 h-24 bg-neutral-100 rounded-full flex items-center justify-center mx-auto mb-6">
              <Search className="w-12 h-12 text-neutral-400" />
            </div>
            <h3 className="text-xl font-semibold text-neutral-900 mb-2">
              No blog posts found
            </h3>
            <p className="text-neutral-600 mb-6">
              {hasFilters
                ? "Try adjusting your search criteria or browse all posts"
                : "Be the first to create a blog post!"}
            </p>
            {hasFilters && (
              <Button onClick={clearFilters}>Clear Filters</Button>
            )}
          </div>
        ) : (
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
            {blogPosts.map((post) => (
              <article
                key={post.id}
                className="bg-white rounded-lg overflow-hidden shadow-soft hover:shadow-lg transition-shadow duration-300 flex flex-col h-full"
                data-glass="content"
              >
                <Link to={`/blog/${post.slug}`}>
                  {post.featured_image ? (
                    <img
                      src={post.featured_image}
                      alt={post.title}
                      className="w-full aspect-video object-cover"
                    />
                  ) : (
                    <div className="w-full aspect-video bg-gradient-to-br from-primary-100 to-primary-200 flex items-center justify-center">
                      <span className="text-4xl text-primary-600 font-bold">
                        {post.title.charAt(0)}
                      </span>
                    </div>
                  )}
                </Link>

                <div className="p-6 flex flex-col flex-1">
                  {/* Category Badge */}
                  {post.category && (
                    <Badge variant="default" className="mb-3">
                      {post.category}
                    </Badge>
                  )}

                  {/* Title */}
                  <Link to={`/blog/${post.slug}`}>
                    <h2 className="text-xl font-bold text-neutral-900 mb-3 hover:text-primary-600 transition-colors line-clamp-2">
                      {post.title}
                    </h2>
                  </Link>

                  {/* Excerpt */}
                  {post.excerpt && (
                    <p className="text-neutral-600 mb-4 line-clamp-3">
                      {post.excerpt}
                    </p>
                  )}

                  {/* Meta Information */}
                  <div className="flex flex-wrap items-center gap-4 text-sm text-neutral-500 mb-4 mt-auto">
                    <div className="flex items-center gap-1">
                      <User className="w-4 h-4" />
                      <span>{post.author.name}</span>
                    </div>
                    <div className="flex items-center gap-1">
                      <Calendar className="w-4 h-4" />
                      <span>{formatDate(post.post_date)}</span>
                    </div>
                  </div>

                  {/* Stats */}
                  <div className="flex items-center gap-4 text-sm text-neutral-500 pt-4 border-t border-neutral-200">
                    <div className="flex items-center gap-1">
                      <Eye className="w-4 h-4" />
                      <span>{post.view_count} views</span>
                    </div>
                    <div className="flex items-center gap-1">
                      <MessageCircle className="w-4 h-4" />
                      <span>{post.comment_count} comments</span>
                    </div>
                  </div>

                  {/* Read More Link */}
                  <Link
                    to={`/blog/${post.slug}`}
                    className="inline-block mt-4 text-primary-600 hover:text-primary-700 font-medium transition-colors"
                  >
                    Read more →
                  </Link>
                </div>
              </article>
            ))}
          </div>
        )}

        {/* Pagination — only rendered when there are more posts than fit on one page */}
        {!isLoading && totalPages > 1 && (
          <nav
            className="flex items-center justify-center gap-4 mt-10"
            aria-label="Blog pagination"
          >
            <Button
              variant="outline"
              onClick={() => goToPage(page - 1)}
              disabled={page <= 1}
              leftIcon={<ChevronLeft className="w-4 h-4" />}
            >
              Previous
            </Button>
            <span className="text-neutral-600">
              Page {page} of {totalPages}
            </span>
            <Button
              variant="outline"
              onClick={() => goToPage(page + 1)}
              disabled={page >= totalPages}
              rightIcon={<ChevronRight className="w-4 h-4" />}
            >
              Next
            </Button>
          </nav>
        )}
      </div>
    </PageLayout>
  );
};
