import { AstraSymbol } from "@/components/design-system/AstraSymbol";
import { useCallback } from "react";
import * as React from "react";
import { sanitizeHtml } from "@/utils/sanitize";
import { useParams, useNavigate } from "react-router-dom";
import {
  Play,
  ArrowLeft,
  CheckCircle,
  CheckCircle2,
  List,
  X,
  StickyNote,
  Trash2,
  Plus,
  Shield,
  HelpCircle,
  PenTool,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  VideoPlayer,
  type VideoPlayerHandle,
} from "@/components/video/video-player";
import { H5PLesson } from "@/components/h5p/H5PLesson";
import { GamePlayer } from "@/components/games/GamePlayer";
import { GeoGebraEmbed } from "@/components/geogebra/GeoGebraEmbed";
import { ThreeDCheckYourself } from "@/components/three-d/ThreeDCheckYourself";
import { DeferredThreeD } from "@/components/three-d/DeferredThreeD";
import { AudioOnlyToggle } from "@/components/video/AudioOnlyToggle";
import { VirtualLabEmbed } from "@/components/labs/VirtualLabEmbed";
import TutorDrawer from "@/components/ai/TutorDrawer";
import { cn } from "@/utils/cn";
import { api } from "@/api/axios";
import { signal, flushSignals } from "@/api/signals";
import { courseAPI } from "@/api/course";
import { uploadDocument } from "@/api/upload";
import toast from "react-hot-toast";
import { useTheme } from "@/contexts/theme-context";
import { celebrationAnimation } from "@/utils/animations";
import { getBackendUrl } from "@/config/urls";

// Quiz Renderer Component
const QuizRenderer: React.FC<{
  quizId: number;
  courseId: number;
  onNext?: () => void;
}> = ({ quizId, courseId, onNext }) => {
  const [quiz, setQuiz] = React.useState<any>(null);
  const [answers, setAnswers] = React.useState<{ [key: string]: any }>({});
  const [submitted, setSubmitted] = React.useState(false);
  const [score, setScore] = React.useState(0);
  const [, setShowExplanations] = React.useState(false);
  const [previousAttempt, setPreviousAttempt] = React.useState<any>(null);
  const [submitting, setSubmitting] = React.useState(false);
  const [attemptsInfo, setAttemptsInfo] = React.useState<{
    used: number;
    max: number;
    remaining: number;
    unlimited: boolean;
  } | null>(null);
  // Result flags from the submit response (spec A1.1/A1.3): pendingReview
  // means one or more essay/open-ended answers still await instructor
  // grading — the percentage shown is auto-graded-only and provisional.
  // lateSubmission means the server force-closed the attempt at the
  // deadline using only answers already saved by then.
  const [pendingReview, setPendingReview] = React.useState(false);
  const [lateSubmission, setLateSubmission] = React.useState(false);

  React.useEffect(() => {
    const loadQuiz = async () => {
      try {
        // Fetch full quiz with questions
        const response = await api.get(
          `/courses/${courseId}/quizzes/${quizId}`,
        );
        setQuiz(response.data);

        // Check if user has a previous attempt
        const attemptResponse = await api.get(
          `/courses/${courseId}/quizzes/${quizId}/attempt`,
        );
        if (attemptResponse.data) {
          setPreviousAttempt(attemptResponse.data);
          setAnswers(attemptResponse.data.answers || {});
          setSubmitted(true);
          setScore(attemptResponse.data.percentage);
        }

        // Get attempts count
        const countResponse = await api.get(
          `/courses/${courseId}/quizzes/${quizId}/attempts-count`,
        );
        setAttemptsInfo({
          used: countResponse.data.attempts_used,
          max: countResponse.data.max_attempts,
          remaining: countResponse.data.remaining,
          unlimited: countResponse.data.unlimited,
        });
      } catch (error) {
        console.error("Failed to load quiz:", error);
        toast.error("Failed to load quiz");
      }
    };
    loadQuiz();
  }, [quizId, courseId]);

  const handleAnswerChange = (questionId: string, answer: any) => {
    setAnswers((prev) => ({ ...prev, [questionId]: answer }));
  };

  const handleSubmit = async () => {
    if (!quiz || submitting) return;

    setSubmitting(true);

    try {
      const response = await api.post(
        `/courses/${courseId}/quizzes/${quizId}/submit`,
        {
          answers: answers,
        },
      );

      const result = response.data;
      setScore(result.percentage);
      setSubmitted(true);
      setShowExplanations(true);
      setPreviousAttempt(result);
      setPendingReview(!!result.pending_review);
      setLateSubmission(!!result.late_submission);

      if (result.late_submission) {
        toast.error(
          "Submitted late — only answers saved before the deadline were scored.",
          { duration: 6000 },
        );
      } else if (result.pending_review) {
        toast(
          "Submitted — some answers need instructor review before your final score is ready.",
          { icon: <AstraSymbol value="📝" />, duration: 6000 },
        );
      } else if (result.passed) {
        toast.success(`Passed! Score: ${result.percentage}%`);
      } else {
        toast.error(
          `Score: ${result.percentage}%. Passing: ${result.passing_grade}%`,
        );
      }
    } catch (error: any) {
      console.error("Failed to submit quiz:", error);
      toast.error(error.response?.data?.detail || "Failed to submit quiz");
    } finally {
      setSubmitting(false);
    }
  };

  const handleRetry = async () => {
    setAnswers({});
    setSubmitted(false);
    setScore(0);
    setShowExplanations(false);
    setPreviousAttempt(null);
    setPendingReview(false);
    setLateSubmission(false);

    // Refresh attempts count
    try {
      const countResponse = await api.get(
        `/courses/${courseId}/quizzes/${quizId}/attempts-count`,
      );
      setAttemptsInfo({
        used: countResponse.data.attempts_used,
        max: countResponse.data.max_attempts,
        remaining: countResponse.data.remaining,
        unlimited: countResponse.data.unlimited,
      });
    } catch (error) {
      console.error("Failed to refresh attempts count:", error);
    }

    toast.success("Quiz reset. Try again!");
  };

  if (!quiz) {
    return (
      <div className="flex items-center justify-center h-full bg-neutral-900 text-white">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    );
  }

  return (
    <div className="h-full overflow-y-auto bg-neutral-900 text-white p-8">
      <div className="max-w-4xl mx-auto">
        <div className="mb-8">
          <h1 className="text-3xl font-bold mb-2">{quiz.title}</h1>
          <p className="text-neutral-400">{quiz.description}</p>
          <div className="flex gap-4 mt-4 text-sm flex-wrap">
            <span className="text-neutral-500">
              <AstraSymbol value="⏱️" /> {quiz.timeLimit} minutes
            </span>
            <span className="text-neutral-500">
              <AstraSymbol value="📊" /> Passing: {quiz.passingScore}%
            </span>
            <span className="text-neutral-500">
              <AstraSymbol value="📝" /> {quiz.questions?.length || 0} questions
            </span>
            {attemptsInfo && !attemptsInfo.unlimited && (
              <span className="text-neutral-500">
                <AstraSymbol value="🔄" /> {attemptsInfo.used}/{attemptsInfo.max} attempts
              </span>
            )}
            {attemptsInfo?.unlimited && (
              <span className="text-neutral-500"><AstraSymbol value="🔄" /> Unlimited attempts</span>
            )}
          </div>
        </div>

        {submitted && (
          <div className="mb-8">
            {lateSubmission && (
              <div className="mb-4 p-4 rounded-xl border-2 border-red-600 bg-red-900/30 text-red-200 flex items-start gap-3">
                <span className="text-xl">⏰</span>
                <div>
                  <p className="font-semibold">Submitted late</p>
                  <p className="text-sm text-red-300">
                    The deadline passed before you submitted — only answers
                    already saved by then were scored.
                  </p>
                </div>
              </div>
            )}
            {pendingReview && (
              <div className="mb-4 p-4 rounded-xl border-2 border-amber-500 bg-amber-900/20 text-amber-200 flex items-start gap-3">
                <span className="text-xl"><AstraSymbol value="📝" /></span>
                <div>
                  <p className="font-semibold">Awaiting instructor review</p>
                  <p className="text-sm text-amber-300">
                    One or more essay/open-ended answers still need to be graded
                    by your instructor. The score below reflects only the
                    auto-graded portion and is not final yet.
                  </p>
                </div>
              </div>
            )}
            {/* Results Screen with Percentage Meter */}
            <div
              className={cn(
                "p-8 rounded-2xl border-2 text-center",
                pendingReview
                  ? "bg-gradient-to-br from-amber-900/40 to-amber-800/20 border-amber-600"
                  : score >= quiz.passingScore
                    ? "bg-gradient-to-br from-green-900/40 to-green-800/20 border-green-600"
                    : "bg-gradient-to-br from-red-900/40 to-red-800/20 border-red-600",
              )}
            >
              <h2 className="text-3xl font-bold mb-4">
                {pendingReview
                  ? "📝 Submitted for review"
                  : score >= quiz.passingScore
                    ? "🎉 Congratulations!"
                    : "📚 Keep Learning"}
              </h2>

              {/* Circular Percentage Meter */}
              <div className="relative w-48 h-48 mx-auto mb-6">
                <svg className="w-full h-full transform -rotate-90">
                  <circle
                    cx="96"
                    cy="96"
                    r="88"
                    stroke="currentColor"
                    strokeWidth="12"
                    fill="none"
                    className="text-neutral-700"
                  />
                  <circle
                    cx="96"
                    cy="96"
                    r="88"
                    stroke="currentColor"
                    strokeWidth="12"
                    fill="none"
                    strokeDasharray={`${2 * Math.PI * 88}`}
                    strokeDashoffset={`${2 * Math.PI * 88 * (1 - score / 100)}`}
                    className={
                      pendingReview
                        ? "text-amber-500"
                        : score >= quiz.passingScore
                          ? "text-green-500"
                          : "text-red-500"
                    }
                    strokeLinecap="round"
                  />
                </svg>
                <div className="absolute inset-0 flex items-center justify-center">
                  <div>
                    <div className="text-5xl font-bold">
                      {score.toFixed(0)}%
                    </div>
                    <div className="text-sm text-neutral-400 mt-1">
                      {pendingReview ? "Auto-graded so far" : "Your Score"}
                    </div>
                  </div>
                </div>
              </div>

              <div className="space-y-2 mb-6">
                <p className="text-lg">
                  {pendingReview ? (
                    <span className="text-amber-400"><AstraSymbol value="⏳" /> Awaiting review</span>
                  ) : (
                    <span
                      className={
                        score >= quiz.passingScore
                          ? "text-green-400"
                          : "text-red-400"
                      }
                    >
                      {score >= quiz.passingScore
                        ? "✅ Passed!"
                        : "❌ Not Passed"}
                    </span>
                  )}
                </p>
                <p className="text-neutral-300">
                  {previousAttempt
                    ? `${previousAttempt.earned_marks}/${previousAttempt.total_marks}`
                    : `${Math.round((score / 100) * quiz.questions.length)}/${quiz.questions.length}`}{" "}
                  correct answers
                </p>
                <p className="text-sm text-neutral-400">
                  Passing grade: {quiz.passingScore}%
                </p>
                {attemptsInfo && !attemptsInfo.unlimited && (
                  <p className="text-sm text-neutral-400">
                    Attempts: {attemptsInfo.used}/{attemptsInfo.max}{" "}
                    {attemptsInfo.remaining > 0 &&
                      `(${attemptsInfo.remaining} remaining)`}
                  </p>
                )}
                {attemptsInfo?.unlimited && (
                  <p className="text-sm text-neutral-400">
                    Unlimited attempts available
                  </p>
                )}
              </div>

              {/* Action Buttons */}
              <div className="flex gap-3 justify-center flex-wrap">
                {/* Retry Button - only if failed, not pending review, and attempts remaining.
                    A pending_review attempt already counts toward max_attempts server-side —
                    retrying isn't the right next step while a grade is pending. */}
                {!pendingReview &&
                  score < quiz.passingScore &&
                  attemptsInfo &&
                  (attemptsInfo.remaining > 0 || attemptsInfo.unlimited) && (
                    <Button
                      onClick={handleRetry}
                      size="lg"
                      variant="outline"
                      className="px-6 border-primary-500 text-primary-400 hover:bg-primary-900/30"
                    >
                      <AstraSymbol value="🔄" /> Retry Quiz
                      {!attemptsInfo.unlimited &&
                        ` (${attemptsInfo.remaining} left)`}
                    </Button>
                  )}
                {/* Next Lesson Button - only if passed (not while pending review) */}
                {onNext && !pendingReview && score >= quiz.passingScore && (
                  <Button onClick={onNext} size="lg" className="px-8">
                    Next Lesson →
                  </Button>
                )}
                {/* No attempts remaining message */}
                {score < quiz.passingScore &&
                  attemptsInfo &&
                  attemptsInfo.remaining === 0 &&
                  !attemptsInfo.unlimited && (
                    <p className="text-red-400 text-sm">
                      No attempts remaining. Contact your instructor.
                    </p>
                  )}
              </div>
            </div>
          </div>
        )}

        <div className="space-y-6">
          {quiz.questions?.map((question: any, index: number) => {
            const userAnswer = answers[question.id];
            const isCorrect =
              submitted &&
              (question.type === "multiple_choice"
                ? userAnswer === question.correctAnswer
                : question.type === "true_false"
                  ? userAnswer === question.correctAnswer
                  : question.type === "fill_in_blank"
                    ? String(userAnswer || "")
                        .trim()
                        .toLowerCase() ===
                      String(question.correctAnswer || "")
                        .trim()
                        .toLowerCase()
                    : null);

            return (
              <div key={question.id} className="bg-neutral-800 rounded-lg p-6">
                <div className="flex items-start gap-3 mb-4">
                  <span className="text-primary-500 font-bold">
                    Q{index + 1}
                  </span>
                  <div className="flex-1">
                    {question.type !== "fill_in_blank" && (
                      <p className="text-lg font-medium">{question.question}</p>
                    )}
                    <span className="text-sm text-neutral-500">
                      {question.points} points
                    </span>
                  </div>
                  {submitted && (
                    <span
                      className={cn(
                        "text-2xl",
                        isCorrect ? "text-green-500" : "text-red-500",
                      )}
                    >
                      {isCorrect ? "✓" : "✗"}
                    </span>
                  )}
                </div>

                {question.type === "multiple_choice" && (
                  <div className="space-y-2">
                    {question.options?.map(
                      (option: string, optIndex: number) => (
                        <label
                          key={optIndex}
                          className={cn(
                            "block p-3 rounded-lg border-2 cursor-pointer transition-all",
                            submitted
                              ? optIndex === question.correctAnswer
                                ? "border-green-500 bg-green-900/30"
                                : userAnswer === optIndex
                                  ? "border-red-500 bg-red-900/30"
                                  : "border-neutral-700"
                              : userAnswer === optIndex
                                ? "border-primary-500 bg-primary-900/30"
                                : "border-neutral-700 hover:border-neutral-600",
                          )}
                        >
                          <input
                            type="radio"
                            name={`question-${question.id}`}
                            value={optIndex}
                            checked={userAnswer === optIndex}
                            onChange={() =>
                              !submitted &&
                              handleAnswerChange(question.id, optIndex)
                            }
                            disabled={submitted}
                            className="mr-3"
                          />
                          {option}
                        </label>
                      ),
                    )}
                  </div>
                )}

                {question.type === "true_false" && (
                  <div className="space-y-2">
                    {["true", "false"].map((option) => (
                      <label
                        key={option}
                        className={cn(
                          "block p-3 rounded-lg border-2 cursor-pointer transition-all",
                          submitted
                            ? option === question.correctAnswer
                              ? "border-green-500 bg-green-900/30"
                              : userAnswer === option
                                ? "border-red-500 bg-red-900/30"
                                : "border-neutral-700"
                            : userAnswer === option
                              ? "border-primary-500 bg-primary-900/30"
                              : "border-neutral-700 hover:border-neutral-600",
                        )}
                      >
                        <input
                          type="radio"
                          name={`question-${question.id}`}
                          value={option}
                          checked={userAnswer === option}
                          onChange={() =>
                            !submitted &&
                            handleAnswerChange(question.id, option)
                          }
                          disabled={submitted}
                          className="mr-3"
                        />
                        {option.charAt(0).toUpperCase() + option.slice(1)}
                      </label>
                    ))}
                  </div>
                )}

                {/* Fill in the Blank */}
                {question.type === "fill_in_blank" && (
                  <div className="space-y-3">
                    {question.question.includes("___") ? (
                      // Question has blank placeholders
                      <div className="flex flex-wrap items-center gap-1 text-base leading-loose">
                        {question.question
                          .split(/_{3,}/gi)
                          .map((part: string, i: number, arr: string[]) => (
                            <span
                              key={i}
                              className="flex items-center gap-1 flex-wrap"
                            >
                              <span className="text-white">{part}</span>
                              {i < arr.length - 1 &&
                                (submitted ? (
                                  <span
                                    className={cn(
                                      "inline-block px-3 py-1 rounded border-2 text-sm font-medium min-w-[100px] text-center",
                                      userAnswer?.toString().toLowerCase() ===
                                        question.correctAnswer
                                          ?.toString()
                                          .toLowerCase()
                                        ? "border-green-500 bg-green-900/30 text-green-300"
                                        : "border-red-500 bg-red-900/30 text-red-300",
                                    )}
                                  >
                                    {Array.isArray(userAnswer)
                                      ? userAnswer[i]
                                      : userAnswer}
                                  </span>
                                ) : (
                                  <input
                                    type="text"
                                    value={
                                      Array.isArray(userAnswer)
                                        ? userAnswer[i] || ""
                                        : i === 0
                                          ? userAnswer || ""
                                          : ""
                                    }
                                    onChange={(e) => {
                                      const prev = Array.isArray(userAnswer)
                                        ? [...userAnswer]
                                        : [userAnswer || ""];
                                      while (prev.length <= i) prev.push("");
                                      prev[i] = e.target.value;
                                      handleAnswerChange(
                                        question.id,
                                        prev.length === 1 ? prev[0] : prev,
                                      );
                                    }}
                                    placeholder="type here"
                                    className="border-b-2 border-orange-400 outline-none px-2 py-1 min-w-[120px] bg-neutral-700 rounded text-center text-sm font-medium text-white placeholder-neutral-400 focus:border-orange-300"
                                  />
                                ))}
                            </span>
                          ))}
                      </div>
                    ) : (
                      // Fallback: plain question text with single input field
                      <>
                        <p className="text-lg font-medium mb-3">
                          {question.question}
                        </p>
                        {submitted ? (
                          <div
                            className={cn(
                              "inline-block px-4 py-2 rounded border-2 text-base font-medium",
                              userAnswer?.toString().toLowerCase() ===
                                question.correctAnswer?.toString().toLowerCase()
                                ? "border-green-500 bg-green-900/30 text-green-300"
                                : "border-red-500 bg-red-900/30 text-red-300",
                            )}
                          >
                            {userAnswer || "(no answer)"}
                          </div>
                        ) : (
                          <input
                            type="text"
                            value={userAnswer || ""}
                            onChange={(e) =>
                              handleAnswerChange(question.id, e.target.value)
                            }
                            placeholder="Type your answer here..."
                            className="w-full max-w-md px-4 py-2 border-2 border-orange-400 rounded-lg bg-neutral-700 text-white placeholder-neutral-400 focus:border-orange-300 focus:outline-none"
                          />
                        )}
                      </>
                    )}
                  </div>
                )}
                {/* Show correct answer and explanation after submission */}
                {submitted && (
                  <div className="mt-4 space-y-3">
                    {/* Show correct answer for wrong answers */}
                    {!isCorrect && question.correctAnswer && (
                      <div className="p-4 bg-green-900/20 border border-green-700/50 rounded-lg">
                        <p className="text-sm font-semibold text-green-300 mb-1">
                          ✓ Correct Answer:
                        </p>
                        <p className="text-sm text-green-100">
                          {question.type === "multiple_choice"
                            ? question.options?.[question.correctAnswer]
                            : typeof question.correctAnswer === "string"
                              ? question.correctAnswer.charAt(0).toUpperCase() +
                                question.correctAnswer.slice(1)
                              : question.correctAnswer}
                        </p>
                      </div>
                    )}
                    {/* Show explanation if available */}
                    {question.explanation && (
                      <div className="p-4 bg-blue-900/30 border border-blue-700 rounded-lg">
                        <p className="text-sm font-semibold text-blue-300 mb-1">
                          <AstraSymbol value="💡" /> Explanation:
                        </p>
                        <p className="text-sm text-blue-100">
                          {question.explanation}
                        </p>
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>

        {!submitted && (
          <div className="mt-8 flex justify-center">
            <Button
              onClick={handleSubmit}
              size="lg"
              className="px-8"
              disabled={
                Object.keys(answers).length !== quiz.questions?.length ||
                submitting
              }
            >
              {submitting ? "Submitting..." : "Submit Quiz"}
            </Button>
          </div>
        )}
      </div>
    </div>
  );
};

// Assignment Renderer Component
const AssignmentRenderer: React.FC<{
  assignmentId: number;
  courseId: number;
  onNext?: () => void;
}> = ({ assignmentId, courseId, onNext }) => {
  const [assignment, setAssignment] = React.useState<any>(null);
  const [submission, setSubmission] = React.useState<string>("");
  const [files, setFiles] = React.useState<File[]>([]);
  const [submitted, setSubmitted] = React.useState(false);
  const [startDate, setStartDate] = React.useState<Date | null>(null);
  const [submitting, setSubmitting] = React.useState(false);

  React.useEffect(() => {
    const loadAssignment = async () => {
      try {
        // Load assignment data
        const response = await api.get(
          `/courses/${courseId}/assignments/${assignmentId}`,
        );
        setAssignment(response.data);

        // Check if already submitted or returned
        if (response.data.isSubmitted && response.data.submission) {
          const isReturned = response.data.submission.status === "returned";
          setSubmitted(!isReturned); // Allow resubmission if returned
          setSubmission(response.data.submission.textContent || "");
        }

        // Set start date (when student first opens assignment)
        const savedStartDate = localStorage.getItem(
          `assignment_start_${assignmentId}`,
        );
        if (savedStartDate) {
          setStartDate(new Date(savedStartDate));
        } else {
          const now = new Date();
          setStartDate(now);
          localStorage.setItem(
            `assignment_start_${assignmentId}`,
            now.toISOString(),
          );
        }
      } catch (error) {
        console.error("Failed to load assignment:", error);
        toast.error("Failed to load assignment");
      }
    };
    loadAssignment();
  }, [assignmentId, courseId]);

  const handleSubmit = async () => {
    if (submitting) return;
    setSubmitting(true);
    try {
      // Upload the selected files first — the submit endpoint expects
      // uploaded file descriptors, not raw File objects (same mechanism as
      // the standalone assignment-submission page). Previously files were
      // silently dropped (`files: []`).
      const uploadedFiles: Array<{
        id: string;
        name: string;
        url: string;
        size: number;
        type: string;
      }> = [];
      for (const file of files) {
        const response = await uploadDocument(file);
        uploadedFiles.push({
          id: response.filename,
          name: response.original_filename,
          url: response.file_url,
          size: response.size,
          type: response.content_type,
        });
      }

      await api.post(`/assignments/${assignmentId}/submit`, {
        textContent: submission,
        files: uploadedFiles,
      });
      setSubmitted(true);
      toast.success("Assignment submitted successfully!");
    } catch (error: any) {
      toast.error(
        error.response?.data?.detail || "Failed to submit assignment",
      );
    } finally {
      setSubmitting(false);
    }
  };

  if (!assignment) {
    return (
      <div className="flex items-center justify-center h-full bg-neutral-900 text-white">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    );
  }

  // Parse due date from API
  const dueDate = assignment.dueDate ? new Date(assignment.dueDate) : null;
  const daysRemaining = dueDate
    ? Math.ceil(
        (dueDate.getTime() - new Date().getTime()) / (1000 * 60 * 60 * 24),
      )
    : null;

  const isReturned = assignment.submission?.status === "returned";

  return (
    <div className="h-full overflow-y-auto bg-neutral-900 text-white p-8">
      <div className="max-w-4xl mx-auto">
        {/* Returned Assignment Alert */}
        {isReturned && (
          <div className="bg-red-900/30 border-l-4 border-red-500 rounded-lg p-6 mb-6">
            <div className="flex items-start gap-4">
              <div className="flex-shrink-0">
                <svg
                  className="w-8 h-8 text-red-400"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                  />
                </svg>
              </div>
              <div className="flex-1">
                <h3 className="text-lg font-semibold text-red-400 mb-2">
                  Assignment Returned for Revision
                </h3>
                <p className="text-red-200 mb-4">
                  Your submission has been returned by the instructor. Please
                  review the feedback below and resubmit.
                </p>
                {assignment.submission?.feedback && (
                  <div className="bg-neutral-800 rounded-lg p-4 border border-red-700">
                    <p className="text-sm font-semibold text-white mb-2">
                      Instructor Feedback:
                    </p>
                    <p className="text-sm text-neutral-300">
                      {assignment.submission.feedback}
                    </p>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        <div className="mb-8">
          <h1 className="text-3xl font-bold mb-2">{assignment.title}</h1>
          <p className="text-neutral-400 mb-4">{assignment.description}</p>

          <div className="bg-neutral-800 rounded-lg p-4 mb-6">
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <span className="text-neutral-500">Started:</span>
                <p className="font-medium">{startDate?.toLocaleDateString()}</p>
              </div>
              <div>
                <span className="text-neutral-500">Due Date:</span>
                <p
                  className={cn(
                    "font-medium",
                    daysRemaining && daysRemaining < 2
                      ? "text-red-400"
                      : "text-white",
                  )}
                >
                  {dueDate?.toLocaleDateString()}
                  {daysRemaining !== null && (
                    <span className="text-xs ml-2">
                      (
                      {daysRemaining > 0
                        ? `${daysRemaining} days left`
                        : "Overdue"}
                      )
                    </span>
                  )}
                </p>
              </div>
              <div>
                <span className="text-neutral-500">Points:</span>
                <p className="font-medium">{assignment.totalPoints}</p>
              </div>
              <div>
                <span className="text-neutral-500">Submission Type:</span>
                <p className="font-medium capitalize">
                  {assignment.submissionType}
                </p>
              </div>
            </div>
          </div>

          <div className="prose prose-invert max-w-none mb-6">
            <h2 className="text-xl font-semibold mb-3">Instructions</h2>
            <div
              dangerouslySetInnerHTML={{
                __html: sanitizeHtml(
                  assignment.instructions || "No instructions provided.",
                ),
              }}
            />
          </div>

          {/* Reference Files from Instructor */}
          {assignment.attachments && assignment.attachments.length > 0 && (
            <div className="bg-neutral-800 rounded-lg p-6 mb-6">
              <h2 className="text-xl font-semibold mb-4">Reference Files</h2>
              <div className="space-y-3">
                {assignment.attachments.map((file: any, index: number) => {
                  const fileUrl = typeof file === "string" ? file : file.url;
                  const fileName =
                    typeof file === "string"
                      ? file.split("/").pop()
                      : file.name;
                  const fileSize =
                    typeof file === "object" && file.size
                      ? file.size < 1024
                        ? `${file.size} B`
                        : file.size < 1024 * 1024
                          ? `${(file.size / 1024).toFixed(1)} KB`
                          : `${(file.size / (1024 * 1024)).toFixed(1)} MB`
                      : "";
                  const fullUrl = fileUrl.startsWith("http")
                    ? fileUrl
                    : getBackendUrl(fileUrl);

                  return (
                    <a
                      key={index}
                      href={fullUrl}
                      download
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center justify-between p-4 bg-neutral-700 hover:bg-neutral-600 rounded-lg transition-colors"
                    >
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 bg-primary-600 rounded-lg flex items-center justify-center">
                          <svg
                            className="w-5 h-5"
                            fill="none"
                            stroke="currentColor"
                            viewBox="0 0 24 24"
                          >
                            <path
                              strokeLinecap="round"
                              strokeLinejoin="round"
                              strokeWidth={2}
                              d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z"
                            />
                          </svg>
                        </div>
                        <div>
                          <p className="font-medium text-white">{fileName}</p>
                          {fileSize && (
                            <p className="text-sm text-neutral-400">
                              {fileSize}
                            </p>
                          )}
                        </div>
                      </div>
                      <svg
                        className="w-5 h-5 text-neutral-400"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"
                        />
                      </svg>
                    </a>
                  );
                })}
              </div>
            </div>
          )}
        </div>

        {!submitted ? (
          <div className="space-y-6">
            {(assignment.submissionType === "text" ||
              assignment.submissionType === "both") && (
              <div>
                <label className="block text-sm font-medium mb-2">
                  Your Submission
                </label>
                <textarea
                  value={submission}
                  onChange={(e) => setSubmission(e.target.value)}
                  rows={10}
                  className="w-full px-4 py-3 bg-neutral-800 border border-neutral-700 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                  placeholder="Write your submission here..."
                />
              </div>
            )}

            {(assignment.submissionType === "file" ||
              assignment.submissionType === "both") && (
              <div>
                <label className="block text-sm font-medium mb-2">
                  Upload Files
                </label>
                <input
                  type="file"
                  multiple
                  onChange={(e) => setFiles(Array.from(e.target.files || []))}
                  className="w-full px-4 py-3 bg-neutral-800 border border-neutral-700 rounded-lg"
                />
                <p className="text-xs text-neutral-500 mt-2">
                  Max {assignment.maxFiles} files, {assignment.maxFileSize}MB
                  each
                </p>
              </div>
            )}

            <Button
              onClick={handleSubmit}
              size="lg"
              className="w-full"
              disabled={submitting || (!submission && files.length === 0)}
            >
              {submitting ? "Submitting..." : "Submit Assignment"}
            </Button>
          </div>
        ) : (
          <div className="bg-green-900/30 border border-green-700 rounded-lg p-6 text-center">
            <CheckCircle className="w-16 h-16 text-green-500 mx-auto mb-4" />
            <h2 className="text-2xl font-bold mb-2">Assignment Submitted!</h2>
            <p className="text-neutral-400 mb-6">
              Your assignment has been submitted for grading.
            </p>
            {onNext && (
              <Button onClick={onNext} size="lg" className="px-8">
                Next Lesson →
              </Button>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export const LessonPageRedesigned = () => {
  const { courseId, lessonId, id } = useParams<{
    courseId?: string;
    lessonId?: string;
    id?: string;
  }>();
  const navigate = useNavigate();
  const currentCourseId = id || courseId;
  useTheme();

  // State
  const [lesson, setLesson] = React.useState<any>(null);
  const [course, setCourse] = React.useState<any>(null);

  // Use numeric course.id from API response when available, fallback to URL param
  const numericCourseId = React.useMemo(
    () =>
      course?.id || (currentCourseId ? parseInt(currentCourseId) : undefined),
    [course?.id, currentCourseId],
  );

  const [loading, setLoading] = React.useState(true);
  const [sidebarOpen, setSidebarOpen] = React.useState(() => {
    // Start with sidebar closed on mobile, open on desktop
    if (typeof window !== "undefined") {
      return window.innerWidth >= 1024; // lg breakpoint
    }
    return true;
  });
  const [showAutoAdvance, setShowAutoAdvance] = React.useState(false);
  const [autoAdvanceCountdown, setAutoAdvanceCountdown] = React.useState(5);
  const autoAdvanceTimerRef = React.useRef<any>(null);
  const [certificateAvailable, setCertificateAvailable] = React.useState(false);
  const [showCertificateBanner, setShowCertificateBanner] =
    React.useState(true);

  // Video player state
  const [isPlaying, setIsPlaying] = React.useState(false);
  const [audioSrc, setAudioSrc] = React.useState<string | null>(null); // roadmap item 9: audio-only rendition
  const [isMuted, setIsMuted] = React.useState(false);
  const [progress, setProgress] = React.useState(0);
  const [courseProgress, setCourseProgress] = React.useState(0);
  const [duration, setDuration] = React.useState(0);
  const [currentTime, setCurrentTime] = React.useState(0);
  const [playbackRate] = React.useState(1);
  const playerRef = React.useRef<VideoPlayerHandle>(null);

  // Enhanced features state
  const [notes, setNotes] = React.useState<
    Array<{ timestamp: number; content: string; id: string }>
  >([]);
  const [showNotesPanel, setShowNotesPanel] = React.useState(false);
  const [currentNote, setCurrentNote] = React.useState("");
  const [showKeyboardShortcuts, setShowKeyboardShortcuts] =
    React.useState(false);
  const [, setIsPiPMode] = React.useState(false);
  const [showQualitySelector, setShowQualitySelector] = React.useState(false);
  const [showThemeSwitcher, setShowThemeSwitcher] = React.useState(false);

  // Quiz/Checkpoint state
  const [checkpoints] = React.useState<
    Array<{
      timestamp: number;
      question: string;
      options: string[];
      correctAnswer: number;
      explanation: string;
    }>
  >([]);
  const [activeCheckpoint, setActiveCheckpoint] = React.useState<any>(null);
  const [, setSelectedAnswer] = React.useState<number | null>(null);
  const [, setCheckpointAnswered] = React.useState(false);

  // Advanced features state
  const [ambientLighting] = React.useState(true);
  const [, setShowAchievement] = React.useState<{
    title: string;
    description: string;
    icon: string;
  } | null>(null);
  // Shape of the current stream. Lessons filmed at 4:3 (or any non-16:9 ratio)
  // used to sit letterboxed inside a fixed 16:9 stage, which wasted most of the
  // screen; the stage follows the real ratio once the metadata has loaded.
  const [videoAspect, setVideoAspect] = React.useState<number | null>(null);
  const toggleMute = useCallback(() => setIsMuted(!isMuted), [isMuted]);
  const skipTime = useCallback(
    (seconds: number) => {
      if (playerRef.current && duration > 0) {
        const newTime = Math.max(0, Math.min(currentTime + seconds, duration));
        playerRef.current.seekTo(newTime);
      }
    },
    [currentTime, duration],
  );
  const handleSeek = useCallback(
    (seconds: number) => {
      if (playerRef.current && duration > 0) {
        // Use absolute seconds for video player
        playerRef.current.seekTo(seconds);
      } else {
        console.warn("Cannot seek, duration invalid:", duration);
      }
    },
    [duration],
  );
  const handlePlayPause = useCallback(
    () => setIsPlaying(!isPlaying),
    [isPlaying],
  );
  React.useEffect(() => {
    setVideoAspect(null);
  }, [lessonId]);
  const videoContainerRef = React.useRef<HTMLDivElement>(null);
  const sidebarRef = React.useRef<HTMLDivElement>(null);
  const activeItemRef = React.useRef<HTMLButtonElement>(null);

  // Fetch course and lesson data
  const courseLoaded = React.useRef(false);
  const fetchCourse = React.useCallback(async () => {
    try {
      if (!courseLoaded.current) setLoading(true);
      const api = (await import("@/api/axios")).api;

      if (!currentCourseId) {
        console.error("No course ID provided");
        return;
      }

      const courseResponse = await api.get(
        `/courses/${numericCourseId || currentCourseId}`,
      );
      const courseData = courseResponse.data;

      // Combine lessons, quizzes, and assignments into course content
      const allContent = [
        ...(courseData.lessons || []).map((l: any) => ({
          ...l,
          type: "lesson",
          contentId: `lesson-${l.id}`,
        })),
        ...(courseData.quizzes || []).map((q: any) => ({
          ...q,
          type: "quiz",
          lesson_title: q.title,
          contentId: `quiz-${q.id}`,
        })),
        ...(courseData.assignments || []).map((a: any) => ({
          ...a,
          type: "assignment",
          lesson_title: a.title,
          contentId: `assignment-${a.id}`,
        })),
      ];

      // Sort by creation date to maintain chronological order
      allContent.sort((a, b) => {
        const dateA = new Date(a.created_at || a.post_date || 0).getTime();
        const dateB = new Date(b.created_at || b.post_date || 0).getTime();
        return dateA - dateB;
      });

      // Build sections from sections_meta if available
      let courseSections: any[] = [];
      if (courseData.sections_meta) {
        try {
          const meta = JSON.parse(courseData.sections_meta);
          const contentMap = new Map(
            allContent.map((c: any) => [c.contentId, c]),
          );
          // Normalize lectureIds - add prefix if missing
          const normalizeLid = (lid: string) => {
            if (
              lid.startsWith("lesson-") ||
              lid.startsWith("quiz-") ||
              lid.startsWith("assignment-")
            )
              return lid;
            return "lesson-" + lid;
          };
          courseSections = meta
            .map((s: any) => ({
              id: s.id,
              title: s.title,
              description: s.description,
              lessons: (s.lectureIds || [])
                .map((lid: string) => contentMap.get(normalizeLid(lid)))
                .filter(Boolean),
            }))
            .filter((s: any) => s.lessons.length > 0);
          // Add orphan lessons to last section or new section
          const assignedIds = new Set(
            meta.flatMap((s: any) => s.lectureIds || []),
          );
          const orphans = allContent.filter(
            (c: any) => !assignedIds.has(c.contentId),
          );
          if (orphans.length > 0) {
            if (courseSections.length === 0) {
              courseSections.push({
                id: "default",
                title: "Course Content",
                description: "",
                lessons: orphans,
              });
            } else {
              courseSections[courseSections.length - 1].lessons.push(
                ...orphans,
              );
            }
          }
        } catch {
          courseSections = [];
        }
      }
      if (courseSections.length === 0) {
        courseSections = [
          {
            id: "default",
            title: "Course Content",
            description: "",
            lessons: allContent,
          },
        ];
      }
      // Fetch lesson completion status
      let completedLessonIds: number[] = [];
      let overallProgress = 0;
      try {
        // Use the numeric id the course fetch just returned. currentCourseId is
        // the slug (e.g. "react-js-mastery-tamil") and numericCourseId is still
        // NaN on first load, so either would make /progress 422 (expects an int).
        const progressRes = await api.get(`/courses/${courseData.id}/progress`);
        completedLessonIds = progressRes.data?.completed_lesson_ids || [];
        overallProgress = progressRes.data?.overall_progress || 0;
        // Mark completed lessons
        allContent.forEach((c: any) => {
          if (c.type === "lesson") {
            c.is_completed = completedLessonIds.includes(c.id);
          }
        });
      } catch {}
      setCourseProgress(overallProgress);
      setCourse({
        id: courseData.id,
        title: courseData.title,
        lessons: allContent,
        sections: courseSections,
      });

      // Check for certificate availability
      if (courseData.progress === 100 && courseData.enrollment_date) {
        try {
          // Real route is /certificates/course/{course_id} (404 when not issued);
          // it returns the certificate object itself, not a { certificate } wrapper.
          const certResponse = await api.get(
            `/certificates/course/${courseData.id}`,
          );
          if (certResponse.data && certResponse.data.id) {
            setCertificateAvailable(true);
          }
        } catch (error) {
          // Certificate not available yet or error
        }
      }
      if (!lessonId && allContent.length > 0) {
        const firstContent = allContent[0];
        const targetId = numericCourseId || currentCourseId;
        if (!targetId) {
          console.error("No course ID available for initial navigation");
          return;
        }
        navigate(`/courses/${targetId}/lessons/${firstContent.contentId}`, {
          replace: true,
        });
        return;
      }

      if (lessonId && allContent.length > 0) {
        // Match by contentId (e.g., "quiz-1", "assignment-1", "lesson-1")
        let currentLesson = allContent.find(
          (l: any) => l.contentId === lessonId,
        );

        // Fallback: if lessonId is just a number (old format), try to find by ID and type
        if (!currentLesson) {
          currentLesson = allContent.find(
            (l: any) => l.id === parseInt(lessonId) && l.type === "lesson",
          );
        }

        if (currentLesson) {
          // Store the current lesson type for rendering
          const videoUrl = currentLesson.lesson_video || "";
          const youtubeUrl = currentLesson.youtube_url || "";
          const fullVideoUrl = videoUrl.startsWith("/")
            ? getBackendUrl(videoUrl)
            : videoUrl;

          // Prefer direct video uploads over YouTube URLs
          const primaryVideoUrl = fullVideoUrl || youtubeUrl;

          setLesson({
            id: currentLesson.id,
            title: currentLesson.lesson_title || currentLesson.title,
            description:
              currentLesson.lesson_content || "No description available",
            video_url: primaryVideoUrl,
            youtube_url: youtubeUrl,
            // Reflect real completion so the "Mark as Complete" button and a
            // re-opened lesson show the correct state (was hardcoded false).
            is_completed:
              currentLesson.is_completed ||
              completedLessonIds.includes(currentLesson.id),
            is_preview: currentLesson.is_preview || false,
            type: currentLesson.type || "lesson",
            attachment_url: currentLesson.attachment_url || "",
            // H5P interactive-content support (spec B6/B7, plan Task 5).
            // "video" (default) keeps the existing VideoPlayer path.
            lesson_content_type: currentLesson.lesson_content_type || "video",
            h5p_content_id: currentLesson.h5p_content_id ?? null,
            h5p_public_id: currentLesson.h5p_public_id ?? null,
            // Learning-game support (spec §5, plan Task 6 backend serializes
            // these on the lesson payload).
            game_id: currentLesson.game_id ?? null,
            game_title: currentLesson.game_title ?? null,
            // GeoGebra / 3D / virtual-lab handles — the player branches below read
            // these off `lesson`, so they must be copied here (were missing → every
            // such lesson fell through to "No Video Available").
            geogebra_applet_id: currentLesson.geogebra_applet_id ?? null,
            three_d_model_id: currentLesson.three_d_model_id ?? null,
            virtual_lab_sim: currentLesson.virtual_lab_sim ?? null,
            content: currentLesson,
          });
        }
      }
    } catch (error) {
      console.error("Error fetching course/lesson data:", error);
      toast.error("Failed to load lesson");
    } finally {
      courseLoaded.current = true;
      setLoading(false);
    }
  }, [currentCourseId, numericCourseId, lessonId, navigate]);

  React.useEffect(() => {
    fetchCourse();
  }, [fetchCourse]);

  // Save sidebar scroll position before lessonId change and restore after
  const sidebarScrollPos = React.useRef(0);

  // Save scroll position when user scrolls sidebar
  React.useEffect(() => {
    const sidebar = sidebarRef.current;
    if (!sidebar) return;
    const onScroll = () => {
      sidebarScrollPos.current = sidebar.scrollTop;
    };
    sidebar.addEventListener("scroll", onScroll, { passive: true });
    return () => sidebar.removeEventListener("scroll", onScroll);
  }, []);

  // Restore scroll position after EVERY render synchronously
  React.useLayoutEffect(() => {
    if (sidebarRef.current && sidebarScrollPos.current > 0) {
      sidebarRef.current.scrollTop = sidebarScrollPos.current;
    }
  });

  // When lessonId changes, update active lesson from cached course data
  React.useEffect(() => {
    if (!lessonId || !course) return;
    const allContent = course.lessons || [];
    let currentLesson = allContent.find((l: any) => l.contentId === lessonId);
    if (!currentLesson) {
      currentLesson = allContent.find(
        (l: any) => l.id === parseInt(lessonId) && l.type === "lesson",
      );
    }
    if (currentLesson) {
      const videoUrl = currentLesson.lesson_video || "";
      const youtubeUrl = currentLesson.youtube_url || "";
      const fullVideoUrl = videoUrl.startsWith("/")
        ? `${window.location.origin}${videoUrl}`
        : videoUrl;
      const primaryVideoUrl = fullVideoUrl || youtubeUrl;
      setLesson({
        id: currentLesson.id,
        title: currentLesson.lesson_title || currentLesson.title,
        description: currentLesson.lesson_content || "No description available",
        video_url: primaryVideoUrl,
        youtube_url: youtubeUrl,
        // Reflect real completion (was hardcoded false, so a completed lesson
        // re-opened from the sidebar showed as incomplete again).
        is_completed: currentLesson.is_completed || false,
        is_preview: currentLesson.is_preview || false,
        type: currentLesson.type || "lesson",
        attachment_url: currentLesson.attachment_url || "",
        // H5P interactive-content support (spec B6/B7, plan Task 5).
        lesson_content_type: currentLesson.lesson_content_type || "video",
        h5p_content_id: currentLesson.h5p_content_id ?? null,
        h5p_public_id: currentLesson.h5p_public_id ?? null,
        // Learning-game support (spec §5, plan Task 6 backend serializes
        // these on the lesson payload).
        game_id: currentLesson.game_id ?? null,
        game_title: currentLesson.game_title ?? null,
        geogebra_applet_id: currentLesson.geogebra_applet_id ?? null,
        three_d_model_id: currentLesson.three_d_model_id ?? null,
        virtual_lab_sim: currentLesson.virtual_lab_sim ?? null,
        content: currentLesson,
      });
    }
  }, [lessonId, course]);

  // Learning signals (2026-09-06): seeks, replays, pauses, early quits and
  // notes are buffered by api/signals and turned into a per-concept struggle
  // profile server-side. Everything here is best-effort and never throws.
  const signalLessonId = React.useMemo(() => {
    const n = Number(
      String(lessonId || "").replace(/^(lesson|quiz|assignment)-/, ""),
    );
    return Number.isFinite(n) &&
      n > 0 &&
      String(lessonId || "").indexOf("quiz-") !== 0 &&
      String(lessonId || "").indexOf("assignment-") !== 0
      ? n
      : undefined;
  }, [lessonId]);
  const signalCourseId = numericCourseId ? Number(numericCourseId) : undefined;
  const lastTimeRef = React.useRef(0);
  const watchedSegmentsRef = React.useRef<Set<number>>(new Set());
  const passRef = React.useRef(0);
  const seenInPassRef = React.useRef<Map<number, number>>(new Map());
  const quitSentRef = React.useRef(false);
  const progressRef = React.useRef(0);
  progressRef.current = progress;

  // Video controls

  const handleProgress = (state: any) => {
    setProgress(state.played * 100);
    setCurrentTime(state.playedSeconds);
    const t = Number(state.playedSeconds) || 0;
    const last = lastTimeRef.current;
    const seg = Math.floor(t / 10);
    if (signalLessonId && last > 0) {
      if (t < last - 3) {
        passRef.current += 1;
        signal({
          kind: "video_rewind",
          course_id: signalCourseId,
          lesson_id: signalLessonId,
          position_s: Math.round(t),
          value: Math.round(last - t),
        });
      } else if (t > last + 10) {
        signal({
          kind: "video_skip",
          course_id: signalCourseId,
          lesson_id: signalLessonId,
          position_s: Math.round(last),
          value: Math.round(t - last),
        });
      } else if (
        watchedSegmentsRef.current.has(seg) &&
        seenInPassRef.current.get(seg) !== passRef.current
      ) {
        signal({
          kind: "video_replay",
          course_id: signalCourseId,
          lesson_id: signalLessonId,
          position_s: Math.round(t),
        });
      }
    }
    seenInPassRef.current.set(seg, passRef.current);
    watchedSegmentsRef.current.add(seg);
    lastTimeRef.current = t;
  };
  const handleDuration = (duration: number) => setDuration(duration);

  // Issue 8: best-effort watch-event tracking for the Student Activity panel.
  // We remember when the current play segment started so we can report the
  // watched duration on pause/end. Failures are swallowed so a tracking
  // error can never interrupt playback.
  const segmentStartRef = React.useRef<number | null>(null);
  const recordWatchEvent = (
    event: "started" | "paused" | "resumed" | "completed",
  ) => {
    if (!numericCourseId || !lesson?.id) return;
    const now = Date.now();
    let duration = 0;
    if (event === "paused" || event === "completed") {
      if (segmentStartRef.current !== null) {
        duration = Math.max(
          0,
          Math.round((now - segmentStartRef.current) / 1000),
        );
      }
      segmentStartRef.current = null;
      if (event === "paused" && duration >= 2 && signalLessonId) {
        signal({
          kind: "video_pause",
          course_id: signalCourseId,
          lesson_id: signalLessonId,
          position_s: Math.round(currentTime || 0),
          value: duration,
        });
      }
    } else {
      // 'started' or 'resumed' opens a new segment.
      segmentStartRef.current = now;
    }
    api
      .post("/progress/watch-event", {
        lesson_id: Number(lesson.id),
        course_id: Number(numericCourseId),
        event,
        duration_seconds: duration,
        position_seconds: Math.round(currentTime || 0),
      })
      .catch(() => {
        /* best-effort */
      });
  };
  // Early quit: leaving a lesson (route change, tab close) between 5% and
  // 60% of the way through is the strongest "gave up" signal we have.
  React.useEffect(() => {
    quitSentRef.current = false;
    lastTimeRef.current = 0;
    watchedSegmentsRef.current = new Set();
    seenInPassRef.current = new Map();
    passRef.current = 0;
    if (!signalLessonId) return;
    const lid = signalLessonId;
    const cid = signalCourseId;
    const send = () => {
      const p = progressRef.current;
      if (quitSentRef.current || p < 5 || p > 60) return;
      quitSentRef.current = true;
      signal({
        kind: "quit_early",
        course_id: cid,
        lesson_id: lid,
        position_s: Math.round(lastTimeRef.current),
        value: Math.round(p),
      });
      flushSignals();
    };
    window.addEventListener("pagehide", send);
    return () => {
      window.removeEventListener("pagehide", send);
      send();
    };
  }, [signalLessonId, signalCourseId]);
  React.useEffect(() => {
    if (signalLessonId && playbackRate !== 1) {
      signal({
        kind: "rate_change",
        course_id: signalCourseId,
        lesson_id: signalLessonId,
        position_s: Math.round(lastTimeRef.current),
        value: playbackRate,
      });
    }
  }, [playbackRate, signalLessonId, signalCourseId]);

  const toggleFullscreen = () => {
    const elem = document.getElementById("video-container");
    if (elem) {
      if (!document.fullscreenElement) {
        elem.requestFullscreen();
      } else {
        document.exitFullscreen();
      }
    }
  };

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, "0")}`;
  };

  // Notes functionality
  const loadNotes = React.useCallback(() => {
    if (currentCourseId && lessonId) {
      const storedNotes = localStorage.getItem(
        `lesson_notes_${currentCourseId}_${lessonId}`,
      );
      if (storedNotes) {
        setNotes(JSON.parse(storedNotes));
      }
    }
  }, [currentCourseId, lessonId]);

  const saveNotes = React.useCallback(
    (updatedNotes: typeof notes) => {
      if (currentCourseId && lessonId) {
        localStorage.setItem(
          `lesson_notes_${currentCourseId}_${lessonId}`,
          JSON.stringify(updatedNotes),
        );
      }
    },
    [currentCourseId, lessonId],
  );

  const addNote = () => {
    if (currentNote.trim()) {
      const newNote = {
        id: Date.now().toString(),
        timestamp: currentTime,
        content: currentNote.trim(),
      };
      const updatedNotes = [...notes, newNote].sort(
        (a, b) => a.timestamp - b.timestamp,
      );
      setNotes(updatedNotes);
      saveNotes(updatedNotes);
      setCurrentNote("");
      toast.success("Note added!");
      if (signalLessonId)
        signal({
          kind: "note_written",
          course_id: signalCourseId,
          lesson_id: signalLessonId,
          position_s: Math.round(currentTime || 0),
          value: newNote.content.length,
        });
    }
  };

  const deleteNote = (id: string) => {
    const updatedNotes = notes.filter((note) => note.id !== id);
    setNotes(updatedNotes);
    saveNotes(updatedNotes);
    toast.success("Note deleted");
  };

  const jumpToNote = (timestamp: number) => {
    handleSeek(timestamp);
    setIsPlaying(true);
  };

  // Load notes on mount
  React.useEffect(() => {
    loadNotes();
  }, [loadNotes]);
  // Sample checkpoints disabled

  // Record a video view once per lesson open (Issue 1: video view count).
  // Best-effort — failures are swallowed inside courseAPI.recordLessonView.
  React.useEffect(() => {
    if (!courseId || !lessonId) return;
    // lessonId is the contentId (e.g. "lesson-12", "quiz-3") — strip the
    // type prefix so Number() yields the numeric id instead of NaN.
    const numericLessonId = Number(
      lessonId.replace(/^(lesson|quiz|assignment)-/, ""),
    );
    const courseIdNum = Number(courseId);
    if (Number.isFinite(courseIdNum) && Number.isFinite(numericLessonId)) {
      courseAPI.recordLessonView(courseIdNum, numericLessonId);
    }
  }, [courseId, lessonId]);

  // Check for checkpoint triggers during playback
  React.useEffect(() => {
    if (!isPlaying || activeCheckpoint || checkpoints.length === 0) return;

    const currentCheckpoint = checkpoints.find(
      (cp) =>
        Math.abs(currentTime - cp.timestamp) < 0.5 &&
        currentTime >= cp.timestamp,
    );

    if (currentCheckpoint) {
      setActiveCheckpoint(currentCheckpoint);
      setIsPlaying(false);
      setSelectedAnswer(null);
      setCheckpointAnswered(false);
    }
  }, [currentTime, checkpoints, activeCheckpoint, isPlaying]);

  // Speed indicator animation

  // Add reaction animation

  // Focus mode toggle

  // Show achievement
  const showAchievementNotification = (
    title: string,
    description: string,
    icon: string,
  ) => {
    setShowAchievement({ title, description, icon });
    celebrationAnimation();
    setTimeout(() => setShowAchievement(null), 4000);
  };

  // Study assistant suggestions

  // Keyboard shortcuts
  React.useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Ignore if typing in input fields
      if (
        e.target instanceof HTMLInputElement ||
        e.target instanceof HTMLTextAreaElement
      ) {
        return;
      }

      switch (e.key.toLowerCase()) {
        case " ":
        case "k":
          e.preventDefault();
          handlePlayPause();
          break;
        case "j":
          e.preventDefault();
          skipTime(-10);
          break;
        case "l":
          e.preventDefault();
          skipTime(10);
          break;
        case "arrowleft":
          e.preventDefault();
          skipTime(-5);
          break;
        case "arrowright":
          e.preventDefault();
          skipTime(5);
          break;
        case "m":
          e.preventDefault();
          toggleMute();
          break;
        case "f":
          e.preventDefault();
          toggleFullscreen();
          break;
        case "p": {
          e.preventDefault();
          const videoElement = document.querySelector("video");
          if (videoElement && document.pictureInPictureEnabled) {
            if (document.pictureInPictureElement) {
              document.exitPictureInPicture();
              setIsPiPMode(false);
            } else {
              videoElement.requestPictureInPicture();
              setIsPiPMode(true);
            }
          }
          break;
        }
        case "n":
          e.preventDefault();
          setShowNotesPanel(true);
          break;
        case "?":
          e.preventDefault();
          setShowKeyboardShortcuts(true);
          break;
        case "escape":
          if (showKeyboardShortcuts) {
            setShowKeyboardShortcuts(false);
          }
          break;
        default:
          // Number keys 0-9 for seeking
          if (e.key >= "0" && e.key <= "9") {
            e.preventDefault();
            const percentage = parseInt(e.key) * 10;
            const seekTime = (percentage / 100) * duration;
            handleSeek(seekTime);
          }
          break;
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [
    isPlaying,
    duration,
    currentTime,
    showKeyboardShortcuts,
    handlePlayPause,
    skipTime,
    toggleMute,
    handleSeek,
  ]);

  // Close quality selector and theme switcher when clicking outside
  React.useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      const target = e.target as Element;

      // Close quality selector
      if (showQualitySelector && !target.closest("#quality-selector")) {
        setShowQualitySelector(false);
      }

      // Close theme switcher
      if (showThemeSwitcher && !target.closest("#theme-switcher")) {
        setShowThemeSwitcher(false);
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [showQualitySelector, showThemeSwitcher]);

  // Ambient lighting effect
  React.useEffect(() => {
    if (!ambientLighting || !videoContainerRef.current) return;

    const updateAmbientColor = () => {
      const video = videoContainerRef.current?.querySelector("video");
      if (!video) return;

      // Create canvas to sample video colors
      const canvas = document.createElement("canvas");
      const ctx = canvas.getContext("2d");
      if (!ctx) return;

      canvas.width = 50;
      canvas.height = 50;

      try {
        ctx.drawImage(video, 0, 0, 50, 50);
        const imageData = ctx.getImageData(0, 0, 50, 50).data;

        let r = 0,
          g = 0,
          b = 0;
        const len = imageData.length;

        for (let i = 0; i < len; i += 4) {
          r += imageData[i];
          g += imageData[i + 1];
          b += imageData[i + 2];
        }

        r = Math.floor(r / (len / 4));
        g = Math.floor(g / (len / 4));
        b = Math.floor(b / (len / 4));

        document.body.style.background = `radial-gradient(circle at 50% 50%, rgba(${r},${g},${b},0.15) 0%, rgba(0,0,0,1) 70%)`;
      } catch (e) {
        // CORS or other error - ignore
      }
    };

    const interval = setInterval(updateAmbientColor, 500);
    return () => {
      clearInterval(interval);
      document.body.style.background = "";
    };
  }, [ambientLighting, isPlaying]);

  // Video protection - disable dev tools shortcuts and screen capture
  React.useEffect(() => {
    const preventDevTools = (e: KeyboardEvent) => {
      // Prevent F12, Ctrl+Shift+I, Ctrl+Shift+J, Ctrl+U
      if (
        e.key === "F12" ||
        (e.ctrlKey &&
          e.shiftKey &&
          (e.key === "I" || e.key === "J" || e.key === "C")) ||
        (e.ctrlKey && e.key === "u")
      ) {
        e.preventDefault();
        toast.error("Developer tools are disabled for content protection");
        return false;
      }

      // Prevent Print Screen
      if (e.key === "PrintScreen") {
        e.preventDefault();
        toast.error("Screenshots are disabled for content protection");
        return false;
      }
    };

    // Disable right-click on video
    const videoContainer = document.getElementById("video-container");
    const preventContextMenu = (e: Event) => {
      e.preventDefault();
      return false;
    };

    document.addEventListener("keydown", preventDevTools);
    if (videoContainer) {
      videoContainer.addEventListener("contextmenu", preventContextMenu);
    }

    return () => {
      document.removeEventListener("keydown", preventDevTools);
      if (videoContainer) {
        videoContainer.removeEventListener("contextmenu", preventContextMenu);
      }
    };
  }, []);

  // Immediately reflect completion in local state (current lesson + sidebar
  // list) so the checkmark shows without waiting on the refetch to round-trip.
  const markLessonCompleteLocally = (completedId: number) => {
    setLesson((prev: any) =>
      prev && prev.id === completedId ? { ...prev, is_completed: true } : prev,
    );
    setCourse((prev: any) => {
      if (!prev) return prev;
      const mark = (arr: any[]) =>
        (arr || []).map((l: any) =>
          l.id === completedId && (l.type === "lesson" || !l.type)
            ? { ...l, is_completed: true }
            : l,
        );
      return {
        ...prev,
        lessons: mark(prev.lessons),
        sections: (prev.sections || []).map((s: any) => ({
          ...s,
          lessons: mark(s.lessons),
        })),
      };
    });
  };

  const handleMarkComplete = async () => {
    if (!lesson?.id || !currentCourseId) {
      toast.error("Unable to mark lesson as complete");
      return;
    }

    try {
      // Prefer the numeric id; currentCourseId may be the slug (endpoint expects int).
      const response = await api.post(
        `/courses/${numericCourseId || currentCourseId}/lessons/${lesson.id}/complete`,
      );

      markLessonCompleteLocally(lesson.id);
      toast.success("Lesson marked as complete!");
      await fetchCourse();

      if (
        response.data.course_completed &&
        response.data.certificate_available
      ) {
        toast.success("🎉 Congratulations! Course completed!");
      }
    } catch (error: any) {
      toast.error(
        error.response?.data?.detail || "Failed to mark lesson as complete",
      );
    }
  };

  const navigateToLesson = (
    contentIdOrLessonId: string | number,
    lessonType?: string,
  ) => {
    setShowAutoAdvance(false);
    setAutoAdvanceCountdown(5);
    if (autoAdvanceTimerRef.current) {
      clearInterval(autoAdvanceTimerRef.current);
    }

    // Use numeric course ID for navigation
    const targetCourseId = numericCourseId || currentCourseId;
    if (!targetCourseId) {
      console.error("No course ID available for navigation");
      return;
    }
    // Close sidebar on mobile after selecting a lesson
    if (typeof window !== "undefined" && window.innerWidth < 1024) {
      setSidebarOpen(false);
    }
    // All content types (lessons, quizzes, assignments) now use the same route for inline rendering
    // Use contentId if it's a string (e.g., "quiz-1"), otherwise construct it from type and ID
    let contentId: string;
    if (typeof contentIdOrLessonId === "string") {
      contentId = contentIdOrLessonId;
    } else {
      contentId = lessonType
        ? `${lessonType}-${contentIdOrLessonId}`
        : `lesson-${contentIdOrLessonId}`;
    }
    // Save scroll position right before navigation
    if (sidebarRef.current) {
      sidebarScrollPos.current = sidebarRef.current.scrollTop;
    }
    navigate(`/courses/${targetCourseId}/lessons/${contentId}`);
  };

  const handleNextLesson = () => {
    if (!course || !course.lessons || !lessonId) return;

    const currentIndex = course.lessons.findIndex(
      (l: any) => l.contentId === lessonId,
    );
    if (currentIndex === -1) {
      toast.error("Current lesson not found in course");
      return;
    }
    if (currentIndex >= course.lessons.length - 1) {
      toast.success("🎉 You have completed all content in this course!");
      return;
    }

    const nextLesson = course.lessons[currentIndex + 1];
    navigateToLesson(nextLesson.contentId);
  };

  const startAutoAdvance = () => {
    if (!course || !course.lessons || !lessonId) return;

    const currentIndex = course.lessons.findIndex(
      (l: any) => l.contentId === lessonId,
    );
    if (currentIndex === -1 || currentIndex >= course.lessons.length - 1)
      return; // No next lesson

    setShowAutoAdvance(true);
    setAutoAdvanceCountdown(5);

    let countdown = 5;
    autoAdvanceTimerRef.current = setInterval(() => {
      countdown -= 1;

      if (countdown <= 0) {
        // Time's up, go to next lesson
        if (autoAdvanceTimerRef.current) {
          clearInterval(autoAdvanceTimerRef.current);
        }
        setShowAutoAdvance(false);

        // Navigate in next tick to avoid setState during render
        setTimeout(() => {
          const nextLesson = course.lessons[currentIndex + 1];
          navigate(
            `/courses/${currentCourseId}/lessons/${nextLesson.contentId}`,
          );
        }, 0);
      } else {
        setAutoAdvanceCountdown(countdown);
      }
    }, 1000);
  };

  const cancelAutoAdvance = () => {
    setShowAutoAdvance(false);
    setAutoAdvanceCountdown(5);
    if (autoAdvanceTimerRef.current) {
      clearInterval(autoAdvanceTimerRef.current);
    }
  };

  const handleVideoEnd = async () => {
    setIsPlaying(false);
    // Issue 8: record the completed watch segment.
    recordWatchEvent("completed");

    // Mark lesson as complete. Only for plain lessons (Issue 3): quizzes
    // and assignments can only be completed by passing/submitting them —
    // the backend rejects button-completion for any other type (403).
    if (lesson?.id && currentCourseId && lesson.type === "lesson") {
      try {
        const response = await api.post(
          `/courses/${numericCourseId || currentCourseId}/lessons/${lesson.id}/complete`,
        );

        markLessonCompleteLocally(lesson.id);
        await fetchCourse();

        if (
          response.data.course_completed &&
          response.data.certificate_available
        ) {
          toast.success("🎉 Congratulations! Course completed!");
        } else {
          toast.success("Lesson completed!");
        }
      } catch (error: any) {
        console.error("Error marking lesson as complete:", error);
      }
    }

    // Start auto-advance timer
    startAutoAdvance();
  };

  // H5P interactive-content completion (spec B6, plan Task 5). H5PLesson
  // already POSTed the advisory result and applied the score/completed
  // threshold before calling this — mirrors handleVideoEnd's lesson-complete
  // + achievement-celebration flow, minus watch-event tracking (not
  // applicable to H5P content).
  const h5pCompletionHandledRef = React.useRef(false);
  React.useEffect(() => {
    h5pCompletionHandledRef.current = false;
  }, [lessonId]);
  const handleH5PCompleted = React.useCallback(async () => {
    if (h5pCompletionHandledRef.current) return;
    h5pCompletionHandledRef.current = true;
    if (!lesson?.id || !currentCourseId || lesson.type !== "lesson") return;

    try {
      const response = await api.post(
        `/courses/${numericCourseId || currentCourseId}/lessons/${lesson.id}/complete`,
      );
      markLessonCompleteLocally(lesson.id);
      await fetchCourse();

      if (
        response.data.course_completed &&
        response.data.certificate_available
      ) {
        showAchievementNotification(
          "Course completed!",
          "Your certificate is ready.",
          "🎉",
        );
      } else {
        showAchievementNotification(
          "Lesson completed!",
          "Great work — keep going.",
          "✅",
        );
      }
    } catch (error: any) {
      console.error("Error marking H5P lesson as complete:", error);
    }
  }, [lesson?.id, lesson?.type, currentCourseId, numericCourseId, fetchCourse]);

  // Learning-game completion (spec §5): reuse the H5P lesson-complete
  // mechanism EXACTLY — GamePlayer already POSTed the advisory result
  // before calling this. Game lessons therefore count in
  // calculate_course_progress with zero new progress infrastructure.
  const gameCompletionHandledRef = React.useRef(false);
  React.useEffect(() => {
    gameCompletionHandledRef.current = false;
  }, [lessonId]);
  const handleGameCompleted = React.useCallback(async () => {
    if (gameCompletionHandledRef.current) return;
    gameCompletionHandledRef.current = true;
    if (!lesson?.id || !currentCourseId || lesson.type !== "lesson") return;

    try {
      const response = await api.post(
        `/courses/${numericCourseId || currentCourseId}/lessons/${lesson.id}/complete`,
      );
      markLessonCompleteLocally(lesson.id);
      await fetchCourse();

      if (
        response.data.course_completed &&
        response.data.certificate_available
      ) {
        showAchievementNotification(
          "Course completed!",
          "Your certificate is ready.",
          "🎉",
        );
      } else {
        showAchievementNotification(
          "Lesson completed!",
          "Great work — keep going.",
          "✅",
        );
      }
    } catch (error: any) {
      console.error("Error marking game lesson as complete:", error);
    }
  }, [lesson?.id, lesson?.type, currentCourseId, numericCourseId, fetchCourse]);

  // Cleanup on unmount
  React.useEffect(() => {
    return () => {
      if (autoAdvanceTimerRef.current) {
        clearInterval(autoAdvanceTimerRef.current);
      }
    };
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen bg-neutral-900 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto mb-4"></div>
          <p className="text-neutral-400">Loading lesson...</p>
        </div>
      </div>
    );
  }

  if (!course || !lesson) {
    return (
      <div className="min-h-screen bg-neutral-900 flex items-center justify-center">
        <div className="text-center text-neutral-300">
          <h2 className="text-2xl font-bold mb-2">No Lessons Available</h2>
          <p className="text-neutral-500 mb-4">
            This course doesn't have any lessons yet.
          </p>
          <Button onClick={() => navigate(`/courses/${currentCourseId}`)}>
            Back to Course
          </Button>
        </div>
      </div>
    );
  }

  // ---- Rebuilt from scratch: clean, fully responsive lesson layout ----
  const sections = course.sections || [
    { id: "default", title: "", lessons: course.lessons || [] },
  ];
  const roundedProgress = Math.round(courseProgress || 0);
  const isInteractive = lesson.type === "quiz" || lesson.type === "assignment";

  // Issue 3: interactive content items (quizzes AND assignments) cannot be
  // manually marked complete — the backend rejects button-completion for any
  // type other than 'lesson' (403). Disable the manual button for those
  // items so the only path to completion is a real submission / passing
  // attempt.
  const isNonLessonItem = lesson.type !== "lesson";
  const MarkCompleteButton = ({ className }: { className?: string }) => (
    <Button
      onClick={handleMarkComplete}
      disabled={lesson.is_completed || isNonLessonItem}
      title={
        isNonLessonItem && !lesson.is_completed
          ? "Complete this item to mark it as complete"
          : undefined
      }
      className={className}
    >
      {lesson.is_completed ? (
        <>
          <CheckCircle className="w-4 h-4 mr-2" />
          Completed
        </>
      ) : isNonLessonItem ? (
        lesson.type === "quiz" ? (
          "Pass the quiz to complete"
        ) : (
          "Submit to complete"
        )
      ) : (
        "Mark as complete"
      )}
    </Button>
  );

  return (
    <div className="rd-lesson min-h-dvh bg-neutral-950 text-white flex flex-col lg:flex-row">
      <header className="lg:hidden sticky top-0 z-30 flex items-center gap-3 h-14 px-3 bg-neutral-900/95 backdrop-blur border-b border-neutral-800">
        <button
          onClick={() => setSidebarOpen(true)}
          aria-label="Open lessons"
          className="p-2 rounded-lg hover:bg-neutral-800 text-neutral-200"
        >
          <List className="w-5 h-5" />
        </button>
        <div className="min-w-0 flex-1">
          <p className="text-[11px] text-primary-400 truncate">
            {course.title}
          </p>
          <p className="text-sm font-semibold text-white truncate">
            {lesson.title}
          </p>
        </div>
      </header>
      {sidebarOpen && (
        <div
          className="lg:hidden fixed inset-0 bg-black/60 z-40"
          onClick={() => setSidebarOpen(false)}
        />
      )}
      <TutorDrawer courseId={courseId ? Number(courseId) : undefined} />
      <main className="flex-1 min-w-0 flex flex-col">
        <div className="rd-lesson-topbar">
          <button onClick={() => navigate(`/courses/${currentCourseId}`)}>
            <ArrowLeft size={15} />
            {course.title}
          </button>
          <span>{roundedProgress}% complete</span>
        </div>
        {/* Certificate banner */}
        {certificateAvailable && showCertificateBanner && (
          <div className="flex items-center justify-between gap-3 px-4 sm:px-6 py-3 bg-gradient-to-r from-green-600 to-emerald-600">
            <div className="flex items-center gap-3 min-w-0">
              <CheckCircle2 className="w-5 h-5 shrink-0" />
              <p className="text-sm font-medium truncate">
                Certificate ready — you've completed this course.
              </p>
            </div>
            <div className="flex items-center gap-2 shrink-0">
              <Button
                onClick={() => navigate(`/certificates/${currentCourseId}`)}
                className="bg-white text-green-700 hover:bg-white/90 h-8 px-3 text-sm"
              >
                View
              </Button>
              <button
                onClick={() => setShowCertificateBanner(false)}
                className="p-1.5 text-white/80 hover:text-white"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}

        {/* Player: 16:9 stage that always fits the viewport (see .lesson-video-stage).
            The wrapper stays full-bleed black so a height-capped stage in
            landscape is centred rather than left-aligned. */}
        <div className="w-full shrink-0 bg-black">
          <div
            ref={videoContainerRef}
            id="video-container"
            className="lesson-video-stage bg-black overflow-hidden"
            style={
              videoAspect
                ? ({ "--lesson-aspect": videoAspect } as React.CSSProperties)
                : undefined
            }
            onContextMenu={(e) => {
              e.preventDefault();
              return false;
            }}
          >
            <div className="absolute inset-0">
              {lesson.type === "quiz" ? (
                <QuizRenderer
                  quizId={lesson.id}
                  courseId={numericCourseId!}
                  onNext={handleNextLesson}
                />
              ) : lesson.type === "assignment" ? (
                <AssignmentRenderer
                  assignmentId={lesson.id}
                  courseId={numericCourseId!}
                  onNext={handleNextLesson}
                />
              ) : lesson.type === "lesson" &&
                lesson.lesson_content_type === "h5p" &&
                lesson.h5p_public_id ? (
                <H5PLesson
                  contentId={lesson.h5p_public_id}
                  title={lesson.title}
                  onCompleted={handleH5PCompleted}
                />
              ) : lesson.type === "lesson" &&
                lesson.lesson_content_type === "three_d" &&
                lesson.three_d_model_id ? (
                <div className="rounded-xl border border-gray-200 p-4 bg-gray-50">
                  <h3 className="font-semibold text-gray-900 mb-1">
                    {lesson.title}
                  </h3>
                  <p className="text-xs text-gray-500 mb-3">
                    Explore the 3D model — rotate, zoom, inspect.
                  </p>
                  <DeferredThreeD
                    modelId={lesson.three_d_model_id}
                    description={
                      lesson.content
                        ? String(lesson.content).replace(/<[^>]+>/g, "")
                        : undefined
                    }
                  />
                  <ThreeDCheckYourself modelId={lesson.three_d_model_id} />
                </div>
              ) : lesson.type === "lesson" &&
                lesson.lesson_content_type === "virtual_lab" &&
                lesson.virtual_lab_sim ? (
                <div className="rounded-xl border border-gray-200 p-4 bg-gray-50">
                  <h3 className="font-semibold text-gray-900 mb-1">
                    {lesson.title}
                  </h3>
                  <p className="text-xs text-gray-500 mb-3">
                    Run the simulation and verify what you learned.
                  </p>
                  <VirtualLabEmbed
                    sim={lesson.virtual_lab_sim}
                    title={lesson.title}
                    onLessonComplete={handleGameCompleted}
                  />
                </div>
              ) : lesson.type === "lesson" &&
                lesson.lesson_content_type === "geogebra" &&
                lesson.geogebra_applet_id ? (
                <div className="rounded-xl border border-gray-200 p-4 bg-gray-50">
                  <h3 className="font-semibold text-gray-900 mb-1">
                    {lesson.title}
                  </h3>
                  <p className="text-xs text-gray-500 mb-3">
                    Interactive — drag, plot and explore. Changes stay on your
                    screen.
                  </p>
                  <GeoGebraEmbed
                    appletId={lesson.geogebra_applet_id}
                    lessonId={lesson.id}
                  />
                </div>
              ) : lesson.type === "lesson" &&
                lesson.lesson_content_type === "game" &&
                lesson.game_id ? (
                <GamePlayer
                  gameId={lesson.game_id}
                  previewOnly={false}
                  onLessonComplete={handleGameCompleted}
                  className="min-h-[60vh]"
                />
              ) : (
                <>
                  <AudioOnlyToggle
                    src={lesson.video_url || ""}
                    value={audioSrc}
                    onChange={setAudioSrc}
                  />
                  <VideoPlayer
                    ref={playerRef}
                    className="h-full"
                    src={
                      audioSrc || lesson.video_url || lesson.youtube_url || ""
                    }
                    title={lesson.title}
                    poster={lesson.thumbnail}
                    autoPlay={false}
                    onPlay={() => {
                      setIsPlaying(true);
                      recordWatchEvent("started");
                    }}
                    onPause={() => {
                      setIsPlaying(false);
                      recordWatchEvent("paused");
                    }}
                    onEnded={handleVideoEnd}
                    onTimeUpdate={(state) => handleProgress(state)}
                    onDuration={handleDuration}
                    onAspectRatio={setVideoAspect}
                    lessonId={lesson.id}
                    courseId={numericCourseId!}
                  />
                </>
              )}
            </div>

            {/* Protected badge (video only) */}
            {!isInteractive && (
              <div className="absolute top-3 right-3 z-10 pointer-events-none">
                <div className="flex items-center gap-1.5 bg-black/60 backdrop-blur rounded-md px-2.5 py-1.5 border border-white/10">
                  <Shield className="w-3.5 h-3.5 text-green-400" />
                  <span className="text-[11px] font-medium text-white">
                    Protected
                  </span>
                </div>
              </div>
            )}

            {/* Auto-advance overlay */}
            {showAutoAdvance && (
              <div className="absolute inset-0 z-20 flex items-center justify-center bg-black/80">
                <div className="text-center px-4 sm:px-6">
                  <div className="w-12 h-12 sm:w-14 sm:h-14 rounded-full bg-primary-600 flex items-center justify-center text-xl sm:text-2xl font-bold mx-auto mb-3 sm:mb-4">
                    {autoAdvanceCountdown}
                  </div>
                  <p className="text-white font-semibold mb-3 sm:mb-4 text-sm sm:text-base">
                    Next lesson starting…
                  </p>
                  <div className="flex items-center justify-center gap-3">
                    <Button variant="outline" onClick={cancelAutoAdvance}>
                      Cancel
                    </Button>
                    <Button onClick={handleNextLesson}>Go now</Button>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Content below the player */}
        <div className="flex-1 bg-neutral-900/40 border-t border-neutral-800/60">
          <div className="max-w-4xl mx-auto w-full px-4 sm:px-6 py-5 sm:py-7">
            {/* Title + notes toggle */}
            <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3 mb-4">
              <div className="min-w-0">
                <span className="inline-block text-[11px] font-semibold uppercase tracking-wider text-primary-400 mb-1">
                  {lesson.type === "quiz"
                    ? "Quiz"
                    : lesson.type === "assignment"
                      ? "Assignment"
                      : "Lesson"}
                </span>
                <h1 className="text-xl sm:text-2xl font-bold text-white leading-snug break-words">
                  {lesson.title}
                </h1>
              </div>
              {!isInteractive && (
                <button
                  onClick={() => setShowNotesPanel((v) => !v)}
                  className={cn(
                    "shrink-0 inline-flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium border transition-colors",
                    showNotesPanel
                      ? "bg-primary-600 border-primary-500 text-white"
                      : "bg-neutral-800 border-neutral-700 text-neutral-200 hover:border-primary-500 hover:text-white",
                  )}
                >
                  <StickyNote className="w-4 h-4" />
                  <span>Notes</span>
                  {notes.length > 0 && (
                    <span className="text-xs bg-black/30 rounded-full px-1.5 py-0.5">
                      {notes.length}
                    </span>
                  )}
                </button>
              )}
            </div>

            {/* Description */}
            {lesson.description && (
              <div
                className="prose prose-invert prose-sm sm:prose-base max-w-none text-neutral-300 leading-relaxed"
                dangerouslySetInnerHTML={{
                  __html: sanitizeHtml(lesson.description),
                }}
              />
            )}

            {/* Resources */}
            {lesson.attachment_url &&
              (() => {
                let files: string[] = [];
                try {
                  files = JSON.parse(lesson.attachment_url);
                } catch {
                  files = lesson.attachment_url ? [lesson.attachment_url] : [];
                }
                return files.length > 0 ? (
                  <div className="mt-6">
                    <h3 className="text-sm font-semibold text-neutral-400 uppercase tracking-wider mb-3">
                      Resources
                    </h3>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                      {files.map((url: string, idx: number) => (
                        <button
                          key={idx}
                          onClick={() => {
                            const fileUrl = url.startsWith("http")
                              ? url
                              : `${window.location.origin}${url}`;
                            window.location.href = fileUrl;
                          }}
                          className="inline-flex items-center gap-3 px-4 py-3 bg-neutral-800 hover:bg-neutral-700 border border-neutral-700 hover:border-orange-500 text-white rounded-lg text-sm font-medium transition-colors text-left"
                        >
                          <span className="text-lg"><AstraSymbol value="📎" /></span>
                          <span className="truncate">
                            Download file {idx + 1}
                          </span>
                        </button>
                      ))}
                    </div>
                  </div>
                ) : null;
              })()}

            {/* Mobile mark-complete */}
            {!isInteractive && (
              <div className="mt-6 lg:hidden">
                <MarkCompleteButton className="w-full" />
              </div>
            )}

            {/* Notes panel (inline) */}
            {showNotesPanel && !isInteractive && (
              <div className="mt-8 border-t border-neutral-800 pt-6">
                <h3 className="font-bold text-white flex items-center gap-2 mb-4">
                  <StickyNote className="w-5 h-5 text-primary-500" />
                  My notes
                  <span className="text-sm font-normal text-neutral-400">
                    ({notes.length})
                  </span>
                </h3>
                <div className="flex gap-2 mb-4">
                  <input
                    type="text"
                    value={currentNote}
                    onChange={(e) => setCurrentNote(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && addNote()}
                    placeholder={`Add a note at ${formatTime(currentTime)}…`}
                    className="flex-1 bg-neutral-900 border border-neutral-700 rounded-lg px-3 py-2 text-sm text-white focus:border-primary-500 focus:outline-none"
                  />
                  <Button onClick={addNote} disabled={!currentNote.trim()}>
                    <Plus className="w-4 h-4" />
                  </Button>
                </div>
                <div className="space-y-2">
                  {notes.length === 0 ? (
                    <p className="text-sm text-neutral-500 text-center py-6">
                      No notes yet. Add one at the current timestamp.
                    </p>
                  ) : (
                    notes.map((note) => (
                      <div
                        key={note.id}
                        className="flex items-start gap-3 bg-neutral-800/50 rounded-lg p-3 border border-neutral-700/50 group"
                      >
                        <button
                          onClick={() => jumpToNote(note.timestamp)}
                          className="shrink-0 px-2.5 py-1 bg-primary-900/40 hover:bg-primary-600 text-primary-300 hover:text-white rounded font-mono text-xs transition-colors"
                        >
                          {formatTime(note.timestamp)}
                        </button>
                        <p className="flex-1 text-sm text-neutral-200 leading-relaxed">
                          {note.content}
                        </p>
                        <button
                          onClick={() => deleteNote(note.id)}
                          className="shrink-0 text-neutral-500 hover:text-red-400 opacity-0 group-hover:opacity-100 transition-opacity"
                          aria-label="Delete note"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    ))
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      </main>
      <aside
        className={cn(
          "rd-lesson-rail fixed left-0 lg:left-auto lg:sticky top-0 z-50 lg:z-auto h-dvh w-[85vw] max-w-xs lg:w-[296px] shrink-0",
          "bg-neutral-900/80 backdrop-blur-xl border-l border-white/10 flex flex-col transition-transform duration-300",
          sidebarOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0",
        )}
      >
        {/* Sidebar header */}
        <div className="p-4 border-b border-neutral-800">
          <div className="flex items-center justify-between mb-3">
            <button
              onClick={() => navigate(`/courses/${currentCourseId}`)}
              className="inline-flex items-center gap-2 text-sm text-neutral-300 hover:text-white transition-colors"
            >
              <ArrowLeft className="w-4 h-4" />
              Back to course
            </button>
            <button
              onClick={() => setSidebarOpen(false)}
              aria-label="Close"
              className="lg:hidden p-1.5 rounded-lg text-neutral-400 hover:text-white hover:bg-neutral-800"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
          <h2 className="font-bold text-white truncate">{course.title}</h2>
          <div className="flex items-center gap-2 mt-3">
            <div className="flex-1 h-2 bg-neutral-800 rounded-full overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-primary-600 to-primary-500 transition-all duration-500"
                style={{ width: `${roundedProgress}%` }}
              />
            </div>
            <span className="text-xs text-neutral-400 font-medium tabular-nums">
              {roundedProgress}%
            </span>
          </div>
        </div>

        {/* Lesson list */}
        <div
          ref={sidebarRef}
          className="flex-1 overflow-y-auto custom-scrollbar"
        >
          {sections.map((section: any) => (
            <div key={section.id}>
              {section.title && (
                <div className="px-4 py-2 bg-neutral-950/60 border-b border-neutral-800/70 sticky top-0">
                  <p className="text-[11px] font-semibold text-primary-400 uppercase tracking-wider">
                    {section.title}
                  </p>
                </div>
              )}
              {section.lessons?.map((l: any, index: number) => {
                const isCurrent = l.contentId === lessonId;
                return (
                  <button
                    key={l.contentId}
                    ref={isCurrent ? activeItemRef : null}
                    onClick={() => navigateToLesson(l.contentId)}
                    className={cn(
                      "w-full flex items-start gap-3 px-4 py-3 text-left border-b border-neutral-800/50 transition-colors",
                      isCurrent
                        ? "bg-primary-950/40 border-l-2 border-l-primary-500"
                        : "hover:bg-neutral-800/50",
                    )}
                  >
                    <span className="shrink-0 mt-0.5">
                      {l.is_completed ? (
                        <CheckCircle className="w-5 h-5 text-green-500" />
                      ) : isCurrent ? (
                        <Play className="w-5 h-5 text-primary-500" />
                      ) : l.type === "quiz" ? (
                        <HelpCircle className="w-5 h-5 text-neutral-500" />
                      ) : l.type === "assignment" ? (
                        <PenTool className="w-5 h-5 text-neutral-500" />
                      ) : (
                        <span className="w-5 h-5 rounded-full border border-neutral-600 flex items-center justify-center text-[11px] text-neutral-400">
                          {index + 1}
                        </span>
                      )}
                    </span>
                    <span className="min-w-0 flex-1">
                      <span className="block text-[11px] text-neutral-500 mb-0.5">
                        {l.type === "quiz"
                          ? "Quiz"
                          : l.type === "assignment"
                            ? "Assignment"
                            : `Lesson ${index + 1}`}
                      </span>
                      <span
                        className={cn(
                          "block text-sm truncate",
                          isCurrent
                            ? "text-white font-semibold"
                            : "text-neutral-300",
                        )}
                      >
                        {l.lesson_title || l.title}
                      </span>
                    </span>
                  </button>
                );
              })}
            </div>
          ))}
        </div>

        {/* Desktop mark-complete — hidden for interactive items (quiz /
            assignment), which cannot be manually marked complete. */}
        {!isInteractive && (
          <div className="hidden lg:block p-4 border-t border-neutral-800">
            <MarkCompleteButton className="w-full" />
          </div>
        )}
      </aside>
    </div>
  );
};
