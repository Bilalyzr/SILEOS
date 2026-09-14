import { PageBackButton } from '@/components/routing/PageBackButton';
import { PageLayout, PageHeader } from "@/components/design-system/PageLayout";
import { useCallback } from "react";
import React, { useState, useEffect, useRef } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";
import {
  Plus,
  Trash2,
  Save,
  GripVertical,
  CheckCircle,
  CheckSquare,
  AlertCircle,
  AlertTriangle,
  FileText,
  Download,
  Upload,
} from "lucide-react";
import toast from "react-hot-toast";
import { api } from "@/api/axios";
import { ScorableItemsEditor } from "@/components/assessment/ScorableItemsEditor";
import { BankDrawDialog } from "@/components/assessment/BankDrawDialog";
import type { ScorableItem } from "@/api/scorable";
import { useAuthStore } from "@/store/auth";
import {
  QUESTION_TYPES,
  validateQuestions,
  duplicateOptionWarnings,
  friendlyServerError,
  type QuizQuestionType,
} from "./quizBuilderValidation";

interface QuizQuestion {
  id: string;
  type: QuizQuestionType;
  question: string;
  points: number;
  options?: string[];
  correctAnswer?: string | number;
  correctAnswers?: number[];
  explanation?: string;
  imageUrl?: string;
}

type FeedbackMode = "reveal_immediate" | "reveal_after_due" | "reveal_never";

interface QuizSettings {
  title: string;
  description: string;
  timeLimit: number; // in minutes
  passingScore: number; // percentage
  maxAttempts: number;
  maxQuestionsForTake?: number; // roadmap item 5: random subset per attempt (0 = all)
  randomizeQuestions: boolean;
  feedbackMode: FeedbackMode;
  availableFrom?: string;
  availableUntil?: string;
}

const QuizBuilder: React.FC = () => {
  const navigate = useNavigate();
  const { courseId, quizId } = useParams();
  const [searchParams] = useSearchParams();
  const sectionId = searchParams.get("sectionId");
  const { user } = useAuthStore();
  const isAdmin = user?.role === "admin";

  const [settings, setSettings] = useState<QuizSettings>({
    title: "",
    description: "",
    timeLimit: 30,
    passingScore: 70,
    maxAttempts: 3,
    randomizeQuestions: false,
    feedbackMode: "reveal_immediate",
  });

  const [questions, setQuestions] = useState<QuizQuestion[]>([]);
  const [modules, setModules] = useState<ScorableItem[]>([]);
  const [activeTab, setActiveTab] = useState<"questions" | "settings">(
    "questions",
  );
  const [saving, setSaving] = useState(false);
  const [, setLoading] = useState(false);
  const [isEditingExisting, setIsEditingExisting] = useState(false);
  // Question index -> server-reported error message (422 detail.index).
  const [questionErrors, setQuestionErrors] = useState<Record<number, string>>(
    {},
  );
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Load existing quiz if editing
  const loadQuiz = useCallback(async () => {
    setLoading(true);
    try {
      const response = await api.get(`/courses/${courseId}/quizzes/${quizId}`);
      const quizData = response.data;

      setSettings({
        title: quizData.title,
        description: quizData.description,
        timeLimit: quizData.timeLimit,
        passingScore: quizData.passingScore,
        maxAttempts: quizData.maxAttempts,
        randomizeQuestions: quizData.randomizeQuestions,
        feedbackMode: ([
          "reveal_immediate",
          "reveal_after_due",
          "reveal_never",
        ].includes(quizData.feedbackMode)
          ? quizData.feedbackMode
          : "reveal_immediate") as FeedbackMode,
      });

      setQuestions(quizData.questions || []);
      setModules((quizData.interactive_modules || []) as ScorableItem[]);
      setIsEditingExisting(true); // Mark as editing existing quiz
    } catch (error: any) {
      console.error("Error loading quiz:", error);
      setIsEditingExisting(false); // Mark as creating new quiz
      // 401 is handled by token refresh interceptor, 404 means new quiz - don't show toast
      if (
        error.response?.status !== 404 &&
        error.response?.status !== 401 &&
        !error.config?._retry
      ) {
        toast.error("Failed to load quiz");
      }
    } finally {
      setLoading(false);
    }
  }, [courseId, quizId]);
  useEffect(() => {
    if (quizId && courseId) {
      loadQuiz();
    }
  }, [quizId, courseId, loadQuiz]);

  // Add new question
  const addQuestion = (type: QuizQuestion["type"]) => {
    const newQuestion: QuizQuestion = {
      id: `q-${Date.now()}`,
      type,
      question: "",
      points: 1,
      options:
        type === "multiple_choice" || type === "multi_select"
          ? ["", "", "", ""]
          : undefined,
      correctAnswer:
        type === "true_false"
          ? "true"
          : type === "fill_in_blank"
            ? ""
            : undefined,
      correctAnswers: type === "multi_select" ? [] : undefined,
    };

    setQuestions([...questions, newQuestion]);
  };

  // Update question
  const updateQuestion = (id: string, updates: Partial<QuizQuestion>) => {
    setQuestions(
      questions.map((q) => (q.id === id ? { ...q, ...updates } : q)),
    );
  };

  // Change a question's type, converting/clearing stale answer fields so
  // switching type never leaves an answer shape that doesn't match the new
  // type (e.g. a leftover `correctAnswers` array on a plain multiple_choice
  // question, or a stale option-index `correctAnswer` on a fill_in_blank).
  const changeQuestionType = (id: string, newType: QuizQuestion["type"]) => {
    setQuestions(
      questions.map((q) => {
        if (q.id !== id) return q;

        const wasChoiceLike =
          q.type === "multiple_choice" || q.type === "multi_select";
        const isChoiceLike =
          newType === "multiple_choice" || newType === "multi_select";

        const next: QuizQuestion = {
          ...q,
          type: newType,
          options: isChoiceLike
            ? q.options && q.options.length >= 2
              ? q.options
              : ["", "", "", ""]
            : undefined,
          correctAnswer: undefined,
          correctAnswers: undefined,
        };

        if (newType === "multiple_choice") {
          // multi_select -> multiple_choice keeps the first selected index.
          if (
            wasChoiceLike &&
            q.type === "multi_select" &&
            q.correctAnswers &&
            q.correctAnswers.length > 0
          ) {
            next.correctAnswer = q.correctAnswers[0];
          }
        } else if (newType === "multi_select") {
          // multiple_choice -> multi_select keeps the single index as a list.
          if (
            wasChoiceLike &&
            q.type === "multiple_choice" &&
            typeof q.correctAnswer === "number"
          ) {
            next.correctAnswers = [q.correctAnswer];
          } else {
            next.correctAnswers = [];
          }
        } else if (newType === "true_false") {
          next.correctAnswer = "true";
        } else if (newType === "fill_in_blank") {
          next.correctAnswer = "";
        }
        // short_answer / essay: no correctAnswer needed (essay never graded
        // automatically; short_answer's empty correctAnswer means manual grade).

        return next;
      }),
    );
  };

  // Toggle one option index inside a multi_select question's correctAnswers.
  const toggleMultiSelectAnswer = (questionId: string, optionIndex: number) => {
    setQuestions(
      questions.map((q) => {
        if (q.id !== questionId) return q;
        const current = q.correctAnswers || [];
        const next = current.includes(optionIndex)
          ? current.filter((i) => i !== optionIndex)
          : [...current, optionIndex].sort((a, b) => a - b);
        return { ...q, correctAnswers: next };
      }),
    );
  };

  // Delete question
  const deleteQuestion = (id: string) => {
    setQuestions(questions.filter((q) => q.id !== id));
  };

  // Update option for multiple choice
  const updateOption = (
    questionId: string,
    optionIndex: number,
    value: string,
  ) => {
    setQuestions(
      questions.map((q) => {
        if (q.id === questionId && q.options) {
          const newOptions = [...q.options];
          newOptions[optionIndex] = value;
          return { ...q, options: newOptions };
        }
        return q;
      }),
    );
  };

  // Add option to multiple choice
  const addOption = (questionId: string) => {
    setQuestions(
      questions.map((q) => {
        if (q.id === questionId && q.options) {
          return { ...q, options: [...q.options, ""] };
        }
        return q;
      }),
    );
  };

  // Remove option from multiple choice / multi_select. Reindexes
  // correctAnswer/correctAnswers so a stale index never points at a
  // shifted or removed option.
  const removeOption = (questionId: string, optionIndex: number) => {
    setQuestions(
      questions.map((q) => {
        if (q.id === questionId && q.options && q.options.length > 2) {
          const newOptions = q.options.filter((_, i) => i !== optionIndex);
          const reindex = (i: number) =>
            i === optionIndex ? -1 : i > optionIndex ? i - 1 : i;
          if (
            q.type === "multiple_choice" &&
            typeof q.correctAnswer === "number"
          ) {
            const newCorrect = reindex(q.correctAnswer);
            return {
              ...q,
              options: newOptions,
              correctAnswer: newCorrect === -1 ? undefined : newCorrect,
            };
          }
          if (q.type === "multi_select" && q.correctAnswers) {
            const newCorrectAnswers = q.correctAnswers
              .map(reindex)
              .filter((i) => i !== -1);
            return {
              ...q,
              options: newOptions,
              correctAnswers: newCorrectAnswers,
            };
          }
          return { ...q, options: newOptions };
        }
        return q;
      }),
    );
  };

  // Export quiz to JSON
  const handleExportQuiz = () => {
    const exportData = {
      version: "1.0",
      title: settings.title,
      description: settings.description,
      timeLimit: settings.timeLimit,
      availableFrom: settings.availableFrom || "",
      availableUntil: settings.availableUntil || "",
      passingScore: settings.passingScore,
      maxAttempts: settings.maxAttempts,
      maxQuestionsForTake: settings.maxQuestionsForTake || 0,
      randomizeQuestions: settings.randomizeQuestions,
      feedbackMode: settings.feedbackMode,
      questions: questions.map((q) => ({
        type: q.type,
        question: q.question,
        points: q.points,
        options: q.options,
        correctAnswer: q.correctAnswer,
        correctAnswers: q.correctAnswers,
        explanation: q.explanation || "",
        imageUrl: q.imageUrl || "",
      })),
    };

    const blob = new Blob([JSON.stringify(exportData, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${settings.title.replace(/[^a-z0-9]/gi, "_").toLowerCase()}_quiz.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    toast.success("Quiz exported successfully!");
  };

  // Download template
  const handleDownloadTemplate = () => {
    const template = {
      version: "1.0",
      title: "Sample Quiz Title",
      description: "Quiz description goes here",
      timeLimit: 30,
      passingScore: 70,
      maxAttempts: 3,
      randomizeQuestions: false,
      feedbackMode: "reveal_immediate",
      questions: [
        {
          type: "multiple_choice",
          question: "What is React?",
          points: 10,
          options: ["A library", "A framework", "A database", "An IDE"],
          correctAnswer: 0,
          explanation: "React is a JavaScript library for building UIs",
          imageUrl: "",
        },
        {
          type: "multi_select",
          question:
            "Which of these are JavaScript libraries/frameworks? (select all that apply)",
          points: 10,
          options: ["React", "Django", "Vue", "Flask"],
          correctAnswers: [0, 2],
          explanation:
            "React and Vue are JS frameworks/libraries; Django and Flask are Python.",
          imageUrl: "",
        },
        {
          type: "true_false",
          question: "React components must start with uppercase",
          points: 10,
          correctAnswer: "true",
          explanation: "True, React component names must start with uppercase",
          imageUrl: "",
        },
        {
          type: "fill_in_blank",
          question: "React uses _____ to describe UI",
          points: 10,
          correctAnswer: "JSX",
          explanation: "",
          imageUrl: "",
        },
        {
          type: "short_answer",
          question: "What is a React hook?",
          points: 10,
          correctAnswer: "Functions that let you use state and lifecycle",
          explanation: "",
          imageUrl: "",
        },
        {
          type: "essay",
          question: "Explain the component lifecycle in React",
          points: 20,
          correctAnswer: "",
          explanation: "",
          imageUrl: "",
        },
      ],
    };

    const blob = new Blob([JSON.stringify(template, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "quiz_template.json";
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    toast.success("Template downloaded!");
  };

  // Import quiz from JSON
  const handleImportQuiz = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const data = JSON.parse(e.target?.result as string);

        // Validate basic structure
        if (!data.questions || !Array.isArray(data.questions)) {
          toast.error("Invalid quiz file: missing questions array");
          return;
        }

        // Validate and transform questions
        const importedQuestions: QuizQuestion[] = [];

        for (const q of data.questions) {
          if (!q.type || !QUESTION_TYPES.includes(q.type)) {
            toast.error(`Invalid question type: ${q.type}`);
            return;
          }
          if (!q.question || typeof q.question !== "string") {
            toast.error("Each question must have a text");
            return;
          }

          importedQuestions.push({
            id: `q-${Date.now()}-${Math.random()}`,
            type: q.type,
            question: q.question,
            points: q.points || 10,
            options: q.options || undefined,
            correctAnswer: q.correctAnswer,
            correctAnswers: Array.isArray(q.correctAnswers)
              ? q.correctAnswers
              : undefined,
            explanation: q.explanation || "",
            imageUrl: q.imageUrl || "",
          });
        }

        // Update settings if provided
        if (data.title) setSettings((prev) => ({ ...prev, title: data.title }));
        if (data.description !== undefined)
          setSettings((prev) => ({ ...prev, description: data.description }));
        if (data.timeLimit !== undefined)
          setSettings((prev) => ({ ...prev, timeLimit: data.timeLimit }));
        if (data.maxQuestionsForTake !== undefined)
          setSettings((prev) => ({
            ...prev,
            maxQuestionsForTake: data.maxQuestionsForTake || 0,
          }));
        if (data.availableFrom !== undefined)
          setSettings((prev) => ({
            ...prev,
            availableFrom: data.availableFrom || "",
            availableUntil: data.availableUntil || "",
          }));
        if (data.passingScore !== undefined)
          setSettings((prev) => ({ ...prev, passingScore: data.passingScore }));
        if (data.maxAttempts !== undefined)
          setSettings((prev) => ({ ...prev, maxAttempts: data.maxAttempts }));
        if (data.randomizeQuestions !== undefined)
          setSettings((prev) => ({
            ...prev,
            randomizeQuestions: data.randomizeQuestions,
          }));
        if (
          ["reveal_immediate", "reveal_after_due", "reveal_never"].includes(
            data.feedbackMode,
          )
        ) {
          setSettings((prev) => ({ ...prev, feedbackMode: data.feedbackMode }));
        }

        setQuestions(importedQuestions);
        toast.success(`Imported ${importedQuestions.length} questions!`);
      } catch (error) {
        console.error("Import error:", error);
        toast.error("Failed to parse quiz file. Please check the format.");
      }
    };

    reader.readAsText(file);

    // Reset input
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  // Save quiz
  const handleSave = async () => {
    if (!settings.title.trim()) {
      toast.error("Please enter a quiz title");
      return;
    }

    if (questions.length === 0) {
      toast.error("Please add at least one question");
      return;
    }

    if (questions.some((q) => !q.question.trim())) {
      toast.error("Please enter the question text for every question");
      return;
    }

    // Client-side validation mirrors the server's R7 rules (reduces round
    // trips) — but the server is authoritative, so a 422 is still handled
    // below regardless of what this finds.
    const clientErrors = validateQuestions(questions);
    if (clientErrors.length > 0) {
      const errorMap: Record<number, string> = {};
      clientErrors.forEach((e) => {
        errorMap[e.index] = e.message;
      });
      setQuestionErrors(errorMap);
      toast.error(
        clientErrors.length === 1
          ? `Question ${clientErrors[0].index + 1}: ${clientErrors[0].message}`
          : `Please fix ${clientErrors.length} question(s) before saving`,
      );
      return;
    }
    setQuestionErrors({});

    setSaving(true);
    try {
      // The builder always sends the FULL settings object — including
      // feedbackMode — on both create and update, never a partial PUT that
      // could reset/omit it server-side.
      const quizData = {
        title: settings.title,
        description: settings.description,
        timeLimit: settings.timeLimit,
        availableFrom: settings.availableFrom || "",
        availableUntil: settings.availableUntil || "",
        passingScore: settings.passingScore,
        maxAttempts: settings.maxAttempts,
        maxQuestionsForTake: settings.maxQuestionsForTake || 0,
        randomizeQuestions: settings.randomizeQuestions,
        feedbackMode: settings.feedbackMode,
        interactive_modules: modules,
        questions: questions.map((q) => ({
          type: q.type,
          question: q.question,
          points: q.points,
          options: q.options,
          correctAnswer: q.correctAnswer,
          correctAnswers: q.correctAnswers,
          explanation: q.explanation || "",
          imageUrl: q.imageUrl || "",
        })),
      };

      let savedQuizId = quizId;
      if (isEditingExisting) {
        await api.put(`/courses/${courseId}/quizzes/${quizId}`, quizData);
        toast.success("Quiz updated successfully!");
      } else {
        const response = await api.post(
          `/courses/${courseId}/quizzes`,
          quizData,
        );
        savedQuizId = response?.data?.id?.toString() || quizId;
        toast.success("Quiz created successfully!");
      }

      // Update sections_meta to keep quiz in correct section
      if (sectionId && courseId) {
        try {
          const courseResp = await api.get(`/courses/${courseId}`);
          const courseData = courseResp.data;
          let sections = [];
          try {
            sections = JSON.parse(courseData.sections_meta || "[]");
          } catch {
            sections = [];
          }
          const newQuizId = `quiz-${savedQuizId}`;
          // Add to section if not already there
          const inSection = sections.some((s: any) =>
            s.lectureIds?.includes(newQuizId),
          );
          if (!inSection) {
            sections = sections.map((s: any) =>
              s.id === sectionId
                ? { ...s, lectureIds: [...(s.lectureIds || []), newQuizId] }
                : s,
            );
            await api.put(`/courses/${courseId}`, {
              sections_meta: JSON.stringify(sections),
            });
          }
        } catch {}
      }
      navigate(`/${isAdmin ? "admin" : "instructor"}/courses/${courseId}/edit`);
    } catch (error: any) {
      const status = error.response?.status;
      if (status === 422) {
        const { message, index } = friendlyServerError(
          error.response?.data?.detail,
        );
        if (index !== null) {
          setQuestionErrors({ [index]: message });
          toast.error(`Question ${index + 1}: ${message}`);
        } else {
          toast.error(message);
        }
      } else {
        toast.error(error.response?.data?.detail || "Failed to save quiz");
      }
      console.error(error);
    } finally {
      setSaving(false);
    }
  };

  // Calculate total points
  const totalPoints = questions.reduce((sum, q) => sum + q.points, 0);

  // Non-blocking duplicate-option warnings (deferred F6-style minor).
  const duplicateWarningsList = duplicateOptionWarnings(questions);

  return (
    <div className="min-h-screen bg-neutral-50 py-8">
      <PageLayout
        header={
          <PageHeader>
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-4">
                <PageBackButton className="btn btn-ghost"/>
                <div>
                  <h1 className="text-2xl font-bold text-neutral-900">
                    {quizId ? "Edit Quiz" : "Create New Quiz"}
                  </h1>
                  <p className="text-neutral-600 text-sm mt-1">
                    {questions.length} questions • {totalPoints} total points
                  </p>
                </div>
                {quizId && (
                  <BankDrawDialog
                    quizId={Number(quizId)}
                    onDone={() => window.location.reload()}
                  />
                )}
              </div>
              <div className="flex gap-2">
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".json"
                  onChange={handleImportQuiz}
                  className="hidden"
                />
                <button
                  onClick={handleDownloadTemplate}
                  className="btn btn-outline"
                  title="Download quiz template"
                >
                  <Download className="w-5 h-5" />
                </button>
                <button
                  onClick={() => fileInputRef.current?.click()}
                  className="btn btn-outline"
                  title="Import quiz from JSON"
                >
                  <Upload className="w-5 h-5" />
                </button>
                <button
                  onClick={handleExportQuiz}
                  className="btn btn-outline"
                  title="Export quiz to JSON"
                >
                  <Download className="w-5 h-5 rotate-180" />
                </button>
                <button
                  onClick={handleSave}
                  disabled={saving}
                  className="btn btn-primary"
                >
                  <Save className="w-5 h-5 mr-2" />
                  {saving ? "Saving..." : "Save Quiz"}
                </button>
              </div>
            </div>

            {/* Tabs */}
            <div className="flex gap-2 border-b">
              <button
                onClick={() => setActiveTab("questions")}
                className={`px-4 py-2 font-medium transition-colors ${
                  activeTab === "questions"
                    ? "text-primary-600 border-b-2 border-primary-600"
                    : "text-neutral-600 hover:text-neutral-900"
                }`}
              >
                Questions ({questions.length})
              </button>
              <button
                onClick={() => setActiveTab("settings")}
                className={`px-4 py-2 font-medium transition-colors ${
                  activeTab === "settings"
                    ? "text-primary-600 border-b-2 border-primary-600"
                    : "text-neutral-600 hover:text-neutral-900"
                }`}
              >
                Settings
              </button>
            </div>
          </PageHeader>
        }
        className="rd-screen rd-screen-instructor-quiz-builder"
      >
        {activeTab === "questions" && (
          <div className="space-y-6">
            {/* Scorable items — v2.0 §5 quiz-as-container */}
            <ScorableItemsEditor items={modules} onChange={setModules} />

            {/* Add Question Buttons */}
            <div
              className="bg-white rounded-xl shadow-soft p-6"
              data-glass="content"
            >
              <h3 className="font-semibold text-neutral-900 mb-4">
                Add Question
              </h3>
              <div className="grid grid-cols-2 md:grid-cols-6 gap-3">
                <button
                  onClick={() => addQuestion("multiple_choice")}
                  className="btn btn-outline flex-col h-auto py-4"
                >
                  <CheckCircle className="w-6 h-6 mb-2" />
                  <span className="text-sm">Multiple Choice</span>
                </button>
                <button
                  onClick={() => addQuestion("multi_select")}
                  className="btn btn-outline flex-col h-auto py-4"
                  title="Checkbox question — one or more correct answers"
                >
                  <CheckSquare className="w-6 h-6 mb-2" />
                  <span className="text-sm">Multiple Select</span>
                </button>
                <button
                  onClick={() => addQuestion("true_false")}
                  className="btn btn-outline flex-col h-auto py-4"
                >
                  <AlertCircle className="w-6 h-6 mb-2" />
                  <span className="text-sm">True/False</span>
                </button>
                <button
                  onClick={() => addQuestion("short_answer")}
                  className="btn btn-outline flex-col h-auto py-4"
                >
                  <FileText className="w-6 h-6 mb-2" />
                  <span className="text-sm">Short Answer</span>
                </button>
                <button
                  onClick={() => addQuestion("fill_in_blank")}
                  className="btn btn-outline flex-col h-auto py-4"
                >
                  <FileText className="w-6 h-6 mb-2" />
                  <span className="text-sm">Fill in Blank</span>
                </button>
                <button
                  onClick={() => addQuestion("essay")}
                  className="btn btn-outline flex-col h-auto py-4"
                  title="Manually graded — instructor reviews the answer after the student submits"
                >
                  <FileText className="w-6 h-6 mb-2" />
                  <span className="text-sm">Essay (manually graded)</span>
                </button>
              </div>
            </div>

            {/* Questions List */}
            {questions.map((question, index) => (
              <div
                key={question.id}
                className={`bg-white rounded-xl shadow-soft p-6 ${
                  questionErrors[index] ? "ring-2 ring-danger-500" : ""
                }`}
                data-glass="work"
              >
                <div className="flex items-start gap-4">
                  <div className="flex-shrink-0 mt-2">
                    <GripVertical className="w-5 h-5 text-neutral-400 cursor-move" />
                  </div>

                  <div className="flex-1 space-y-4">
                    {/* Question Header */}
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-2 flex-wrap">
                          <span className="text-sm font-semibold text-neutral-600">
                            Question {index + 1}
                          </span>
                          <select
                            aria-label={`Question ${index + 1} type`}
                            value={question.type}
                            onChange={(e) =>
                              changeQuestionType(
                                question.id,
                                e.target.value as QuizQuestion["type"],
                              )
                            }
                            className="input input-sm text-sm py-1"
                          >
                            <option value="multiple_choice">
                              Multiple Choice
                            </option>
                            <option value="multi_select">
                              Multiple Select
                            </option>
                            <option value="true_false">True/False</option>
                            <option value="short_answer">Short Answer</option>
                            <option value="fill_in_blank">Fill in Blank</option>
                            <option value="essay">
                              Essay (manually graded)
                            </option>
                          </select>
                          {(question.type === "essay" ||
                            question.type === "open_ended") && (
                            <span className="badge badge-sm bg-purple-100 text-purple-700">
                              Manually graded
                            </span>
                          )}
                          {duplicateWarningsList.some((w) =>
                            w.startsWith(`Question ${index + 1} `),
                          ) && (
                            <span className="badge badge-sm bg-amber-100 text-amber-800 flex items-center gap-1">
                              <AlertTriangle className="w-3 h-3" />
                              Duplicate options
                            </span>
                          )}
                        </div>
                        <textarea
                          value={question.question}
                          onChange={(e) =>
                            updateQuestion(question.id, {
                              question: e.target.value,
                            })
                          }
                          placeholder="Enter your question..."
                          className="input w-full min-h-[80px]"
                          rows={3}
                        />
                        {questionErrors[index] && (
                          <p className="text-sm text-danger-600 mt-1 flex items-center gap-1">
                            <AlertCircle className="w-4 h-4" />
                            {questionErrors[index]}
                          </p>
                        )}
                      </div>
                      <button
                        onClick={() => deleteQuestion(question.id)}
                        className="btn btn-ghost btn-sm text-danger-600 hover:bg-danger-50"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>

                    {/* Multiple Choice Options */}
                    {question.type === "multiple_choice" && (
                      <div className="space-y-2">
                        <label className="block text-sm font-medium text-neutral-700">
                          Answer Options — select the radio button for the
                          correct answer
                        </label>
                        {question.options?.map((option, optIndex) => (
                          <div
                            key={optIndex}
                            className="flex items-center gap-2"
                          >
                            <input
                              type="radio"
                              name={`correct-${question.id}`}
                              checked={question.correctAnswer === optIndex}
                              onChange={() =>
                                updateQuestion(question.id, {
                                  correctAnswer: optIndex,
                                })
                              }
                              className="radio"
                            />
                            <input
                              type="text"
                              value={option}
                              onChange={(e) =>
                                updateOption(
                                  question.id,
                                  optIndex,
                                  e.target.value,
                                )
                              }
                              placeholder={`Option ${optIndex + 1}`}
                              className="input flex-1"
                            />
                            {question.options &&
                              question.options.length > 2 && (
                                <button
                                  onClick={() =>
                                    removeOption(question.id, optIndex)
                                  }
                                  className="btn btn-ghost btn-sm text-danger-600"
                                >
                                  <Trash2 className="w-4 h-4" />
                                </button>
                              )}
                          </div>
                        ))}
                        <button
                          onClick={() => addOption(question.id)}
                          className="btn btn-sm btn-outline"
                        >
                          <Plus className="w-4 h-4 mr-1" />
                          Add Option
                        </button>
                      </div>
                    )}

                    {/* Multiple Select (checkbox) Options */}
                    {question.type === "multi_select" && (
                      <div className="space-y-2">
                        <label className="block text-sm font-medium text-neutral-700">
                          Answer Options — check every correct answer (at least
                          one)
                        </label>
                        {question.options?.map((option, optIndex) => (
                          <div
                            key={optIndex}
                            className="flex items-center gap-2"
                          >
                            <input
                              type="checkbox"
                              aria-label={`Option ${optIndex + 1} is correct`}
                              checked={(question.correctAnswers || []).includes(
                                optIndex,
                              )}
                              onChange={() =>
                                toggleMultiSelectAnswer(question.id, optIndex)
                              }
                              className="checkbox"
                            />
                            <input
                              type="text"
                              value={option}
                              onChange={(e) =>
                                updateOption(
                                  question.id,
                                  optIndex,
                                  e.target.value,
                                )
                              }
                              placeholder={`Option ${optIndex + 1}`}
                              className="input flex-1"
                            />
                            {question.options &&
                              question.options.length > 2 && (
                                <button
                                  onClick={() =>
                                    removeOption(question.id, optIndex)
                                  }
                                  className="btn btn-ghost btn-sm text-danger-600"
                                >
                                  <Trash2 className="w-4 h-4" />
                                </button>
                              )}
                          </div>
                        ))}
                        <button
                          onClick={() => addOption(question.id)}
                          className="btn btn-sm btn-outline"
                        >
                          <Plus className="w-4 h-4 mr-1" />
                          Add Option
                        </button>
                      </div>
                    )}

                    {/* True/False */}
                    {question.type === "true_false" && (
                      <div className="space-y-2">
                        <label className="block text-sm font-medium text-neutral-700">
                          Correct Answer
                        </label>
                        <div className="flex gap-4">
                          <label className="flex items-center gap-2 cursor-pointer">
                            <input
                              type="radio"
                              name={`tf-${question.id}`}
                              value="true"
                              checked={question.correctAnswer === "true"}
                              onChange={() =>
                                updateQuestion(question.id, {
                                  correctAnswer: "true",
                                })
                              }
                              className="radio"
                            />
                            <span>True</span>
                          </label>
                          <label className="flex items-center gap-2 cursor-pointer">
                            <input
                              type="radio"
                              name={`tf-${question.id}`}
                              value="false"
                              checked={question.correctAnswer === "false"}
                              onChange={() =>
                                updateQuestion(question.id, {
                                  correctAnswer: "false",
                                })
                              }
                              className="radio"
                            />
                            <span>False</span>
                          </label>
                        </div>
                      </div>
                    )}

                    {/* Fill in Blank */}
                    {question.type === "fill_in_blank" && (
                      <div className="space-y-2">
                        <label className="block text-sm font-medium text-neutral-700">
                          Correct Answer
                        </label>
                        <input
                          type="text"
                          value={(question.correctAnswer as string) || ""}
                          onChange={(e) =>
                            updateQuestion(question.id, {
                              correctAnswer: e.target.value,
                            })
                          }
                          placeholder="Enter the correct answer..."
                          className="input w-full"
                          maxLength={200}
                        />
                        <p className="text-xs text-neutral-500">
                          Students must type this exact answer
                          (case-insensitive). Max 200 characters.
                        </p>
                      </div>
                    )}

                    {/* Short Answer */}
                    {question.type === "short_answer" && (
                      <div className="space-y-2">
                        <label className="block text-sm font-medium text-neutral-700">
                          Correct Answer (optional)
                        </label>
                        <input
                          type="text"
                          value={(question.correctAnswer as string) || ""}
                          onChange={(e) =>
                            updateQuestion(question.id, {
                              correctAnswer: e.target.value,
                            })
                          }
                          placeholder="Leave blank to grade manually"
                          className="input w-full"
                        />
                        <p className="text-xs text-neutral-500">
                          {String(question.correctAnswer || "").trim()
                            ? "Students must type this exact answer (case-insensitive)."
                            : "No answer set — this question will be graded manually by an instructor."}
                        </p>
                      </div>
                    )}

                    {/* Essay / Open ended */}
                    {(question.type === "essay" ||
                      question.type === "open_ended") && (
                      <div className="space-y-2">
                        <p className="text-xs text-neutral-500 bg-purple-50 border border-purple-200 rounded-lg px-3 py-2">
                          This question has no automatic answer key — an
                          instructor manually reviews and grades each response
                          after submission.
                        </p>
                      </div>
                    )}

                    {/* Points and Explanation */}
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="block text-sm font-medium text-neutral-700 mb-1">
                          Points
                        </label>
                        <input
                          type="number"
                          min="1"
                          value={question.points}
                          onChange={(e) =>
                            updateQuestion(question.id, {
                              points: parseInt(e.target.value) || 1,
                            })
                          }
                          className="input w-full"
                        />
                      </div>
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-neutral-700 mb-1">
                        Explanation (Optional)
                      </label>
                      <textarea
                        value={question.explanation || ""}
                        onChange={(e) =>
                          updateQuestion(question.id, {
                            explanation: e.target.value,
                          })
                        }
                        placeholder="Explain the correct answer..."
                        className="input w-full"
                        rows={2}
                      />
                    </div>
                  </div>
                </div>
              </div>
            ))}

            {questions.length === 0 && (
              <div
                className="bg-white rounded-xl shadow-soft p-12 text-center"
                data-glass="content"
              >
                <FileText className="w-16 h-16 text-neutral-300 mx-auto mb-4" />
                <p className="text-neutral-600">No questions added yet</p>
                <p className="text-sm text-neutral-500 mt-1">
                  Click the buttons above to add your first question
                </p>
              </div>
            )}
          </div>
        )}
        {activeTab === "settings" && (
          <div
            className="bg-white rounded-xl shadow-soft p-6 space-y-6"
            data-glass="work"
          >
            <div>
              <label className="block text-sm font-medium text-neutral-700 mb-2">
                Quiz Title *
              </label>
              <input
                type="text"
                value={settings.title}
                onChange={(e) =>
                  setSettings({ ...settings, title: e.target.value })
                }
                placeholder="e.g., Module 1 Quiz"
                className="input w-full"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-neutral-700 mb-2">
                Description
              </label>
              <textarea
                value={settings.description}
                onChange={(e) =>
                  setSettings({ ...settings, description: e.target.value })
                }
                placeholder="Brief description of this quiz..."
                className="input w-full"
                rows={3}
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-neutral-700 mb-2">
                  Time Limit (minutes)
                </label>
                <input
                  type="number"
                  min="0"
                  value={settings.timeLimit}
                  onChange={(e) =>
                    setSettings({
                      ...settings,
                      timeLimit: parseInt(e.target.value) || 0,
                    })
                  }
                  className="input w-full"
                />
              </div>
              {/* R8: timed window — learners can only start between these (owner may always test) */}
              <div>
                <label className="block text-sm font-medium text-neutral-700 mb-2">
                  Opens at (optional)
                </label>
                <input
                  type="datetime-local"
                  value={
                    settings.availableFrom
                      ? new Date(settings.availableFrom)
                          .toISOString()
                          .slice(0, 16)
                      : ""
                  }
                  onChange={(e) =>
                    setSettings({
                      ...settings,
                      availableFrom: e.target.value
                        ? new Date(e.target.value).toISOString()
                        : "",
                    })
                  }
                  className="input w-full"
                  data-testid="quiz-opens-at"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-neutral-700 mb-2">
                  Closes at (optional)
                </label>
                <input
                  type="datetime-local"
                  value={
                    settings.availableUntil
                      ? new Date(settings.availableUntil)
                          .toISOString()
                          .slice(0, 16)
                      : ""
                  }
                  onChange={(e) =>
                    setSettings({
                      ...settings,
                      availableUntil: e.target.value
                        ? new Date(e.target.value).toISOString()
                        : "",
                    })
                  }
                  className="input w-full"
                  data-testid="quiz-closes-at"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-neutral-700 mb-2">
                  Passing Score (%)
                </label>
                <input
                  type="number"
                  min="0"
                  max="100"
                  value={settings.passingScore}
                  onChange={(e) =>
                    setSettings({
                      ...settings,
                      passingScore: parseInt(e.target.value) || 0,
                    })
                  }
                  className="input w-full"
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-neutral-700 mb-2">
                Maximum Attempts
              </label>
              <input
                type="number"
                min="1"
                value={settings.maxAttempts}
                onChange={(e) =>
                  setSettings({
                    ...settings,
                    maxAttempts: parseInt(e.target.value) || 1,
                  })
                }
                className="input w-full"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-neutral-700 mb-2">
                Questions per attempt (0 = all)
              </label>
              <input
                type="number"
                min="0"
                value={settings.maxQuestionsForTake || 0}
                onChange={(e) =>
                  setSettings({
                    ...settings,
                    maxQuestionsForTake: parseInt(e.target.value) || 0,
                  })
                }
                className="input w-full"
                data-testid="questions-per-attempt"
              />
              <p className="text-xs text-neutral-500 mt-1">
                Each attempt draws a different random subset — pair with "Add
                from bank".
              </p>
            </div>

            <div className="space-y-3">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={settings.randomizeQuestions}
                  onChange={(e) =>
                    setSettings({
                      ...settings,
                      randomizeQuestions: e.target.checked,
                    })
                  }
                  className="checkbox"
                />
                <span className="text-sm">Randomize question order</span>
              </label>
            </div>

            <div>
              <label
                htmlFor="feedback-mode"
                className="block text-sm font-medium text-neutral-700 mb-2"
              >
                Answer reveal
              </label>
              <select
                id="feedback-mode"
                value={settings.feedbackMode}
                onChange={(e) =>
                  setSettings({
                    ...settings,
                    feedbackMode: e.target.value as FeedbackMode,
                  })
                }
                className="input w-full"
              >
                <option value="reveal_immediate">Right after submitting</option>
                <option value="reveal_after_due">
                  After the deadline passes
                </option>
                <option value="reveal_never">Never (score only)</option>
              </select>
              <p className="text-xs text-neutral-500 mt-1">
                Controls when students see correct answers and explanations for
                this quiz.
              </p>
            </div>
          </div>
        )}
      </PageLayout>
    </div>
  );
};

export default QuizBuilder;
