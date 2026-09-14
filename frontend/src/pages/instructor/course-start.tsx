import { CourseLinkField } from "@/components/course/CourseLinkField";
import { PageLayout, PageHeader } from "@/components/design-system/PageLayout";
/**
 * Course start form (Q2-A decision, 2026-09-04): creation is draft-first.
 * Fill 5 fields, the draft is created, and the instructor lands in the SAME
 * tabbed editor used for editing — create and edit are one flow forever.
 * Type is a LABEL/BUCKET only (Q3-B): it never gates tools.
 */
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import toast from "react-hot-toast";
import { Button } from "@/components/ui/button";
import { COURSE_TYPES } from "@/config/courseTypes";
import { courseAPI } from "@/api/course";
import { TemplatePicker } from "@/components/course/TemplatePicker";

export default function CourseStartPage() {
  const navigate = useNavigate();
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState({
    title: "",
    slug: "",
    courseType: "meiporul",
    category: "",
    price: 0,
    description: "",
  });

  async function start(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    try {
      const created = await courseAPI.createCourse({
        title: form.title,
        slug: form.slug || undefined,
        description: form.description || form.title,
        excerpt: form.title,
        content: form.description || form.title,
        category: form.category || "General",
        course_type: form.courseType,
        level: "beginner",
        language: "English",
        price: Number(form.price) || 0,
        status: "draft",
      });
      toast.success("Draft created — build your course below");
      // v2.0 §4.1 (WP6): open on the type-specific Studio face
      navigate(`/instructor/courses/${created.id}/edit?tab=curriculum&face=1`, {
        replace: true,
      });
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })
        ?.response?.data?.detail;
      toast.error(
        typeof detail === "string" ? detail : "Failed to create draft",
      );
    } finally {
      setSaving(false);
    }
  }

  return (
    <PageLayout
      header={
        <PageHeader>
          <CourseLinkField
            value={form.slug}
            onChange={(slug) => setForm({ ...form, slug })}
          />
          <div>
            <h1 className="text-2xl font-bold text-gray-900 mb-1">
              Start a New Course
            </h1>
            <p className="text-slate-600 text-sm mb-8">
              Create your draft, then open the full course editor — curriculum,
              drag-drop ordering, live classes, everything.
            </p>
          </div>
        </PageHeader>
      }
      className="rd-screen rd-screen-instructor-course-start"
    >
      <TemplatePicker />
      <form onSubmit={start} className="glass-panel rounded-xl p-6 space-y-5">
        <label className="block text-sm font-medium text-gray-700">
          Course Title *
          <input
            type="text"
            required
            value={form.title}
            onChange={(e) => setForm({ ...form, title: e.target.value })}
            className="mt-1 w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
            placeholder="e.g., Class 10 Physics — Complete Course"
          />
        </label>

        <div>
          <span className="block text-sm font-medium text-gray-700 mb-1">
            Course Type *
          </span>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
            {COURSE_TYPES.map((t) => (
              <button
                key={t.value}
                type="button"
                onClick={() => setForm({ ...form, courseType: t.value })}
                className={`p-3 rounded-lg border-2 text-left transition-all ${t.cardClass} ${
                  form.courseType === t.value
                    ? t.selectedClass
                    : "border-gray-200 bg-white"
                }`}
              >
                <span className="text-lg">{t.emoji}</span>
                <span className="block font-semibold text-gray-900 text-sm">
                  {t.label}
                </span>
                <span className="block text-[11px] text-gray-500">
                  {t.tamil}
                </span>
              </button>
            ))}
          </div>
          <p className="text-[11px] text-gray-400 mt-1">
            A label that tells students what the course is — all tools are
            available for every type.
          </p>
        </div>

        <label className="block text-sm font-medium text-gray-700">
          Category (free-form)
          <input
            type="text"
            value={form.category}
            onChange={(e) => setForm({ ...form, category: e.target.value })}
            className="mt-1 w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
            placeholder="e.g. Tamil Grammar, NEET Biology"
          />
        </label>

        <label className="block text-sm font-medium text-gray-700">
          Price (₹, 0 = free)
          <input
            type="number"
            min="0"
            step="1"
            value={form.price}
            onChange={(e) =>
              setForm({ ...form, price: Number(e.target.value) })
            }
            className="mt-1 w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
          />
        </label>

        <label className="block text-sm font-medium text-gray-700">
          Short description (optional — editable later)
          <textarea
            rows={2}
            value={form.description}
            onChange={(e) => setForm({ ...form, description: e.target.value })}
            className="mt-1 w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
            placeholder="One line about the course"
          />
        </label>

        <div className="flex gap-3">
          <Button type="submit" disabled={saving || !form.title.trim()}>
            {saving ? "Creating…" : "Create draft & open editor →"}
          </Button>
          <Button variant="outline" onClick={() => navigate(-1)}>
            Cancel
          </Button>
        </div>
      </form>
    </PageLayout>
  );
}
