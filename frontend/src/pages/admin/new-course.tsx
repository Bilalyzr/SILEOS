import { PageLayout, PageHeader } from "@/components/design-system/PageLayout";
import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Save, X, Plus, Trash2 } from "lucide-react";
import { courseAPI } from "@/api/course";
import { ImageUpload } from "@/components/upload";
import { CourseLinkField } from "@/components/course/CourseLinkField";

export const AdminNewCourse: React.FC = () => {
  const navigate = useNavigate();
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [formData, setFormData] = useState({
    title: "",
    slug: "",
    description: "",
    excerpt: "",
    level: "beginner",
    price: "",
    salePrice: "",
    duration: "",
    category: "excel",
    status: "draft",
    thumbnail: "",
    videoUrl: "",
    requirements: [""],
    benefits: [""],
    targetAudience: [""],
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (submitting) return;
    setError(null);

    if (!formData.title.trim() || !formData.description.trim()) {
      setError("Title and description are required.");
      return;
    }

    const payload = {
      title: formData.title.trim(),
      slug: formData.slug || undefined,
      description: formData.description,
      content: formData.description,
      excerpt: formData.excerpt,
      level: formData.level,
      category: formData.category,
      status: formData.status,
      target_audience: formData.targetAudience
        .map((t) => t.trim())
        .filter(Boolean)
        .join("\n"),
      price: parseFloat(formData.price) || 0,
      sale_price: formData.salePrice ? parseFloat(formData.salePrice) : null,
      // Backend expects an integer number of hours; the form is free-text.
      duration: parseInt(formData.duration, 10) || 0,
      thumbnail: formData.thumbnail,
      intro_video: formData.videoUrl,
      requirements: formData.requirements.map((r) => r.trim()).filter(Boolean),
      benefits: formData.benefits.map((b) => b.trim()).filter(Boolean),
    };

    try {
      setSubmitting(true);
      const created = await courseAPI.createCourse(payload);
      // Go to the new course's edit page if we got an id back, else the list.
      const id = (created as { id?: number })?.id;
      navigate(id ? `/admin/courses/${id}/edit` : "/admin/courses");
    } catch (err) {
      const message =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail ||
        (err as Error)?.message ||
        "Failed to create course. Please try again.";
      setError(
        typeof message === "string" ? message : "Failed to create course.",
      );
    } finally {
      setSubmitting(false);
    }
  };

  const addArrayField = (
    field: "requirements" | "benefits" | "targetAudience",
  ) => {
    setFormData((prev) => ({
      ...prev,
      [field]: [...prev[field], ""],
    }));
  };

  const removeArrayField = (
    field: "requirements" | "benefits" | "targetAudience",
    index: number,
  ) => {
    setFormData((prev) => ({
      ...prev,
      [field]: prev[field].filter((_, i) => i !== index),
    }));
  };

  const updateArrayField = (
    field: "requirements" | "benefits" | "targetAudience",
    index: number,
    value: string,
  ) => {
    setFormData((prev) => ({
      ...prev,
      [field]: prev[field].map((item, i) => (i === index ? value : item)),
    }));
  };

  return (
    <PageLayout
      header={
        <PageHeader>
          <h1 className="text-3xl font-bold text-gray-900">Add New Course</h1>
          <p className="text-gray-600 mt-1">
            Create a new course for SashaInfinity LMS
          </p>
        </PageHeader>
      }
      className="rd-screen rd-screen-admin-new-course"
    >
      <form onSubmit={handleSubmit} className="space-y-6">
        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 rounded-lg px-4 py-3 text-sm">
            {error}
          </div>
        )}
        {/* Main Course Info */}
        <div
          className="bg-white rounded-lg border border-gray-200 p-6"
          data-glass="work"
        >
          <h2 className="text-xl font-bold text-gray-900 mb-4">
            Course Information
          </h2>

          <div className="space-y-4">
            <CourseLinkField
              value={formData.slug}
              onChange={(slug) => setFormData({ ...formData, slug })}
            />
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Course Title *
              </label>
              <input
                type="text"
                required
                value={formData.title}
                onChange={(e) =>
                  setFormData({ ...formData, title: e.target.value })
                }
                placeholder="e.g., Data Analytics Using Microsoft Excel"
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Course Description *
              </label>
              <textarea
                required
                rows={6}
                value={formData.description}
                onChange={(e) =>
                  setFormData({ ...formData, description: e.target.value })
                }
                placeholder="Provide a detailed description of the course..."
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Short Description
              </label>
              <textarea
                rows={3}
                value={formData.excerpt}
                onChange={(e) =>
                  setFormData({ ...formData, excerpt: e.target.value })
                }
                placeholder="Brief summary that appears in course listings..."
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Course Level *
                </label>
                <select
                  required
                  value={formData.level}
                  onChange={(e) =>
                    setFormData({ ...formData, level: e.target.value })
                  }
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                >
                  <option value="beginner">Beginner</option>
                  <option value="intermediate">Intermediate</option>
                  <option value="advanced">Advanced</option>
                  <option value="expert">Expert</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Category *
                </label>
                <select
                  required
                  value={formData.category}
                  onChange={(e) =>
                    setFormData({ ...formData, category: e.target.value })
                  }
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                >
                  <option value="excel">Microsoft Excel</option>
                  <option value="data-analytics">Data Analytics</option>
                  <option value="data-visualization">Data Visualization</option>
                  <option value="business-intelligence">
                    Business Intelligence
                  </option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Regular Price ($) *
                </label>
                <input
                  type="number"
                  required
                  step="0.01"
                  value={formData.price}
                  onChange={(e) =>
                    setFormData({ ...formData, price: e.target.value })
                  }
                  placeholder="299.00"
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Sale Price ($)
                </label>
                <input
                  type="number"
                  step="0.01"
                  value={formData.salePrice}
                  onChange={(e) =>
                    setFormData({ ...formData, salePrice: e.target.value })
                  }
                  placeholder="199.00"
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Duration
                </label>
                <input
                  type="text"
                  value={formData.duration}
                  onChange={(e) =>
                    setFormData({ ...formData, duration: e.target.value })
                  }
                  placeholder="e.g., 25 hours"
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Status *
                </label>
                <select
                  required
                  value={formData.status}
                  onChange={(e) =>
                    setFormData({ ...formData, status: e.target.value })
                  }
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                >
                  <option value="draft">Draft</option>
                  <option value="publish">Publish</option>
                  <option value="pending">Pending Review</option>
                  <option value="private">Private</option>
                </select>
              </div>
            </div>
          </div>
        </div>

        {/* Course Media */}
        <div
          className="bg-white rounded-lg border border-gray-200 p-6"
          data-glass="work"
        >
          <h2 className="text-xl font-bold text-gray-900 mb-4">Course Media</h2>

          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Course Thumbnail
              </label>
              <ImageUpload
                value={formData.thumbnail}
                onChange={(url) => setFormData({ ...formData, thumbnail: url })}
              />
              <p className="text-sm text-gray-500 mt-1">
                Recommended: 1280x720px
              </p>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Intro Video URL
              </label>
              <input
                type="url"
                value={formData.videoUrl}
                onChange={(e) =>
                  setFormData({ ...formData, videoUrl: e.target.value })
                }
                placeholder="https://youtube.com/watch?v=..."
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>
          </div>
        </div>

        {/* Course Requirements */}
        <div
          className="bg-white rounded-lg border border-gray-200 p-6"
          data-glass="work"
        >
          <h2 className="text-xl font-bold text-gray-900 mb-4">
            Requirements & Benefits
          </h2>

          <div className="space-y-6">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Course Requirements
              </label>
              {formData.requirements.map((req, index) => (
                <div key={index} className="flex items-center space-x-2 mb-2">
                  <input
                    type="text"
                    value={req}
                    onChange={(e) =>
                      updateArrayField("requirements", index, e.target.value)
                    }
                    placeholder="e.g., Basic computer skills"
                    className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  />
                  <button
                    type="button"
                    onClick={() => removeArrayField("requirements", index)}
                    className="p-2 text-red-600 hover:bg-red-50 rounded"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              ))}
              <button
                type="button"
                onClick={() => addArrayField("requirements")}
                className="mt-2 px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 flex items-center space-x-2 text-sm"
              >
                <Plus className="w-4 h-4" />
                <span>Add Requirement</span>
              </button>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                What Students Will Learn
              </label>
              {formData.benefits.map((benefit, index) => (
                <div key={index} className="flex items-center space-x-2 mb-2">
                  <input
                    type="text"
                    value={benefit}
                    onChange={(e) =>
                      updateArrayField("benefits", index, e.target.value)
                    }
                    placeholder="e.g., Master Excel formulas and functions"
                    className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  />
                  <button
                    type="button"
                    onClick={() => removeArrayField("benefits", index)}
                    className="p-2 text-red-600 hover:bg-red-50 rounded"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              ))}
              <button
                type="button"
                onClick={() => addArrayField("benefits")}
                className="mt-2 px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 flex items-center space-x-2 text-sm"
              >
                <Plus className="w-4 h-4" />
                <span>Add Learning Outcome</span>
              </button>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Target Audience
              </label>
              {formData.targetAudience.map((audience, index) => (
                <div key={index} className="flex items-center space-x-2 mb-2">
                  <input
                    type="text"
                    value={audience}
                    onChange={(e) =>
                      updateArrayField("targetAudience", index, e.target.value)
                    }
                    placeholder="e.g., Beginners in data analytics"
                    className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  />
                  <button
                    type="button"
                    onClick={() => removeArrayField("targetAudience", index)}
                    className="p-2 text-red-600 hover:bg-red-50 rounded"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              ))}
              <button
                type="button"
                onClick={() => addArrayField("targetAudience")}
                className="mt-2 px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 flex items-center space-x-2 text-sm"
              >
                <Plus className="w-4 h-4" />
                <span>Add Target Audience</span>
              </button>
            </div>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center justify-end space-x-4">
          <button
            type="button"
            onClick={() => navigate("/admin/courses")}
            className="px-6 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors flex items-center space-x-2"
          >
            <X className="w-4 h-4" />
            <span>Cancel</span>
          </button>
          <button
            type="submit"
            disabled={submitting}
            className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors flex items-center space-x-2 disabled:opacity-60 disabled:cursor-not-allowed"
          >
            <Save className="w-4 h-4" />
            <span>{submitting ? "Creating…" : "Create Course"}</span>
          </button>
        </div>
      </form>
    </PageLayout>
  );
};
