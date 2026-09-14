import { PageLayout, PageHeader } from "@/components/design-system/PageLayout";
import { useCallback } from "react";
import { useState, useEffect } from "react";
import { confirmDialog } from "@/components/ui/confirm";
import {
  Plus,
  Edit,
  Trash2,
  Search,
  Eye,
  Calendar,
  FileText,
  CheckCircle,
  XCircle,
  ChevronLeft,
  ChevronRight,
  Check,
  X,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  getAdminBlogs,
  getAdminBlogCategories,
  updateBlogStatus,
  deleteBlog,
  bulkDeleteBlogs,
  type Blog,
} from "@/api/blog";
import toast from "react-hot-toast";
import { ExportImportPanel } from "@/components/admin/ExportImportPanel";

export function AdminBlogs() {
  const [blogs, setBlogs] = useState<Blog[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [categoryFilter, setCategoryFilter] = useState<string>("all");
  const [categories, setCategories] = useState<string[]>([]);
  const [selectedBlogs, setSelectedBlogs] = useState<Set<number>>(new Set());
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [total, setTotal] = useState(0);
  const pageSize = 20;

  const fetchBlogs = useCallback(async () => {
    try {
      setLoading(true);
      const params: any = {
        page: currentPage,
        page_size: pageSize,
      };

      if (searchQuery) params.search = searchQuery;
      if (statusFilter !== "all") params.status = statusFilter;
      if (categoryFilter !== "all") params.category = categoryFilter;

      const response = await getAdminBlogs(params);
      setBlogs(response.blogs);
      setTotal(response.total);
      setTotalPages(response.total_pages);
    } catch (error: any) {
      console.error("Error fetching blogs:", error);
      toast.error("Failed to fetch blogs");
    } finally {
      setLoading(false);
    }
  }, [categoryFilter, currentPage, searchQuery, statusFilter]);
  useEffect(() => {
    fetchBlogs();
  }, [currentPage, statusFilter, categoryFilter, fetchBlogs]);

  // Categories come from a dedicated endpoint. They must NOT be derived from
  // the blog list response: that response is filtered and paginated, so
  // selecting a category would leave only that category in the dropdown.
  const fetchCategories = async () => {
    try {
      setCategories(await getAdminBlogCategories());
    } catch (error: any) {
      console.error("Error fetching blog categories:", error);
    }
  };

  useEffect(() => {
    fetchCategories();
  }, []);

  const handleSearch = () => {
    setCurrentPage(1);
    fetchBlogs();
  };

  const handleStatusToggle = async (blog: Blog) => {
    const newStatus = blog.status === "published" ? "draft" : "published";
    try {
      await updateBlogStatus(blog.id, newStatus);
      toast.success(
        `Blog ${newStatus === "published" ? "published" : "unpublished"} successfully`,
      );
      fetchBlogs();
    } catch (error: any) {
      console.error("Error updating blog status:", error);
      toast.error(
        error.response?.data?.detail || "Failed to update blog status",
      );
    }
  };

  const handleDelete = async (blogId: number) => {
    if (!(await confirmDialog("Are you sure you want to delete this blog?")))
      return;

    try {
      await deleteBlog(blogId);
      toast.success("Blog deleted successfully");
      fetchBlogs();
      fetchCategories();
    } catch (error: any) {
      console.error("Error deleting blog:", error);
      toast.error(error.response?.data?.detail || "Failed to delete blog");
    }
  };

  const handleApprove = async (blog: Blog) => {
    try {
      await updateBlogStatus(blog.id, "published");
      toast.success("Blog approved and published successfully");
      fetchBlogs();
    } catch (error: any) {
      console.error("Error approving blog:", error);
      toast.error(error.response?.data?.detail || "Failed to approve blog");
    }
  };

  const handleReject = async (blog: Blog) => {
    try {
      await updateBlogStatus(blog.id, "draft");
      toast.success("Blog rejected and sent to draft");
      fetchBlogs();
    } catch (error: any) {
      console.error("Error rejecting blog:", error);
      toast.error(error.response?.data?.detail || "Failed to reject blog");
    }
  };

  const handleBulkDelete = async () => {
    if (selectedBlogs.size === 0) {
      toast.error("Please select at least one blog to delete");
      return;
    }

    if (
      !(await confirmDialog(
        `Are you sure you want to delete ${selectedBlogs.size} blog(s)?`,
      ))
    )
      return;

    try {
      await bulkDeleteBlogs(Array.from(selectedBlogs));
      toast.success(`${selectedBlogs.size} blog(s) deleted successfully`);
      setSelectedBlogs(new Set());
      fetchBlogs();
      fetchCategories();
    } catch (error: any) {
      console.error("Error bulk deleting blogs:", error);
      toast.error(error.response?.data?.detail || "Failed to delete blogs");
    }
  };

  const handleSelectAll = () => {
    if (selectedBlogs.size === blogs.length) {
      setSelectedBlogs(new Set());
    } else {
      setSelectedBlogs(new Set(blogs.map((b) => b.id)));
    }
  };

  const handleSelectBlog = (blogId: number) => {
    const newSelected = new Set(selectedBlogs);
    if (newSelected.has(blogId)) {
      newSelected.delete(blogId);
    } else {
      newSelected.add(blogId);
    }
    setSelectedBlogs(newSelected);
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  };

  // Keep the active filter selectable even if its last post was just deleted,
  // so the <select> never renders with a value that has no matching option.
  const categoryOptions =
    categoryFilter !== "all" && !categories.includes(categoryFilter)
      ? [...categories, categoryFilter].sort()
      : categories;

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <PageLayout
        header={
          <PageHeader>
            <h1 className="text-3xl font-bold text-gray-900 mb-2">
              Blog Management
            </h1>
            <p className="text-gray-600">Create and manage blog posts</p>
          </PageHeader>
        }
        className="rd-screen rd-screen-admin-blogs"
      >
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
          <div className="bg-white rounded-lg shadow p-6" data-glass="content">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Total Blogs</p>
                <p className="text-2xl font-bold text-gray-900">{total}</p>
              </div>
              <FileText className="w-10 h-10 text-blue-500" />
            </div>
          </div>

          <div className="bg-white rounded-lg shadow p-6" data-glass="content">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Published</p>
                <p className="text-2xl font-bold text-green-600">
                  {blogs.filter((b) => b.status === "published").length}
                </p>
              </div>
              <CheckCircle className="w-10 h-10 text-green-500" />
            </div>
          </div>

          <div className="bg-white rounded-lg shadow p-6" data-glass="content">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Drafts</p>
                <p className="text-2xl font-bold text-gray-600">
                  {blogs.filter((b) => b.status === "draft").length}
                </p>
              </div>
              <XCircle className="w-10 h-10 text-gray-500" />
            </div>
          </div>

          <div className="bg-white rounded-lg shadow p-6" data-glass="content">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Pending</p>
                <p className="text-2xl font-bold text-yellow-600">
                  {blogs.filter((b) => b.status === "pending").length}
                </p>
              </div>
              <Calendar className="w-10 h-10 text-yellow-500" />
            </div>
          </div>

          <div className="bg-white rounded-lg shadow p-6" data-glass="content">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Total Views</p>
                <p className="text-2xl font-bold text-purple-600">
                  {blogs.reduce((sum, b) => sum + b.views, 0)}
                </p>
              </div>
              <Eye className="w-10 h-10 text-purple-500" />
            </div>
          </div>
        </div>
        <div className="bg-white rounded-lg shadow p-6 mb-6" data-glass="work">
          <div className="flex flex-col md:flex-row gap-4">
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
              <Input
                type="text"
                placeholder="Search blogs..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleSearch()}
                className="pl-10"
              />
            </div>

            <div className="flex gap-2">
              <select
                value={statusFilter}
                onChange={(e) => {
                  setStatusFilter(e.target.value);
                  setCurrentPage(1);
                }}
                className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                <option value="all">All Status</option>
                <option value="published">Published</option>
                <option value="draft">Draft</option>
                <option value="pending">Pending</option>
              </select>

              <select
                value={categoryFilter}
                onChange={(e) => {
                  setCategoryFilter(e.target.value);
                  setCurrentPage(1);
                }}
                className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                <option value="all">All Categories</option>
                {categoryOptions.map((cat) => (
                  <option key={cat} value={cat}>
                    {cat}
                  </option>
                ))}
              </select>

              {selectedBlogs.size > 0 && (
                <Button
                  variant="destructive"
                  onClick={handleBulkDelete}
                  className="flex items-center gap-2"
                >
                  <Trash2 className="w-4 h-4" />
                  Delete ({selectedBlogs.size})
                </Button>
              )}

              <ExportImportPanel
                section="blogs"
                onImportComplete={fetchBlogs}
              />

              <Button
                onClick={() => (window.location.href = "/admin/blogs/create")}
                className="flex items-center gap-2"
              >
                <Plus className="w-5 h-5" />
                Create New Blog
              </Button>
            </div>
          </div>
        </div>
        <div
          className="bg-white rounded-lg shadow overflow-hidden"
          data-glass="work"
        >
          {loading ? (
            <div className="p-12 text-center">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
              <p className="mt-4 text-gray-600">Loading blogs...</p>
            </div>
          ) : blogs.length === 0 ? (
            <div className="p-12 text-center">
              <FileText className="w-16 h-16 text-gray-400 mx-auto mb-4" />
              <p className="text-xl text-gray-600 mb-2">No blogs found</p>
              <p className="text-gray-500">
                Create your first blog post to get started
              </p>
            </div>
          ) : (
            <>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-gray-50 border-b">
                    <tr>
                      <th className="px-4 py-3 text-left">
                        <input
                          type="checkbox"
                          checked={
                            selectedBlogs.size === blogs.length &&
                            blogs.length > 0
                          }
                          onChange={handleSelectAll}
                          className="rounded"
                        />
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Title
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Author
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Status
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Category
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Views
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Date
                      </th>
                      <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Actions
                      </th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {blogs.map((blog) => (
                      <tr key={blog.id} className="hover:bg-gray-50">
                        <td className="px-4 py-4">
                          <input
                            type="checkbox"
                            checked={selectedBlogs.has(blog.id)}
                            onChange={() => handleSelectBlog(blog.id)}
                            className="rounded"
                          />
                        </td>
                        <td className="px-6 py-4">
                          <div className="text-sm font-medium text-gray-900">
                            {blog.title}
                          </div>
                          <div className="text-sm text-gray-500 truncate max-w-xs">
                            {blog.category || "No category"}
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                          {blog.author_name}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <Badge
                            variant={
                              blog.status === "published"
                                ? "success"
                                : blog.status === "pending"
                                  ? "warning"
                                  : "neutral"
                            }
                          >
                            {blog.status === "published"
                              ? "Published"
                              : blog.status === "pending"
                                ? "Pending"
                                : "Draft"}
                          </Badge>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                          {blog.category || "-"}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                          <div className="flex items-center gap-1">
                            <Eye className="w-4 h-4" />
                            {blog.views}
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                          <div className="flex items-center gap-1">
                            <Calendar className="w-4 h-4" />
                            {formatDate(blog.created_at)}
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                          <div className="flex items-center justify-end gap-2">
                            <button
                              onClick={() =>
                                (window.location.href = `/admin/blogs/edit/${blog.id}`)
                              }
                              className="text-blue-600 hover:text-blue-900"
                              title="Edit"
                            >
                              <Edit className="w-5 h-5" />
                            </button>
                            {blog.status === "pending" ? (
                              <>
                                <button
                                  onClick={() => handleApprove(blog)}
                                  className="text-green-600 hover:text-green-900"
                                  title="Approve & Publish"
                                >
                                  <Check className="w-5 h-5" />
                                </button>
                                <button
                                  onClick={() => handleReject(blog)}
                                  className="text-red-600 hover:text-red-900"
                                  title="Reject (Send to Draft)"
                                >
                                  <X className="w-5 h-5" />
                                </button>
                              </>
                            ) : (
                              <button
                                onClick={() => handleStatusToggle(blog)}
                                className={`${
                                  blog.status === "published"
                                    ? "text-orange-600 hover:text-orange-900"
                                    : "text-green-600 hover:text-green-900"
                                }`}
                                title={
                                  blog.status === "published"
                                    ? "Unpublish"
                                    : "Publish"
                                }
                              >
                                {blog.status === "published" ? (
                                  <XCircle className="w-5 h-5" />
                                ) : (
                                  <CheckCircle className="w-5 h-5" />
                                )}
                              </button>
                            )}
                            <button
                              onClick={() => handleDelete(blog.id)}
                              className="text-red-600 hover:text-red-900"
                              title="Delete"
                            >
                              <Trash2 className="w-5 h-5" />
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Pagination */}
              <div className="bg-gray-50 px-6 py-4 border-t flex items-center justify-between">
                <div className="text-sm text-gray-700">
                  Showing {Math.min((currentPage - 1) * pageSize + 1, total)} to{" "}
                  {Math.min(currentPage * pageSize, total)} of {total} results
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                    disabled={currentPage === 1}
                    className="p-2 rounded border border-gray-300 hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <ChevronLeft className="w-4 h-4" />
                  </button>
                  <span className="text-sm text-gray-700">
                    Page {currentPage} of {totalPages}
                  </span>
                  <button
                    onClick={() =>
                      setCurrentPage((p) => Math.min(totalPages, p + 1))
                    }
                    disabled={currentPage === totalPages}
                    className="p-2 rounded border border-gray-300 hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <ChevronRight className="w-4 h-4" />
                  </button>
                </div>
              </div>
            </>
          )}
        </div>
      </PageLayout>
    </div>
  );
}
