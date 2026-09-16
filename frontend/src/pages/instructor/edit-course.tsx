import { CourseLinkField } from "@/components/course/CourseLinkField";
import { AstraSymbol } from "@/components/design-system/AstraSymbol";
import { PageLayout, PageHeader } from "@/components/design-system/PageLayout";
import React, { useState, useEffect } from "react";
import { confirmDialog } from "@/components/ui/confirm";
import {
  Link,
  useParams,
  useNavigate,
  useSearchParams,
} from "react-router-dom";
import {
  ArrowLeft,
  Plus,
  Minus,
  Trash2,
  Save,
  Eye,
  Video,
  FileText,
  HelpCircle,
  PenTool,
  ChevronDown,
  ChevronRight,
  Clock,
  GripVertical,
  Link as LinkIcon,
} from "lucide-react";
import {
  DndContext,
  closestCenter,
  PointerSensor,
  useSensor,
  useSensors,
  type DragEndEvent,
} from "@dnd-kit/core";
import {
  SortableContext,
  verticalListSortingStrategy,
  arrayMove,
  useSortable,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { SortableLecture } from "@/components/SortableLecture";
import { TagsEditor } from "@/components/course/TagsEditor";
import { StudioFace } from "@/components/studio/StudioFace";
import { TierPreview } from "@/components/studio/TierPreview";
import { ThreeDTeachingKit } from "@/components/three-d/ThreeDTeachingKit";
import LessonStruggleMap from "@/components/signals/LessonStruggleMap";
import { GuardianVisibility } from "@/components/studio/GuardianVisibility";
import { RewardDesigner } from "@/components/studio/RewardDesigner";
import { studioAPI, type StudioSettings } from "@/api/studio";
import { QuizCsvImport } from "@/components/assessment/QuizCsvImport";
import { CollaboratorsBlock } from "@/components/course/CollaboratorsBlock";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { toast } from "react-hot-toast";
import { ImageUpload } from "@/components/upload/image-upload";
import { VideoUpload } from "@/components/upload/video-upload";
import { H5PPicker } from "@/components/h5p/H5PPicker";
import { GamePicker } from "@/components/games/GamePicker";
import { GeoGebraAuthorCard } from "@/components/geogebra/GeoGebraAuthorCard";
import { ThreeDModelPicker } from "@/components/three-d/ThreeDModelPicker";
import { VirtualLabPicker } from "@/components/labs/VirtualLabPicker";
import { lessonContentSyncPayload } from "@/lib/lessonContentSync";
import { useAuthStore } from "@/store/auth";
import { useCallback, useRef } from "react";
import { api } from "@/api/axios";
import { COURSE_TYPES } from "@/config/courseTypes";
import { listDesignerTemplates } from "@/api/certificateDesigner";
import type { DesignerTemplate } from "@/lib/certificateDesignerTypes";
import {
  canUseDesignerTemplates,
  mergeTemplateLists,
  type PickerTemplate,
} from "@/lib/certificateTemplatePicker";

// Drag wrapper for a whole curriculum section block. Renders its own handle
// (absolute, on the block's left edge) so the header's click-to-collapse
// behaviour is untouched; children are the section card as-is.
function SortableSection({
  id,
  children,
}: {
  id: string;
  children: React.ReactNode;
}) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id });
  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
    zIndex: isDragging ? 999 : "auto",
  } as React.CSSProperties;
  return (
    <div ref={setNodeRef} style={style} className="relative">
      <button
        type="button"
        {...attributes}
        {...listeners}
        aria-label="Drag to reorder section"
        title="Drag to reorder section"
        className="absolute left-0 top-1/2 -translate-y-1/2 z-10 p-1 text-gray-400 hover:text-blue-600 cursor-grab active:cursor-grabbing bg-white/70 rounded"
        style={{ touchAction: "none" }}
        onClick={(e) => e.stopPropagation()}
      >
        <GripVertical className="h-4 w-4" />
      </button>
      <div className="pl-5">{children}</div>
    </div>
  );
}

interface CourseData {
  slug?: string;
  id: number;
  title: string;
  description: string;
  shortDescription: string;
  category: string;
  course_type: string;
  level: string;
  language: string;
  price: number;
  discountPrice?: number;
  thumbnail: string;
  introVideo?: string;
  status: "published" | "draft" | "pending";
  tags: string[];
  requirements: string[];
  learningObjectives: string[];
  targetAudience?: string;
  sections: Section[];
  numOfflineWorkshops?: number;
  numHours?: number;
  institution?: string;
  certificateId?: string;
  createdAt: string;
  updatedAt: string;
}

/**
 * The backend stores post_status as "publish"/"published"/"pending"/"draft"
 * (both publish spellings exist across import and admin paths). The UI only
 * knows published/pending/draft, so a raw "publish" fell through to the "draft"
 * branch and the badge showed the wrong state. Normalize once on load.
 */
const normalizeCourseStatus = (raw?: string): CourseData["status"] => {
  switch ((raw || "").toLowerCase()) {
    case "publish":
    case "published":
      return "published";
    case "pending":
      return "pending";
    default:
      return "draft";
  }
};

interface Section {
  id: string;
  title: string;
  description: string;
  lectures: Lecture[];
}

interface Lecture {
  description?: string;
  sourceType?: "lesson" | "quiz" | "assignment";
  sourceId?: string;
  id: string;
  title: string;
  type: "video" | "text" | "quiz" | "assignment";
  duration: string;
  content: string;
  videoUrl?: string;
  youtubeUrl?: string;
  videoDuration?: number;
  resources?: Resource[];
  isPublished: boolean;
  // H5P interactive-content support (spec B5/B7, plan Task 5). Only
  // meaningful when `type === 'video'` — a lesson's content_type sub-toggle
  // between the plain VideoPlayer path ("video", default), the sandboxed
  // H5P player ("h5p"), and the native learning-game player ("game").
  // `h5pContentId` is the H5PContent integer PK (matches the backend's
  // h5p_content_id lesson field); `gameId` is the Game integer PK
  // (matches the backend's game_id lesson field).
  contentType?:
    | "video"
    | "h5p"
    | "game"
    | "geogebra"
    | "three_d"
    | "virtual_lab";
  h5pContentId?: number | null;
  gameId?: number | null;
  threeDModelId?: number | null;
  virtualLabSim?: string | null;
  geogebraAppletId?: number | null;
}

interface Resource {
  id: string;
  title: string;
  type: "pdf" | "doc" | "link" | "zip";
  url: string;
  size?: string;
}

export function EditCourse() {
  const [curating, setCurating] = React.useState(false);
  const curateStudyGuide = async () => {
    if (!course?.id) return;
    setCurating(true);
    try {
      const r = await api.post(`/ai/curate-lesson/${course.id}`);
      toast.success(
        `Study guide drafted (${r.data.notes} notes, ${r.data.flashcards} flashcards) — review in lessons`,
      );
      window.location.reload();
    } catch (e: unknown) {
      const detail = (e as { response?: { data?: { detail?: string } } })
        ?.response?.data?.detail;
      toast.error(typeof detail === "string" ? detail : "Curation failed");
    } finally {
      setCurating(false);
    }
  };

  const { id } = useParams();
  const navigate = useNavigate();
  const { user } = useAuthStore();
  const isAdmin = user?.role === "admin";
  const accessToken = useAuthStore((state) => state.accessToken);
  const [course, setCourseState] = useState<CourseData | null>(null);
  const setCourse = useCallback(
    (
      update: CourseData | null | ((previous: CourseData) => CourseData | null),
    ) => {
      setCourseState((previous) =>
        typeof update === "function"
          ? previous
            ? update(previous)
            : null
          : update,
      );
    },
    [],
  );
  // v2.0 §4 (WP6): the draft-first start form lands here with ?tab=curriculum&face=1
  // so the type-specific Studio face opens first.
  const [searchParams] = useSearchParams();
  const [activeTab, setActiveTab] = useState(() => {
    const t = searchParams.get("tab");
    return t && ["basic", "content", "curriculum", "settings"].includes(t)
      ? t
      : "basic";
  });
  const forceFace = searchParams.get("face") === "1";
  const [studioSettings, setStudioSettings] = useState<StudioSettings | null>(
    null,
  );
  const [isLoading, setIsLoading] = useState(true);
  const [certTemplates, setCertTemplates] = React.useState<any[]>([]);
  const [previewTemplate, setPreviewTemplate] = React.useState<any | null>(
    null,
  );
  const [colleges, setColleges] = React.useState<any[]>([]);
  const [savingLessons, setSavingLessons] = useState<Set<string>>(new Set());
  const [expandedSections, setExpandedSections] = useState<Set<string>>(
    new Set(),
  );
  const [, setSectionsDirty] = useState(false);
  // Blocks a second "Add" while the first lesson POST is still in flight —
  // the backend appends without dedupe, so a double click created two lessons.
  const [addingLecture, setAddingLecture] = useState(false);
  const [expandedLectures, setExpandedLectures] = useState<Set<string>>(
    new Set(),
  );

  useEffect(() => {
    if (!id || activeTab !== "settings" || studioSettings) return;
    studioAPI
      .settings(Number(id))
      .then(setStudioSettings)
      .catch(() => {});
  }, [id, activeTab, studioSettings]);

  // Debounce timers for text updates
  const updateTimerRef = useRef<{ [key: string]: NodeJS.Timeout }>({});

  // Debounce helper
  const debounce = useCallback(
    (key: string, callback: () => void, delay: number = 1000) => {
      if (updateTimerRef.current[key]) {
        clearTimeout(updateTimerRef.current[key]);
      }
      updateTimerRef.current[key] = setTimeout(callback, delay);
    },
    [],
  );

  useEffect(() => {
    // Fetch certificate templates. Review finding I2: the public
    // /templates/list endpoint is anonymous and therefore only exposes legacy
    // (slug) + global rows, so an instructor's OWN designer templates would
    // be unreachable from the course editor. Instructors/admins additionally
    // pull /certificates/designer/ and the lists are merged (deduped by id;
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

    // Fetch colleges for institution dropdown
    api
      .get("/cohorts/colleges")
      .then((res) => {
        setColleges(res.data || []);
      })
      .catch(() => {});

    return () => {
      cancelled = true;
    };
  }, [user?.role]);

  useEffect(() => {
    const fetchCourse = async () => {
      if (!id) return;

      try {
        setIsLoading(true);

        const response = await api.get(`/courses/${id}`);
        const data = response.data;

        // Transform lessons into sections/lectures structure
        const sections: Section[] = [];
        const allLectures: any[] = [];

        // Add lessons
        if (data.lessons && data.lessons.length > 0) {
          allLectures.push(
            ...data.lessons.map((lesson: any) => {
              const hasVideo = !!(lesson.lesson_video || lesson.video_url);
              const hasYoutube = !!lesson.youtube_url;
              // Infer type based on content. If it has a youtube URL or video URL, consider it a video. Otherwise, consider it text.
              // Interactive content types live inside a 'video'-type lecture (that is the
              // container whose content selector shows the H5P/game/GeoGebra/3D/lab
              // pickers), so such lessons must never load as 'text'.
              const INTERACTIVE = [
                "h5p",
                "game",
                "geogebra",
                "three_d",
                "virtual_lab",
              ];
              const isInteractive = INTERACTIVE.includes(
                lesson.lesson_content_type,
              );
              const inferredType =
                isInteractive || hasVideo || hasYoutube ? "video" : "text";

              return {
                id: `lesson-${lesson.id}`,
                title: lesson.title || lesson.lesson_title,
                type: inferredType as any,
                duration: lesson.duration
                  ? lesson.duration.toString()
                  : lesson.video_duration || "0",
                content: lesson.lesson_content || lesson.content || "",
                videoUrl: lesson.lesson_video || lesson.video_url || "",
                youtubeUrl: lesson.youtube_url || "",
                resources: [],
                isPublished:
                  lesson.post_status === "publish" ||
                  lesson.post_status === "published" ||
                  lesson.is_preview,
                sourceType: "lesson",
                sourceId: lesson.id.toString(),
                createdAt: lesson.created_at || lesson.post_date,
                contentType: isInteractive
                  ? lesson.lesson_content_type
                  : "video",
                h5pContentId: lesson.h5p_content_id ?? null,
                gameId: lesson.game_id ?? null,
                geogebraAppletId: lesson.geogebra_applet_id ?? null,
                threeDModelId: lesson.three_d_model_id ?? null,
                virtualLabSim: lesson.virtual_lab_sim ?? null,
              };
            }),
          );
        }

        // Add quizzes
        if (data.quizzes && data.quizzes.length > 0) {
          allLectures.push(
            ...data.quizzes.map((quiz: any) => ({
              id: `quiz-${quiz.id}`,
              title: quiz.title,
              type: "quiz" as const,
              duration: quiz.time_limit ? `${quiz.time_limit}` : "30",
              content: `Quiz with ${quiz.questions_count} question(s)`,
              videoUrl: "",
              resources: [],
              isPublished: true,
              sourceType: "quiz",
              sourceId: quiz.id.toString(),
              questionsCount: quiz.questions_count,
              createdAt: quiz.created_at,
            })),
          );
        }

        // Add assignments
        if (data.assignments && data.assignments.length > 0) {
          allLectures.push(
            ...data.assignments.map((assignment: any) => ({
              id: `assignment-${assignment.id}`,
              title: assignment.title,
              type: "assignment" as const,
              duration: "0",
              content: assignment.description || "",
              videoUrl: "",
              resources: [],
              isPublished: true,
              sourceType: "assignment",
              sourceId: assignment.id.toString(),
              createdAt: assignment.created_at,
            })),
          );
        }

        // Restore sections from saved sections_meta (preserves user-defined order)
        const savedMeta = data.sections_meta || data.course_sections_meta;
        if (savedMeta) {
          try {
            const savedSections = JSON.parse(savedMeta);
            const lectureMap = new Map(allLectures.map((l: any) => [l.id, l]));
            savedSections.forEach((s: any) => {
              const sectionLectures = (s.lectureIds || [])
                .map((lid: string) => lectureMap.get(lid))
                .filter(Boolean);
              sections.push({
                id: s.id,
                title: s.title || "Section",
                description: s.description || "",
                lectures: sectionLectures,
              });
            });
            const assignedIds = new Set(
              savedSections.flatMap((s: any) => s.lectureIds || []),
            );
            const orphans = allLectures.filter(
              (l: any) => !assignedIds.has(l.id),
            );
            if (orphans.length > 0 && sections.length > 0) {
              sections[0].lectures = [...sections[0].lectures, ...orphans];
            }
          } catch (e) {
            sections.push({
              id: "section-1",
              title: "Course Content",
              description: "",
              lectures: allLectures,
            });
          }
        } else if (allLectures.length > 0) {
          sections.push({
            id: "section-1",
            title: "Course Content",
            description: "",
            lectures: allLectures,
          });
        }
        // Transform API data to CourseData format
        const transformedCourse: CourseData = {
          id: data.id,
          title: data.title,
          slug: data.slug || "",
          description: data.content,
          shortDescription: data.excerpt,
          category: data.category,
          course_type: data.course_type || "",
          level: data.level,
          language: data.language || "English",
          price: data.price,
          discountPrice: data.sale_price || 0,
          thumbnail: data.thumbnail,
          introVideo: data.intro_video || "",
          status: normalizeCourseStatus(data.status),
          tags: Array.isArray(data.tags) ? data.tags : [],
          requirements: Array.isArray(data.requirements)
            ? data.requirements
            : [],
          learningObjectives: Array.isArray(data.benefits) ? data.benefits : [],
          targetAudience:
            data.course_target_audience || data.target_audience || "",
          sections: sections,
          numOfflineWorkshops: data.num_offline_workshops || 0,
          numHours: data.num_hours || 0,
          institution: data.institution || "",
          certificateId:
            (data.certificate_id ?? data.certificate_template)
              ? String(data.certificate_id ?? data.certificate_template)
              : "",
          createdAt: data.created_at,
          updatedAt: data.updated_at,
        };

        setCourse(transformedCourse);
      } catch (error) {
        console.error("Error fetching course:", error);
        toast.error("Failed to load course data");
      } finally {
        setIsLoading(false);
      }
    };

    fetchCourse();
  }, [id, setCourse]);

  const handleInputChange = (
    e: React.ChangeEvent<
      HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement
    >,
  ) => {
    const { name, value } = e.target;
    // Convert numeric fields
    const finalValue =
      name === "numOfflineWorkshops" || name === "numHours"
        ? parseInt(value)
        : value;
    setCourse((prev) => ({ ...prev, [name]: finalValue }));
  };

  const addSection = () => {
    const newSection: Section = {
      id: Date.now().toString(),
      title: "",
      description: "",
      lectures: [],
    };
    setCourse((prev) => ({
      ...prev,
      sections: [...prev.sections, newSection],
    }));
  };

  const updateSection = (sectionId: string, field: string, value: string) => {
    setCourse((prev) => ({
      ...prev,
      sections: prev.sections.map((section) =>
        section.id === sectionId ? { ...section, [field]: value } : section,
      ),
    }));
    // Mark section as dirty so save button knows to persist
    setSectionsDirty(true);
  };

  const removeSection = (sectionId: string) => {
    setCourse((prev) => ({
      ...prev,
      sections: prev.sections.filter((section) => section.id !== sectionId),
    }));
  };

  const addLecture = async (sectionId: string) => {
    if (!course || !accessToken) {
      toast.error("Please login to add lessons");
      return;
    }
    if (addingLecture) return;
    setAddingLecture(true);

    try {
      // Create lesson via API
      const response = await api.post(`/courses/${course.id}/lessons`, {
        title: "New Lesson",
        content: "",
        video_url: "",
        video_duration: 0,
        is_preview: false,
      });

      if (response.status !== 200 && response.status !== 201) {
        throw new Error("Failed to create lesson");
      }

      const newLesson = response.data;

      // Add to UI
      const newLecture: Lecture = {
        id: newLesson.id.toString(),
        title: newLesson.title,
        type: "text",
        duration: newLesson.video_duration || "",
        content: newLesson.content || "",
        videoUrl: newLesson.video_url || "",
        resources: [],
        isPublished: true,
      };
      setCourse((prev) => {
        const updated = {
          ...prev,
          sections: prev.sections.map((section) =>
            section.id === sectionId
              ? { ...section, lectures: [...section.lectures, newLecture] }
              : section,
          ),
        };
        const secMeta = updated.sections.map((s: any, idx: number) => ({
          id: s.id,
          title: s.title,
          description: s.description || "",
          order: idx,
          lectureIds: s.lectures.map((l: any) => {
            const lid = l.id.toString();
            return lid.startsWith("lesson-") ||
              lid.startsWith("quiz-") ||
              lid.startsWith("assignment-")
              ? lid
              : "lesson-" + lid;
          }),
        }));
        api
          .put(`/courses/${prev.id}`, {
            sections_meta: JSON.stringify(secMeta),
          })
          .catch(() => {});
        return updated;
      });
      toast.success("Lesson created successfully");
    } catch (error: any) {
      console.error("Error creating lesson:", error);
      toast.error(error?.response?.data?.detail || "Failed to create lesson");
    } finally {
      setAddingLecture(false);
    }
  };

  const updateLecture = async (
    sectionId: string,
    lectureId: string,
    field: string,
    value: any,
    skipDebounce: boolean = false,
  ) => {
    if (!course || !accessToken) {
      toast.error("Please login to update lesson");
      return;
    }

    // First update local state for immediate UI feedback
    setCourse((prev) => ({
      ...prev,
      sections: prev.sections.map((section) =>
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
    }));

    // Prepare the API call
    const performUpdate = async () => {
      // Mark lesson as saving
      setSavingLessons((prev) => new Set(prev).add(lectureId));

      try {
        // Prepare update data based on field
        const updateData: any = {};

        // Extract the real ID from the composite key
        const realId = lectureId.replace(/^(lesson|quiz|assignment)-/, "");

        // Quiz rows share the lecture list, but their "duration" is the quiz
        // time limit — sending it to the lessons endpoint 404s (quiz ids
        // live in a different table), which is why duration edits on quiz
        // rows silently failed.
        if (lectureId.startsWith("quiz-")) {
          if (field === "duration") {
            await api.put(`/courses/${course.id}/quizzes/${realId}`, {
              timeLimit: parseInt(value as string) || 0,
            });
          }
          setSavingLessons((prev) => {
            const next = new Set(prev);
            next.delete(lectureId);
            return next;
          });
          return;
        }

        // Assignments have no duration in the backend; a lesson PATCH with
        // an assignment id 404s (same cross-table id trap as quizzes).
        // Their settings are managed in the assignment builder.
        if (lectureId.startsWith("assignment-")) {
          setSavingLessons((prev) => {
            const next = new Set(prev);
            next.delete(lectureId);
            return next;
          });
          return;
        }

        if (field === "title") updateData.title = value as string;
        else if (field === "content") updateData.content = value as string;
        else if (field === "videoUrl") updateData.video_url = value as string;
        else if (field === "youtubeUrl")
          updateData.youtube_url = value as string;
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
          // a 400 (which the catch below would answer with a full page
          // reload). Only the flip back to video syncs alone here (the
          // server clears both FKs); 'h5p'/'game' sync together with their
          // id once content is actually picked. See lessonContentSync.ts.
          Object.assign(
            updateData,
            lessonContentSyncPayload(field, value as any),
          );
        } else if (field === "duration") {
          // Convert duration string to seconds if needed
          const duration = value as string;
          updateData.video_duration = duration ? parseInt(duration) || 0 : 0;
        } else if (field === "isPublished")
          updateData.is_preview = value as boolean;
        else if (field === "type") {
          // Type changes don't need backend update for now
          setSavingLessons((prev) => {
            const next = new Set(prev);
            next.delete(lectureId);
            return next;
          });
          return;
        }

        // Fields that intentionally don't sync (e.g. contentType='h5p' before
        // a package is picked) leave updateData empty — skip the round-trip.
        if (Object.keys(updateData).length === 0) return;

        const response = await api.patch(
          `/courses/${course.id}/lessons/${realId}`,
          updateData,
        );

        if (response.status !== 200) {
          throw new Error(response.data?.detail || "Failed to update lesson");
        }

        // Don't show success toast for every field change (too noisy)
        if (field === "videoUrl") {
          toast.success("Video updated successfully");
        }
      } catch (error: any) {
        console.error("Error updating lesson:", error);
        toast.error(error.message || "Failed to update lesson");

        // Revert local state on error
        window.location.reload();
      } finally {
        // Remove from saving state
        setSavingLessons((prev) => {
          const next = new Set(prev);
          next.delete(lectureId);
          return next;
        });
      }
    };

    // Debounce text field updates, but immediately update videos and toggles
    const shouldDebounce =
      (field === "title" || field === "content") && !skipDebounce;

    if (shouldDebounce) {
      debounce(`lesson-${lectureId}-${field}`, performUpdate, 1500);
    } else {
      await performUpdate();
    }
  };

  const moveLecture = (
    sectionId: string,
    lectureId: string,
    direction: "up" | "down",
  ) => {
    setCourse((prev) => ({
      ...prev,
      sections: prev.sections.map((section) => {
        if (section.id !== sectionId) return section;
        const idx = section.lectures.findIndex((l) => l.id === lectureId);
        if (idx === -1) return section;
        const lectures = [...section.lectures];
        if (direction === "up" && idx > 0) {
          [lectures[idx - 1], lectures[idx]] = [
            lectures[idx],
            lectures[idx - 1],
          ];
        } else if (direction === "down" && idx < lectures.length - 1) {
          [lectures[idx], lectures[idx + 1]] = [
            lectures[idx + 1],
            lectures[idx],
          ];
        }
        return { ...section, lectures };
      }),
    }));
  };

  // Drag-to-reorder lectures within a section. 6px activation distance so
  // plain clicks (expand/collapse, buttons) never start a drag; the save path
  // already persists array index as `order`, so reordering the state array
  // is the whole job. The old up/down arrow buttons stay as an alternative.
  const lectureDragSensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 6 } }),
  );

  const onLectureDragEnd = (sectionId: string, event: DragEndEvent) => {
    const { active, over } = event;
    if (!over || active.id === over.id) return;
    setCourse((prev) => ({
      ...prev,
      sections: prev.sections.map((section) => {
        if (section.id !== sectionId) return section;
        const oldIndex = section.lectures.findIndex((l) => l.id === active.id);
        const newIndex = section.lectures.findIndex((l) => l.id === over.id);
        if (oldIndex === -1 || newIndex === -1) return section;
        return {
          ...section,
          lectures: arrayMove(section.lectures, oldIndex, newIndex),
        };
      }),
    }));
  };

  // Drag whole sections (HTML / CSS / JS modules…) to reorder the curriculum.
  // Same state pattern as lectures: the save path persists array index as the
  // section's `order`, so reordering + Save is the entire job.
  const onSectionDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    if (!over || active.id === over.id) return;
    setCourse((prev) => ({
      ...prev,
      sections: arrayMove(
        prev.sections,
        prev.sections.findIndex((s) => s.id === active.id),
        prev.sections.findIndex((s) => s.id === over.id),
      ),
    }));
  };

  const removeLecture = async (sectionId: string, lectureId: string) => {
    if (!course || !accessToken) {
      toast.error("Please login to delete lesson");
      return;
    }

    // Show confirmation dialog
    if (
      !(await confirmDialog(
        "Are you sure you want to delete this lesson? This action cannot be undone.",
      ))
    ) {
      return;
    }

    // Optimistically remove from UI
    const previousSections = course.sections;
    setCourse((prev) => ({
      ...prev,
      sections: prev.sections.map((section) =>
        section.id === sectionId
          ? {
              ...section,
              lectures: section.lectures.filter(
                (lecture) => lecture.id !== lectureId,
              ),
            }
          : section,
      ),
    }));

    try {
      // Extract the real ID and route to correct endpoint based on type
      const realId = lectureId.replace(/^(lesson|quiz|assignment)-/, "");
      let response;
      if (lectureId.startsWith("quiz-")) {
        response = await api.delete(`/courses/${course.id}/quizzes/${realId}`);
      } else if (lectureId.startsWith("assignment-")) {
        response = await api.delete(
          `/courses/${course.id}/assignments/${realId}`,
        );
      } else {
        response = await api.delete(`/courses/${course.id}/lessons/${realId}`);
      }
      if (response.status !== 200 && response.status !== 204) {
        throw new Error("Failed to delete");
      }
      toast.success("Deleted successfully");
    } catch (error: any) {
      console.error("Error deleting lesson:", error);
      toast.error("Failed to delete lesson");

      // Rollback on error
      setCourse((prev) => ({
        ...prev,
        sections: previousSections,
      }));
    }
  };

  const handleConfigureQuiz = async (sectionId: string, lecture: Lecture) => {
    if (!course) return;
    // If quiz already exists, navigate directly
    if ((lecture as any).sourceType === "quiz" && (lecture as any).sourceId) {
      navigate(
        `/${isAdmin ? "admin" : "instructor"}/courses/${course.id}/quiz-builder/${(lecture as any).sourceId}?sectionId=${sectionId}`,
      );
      return;
    }

    // Create new quiz first
    if (!course || !accessToken) {
      toast.error("Please login to configure quiz");
      return;
    }

    try {
      const response = await api.post(`/courses/${course.id}/quizzes`, {
        title: lecture.title || "Untitled Quiz",
        description: lecture.content || "",
        timeLimit: parseInt(lecture.duration) || 30,
        passingScore: 70,
        maxAttempts: 0,
        randomizeQuestions: false,
        questions: [],
      });

      if (response.status !== 200 && response.status !== 201) {
        throw new Error("Failed to create quiz");
      }

      const newQuiz = response.data;

      // Update lecture to have quiz sourceType and sourceId
      setCourse((prev) => ({
        ...prev,
        sections: prev.sections.map((section) =>
          section.id === sectionId
            ? {
                ...section,
                lectures: section.lectures.map((l) =>
                  l.id === lecture.id
                    ? {
                        ...l,
                        sourceType: "quiz" as const,
                        sourceId:
                          newQuiz.id?.toString() || newQuiz.quiz_id?.toString(),
                      }
                    : l,
                ),
              }
            : section,
        ),
      }));

      // Navigate to quiz builder
      const quizId = newQuiz.id || newQuiz.quiz_id;
      navigate(
        `/${isAdmin ? "admin" : "instructor"}/courses/${course.id}/quiz-builder/${quizId}?sectionId=${sectionId}`,
      );
      toast.success("Quiz created successfully");
    } catch (error: any) {
      console.error("Error creating quiz:", error);
      toast.error("Failed to create quiz");
    }
  };

  const handleConfigureAssignment = async (
    sectionId: string,
    lecture: Lecture,
  ) => {
    if (!course) return;
    // If assignment already exists, navigate directly
    if (
      (lecture as any).sourceType === "assignment" &&
      (lecture as any).sourceId
    ) {
      navigate(
        `/${isAdmin ? "admin" : "instructor"}/courses/${course.id}/assignment-builder/${(lecture as any).sourceId}?sectionId=${sectionId}`,
      );
      return;
    }

    // Create new assignment first
    if (!course || !accessToken) {
      toast.error("Please login to configure assignment");
      return;
    }

    try {
      const response = await api.post(`/courses/${course.id}/assignments`, {
        title: lecture.title || "Untitled Assignment",
        description: lecture.content || "",
        instructions: "",
        dueDate: "",
        totalPoints: 100,
        allowedFileTypes: [".pdf", ".doc", ".docx", ".zip"],
        maxFileSize: 10,
        maxFiles: 5,
        submissionType: "both",
        attachments: [],
      });

      if (response.status !== 200 && response.status !== 201) {
        throw new Error("Failed to create assignment");
      }

      const newAssignment = response.data;

      // Update lecture to have assignment sourceType and sourceId
      setCourse((prev) => ({
        ...prev,
        sections: prev.sections.map((section) =>
          section.id === sectionId
            ? {
                ...section,
                lectures: section.lectures.map((l) =>
                  l.id === lecture.id
                    ? {
                        ...l,
                        sourceType: "assignment" as const,
                        sourceId:
                          newAssignment.id?.toString() ||
                          newAssignment.assignment_id?.toString(),
                      }
                    : l,
                ),
              }
            : section,
        ),
      }));

      // Navigate to assignment builder
      const assignmentId = newAssignment.id || newAssignment.assignment_id;
      navigate(
        `/${isAdmin ? "admin" : "instructor"}/courses/${course.id}/assignment-builder/${assignmentId}?sectionId=${sectionId}`,
      );
      toast.success("Assignment created successfully");
    } catch (error: any) {
      console.error("Error creating assignment:", error);
      toast.error("Failed to create assignment");
    }
  };

  const moveSection = (sectionId: string, direction: "up" | "down") => {
    setCourse((prev) => {
      const idx = prev.sections.findIndex((s) => s.id === sectionId);
      if (idx === -1) return prev;
      const sections = [...prev.sections];
      if (direction === "up" && idx > 0) {
        [sections[idx - 1], sections[idx]] = [sections[idx], sections[idx - 1]];
      } else if (direction === "down" && idx < sections.length - 1) {
        [sections[idx], sections[idx + 1]] = [sections[idx + 1], sections[idx]];
      }
      return { ...prev, sections };
    });
  };

  const handleSave = async () => {
    if (!course) return false;

    try {
      setIsLoading(true);

      // Prepare update data
      const updateData = {
        sections_meta: "",
        title: course.title,
        slug: course.slug || undefined,
        description: course.description,
        content: course.description,
        excerpt: course.shortDescription,
        thumbnail: course.thumbnail,
        intro_video: course.introVideo || "",
        price: course.price,
        sale_price: parseFloat(course.discountPrice as any) || 0,
        level: course.level.toLowerCase(),
        category: course.category,
        course_type: course.course_type || "",
        language: course.language,
        requirements: course.requirements,
        benefits: course.learningObjectives,
        target_audience: course.targetAudience || "",
        tags: course.tags,
        certificate_id: course.certificateId || null,
        num_offline_workshops: parseInt(course.numOfflineWorkshops as any) || 0,
        num_hours: parseInt(course.numHours as any) || 0,
        institution: course.institution || "",
      };

      // Use api instance which handles authentication automatically
      updateData["sections_meta"] = JSON.stringify(
        course.sections.map((s: any, idx: number) => ({
          id: s.id,
          title: s.title,
          description: s.description,
          order: idx,
          lectureIds: s.lectures.map((l: any) =>
            l.id.startsWith("lesson-") ||
            l.id.startsWith("quiz-") ||
            l.id.startsWith("assignment-")
              ? l.id
              : "lesson-" + l.id,
          ),
        })),
      );
      await api.put(`/courses/${course.id}`, updateData);

      toast.success("Course updated successfully!");
      return true;
    } catch (error: any) {
      console.error("Error updating course:", error);
      toast.error(
        error.response?.data?.detail ||
          error.message ||
          "Failed to update course",
      );
      return false;
    } finally {
      setIsLoading(false);
    }
  };

  const handlePublish = async () => {
    if (!course) return;
    // Saving alone never changed post_status: the update payload doesn't carry
    // one, so the local 'published' flag was thrown away. Publishing goes
    // through the dedicated endpoint, which also applies the role rules
    // (admin → live, instructor → pending admin approval).
    if (!(await handleSave())) return;
    try {
      const res = await api.patch(`/courses/${course.id}/publish`);
      const newStatus = res.data?.status;
      setCourse((prev) => ({
        ...prev,
        status: normalizeCourseStatus(newStatus),
      }));
      toast.success(res.data?.message || "Course submitted");
      navigate(isAdmin ? "/admin/courses" : "/instructor/courses");
    } catch (error: any) {
      console.error("Error publishing course:", error);
      toast.error(error.response?.data?.detail || "Failed to publish course");
    }
  };

  const toggleSection = (sectionId: string) => {
    setExpandedSections((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(sectionId)) {
        newSet.delete(sectionId);
      } else {
        newSet.add(sectionId);
      }
      return newSet;
    });
  };

  const toggleLecture = (lectureId: string) => {
    setExpandedLectures((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(lectureId)) {
        newSet.delete(lectureId);
      } else {
        newSet.add(lectureId);
      }
      return newSet;
    });
  };

  const getLectureIcon = (type: string) => {
    switch (type) {
      case "video":
        return <Video className="h-4 w-4" />;
      case "text":
        return <FileText className="h-4 w-4" />;
      case "quiz":
        return <HelpCircle className="h-4 w-4" />;
      case "assignment":
        return <PenTool className="h-4 w-4" />;
      default:
        return <FileText className="h-4 w-4" />;
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading course data...</p>
        </div>
      </div>
    );
  }

  if (!course) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <h2 className="text-2xl font-bold text-gray-900 mb-2">
            Course not found
          </h2>
          <p className="text-gray-600 mb-4">
            The course you're trying to edit doesn't exist.
          </p>
          <Link
            to="/instructor/courses"
            className="text-blue-600 hover:underline"
          >
            Back to Courses
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <PageLayout
        header={
          <PageHeader>
            <div className="flex items-center">
              <Link
                to="/instructor/courses"
                className="flex items-center text-blue-600 hover:text-blue-700 mr-4"
              >
                <ArrowLeft className="h-4 w-4 mr-1" />
                Back to Courses
              </Link>
              <div>
                <h1 className="text-3xl font-bold text-gray-900">
                  Edit Course
                </h1>
                <p className="text-gray-600 mt-1">
                  Last updated:{" "}
                  {new Date(course.updatedAt).toLocaleDateString()}
                </p>
              </div>
            </div>
            <div className="flex items-center space-x-3">
              <Badge
                className={
                  course.status === "published"
                    ? "bg-green-600"
                    : "bg-yellow-600"
                }
              >
                {course.status.charAt(0).toUpperCase() + course.status.slice(1)}
              </Badge>
              <Button
                variant="outline"
                onClick={() => window.open(`/courses/${course.id}`, "_blank")}
              >
                <Eye className="h-4 w-4 mr-2" />
                Preview
              </Button>
              <Button
                variant="outline"
                onClick={() =>
                  navigate(`/instructor/courses/${course.id}/coverage`)
                }
                title="Concepts, outcome definition and the coverage gap report"
              >
                Coverage
              </Button>
              <Button onClick={handleSave} disabled={isLoading}>
                <Save className="h-4 w-4 mr-2" />
                {isLoading ? "Saving..." : "Save Changes"}
              </Button>
            </div>
          </PageHeader>
        }
        className="rd-screen rd-screen-instructor-edit-course"
      >
        <div className="mb-8">
          <div className="border-b border-gray-200">
            <nav className="-mb-px flex space-x-8">
              {[
                { id: "basic", label: "Basic Info" },
                { id: "content", label: "Content" },
                { id: "curriculum", label: "Curriculum" },
                { id: "settings", label: "Settings" },
              ].map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`py-2 px-1 border-b-2 font-medium text-sm ${
                    activeTab === tab.id
                      ? "border-blue-500 text-blue-600"
                      : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
                  }`}
                >
                  {tab.label}
                </button>
              ))}
            </nav>
          </div>
        </div>
        {activeTab === "basic" && (
          <Card className="p-6">
            <h2 className="text-xl font-semibold text-gray-900 mb-6">
              Basic Information
            </h2>
            <div className="space-y-6">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Course Title *
                </label>
                <input
                  type="text"
                  name="title"
                  value={course.title}
                  onChange={handleInputChange}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>

              <CourseLinkField
                value={course.slug || ""}
                courseId={course.id}
                onChange={(slug) => setCourse((prev) => ({ ...prev, slug }))}
              />
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Short Description *
                </label>
                <input
                  type="text"
                  name="shortDescription"
                  value={course.shortDescription}
                  onChange={handleInputChange}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Course Description *
                </label>
                <textarea
                  name="description"
                  value={course.description}
                  onChange={handleInputChange}
                  rows={6}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Course Type
                  </label>
                  <select
                    name="course_type"
                    value={course.course_type || ""}
                    onChange={handleInputChange}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-transparent"
                  >
                    <option value="">-- Select Type --</option>
                    {COURSE_TYPES.map((t) => (
                      <option key={t.value} value={t.value}>
                        {t.emoji} {t.label} — {t.tagline} ({t.tamil})
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Category
                  </label>
                  <input
                    type="text"
                    name="category"
                    value={course.category}
                    onChange={handleInputChange}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    placeholder="Type any category (free-form)"
                  />
                </div>
                <div className="md:col-span-3">
                  {/* v2.0 §3: free tags + suggestions derived from the course content */}
                  <TagsEditor
                    tags={course.tags || []}
                    onChange={(tags) =>
                      setCourse((prev) => ({ ...prev, tags }))
                    }
                    title={course.title}
                    description={course.description}
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Level
                  </label>
                  <select
                    name="level"
                    value={course.level}
                    onChange={handleInputChange}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  >
                    <option value="Beginner">Beginner</option>
                    <option value="Intermediate">Intermediate</option>
                    <option value="Advanced">Advanced</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Language
                  </label>
                  <select
                    name="language"
                    value={course.language}
                    onChange={handleInputChange}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  >
                    <option value="English">English</option>
                    <option value="Spanish">Spanish</option>
                    <option value="French">French</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Price (₹)
                  </label>
                  <input
                    type="number"
                    name="price"
                    value={course.price}
                    onChange={handleInputChange}
                    min="0"
                    step="0.01"
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Discount Price (₹)
                  </label>
                  <input
                    type="number"
                    name="discountPrice"
                    value={course.discountPrice || ""}
                    onChange={handleInputChange}
                    min="0"
                    step="0.01"
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  />
                </div>
              </div>

              <div>
                <ImageUpload
                  value={course.thumbnail}
                  onChange={(url) =>
                    setCourse((prev) => ({ ...prev, thumbnail: url }))
                  }
                  label="Course Thumbnail"
                  description="Upload a thumbnail image for your course (recommended: 1280x720px)"
                />
              </div>

              <div>
                <VideoUpload
                  value={course.introVideo}
                  onChange={(url) =>
                    setCourse((prev) => ({ ...prev, introVideo: url }))
                  }
                  label="Course Intro Video (Optional)"
                  description="Upload a promotional video for your course"
                />
              </div>
            </div>
          </Card>
        )}
        {activeTab === "content" && (
          <Card className="p-6">
            <h2 className="text-xl font-semibold text-gray-900 mb-6">
              Course Content
            </h2>
            <div className="space-y-6">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Course Description *
                </label>
                <textarea
                  value={course.description}
                  onChange={(e) =>
                    setCourse({ ...course, description: e.target.value })
                  }
                  rows={8}
                  className="w-full px-4 py-3 rounded-lg border border-gray-300 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="Describe what students will learn in this course..."
                />
                <p className="text-sm text-gray-500 mt-1">
                  Provide a comprehensive description of your course content and
                  learning objectives
                </p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  What You'll Learn
                </label>
                <div className="space-y-3">
                  {(course.learningObjectives || []).map((benefit, index) => (
                    <div key={index} className="flex gap-2">
                      <input
                        type="text"
                        value={benefit}
                        onChange={(e) => {
                          const newBenefits = [
                            ...(course.learningObjectives || []),
                          ];
                          newBenefits[index] = e.target.value;
                          setCourse({
                            ...course,
                            learningObjectives: newBenefits,
                          });
                        }}
                        className="flex-1 px-4 py-2 rounded-lg border border-gray-300 focus:ring-2 focus:ring-blue-500"
                        placeholder="Enter a learning outcome"
                      />
                      <Button
                        variant="outline"
                        onClick={() => {
                          const newBenefits = (
                            course.learningObjectives || []
                          ).filter((_, i) => i !== index);
                          setCourse({
                            ...course,
                            learningObjectives: newBenefits,
                          });
                        }}
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  ))}
                  <Button
                    variant="outline"
                    onClick={() => {
                      setCourse({
                        ...course,
                        learningObjectives: [
                          ...(course.learningObjectives || []),
                          "",
                        ],
                      });
                    }}
                  >
                    <Plus className="h-4 w-4 mr-2" />
                    Add Learning Outcome
                  </Button>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Requirements
                </label>
                <div className="space-y-3">
                  {(course.requirements || []).map((requirement, index) => (
                    <div key={index} className="flex gap-2">
                      <input
                        type="text"
                        value={requirement}
                        onChange={(e) => {
                          const newRequirements = [
                            ...(course.requirements || []),
                          ];
                          newRequirements[index] = e.target.value;
                          setCourse({
                            ...course,
                            requirements: newRequirements,
                          });
                        }}
                        className="flex-1 px-4 py-2 rounded-lg border border-gray-300 focus:ring-2 focus:ring-blue-500"
                        placeholder="Enter a requirement"
                      />
                      <Button
                        variant="outline"
                        onClick={() => {
                          const newRequirements = (
                            course.requirements || []
                          ).filter((_, i) => i !== index);
                          setCourse({
                            ...course,
                            requirements: newRequirements,
                          });
                        }}
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  ))}
                  <Button
                    variant="outline"
                    onClick={() => {
                      setCourse({
                        ...course,
                        requirements: [...(course.requirements || []), ""],
                      });
                    }}
                  >
                    <Plus className="h-4 w-4 mr-2" />
                    Add Requirement
                  </Button>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    No. of Offline Workshops
                  </label>
                  <select
                    name="numOfflineWorkshops"
                    value={course.numOfflineWorkshops || 0}
                    onChange={handleInputChange}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  >
                    {[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map((num) => (
                      <option key={num} value={num}>
                        {num}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    No. of Offline Hours
                  </label>
                  <div className="flex items-center">
                    <button
                      type="button"
                      onClick={() =>
                        setCourse((prev) => ({
                          ...prev,
                          numHours: Math.max(
                            0,
                            (parseInt(prev.numHours as any) || 0) - 1,
                          ),
                        }))
                      }
                      className="flex items-center justify-center w-10 h-[42px] border border-gray-300 rounded-l-lg bg-gray-50 hover:bg-gray-100 text-gray-700"
                      aria-label="Decrease hours"
                    >
                      <Minus className="h-4 w-4" />
                    </button>
                    <input
                      type="number"
                      name="numHours"
                      min={0}
                      value={course.numHours || 0}
                      onChange={handleInputChange}
                      className="w-full text-center px-3 py-2 border-t border-b border-gray-300 focus:ring-2 focus:ring-blue-500 focus:border-transparent [appearance:textfield] [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none"
                    />
                    <button
                      type="button"
                      onClick={() =>
                        setCourse((prev) => ({
                          ...prev,
                          numHours: (parseInt(prev.numHours as any) || 0) + 1,
                        }))
                      }
                      className="flex items-center justify-center w-10 h-[42px] border border-gray-300 rounded-r-lg bg-gray-50 hover:bg-gray-100 text-gray-700"
                      aria-label="Increase hours"
                    >
                      <Plus className="h-4 w-4" />
                    </button>
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    College
                  </label>
                  <select
                    name="institution"
                    value={course.institution || ""}
                    onChange={handleInputChange}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  >
                    <option value="">-- Select College --</option>
                    {colleges.map((college) => (
                      <option key={college.id} value={college.name}>
                        {college.name}
                      </option>
                    ))}
                    <option value="SashaInfinity">SashaInfinity</option>
                    <option value="Other">Other</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Target Audience
                </label>
                <textarea
                  value={course.targetAudience || ""}
                  onChange={(e) =>
                    setCourse({ ...course, targetAudience: e.target.value })
                  }
                  rows={4}
                  className="w-full px-4 py-3 rounded-lg border border-gray-300 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="Who is this course for?"
                />
              </div>
            </div>
          </Card>
        )}
        {activeTab === "curriculum" && (
          <Card className="p-6">
            {id && (
              <StudioFace
                courseId={Number(id)}
                courseType={course?.course_type || ""}
                forceOpen={forceFace}
              />
            )}
            <div className="flex items-center justify-between mb-6">
              <div>
                <h2 className="text-xl font-semibold text-gray-900">
                  Course Curriculum
                </h2>
                <p className="text-xs text-gray-500 mt-0.5">
                  Any lesson — video, text, 3D, lab or game — can be a{" "}
                  <span className="font-medium text-orange-700">
                    Public preview
                  </span>
                  : visitors open it from the course page before enrolling.
                  Everything else stays locked.
                </p>
              </div>
              <div className="flex items-center gap-2">
                {id && (
                  <QuizCsvImport
                    courseId={Number(id)}
                    onImported={() => window.location.reload()}
                  />
                )}
                <button
                  type="button"
                  onClick={curateStudyGuide}
                  disabled={curating}
                  className="px-3 py-1.5 text-sm rounded-lg border border-violet-300 text-violet-700 hover:bg-violet-50 disabled:opacity-40"
                >
                  ✨ {curating ? "Curating…" : "AI Study Guide"}
                </button>
                <Button onClick={addSection}>
                  <Plus className="h-4 w-4 mr-2" />
                  Add Section
                </Button>
              </div>
            </div>

            <div className="space-y-3">
              <DndContext
                sensors={lectureDragSensors}
                collisionDetection={closestCenter}
                onDragEnd={onSectionDragEnd}
              >
                <SortableContext
                  items={course.sections.map((s) => s.id)}
                  strategy={verticalListSortingStrategy}
                >
                  {course.sections.map((section, sectionIndex) => {
                    const isExpanded = expandedSections.has(section.id);
                    const totalDuration = section.lectures.reduce(
                      (sum, lecture) => {
                        const parts = (lecture.duration || "0").split(":");
                        const minutes = parseInt(parts[0] || "0");
                        const seconds = parseInt(parts[1] || "0");
                        return sum + minutes + seconds / 60;
                      },
                      0,
                    );

                    return (
                      <SortableSection key={section.id} id={section.id}>
                        <div
                          className="border border-gray-200 rounded-lg overflow-hidden bg-white"
                          data-glass="work"
                        >
                          {/* Section Header - Collapsible */}
                          <div
                            className="flex items-center justify-between p-4 bg-gradient-to-r from-blue-50 to-white hover:from-blue-100 hover:to-blue-50 cursor-pointer transition-colors"
                            onClick={() => toggleSection(section.id)}
                          >
                            <div className="flex items-center gap-3 flex-1">
                              <button className="text-gray-600 hover:text-gray-900">
                                {isExpanded ? (
                                  <ChevronDown className="h-5 w-5" />
                                ) : (
                                  <ChevronRight className="h-5 w-5" />
                                )}
                              </button>
                              <div className="flex-1">
                                <h3 className="text-base font-semibold text-gray-900">
                                  {section.title ||
                                    `Section ${sectionIndex + 1}`}
                                </h3>
                                <div className="flex items-center gap-4 mt-1 text-sm text-gray-600">
                                  <span>
                                    {section.lectures.length} lectures
                                  </span>
                                  <div className="flex items-center gap-1">
                                    <Clock className="h-3 w-3" />
                                    <span>{Math.floor(totalDuration)}min</span>
                                  </div>
                                </div>
                              </div>
                            </div>
                            <div
                              className="flex items-center gap-2"
                              onClick={(e) => e.stopPropagation()}
                            >
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={() => addLecture(section.id)}
                                className="text-xs"
                                disabled={addingLecture}
                              >
                                <Plus className="h-3 w-3 mr-1" />
                                {addingLecture ? "Adding…" : "Add"}
                              </Button>
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={() => moveSection(section.id, "up")}
                                className="text-xs"
                                title="Move up"
                              >
                                ↑
                              </Button>
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={() => moveSection(section.id, "down")}
                                className="text-xs"
                                title="Move down"
                              >
                                ↓
                              </Button>
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={() => removeSection(section.id)}
                                className="text-red-600 text-xs"
                              >
                                <Trash2 className="h-3 w-3" />
                              </Button>
                            </div>
                          </div>

                          {/* Section Content - Expandable */}
                          {isExpanded && (
                            <div className="border-t border-gray-200">
                              {/* Section Edit Fields */}
                              <div className="p-4 bg-gray-50 space-y-3">
                                <input
                                  type="text"
                                  value={section.title}
                                  onChange={(e) =>
                                    updateSection(
                                      section.id,
                                      "title",
                                      e.target.value,
                                    )
                                  }
                                  placeholder="Section title"
                                  className="w-full px-3 py-2 text-sm border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                  onClick={(e) => e.stopPropagation()}
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
                                  className="w-full px-3 py-2 text-sm border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                  onClick={(e) => e.stopPropagation()}
                                />
                              </div>

                              {/* Lectures */}
                              <div className="bg-white">
                                <div className="space-y-2 px-4 pb-4">
                                  <DndContext
                                    sensors={lectureDragSensors}
                                    collisionDetection={closestCenter}
                                    onDragEnd={(event) =>
                                      onLectureDragEnd(section.id, event)
                                    }
                                  >
                                    <SortableContext
                                      items={section.lectures.map((l) => l.id)}
                                      strategy={verticalListSortingStrategy}
                                    >
                                      {section.lectures.map(
                                        (lecture, lectureIndex) => {
                                          const isLectureExpanded =
                                            expandedLectures.has(lecture.id);

                                          return (
                                            <SortableLecture
                                              key={lecture.id}
                                              id={lecture.id}
                                            >
                                              <div className="border border-gray-200 rounded-lg overflow-hidden">
                                                {/* Lecture Header */}
                                                <div
                                                  className="flex items-center gap-3 p-3 bg-white hover:bg-gray-50 cursor-pointer transition-colors"
                                                  onClick={() =>
                                                    toggleLecture(lecture.id)
                                                  }
                                                >
                                                  <button className="text-gray-400">
                                                    {isLectureExpanded ? (
                                                      <ChevronDown className="h-4 w-4" />
                                                    ) : (
                                                      <ChevronRight className="h-4 w-4" />
                                                    )}
                                                  </button>
                                                  {getLectureIcon(lecture.type)}
                                                  <div className="flex-1">
                                                    <div className="flex items-center gap-2">
                                                      <span className="text-sm font-medium text-gray-900">
                                                        {lecture.title ||
                                                          `Lecture ${lectureIndex + 1}`}
                                                      </span>
                                                      <Badge
                                                        variant={
                                                          lecture.isPublished
                                                            ? "default"
                                                            : "secondary"
                                                        }
                                                        className={`text-xs ${lecture.isPublished ? "bg-orange-100 text-orange-800 hover:bg-orange-100" : "bg-gray-100 text-gray-600 hover:bg-gray-100"}`}
                                                        title={
                                                          lecture.isPublished
                                                            ? "Anyone can open this lesson from the course page before enrolling"
                                                            : "Only enrolled learners can open this lesson"
                                                        }
                                                      >
                                                        {lecture.isPublished
                                                          ? "Public preview"
                                                          : "Locked"}
                                                      </Badge>
                                                      {savingLessons.has(
                                                        lecture.id,
                                                      ) && (
                                                        <Badge className="bg-blue-500 text-xs">
                                                          Saving...
                                                        </Badge>
                                                      )}
                                                      {(lecture as any)
                                                        .sourceType ===
                                                        "quiz" && (
                                                        <Badge className="bg-purple-100 text-purple-700 text-xs">
                                                          {
                                                            (lecture as any)
                                                              .questionsCount
                                                          }{" "}
                                                          Q
                                                        </Badge>
                                                      )}
                                                      {lecture.type ===
                                                        "video" &&
                                                        lecture.contentType ===
                                                          "h5p" && (
                                                          <Badge className="bg-indigo-100 text-indigo-700 text-xs">
                                                            H5P
                                                          </Badge>
                                                        )}
                                                      {lecture.type ===
                                                        "video" &&
                                                        lecture.contentType ===
                                                          "game" && (
                                                          <Badge className="bg-emerald-100 text-emerald-700 text-xs">
                                                            Game
                                                          </Badge>
                                                        )}
                                                    </div>
                                                    <div className="flex items-center gap-2 mt-0.5 text-xs text-gray-500">
                                                      <Clock className="h-3 w-3" />
                                                      <span>
                                                        {lecture.duration ||
                                                          "0"}{" "}
                                                        min
                                                      </span>
                                                      <span className="text-gray-300">
                                                        •
                                                      </span>
                                                      <span className="capitalize">
                                                        {lecture.type}
                                                      </span>
                                                    </div>
                                                  </div>
                                                  <div
                                                    className="flex items-center gap-1"
                                                    onClick={(e) =>
                                                      e.stopPropagation()
                                                    }
                                                  >
                                                    <Button
                                                      variant="ghost"
                                                      size="sm"
                                                      onClick={() =>
                                                        updateLecture(
                                                          section.id,
                                                          lecture.id,
                                                          "isPublished",
                                                          !lecture.isPublished,
                                                        )
                                                      }
                                                      className="h-7 px-2 text-xs"
                                                      title={
                                                        lecture.isPublished
                                                          ? "Lock this lesson — only enrolled learners can open it"
                                                          : "Let anyone try this lesson before enrolling"
                                                      }
                                                    >
                                                      <Eye className="h-3 w-3 mr-1" />
                                                      {lecture.isPublished
                                                        ? "Lock again"
                                                        : "Make public preview"}
                                                    </Button>
                                                    <Button
                                                      variant="ghost"
                                                      size="sm"
                                                      onClick={() =>
                                                        moveLecture(
                                                          section.id,
                                                          lecture.id,
                                                          "up",
                                                        )
                                                      }
                                                      className="h-7 px-2 text-xs"
                                                      title="Move up"
                                                    >
                                                      ↑
                                                    </Button>
                                                    <Button
                                                      variant="ghost"
                                                      size="sm"
                                                      onClick={() =>
                                                        moveLecture(
                                                          section.id,
                                                          lecture.id,
                                                          "down",
                                                        )
                                                      }
                                                      className="h-7 px-2 text-xs"
                                                      title="Move down"
                                                    >
                                                      ↓
                                                    </Button>
                                                    <Button
                                                      variant="ghost"
                                                      size="sm"
                                                      onClick={() =>
                                                        removeLecture(
                                                          section.id,
                                                          lecture.id,
                                                        )
                                                      }
                                                      className="h-7 px-2 text-xs text-red-600 hover:text-red-700"
                                                    >
                                                      <Trash2 className="h-3 w-3" />
                                                    </Button>
                                                  </div>
                                                </div>

                                                {/* Lecture Edit Form - Expandable */}
                                                {isLectureExpanded && (
                                                  <div className="border-t border-gray-200 p-4 bg-gray-50 space-y-3">
                                                    <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
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
                                                        className="px-3 py-2 text-sm border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                                      />
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
                                                        className="px-3 py-2 text-sm border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                                      >
                                                        <option value="video">
                                                          Video
                                                        </option>
                                                        <option value="text">
                                                          Text
                                                        </option>
                                                        <option value="quiz">
                                                          Quiz
                                                        </option>
                                                        <option value="assignment">
                                                          Assignment
                                                        </option>
                                                      </select>
                                                      <input
                                                        type="text"
                                                        value={lecture.duration}
                                                        onChange={(e) =>
                                                          updateLecture(
                                                            section.id,
                                                            lecture.id,
                                                            "duration",
                                                            e.target.value,
                                                          )
                                                        }
                                                        placeholder="Duration (min)"
                                                        disabled={
                                                          lecture.type ===
                                                          "assignment"
                                                        }
                                                        title={
                                                          lecture.type ===
                                                          "assignment"
                                                            ? "Assignments have no duration — settings live in the assignment builder"
                                                            : undefined
                                                        }
                                                        className="px-3 py-2 text-sm border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-100 disabled:text-gray-400"
                                                      />
                                                    </div>

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
                                                      placeholder="Lecture description"
                                                      rows={2}
                                                      className="w-full px-3 py-2 text-sm border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                                    />

                                                    {/^(lesson-)?\d+$/.test(
                                                      String(lecture.id),
                                                    ) &&
                                                      lecture.type !== "quiz" &&
                                                      lecture.type !==
                                                        "assignment" && (
                                                        <LessonStruggleMap
                                                          lessonId={Number(
                                                            String(
                                                              lecture.id,
                                                            ).replace(
                                                              /^lesson-/,
                                                              "",
                                                            ),
                                                          )}
                                                        />
                                                      )}

                                                    {lecture.type ===
                                                      "video" && (
                                                      <div className="space-y-3">
                                                        {/* Content-type sub-toggle (spec B7, plan Task 5/9): a
                                              "video" lecture's actual player content can be a
                                              plain video, a sandboxed H5P interactive item, or a
                                              native learning game. */}
                                                        <div className="space-y-2">
                                                          <label className="block text-sm font-medium text-gray-700">
                                                            Content type
                                                          </label>
                                                          <select
                                                            value={
                                                              lecture.contentType ||
                                                              "video"
                                                            }
                                                            onChange={(e) => {
                                                              const nextType = e
                                                                .target
                                                                .value as
                                                                | "video"
                                                                | "h5p"
                                                                | "game"
                                                                | "geogebra"
                                                                | "three_d"
                                                                | "virtual_lab";
                                                              updateLecture(
                                                                section.id,
                                                                lecture.id,
                                                                "contentType",
                                                                nextType,
                                                              );
                                                              if (
                                                                nextType !==
                                                                "h5p"
                                                              )
                                                                updateLecture(
                                                                  section.id,
                                                                  lecture.id,
                                                                  "h5pContentId",
                                                                  null,
                                                                );
                                                              if (
                                                                nextType !==
                                                                "game"
                                                              )
                                                                updateLecture(
                                                                  section.id,
                                                                  lecture.id,
                                                                  "gameId",
                                                                  null,
                                                                );
                                                              if (
                                                                nextType !==
                                                                "geogebra"
                                                              )
                                                                updateLecture(
                                                                  section.id,
                                                                  lecture.id,
                                                                  "geogebraAppletId",
                                                                  null,
                                                                );
                                                              if (
                                                                nextType !==
                                                                "three_d"
                                                              )
                                                                updateLecture(
                                                                  section.id,
                                                                  lecture.id,
                                                                  "threeDModelId",
                                                                  null,
                                                                );
                                                              if (
                                                                nextType !==
                                                                "virtual_lab"
                                                              )
                                                                updateLecture(
                                                                  section.id,
                                                                  lecture.id,
                                                                  "virtualLabSim",
                                                                  null,
                                                                );
                                                            }}
                                                            className="px-3 py-2 text-sm border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                                          >
                                                            <option value="video">
                                                              Video
                                                            </option>
                                                            <option value="h5p">
                                                              H5P interactive
                                                            </option>
                                                            <option value="game">
                                                              Learning game
                                                            </option>
                                                            <option value="geogebra">
                                                              GeoGebra
                                                              interactive{" "}
                                                              <AstraSymbol value="📐" />
                                                            </option>
                                                            <option value="three_d">
                                                              <AstraSymbol value="🧊" />{" "}
                                                              3D Model (GLB)
                                                            </option>
                                                            <option value="virtual_lab">
                                                              <AstraSymbol value="🔬" />{" "}
                                                              Virtual Lab (PhET)
                                                            </option>
                                                          </select>
                                                        </div>

                                                        {lecture.contentType ===
                                                        "h5p" ? (
                                                          <H5PPicker
                                                            value={
                                                              lecture.h5pContentId ??
                                                              null
                                                            }
                                                            onChange={(
                                                              contentId,
                                                            ) =>
                                                              updateLecture(
                                                                section.id,
                                                                lecture.id,
                                                                "h5pContentId",
                                                                contentId,
                                                              )
                                                            }
                                                          />
                                                        ) : lecture.contentType ===
                                                          "three_d" ? (
                                                          <>
                                                            <ThreeDModelPicker
                                                              title={
                                                                lecture.title
                                                              }
                                                              attachedId={
                                                                lecture.threeDModelId ??
                                                                null
                                                              }
                                                              onAttach={(
                                                                modelId,
                                                              ) =>
                                                                updateLecture(
                                                                  section.id,
                                                                  lecture.id,
                                                                  "threeDModelId",
                                                                  modelId,
                                                                )
                                                              }
                                                            />
                                                            {lecture.threeDModelId ? (
                                                              <TierPreview
                                                                modelId={
                                                                  lecture.threeDModelId
                                                                }
                                                                description={
                                                                  lecture.description ||
                                                                  undefined
                                                                }
                                                              />
                                                            ) : null}
                                                            {lecture.threeDModelId ? (
                                                              <ThreeDTeachingKit
                                                                modelId={
                                                                  lecture.threeDModelId
                                                                }
                                                                lessonTitle={
                                                                  lecture.title
                                                                }
                                                                hasDescription={
                                                                  !!lecture.description
                                                                }
                                                              />
                                                            ) : null}
                                                          </>
                                                        ) : lecture.contentType ===
                                                          "virtual_lab" ? (
                                                          <VirtualLabPicker
                                                            attachedSim={
                                                              lecture.virtualLabSim ??
                                                              null
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
                                                        ) : lecture.contentType ===
                                                          "geogebra" ? (
                                                          <GeoGebraAuthorCard
                                                            title={
                                                              lecture.title
                                                            }
                                                            attachedId={
                                                              lecture.geogebraAppletId ??
                                                              null
                                                            }
                                                            onAttach={(
                                                              appletId,
                                                            ) =>
                                                              updateLecture(
                                                                section.id,
                                                                lecture.id,
                                                                "geogebraAppletId",
                                                                appletId,
                                                              )
                                                            }
                                                          />
                                                        ) : lecture.contentType ===
                                                          "game" ? (
                                                          <GamePicker
                                                            value={
                                                              lecture.gameId ??
                                                              null
                                                            }
                                                            onChange={(
                                                              gameId,
                                                            ) =>
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
                                                            <VideoUpload
                                                              value={
                                                                lecture.videoUrl ||
                                                                ""
                                                              }
                                                              onChange={(url) =>
                                                                updateLecture(
                                                                  section.id,
                                                                  lecture.id,
                                                                  "videoUrl",
                                                                  url,
                                                                )
                                                              }
                                                              onDurationChange={(
                                                                duration,
                                                              ) => {
                                                                // Convert minutes to MM:SS format
                                                                const minutes =
                                                                  Math.floor(
                                                                    duration,
                                                                  );
                                                                const seconds =
                                                                  Math.round(
                                                                    (duration -
                                                                      minutes) *
                                                                      60,
                                                                  );
                                                                const formattedDuration = `${minutes}:${seconds.toString().padStart(2, "0")}`;
                                                                updateLecture(
                                                                  section.id,
                                                                  lecture.id,
                                                                  "duration",
                                                                  formattedDuration,
                                                                );
                                                              }}
                                                              label="Upload Lecture Video"
                                                              description="Upload a video for this lecture"
                                                            />

                                                            {/* YouTube URL input for video lectures */}
                                                            <div className="space-y-2">
                                                              <label className="block text-sm font-medium text-gray-700 flex items-center gap-2">
                                                                <LinkIcon className="w-4 h-4" />
                                                                YouTube URL
                                                                (Alternative)
                                                              </label>
                                                              <input
                                                                type="url"
                                                                value={
                                                                  lecture.youtubeUrl ||
                                                                  ""
                                                                }
                                                                onChange={(e) =>
                                                                  updateLecture(
                                                                    section.id,
                                                                    lecture.id,
                                                                    "youtubeUrl",
                                                                    e.target
                                                                      .value,
                                                                  )
                                                                }
                                                                placeholder="YouTube URL or Bunny player URL (https://player.mediadelivery.net/play/...)"
                                                                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
                                                              />
                                                              <p className="text-xs text-gray-500">
                                                                Paste a YouTube
                                                                video URL to
                                                                extract and play
                                                                without branding
                                                              </p>
                                                            </div>
                                                          </>
                                                        )}
                                                      </div>
                                                    )}

                                                    {lecture.type ===
                                                      "quiz" && (
                                                      <div className="mt-3 p-4 bg-blue-50 border border-blue-200 rounded-lg">
                                                        <div className="flex items-center justify-between mb-3">
                                                          <h5 className="font-medium text-gray-900">
                                                            Quiz Configuration
                                                          </h5>
                                                          <Button
                                                            size="sm"
                                                            onClick={() =>
                                                              handleConfigureQuiz(
                                                                section.id,
                                                                lecture,
                                                              )
                                                            }
                                                          >
                                                            <HelpCircle className="h-4 w-4 mr-1" />
                                                            {(lecture as any)
                                                              .sourceType ===
                                                            "quiz"
                                                              ? "Edit Quiz"
                                                              : "Configure Quiz"}
                                                          </Button>
                                                        </div>
                                                        {(lecture as any)
                                                          .sourceType ===
                                                        "quiz" ? (
                                                          <div className="text-sm text-gray-700">
                                                            <p className="mb-1">
                                                              ✓ Quiz configured
                                                              with{" "}
                                                              {
                                                                (lecture as any)
                                                                  .questionsCount
                                                              }{" "}
                                                              question(s)
                                                            </p>
                                                            <p className="text-xs text-gray-500">
                                                              Time limit:{" "}
                                                              {lecture.duration}{" "}
                                                              minutes
                                                            </p>
                                                          </div>
                                                        ) : (
                                                          <>
                                                            <p className="text-sm text-gray-600">
                                                              Click "Configure
                                                              Quiz" to set up
                                                              questions, time
                                                              limits, passing
                                                              scores, and
                                                              grading options
                                                              for this quiz.
                                                            </p>
                                                            <div className="mt-2 text-xs text-gray-500">
                                                              Note: Quiz content
                                                              is managed
                                                              separately from
                                                              lesson content.
                                                            </div>
                                                          </>
                                                        )}
                                                      </div>
                                                    )}

                                                    {lecture.type ===
                                                      "assignment" && (
                                                      <div className="mt-3 p-4 bg-orange-50 border border-orange-200 rounded-lg">
                                                        <div className="flex items-center justify-between mb-3">
                                                          <h5 className="font-medium text-gray-900">
                                                            Assignment
                                                            Configuration
                                                          </h5>
                                                          <Button
                                                            size="sm"
                                                            onClick={() =>
                                                              handleConfigureAssignment(
                                                                section.id,
                                                                lecture,
                                                              )
                                                            }
                                                          >
                                                            <PenTool className="h-4 w-4 mr-1" />
                                                            {(lecture as any)
                                                              .sourceType ===
                                                            "assignment"
                                                              ? "Edit Assignment"
                                                              : "Configure Assignment"}
                                                          </Button>
                                                        </div>
                                                        {(lecture as any)
                                                          .sourceType ===
                                                        "assignment" ? (
                                                          <div className="text-sm text-gray-700">
                                                            <p className="mb-1">
                                                              ✓ Assignment
                                                              configured
                                                            </p>
                                                            <p className="text-xs text-gray-500">
                                                              {lecture.content}
                                                            </p>
                                                          </div>
                                                        ) : (
                                                          <>
                                                            <p className="text-sm text-gray-600">
                                                              Click "Configure
                                                              Assignment" to set
                                                              up submission
                                                              requirements, file
                                                              upload settings,
                                                              grading criteria,
                                                              and due dates.
                                                            </p>
                                                            <div className="mt-2 text-xs text-gray-500">
                                                              Note: Assignment
                                                              settings are
                                                              managed separately
                                                              from lesson
                                                              content.
                                                            </div>
                                                          </>
                                                        )}
                                                      </div>
                                                    )}
                                                  </div>
                                                )}
                                              </div>
                                            </SortableLecture>
                                          );
                                        },
                                      )}
                                    </SortableContext>
                                  </DndContext>
                                </div>
                              </div>
                            </div>
                          )}
                        </div>
                      </SortableSection>
                    );
                  })}
                </SortableContext>
              </DndContext>
            </div>
          </Card>
        )}
        {activeTab === "settings" && (
          <Card className="p-6">
            <h2 className="text-xl font-semibold text-gray-900 mb-6">
              Course Settings
            </h2>
            <div className="space-y-6">
              {/* v2.0 §4.2 (WP6): Parent View Configurator + Reward System Designer */}
              {id && studioSettings && (
                <>
                  <GuardianVisibility
                    courseId={Number(id)}
                    settings={studioSettings}
                    onChange={setStudioSettings}
                  />
                  <RewardDesigner
                    courseId={Number(id)}
                    settings={studioSettings}
                    onChange={setStudioSettings}
                  />
                  <CollaboratorsBlock courseId={Number(id)} />
                </>
              )}
              {/* Certificate Selection */}
              <div className="border border-gray-200 rounded-xl p-6 bg-orange-50">
                <div className="flex items-center gap-3 mb-4">
                  <div className="w-10 h-10 bg-orange-100 rounded-lg flex items-center justify-center">
                    <span className="text-orange-600 text-xl">
                      <AstraSymbol value="🏆" />
                    </span>
                  </div>
                  <div>
                    <h3 className="text-lg font-semibold text-gray-900">
                      Certificate of Completion
                    </h3>
                    <p className="text-sm text-gray-500">
                      Students will receive this certificate when they complete
                      the course
                    </p>
                  </div>
                </div>
                <div className="space-y-4">
                  <label className="block text-sm font-medium text-gray-700 mb-3">
                    Choose Certificate Template
                  </label>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {/* No Certificate option */}
                    <div
                      onClick={() =>
                        setCourse((prev) => ({ ...prev, certificateId: "" }))
                      }
                      className={`cursor-pointer rounded-xl border-2 p-4 transition-all duration-200 flex flex-col items-center justify-center gap-2 h-40 ${!course.certificateId ? "border-orange-500 bg-orange-50 shadow-md" : "border-gray-200 bg-gray-50 hover:border-gray-300"}`}
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
                          setCourse((prev) => ({
                            ...prev,
                            certificateId: String(t.id),
                          }))
                        }
                        className={`group cursor-pointer rounded-xl border-2 transition-all duration-200 overflow-hidden ${String(course.certificateId) === String(t.id) ? "border-orange-500 shadow-md" : "border-gray-200 hover:border-orange-300"}`}
                      >
                        {/* Certificate Preview — real thumbnail with CSS-mock fallback */}
                        <div
                          className="h-32 relative overflow-hidden flex flex-col items-center justify-center p-4"
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
                          <div
                            className="absolute top-2 left-2 right-2 h-0.5 opacity-30"
                            style={{ backgroundColor: t.title_color }}
                          />
                          <div
                            className="absolute bottom-2 left-2 right-2 h-0.5 opacity-30"
                            style={{ backgroundColor: t.title_color }}
                          />
                          <p
                            className="text-xs font-semibold tracking-widest uppercase opacity-60"
                            style={{ color: t.title_color }}
                          >
                            Certificate of Completion
                          </p>
                          <p
                            className="text-sm font-bold mt-1"
                            style={{ color: t.title_color }}
                          >
                            Student Name
                          </p>
                          <p
                            className="text-xs opacity-50 mt-1"
                            style={{ color: t.title_color }}
                          >
                            Course Title
                          </p>
                        </div>
                        {/* Template Name */}
                        <div
                          className={`px-3 py-2 flex items-center justify-between ${String(course.certificateId) === String(t.id) ? "bg-orange-50" : "bg-white"}`}
                        >
                          <p className="text-sm font-medium text-gray-800">
                            {t.name || `Template ${t.id}`}
                          </p>
                          {String(course.certificateId) === String(t.id) && (
                            <span className="text-orange-500 text-xs font-bold">
                              ✓ Selected
                            </span>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                  {course.certificateId && (
                    <div className="bg-green-50 border border-green-200 rounded-lg p-3 flex items-center gap-3 mt-2">
                      <span className="text-xl">
                        <AstraSymbol value="🎓" />
                      </span>
                      <p className="text-sm text-green-700 font-medium">
                        Certificate enabled — students receive it automatically
                        on 100% completion
                      </p>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </Card>
        )}
        {previewTemplate && (
          <div
            className="fixed inset-0 z-[100] bg-black/70 flex items-center justify-center p-4"
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
        <div className="flex items-center justify-between mt-8">
          <Button
            variant="outline"
            onClick={() =>
              navigate(isAdmin ? "/admin/courses" : "/instructor/courses")
            }
          >
            Cancel
          </Button>
          <div className="flex space-x-3">
            <Button variant="outline" onClick={handleSave} disabled={isLoading}>
              Save as Draft
            </Button>
            <Button onClick={handlePublish} disabled={isLoading}>
              {course.status === "published"
                ? "Update & Publish"
                : "Publish Course"}
            </Button>
          </div>
        </div>
      </PageLayout>
    </div>
  );
} // cache bust 1778509610
