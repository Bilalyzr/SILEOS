import { PageLayout, PageHeader } from "@/components/design-system/PageLayout";
import { useCallback } from "react";
import * as React from "react";
import { useNavigate, useParams } from "react-router-dom";
import {
  ArrowLeft,
  Save,
  Eye,
  HelpCircle,
  Copy,
  CheckCircle,
  X,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { api } from "@/api/axios";
import toast from "react-hot-toast";
import { ImageUpload } from "@/components/upload";
import * as Dialog from "@radix-ui/react-dialog";
import { internshipApi } from "@/api/internship";
import { useAuthStore } from "@/store/auth";

interface BlogForm {
  title: string;
  content: string;
  excerpt: string;
  featured_image: string;
  category: string;
  tags: string;
  meta_title: string;
  meta_description: string;
  status: "DRAFT" | "PUBLISHED";
  related_course_ids: number[];
  related_internship_ids: number[];
}

export const BlogEditorPage = () => {
  const navigate = useNavigate();
  const { id } = useParams<{ id: string }>();
  const isEditMode = Boolean(id);
  const { user } = useAuthStore();

  // Determine correct blog route based on user role.
  // Students have no blog list page, so they return to their dashboard.
  const getBlogRoute = () =>
    user?.role === "admin"
      ? "/admin/blogs"
      : user?.role === "student"
        ? "/dashboard"
        : "/instructor/blog";

  const [form, setForm] = React.useState<BlogForm>({
    title: "",
    content: "",
    excerpt: "",
    featured_image: "",
    category: "",
    tags: "",
    meta_title: "",
    meta_description: "",
    status: "DRAFT",
    related_course_ids: [],
    related_internship_ids: [],
  });

  const [isLoading, setIsLoading] = React.useState(false);
  const [isSaving, setIsSaving] = React.useState(false);
  const [showGuidelinesModal, setShowGuidelinesModal] = React.useState(false);
  const [copiedPrompt, setCopiedPrompt] = React.useState(false);

  // Related courses and internships
  const [courses, setCourses] = React.useState<any[]>([]);
  const [internships, setInternships] = React.useState<any[]>([]);
  const [isLoadingCourses, setIsLoadingCourses] = React.useState(false);
  const [isLoadingInternships, setIsLoadingInternships] = React.useState(false);
  const [showCourseDropdown, setShowCourseDropdown] = React.useState(false);
  const [showInternshipDropdown, setShowInternshipDropdown] =
    React.useState(false);

  // Fetch post data if editing
  const fetchPost = useCallback(async () => {
    try {
      setIsLoading(true);
      // Use the get-by-id endpoint which works for any user's blog (admin can edit others')
      const response = await api.get(`/blog/id/${id}`);
      const post = response.data;

      if (post) {
        setForm({
          title: post.title || "",
          content: post.content || "",
          excerpt: post.excerpt || "",
          featured_image: post.featured_image || "",
          category: post.category || "",
          tags: post.tags || "",
          meta_title: post.meta_title || "",
          meta_description: post.meta_description || "",
          status: post.status || "DRAFT",
          related_course_ids: post.related_course_ids || [],
          related_internship_ids: post.related_internship_ids || [],
        });
      }
    } catch (error) {
      console.error("Failed to fetch post:", error);
      toast.error("Failed to load blog post");
    } finally {
      setIsLoading(false);
    }
  }, [id]);
  React.useEffect(() => {
    if (isEditMode && id) {
      fetchPost();
    }
    fetchCourses();
    fetchInternships();
  }, [isEditMode, id, fetchPost]);

  const fetchCourses = async () => {
    try {
      setIsLoadingCourses(true);
      const response = await api.get<{
        courses: { id: number; title: string }[];
      }>("/courses", { params: { page_size: 100 } });
      setCourses(response.data.courses || []);
    } catch (error) {
      console.error("Failed to fetch courses:", error);
      setCourses([]);
    } finally {
      setIsLoadingCourses(false);
    }
  };

  const fetchInternships = async () => {
    try {
      setIsLoadingInternships(true);
      const response = await internshipApi.list();
      setInternships(response || []);
    } catch (error) {
      console.error("Failed to fetch internships:", error);
    } finally {
      setIsLoadingInternships(false);
    }
  };

  const handleInputChange = (
    e: React.ChangeEvent<
      HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement
    >,
  ) => {
    const { name, value } = e.target;
    setForm((prev) => ({ ...prev, [name]: value }));
  };

  const handleCopyPrompt = () => {
    const aiPrompt = `Convert the following content into beautifully formatted HTML for a blog post.

Requirements:
- Use semantic HTML5 tags (article, section, h1-h6, p, ul, ol, blockquote, code, pre, etc.)
- Add appropriate CSS classes for styling (use Tailwind CSS classes if applicable)
- Ensure proper heading hierarchy
- Format code blocks with <pre><code> tags
- Use <blockquote> for quotes
- Add proper spacing and line breaks
- Make it mobile-responsive
- Preserve the original meaning and structure

Content to convert:
[PASTE YOUR CONTENT HERE]

Please return only the HTML code without any explanations.`;

    navigator.clipboard.writeText(aiPrompt);
    setCopiedPrompt(true);
    toast.success("AI prompt copied to clipboard!");

    setTimeout(() => setCopiedPrompt(false), 3000);
  };

  const handleSave = async (status: "DRAFT" | "PUBLISHED") => {
    // Validation
    if (!form.title.trim()) {
      toast.error("Please enter a title");
      return;
    }

    if (!form.content.trim()) {
      toast.error("Please enter content");
      return;
    }

    try {
      setIsSaving(true);

      const data = {
        ...form,
        status,
        excerpt: form.excerpt || form.content.substring(0, 200) + "...",
      };

      if (isEditMode && id) {
        // Update existing post
        await api.put(`/blog/${id}`, data);
        toast.success(
          `Blog post ${status === "PUBLISHED" ? "published" : "saved as draft"} successfully`,
        );
      } else {
        // Create new post
        await api.post("/blog/", data);
        toast.success(
          `Blog post ${status === "PUBLISHED" ? "published" : "created as draft"} successfully`,
        );
      }

      navigate(getBlogRoute());
    } catch (error: any) {
      console.error("Failed to save blog post:", error);
      toast.error(error.response?.data?.detail || "Failed to save blog post");
    } finally {
      setIsSaving(false);
    }
  };

  if (isLoading) {
    return (
      <div className="container-custom py-8">
        <div className="max-w-4xl mx-auto">
          <div
            className="bg-white rounded-lg shadow-soft p-8 animate-pulse"
            data-glass="content"
          >
            <div className="h-8 bg-neutral-200 rounded w-1/3 mb-6"></div>
            <div className="space-y-4">
              <div className="h-10 bg-neutral-200 rounded"></div>
              <div className="h-64 bg-neutral-200 rounded"></div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="container-custom py-8">
      <PageLayout
        header={
          <PageHeader>
            <div className="flex items-center gap-4">
              <Button
                variant="ghost"
                onClick={() => navigate(getBlogRoute())}
                className="text-neutral-600 hover:text-neutral-900"
              >
                <ArrowLeft className="w-4 h-4 mr-2" />
                Back
              </Button>
              <h1 className="text-3xl font-bold text-neutral-900">
                {isEditMode ? "Edit Blog Post" : "Create New Blog Post"}
              </h1>
            </div>
            <div className="flex items-center gap-3">
              <Button
                variant="outline"
                onClick={() => handleSave("DRAFT")}
                disabled={isSaving}
              >
                <Save className="w-4 h-4 mr-2" />
                Save Draft
              </Button>
              <Button
                onClick={() => handleSave("PUBLISHED")}
                disabled={isSaving}
              >
                <Eye className="w-4 h-4 mr-2" />
                {isSaving ? "Publishing..." : "Publish"}
              </Button>
            </div>
          </PageHeader>
        }
        className="rd-screen rd-screen-instructor-blog-editor"
      >
        <div
          className="bg-white rounded-lg shadow-soft p-8 space-y-6"
          data-glass="work"
        >
          {/* Title */}
          <div>
            <label className="block text-sm font-medium text-neutral-700 mb-2">
              Title <span className="text-danger-600">*</span>
            </label>
            <Input
              name="title"
              value={form.title}
              onChange={handleInputChange}
              placeholder="Enter blog post title..."
              className="text-lg"
            />
          </div>

          {/* Featured Image */}
          <div>
            <label className="block text-sm font-medium text-neutral-700 mb-2">
              Featured Image
            </label>
            <ImageUpload
              value={form.featured_image}
              onChange={(url) =>
                setForm((prev) => ({ ...prev, featured_image: url }))
              }
              className="mb-2"
            />
            {form.featured_image && (
              <div className="mt-4">
                <img
                  src={form.featured_image}
                  alt="Featured"
                  className="w-full max-w-2xl rounded-lg"
                />
              </div>
            )}
          </div>

          {/* Content */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="block text-sm font-medium text-neutral-700">
                Content <span className="text-danger-600">*</span>
              </label>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => setShowGuidelinesModal(true)}
                className="text-primary-600 hover:text-primary-700"
              >
                <HelpCircle className="w-4 h-4 mr-2" />
                HTML Guidelines
              </Button>
            </div>
            <textarea
              name="content"
              value={form.content}
              onChange={handleInputChange}
              rows={16}
              placeholder="Write your blog content here..."
              className="w-full px-4 py-3 border border-neutral-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent resize-none font-mono text-sm"
            />
            <p className="text-sm text-neutral-500 mt-2">
              Tip: You can use HTML for formatting. Click "HTML Guidelines" for
              AI conversion tips.
            </p>
          </div>

          {/* Excerpt */}
          <div>
            <label className="block text-sm font-medium text-neutral-700 mb-2">
              Excerpt
            </label>
            <textarea
              name="excerpt"
              value={form.excerpt}
              onChange={handleInputChange}
              rows={3}
              placeholder="Brief summary of your blog post (optional, auto-generated if left empty)"
              className="w-full px-4 py-3 border border-neutral-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent resize-none"
            />
          </div>

          {/* Category and Tags */}
          <div className="grid md:grid-cols-2 gap-6">
            <div>
              <label className="block text-sm font-medium text-neutral-700 mb-2">
                Category
              </label>
              <Input
                name="category"
                value={form.category}
                onChange={handleInputChange}
                placeholder="e.g., Tutorial, News, Tips"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-neutral-700 mb-2">
                Tags
              </label>
              <Input
                name="tags"
                value={form.tags}
                onChange={handleInputChange}
                placeholder="comma, separated, tags"
              />
            </div>
          </div>

          {/* Related Courses */}
          <div className="relative">
            <label className="block text-sm font-medium text-neutral-700 mb-2">
              Related Courses
            </label>
            <div
              className="w-full px-4 py-3 border border-neutral-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent min-h-[48px] cursor-text"
              onClick={() => setShowCourseDropdown(!showCourseDropdown)}
            >
              {form.related_course_ids.length === 0 ? (
                <span className="text-neutral-400">
                  Select courses to link to this post...
                </span>
              ) : (
                <div className="flex flex-wrap gap-2">
                  {form.related_course_ids.map((courseId) => {
                    const course = courses.find((c) => c.id === courseId);
                    return course ? (
                      <span
                        key={courseId}
                        className="inline-flex items-center gap-1 bg-primary-100 text-primary-700 px-3 py-1 rounded-full text-sm"
                        onClick={(e) => {
                          e.stopPropagation();
                          setForm((prev) => ({
                            ...prev,
                            related_course_ids: prev.related_course_ids.filter(
                              (id) => id !== courseId,
                            ),
                          }));
                        }}
                      >
                        {course.title}
                        <X className="w-3 h-3 cursor-pointer hover:text-primary-900" />
                      </span>
                    ) : null;
                  })}
                </div>
              )}
            </div>

            {showCourseDropdown && (
              <div className="absolute z-10 w-full mt-1 bg-white border border-neutral-300 rounded-lg shadow-lg max-h-60 overflow-y-auto">
                {isLoadingCourses ? (
                  <div className="p-4 text-center text-neutral-500">
                    Loading courses...
                  </div>
                ) : courses.length === 0 ? (
                  <div className="p-4 text-center text-neutral-500">
                    No courses available
                  </div>
                ) : (
                  courses.map((course) => (
                    <div
                      key={course.id}
                      className={`px-4 py-3 hover:bg-neutral-50 cursor-pointer flex items-center gap-3 ${
                        form.related_course_ids.includes(course.id)
                          ? "bg-primary-50"
                          : ""
                      }`}
                      onClick={() => {
                        setForm((prev) => ({
                          ...prev,
                          related_course_ids: prev.related_course_ids.includes(
                            course.id,
                          )
                            ? prev.related_course_ids.filter(
                                (id) => id !== course.id,
                              )
                            : [...prev.related_course_ids, course.id],
                        }));
                      }}
                    >
                      <input
                        type="checkbox"
                        checked={form.related_course_ids.includes(course.id)}
                        onChange={() => {}}
                        className="rounded border-neutral-300 text-primary-600 focus:ring-primary-500"
                        readOnly
                      />
                      <div className="flex-1">
                        <div className="font-medium text-neutral-900">
                          {course.title}
                        </div>
                        {course.thumbnail && (
                          <img
                            src={course.thumbnail}
                            alt=""
                            className="w-8 h-8 object-cover rounded mt-1"
                          />
                        )}
                      </div>
                    </div>
                  ))
                )}
              </div>
            )}
          </div>

          {/* Related Internships */}
          <div className="relative">
            <label className="block text-sm font-medium text-neutral-700 mb-2">
              Related Internships
            </label>
            <div
              className="w-full px-4 py-3 border border-neutral-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent min-h-[48px] cursor-text"
              onClick={() => setShowInternshipDropdown(!showInternshipDropdown)}
            >
              {form.related_internship_ids.length === 0 ? (
                <span className="text-neutral-400">
                  Select internships to link to this post...
                </span>
              ) : (
                <div className="flex flex-wrap gap-2">
                  {form.related_internship_ids.map((internshipId) => {
                    const internship = internships.find(
                      (i) => i.id === internshipId,
                    );
                    return internship ? (
                      <span
                        key={internshipId}
                        className="inline-flex items-center gap-1 bg-secondary-100 text-secondary-700 px-3 py-1 rounded-full text-sm"
                        onClick={(e) => {
                          e.stopPropagation();
                          setForm((prev) => ({
                            ...prev,
                            related_internship_ids:
                              prev.related_internship_ids.filter(
                                (id) => id !== internshipId,
                              ),
                          }));
                        }}
                      >
                        {internship.title}
                        <X className="w-3 h-3 cursor-pointer hover:text-secondary-900" />
                      </span>
                    ) : null;
                  })}
                </div>
              )}
            </div>

            {showInternshipDropdown && (
              <div className="absolute z-10 w-full mt-1 bg-white border border-neutral-300 rounded-lg shadow-lg max-h-60 overflow-y-auto">
                {isLoadingInternships ? (
                  <div className="p-4 text-center text-neutral-500">
                    Loading internships...
                  </div>
                ) : internships.length === 0 ? (
                  <div className="p-4 text-center text-neutral-500">
                    No internships available
                  </div>
                ) : (
                  internships.map((internship) => (
                    <div
                      key={internship.id}
                      className={`px-4 py-3 hover:bg-neutral-50 cursor-pointer flex items-center gap-3 ${
                        form.related_internship_ids.includes(internship.id)
                          ? "bg-secondary-50"
                          : ""
                      }`}
                      onClick={() => {
                        setForm((prev) => ({
                          ...prev,
                          related_internship_ids:
                            prev.related_internship_ids.includes(internship.id)
                              ? prev.related_internship_ids.filter(
                                  (id) => id !== internship.id,
                                )
                              : [...prev.related_internship_ids, internship.id],
                        }));
                      }}
                    >
                      <input
                        type="checkbox"
                        checked={form.related_internship_ids.includes(
                          internship.id,
                        )}
                        onChange={() => {}}
                        className="rounded border-neutral-300 text-secondary-600 focus:ring-secondary-500"
                        readOnly
                      />
                      <div className="flex-1">
                        <div className="font-medium text-neutral-900">
                          {internship.title}
                        </div>
                      </div>
                    </div>
                  ))
                )}
              </div>
            )}
          </div>

          {/* SEO Section */}
          <div className="border-t border-neutral-200 pt-6">
            <h3 className="text-lg font-semibold text-neutral-900 mb-4">
              SEO Settings (Optional)
            </h3>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-neutral-700 mb-2">
                  Meta Title
                </label>
                <Input
                  name="meta_title"
                  value={form.meta_title}
                  onChange={handleInputChange}
                  placeholder="SEO title (defaults to post title)"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-neutral-700 mb-2">
                  Meta Description
                </label>
                <textarea
                  name="meta_description"
                  value={form.meta_description}
                  onChange={handleInputChange}
                  rows={3}
                  placeholder="SEO description (defaults to excerpt)"
                  className="w-full px-4 py-3 border border-neutral-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent resize-none"
                />
              </div>
            </div>
          </div>

          {/* Status Info */}
          <div className="bg-neutral-50 rounded-lg p-4 border border-neutral-200">
            <p className="text-sm text-neutral-600">
              <strong>Current Status:</strong>{" "}
              <span
                className={
                  form.status === "PUBLISHED"
                    ? "text-success-600"
                    : "text-warning-600"
                }
              >
                {form.status}
              </span>
            </p>
          </div>
        </div>
      </PageLayout>

      {/* HTML Guidelines Modal */}
      <Dialog.Root
        open={showGuidelinesModal}
        onOpenChange={setShowGuidelinesModal}
      >
        <Dialog.Portal>
          <Dialog.Overlay className="fixed inset-0 bg-black/50 z-modal" />
          <Dialog.Content className="fixed top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 bg-white rounded-lg shadow-xl max-w-3xl w-full max-h-[90vh] overflow-y-auto z-50 p-8">
            <Dialog.Title className="text-2xl font-bold text-neutral-900 mb-6">
              HTML Formatting Guidelines
            </Dialog.Title>

            <div className="space-y-6">
              {/* Introduction */}
              <div className="bg-primary-50 border border-primary-200 rounded-lg p-4">
                <p className="text-neutral-700">
                  Use AI tools like <strong>ChatGPT</strong> or{" "}
                  <strong>Google Gemini</strong> to convert your regular content
                  into beautifully formatted HTML. Follow the steps below:
                </p>
              </div>

              {/* Step 1: AI Prompt */}
              <div>
                <h3 className="text-lg font-semibold text-neutral-900 mb-3">
                  Step 1: Copy the AI Prompt Template
                </h3>
                <p className="text-neutral-600 mb-3">
                  Click the button below to copy a ready-to-use AI prompt to
                  your clipboard:
                </p>
                <Button
                  onClick={handleCopyPrompt}
                  className="w-full mb-3"
                  variant={copiedPrompt ? "outline" : "default"}
                >
                  {copiedPrompt ? (
                    <>
                      <CheckCircle className="w-4 h-4 mr-2" />
                      Prompt Copied!
                    </>
                  ) : (
                    <>
                      <Copy className="w-4 h-4 mr-2" />
                      Copy AI Prompt Template
                    </>
                  )}
                </Button>

                <div className="bg-neutral-100 rounded-lg p-4 font-mono text-sm overflow-x-auto">
                  <pre className="whitespace-pre-wrap text-neutral-700">
                    {`Convert the following content into beautifully formatted HTML for a blog post.

Requirements:
- Use semantic HTML5 tags (article, section, h1-h6, p, ul, ol, blockquote, code, pre, etc.)
- Add appropriate CSS classes for styling (use Tailwind CSS classes if applicable)
- Ensure proper heading hierarchy
- Format code blocks with <pre><code> tags
- Use <blockquote> for quotes
- Add proper spacing and line breaks
- Make it mobile-responsive
- Preserve the original meaning and structure

Content to convert:
[PASTE YOUR CONTENT HERE]

Please return only the HTML code without any explanations.`}
                  </pre>
                </div>
              </div>

              {/* Step 2: Replace Placeholder */}
              <div>
                <h3 className="text-lg font-semibold text-neutral-900 mb-3">
                  Step 2: Replace the Placeholder
                </h3>
                <p className="text-neutral-600">
                  In the AI prompt, replace{" "}
                  <code className="bg-neutral-200 px-2 py-1 rounded text-sm">
                    [PASTE YOUR CONTENT HERE]
                  </code>{" "}
                  with your actual blog content (plain text or markdown).
                </p>
              </div>

              {/* Step 3: Use AI Tool */}
              <div>
                <h3 className="text-lg font-semibold text-neutral-900 mb-3">
                  Step 3: Use an AI Tool
                </h3>
                <p className="text-neutral-600 mb-3">
                  Paste the prompt into one of these AI tools:
                </p>
                <div className="space-y-2">
                  <a
                    href="https://chat.openai.com"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="block p-3 bg-white border border-neutral-300 rounded-lg hover:border-primary-500 hover:shadow-md transition-all"
                  >
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="font-semibold text-neutral-900">
                          ChatGPT (OpenAI)
                        </p>
                        <p className="text-sm text-neutral-600">
                          Free tier available - Excellent for HTML conversion
                        </p>
                      </div>
                      <span className="text-primary-600">→</span>
                    </div>
                  </a>
                  <a
                    href="https://gemini.google.com"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="block p-3 bg-white border border-neutral-300 rounded-lg hover:border-primary-500 hover:shadow-md transition-all"
                  >
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="font-semibold text-neutral-900">
                          Google Gemini
                        </p>
                        <p className="text-sm text-neutral-600">
                          Free to use - Great for content formatting
                        </p>
                      </div>
                      <span className="text-primary-600">→</span>
                    </div>
                  </a>
                  <a
                    href="https://claude.ai"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="block p-3 bg-white border border-neutral-300 rounded-lg hover:border-primary-500 hover:shadow-md transition-all"
                  >
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="font-semibold text-neutral-900">
                          Claude (Anthropic)
                        </p>
                        <p className="text-sm text-neutral-600">
                          Free tier available - Excellent formatting
                          capabilities
                        </p>
                      </div>
                      <span className="text-primary-600">→</span>
                    </div>
                  </a>
                </div>
              </div>

              {/* Step 4: Copy HTML */}
              <div>
                <h3 className="text-lg font-semibold text-neutral-900 mb-3">
                  Step 4: Copy the Generated HTML
                </h3>
                <p className="text-neutral-600">
                  The AI will generate clean, formatted HTML. Copy the entire
                  HTML output and paste it into the "Content" field in your blog
                  editor.
                </p>
              </div>

              {/* Step 5: Preview */}
              <div className="bg-success-50 border border-success-200 rounded-lg p-4">
                <h3 className="text-lg font-semibold text-success-900 mb-2">
                  Step 5: Preview and Publish
                </h3>
                <p className="text-success-700">
                  Save as draft first and preview your blog post to ensure the
                  HTML renders correctly. Make any final adjustments before
                  publishing!
                </p>
              </div>
            </div>

            <div className="mt-8 flex justify-end">
              <Button
                variant="outline"
                onClick={() => setShowGuidelinesModal(false)}
              >
                Close
              </Button>
            </div>
          </Dialog.Content>
        </Dialog.Portal>
      </Dialog.Root>
    </div>
  );
};
