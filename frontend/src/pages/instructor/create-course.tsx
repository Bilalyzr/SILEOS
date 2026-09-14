import { CourseLinkField } from "@/components/course/CourseLinkField";
import { AstraSymbol } from "@/components/design-system/AstraSymbol";
import { PageLayout, PageHeader } from "@/components/design-system/PageLayout";
import React, { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ArrowLeft, Plus, Trash2, Save, Eye } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { ImageUpload, VideoUpload, DocumentUpload } from "@/components/upload";
import { H5PPicker } from "@/components/h5p/H5PPicker";
import { GamePicker } from "@/components/games/GamePicker";
import { GeoGebraAuthorCard } from "@/components/geogebra/GeoGebraAuthorCard";
import { ThreeDModelPicker } from "@/components/three-d/ThreeDModelPicker";
import { VirtualLabPicker } from "@/components/labs/VirtualLabPicker";
import { lessonContentSyncPayload } from "@/lib/lessonContentSync";
import { courseAPI } from "@/api/course";
import { useAuthStore } from "@/store/auth";
import { getAuthToken } from "@/utils/auth-helper";
import { api } from "@/api/axios";
import { listDesignerTemplates } from "@/api/certificateDesigner";
import type { DesignerTemplate } from "@/lib/certificateDesignerTypes";
import {
  canUseDesignerTemplates,
  mergeTemplateLists,
  type PickerTemplate,
} from "@/lib/certificateTemplatePicker";
import { toast } from "react-hot-toast";
import QuizSetupModal from "@/components/instructor/QuizSetupModal";
import {
  COURSE_TYPES,
  courseTypeLabel,
  TYPE_TOOLS,
  TOOL_LABELS,
  typeSupports,
} from "@/config/courseTypes";

interface CourseForm {
  slug?: string;
  title: string;
  description: string;
  shortDescription: string;
  category: string;
  courseType: string;
  level: string;
  language: string;
  price: string;
  discountPrice: string;
  thumbnail: string;
  introVideo?: string;
  tags: string[];
  requirements: string[];
  learningObjectives: string[];
  certificateId?: string;
  courseStructure: {
    sections: Section[];
  };
}

interface Section {
  id: string;
  title: string;
  description: string;
  lectures: Lecture[];
}

interface QuizQuestion {
  id: string;
  question: string;
  options: string[];
  correctAnswer: number;
  points: number;
}

interface QuizData {
  title: string;
  description: string;
  timeLimit: number;
  passingScore: number;
  questions: QuizQuestion[];
}

interface AssignmentData {
  title: string;
  description: string;
  maxScore: number;
  dueDate?: string;
  allowedFileTypes: string[];
  attachments?: string[]; // URLs of instructor-uploaded reference files
}

interface Lecture {
  id: string;
  title: string;
  type: "video" | "text" | "quiz" | "assignment";
  duration: string;
  content: string;
  videoUrl?: string;
  videoDuration?: number;
  youtubeUrl?: string;
  // H5P/game interactive-content support — mirrors edit-course.tsx: a
  // "video" lecture's player content can be a plain video, a sandboxed
  // H5P item, or a native learning game. `h5pContentId` is the H5PContent
  // integer PK (backend h5p_content_id); `gameId` is the Game integer PK
  // (backend game_id).
  contentType?:
    | "video"
    | "h5p"
    | "game"
    | "geogebra"
    | "three_d"
    | "virtual_lab";
  videoSource?: "upload" | "youtube" | "direct";
  h5pContentId?: number | null;
  gameId?: number | null;
  geogebraAppletId?: number | null;
  threeDModelId?: number | null;
  virtualLabSim?: string | null;
  quizData?: QuizData;
  /** Real quiz id (backend Quiz.id) once the quiz was created via the setup popup */
  quizId?: number;
  assignmentData?: AssignmentData;
  isPreview?: boolean;
}

const levels = ["beginner", "intermediate", "advanced", "expert"];
const levelLabels: Record<string, string> = {
  beginner: "Beginner",
  intermediate: "Intermediate",
  advanced: "Advanced",
  expert: "Expert",
};
const languages = [
  { code: "en", name: "English", flag: "🇬🇧" },
  { code: "es", name: "Spanish", flag: "🇪🇸" },
  { code: "fr", name: "French", flag: "🇫🇷" },
  { code: "de", name: "German", flag: "🇩🇪" },
  { code: "ja", name: "Japanese", flag: "🇯🇵" },
  { code: "zh", name: "Chinese", flag: "🇨🇳" },
  { code: "pt", name: "Portuguese", flag: "🇵🇹" },
  { code: "ru", name: "Russian", flag: "🇷🇺" },
  { code: "ar", name: "Arabic", flag: "🇸🇦" },
  { code: "hi", name: "Hindi", flag: "🇮🇳" },
  { code: "ta", name: "Tamil", flag: "🇮🇳" },
  { code: "ko", name: "Korean", flag: "🇰🇷" },
  { code: "it", name: "Italian", flag: "🇮🇹" },
];

export function CreateCourse() {
  const navigate = useNavigate();
  const [currentStep, setCurrentStep] = useState(1);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [courseId, setCourseId] = useState<number | null>(null);
  const [isAutoSaving, setIsAutoSaving] = useState(false);
  // Tracks the in-flight "Add Lecture" request so a second click cannot append
  // a duplicate lesson while the first is still on the wire.
  const [addingLecture, setAddingLecture] = useState(false);
  // Holds the in-flight draft-course creation. `courseId` is React state, so
  // two rapid addLecture() calls would both read it as null and each create
  // their own draft course; sharing the promise makes creation happen once.
  const courseCreationRef = React.useRef<Promise<number> | null>(null);
  const [form, setForm] = useState<CourseForm>({
    title: "",
    description: "",
    shortDescription: "",
    category: "",
    courseType: "",
    level: "",
    language: "English",
    price: "",
    discountPrice: "",
    thumbnail: "",
    introVideo: "",
    tags: [],
    requirements: [""],
    learningObjectives: [""],
    certificateId: "",
    courseStructure: {
      sections: [],
    },
  });

  const [newTag, setNewTag] = useState("");
  // Quiz-setup popup target: which lecture's "Configure quiz" button opened it
  const [quizModalLecture, setQuizModalLecture] = useState<{
    sectionId: string;
    lectureId: string;
  } | null>(null);
  const { user } = useAuthStore();
  const isAdmin = user?.role === "admin";
  const [instructors, setInstructors] = useState<
    { id: number; name: string; email: string }[]
  >([]);
  const [selectedInstructorId, setSelectedInstructorId] = useState<
    number | null
  >(null);
  const [certTemplates, setCertTemplates] = useState<any[]>([]);
  const [previewTemplate, setPreviewTemplate] = useState<any | null>(null);

  useEffect(() => {
    // Review finding I2: the public /templates/list endpoint is anonymous and
    // therefore only exposes legacy (slug) + global rows — an instructor's own
    // designer templates are private and would otherwise be unreachable from
    // the course editor. Instructors/admins additionally pull
    // /certificates/designer/ and the two lists are merged (deduped by id;
    // both endpoints emit plain Certificate ids).
    let cancelled = false;

    const loadTemplates = async () => {
      let publicTemplates: PickerTemplate[] = [];
      try {
        const res = await api.get("/certificates/templates/list");
        publicTemplates = Array.isArray(res.data) ? res.data : [];
      } catch {
        publicTemplates = [];
      }

      let designerTemplates: DesignerTemplate[] = [];
      if (canUseDesignerTemplates(user?.role)) {
        try {
          designerTemplates = await listDesignerTemplates();
        } catch {
          // Non-fatal: fall back to the public list alone.
          designerTemplates = [];
        }
      }

      if (!cancelled) {
        setCertTemplates(
          mergeTemplateLists(publicTemplates, designerTemplates),
        );
      }
    };

    loadTemplates();
    return () => {
      cancelled = true;
    };
  }, [user?.role]);

  useEffect(() => {
    if (isAdmin) {
      fetch("/api/v1/admin/instructors/list", {
        headers: { Authorization: `Bearer ${getAuthToken()}` },
      })
        .then((r) => r.json())
        .then(setInstructors)
        .catch(() => {});
    }
  }, [isAdmin]);

  const handleInputChange = (
    e: React.ChangeEvent<
      HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement
    >,
  ) => {
    const { name, value } = e.target;
    setForm((prev) => ({ ...prev, [name]: value }));
  };

  const addTag = () => {
    if (newTag.trim() && !form.tags.includes(newTag.trim())) {
      setForm((prev) => ({
        ...prev,
        tags: [...prev.tags, newTag.trim()],
      }));
      setNewTag("");
    }
  };

  const removeTag = (tagToRemove: string) => {
    setForm((prev) => ({
      ...prev,
      tags: prev.tags.filter((tag) => tag !== tagToRemove),
    }));
  };

  const updateArrayField = (
    field: "requirements" | "learningObjectives",
    index: number,
    value: string,
  ) => {
    setForm((prev) => ({
      ...prev,
      [field]: prev[field].map((item, i) => (i === index ? value : item)),
    }));
  };

  const addArrayField = (field: "requirements" | "learningObjectives") => {
    setForm((prev) => ({
      ...prev,
      [field]: [...prev[field], ""],
    }));
  };

  const removeArrayField = (
    field: "requirements" | "learningObjectives",
    index: number,
  ) => {
    setForm((prev) => ({
      ...prev,
      [field]: prev[field].filter((_, i) => i !== index),
    }));
  };

  const addSection = () => {
    const newSection: Section = {
      id: Date.now().toString(),
      title: "",
      description: "",
      lectures: [],
    };
    setForm((prev) => ({
      ...prev,
      courseStructure: {
        sections: [...prev.courseStructure.sections, newSection],
      },
    }));
  };

  const updateSection = (sectionId: string, field: string, value: string) => {
    setForm((prev) => ({
      ...prev,
      courseStructure: {
        sections: prev.courseStructure.sections.map((section) =>
          section.id === sectionId ? { ...section, [field]: value } : section,
        ),
      },
    }));
  };

  const removeSection = (sectionId: string) => {
    setForm((prev) => ({
      ...prev,
      courseStructure: {
        sections: prev.courseStructure.sections.filter(
          (section) => section.id !== sectionId,
        ),
      },
    }));
  };

  // Helper: ensure a course exists on the backend before creating lessons.
  // Concurrent callers share one in-flight creation via courseCreationRef so
  // we never end up with several draft courses for the same form.
  const ensureCourseExists = async (): Promise<number> => {
    if (courseId) return courseId;
    if (courseCreationRef.current) return courseCreationRef.current;

    const creation = createDraftCourse();
    courseCreationRef.current = creation;
    try {
      return await creation;
    } catch (err) {
      // Let the next attempt retry rather than caching a rejected promise.
      courseCreationRef.current = null;
      throw err;
    }
  };

  const createDraftCourse = async (): Promise<number> => {
    // Auto-create a draft course so we can attach lessons to it
    const courseData: Record<string, any> = {
      title: form.title || "Untitled Course",
      slug: form.slug || undefined,
      description: form.description || "Draft course",
      excerpt: form.shortDescription || "",
      content: form.description || "",
      thumbnail: form.thumbnail || "",
      price: parseFloat(form.price) || 0,
      sale_price: parseFloat(form.discountPrice) || null,
      level: form.level || "beginner",
      category: form.category || "General",
      course_type: form.courseType || undefined,
      language: form.language || "English",
      requirements: form.requirements.filter((r) => r.trim()),
      benefits: form.learningObjectives.filter((o) => o.trim()),
      duration: 0,
      certificate_id: form.certificateId ? Number(form.certificateId) : null,
    };

    const createdCourse = await courseAPI.createCourse(
      isAdmin && selectedInstructorId
        ? { ...courseData, instructor_id: selectedInstructorId }
        : courseData,
    );
    const newId = createdCourse.id;
    setCourseId(newId);
    return newId;
  };

  const addLecture = async (sectionId: string) => {
    // Each click POSTs a new lesson and the backend has no dedupe, so an
    // impatient second click while the first is still pending created a
    // duplicate. Ignore re-entrant calls.
    if (addingLecture) return;
    setAddingLecture(true);
    try {
      // Ensure we have a course on the backend to attach the lesson to
      const targetCourseId = await ensureCourseExists();

      // Create the lesson immediately via API (same pattern as edit-course.tsx)
      const response = await api.post(`/courses/${targetCourseId}/lessons`, {
        title: "New Lesson",
        content: "",
        video_url: "",
        video_duration: 0,
        is_preview: false,
      });

      if (response.status !== 200 && response.status !== 201) {
        throw new Error("Failed to create lesson on server");
      }

      const newLesson = response.data;

      // Add to local UI state with the REAL backend ID
      const newLecture: Lecture = {
        id: newLesson.id?.toString() || Date.now().toString(),
        title: newLesson.title || "New Lesson",
        type: "text",
        duration: "",
        content: "",
        youtubeUrl: "",
        isPreview: false,
      };

      setForm((prev) => ({
        ...prev,
        courseStructure: {
          sections: prev.courseStructure.sections.map((section) =>
            section.id === sectionId
              ? { ...section, lectures: [...section.lectures, newLecture] }
              : section,
          ),
        },
      }));

      toast.success("Lesson created successfully");
    } catch (error: any) {
      console.error("Error creating lesson:", error);
      toast.error(
        error?.response?.data?.detail ||
          error?.message ||
          "Failed to create lesson",
      );
    } finally {
      setAddingLecture(false);
    }
  };

  const updateLecture = (
    sectionId: string,
    lectureId: string,
    field: string,
    value: any,
  ) => {
    setForm((prev) => ({
      ...prev,
      courseStructure: {
        sections: prev.courseStructure.sections.map((section) =>
          section.id === sectionId
            ? {
                ...section,
                lectures: section.lectures.map((lecture) =>
                  lecture.id === lectureId
                    ? { ...lecture, [field]: value }
                    : lecture,
                ),
              }
            : section,
        ),
      },
    }));

    // Also update on backend if we have a course ID and a real lesson ID (not a temp ID)
    if (courseId && !isNaN(Number(lectureId))) {
      const updateData: Record<string, any> = {};
      if (field === "title") updateData.title = value as string;
      else if (field === "content") updateData.content = value as string;
      else if (field === "videoUrl") updateData.video_url = value as string;
      else if (field === "youtubeUrl") updateData.youtube_url = value as string;
      else if (
        field === "contentType" ||
        field === "h5pContentId" ||
        field === "gameId" ||
        field === "geogebraAppletId" ||
        field === "threeDModelId" ||
        field === "virtualLabSim"
      ) {
        // The backend validates (lesson_content_type, h5p_content_id,
        // game_id) as an atomic set — PATCHing type='h5p'/'game' alone is
        // a 400. Only the flip back to video syncs alone here (the server
        // clears both FKs); 'h5p'/'game' sync together with their id once
        // content is actually picked. See lessonContentSync.ts.
        Object.assign(
          updateData,
          lessonContentSyncPayload(field, value as any),
        );
      } else if (field === "duration")
        updateData.video_duration = parseInt(value) || 0;
      else if (field === "isPreview") updateData.is_preview = value as boolean;

      if (Object.keys(updateData).length > 0) {
        // Debounce: delay the API call slightly to avoid spamming
        setTimeout(async () => {
          try {
            await api.patch(
              `/courses/${courseId}/lessons/${lectureId}`,
              updateData,
            );
          } catch (err) {
            console.error("Failed to sync lesson update to backend:", err);
          }
        }, 1000);
      }
    }
  };

  const removeLecture = async (sectionId: string, lectureId: string) => {
    // Remove from local UI immediately
    setForm((prev) => ({
      ...prev,
      courseStructure: {
        sections: prev.courseStructure.sections.map((section) =>
          section.id === sectionId
            ? {
                ...section,
                lectures: section.lectures.filter(
                  (lecture) => lecture.id !== lectureId,
                ),
              }
            : section,
        ),
      },
    }));

    // Also delete from backend if it's a real lesson ID
    if (courseId && !isNaN(Number(lectureId))) {
      try {
        await api.delete(`/courses/${courseId}/lessons/${lectureId}`);
      } catch (err) {
        console.error("Failed to delete lesson from backend:", err);
      }
    }
  };

  const createOrUpdateCourse = async (publishImmediately: boolean = false) => {
    try {
      setIsSubmitting(true);

      // Calculate total duration from all lectures (in minutes)
      const totalDuration = form.courseStructure.sections.reduce(
        (total, section) => {
          return (
            total +
            section.lectures.reduce((sectionTotal, lecture) => {
              const duration = parseInt(lecture.duration) || 0;
              return sectionTotal + duration;
            }, 0)
          );
        },
        0,
      );

      // Count lessons that were already created via addLecture
      const lessonCount = form.courseStructure.sections.reduce(
        (sum, section) => sum + section.lectures.length,
        0,
      );

      // Create course data payload (metadata only — lessons were already created via addLecture)
      const courseData: Record<string, any> = {
        title: form.title,
        slug: form.slug || undefined,
        description: form.description,
        excerpt: form.shortDescription,
        content: form.description,
        thumbnail: form.thumbnail,
        intro_video: form.introVideo || null,
        price: parseFloat(form.price) || 0,
        sale_price: parseFloat(form.discountPrice) || null,
        level: form.level,
        category: form.category,
        course_type: form.courseType || undefined,
        language: form.language,
        requirements: form.requirements.filter((r) => r.trim()),
        benefits: form.learningObjectives.filter((o) => o.trim()),
        duration: totalDuration,
        certificate_id: form.certificateId ? Number(form.certificateId) : null,
      };

      let targetCourseId = courseId;

      if (targetCourseId) {
        // Update existing course
        courseData.status =
          publishImmediately || isAdmin ? "published" : "draft";
        await courseAPI.updateCourse(targetCourseId, courseData);
      } else {
        // Create new course (only if somehow no course was created yet)
        const createdCourse = await courseAPI.createCourse(
          isAdmin && selectedInstructorId
            ? { ...courseData, instructor_id: selectedInstructorId }
            : courseData,
        );
        targetCourseId = createdCourse.id;
        setCourseId(targetCourseId);
      }

      // Publish if requested
      if (publishImmediately) {
        // Always use force-publish for admin, regular publish for instructor
        const token = localStorage.getItem("access_token");
        if (isAdmin) {
          await fetch(`/api/v1/admin/courses/${targetCourseId}/force-publish`, {
            method: "PATCH",
            headers: { Authorization: `Bearer ${token}` },
          });
        } else {
          await courseAPI.publishCourse(targetCourseId);
        }
        toast.success(
          `Course "${form.title}" with ${lessonCount} lessons published!`,
        );
      } else {
        toast.success(
          `Course "${form.title}" with ${lessonCount} lessons saved as draft!`,
        );
      }

      navigate(isAdmin ? "/admin/courses" : "/instructor/courses");
    } catch (error: any) {
      console.error("Failed to save course:", error);
      const errorMsg =
        error?.response?.data?.detail ||
        error?.message ||
        "Failed to save course";
      toast.error(errorMsg);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    await createOrUpdateCourse(false); // Save as draft by default
  };

  const handlePublish = async () => {
    await createOrUpdateCourse(true); // Publish the course
  };

  // Auto-save draft functionality when completing a step
  const autoSaveDraft = async (stepCompleted: number) => {
    if (isAdmin) return; // Admin courses don't auto-save as draft
    setIsAutoSaving(true);
    try {
      // Prepare course data based on current step
      const courseData: any = {
        title: form.title || "Draft Course",
        slug: form.slug || undefined,
        description: form.description || "",
        short_description: form.shortDescription || "",
        category: form.category || "",
        course_type: form.courseType || undefined,
        level: form.level || "beginner",
        language: form.language || "English",
        price: parseFloat(form.price) || 0,
        thumbnail: form.thumbnail || "",
        status: isAdmin ? "published" : "draft", // Admin courses auto-publish
        requirements: form.requirements.filter((r) => r.trim()),
        benefits: form.learningObjectives.filter((o) => o.trim()),
        certificate_id: form.certificateId ? Number(form.certificateId) : null,
      };

      // Add tags if available
      if (form.tags.length > 0) {
        courseData.tags = form.tags;
      }

      // Add course structure if we're in step 3 or beyond
      if (stepCompleted >= 3 && form.courseStructure.sections.length > 0) {
        courseData.course_structure = form.courseStructure;
      }

      let createdCourse;
      if (courseId) {
        // Update existing course
        createdCourse = await courseAPI.updateCourse(courseId, courseData);
      } else {
        // Create new course draft
        createdCourse = await courseAPI.createCourse(
          isAdmin && selectedInstructorId
            ? { ...courseData, instructor_id: selectedInstructorId }
            : courseData,
        );
        setCourseId(createdCourse.id);
      }

      // Show subtle success message for auto-save
      toast.success(`Course auto-saved as draft`, {
        duration: 2000,
        style: {
          background: "#10b981",
          color: "white",
          fontSize: "14px",
        },
      });
    } catch (error: any) {
      console.error(`Failed to auto-save after Step ${stepCompleted}:`, error);
      // Show subtle error message for auto-save failure (don't block navigation)
      toast.error("Auto-save failed, but you can continue working", {
        duration: 3000,
        style: {
          background: "#f59e0b",
          color: "white",
          fontSize: "14px",
        },
      });
    } finally {
      setIsAutoSaving(false);
    }
  };

  const nextStep = async () => {
    // Only auto-save if moving forward (not backward)
    const currentStepNumber = currentStep;
    const nextStepNumber = Math.min(currentStep + 1, 4);

    // Auto-save when completing steps 1, 2, or 3
    if (currentStepNumber < 4 && currentStepNumber >= 1) {
      // Validate current step before proceeding
      let canProceed = true;
      let errorMessage = "";

      if (currentStepNumber === 1) {
        // Step 1 validation: title and description are required
        if (!form.title.trim()) {
          errorMessage = "Please enter a course title";
          canProceed = false;
        } else if (!form.description.trim()) {
          errorMessage = "Please enter a course description";
          canProceed = false;
        } else if (!form.courseType) {
          errorMessage =
            "Please choose a course type (Meiporul, Seyappaduporul or Utporul)";
          canProceed = false;
        } else if (!form.category) {
          errorMessage = "Please select a category";
          canProceed = false;
        }
      } else if (currentStepNumber === 2) {
        // Step 2 validation: at least one requirement and one learning objective
        const validRequirements = form.requirements.filter((r) => r.trim());
        const validObjectives = form.learningObjectives.filter((o) => o.trim());
        if (validRequirements.length === 0) {
          errorMessage = "Please add at least one course requirement";
          canProceed = false;
        } else if (validObjectives.length === 0) {
          errorMessage = "Please add at least one learning objective";
          canProceed = false;
        }
      }
      // Step 3 doesn't require validation - curriculum can be empty initially

      if (!canProceed) {
        toast.error(errorMessage);
        return;
      }

      // Auto-save the current progress
      await autoSaveDraft(currentStepNumber);
    }

    // Move to next step
    setCurrentStep(nextStepNumber);
  };

  const prevStep = () => {
    // Going back doesn't need auto-save (we already saved when moving forward)
    setCurrentStep((prev) => Math.max(prev - 1, 1));
  };

  const stepTitles = [
    "Basic Information",
    "Course Content",
    "Curriculum",
    "Publish",
  ];

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <PageLayout
        header={
          <PageHeader>
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center">
                <Link
                  to="/instructor/courses"
                  className="flex items-center text-blue-600 hover:text-blue-700 mr-4"
                >
                  <ArrowLeft className="h-4 w-4 mr-1" />
                  Back to Courses
                </Link>
                <h1 className="text-3xl font-bold text-gray-900">
                  Create New Course
                </h1>
              </div>

              {/* Auto-save Status */}
              <div className="flex items-center space-x-4">
                {courseId && (
                  <div className="flex items-center text-sm text-gray-600">
                    <div className="h-2 w-2 bg-green-500 rounded-full mr-2"></div>
                    Course ID: {courseId} (Draft)
                  </div>
                )}
                {isAutoSaving && (
                  <div className="flex items-center text-sm text-blue-600">
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600 mr-2"></div>
                    Auto-saving...
                  </div>
                )}
              </div>
            </div>

            <p className="text-gray-600">
              Your course will be automatically saved as a draft after each step
            </p>
          </PageHeader>
        }
        className="rd-screen rd-screen-instructor-create-course"
      >
        <div className="mb-8">
          <div className="flex items-center justify-between">
            {stepTitles.map((title, index) => {
              const stepNumber = index + 1;
              const isCompleted = stepNumber < currentStep;
              const isCurrent = stepNumber === currentStep;

              return (
                <div key={index} className="flex items-center">
                  <div className="flex flex-col items-center">
                    <div
                      className={`w-10 h-10 rounded-full flex items-center justify-center text-sm font-semibold transition-all duration-200 ${
                        isCompleted
                          ? "bg-blue-600 text-white shadow-md"
                          : isCurrent
                            ? "border-2 border-blue-600 text-blue-600 bg-blue-50"
                            : "border-2 border-gray-300 text-gray-400 bg-white"
                      }`}
                    >
                      {isCompleted ? (
                        <svg
                          className="w-5 h-5"
                          fill="currentColor"
                          viewBox="0 0 20 20"
                        >
                          <path
                            fillRule="evenodd"
                            d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                            clipRule="evenodd"
                          />
                        </svg>
                      ) : (
                        stepNumber
                      )}
                    </div>
                    <div
                      className={`mt-2 text-sm font-medium whitespace-nowrap ${
                        isCurrent
                          ? "text-blue-600"
                          : isCompleted
                            ? "text-gray-900"
                            : "text-gray-500"
                      }`}
                    >
                      {title}
                    </div>
                  </div>
                  {index < stepTitles.length - 1 && (
                    <div
                      className={`mx-4 flex-1 h-0.5 transition-all duration-200 ${
                        isCompleted ? "bg-blue-600" : "bg-gray-300"
                      }`}
                    />
                  )}
                </div>
              );
            })}
          </div>
        </div>
        <form onSubmit={handleSubmit}>
          {quizModalLecture && (
            <QuizSetupModal
              courseId={courseId}
              ensureCourseExists={ensureCourseExists}
              defaultCourseType={form.courseType}
              onCourseTypeChange={(t) =>
                setForm((prev) => ({ ...prev, courseType: t }))
              }
              onClose={() => setQuizModalLecture(null)}
              onCreated={(quizId) => {
                if (quizModalLecture) {
                  updateLecture(
                    quizModalLecture.sectionId,
                    quizModalLecture.lectureId,
                    "quizId",
                    quizId,
                  );
                }
              }}
            />
          )}
          {/* Admin: Instructor Selector */}
          {isAdmin && (
            <div className="mb-6 p-4 bg-orange-50 border border-orange-200 rounded-xl">
              <label className="block text-sm font-semibold text-orange-800 mb-2">
                <AstraSymbol value="👑" /> Admin: Assign to Instructor
              </label>
              <select
                className="w-full border border-orange-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-orange-400 bg-white"
                value={selectedInstructorId || ""}
                onChange={(e) =>
                  setSelectedInstructorId(
                    e.target.value ? parseInt(e.target.value) : null,
                  )
                }
              >
                <option value="">Select instructor to assign course to</option>
                {instructors.map((i) => (
                  <option key={i.id} value={i.id}>
                    {i.name} ({i.email})
                  </option>
                ))}
              </select>
              {!selectedInstructorId && (
                <p className="text-xs text-orange-600 mt-1">
                  <AstraSymbol value="⚠️" /> Course will be assigned to you if
                  no instructor selected
                </p>
              )}
            </div>
          )}
          {/* Step 1: Basic Information */}
          {currentStep === 1 && (
            <Card className="p-8">
              <h2 className="text-2xl font-semibold text-gray-900 mb-2">
                Course Basic Information
              </h2>
              <p className="text-gray-600 text-sm mb-8">
                Tell us about your course and help students understand what
                they'll learn
              </p>

              <div className="space-y-8">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Course Title *
                    <span className="block text-xs font-normal text-gray-500 mt-1">
                      Choose a clear, descriptive title that tells students what
                      they'll learn
                    </span>
                  </label>
                  <input
                    type="text"
                    name="title"
                    value={form.title}
                    onChange={handleInputChange}
                    required
                    className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    placeholder="e.g., Complete Web Development Bootcamp 2024"
                  />
                </div>

                <CourseLinkField
                  value={form.slug || ""}
                  courseId={courseId}
                  onChange={(slug) => setForm((prev) => ({ ...prev, slug }))}
                />
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Short Description *
                    <span className="block text-xs font-normal text-gray-500 mt-1">
                      Write a brief summary that appears in course listings (max
                      120 characters recommended)
                    </span>
                  </label>
                  <input
                    type="text"
                    name="shortDescription"
                    value={form.shortDescription}
                    onChange={handleInputChange}
                    required
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    placeholder="Brief description for course preview"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Course Description *
                  </label>
                  <textarea
                    name="description"
                    value={form.description}
                    onChange={handleInputChange}
                    required
                    rows={6}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    placeholder="Detailed course description"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Course Type *
                    <span className="block text-xs font-normal text-gray-500 mt-1">
                      Every course belongs to exactly one type. Categories and
                      tags below are for sorting within the type.
                    </span>
                  </label>
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                    {COURSE_TYPES.map((t) => (
                      <button
                        key={t.value}
                        type="button"
                        onClick={() =>
                          setForm((prev) => ({ ...prev, courseType: t.value }))
                        }
                        className={`p-4 rounded-xl border-2 text-left transition-all ${t.cardClass} ${form.courseType === t.value ? t.selectedClass : "border-gray-200 bg-white"}`}
                      >
                        <div className="text-2xl mb-1">{t.emoji}</div>
                        <div className="font-semibold text-gray-900">
                          {t.label}
                        </div>
                        <div className="text-xs text-gray-500">{t.tamil}</div>
                        <div className="text-xs text-gray-400 mt-1">
                          {t.tagline}
                        </div>
                      </button>
                    ))}
                  </div>
                  {form.courseType && (
                    <div className="mt-2">
                      <p className="text-xs text-emerald-600">
                        ✓ Type: {courseTypeLabel(form.courseType)}
                      </p>
                      <p className="text-xs text-gray-500 mt-1">
                        Enabled tools:{" "}
                        {TYPE_TOOLS[form.courseType].tools
                          .map((t) => TOOL_LABELS[t])
                          .join(" · ")}
                        {TYPE_TOOLS[form.courseType].planned.length > 0 && (
                          <span className="text-gray-400">
                            {" "}
                            · coming soon:{" "}
                            {TYPE_TOOLS[form.courseType].planned
                              .map((t) => TOOL_LABELS[t])
                              .join(", ")}
                          </span>
                        )}
                      </p>
                    </div>
                  )}
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Category *
                    </label>
                    <input
                      type="text"
                      name="category"
                      value={form.category}
                      onChange={handleInputChange}
                      required
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      placeholder="Type any category — e.g. Tamil Grammar, NEET Biology"
                    />
                    <span className="text-xs text-gray-400 mt-1 block">
                      Free-form: categories are yours to define (used for
                      sorting within the type)
                    </span>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Level *
                    </label>
                    <select
                      name="level"
                      value={form.level}
                      onChange={handleInputChange}
                      required
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    >
                      <option value="">Select Level</option>
                      {levels.map((level) => (
                        <option key={level} value={level}>
                          {levelLabels[level]}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Course Language *
                      <span className="block text-xs font-normal text-gray-500 mt-1">
                        Select the primary language for course delivery. This
                        helps students find courses in their preferred language.
                      </span>
                    </label>
                    <select
                      name="language"
                      value={form.language}
                      onChange={handleInputChange}
                      required
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    >
                      {languages.map((lang) => (
                        <option key={lang.code} value={lang.name}>
                          {lang.flag} {lang.name}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Price (₹) *
                    </label>
                    <input
                      type="number"
                      name="price"
                      value={form.price}
                      onChange={handleInputChange}
                      required
                      min="0"
                      step="1"
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      placeholder="0"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Discount Price (₹)
                    </label>
                    <input
                      type="number"
                      name="discountPrice"
                      value={form.discountPrice}
                      onChange={handleInputChange}
                      min="0"
                      step="1"
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      placeholder="0"
                    />
                  </div>
                </div>

                <ImageUpload
                  value={form.thumbnail}
                  onChange={(url) =>
                    setForm((prev) => ({ ...prev, thumbnail: url }))
                  }
                  label="Course Thumbnail *"
                  aspectRatio="aspect-video"
                />

                <VideoUpload
                  value={form.introVideo}
                  onChange={(url) =>
                    setForm((prev) => ({ ...prev, introVideo: url }))
                  }
                  label="Course Intro Video (Optional)"
                />
              </div>
            </Card>
          )}

          {/* Step 2: Course Content */}
          {currentStep === 2 && (
            <Card className="p-6">
              <h2 className="text-xl font-semibold text-gray-900 mb-6">
                Course Content Details
              </h2>

              <div className="space-y-6">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Course Tags
                  </label>
                  <div className="flex flex-wrap gap-2 mb-3">
                    {form.tags.map((tag, index) => (
                      <span
                        key={index}
                        className="bg-blue-100 text-blue-800 px-3 py-1 rounded-full text-sm flex items-center"
                      >
                        {tag}
                        <button
                          type="button"
                          onClick={() => removeTag(tag)}
                          className="ml-2 text-blue-600 hover:text-blue-800"
                        >
                          ×
                        </button>
                      </span>
                    ))}
                  </div>
                  <div className="flex gap-2">
                    <input
                      type="text"
                      value={newTag}
                      onChange={(e) => setNewTag(e.target.value)}
                      placeholder="Add a tag"
                      className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      onKeyPress={(e) =>
                        e.key === "Enter" && (e.preventDefault(), addTag())
                      }
                    />
                    <Button type="button" onClick={addTag} variant="outline">
                      Add
                    </Button>
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Course Requirements
                  </label>
                  {form.requirements.map((requirement, index) => (
                    <div key={index} className="flex gap-2 mb-3">
                      <input
                        type="text"
                        value={requirement}
                        onChange={(e) =>
                          updateArrayField(
                            "requirements",
                            index,
                            e.target.value,
                          )
                        }
                        placeholder="What should students know before taking this course?"
                        className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      />
                      <Button
                        type="button"
                        variant="outline"
                        onClick={() => removeArrayField("requirements", index)}
                        className="text-red-600"
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  ))}
                  <Button
                    type="button"
                    variant="outline"
                    onClick={() => addArrayField("requirements")}
                  >
                    <Plus className="h-4 w-4 mr-2" />
                    Add Requirement
                  </Button>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Learning Objectives
                  </label>
                  {form.learningObjectives.map((objective, index) => (
                    <div key={index} className="flex gap-2 mb-3">
                      <input
                        type="text"
                        value={objective}
                        onChange={(e) =>
                          updateArrayField(
                            "learningObjectives",
                            index,
                            e.target.value,
                          )
                        }
                        placeholder="What will students learn from this course?"
                        className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      />
                      <Button
                        type="button"
                        variant="outline"
                        onClick={() =>
                          removeArrayField("learningObjectives", index)
                        }
                        className="text-red-600"
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  ))}
                  <Button
                    type="button"
                    variant="outline"
                    onClick={() => addArrayField("learningObjectives")}
                  >
                    <Plus className="h-4 w-4 mr-2" />
                    Add Learning Objective
                  </Button>
                </div>

                {/* Certificate Template */}
                <div className="border border-gray-200 rounded-xl p-5 bg-orange-50/50">
                  <label className="block text-sm font-semibold text-gray-900 mb-1">
                    Certificate Template
                  </label>
                  <p className="text-xs text-gray-500 mb-4">
                    Pick the certificate students receive when they complete
                    this course. You can change this later in course settings.
                  </p>
                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                    {/* No Certificate */}
                    <div
                      onClick={() => setForm({ ...form, certificateId: "" })}
                      className={`cursor-pointer rounded-xl border-2 p-4 flex flex-col items-center justify-center gap-2 h-40 transition-all ${!form.certificateId ? "border-orange-500 bg-orange-50 shadow-md" : "border-gray-200 bg-white hover:border-gray-300"}`}
                      data-glass="content"
                    >
                      <span className="text-3xl">
                        <AstraSymbol value="🚫" />
                      </span>
                      <p className="font-medium text-gray-700 text-sm">
                        No Certificate
                      </p>
                      <p className="text-xs text-gray-400 text-center">
                        Students won't receive a certificate
                      </p>
                    </div>
                    {certTemplates.map((t: any) => (
                      <div
                        key={t.id}
                        onClick={() =>
                          setForm({ ...form, certificateId: String(t.id) })
                        }
                        className={`group cursor-pointer rounded-xl border-2 overflow-hidden transition-all ${String(form.certificateId) === String(t.id) ? "border-orange-500 shadow-md" : "border-gray-200 hover:border-orange-300"}`}
                      >
                        <div
                          className="h-28 relative overflow-hidden flex flex-col items-center justify-center p-3"
                          style={{
                            backgroundColor: t.bg_color || "#FFF8DC",
                            fontFamily: t.font || "Georgia",
                          }}
                        >
                          {t.thumbnail ? (
                            <img
                              src={t.thumbnail}
                              alt={t.name || `Template ${t.id}`}
                              loading="lazy"
                              className="absolute inset-0 w-full h-full object-cover"
                              onError={(e) => {
                                (
                                  e.currentTarget as HTMLImageElement
                                ).style.display = "none";
                              }}
                            />
                          ) : null}
                          <p
                            className="text-[10px] font-semibold tracking-widest uppercase opacity-60"
                            style={{ color: t.title_color }}
                          >
                            Certificate
                          </p>
                          <p
                            className="text-sm font-bold mt-1"
                            style={{ color: t.title_color }}
                          >
                            Student Name
                          </p>
                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation();
                              setPreviewTemplate(t);
                            }}
                            className="absolute top-2 right-2 z-10 bg-white/90 hover:bg-white text-gray-700 text-[11px] font-semibold px-2 py-1 rounded-md shadow-sm opacity-0 group-hover:opacity-100 transition-opacity"
                          >
                            <AstraSymbol value="🔍" /> Preview
                          </button>
                        </div>
                        <div
                          className={`px-3 py-2 flex items-center justify-between ${String(form.certificateId) === String(t.id) ? "bg-orange-50" : "bg-white"}`}
                        >
                          <p className="text-sm font-medium text-gray-800 truncate">
                            {t.name || `Template ${t.id}`}
                          </p>
                          {String(form.certificateId) === String(t.id) && (
                            <span className="text-orange-500 text-xs font-bold whitespace-nowrap ml-2">
                              ✓ Selected
                            </span>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </Card>
          )}

          {/* Certificate template full-size preview */}
          {previewTemplate && (
            <div
              className="fixed inset-0 z-modal bg-black/70 flex items-center justify-center p-4"
              onClick={() => setPreviewTemplate(null)}
            >
              <div
                className="bg-white rounded-2xl max-w-4xl w-full overflow-hidden shadow-2xl"
                onClick={(e) => e.stopPropagation()}
                data-glass="content"
              >
                <div className="flex items-center justify-between px-5 py-3 border-b border-gray-100">
                  <p className="font-semibold text-gray-900">
                    {previewTemplate.name || "Certificate Template"}
                  </p>
                  <button
                    type="button"
                    onClick={() => setPreviewTemplate(null)}
                    className="text-gray-400 hover:text-gray-700 text-2xl leading-none"
                  >
                    ×
                  </button>
                </div>
                <div className="bg-gray-50 p-4 flex items-center justify-center">
                  <img
                    src={previewTemplate.thumbnail}
                    alt={previewTemplate.name || "Certificate preview"}
                    className="max-h-[70vh] w-auto object-contain rounded-lg shadow"
                  />
                </div>
              </div>
            </div>
          )}

          {/* Step 3: Curriculum */}
          {currentStep === 3 && (
            <Card className="p-6">
              <h2 className="text-xl font-semibold text-gray-900 mb-6">
                Course Curriculum
              </h2>

              <div className="space-y-6">
                {form.courseStructure.sections.map((section, sectionIndex) => (
                  <div
                    key={section.id}
                    className="border border-gray-200 rounded-lg p-4"
                  >
                    <div className="flex items-center justify-between mb-4">
                      <h3 className="text-lg font-medium text-gray-900">
                        Section {sectionIndex + 1}
                      </h3>
                      <Button
                        type="button"
                        variant="outline"
                        onClick={() => removeSection(section.id)}
                        className="text-red-600"
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>

                    <div className="space-y-4">
                      <input
                        type="text"
                        value={section.title}
                        onChange={(e) =>
                          updateSection(section.id, "title", e.target.value)
                        }
                        placeholder="Section title"
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      />

                      <textarea
                        value={section.description}
                        onChange={(e) =>
                          updateSection(
                            section.id,
                            "description",
                            e.target.value,
                          )
                        }
                        placeholder="Section description"
                        rows={2}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      />

                      {/* Lectures */}
                      <div className="ml-4">
                        <h4 className="text-sm font-medium text-gray-700 mb-2">
                          Lectures
                        </h4>
                        {section.lectures.map((lecture) => (
                          <div
                            key={lecture.id}
                            className="flex gap-2 mb-3 p-3 bg-gray-50 rounded"
                          >
                            <div className="flex-1 space-y-3">
                              <input
                                type="text"
                                value={lecture.title}
                                onChange={(e) =>
                                  updateLecture(
                                    section.id,
                                    lecture.id,
                                    "title",
                                    e.target.value,
                                  )
                                }
                                placeholder="Lecture title"
                                className="w-full px-3 py-2 border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
                              />
                              <div className="flex gap-2">
                                <select
                                  value={lecture.type}
                                  onChange={(e) =>
                                    updateLecture(
                                      section.id,
                                      lecture.id,
                                      "type",
                                      e.target.value,
                                    )
                                  }
                                  className="px-3 py-2 border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
                                >
                                  <option value="video">Video</option>
                                  <option value="text">Text</option>
                                  <option value="quiz">Quiz</option>
                                  <option value="assignment">Assignment</option>
                                </select>
                                <input
                                  type="number"
                                  value={lecture.duration}
                                  onChange={(e) =>
                                    updateLecture(
                                      section.id,
                                      lecture.id,
                                      "duration",
                                      e.target.value,
                                    )
                                  }
                                  placeholder="Duration (minutes)"
                                  className="px-3 py-2 border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
                                  min="0"
                                />
                              </div>

                              {/* Video Upload for video lectures */}
                              {lecture.type === "video" && (
                                <>
                                  {/* Content-type sub-toggle — same pattern as
                                      edit-course.tsx: a "video" lecture's actual
                                      player content can be a plain video, a
                                      sandboxed H5P interactive item, or a native
                                      learning game. */}
                                  <div className="space-y-2">
                                    <label className="block text-sm font-medium text-gray-700">
                                      Content type
                                    </label>
                                    <select
                                      value={lecture.contentType || "video"}
                                      onChange={(e) => {
                                        const nextType = e.target
                                          .value as NonNullable<
                                          Lecture["contentType"]
                                        >;
                                        updateLecture(
                                          section.id,
                                          lecture.id,
                                          "contentType",
                                          nextType,
                                        );
                                        if (nextType !== "h5p")
                                          updateLecture(
                                            section.id,
                                            lecture.id,
                                            "h5pContentId",
                                            null,
                                          );
                                        if (nextType !== "game")
                                          updateLecture(
                                            section.id,
                                            lecture.id,
                                            "gameId",
                                            null,
                                          );
                                        if (nextType !== "geogebra")
                                          updateLecture(
                                            section.id,
                                            lecture.id,
                                            "geogebraAppletId",
                                            null,
                                          );
                                        if (nextType !== "three_d")
                                          updateLecture(
                                            section.id,
                                            lecture.id,
                                            "threeDModelId",
                                            null,
                                          );
                                        if (nextType !== "virtual_lab")
                                          updateLecture(
                                            section.id,
                                            lecture.id,
                                            "virtualLabSim",
                                            null,
                                          );
                                      }}
                                      className="px-3 py-2 text-sm border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                    >
                                      <option value="video">Video</option>
                                      <option
                                        value="geogebra"
                                        disabled={
                                          !typeSupports(
                                            form.courseType,
                                            "geogebra",
                                          ) ||
                                          (parseFloat(form.price) || 0) !== 0
                                        }
                                      >
                                        GeoGebra interactive{" "}
                                        <AstraSymbol value="📐" />
                                        {!typeSupports(
                                          form.courseType,
                                          "geogebra",
                                        )
                                          ? " — MP/UP only"
                                          : (parseFloat(form.price) || 0) !== 0
                                            ? " — free courses only"
                                            : ""}
                                      </option>
                                      <option
                                        value="three_d"
                                        disabled={
                                          !typeSupports(
                                            form.courseType,
                                            "three_d_models",
                                          )
                                        }
                                      >
                                        <AstraSymbol value="🧊" /> 3D Model
                                        (GLB)
                                        {!typeSupports(
                                          form.courseType,
                                          "three_d_models",
                                        )
                                          ? " — MP/UP only"
                                          : ""}
                                      </option>
                                      <option value="virtual_lab">
                                        <AstraSymbol value="🔬" /> Virtual Lab
                                        (PhET)
                                      </option>
                                    </select>
                                    <p className="text-[11px] text-gray-400 mt-0.5">
                                      H5P &amp; games are scored modules inside
                                      quizzes — add them via the Quiz setup
                                      popup
                                    </p>
                                  </div>

                                  {lecture.contentType === "h5p" ? (
                                    <H5PPicker
                                      value={lecture.h5pContentId ?? null}
                                      onChange={(contentId) =>
                                        updateLecture(
                                          section.id,
                                          lecture.id,
                                          "h5pContentId",
                                          contentId,
                                        )
                                      }
                                    />
                                  ) : lecture.contentType === "geogebra" ? (
                                    <GeoGebraAuthorCard
                                      title={lecture.title}
                                      attachedId={
                                        lecture.geogebraAppletId ?? null
                                      }
                                      onAttach={(appletId) =>
                                        updateLecture(
                                          section.id,
                                          lecture.id,
                                          "geogebraAppletId",
                                          appletId,
                                        )
                                      }
                                    />
                                  ) : lecture.contentType === "three_d" ? (
                                    <ThreeDModelPicker
                                      title={lecture.title}
                                      attachedId={lecture.threeDModelId ?? null}
                                      onAttach={(modelId) =>
                                        updateLecture(
                                          section.id,
                                          lecture.id,
                                          "threeDModelId",
                                          modelId,
                                        )
                                      }
                                    />
                                  ) : lecture.contentType === "virtual_lab" ? (
                                    <VirtualLabPicker
                                      attachedSim={
                                        lecture.virtualLabSim ?? null
                                      }
                                      onAttach={(sim) =>
                                        updateLecture(
                                          section.id,
                                          lecture.id,
                                          "virtualLabSim",
                                          sim,
                                        )
                                      }
                                    />
                                  ) : lecture.contentType === "game" ? (
                                    <GamePicker
                                      value={lecture.gameId ?? null}
                                      onChange={(gameId) =>
                                        updateLecture(
                                          section.id,
                                          lecture.id,
                                          "gameId",
                                          gameId,
                                        )
                                      }
                                    />
                                  ) : (
                                    <>
                                      {(() => {
                                        const src =
                                          lecture.videoSource ??
                                          (lecture.youtubeUrl
                                            ? "youtube"
                                            : "upload");
                                        const setSrc = (
                                          v: "upload" | "youtube" | "direct",
                                        ) => {
                                          updateLecture(
                                            section.id,
                                            lecture.id,
                                            "videoSource",
                                            v,
                                          );
                                        };
                                        return (
                                          <div className="space-y-2">
                                            <div
                                              className="flex gap-2"
                                              role="tablist"
                                              aria-label="Video source"
                                            >
                                              {(
                                                [
                                                  ["upload", "⬆ Upload"],
                                                  ["youtube", "▶ YouTube"],
                                                  [
                                                    "direct",
                                                    "🔗 Direct URL (Bunny/CDN)",
                                                  ],
                                                ] as const
                                              ).map(([v, label]) => (
                                                <button
                                                  key={v}
                                                  type="button"
                                                  role="tab"
                                                  aria-selected={src === v}
                                                  onClick={() => setSrc(v)}
                                                  className={`px-3 py-1.5 text-xs font-medium rounded-full border ${src === v ? "bg-blue-600 text-white border-blue-600" : "bg-white text-gray-700 border-gray-300"}`}
                                                >
                                                  {label}
                                                </button>
                                              ))}
                                            </div>
                                            {src === "upload" && (
                                              <VideoUpload
                                                value={lecture.videoUrl}
                                                onChange={(url) =>
                                                  updateLecture(
                                                    section.id,
                                                    lecture.id,
                                                    "videoUrl",
                                                    url,
                                                  )
                                                }
                                                onDurationChange={(duration) =>
                                                  updateLecture(
                                                    section.id,
                                                    lecture.id,
                                                    "duration",
                                                    duration.toString(),
                                                  )
                                                }
                                                label="Upload Lecture Video"
                                              />
                                            )}
                                            {src === "youtube" && (
                                              <div className="space-y-1">
                                                <input
                                                  type="url"
                                                  value={
                                                    lecture.youtubeUrl || ""
                                                  }
                                                  onChange={(e) =>
                                                    updateLecture(
                                                      section.id,
                                                      lecture.id,
                                                      "youtubeUrl",
                                                      e.target.value,
                                                    )
                                                  }
                                                  placeholder="https://www.youtube.com/watch?v=..."
                                                  className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
                                                />
                                                <p className="text-xs text-gray-500">
                                                  Plays without branding via the
                                                  built-in extractor
                                                </p>
                                              </div>
                                            )}
                                            {src === "direct" && (
                                              <div className="space-y-1">
                                                <input
                                                  type="url"
                                                  value={lecture.videoUrl || ""}
                                                  onChange={(e) =>
                                                    updateLecture(
                                                      section.id,
                                                      lecture.id,
                                                      "videoUrl",
                                                      e.target.value,
                                                    )
                                                  }
                                                  placeholder="https://cdn.example.com/lecture.m3u8 or .mp4 (Bunny/CDN)"
                                                  className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
                                                />
                                                <p className="text-xs text-gray-500">
                                                  Any direct MP4/HLS stream link
                                                </p>
                                              </div>
                                            )}
                                          </div>
                                        );
                                      })()}
                                    </>
                                  )}
                                </>
                              )}

                              {/* Text content area */}
                              {lecture.type === "text" && (
                                <textarea
                                  value={lecture.content}
                                  onChange={(e) =>
                                    updateLecture(
                                      section.id,
                                      lecture.id,
                                      "content",
                                      e.target.value,
                                    )
                                  }
                                  placeholder="Lecture content"
                                  className="w-full px-3 py-2 border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
                                  rows={3}
                                />
                              )}

                              {/* Quiz Configuration - Inline Builder */}
                              {lecture.type === "quiz" && (
                                <div className="mt-3 p-4 bg-purple-50 border border-purple-200 rounded-lg">
                                  {lecture.quizId ? (
                                    <div className="flex flex-wrap items-center gap-3">
                                      <span className="text-sm font-medium text-emerald-700">
                                        ✓ Quiz created (#{lecture.quizId})
                                      </span>
                                      <Link
                                        to={`/instructor/courses/${courseId}/quiz-builder/${lecture.quizId}`}
                                        className="text-sm text-blue-600 hover:underline"
                                      >
                                        Open Quiz Builder
                                      </Link>
                                      <button
                                        type="button"
                                        onClick={() =>
                                          setQuizModalLecture({
                                            sectionId: section.id,
                                            lectureId: lecture.id,
                                          })
                                        }
                                        className="text-sm text-gray-500 hover:text-gray-700 underline"
                                      >
                                        Reconfigure
                                      </button>
                                    </div>
                                  ) : (
                                    <div className="flex flex-wrap items-center justify-between gap-3">
                                      <div>
                                        <h5 className="font-medium text-gray-900">
                                          Quiz setup
                                        </h5>
                                        <p className="text-xs text-gray-500 mt-0.5">
                                          Pick the course type, then add
                                          questions — all in one popup.
                                        </p>
                                      </div>
                                      <button
                                        type="button"
                                        onClick={() =>
                                          setQuizModalLecture({
                                            sectionId: section.id,
                                            lectureId: lecture.id,
                                          })
                                        }
                                        className="px-4 py-2 bg-purple-600 text-white rounded-lg text-sm font-medium hover:bg-purple-700"
                                      >
                                        ⚙ Set Up Quiz (opens popup)
                                      </button>
                                    </div>
                                  )}
                                </div>
                              )}

                              {/* Assignment Configuration - Inline Builder */}
                              {lecture.type === "assignment" && (
                                <div className="mt-3 p-4 bg-orange-50 border border-orange-200 rounded-lg">
                                  <h5 className="font-medium text-gray-900 mb-3">
                                    Assignment Configuration
                                  </h5>

                                  {/* Assignment Settings */}
                                  <div className="space-y-3">
                                    <div>
                                      <label className="block text-xs font-medium text-gray-700 mb-1">
                                        Assignment Description
                                      </label>
                                      <textarea
                                        value={
                                          lecture.assignmentData?.description ||
                                          ""
                                        }
                                        onChange={(e) => {
                                          const assignmentData =
                                            lecture.assignmentData || {
                                              title: lecture.title,
                                              description: "",
                                              maxScore: 100,
                                              allowedFileTypes: [
                                                "pdf",
                                                "doc",
                                                "docx",
                                              ],
                                              attachments: [],
                                            };
                                          updateLecture(
                                            section.id,
                                            lecture.id,
                                            "assignmentData",
                                            {
                                              ...assignmentData,
                                              description: e.target.value,
                                            },
                                          );
                                        }}
                                        placeholder="Describe what students need to submit..."
                                        className="w-full px-2 py-1 border border-gray-300 rounded text-sm"
                                        rows={3}
                                      />
                                    </div>

                                    <div>
                                      <label className="block text-xs font-medium text-gray-700 mb-1">
                                        Reference Files (Optional)
                                        <span className="text-gray-500 font-normal ml-1">
                                          - Upload files for students to
                                          reference
                                        </span>
                                      </label>
                                      <div className="space-y-2">
                                        <DocumentUpload
                                          onChange={(url) => {
                                            const assignmentData =
                                              lecture.assignmentData || {
                                                title: lecture.title,
                                                description: "",
                                                maxScore: 100,
                                                allowedFileTypes: [
                                                  "pdf",
                                                  "doc",
                                                  "docx",
                                                ],
                                                attachments: [],
                                              };
                                            const attachments =
                                              assignmentData.attachments || [];
                                            updateLecture(
                                              section.id,
                                              lecture.id,
                                              "assignmentData",
                                              {
                                                ...assignmentData,
                                                attachments: [
                                                  ...attachments,
                                                  url,
                                                ],
                                              },
                                            );
                                          }}
                                          className="w-full"
                                        />
                                        {lecture.assignmentData?.attachments &&
                                          lecture.assignmentData.attachments
                                            .length > 0 && (
                                            <div className="space-y-1">
                                              {lecture.assignmentData.attachments.map(
                                                (attachment, idx) => (
                                                  <div
                                                    key={idx}
                                                    className="flex items-center justify-between text-xs bg-gray-50 px-2 py-1 rounded"
                                                  >
                                                    <span className="truncate flex-1">
                                                      {attachment
                                                        .split("/")
                                                        .pop()}
                                                    </span>
                                                    <button
                                                      type="button"
                                                      onClick={() => {
                                                        const assignmentData =
                                                          lecture.assignmentData!;
                                                        const attachments =
                                                          assignmentData.attachments!.filter(
                                                            (_, i) => i !== idx,
                                                          );
                                                        updateLecture(
                                                          section.id,
                                                          lecture.id,
                                                          "assignmentData",
                                                          {
                                                            ...assignmentData,
                                                            attachments,
                                                          },
                                                        );
                                                      }}
                                                      className="ml-2 text-red-600 hover:text-red-800"
                                                    >
                                                      <Trash2 className="h-3 w-3" />
                                                    </button>
                                                  </div>
                                                ),
                                              )}
                                            </div>
                                          )}
                                      </div>
                                    </div>

                                    <div className="grid grid-cols-2 gap-3">
                                      <div>
                                        <label className="block text-xs font-medium text-gray-700 mb-1">
                                          Maximum Score
                                        </label>
                                        <input
                                          type="number"
                                          value={
                                            lecture.assignmentData?.maxScore ||
                                            100
                                          }
                                          onChange={(e) => {
                                            const assignmentData =
                                              lecture.assignmentData || {
                                                title: lecture.title,
                                                description: "",
                                                maxScore: 100,
                                                allowedFileTypes: [
                                                  "pdf",
                                                  "doc",
                                                  "docx",
                                                ],
                                              };
                                            updateLecture(
                                              section.id,
                                              lecture.id,
                                              "assignmentData",
                                              {
                                                ...assignmentData,
                                                maxScore: parseInt(
                                                  e.target.value,
                                                ),
                                              },
                                            );
                                          }}
                                          className="w-full px-2 py-1 border border-gray-300 rounded text-sm"
                                          min="1"
                                        />
                                      </div>
                                      <div>
                                        <label className="block text-xs font-medium text-gray-700 mb-1">
                                          Due Date (optional)
                                        </label>
                                        <input
                                          type="date"
                                          value={
                                            lecture.assignmentData?.dueDate ||
                                            ""
                                          }
                                          onChange={(e) => {
                                            const assignmentData =
                                              lecture.assignmentData || {
                                                title: lecture.title,
                                                description: "",
                                                maxScore: 100,
                                                allowedFileTypes: [
                                                  "pdf",
                                                  "doc",
                                                  "docx",
                                                ],
                                              };
                                            updateLecture(
                                              section.id,
                                              lecture.id,
                                              "assignmentData",
                                              {
                                                ...assignmentData,
                                                dueDate: e.target.value,
                                              },
                                            );
                                          }}
                                          className="w-full px-2 py-1 border border-gray-300 rounded text-sm"
                                        />
                                      </div>
                                    </div>

                                    <div>
                                      <label className="block text-xs font-medium text-gray-700 mb-1">
                                        Allowed File Types
                                      </label>
                                      <div className="flex flex-wrap gap-2 mt-1">
                                        {[
                                          "pdf",
                                          "doc",
                                          "docx",
                                          "txt",
                                          "zip",
                                          "jpg",
                                          "png",
                                        ].map((fileType) => (
                                          <label
                                            key={fileType}
                                            className="flex items-center gap-1 text-xs"
                                          >
                                            <input
                                              type="checkbox"
                                              checked={(
                                                lecture.assignmentData
                                                  ?.allowedFileTypes || [
                                                  "pdf",
                                                  "doc",
                                                  "docx",
                                                ]
                                              ).includes(fileType)}
                                              onChange={(e) => {
                                                const assignmentData =
                                                  lecture.assignmentData || {
                                                    title: lecture.title,
                                                    description: "",
                                                    maxScore: 100,
                                                    allowedFileTypes: [
                                                      "pdf",
                                                      "doc",
                                                      "docx",
                                                    ],
                                                  };
                                                const newFileTypes = e.target
                                                  .checked
                                                  ? [
                                                      ...assignmentData.allowedFileTypes,
                                                      fileType,
                                                    ]
                                                  : assignmentData.allowedFileTypes.filter(
                                                      (ft) => ft !== fileType,
                                                    );
                                                updateLecture(
                                                  section.id,
                                                  lecture.id,
                                                  "assignmentData",
                                                  {
                                                    ...assignmentData,
                                                    allowedFileTypes:
                                                      newFileTypes,
                                                  },
                                                );
                                              }}
                                              className="text-orange-600"
                                            />
                                            <span className="uppercase">
                                              {fileType}
                                            </span>
                                          </label>
                                        ))}
                                      </div>
                                    </div>

                                    <div className="text-xs text-gray-600 bg-white p-2 rounded border border-orange-200">
                                      <strong>Instructions:</strong> Students
                                      will be able to upload files matching the
                                      selected types. Make sure to provide clear
                                      submission guidelines in the description
                                      above.
                                    </div>
                                  </div>
                                </div>
                              )}
                            </div>
                            <Button
                              type="button"
                              variant="outline"
                              onClick={() =>
                                removeLecture(section.id, lecture.id)
                              }
                              className="text-red-600"
                            >
                              <Trash2 className="h-4 w-4" />
                            </Button>
                          </div>
                        ))}
                        <Button
                          type="button"
                          variant="outline"
                          onClick={() => addLecture(section.id)}
                          size="sm"
                          disabled={addingLecture}
                        >
                          <Plus className="h-4 w-4 mr-2" />
                          {addingLecture ? "Adding…" : "Add Lecture"}
                        </Button>
                      </div>
                    </div>
                  </div>
                ))}

                <Button
                  type="button"
                  variant="outline"
                  onClick={addSection}
                  className="w-full"
                >
                  <Plus className="h-4 w-4 mr-2" />
                  Add Section
                </Button>
              </div>
            </Card>
          )}

          {/* Step 4: Publish */}
          {currentStep === 4 && (
            <div className="space-y-6">
              {/* Validation Checklist */}
              <Card className="p-6">
                <h2 className="text-xl font-semibold text-gray-900 mb-4">
                  Course Readiness Checklist
                </h2>
                <p className="text-sm text-gray-600 mb-6">
                  Review these requirements before publishing your course
                </p>

                <div className="space-y-3">
                  {[
                    {
                      label: "Course title",
                      value: form.title,
                      required: true,
                    },
                    {
                      label: "Course description",
                      value: form.description,
                      required: true,
                    },
                    {
                      label: "Course category",
                      value: form.category,
                      required: true,
                    },
                    {
                      label: "Course level",
                      value: form.level,
                      required: true,
                    },
                    {
                      label: "Course thumbnail",
                      value: form.thumbnail,
                      required: true,
                    },
                    {
                      label: "Course price",
                      value: form.price,
                      required: true,
                    },
                    {
                      label: "Learning objectives (at least 1)",
                      value:
                        form.learningObjectives.filter((o) => o.trim()).length >
                        0,
                      required: true,
                    },
                    {
                      label: "Requirements (at least 1)",
                      value:
                        form.requirements.filter((r) => r.trim()).length > 0,
                      required: false,
                    },
                    {
                      label: "Course sections (at least 1)",
                      value: form.courseStructure.sections.length > 0,
                      required: true,
                    },
                    {
                      label: "Lectures (at least 1)",
                      value:
                        form.courseStructure.sections.reduce(
                          (total, s) => total + s.lectures.length,
                          0,
                        ) > 0,
                      required: true,
                    },
                  ].map((item, index) => {
                    const isComplete =
                      typeof item.value === "boolean"
                        ? item.value
                        : Boolean(item.value && item.value.toString().trim());
                    return (
                      <div
                        key={index}
                        className="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
                      >
                        <div className="flex items-center">
                          <div
                            className={`w-5 h-5 rounded-full flex items-center justify-center mr-3 ${
                              isComplete
                                ? "bg-green-500"
                                : item.required
                                  ? "bg-red-100"
                                  : "bg-gray-300"
                            }`}
                          >
                            {isComplete ? (
                              <svg
                                className="w-3 h-3 text-white"
                                fill="currentColor"
                                viewBox="0 0 20 20"
                              >
                                <path
                                  fillRule="evenodd"
                                  d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                                  clipRule="evenodd"
                                />
                              </svg>
                            ) : (
                              <div
                                className={`w-2 h-2 rounded-full ${item.required ? "bg-red-500" : "bg-gray-400"}`}
                              ></div>
                            )}
                          </div>
                          <span
                            className={`text-sm ${isComplete ? "text-gray-900" : "text-gray-600"}`}
                          >
                            {item.label}
                          </span>
                        </div>
                        <span
                          className={`text-xs font-medium ${isComplete ? "text-green-600" : item.required ? "text-red-600" : "text-gray-500"}`}
                        >
                          {isComplete
                            ? "Complete"
                            : item.required
                              ? "Required"
                              : "Optional"}
                        </span>
                      </div>
                    );
                  })}
                </div>

                {/* Completion percentage */}
                {(() => {
                  const totalItems = 10;
                  const completedItems = [
                    form.title,
                    form.description,
                    form.category,
                    form.level,
                    form.thumbnail,
                    form.price,
                    form.learningObjectives.filter((o) => o.trim()).length > 0,
                    form.courseStructure.sections.length > 0,
                    form.courseStructure.sections.reduce(
                      (total, s) => total + s.lectures.length,
                      0,
                    ) > 0,
                  ].filter((item) =>
                    typeof item === "boolean"
                      ? item
                      : Boolean(item && item.toString().trim()),
                  ).length;

                  const percentage = Math.round(
                    (completedItems / totalItems) * 100,
                  );

                  return (
                    <div className="mt-6">
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-sm font-medium text-gray-700">
                          Course Completion
                        </span>
                        <span className="text-sm font-semibold text-blue-600">
                          {percentage}%
                        </span>
                      </div>
                      <div className="w-full bg-gray-200 rounded-full h-2">
                        <div
                          className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                          style={{ width: `${percentage}%` }}
                        />
                      </div>
                    </div>
                  );
                })()}
              </Card>

              {/* Course Preview */}
              <Card className="p-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">
                  Course Summary
                </h3>
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <span className="text-gray-600">Title:</span>
                    <p className="font-medium text-gray-900">
                      {form.title || "Not set"}
                    </p>
                  </div>
                  <div>
                    <span className="text-gray-600">Category:</span>
                    <p className="font-medium text-gray-900">
                      {form.category || "Not selected"}
                    </p>
                  </div>
                  <div>
                    <span className="text-gray-600">Level:</span>
                    <p className="font-medium text-gray-900">
                      {levelLabels[form.level] || "Not selected"}
                    </p>
                  </div>
                  <div>
                    <span className="text-gray-600">Language:</span>
                    <p className="font-medium text-gray-900">{form.language}</p>
                  </div>
                  <div>
                    <span className="text-gray-600">Price:</span>
                    <p className="font-medium text-gray-900">
                      ₹{form.price || "0"}
                    </p>
                  </div>
                  <div>
                    <span className="text-gray-600">Discount Price:</span>
                    <p className="font-medium text-gray-900">
                      {form.discountPrice
                        ? `₹${form.discountPrice}`
                        : "No discount"}
                    </p>
                  </div>
                  <div>
                    <span className="text-gray-600">Sections:</span>
                    <p className="font-medium text-gray-900">
                      {form.courseStructure.sections.length}
                    </p>
                  </div>
                  <div>
                    <span className="text-gray-600">Total Lectures:</span>
                    <p className="font-medium text-gray-900">
                      {form.courseStructure.sections.reduce(
                        (total, section) => total + section.lectures.length,
                        0,
                      )}
                    </p>
                  </div>
                </div>
              </Card>

              {/* Publishing Options */}
              <Card className="p-6">
                <h3 className="text-lg font-medium text-gray-900 mb-4">
                  Course Publishing
                </h3>
                <p className="text-gray-600">
                  You're ready to publish your course! Use the buttons below to
                  either save as draft or publish immediately.
                </p>
              </Card>
            </div>
          )}

          {/* Navigation */}
          <div className="flex items-center justify-between mt-8 pt-6 border-t border-gray-200">
            <div>
              {currentStep > 1 && (
                <Button
                  type="button"
                  variant="outline"
                  onClick={prevStep}
                  className="border-gray-300 text-gray-700 hover:bg-gray-50"
                >
                  Previous
                </Button>
              )}
            </div>

            <div className="flex space-x-3">
              {/* Save Draft - Available on all steps */}
              {currentStep < 4 && (
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => createOrUpdateCourse(false)}
                  disabled={isSubmitting}
                  className="border-orange-300 text-orange-600 hover:bg-orange-50"
                >
                  <Save className="h-4 w-4 mr-2" />
                  Save Draft
                </Button>
              )}

              {currentStep < 4 ? (
                <Button
                  type="button"
                  onClick={nextStep}
                  disabled={isAutoSaving}
                  className="bg-orange-600 hover:bg-orange-700 text-white disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isAutoSaving ? (
                    <>
                      <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                      Auto-saving...
                    </>
                  ) : (
                    "Next Step"
                  )}
                </Button>
              ) : (
                <>
                  <Button
                    type="button"
                    variant="outline"
                    disabled={isSubmitting || !courseId}
                    onClick={() =>
                      courseId && window.open(`/courses/${courseId}`, "_blank")
                    }
                    title={
                      courseId
                        ? "Preview course"
                        : "Save the course first to preview it"
                    }
                    className="border-gray-300 text-gray-700 hover:bg-gray-50"
                  >
                    <Eye className="h-4 w-4 mr-2" />
                    Preview
                  </Button>
                  <Button
                    type="button"
                    variant="outline"
                    onClick={() => createOrUpdateCourse(false)}
                    disabled={isSubmitting}
                    className="border-orange-300 text-orange-600 hover:bg-orange-50"
                  >
                    <Save className="h-4 w-4 mr-2" />
                    Save Draft
                  </Button>
                  <Button
                    type="button"
                    onClick={handlePublish}
                    disabled={isSubmitting}
                    className="bg-orange-600 hover:bg-orange-700 text-white"
                  >
                    {isSubmitting ? "Publishing..." : "Publish Course"}
                  </Button>
                </>
              )}
            </div>
          </div>
        </form>
      </PageLayout>
    </div>
  );
}
