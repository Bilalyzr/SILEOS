import { PageLayout, PageHeader } from "@/components/design-system/PageLayout";
/**
 * Instructor Grading Queue — merged oldest-first list of pending quiz-essay
 * attempts and submitted assignments for a course (plan Task 3 / spec A2).
 * Essay entries expand inline to show each manually-graded question +
 * the student's answer with a mark input; once every manual answer is
 * graded, "Finalize attempt" recomputes the score and ends the attempt.
 * Assignment entries link out to the existing assignment-grading page.
 */
import * as React from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import {
  ArrowLeft,
  Inbox,
  FileText,
  MessageSquare,
  ChevronDown,
  ChevronUp,
  CheckCircle2,
} from "lucide-react";
import toast from "react-hot-toast";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  getGradingQueue,
  getQuizAttemptResults,
  gradeQuizAnswer,
  finalizeQuizAttempt,
  type GradingQueueEntry,
  type QuizEssayQueueEntry,
} from "@/api/gradebook";

interface AttemptQuestion {
  question_id: number;
  question: string;
  type: string;
  points: number;
  user_answer: string | number | null;
  achieved_mark: number | null;
  needs_review: boolean;
  attempt_answer_id?: number | null;
}

function formatDate(iso: string | null): string {
  if (!iso) return "Unknown time";
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}

const EssayQueueCard: React.FC<{
  entry: QuizEssayQueueEntry;
  onFinalized: () => void;
}> = ({ entry, onFinalized }) => {
  const [expanded, setExpanded] = React.useState(false);
  const [loading, setLoading] = React.useState(false);
  const [questions, setQuestions] = React.useState<AttemptQuestion[] | null>(
    null,
  );
  const [marks, setMarks] = React.useState<Record<number, string>>({});
  const [savingId, setSavingId] = React.useState<number | null>(null);
  const [finalizing, setFinalizing] = React.useState(false);

  const loadDetail = React.useCallback(async () => {
    setLoading(true);
    try {
      const results = await getQuizAttemptResults(entry.attempt_id);
      const manualIds = new Set(entry.manual_answer_ids);
      const qs: AttemptQuestion[] = (results.questions || []).filter(
        (q: AttemptQuestion) =>
          manualIds.size === 0
            ? q.needs_review
            : manualIds.has(q.question_id) || q.needs_review,
      );
      setQuestions(qs);
    } catch (err: any) {
      toast.error(
        err?.response?.data?.detail ||
          err?.message ||
          "Failed to load the attempt",
      );
    } finally {
      setLoading(false);
    }
  }, [entry.attempt_id, entry.manual_answer_ids]);

  const toggleExpanded = () => {
    const next = !expanded;
    setExpanded(next);
    if (next && questions === null) {
      loadDetail();
    }
  };

  const handleSaveMark = async (question: AttemptQuestion) => {
    const answerId = question.attempt_answer_id;
    if (!answerId) {
      toast.error("Could not resolve this answer — try reloading the page.");
      return;
    }
    const raw = marks[question.question_id];
    const achieved = raw !== undefined ? parseFloat(raw) : NaN;
    if (!Number.isFinite(achieved)) {
      toast.error("Enter a numeric mark before saving");
      return;
    }
    if (achieved < 0 || achieved > question.points) {
      toast.error(`Mark must be between 0 and ${question.points}`);
      return;
    }
    setSavingId(question.question_id);
    try {
      await gradeQuizAnswer(entry.attempt_id, answerId, {
        achieved_mark: achieved,
      });
      toast.success("Mark saved");
      await loadDetail();
    } catch (err: any) {
      toast.error(
        err?.response?.data?.detail ||
          err?.message ||
          "Failed to save the mark",
      );
    } finally {
      setSavingId(null);
    }
  };

  const allGraded =
    questions !== null && questions.every((q) => q.achieved_mark !== null);

  const handleFinalize = async () => {
    setFinalizing(true);
    try {
      await finalizeQuizAttempt(entry.attempt_id);
      toast.success("Attempt finalized");
      onFinalized();
    } catch (err: any) {
      toast.error(
        err?.response?.data?.detail ||
          err?.message ||
          "Failed to finalize the attempt",
      );
    } finally {
      setFinalizing(false);
    }
  };

  return (
    <Card className="overflow-hidden">
      <button
        onClick={toggleExpanded}
        className="w-full flex items-center justify-between gap-4 p-4 text-left hover:bg-slate-50/60 transition-colors"
      >
        <div className="flex items-center gap-3 min-w-0">
          <div className="w-9 h-9 rounded-lg bg-purple-100 text-purple-700 flex items-center justify-center flex-shrink-0">
            <MessageSquare className="w-4 h-4" />
          </div>
          <div className="min-w-0">
            <div className="font-medium text-slate-900 truncate">
              {entry.quiz_title || "Quiz"}{" "}
              <span className="text-slate-400">&middot;</span>{" "}
              {entry.student_name}
            </div>
            <div className="text-xs text-slate-500">
              {entry.student_email} &middot; submitted{" "}
              {formatDate(entry.submitted_at)}
            </div>
          </div>
        </div>
        <div className="flex items-center gap-3 flex-shrink-0">
          <Badge variant="warning">Essay review</Badge>
          {expanded ? (
            <ChevronUp className="w-4 h-4 text-slate-400" />
          ) : (
            <ChevronDown className="w-4 h-4 text-slate-400" />
          )}
        </div>
      </button>

      {expanded && (
        <div className="border-t border-slate-100 p-4 space-y-4">
          {loading ? (
            <div className="space-y-2">
              <div className="h-4 w-3/4 dash-skeleton" />
              <div className="h-16 w-full dash-skeleton" />
            </div>
          ) : !questions || questions.length === 0 ? (
            <p className="text-sm text-slate-500">
              No manually-graded questions found on this attempt.
            </p>
          ) : (
            <>
              {questions.map((q, index) => (
                <div
                  key={q.question_id}
                  className="rounded-lg border border-slate-200 p-4"
                >
                  <div className="flex items-start justify-between gap-3 mb-2">
                    <p className="text-sm font-medium text-slate-900">
                      {q.question}
                    </p>
                    <span className="text-xs text-slate-500 flex-shrink-0">
                      {q.points} pts
                    </span>
                  </div>
                  <div className="bg-slate-50 rounded-md p-3 text-sm text-slate-700 whitespace-pre-wrap mb-3">
                    {q.user_answer || (
                      <span className="text-slate-400 italic">
                        No answer given
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-2">
                    <input
                      type="number"
                      min={0}
                      max={q.points}
                      placeholder={
                        q.achieved_mark !== null
                          ? String(q.achieved_mark)
                          : "Mark"
                      }
                      value={
                        marks[q.question_id] ??
                        (q.achieved_mark !== null
                          ? String(q.achieved_mark)
                          : "")
                      }
                      onChange={(e) =>
                        setMarks((prev) => ({
                          ...prev,
                          [q.question_id]: e.target.value,
                        }))
                      }
                      aria-label={`Mark for question ${index + 1}`}
                      className="input w-24"
                    />
                    <span className="text-xs text-slate-500">
                      / {q.points} pts
                    </span>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => handleSaveMark(q)}
                      disabled={savingId === q.question_id}
                    >
                      {savingId === q.question_id
                        ? "Saving..."
                        : q.achieved_mark !== null
                          ? "Update mark"
                          : "Save mark"}
                    </Button>
                    {q.achieved_mark !== null && (
                      <span className="text-xs text-emerald-600 flex items-center gap-1">
                        <CheckCircle2 className="w-3.5 h-3.5" /> Graded
                      </span>
                    )}
                  </div>
                </div>
              ))}

              <div className="flex items-center justify-between pt-2">
                <p className="text-xs text-slate-500">
                  {allGraded
                    ? "All manual questions graded."
                    : "Grade every question above to finalize."}
                </p>
                <Button
                  onClick={handleFinalize}
                  disabled={!allGraded || finalizing}
                >
                  {finalizing ? "Finalizing..." : "Finalize attempt"}
                </Button>
              </div>
            </>
          )}
        </div>
      )}
    </Card>
  );
};

export default function InstructorGradingQueuePage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const courseId = Number(id);

  const [queue, setQueue] = React.useState<GradingQueueEntry[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);

  const load = React.useCallback(async () => {
    if (!Number.isFinite(courseId)) return;
    try {
      setLoading(true);
      setError(null);
      const data = await getGradingQueue(courseId);
      setQueue(data.queue);
    } catch (err: any) {
      setError(
        err?.response?.data?.detail ||
          err?.message ||
          "Failed to load the grading queue",
      );
    } finally {
      setLoading(false);
    }
  }, [courseId]);

  React.useEffect(() => {
    load();
  }, [load]);

  if (!Number.isFinite(courseId)) {
    return (
      <Card className="p-8 text-center">
        <p className="text-sm text-danger-600">Invalid course.</p>
      </Card>
    );
  }

  return (
    <PageLayout
      header={
        <PageHeader>
          <div className="flex items-center gap-3">
            <button
              onClick={() => navigate(-1)}
              className="btn btn-ghost btn-sm"
              aria-label="Back"
            >
              <ArrowLeft className="h-5 w-5" />
            </button>
            <div>
              <h1 className="dash-h1 mb-1">Grading queue</h1>
              <p className="text-slate-600 text-sm">
                Essay answers and assignment submissions waiting on you, oldest
                first
              </p>
            </div>
          </div>
          <Link to={`/instructor/courses/${courseId}/gradebook`}>
            <Button variant="outline">Gradebook</Button>
          </Link>
        </PageHeader>
      }
      className="rd-screen rd-screen-instructor-grading-queue"
    >
      {loading ? (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <Card key={i} className="p-4">
              <div className="h-5 w-1/2 dash-skeleton mb-2" />
              <div className="h-3 w-1/3 dash-skeleton" />
            </Card>
          ))}
        </div>
      ) : error ? (
        <Card className="p-8 text-center">
          <p className="text-sm text-danger-600 mb-3">{error}</p>
          <Button variant="outline" onClick={load}>
            Try again
          </Button>
        </Card>
      ) : queue.length === 0 ? (
        <Card className="p-12 text-center">
          <Inbox className="h-12 w-12 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">
            Queue is empty
          </h3>
          <p className="text-gray-600">
            Nothing waiting on you right now — nice work.
          </p>
        </Card>
      ) : (
        <div className="space-y-3">
          {queue.map((entry) =>
            entry.type === "quiz_essay" ? (
              <EssayQueueCard
                key={`quiz_essay-${entry.attempt_id}`}
                entry={entry}
                onFinalized={load}
              />
            ) : (
              <Card key={`assignment-${entry.submission_id}`} className="p-4">
                <div className="flex items-center justify-between gap-4 flex-wrap">
                  <div className="flex items-center gap-3 min-w-0">
                    <div className="w-9 h-9 rounded-lg bg-sky-100 text-sky-700 flex items-center justify-center flex-shrink-0">
                      <FileText className="w-4 h-4" />
                    </div>
                    <div className="min-w-0">
                      <div className="font-medium text-slate-900 truncate">
                        {entry.assignment_title || "Assignment"}{" "}
                        <span className="text-slate-400">&middot;</span>{" "}
                        {entry.student_name}
                      </div>
                      <div className="text-xs text-slate-500">
                        {entry.student_email} &middot; submitted{" "}
                        {formatDate(entry.submitted_at)}
                        {entry.is_late && (
                          <span className="text-rose-600 font-medium">
                            {" "}
                            &middot; late
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-3 flex-shrink-0">
                    <Badge variant={entry.is_late ? "danger" : "secondary"}>
                      {entry.is_late ? "Late submission" : "Assignment"}
                    </Badge>
                    <Link
                      to={`/instructor/assignments/${entry.assignment_id}/grade`}
                    >
                      <Button size="sm">Grade</Button>
                    </Link>
                  </div>
                </div>
              </Card>
            ),
          )}
        </div>
      )}
    </PageLayout>
  );
}
