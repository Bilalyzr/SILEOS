import { PageLayout, PageHeader } from "@/components/design-system/PageLayout";
import { useCallback } from "react";
import React, { useState, useEffect } from "react";
import { UserPlus, BookOpen, Award } from "lucide-react";
import { getAuthToken } from "@/utils/auth-helper";
import toast from "react-hot-toast";
import { Link } from "react-router-dom";

const API = "/api/v1";
const h = () => ({
  "Content-Type": "application/json",
  Authorization: `Bearer ${getAuthToken()}`,
});

interface Instructor {
  id: number;
  name: string;
  email: string;
}
interface Template {
  id: number;
  name: string;
  bg_color: string;
  title_color: string;
  font: string;
}
interface Course {
  id: number;
  title: string;
  instructor_name: string;
  status: string;
}

export const AdminManage: React.FC = () => {
  const [tab, setTab] = useState<"instructor" | "assign" | "templates">(
    "instructor",
  );
  const [instructors, setInstructors] = useState<Instructor[]>([]);
  const [templates, setTemplates] = useState<Template[]>([]);
  const [courses, setCourses] = useState<Course[]>([]);
  const [iForm, setIForm] = useState({
    email: "",
    username: "",
    password: "",
    display_name: "",
    bio: "",
  });
  const [assignCourseId, setAssignCourseId] = useState("");
  const [assignInstructorId, setAssignInstructorId] = useState("");

  // Every list endpoint here can answer 401/403/500 with a JSON error object
  // ({detail: "..."}), which parses fine — so a bare .catch() never fires and
  // the error object lands in state. The subsequent .map() in render then
  // throws, which unmounts the whole tree and looks like the app "freezing"
  // on navigation. Coerce to an array before it can reach state.
  const asList = <T,>(d: any, key: string): T[] =>
    Array.isArray(d) ? d : Array.isArray(d?.[key]) ? d[key] : [];

  // FastAPI answers 422 with detail as an array of objects; passing that
  // straight to toast renders "[object Object]".
  const errText = (d: any, fallback: string): string => {
    const detail = d?.detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail))
      return (
        detail
          .map((e: any) => e?.msg)
          .filter(Boolean)
          .join(", ") || fallback
      );
    return fallback;
  };

  const loadInstructors = useCallback(
    () =>
      fetch(`${API}/admin/instructors/list`, { headers: h() })
        .then((r) => r.json())
        .then((d) => setInstructors(asList<Instructor>(d, "instructors")))
        .catch(() => setInstructors([])),
    [],
  );

  const loadData = useCallback(() => {
    loadInstructors();
    fetch(`${API}/admin/certificate-templates`, { headers: h() })
      .then((r) => r.json())
      .then((d) => setTemplates(asList<Template>(d, "templates")))
      .catch(() => setTemplates([]));
    fetch(`${API}/admin/courses`, { headers: h() })
      .then((r) => r.json())
      .then((d) => setCourses(asList<Course>(d, "courses")))
      .catch(() => setCourses([]));
  }, [loadInstructors]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const createInstructor = async () => {
    if (!iForm.email || !iForm.username || !iForm.password) {
      toast.error("Fill all required fields");
      return;
    }
    try {
      const r = await fetch(`${API}/admin/instructors/create`, {
        method: "POST",
        headers: h(),
        body: JSON.stringify(iForm),
      });
      const d = await r.json();
      if (!r.ok) {
        toast.error(errText(d, "Failed to create instructor"));
        return;
      }
      toast.success("Instructor created!");
      setIForm({
        email: "",
        username: "",
        password: "",
        display_name: "",
        bio: "",
      });
      loadInstructors();
    } catch {
      toast.error("Failed to create instructor");
    }
  };

  const assignCourse = async () => {
    if (!assignCourseId || !assignInstructorId) {
      toast.error("Select both course and instructor");
      return;
    }
    try {
      const r = await fetch(
        `${API}/admin/courses/${assignCourseId}/assign-instructor`,
        {
          method: "POST",
          headers: h(),
          body: JSON.stringify({ instructor_id: parseInt(assignInstructorId) }),
        },
      );
      const d = await r.json();
      if (!r.ok) {
        toast.error(errText(d, "Failed to assign course"));
        return;
      }
      toast.success("Course assigned successfully!");
      setAssignCourseId("");
      setAssignInstructorId("");
      loadData();
    } catch {
      toast.error("Failed to assign course");
    }
  };

  const inp =
    "w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-orange-400";
  const btn =
    "px-4 py-2 rounded-lg text-sm font-medium text-white bg-orange-500 hover:bg-orange-600 transition-colors";

  const tabs = [
    ["instructor", "Create Instructor"],
    ["assign", "Assign Course"],
    ["templates", "Certificate Templates"],
  ];

  return (
    <PageLayout
      header={
        <PageHeader>
          <h1 className="text-2xl font-bold text-gray-900">Admin Management</h1>
          <Link
            to="/admin/courses/create"
            className="px-4 py-2 bg-orange-500 hover:bg-orange-600 text-white rounded-lg text-sm font-medium transition-colors"
          >
            + Create New Course
          </Link>
        </PageHeader>
      }
      className="rd-screen rd-screen-admin-manage"
    >
      <div className="flex gap-2 mb-6 border-b">
        {tabs.map(([key, label]) => (
          <button
            key={key}
            onClick={() => setTab(key as any)}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${tab === key ? "border-orange-500 text-orange-600" : "border-transparent text-gray-500 hover:text-gray-700"}`}
          >
            {label}
          </button>
        ))}
      </div>
      {tab === "instructor" && (
        <div
          className="bg-white rounded-xl border p-6 space-y-4"
          data-glass="work"
        >
          <div className="flex items-center gap-2 mb-2">
            <UserPlus className="w-5 h-5 text-orange-500" />
            <h2 className="text-lg font-semibold">Create Instructor Account</h2>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-xs font-medium text-gray-600 mb-1 block">
                Email *
              </label>
              <input
                className={inp}
                value={iForm.email}
                onChange={(e) =>
                  setIForm((p) => ({ ...p, email: e.target.value }))
                }
                placeholder="instructor@email.com"
              />
            </div>
            <div>
              <label className="text-xs font-medium text-gray-600 mb-1 block">
                Username *
              </label>
              <input
                className={inp}
                value={iForm.username}
                onChange={(e) =>
                  setIForm((p) => ({ ...p, username: e.target.value }))
                }
                placeholder="username"
              />
            </div>
            <div>
              <label className="text-xs font-medium text-gray-600 mb-1 block">
                Display Name
              </label>
              <input
                className={inp}
                value={iForm.display_name}
                onChange={(e) =>
                  setIForm((p) => ({ ...p, display_name: e.target.value }))
                }
                placeholder="Full Name"
              />
            </div>
            <div>
              <label className="text-xs font-medium text-gray-600 mb-1 block">
                Password *
              </label>
              <input
                className={inp}
                type="password"
                value={iForm.password}
                onChange={(e) =>
                  setIForm((p) => ({ ...p, password: e.target.value }))
                }
                placeholder="••••••••"
              />
            </div>
          </div>
          <div>
            <label className="text-xs font-medium text-gray-600 mb-1 block">
              Bio
            </label>
            <textarea
              className={inp}
              value={iForm.bio}
              onChange={(e) => setIForm((p) => ({ ...p, bio: e.target.value }))}
              placeholder="Instructor bio..."
              rows={3}
            />
          </div>
          <button onClick={createInstructor} className={btn}>
            Create Instructor
          </button>

          {/* Existing instructors list */}
          {instructors.length > 0 && (
            <div className="mt-6">
              <h3 className="text-sm font-semibold text-gray-700 mb-3">
                Existing Instructors ({instructors.length})
              </h3>
              <div className="space-y-2">
                {instructors.map((i) => (
                  <div
                    key={i.id}
                    className="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
                  >
                    <div>
                      <p className="text-sm font-medium text-gray-800">
                        {i.name}
                      </p>
                      <p className="text-xs text-gray-500">{i.email}</p>
                    </div>
                    <span className="text-xs bg-orange-100 text-orange-700 px-2 py-1 rounded">
                      ID: {i.id}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
      {tab === "assign" && (
        <div
          className="bg-white rounded-xl border p-6 space-y-4"
          data-glass="work"
        >
          <div className="flex items-center gap-2 mb-2">
            <BookOpen className="w-5 h-5 text-orange-500" />
            <h2 className="text-lg font-semibold">
              Assign Course to Instructor
            </h2>
          </div>
          <div className="grid grid-cols-1 gap-4">
            <div>
              <label className="text-xs font-medium text-gray-600 mb-1 block">
                Select Course *
              </label>
              <select
                className={inp}
                value={assignCourseId}
                onChange={(e) => setAssignCourseId(e.target.value)}
              >
                <option value="">Choose a course...</option>
                {courses.map((c) => (
                  <option key={c.id} value={c.id}>
                    [{c.id}] {c.title} — currently:{" "}
                    {c.instructor_name || "unassigned"}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-xs font-medium text-gray-600 mb-1 block">
                Assign to Instructor *
              </label>
              <select
                className={inp}
                value={assignInstructorId}
                onChange={(e) => setAssignInstructorId(e.target.value)}
              >
                <option value="">Choose instructor...</option>
                {instructors.map((i) => (
                  <option key={i.id} value={i.id}>
                    {i.name} ({i.email})
                  </option>
                ))}
              </select>
            </div>
          </div>
          <button onClick={assignCourse} className={btn}>
            Assign Course
          </button>

          {/* Courses list */}
          {courses.length > 0 && (
            <div className="mt-4">
              <h3 className="text-sm font-semibold text-gray-700 mb-3">
                All Courses ({courses.length})
              </h3>
              <div className="space-y-2 max-h-64 overflow-y-auto">
                {courses.map((c) => (
                  <div
                    key={c.id}
                    className="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
                  >
                    <div>
                      <p className="text-sm font-medium text-gray-800">
                        {c.title}
                      </p>
                      <p className="text-xs text-gray-500">
                        Instructor: {c.instructor_name || "none"}
                      </p>
                    </div>
                    <span
                      className={`text-xs px-2 py-1 rounded ${c.status === "publish" ? "bg-green-100 text-green-700" : "bg-yellow-100 text-yellow-700"}`}
                    >
                      {c.status}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
      {tab === "templates" && (
        <div className="space-y-4">
          <div className="flex items-center gap-2 mb-2">
            <Award className="w-5 h-5 text-orange-500" />
            <h2 className="text-lg font-semibold">Certificate Templates</h2>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {templates.map((t) => (
              <div
                key={t.id}
                className="rounded-xl border overflow-hidden shadow-sm"
              >
                <div
                  className="h-24 flex items-center justify-center"
                  style={{ background: t.bg_color }}
                >
                  <div className="text-center">
                    <p
                      className="text-lg font-bold"
                      style={{ color: t.title_color, fontFamily: t.font }}
                    >
                      Certificate
                    </p>
                    <p
                      className="text-xs mt-1"
                      style={{
                        color: t.title_color,
                        fontFamily: t.font,
                        opacity: 0.7,
                      }}
                    >
                      of Achievement
                    </p>
                  </div>
                </div>
                <div className="p-3 bg-white">
                  <p className="font-medium text-sm text-gray-800">{t.name}</p>
                  <p className="text-xs text-gray-500 mt-1">
                    {t.font} • ID: {t.id}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </PageLayout>
  );
};

export default AdminManage;
