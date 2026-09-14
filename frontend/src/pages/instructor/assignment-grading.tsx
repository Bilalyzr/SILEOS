import React, { useState, useEffect } from "react";
import { confirmDialog } from "@/components/ui/confirm";
import { useNavigate, useParams } from "react-router-dom";
import {
  ArrowLeft,
  Download,
  FileText,
  User,
  Calendar,
  Clock,
  CheckCircle2,
  CheckCircle,
  XCircle,
  Search,
} from "lucide-react";
import toast from "react-hot-toast";
import { api } from "@/api/axios";
import { getBackendUrl } from "@/config/urls";
import { RubricScorer } from "@/components/assess/RubricScorer";
import type { RubricCriterion, RubricScoreEntry } from "@/lib/gradebook";

interface StudentSubmission {
  id: number;
  studentId: number;
  studentName: string;
  studentEmail: string;
  studentAvatar?: string;
  submittedAt: string;
  textContent: string;
  files: SubmissionFile[];
  grade?: number;
  rawGrade?: number | null;
  feedback?: string;
  status: "submitted" | "graded" | "returned";
  gradedByRole?: string | null;
  isLate?: boolean;
  rubricScores?: RubricScoreEntry[] | null;
}

interface SubmissionFile {
  id: string;
  name: string;
  url: string;
  size: number;
  type: string;
}

interface AssignmentInfo {
  id: number;
  title: string;
  description: string;
  dueDate: string;
  totalPoints: number;
  totalSubmissions: number;
  gradedSubmissions: number;
  latePolicy?: "allow" | "block" | "penalty";
  latePenaltyPct?: number;
  rubric: RubricCriterion[];
}

const AssignmentGrading: React.FC = () => {
  const navigate = useNavigate();
  const { assignmentId } = useParams();

  const [assignment, setAssignment] = useState<AssignmentInfo | null>(null);
  const [submissions, setSubmissions] = useState<StudentSubmission[]>([]);
  const [selectedSubmission, setSelectedSubmission] =
    useState<StudentSubmission | null>(null);
  const [grade, setGrade] = useState<number>(0);
  const [feedback, setFeedback] = useState("");
  const [rubricScores, setRubricScores] = useState<RubricScoreEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [filterStatus, setFilterStatus] = useState<
    "all" | "submitted" | "graded"
  >("all");
  const [searchQuery, setSearchQuery] = useState("");

  // Load assignment and submissions
  useEffect(() => {
    const loadData = async () => {
      if (!assignmentId) return;

      try {
        // Get submissions from API
        const response = await api.get(
          `/assignments/${assignmentId}/submissions`,
        );
        const submissionsData = response.data.submissions;
        const gradedCount = submissionsData.filter(
          (s: any) => s.status === "graded",
        ).length;

        // Resolve the real assignment details (title, points, rubric, late
        // policy) via the course-scoped endpoint — the basic
        // /assignments/{id} lookup only carries course_id + title.
        let assignmentInfo: AssignmentInfo = {
          id: parseInt(assignmentId),
          title: "Assignment",
          description: "",
          dueDate: new Date().toISOString(),
          totalPoints: 100,
          totalSubmissions: submissionsData.length,
          gradedSubmissions: gradedCount,
          rubric: [],
        };
        try {
          const basic = await api.get(`/assignments/${assignmentId}`);
          const courseId = basic.data.course_id;
          if (courseId) {
            const full = await api.get(
              `/courses/${courseId}/assignments/${assignmentId}`,
            );
            const data = full.data;
            assignmentInfo = {
              id: parseInt(assignmentId),
              title: data.title || "Assignment",
              description: data.description || "",
              dueDate: data.dueDate || new Date().toISOString(),
              totalPoints: data.totalPoints ?? 100,
              totalSubmissions: submissionsData.length,
              gradedSubmissions: gradedCount,
              latePolicy: data.latePolicy,
              latePenaltyPct: data.latePenaltyPct,
              rubric: data.rubric || [],
            };
          }
        } catch (detailError) {
          console.error("Failed to load full assignment details:", detailError);
        }

        // Map submissions to our interface
        const mappedSubmissions: StudentSubmission[] = submissionsData.map(
          (sub: any) => {
            return {
              id: sub.id,
              studentId: sub.studentId,
              studentName: sub.studentName,
              studentEmail: sub.studentEmail,
              submittedAt: sub.submittedAt,
              textContent: sub.textContent || "",
              files: sub.files || [],
              grade: sub.grade,
              feedback: sub.feedback || "",
              status: sub.status,
              gradedByRole: sub.gradedByRole ?? null,
              isLate: !!sub.isLate,
              rubricScores: sub.rubricScores || null,
            };
          },
        );

        setAssignment(assignmentInfo);
        setSubmissions(mappedSubmissions);

        // Select first ungraded submission by default
        const firstUngraded = mappedSubmissions.find(
          (s) => s.status === "submitted",
        );
        if (firstUngraded) {
          setSelectedSubmission(firstUngraded);
          setGrade(firstUngraded.grade || 0);
          setFeedback(firstUngraded.feedback || "");
          setRubricScores(firstUngraded.rubricScores || []);
        }
      } catch (error) {
        toast.error("Failed to load submissions");
        console.error(error);
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, [assignmentId]);

  // Select submission
  const handleSelectSubmission = (submission: StudentSubmission) => {
    setSelectedSubmission(submission);
    setGrade(submission.grade || 0);
    setFeedback(submission.feedback || "");
    setRubricScores(submission.rubricScores || []);
  };

  // Build the grade-endpoint payload: rubricScores are included whenever the
  // assignment has a rubric and at least one score was entered — the
  // backend still lets an explicit `grade` field win over the rubric sum
  // (see grade_submission), so sending both is safe.
  const buildGradePayload = () => {
    const payload: any = { grade, feedback };
    if (assignment && assignment.rubric.length > 0 && rubricScores.length > 0) {
      payload.rubricScores = rubricScores;
    }
    return payload;
  };

  // Save grade (draft)

  // Return assignment as invalid (without grading)
  const handleReturnAssignment = async () => {
    if (!selectedSubmission) return;

    if (!feedback.trim()) {
      toast.error(
        "Please provide feedback explaining why the assignment is being returned",
      );
      return;
    }

    const confirmReturn = await confirmDialog(
      "Are you sure you want to return this assignment as invalid? The student will need to resubmit.",
    );
    if (!confirmReturn) return;

    setSaving(true);
    try {
      await api.post(`/submissions/${selectedSubmission.id}/return`, {
        feedback: feedback,
      });

      // Update local state
      setSubmissions((prev) =>
        prev.map((s) =>
          s.id === selectedSubmission.id
            ? { ...s, feedback, status: "returned" }
            : s,
        ),
      );

      toast.success("Assignment returned to student for revision");

      // Move to next ungraded submission
      const nextUngraded = submissions.find(
        (s) => s.id !== selectedSubmission.id && s.status === "submitted",
      );
      if (nextUngraded) {
        handleSelectSubmission(nextUngraded);
      }
    } catch (error: any) {
      toast.error(
        error.response?.data?.detail || "Failed to return assignment",
      );
      console.error(error);
    } finally {
      setSaving(false);
    }
  };

  // Submit grade and return to student
  const handleReturnGrade = async () => {
    if (!selectedSubmission || !assignment) return;

    if (grade < 0 || grade > assignment.totalPoints) {
      toast.error(`Grade must be between 0 and ${assignment.totalPoints}`);
      return;
    }

    if (!feedback.trim()) {
      const ok = await confirmDialog(
        "Return this grade without feedback? The learner will only see the marks.",
        { confirmLabel: "Return without feedback" },
      );
      if (!ok) return;
    }

    setSaving(true);
    try {
      const response = await api.post(
        `/submissions/${selectedSubmission.id}/grade`,
        buildGradePayload(),
      );

      // Update local state
      setSubmissions((prev) =>
        prev.map((s) =>
          s.id === selectedSubmission.id
            ? {
                ...s,
                grade: response.data.grade ?? grade,
                rawGrade: response.data.rawGrade,
                feedback,
                status: "graded",
                rubricScores,
              }
            : s,
        ),
      );

      // Check response for certificate issuance
      if (response.data.certificate_issued) {
        toast.success(
          "🎉 Certificate issued to student! All assignments completed.",
          {
            duration: 5000,
          },
        );
      } else if (response.data.all_assignments_graded) {
        toast.success(
          "All assignments graded! Student needs to complete course for certificate.",
        );
      } else {
        toast.success("Grade returned to student");
      }

      // Move to next ungraded submission
      const nextUngraded = submissions.find(
        (s) => s.status === "submitted" && s.id !== selectedSubmission.id,
      );
      if (nextUngraded) {
        handleSelectSubmission(nextUngraded);
      }
    } catch (error: any) {
      toast.error(error.response?.data?.detail || "Failed to return grade");
      console.error(error);
    } finally {
      setSaving(false);
    }
  };

  // Quick-approve: sign off a submission at full marks without hand-entering a
  // grade. Instructor approval is the primary path here; an admin using the same
  // action is the fallback when the instructor doesn't get to it.
  const handleApprove = async () => {
    if (!selectedSubmission || !assignment) return;

    setSaving(true);
    try {
      const response = await api.post(
        `/submissions/${selectedSubmission.id}/grade`,
        {
          grade: assignment.totalPoints,
          feedback: feedback.trim() || "Approved",
        },
      );

      setGrade(assignment.totalPoints);
      setSubmissions((prev) =>
        prev.map((s) =>
          s.id === selectedSubmission.id
            ? {
                ...s,
                grade: response.data.grade ?? assignment.totalPoints,
                rawGrade: response.data.rawGrade,
                feedback: feedback.trim() || "Approved",
                status: "graded",
              }
            : s,
        ),
      );

      if (response.data.certificate_issued) {
        toast.success("🎉 Approved — certificate issued to student!", {
          duration: 5000,
        });
      } else {
        toast.success("Submission approved");
      }

      // Advance to the next ungraded submission.
      const nextUngraded = submissions.find(
        (s) => s.status === "submitted" && s.id !== selectedSubmission.id,
      );
      if (nextUngraded) {
        handleSelectSubmission(nextUngraded);
      }
    } catch (error: any) {
      toast.error(
        error.response?.data?.detail || "Failed to approve submission",
      );
      console.error(error);
    } finally {
      setSaving(false);
    }
  };

  // Format file size
  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return bytes + " B";
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
    return (bytes / (1024 * 1024)).toFixed(1) + " MB";
  };

  // Filter submissions
  const filteredSubmissions = submissions.filter((s) => {
    if (filterStatus !== "all" && s.status !== filterStatus) return false;
    if (
      searchQuery &&
      !s.studentName.toLowerCase().includes(searchQuery.toLowerCase())
    )
      return false;
    return true;
  });

  if (loading) {
    return (
      <div className="min-h-screen bg-neutral-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto"></div>
          <p className="mt-4 text-neutral-600">Loading submissions...</p>
        </div>
      </div>
    );
  }

  if (!assignment) {
    return (
      <div className="min-h-screen bg-neutral-50 flex items-center justify-center">
        <div className="text-center">
          <p className="text-neutral-600">Assignment not found</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-neutral-50">
      <div className="flex h-screen">
        {/* Submissions Sidebar */}
        <div className="w-80 bg-white border-r border-neutral-200 flex flex-col">
          {/* Sidebar Header */}
          <div className="p-4 border-b border-neutral-200">
            <button onClick={() => navigate(-1)} className="btn btn-ghost mb-4">
              <ArrowLeft className="w-5 h-5 mr-2" />
              Back
            </button>

            <h2 className="text-lg font-bold text-neutral-900 mb-2">
              {assignment.title}
            </h2>

            <div className="flex items-center gap-4 text-sm text-neutral-600">
              <span>{assignment.totalSubmissions} submissions</span>
              <span>{assignment.gradedSubmissions} graded</span>
            </div>

            {/* Search */}
            <div className="mt-4 relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-400" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search students..."
                className="input input-sm w-full pl-10"
              />
            </div>

            {/* Filter */}
            <div className="mt-3 flex gap-2">
              <button
                onClick={() => setFilterStatus("all")}
                className={`btn btn-sm flex-1 ${
                  filterStatus === "all" ? "btn-primary" : "btn-outline"
                }`}
              >
                All
              </button>
              <button
                onClick={() => setFilterStatus("submitted")}
                className={`btn btn-sm flex-1 ${
                  filterStatus === "submitted" ? "btn-primary" : "btn-outline"
                }`}
              >
                Ungraded
              </button>
              <button
                onClick={() => setFilterStatus("graded")}
                className={`btn btn-sm flex-1 ${
                  filterStatus === "graded" ? "btn-primary" : "btn-outline"
                }`}
              >
                Graded
              </button>
            </div>
          </div>

          {/* Submissions List */}
          <div className="flex-1 overflow-y-auto">
            {filteredSubmissions.map((submission) => (
              <button
                key={submission.id}
                onClick={() => handleSelectSubmission(submission)}
                className={`w-full text-left p-4 border-b border-neutral-200 hover:bg-neutral-50 transition-colors ${
                  selectedSubmission?.id === submission.id
                    ? "bg-primary-50 border-l-4 border-l-primary-600"
                    : ""
                }`}
              >
                <div className="flex items-start justify-between mb-2">
                  <h3 className="font-semibold text-neutral-900 text-sm">
                    {submission.studentName}
                  </h3>
                  {submission.status === "graded" ||
                  submission.status === "returned" ? (
                    <CheckCircle2 className="w-4 h-4 text-success-600 flex-shrink-0" />
                  ) : (
                    <div className="w-2 h-2 bg-primary-600 rounded-full flex-shrink-0 mt-1" />
                  )}
                </div>

                <p className="text-xs text-neutral-600 mb-2 flex items-center gap-2">
                  {new Date(submission.submittedAt).toLocaleString()}
                  {submission.isLate && (
                    <span className="badge badge-sm bg-danger-100 text-danger-700">
                      Late
                    </span>
                  )}
                </p>

                {submission.grade !== undefined && (
                  <div className="text-xs font-semibold text-primary-700">
                    Grade: {submission.grade}/{assignment.totalPoints}
                  </div>
                )}
              </button>
            ))}

            {filteredSubmissions.length === 0 && (
              <div className="p-8 text-center text-neutral-500 text-sm">
                No submissions found
              </div>
            )}
          </div>
        </div>

        {/* Main Content */}
        <div className="flex-1 overflow-y-auto">
          {selectedSubmission ? (
            <div className="p-8 max-w-5xl mx-auto">
              {/* Student Info */}
              <div
                className="bg-white rounded-xl shadow-soft p-6 mb-6"
                data-glass="content"
              >
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-4">
                    <div className="w-12 h-12 bg-primary-100 rounded-full flex items-center justify-center">
                      <User className="w-6 h-6 text-primary-600" />
                    </div>
                    <div>
                      <h2 className="text-xl font-bold text-neutral-900 flex items-center gap-2">
                        {selectedSubmission.studentName}
                        {selectedSubmission.isLate && (
                          <span className="badge bg-danger-100 text-danger-700">
                            Late submission
                          </span>
                        )}
                      </h2>
                      <p className="text-neutral-600 text-sm">
                        {selectedSubmission.studentEmail}
                      </p>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="flex items-center gap-2 text-neutral-600 text-sm mb-1">
                      <Calendar className="w-4 h-4" />
                      <span>
                        {new Date(
                          selectedSubmission.submittedAt,
                        ).toLocaleDateString()}
                      </span>
                    </div>
                    <div className="flex items-center gap-2 text-neutral-600 text-sm">
                      <Clock className="w-4 h-4" />
                      <span>
                        {new Date(
                          selectedSubmission.submittedAt,
                        ).toLocaleTimeString()}
                      </span>
                    </div>
                  </div>
                </div>
                {selectedSubmission.rawGrade != null &&
                  selectedSubmission.rawGrade !== selectedSubmission.grade && (
                    <div className="mt-4 text-xs text-neutral-600 bg-danger-50 border border-danger-100 rounded-lg px-3 py-2 inline-flex items-center gap-2">
                      Late penalty applied: raw score{" "}
                      {selectedSubmission.rawGrade} &rarr; penalized grade{" "}
                      {selectedSubmission.grade}
                    </div>
                  )}
              </div>

              {/* Submission Content */}
              <div
                className="bg-white rounded-xl shadow-soft p-6 mb-6"
                data-glass="content"
              >
                <h3 className="text-lg font-semibold text-neutral-900 mb-4">
                  Submission
                </h3>

                {selectedSubmission.textContent && (
                  <div className="prose prose-sm max-w-none text-neutral-700 mb-6">
                    {selectedSubmission.textContent}
                  </div>
                )}

                {selectedSubmission.files.length > 0 && (
                  <div>
                    <h4 className="text-sm font-semibold text-neutral-700 mb-3">
                      Attachments
                    </h4>
                    <div className="space-y-2">
                      {selectedSubmission.files.map((file) => (
                        <a
                          key={file.id}
                          href={getBackendUrl(file.url)}
                          download
                          target="_blank"
                          rel="noopener noreferrer"
                          className="flex items-center justify-between p-3 bg-neutral-50 border border-neutral-200 rounded-lg hover:bg-neutral-100 transition-colors group"
                        >
                          <div className="flex items-center gap-3">
                            <FileText className="w-5 h-5 text-primary-600" />
                            <div>
                              <p className="text-sm font-medium text-neutral-900">
                                {file.name}
                              </p>
                              <p className="text-xs text-neutral-500">
                                {formatFileSize(file.size)}
                              </p>
                            </div>
                          </div>
                          <Download className="w-5 h-5 text-neutral-400 group-hover:text-primary-600 transition-colors" />
                        </a>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {/* Grading Section */}
              <div
                className="bg-white rounded-xl shadow-soft p-6 mb-6"
                data-glass="work"
              >
                <h3 className="text-lg font-semibold text-neutral-900 mb-4">
                  Grade Submission
                </h3>

                {assignment.rubric.length > 0 && (
                  <RubricScorer
                    rubric={assignment.rubric}
                    scores={rubricScores}
                    onChange={setRubricScores}
                    onUseAsGrade={(total) => setGrade(total)}
                    className="mb-6 pb-6 border-b border-neutral-100"
                  />
                )}

                <div className="mb-6">
                  <label className="block text-sm font-medium text-neutral-700 mb-2">
                    Grade (out of {assignment.totalPoints})
                  </label>
                  <div className="flex items-center gap-4">
                    <input
                      type="number"
                      min="0"
                      max={assignment.totalPoints}
                      value={grade}
                      onChange={(e) =>
                        setGrade(parseFloat(e.target.value) || 0)
                      }
                      className="input w-32"
                    />
                    <input
                      type="range"
                      min="0"
                      max={assignment.totalPoints}
                      value={grade}
                      onChange={(e) => setGrade(parseFloat(e.target.value))}
                      className="flex-1"
                    />
                    <div className="text-lg font-semibold text-neutral-900 w-16 text-right">
                      {Math.round((grade / assignment.totalPoints) * 100)}%
                    </div>
                  </div>
                </div>

                <div className="mb-6">
                  <label className="block text-sm font-medium text-neutral-700 mb-2">
                    Feedback
                  </label>
                  <textarea
                    value={feedback}
                    onChange={(e) => setFeedback(e.target.value)}
                    placeholder="Provide feedback to the student..."
                    className="input w-full min-h-[150px]"
                    rows={6}
                  />
                  <p className="text-sm text-neutral-500 mt-2">
                    {feedback.length} characters
                  </p>
                </div>

                <div className="flex gap-3">
                  <button
                    onClick={handleReturnAssignment}
                    disabled={saving}
                    className="btn btn-outline border-red-300 text-red-600 hover:bg-red-50 flex-1"
                  >
                    <XCircle className="w-5 h-5 mr-2" />
                    {saving ? "Returning..." : "Return (Invalid)"}
                  </button>
                  <button
                    onClick={handleApprove}
                    disabled={saving}
                    className="btn btn-outline border-green-300 text-green-700 hover:bg-green-50 flex-1"
                  >
                    <CheckCircle className="w-5 h-5 mr-2" />
                    {saving ? "Approving..." : "Approve"}
                  </button>
                  <button
                    onClick={handleReturnGrade}
                    disabled={saving}
                    className="btn btn-primary flex-1"
                  >
                    <CheckCircle2 className="w-5 h-5 mr-2" />
                    {saving ? "Submitting..." : "Grade & Return"}
                  </button>
                </div>

                {/* Approver audit — who signed this submission off */}
                {selectedSubmission.status === "graded" &&
                  selectedSubmission.gradedByRole && (
                    <p className="text-xs text-neutral-500 mt-3 flex items-center gap-1.5">
                      <CheckCircle className="w-3.5 h-3.5 text-green-600" />
                      Approved by{" "}
                      {selectedSubmission.gradedByRole === "admin"
                        ? "Admin"
                        : "Instructor"}
                    </p>
                  )}
              </div>
            </div>
          ) : (
            <div className="h-full flex items-center justify-center">
              <div className="text-center text-neutral-500">
                <FileText className="w-16 h-16 mx-auto mb-4 text-neutral-300" />
                <p>Select a submission to start grading</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default AssignmentGrading;
