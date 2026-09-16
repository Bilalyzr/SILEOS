import { PageLayout, PageHeader } from "@/components/design-system/PageLayout";
import * as React from "react";
import { Link } from "react-router-dom";
import { Plus, Edit, Trash2, Eye, Calendar, MessageCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { api } from "@/api/axios";
import toast from "react-hot-toast";
import * as Dialog from "@radix-ui/react-dialog";

interface BlogPost {
  id: number;
  title: string;
  slug: string;
  excerpt: string | null;
  featured_image: string | null;
  status: string;
  category: string | null;
  view_count: number;
  comment_count: number;
  post_date: string;
  post_modified: string;
}

export const InstructorBlogPage = () => {
  const [posts, setPosts] = React.useState<BlogPost[]>([]);
  const [isLoading, setIsLoading] = React.useState(true);
  const [deleteDialogOpen, setDeleteDialogOpen] = React.useState(false);
  const [postToDelete, setPostToDelete] = React.useState<BlogPost | null>(null);
  const [isDeleting, setIsDeleting] = React.useState(false);

  React.useEffect(() => {
    fetchPosts();
  }, []);

  const fetchPosts = async () => {
    try {
      setIsLoading(true);
      const response = await api.get("/blog/instructor/my-posts");
      setPosts(response.data);
    } catch (error) {
      console.error("Failed to fetch blog posts:", error);
      toast.error("Failed to load blog posts");
    } finally {
      setIsLoading(false);
    }
  };

  const handleDelete = async () => {
    if (!postToDelete) return;

    try {
      setIsDeleting(true);
      await api.delete(`/blog/${postToDelete.id}`);
      toast.success("Blog post deleted successfully");
      setPosts(posts.filter((p) => p.id !== postToDelete.id));
      setDeleteDialogOpen(false);
      setPostToDelete(null);
    } catch (error) {
      console.error("Failed to delete blog post:", error);
      toast.error("Failed to delete blog post");
    } finally {
      setIsDeleting(false);
    }
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  };

  return (
    <PageLayout
      header={
        <PageHeader>
          <div>
            <h1 className="dash-h1 mb-1">My Blog Posts</h1>
            <p className="text-slate-600 text-sm">
              Manage your blog content and engage with your audience
            </p>
          </div>
          <Link to="/instructor/blog/create">
            <Button>
              <Plus className="w-4 h-4 mr-2" />
              New Post
            </Button>
          </Link>
        </PageHeader>
      }
      className="rd-screen rd-screen-instructor-blog"
    >
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <div className="dash-card p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-neutral-600 mb-1">Total Posts</p>
              <p className="text-2xl font-bold text-neutral-900">
                {posts.length}
              </p>
            </div>
            <div className="w-12 h-12 bg-primary-100 rounded-lg flex items-center justify-center">
              <Edit className="w-6 h-6 text-primary-600" />
            </div>
          </div>
        </div>

        <div className="dash-card p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-neutral-600 mb-1">Total Views</p>
              <p className="text-2xl font-bold text-neutral-900">
                {posts.reduce((sum, p) => sum + p.view_count, 0)}
              </p>
            </div>
            <div className="w-12 h-12 bg-success-100 rounded-lg flex items-center justify-center">
              <Eye className="w-6 h-6 text-success-600" />
            </div>
          </div>
        </div>

        <div className="dash-card p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-neutral-600 mb-1">Total Comments</p>
              <p className="text-2xl font-bold text-neutral-900">
                {posts.reduce((sum, p) => sum + p.comment_count, 0)}
              </p>
            </div>
            <div className="w-12 h-12 bg-warning-100 rounded-lg flex items-center justify-center">
              <MessageCircle className="w-6 h-6 text-warning-600" />
            </div>
          </div>
        </div>
      </div>
      {isLoading ? (
        <div className="space-y-4">
          {Array.from({ length: 3 }).map((_, i) => (
            <div
              key={i}
              className="bg-white rounded-lg p-6 animate-pulse"
              data-glass="content"
            >
              <div className="h-6 bg-neutral-200 rounded w-3/4 mb-4"></div>
              <div className="h-4 bg-neutral-200 rounded w-1/2"></div>
            </div>
          ))}
        </div>
      ) : posts.length === 0 ? (
        <div className="dash-card p-12 text-center">
          <div className="w-24 h-24 bg-neutral-100 rounded-full flex items-center justify-center mx-auto mb-6">
            <Edit className="w-12 h-12 text-neutral-400" />
          </div>
          <h3 className="text-xl font-semibold text-neutral-900 mb-2">
            No blog posts yet
          </h3>
          <p className="text-neutral-600 mb-6">
            Start sharing your knowledge and engage with your students by
            creating your first blog post
          </p>
          <Link to="/instructor/blog/create">
            <Button>
              <Plus className="w-4 h-4 mr-2" />
              Create Your First Post
            </Button>
          </Link>
        </div>
      ) : (
        <div className="dash-card overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-neutral-50 border-b border-neutral-200">
                <tr>
                  <th className="px-6 py-4 text-left text-sm font-semibold text-neutral-900">
                    Title
                  </th>
                  <th className="px-6 py-4 text-left text-sm font-semibold text-neutral-900">
                    Status
                  </th>
                  <th className="px-6 py-4 text-left text-sm font-semibold text-neutral-900">
                    Date
                  </th>
                  <th className="px-6 py-4 text-left text-sm font-semibold text-neutral-900">
                    Views
                  </th>
                  <th className="px-6 py-4 text-left text-sm font-semibold text-neutral-900">
                    Comments
                  </th>
                  <th className="px-6 py-4 text-right text-sm font-semibold text-neutral-900">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-neutral-200">
                {posts.map((post) => (
                  <tr
                    key={post.id}
                    className="hover:bg-neutral-50 transition-colors"
                  >
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-3">
                        {post.featured_image ? (
                          <img
                            src={post.featured_image}
                            alt={post.title}
                            className="w-16 h-16 object-cover rounded"
                          />
                        ) : (
                          <div className="w-16 h-16 bg-neutral-200 rounded flex items-center justify-center">
                            <span className="text-2xl text-neutral-500 font-bold">
                              {post.title.charAt(0)}
                            </span>
                          </div>
                        )}
                        <div className="flex-1 min-w-0">
                          <Link
                            to={`/blog/${post.slug}`}
                            className="font-medium text-neutral-900 hover:text-primary-600 block truncate"
                          >
                            {post.title}
                          </Link>
                          {post.category && (
                            <Badge variant="outline" className="mt-1">
                              {post.category}
                            </Badge>
                          )}
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <Badge
                        variant={
                          post.status === "PUBLISHED" ? "success" : "default"
                        }
                      >
                        {post.status}
                      </Badge>
                    </td>
                    <td className="px-6 py-4 text-sm text-neutral-600">
                      <div className="flex items-center gap-2">
                        <Calendar className="w-4 h-4" />
                        {formatDate(post.post_date)}
                      </div>
                    </td>
                    <td className="px-6 py-4 text-sm text-neutral-600">
                      <div className="flex items-center gap-2">
                        <Eye className="w-4 h-4" />
                        {post.view_count}
                      </div>
                    </td>
                    <td className="px-6 py-4 text-sm text-neutral-600">
                      <div className="flex items-center gap-2">
                        <MessageCircle className="w-4 h-4" />
                        {post.comment_count}
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center justify-end gap-2">
                        <Link to={`/blog/${post.slug}`}>
                          <Button variant="ghost" size="sm">
                            <Eye className="w-4 h-4" />
                          </Button>
                        </Link>
                        <Link to={`/instructor/blog/edit/${post.id}`}>
                          <Button variant="ghost" size="sm">
                            <Edit className="w-4 h-4" />
                          </Button>
                        </Link>
                        <Button
                          variant="ghost"
                          size="sm"
                          className="text-danger-600 hover:text-danger-700 hover:bg-danger-50"
                          onClick={() => {
                            setPostToDelete(post);
                            setDeleteDialogOpen(true);
                          }}
                        >
                          <Trash2 className="w-4 h-4" />
                        </Button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
      <Dialog.Root open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <Dialog.Portal>
          <Dialog.Overlay className="fixed inset-0 bg-black/50 z-50" />
          <Dialog.Content className="fixed top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 bg-white rounded-lg shadow-xl p-6 w-full max-w-md z-50">
            <Dialog.Title className="text-xl font-bold text-neutral-900 mb-4">
              Delete Blog Post
            </Dialog.Title>
            <Dialog.Description className="text-neutral-600 mb-6">
              Are you sure you want to delete "{postToDelete?.title}"? This
              action cannot be undone.
            </Dialog.Description>
            <div className="flex items-center gap-3 justify-end">
              <Dialog.Close asChild>
                <Button variant="outline" disabled={isDeleting}>
                  Cancel
                </Button>
              </Dialog.Close>
              <Button
                variant="destructive"
                onClick={handleDelete}
                disabled={isDeleting}
              >
                {isDeleting ? "Deleting..." : "Delete"}
              </Button>
            </div>
          </Dialog.Content>
        </Dialog.Portal>
      </Dialog.Root>
    </PageLayout>
  );
};
