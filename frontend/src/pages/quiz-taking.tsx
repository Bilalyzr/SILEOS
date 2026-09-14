import { AstraSymbol } from "@/components/design-system/AstraSymbol";
import { PageLayout, PageHeader } from "@/components/design-system/PageLayout";
import React, { useState, useEffect, useCallback } from "react";
import { confirmDialog } from "@/components/ui/confirm";
import { ScorableItemsPanel } from "@/components/assessment/ScorableItemsPanel";
import type { ScorableItem } from "@/api/scorable";
import { useNavigate, useParams } from "react-router-dom";
import {
  Clock,
  AlertCircle,
  XCircle,
  ChevronRight,
  ChevronLeft,
  Flag,
  Award,
  HourglassIcon,
  PauseCircle,
} from "lucide-react";
import toast from "react-hot-toast";
import { api } from "@/api/axios";
import { signal, flushSignals } from "@/api/signals";

interface QuizQuestion {
  id: string;
  type:
    | "multiple_choice"
    | "true_false"
    | "short_answer"
    | "essay"
    | "fill_in_blank"
    | "open_ended";
  question: string;
  points: number;
  options?: string[];
  imageUrl?: string;
}

interface QuizData {
  id: number;
  title: string;
  description: string;
  timeLimit: number;
  passingScore: number;
  maxAttempts: number;
  randomizeQuestions: boolean;
  showCorrectAnswers: boolean;
  questions: QuizQuestion[];
  interactive_modules?: ScorableItem[];
}

interface QuizAnswer {
  questionId: string;
  answer: string | number | string[];
}

// Server timer grace window mirrored from backend/app/routers/quizzes.py
// SUBMIT_GRACE_SECONDS — purely a client-side "don't panic yet" buffer; the
// server is the actual authority and re-checks this independently on submit.
const SUBMIT_GRACE_SECONDS = 90;

interface AttemptInfo {
  attemptId: number;
  courseId: number;
  timeLimit: number; // minutes; 0 = unlimited
  attemptStartedAt: string | null;
  resumed: boolean;
  attemptStatus: string;
}

interface SubmitResultState {
  percentage: number;
  passed: boolean;
  attemptStatus: string;
  pendingReview: boolean;
  lateSubmission: boolean;
}

const QuizTaking: React.FC = () => {
  const navigate = useNavigate();
  const { quizId } = useParams();

  const [quiz, setQuiz] = useState<QuizData | null>(null);
  const [attempt, setAttempt] = useState<AttemptInfo | null>(null);
  const [answers, setAnswers] = useState<QuizAnswer[]>([]);
  const [currentQuestion, setCurrentQuestion] = useState(0);
  const [timeRemaining, setTimeRemaining] = useState(0);
  const [isSubmitted, setIsSubmitted] = useState(false);
  const [result, setResult] = useState<SubmitResultState | null>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [showAllQuestions, setShowAllQuestions] = useState(false);
  const [attemptsInfo, setAttemptsInfo] = useState<{
    used: number;
    max: number;
    remaining: number;
    unlimited: boolean;
  } | null>(null);
  const [pendingReviewLink, setPendingReviewLink] = useState<number | null>(
    null,
  );
  const [pausedNotice, setPausedNotice] = useState(false);
  // Single-shot guard for the expiry auto-submit — the interval could fire
  // again (or React StrictMode could re-run the effect) before isSubmitted
  // commits, double-submitting the attempt.
  const submittedRef = React.useRef(false);
  // Learning signals: time spent per question + how often an answer was
  // changed (hesitation) — sent in batches, never blocking the attempt.
  const qStartRef = React.useRef<number>(Date.now());
  const lastQRef = React.useRef<string | null>(null);
  const qChangesRef = React.useRef<Record<string, number>>({});

  // Server-authoritative deadline (spec A1.3): attempt_started_at +
  // time_limit(minutes) + grace, computed from the /start response — not a
  // client-only countdown reset on reload. Recomputed whenever attempt info
  // changes (e.g. resumed:true returns the ORIGINAL attempt_started_at, so
  // the countdown correctly reflects time already spent, not a fresh 30:00).
  const computeDeadlineSeconds = useCallback((info: AttemptInfo): number => {
    if (!info.timeLimit || info.timeLimit <= 0 || !info.attemptStartedAt) {
      return 0; // unlimited
    }
    const startedMs = new Date(info.attemptStartedAt).getTime();
    const deadlineMs =
      startedMs + info.timeLimit * 60 * 1000 + SUBMIT_GRACE_SECONDS * 1000;
    const remainingMs = deadlineMs - Date.now();
    return Math.max(0, Math.floor(remainingMs / 1000));
  }, []);

  // Load quiz data + start/resume the attempt server-side.
  useEffect(() => {
    const loadQuiz = async () => {
      try {
        // First get the quiz to find its course_id
        const quizResponse = await api.get(`/quizzes/${quizId}`);
        const resolvedCourseId = quizResponse.data.course_id;

        // Then fetch full quiz details with questions
        const response = await api.get(
          `/courses/${resolvedCourseId}/quizzes/${quizId}`,
        );
        const quizData = response.data;

        setQuiz({
          id: quizData.id,
          title: quizData.title,
          description: quizData.description,
          timeLimit: quizData.timeLimit,
          passingScore: quizData.passingScore,
          maxAttempts: quizData.maxAttempts,
          randomizeQuestions: quizData.randomizeQuestions,
          showCorrectAnswers: quizData.showCorrectAnswers,
          questions: quizData.questions || [],
          interactive_modules: quizData.interactive_modules || [],
        });

        // Start (or resume) the server-tracked attempt — this is the
        // authoritative source for the timer deadline, not a fresh
        // client-side countdown from quizData.timeLimit.
        const startResponse = await api.post(`/quizzes/${quizId}/start`);
        const startData = startResponse.data;
        // Roadmap item 5: an attempt may carry its own random subset of questions
        if (
          Array.isArray(startData.question_ids) &&
          startData.question_ids.length > 0
        ) {
          const keep = new Set<number>(
            startData.question_ids.map((x: any) => Number(x)),
          );
          setQuiz((prev) =>
            prev
              ? {
                  ...prev,
                  questions: prev.questions.filter((qq: any) =>
                    keep.has(Number(qq.id ?? qq.question_id)),
                  ),
                }
              : prev,
          );
        }

        if (startData.attempt_status === "pending_review") {
          // A prior attempt is already awaiting instructor review — nothing
          // left to answer here; point the student at their results.
          setPendingReviewLink(startData.attempt_id);
          setLoading(false);
          return;
        }

        const info: AttemptInfo = {
          attemptId: startData.attempt_id,
          courseId: startData.course_id,
          timeLimit: startData.time_limit,
          attemptStartedAt: startData.attempt_started_at,
          resumed: !!startData.resumed,
          attemptStatus: startData.attempt_status,
        };
        setAttempt(info);
        setTimeRemaining(computeDeadlineSeconds(info));

        if (info.resumed) {
          toast("Resuming your in-progress attempt", { icon: <AstraSymbol value="⏳" /> });
          // Rehydrate previously saved answers so a reloaded/resumed
          // session doesn't look blank.
          try {
            const attemptDetail = await api.get(
              `/quiz-attempts/${info.attemptId}`,
            );
            const savedAnswers = attemptDetail.data?.answers || {};
            const rehydrated: QuizAnswer[] = Object.entries(savedAnswers).map(
              ([questionId, answer]) => ({
                questionId,
                answer: answer as string | number,
              }),
            );
            setAnswers(rehydrated);
          } catch {
            // Non-fatal — the student can just re-answer.
          }
        }

        // Get attempts count
        const countResponse = await api.get(
          `/courses/${resolvedCourseId}/quizzes/${quizId}/attempts-count`,
        );
        setAttemptsInfo({
          used: countResponse.data.attempts_used,
          max: countResponse.data.max_attempts,
          remaining: countResponse.data.remaining,
          unlimited: countResponse.data.unlimited,
        });
      } catch (error: any) {
        // 409 here means an unresumable state (e.g. concurrent submit) —
        // still surface a helpful message rather than a blank error toast.
        toast.error(error?.response?.data?.detail || "Failed to load quiz");
        console.error(error);
      } finally {
        setLoading(false);
      }
    };

    loadQuiz();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [quizId]);

  // Timer countdown — ticks the locally-computed deadline. Unlimited
  // (timeLimit 0) quizzes never start this interval.
  // R8 proctoring-lite: tab / focus / clipboard events are reported (advisory)
  useEffect(() => {
    if (!attempt || isSubmitted) return;
    const report = (event: string) => {
      api
        .post(`/quiz-attempts/${attempt.attemptId}/integrity`, { event })
        .catch(() => {});
      if (event === "tab_hidden")
        toast("Leaving the quiz tab is recorded for your instructor.", {
          icon: <AstraSymbol value="👀" />,
        });
    };
    const onVis = () =>
      report(
        document.visibilityState === "hidden" ? "tab_hidden" : "tab_visible",
      );
    const onBlur = () => report("window_blur");
    const onCopy = () => report("copy");
    const onPaste = () => report("paste");
    const onFs = () => {
      if (!document.fullscreenElement) report("fullscreen_exit");
    };
    document.addEventListener("visibilitychange", onVis);
    window.addEventListener("blur", onBlur);
    document.addEventListener("copy", onCopy);
    document.addEventListener("paste", onPaste);
    document.addEventListener("fullscreenchange", onFs);
    return () => {
      document.removeEventListener("visibilitychange", onVis);
      window.removeEventListener("blur", onBlur);
      document.removeEventListener("copy", onCopy);
      document.removeEventListener("paste", onPaste);
      document.removeEventListener("fullscreenchange", onFs);
    };
  }, [attempt, isSubmitted]);

  useEffect(() => {
    if (
      !quiz ||
      !attempt ||
      isSubmitted ||
      attempt.timeLimit <= 0 ||
      timeRemaining <= 0
    )
      return;

    const timer = setInterval(() => {
      if (timeRemaining <= 1) {
        // Expiry — auto-submit from the interval callback, NOT from inside
        // the setTimeRemaining state updater (side effects in updaters run
        // twice under StrictMode and double-submit). Skip the unanswered
        // questions confirm: a timeout leaves the student no choice.
        clearInterval(timer);
        setTimeRemaining(0);
        if (!submittedRef.current) {
          handleSubmit(true);
        }
      } else {
        setTimeRemaining(timeRemaining - 1);
      }
    }, 1000);

    return () => clearInterval(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [quiz, attempt, isSubmitted, timeRemaining]);

  // Update answer — mirrors into local state AND persists server-side
  // per-question (spec: pause blocks answer writes, so a 409 here means
  // the attempt got paused elsewhere; surface that rather than losing the
  // student's input silently).
  const updateAnswer = (
    questionId: string,
    answer: string | number | string[],
  ) => {
    const before = answers.find((a) => a.questionId === questionId);
    if (before && before.answer !== "" && before.answer !== answer) {
      qChangesRef.current[questionId] =
        (qChangesRef.current[questionId] || 0) + 1;
    }
    setAnswers((prev) => {
      const existing = prev.find((a) => a.questionId === questionId);
      if (existing) {
        return prev.map((a) =>
          a.questionId === questionId ? { ...a, answer } : a,
        );
      }
      return [...prev, { questionId, answer }];
    });

    if (!attempt) return;
    api
      .post(`/quiz-attempts/${attempt.attemptId}/answers`, {
        question_id: parseInt(questionId, 10),
        given_answer: answer,
      })
      .catch((error: any) => {
        if (error?.response?.status === 409) {
          setPausedNotice(true);
        }
        // Non-fatal otherwise — the answer is still submitted with the final
        // /submit payload, so a transient save failure isn't destructive.
      });
  };

  useEffect(() => {
    if (!quiz || !attempt) return;
    const q = quiz.questions[currentQuestion];
    const now = Date.now();
    if (lastQRef.current && q && lastQRef.current !== String(q.id)) {
      signal({
        kind: "question_time",
        course_id: attempt.courseId,
        quiz_id: Number(quizId),
        question_id: Number(lastQRef.current),
        value: Math.round((now - qStartRef.current) / 1000),
      });
    }
    lastQRef.current = q ? String(q.id) : null;
    qStartRef.current = now;
  }, [currentQuestion, quiz, attempt, quizId]);

  // Get answer for question
  const getAnswer = (questionId: string): string | number | string[] => {
    const answer = answers.find((a) => a.questionId === questionId);
    return answer?.answer ?? "";
  };

  // Submit quiz. `dueToTimeout` marks the automatic expiry submission,
  // which must not interrupt the student with an unanswered-questions
  // confirm dialog.
  const handleSubmit = async (dueToTimeout: boolean = false) => {
    if (submitting || submittedRef.current || !attempt) return;

    // Check if all questions are answered
    const unansweredQuestions = quiz!.questions.filter((q) => {
      const answer = getAnswer(q.id);
      return !answer && answer !== 0;
    });

    if (!dueToTimeout && unansweredQuestions.length > 0 && !isSubmitted) {
      const ok = await confirmDialog(
        `You have ${unansweredQuestions.length} unanswered question(s). Submit anyway?`,
        {
          confirmLabel: "Submit anyway",
          cancelLabel: "Keep answering",
          danger: false,
        },
      );
      if (!ok) return;
    }

    setSubmitting(true);
    submittedRef.current = true;
    try {
      if (lastQRef.current) {
        signal({
          kind: "question_time",
          course_id: attempt.courseId,
          quiz_id: Number(quizId),
          question_id: Number(lastQRef.current),
          value: Math.round((Date.now() - qStartRef.current) / 1000),
        });
      }
      Object.entries(qChangesRef.current).forEach(([qid, n]) =>
        signal({
          kind: "answer_change",
          course_id: attempt.courseId,
          quiz_id: Number(quizId),
          question_id: Number(qid),
          value: n,
        }),
      );
      flushSignals();
    } catch {
      /* best-effort */
    }
    try {
      // Convert answers to API format
      const answersObj: { [key: string]: string | number | string[] } = {};
      answers.forEach((a) => {
        answersObj[a.questionId] = a.answer;
      });

      // Submit via the attempt-scoped route so the server timer/pause
      // checks (which need a known attempt_started_at) apply.
      const response = await api.post(
        `/quiz-attempts/${attempt.attemptId}/submit`,
        {
          answers: answersObj,
        },
      );
      const data = response.data;

      setResult({
        percentage: data.percentage,
        passed: !!data.passed,
        attemptStatus: data.attempt_status,
        pendingReview: !!data.pending_review,
        lateSubmission: !!data.late_submission,
      });
      setIsSubmitted(true);

      if (data.late_submission) {
        toast.error(
          "Submitted late — the server closed your attempt at the deadline and scored only what was saved in time.",
          { duration: 6000 },
        );
      } else if (data.pending_review) {
        toast(
          "Submitted — some answers need instructor review before your final score is ready.",
          { icon: <AstraSymbol value="📝" />, duration: 6000 },
        );
      } else if (data.passed) {
        toast.success("Congratulations! You passed the quiz!");
      } else {
        toast.error(
          `You scored ${data.percentage}%. Passing score is ${quiz!.passingScore}%`,
        );
      }
    } catch (error: any) {
      // Allow the student to retry after a failed submission.
      submittedRef.current = false;
      const status = error?.response?.status;
      const detail = error?.response?.data?.detail;
      if (status === 409) {
        if (detail && /paused/i.test(detail)) {
          // Paused → prompt resume rather than a generic failure toast.
          setPausedNotice(true);
          toast.error("Your attempt is paused. Resume it before submitting.", {
            duration: 6000,
          });
        } else if (detail && /pending.*review|awaiting/i.test(detail)) {
          // Already pending review elsewhere — send them to results.
          toast.error("This attempt is already awaiting instructor review.");
          setPendingReviewLink(attempt.attemptId);
        } else {
          toast.error(detail || "This attempt cannot be submitted right now.");
        }
      } else {
        toast.error(detail || "Failed to submit quiz");
      }
      console.error(error);
    } finally {
      setSubmitting(false);
    }
  };

  const handleResume = async () => {
    if (!attempt) return;
    try {
      await api.post(`/quiz-attempts/${attempt.attemptId}/resume`);
      setPausedNotice(false);
      toast.success("Attempt resumed");
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || "Failed to resume attempt");
    }
  };

  // Format time
  const formatTime = (seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, "0")}`;
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-neutral-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto"></div>
          <p className="mt-4 text-neutral-600">Loading quiz...</p>
        </div>
      </div>
    );
  }

  // A prior attempt is already pending instructor review — nothing to take.
  if (pendingReviewLink !== null && !isSubmitted) {
    return (
      <div className="min-h-screen bg-neutral-50 flex items-center justify-center">
        <div className="text-center max-w-md mx-auto px-4">
          <HourglassIcon className="w-16 h-16 text-warning-500 mx-auto mb-4" />
          <h2 className="text-2xl font-bold text-neutral-900 mb-2">
            Awaiting instructor review
          </h2>
          <p className="text-neutral-600 mb-6">
            You already have a submitted attempt on this quiz that's waiting for
            your instructor to grade one or more answers. You'll see your final
            score once it's graded.
          </p>
          <button onClick={() => navigate(-1)} className="btn btn-primary">
            Back to course
          </button>
        </div>
      </div>
    );
  }

  if (!quiz || !attempt) {
    return (
      <div className="min-h-screen bg-neutral-50 flex items-center justify-center">
        <div className="text-center">
          <AlertCircle className="w-16 h-16 text-danger-500 mx-auto mb-4" />
          <h2 className="text-2xl font-bold text-neutral-900 mb-2">
            Quiz Not Found
          </h2>
          <button onClick={() => navigate(-1)} className="btn btn-primary mt-4">
            Go Back
          </button>
        </div>
      </div>
    );
  }

  // Results view
  if (isSubmitted && result !== null) {
    const { percentage, passed, pendingReview, lateSubmission } = result;

    return (
      <div className="min-h-screen bg-neutral-50 py-8">
        <div className="container-custom max-w-3xl">
          <div
            className="bg-white rounded-xl shadow-soft p-8 text-center"
            data-glass="content"
          >
            {lateSubmission && (
              <div className="mb-6 bg-danger-50 border border-danger-200 rounded-lg p-4 text-left flex items-start gap-3">
                <AlertCircle className="w-5 h-5 text-danger-600 flex-shrink-0 mt-0.5" />
                <div>
                  <p className="font-semibold text-danger-800">
                    Submitted late
                  </p>
                  <p className="text-sm text-danger-700">
                    The deadline passed before you submitted. Only answers
                    already saved by then were scored.
                  </p>
                </div>
              </div>
            )}

            {pendingReview ? (
              <>
                <HourglassIcon className="w-24 h-24 text-warning-500 mx-auto mb-4" />
                <h1 className="text-3xl font-bold text-neutral-900 mb-2">
                  Awaiting instructor review
                </h1>
                <p className="text-xl text-neutral-600 mb-6">
                  Your auto-graded answers scored {percentage}% so far. One or
                  more essay/open-ended answers still need your instructor's
                  review before your final score is ready.
                </p>
              </>
            ) : passed ? (
              <>
                <Award className="w-24 h-24 text-success-500 mx-auto mb-4" />
                <h1 className="text-3xl font-bold text-neutral-900 mb-2">
                  Congratulations!
                </h1>
                <p className="text-xl text-neutral-600 mb-6">
                  You passed the quiz with a score of {percentage}%
                </p>
              </>
            ) : (
              <>
                <XCircle className="w-24 h-24 text-danger-500 mx-auto mb-4" />
                <h1 className="text-3xl font-bold text-neutral-900 mb-2">
                  Better Luck Next Time
                </h1>
                <p className="text-xl text-neutral-600 mb-6">
                  You scored {percentage}%. Passing score is {quiz.passingScore}
                  %
                </p>
              </>
            )}

            <div className="bg-neutral-50 rounded-lg p-6 mb-6">
              <div className="grid grid-cols-3 gap-4 text-center">
                <div>
                  <p className="text-sm text-neutral-600 mb-1">
                    {pendingReview ? "Auto-graded so far" : "Your Score"}
                  </p>
                  <p className="text-2xl font-bold text-neutral-900">
                    {percentage}%
                  </p>
                </div>
                <div>
                  <p className="text-sm text-neutral-600 mb-1">Passing Score</p>
                  <p className="text-2xl font-bold text-neutral-900">
                    {quiz.passingScore}%
                  </p>
                </div>
                <div>
                  <p className="text-sm text-neutral-600 mb-1">Questions</p>
                  <p className="text-2xl font-bold text-neutral-900">
                    {quiz.questions.length}
                  </p>
                </div>
              </div>
              {attemptsInfo && !attemptsInfo.unlimited && (
                <div className="mt-4 text-center text-sm text-neutral-600">
                  Attempts: {attemptsInfo.used}/{attemptsInfo.max}{" "}
                  {attemptsInfo.remaining > 0 &&
                    `(${attemptsInfo.remaining} remaining)`}
                </div>
              )}
              {attemptsInfo?.unlimited && (
                <div className="mt-4 text-center text-sm text-neutral-600">
                  Unlimited attempts available
                </div>
              )}
            </div>

            <div className="flex gap-4 justify-center flex-wrap">
              <button onClick={() => navigate(-1)} className="btn btn-outline">
                Back to Course
              </button>
              {!pendingReview &&
                !passed &&
                attemptsInfo &&
                (attemptsInfo.remaining > 0 || attemptsInfo.unlimited) && (
                  <button
                    onClick={() => window.location.reload()}
                    className="btn btn-primary"
                  >
                    Retry Quiz
                    {!attemptsInfo.unlimited &&
                      ` (${attemptsInfo.remaining} left)`}
                  </button>
                )}
              {!pendingReview &&
                !passed &&
                attemptsInfo &&
                attemptsInfo.remaining === 0 &&
                !attemptsInfo.unlimited && (
                  <div className="w-full text-center text-danger-600 text-sm mt-2">
                    No attempts remaining. Contact your instructor for
                    assistance.
                  </div>
                )}
            </div>
          </div>
        </div>
      </div>
    );
  }

  const currentQ = quiz.questions[currentQuestion];
  const progress = ((currentQuestion + 1) / quiz.questions.length) * 100;
  const isUnlimitedTime = attempt.timeLimit <= 0;
  const isTimeCritical = !isUnlimitedTime && timeRemaining < 300; // Less than 5 minutes

  return (
    <div className="min-h-screen bg-neutral-50 py-8">
      <PageLayout
        header={
          <PageHeader>
            <div className="flex items-center justify-between mb-4">
              <div>
                <h1 className="text-2xl font-bold text-neutral-900">
                  {quiz.title}
                </h1>
                <p className="text-neutral-600 text-sm mt-1">
                  {quiz.description}
                </p>
                {attempt.resumed && (
                  <p className="text-xs text-primary-600 mt-1">
                    Resuming a previous in-progress attempt
                  </p>
                )}
              </div>
              {!isUnlimitedTime && (
                <div
                  className={`flex items-center gap-2 px-4 py-2 rounded-lg ${
                    isTimeCritical
                      ? "bg-danger-50 text-danger-700"
                      : "bg-neutral-100 text-neutral-700"
                  }`}
                >
                  <Clock className="w-5 h-5" />
                  <span className="font-semibold text-lg">
                    {formatTime(timeRemaining)}
                  </span>
                </div>
              )}
            </div>

            {/* Progress bar */}
            <div className="relative h-2 bg-neutral-200 rounded-full overflow-hidden">
              <div
                className="absolute top-0 left-0 h-full bg-primary-500 transition-all duration-300"
                style={{ width: `${progress}%` }}
              />
            </div>
            <div className="flex justify-between text-sm text-neutral-600 mt-2">
              <span>
                Question {currentQuestion + 1} of {quiz.questions.length}
              </span>
              <span>{Math.round(progress)}% Complete</span>
            </div>
          </PageHeader>
        }
        className="rd-screen rd-screen-quiz-taking"
      >
        {pausedNotice && (
          <div className="bg-warning-50 border border-warning-200 rounded-xl p-4 mb-6 flex items-center justify-between gap-4 flex-wrap">
            <div className="flex items-center gap-3">
              <PauseCircle className="w-5 h-5 text-warning-600 flex-shrink-0" />
              <p className="text-sm text-warning-800">
                This attempt is paused — your answers aren't being saved until
                you resume.
              </p>
            </div>
            <button onClick={handleResume} className="btn btn-sm btn-primary">
              Resume attempt
            </button>
          </div>
        )}
        <ScorableItemsPanel items={quiz.interactive_modules || []} />
        {!showAllQuestions ? (
          <div
            className="bg-white rounded-xl shadow-soft p-8 mb-6"
            data-glass="work"
          >
            <div className="mb-6">
              <div className="flex items-start justify-between mb-4">
                <h2 className="text-xl font-semibold text-neutral-900 flex-1">
                  {currentQ.question}
                </h2>
                <div className="flex items-center gap-2 ml-4 flex-shrink-0">
                  {(currentQ.type === "essay" ||
                    currentQ.type === "open_ended") && (
                    <span className="badge bg-purple-100 text-purple-700">
                      Manually graded
                    </span>
                  )}
                  <span className="badge bg-primary-100 text-primary-700">
                    {currentQ.points}{" "}
                    {currentQ.points === 1 ? "point" : "points"}
                  </span>
                </div>
              </div>

              {currentQ.imageUrl && (
                <img
                  src={currentQ.imageUrl}
                  alt="Question"
                  className="w-full max-w-md rounded-lg mb-6"
                />
              )}
            </div>

            {/* Multiple Choice */}
            {currentQ.type === "multiple_choice" && currentQ.options && (
              <div className="space-y-3">
                {currentQ.options.map((option, index) => (
                  <label
                    key={index}
                    className={`flex items-start gap-3 p-4 border-2 rounded-lg cursor-pointer transition-all ${
                      getAnswer(currentQ.id) === index
                        ? "border-primary-500 bg-primary-50"
                        : "border-neutral-200 hover:border-primary-300"
                    }`}
                  >
                    <input
                      type="radio"
                      name={`question-${currentQ.id}`}
                      checked={getAnswer(currentQ.id) === index}
                      onChange={() => updateAnswer(currentQ.id, index)}
                      className="radio mt-1"
                    />
                    <span className="text-neutral-900">{option}</span>
                  </label>
                ))}
              </div>
            )}

            {/* True/False */}
            {currentQ.type === "true_false" && (
              <div className="space-y-3">
                <label
                  className={`flex items-center gap-3 p-4 border-2 rounded-lg cursor-pointer transition-all ${
                    getAnswer(currentQ.id) === "true"
                      ? "border-primary-500 bg-primary-50"
                      : "border-neutral-200 hover:border-primary-300"
                  }`}
                >
                  <input
                    type="radio"
                    name={`question-${currentQ.id}`}
                    checked={getAnswer(currentQ.id) === "true"}
                    onChange={() => updateAnswer(currentQ.id, "true")}
                    className="radio"
                  />
                  <span className="text-neutral-900 font-medium">True</span>
                </label>
                <label
                  className={`flex items-center gap-3 p-4 border-2 rounded-lg cursor-pointer transition-all ${
                    getAnswer(currentQ.id) === "false"
                      ? "border-primary-500 bg-primary-50"
                      : "border-neutral-200 hover:border-primary-300"
                  }`}
                >
                  <input
                    type="radio"
                    name={`question-${currentQ.id}`}
                    checked={getAnswer(currentQ.id) === "false"}
                    onChange={() => updateAnswer(currentQ.id, "false")}
                    className="radio"
                  />
                  <span className="text-neutral-900 font-medium">False</span>
                </label>
              </div>
            )}

            {/* Short Answer */}
            {currentQ.type === "short_answer" && (
              <input
                type="text"
                value={getAnswer(currentQ.id) as string}
                onChange={(e) => updateAnswer(currentQ.id, e.target.value)}
                placeholder="Enter your answer..."
                className="input w-full"
              />
            )}

            {/* Essay / Open-ended (manually graded) */}
            {(currentQ.type === "essay" || currentQ.type === "open_ended") && (
              <>
                <textarea
                  value={getAnswer(currentQ.id) as string}
                  onChange={(e) => updateAnswer(currentQ.id, e.target.value)}
                  placeholder="Enter your answer..."
                  className="input w-full min-h-[200px]"
                  rows={8}
                />
                <p className="text-xs text-neutral-500 mt-2">
                  This answer is graded manually by your instructor after you
                  submit.
                </p>
              </>
            )}
            {/* Fill in the Blank */}
            {currentQ.type === "fill_in_blank" && (
              <div className="space-y-3">
                {currentQ.question.includes("___") ||
                currentQ.question.includes("[blank]") ? (
                  // Question has blank placeholders
                  <>
                    <p className="text-sm text-neutral-500">
                      Fill in the blank(s) below:
                    </p>
                    <div className="flex flex-wrap items-center gap-1 text-base leading-loose">
                      {currentQ.question
                        .split(/_{3,}|\[blank\]/gi)
                        .map((part: string, i: number, arr: string[]) => (
                          <span
                            key={i}
                            className="flex items-center gap-1 flex-wrap"
                          >
                            <span>{part}</span>
                            {i < arr.length - 1 && (
                              <input
                                type="text"
                                value={
                                  Array.isArray(getAnswer(currentQ.id))
                                    ? (getAnswer(currentQ.id) as string[])[i] ||
                                      ""
                                    : i === 0
                                      ? (getAnswer(currentQ.id) as string) || ""
                                      : ""
                                }
                                onChange={(e) => {
                                  const prev = Array.isArray(
                                    getAnswer(currentQ.id),
                                  )
                                    ? [...(getAnswer(currentQ.id) as string[])]
                                    : [
                                        (getAnswer(currentQ.id) as string) ||
                                          "",
                                      ];
                                  while (prev.length <= i) prev.push("");
                                  prev[i] = e.target.value;
                                  updateAnswer(
                                    currentQ.id,
                                    prev.length === 1 ? prev[0] : prev,
                                  );
                                }}
                                placeholder="type here"
                                className="border-b-2 border-primary-500 outline-none px-2 py-0.5 min-w-[120px] bg-primary-50 rounded text-center text-sm font-medium"
                              />
                            )}
                          </span>
                        ))}
                    </div>
                  </>
                ) : (
                  // Fallback: plain question with single input
                  <>
                    <p className="text-lg font-medium mb-3">
                      {currentQ.question}
                    </p>
                    <input
                      type="text"
                      value={(getAnswer(currentQ.id) as string) || ""}
                      onChange={(e) =>
                        updateAnswer(currentQ.id, e.target.value)
                      }
                      placeholder="Type your answer here..."
                      className="w-full max-w-md px-4 py-2 border-2 border-primary-500 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-300"
                    />
                  </>
                )}
              </div>
            )}
          </div>
        ) : (
          /* All Questions View */
          <div className="space-y-6 mb-6">
            {quiz.questions.map((q, index) => (
              <div
                key={q.id}
                className="bg-white rounded-xl shadow-soft p-6"
                data-glass="work"
              >
                <div className="flex items-start justify-between mb-4">
                  <h3 className="text-lg font-semibold text-neutral-900">
                    {index + 1}. {q.type === "fill_in_blank" ? "" : q.question}
                  </h3>
                  <span className="badge bg-primary-100 text-primary-700">
                    {q.points} pts
                  </span>
                </div>

                {/* Render appropriate input based on question type */}
                {q.type === "multiple_choice" && q.options && (
                  <div className="space-y-2">
                    {q.options.map((option, optIndex) => (
                      <label
                        key={optIndex}
                        className="flex items-center gap-2 cursor-pointer"
                      >
                        <input
                          type="radio"
                          name={`question-${q.id}`}
                          checked={getAnswer(q.id) === optIndex}
                          onChange={() => updateAnswer(q.id, optIndex)}
                          className="radio"
                        />
                        <span className="text-neutral-700">{option}</span>
                      </label>
                    ))}
                  </div>
                )}

                {q.type === "true_false" && (
                  <div className="flex gap-4">
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="radio"
                        name={`question-${q.id}`}
                        checked={getAnswer(q.id) === "true"}
                        onChange={() => updateAnswer(q.id, "true")}
                        className="radio"
                      />
                      <span>True</span>
                    </label>
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="radio"
                        name={`question-${q.id}`}
                        checked={getAnswer(q.id) === "false"}
                        onChange={() => updateAnswer(q.id, "false")}
                        className="radio"
                      />
                      <span>False</span>
                    </label>
                  </div>
                )}

                {q.type === "short_answer" && (
                  <input
                    type="text"
                    value={getAnswer(q.id) as string}
                    onChange={(e) => updateAnswer(q.id, e.target.value)}
                    placeholder="Your answer..."
                    className="input w-full"
                  />
                )}

                {(q.type === "essay" || q.type === "open_ended") && (
                  <textarea
                    value={getAnswer(q.id) as string}
                    onChange={(e) => updateAnswer(q.id, e.target.value)}
                    placeholder="Your answer..."
                    className="input w-full"
                    rows={4}
                  />
                )}
                {q.type === "fill_in_blank" &&
                  (q.question.includes("___") ||
                  q.question.includes("[blank]") ? (
                    // Question has blank placeholders
                    <div className="flex flex-wrap items-center gap-1 text-base leading-loose mt-2">
                      {q.question
                        .split(/_{3,}|\[blank\]/gi)
                        .map((part: string, i: number, arr: string[]) => (
                          <span
                            key={i}
                            className="flex items-center gap-1 flex-wrap"
                          >
                            <span className="text-white">{part}</span>
                            {i < arr.length - 1 && (
                              <input
                                type="text"
                                value={
                                  Array.isArray(getAnswer(q.id))
                                    ? (getAnswer(q.id) as string[])[i] || ""
                                    : i === 0
                                      ? (getAnswer(q.id) as string) || ""
                                      : ""
                                }
                                onChange={(e) => {
                                  const prev = Array.isArray(getAnswer(q.id))
                                    ? [...(getAnswer(q.id) as string[])]
                                    : [(getAnswer(q.id) as string) || ""];
                                  while (prev.length <= i) prev.push("");
                                  prev[i] = e.target.value;
                                  updateAnswer(
                                    q.id,
                                    prev.length === 1 ? prev[0] : prev,
                                  );
                                }}
                                placeholder="answer"
                                className="border-b-2 border-orange-500 outline-none px-2 py-0.5 min-w-[120px] bg-orange-50 rounded text-center text-sm font-medium text-gray-900 placeholder-gray-400"
                              />
                            )}
                          </span>
                        ))}
                    </div>
                  ) : (
                    // Fallback: plain question with single input
                    <div className="mt-2">
                      <p className="text-gray-900 mb-2">{q.question}</p>
                      <input
                        type="text"
                        value={(getAnswer(q.id) as string) || ""}
                        onChange={(e) => updateAnswer(q.id, e.target.value)}
                        placeholder="Type your answer here..."
                        className="w-full max-w-md px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
                      />
                    </div>
                  ))}
              </div>
            ))}
          </div>
        )}
        <div
          className="bg-white rounded-xl shadow-soft p-6"
          data-glass="content"
        >
          <div className="flex items-center justify-between">
            <div className="flex gap-2">
              <button
                onClick={() => setShowAllQuestions(!showAllQuestions)}
                className="btn btn-outline"
              >
                {showAllQuestions
                  ? "Single Question View"
                  : "View All Questions"}
              </button>
            </div>

            {!showAllQuestions && (
              <div className="flex gap-2">
                <button
                  onClick={() =>
                    setCurrentQuestion((prev) => Math.max(0, prev - 1))
                  }
                  disabled={currentQuestion === 0}
                  className="btn btn-outline"
                >
                  <ChevronLeft className="w-5 h-5 mr-1" />
                  Previous
                </button>

                {currentQuestion < quiz.questions.length - 1 ? (
                  <button
                    onClick={() =>
                      setCurrentQuestion((prev) =>
                        Math.min(quiz.questions.length - 1, prev + 1),
                      )
                    }
                    className="btn btn-primary"
                  >
                    Next
                    <ChevronRight className="w-5 h-5 ml-1" />
                  </button>
                ) : (
                  <button
                    onClick={() => handleSubmit()}
                    disabled={submitting}
                    className="btn btn-primary"
                  >
                    <Flag className="w-5 h-5 mr-2" />
                    {submitting ? "Submitting..." : "Submit Quiz"}
                  </button>
                )}
              </div>
            )}

            {showAllQuestions && (
              <button
                onClick={() => handleSubmit()}
                disabled={submitting}
                className="btn btn-primary"
              >
                <Flag className="w-5 h-5 mr-2" />
                {submitting ? "Submitting..." : "Submit Quiz"}
              </button>
            )}
          </div>
        </div>
      </PageLayout>
    </div>
  );
};

export default QuizTaking;
