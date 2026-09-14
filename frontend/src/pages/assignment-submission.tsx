import { PageLayout, PageHeader } from "@/components/design-system/PageLayout";
import React, { useState, useEffect } from "react";
import { sanitizeHtml } from "@/utils/sanitize";
import { useNavigate, useParams } from "react-router-dom";
import {
  Upload,
  X,
  Calendar,
  Clock,
  AlertCircle,
  CheckCircle2,
  FileText,
  Paperclip,
  Send,
} from "lucide-react";
import toast from "react-hot-toast";
import { uploadDocument } from "../api/upload";
import { getBackendUrl } from "@/config/urls";

interface AssignmentData {
  id: number;
  title: string;
  description: string;
  instructions: string;
  attachments?: (UploadedFile | string)[];
  dueDate: string;
  totalPoints: number;
  allowedFileTypes: string[];
  maxFileSize: number; // in MB
  maxFiles: number;
  submissionType: "text" | "file" | "both";
  isSubmitted: boolean;
  submission?: {
    id: number;
    textContent: string;
    files: UploadedFile[];
    submittedAt: string;
    grade?: number;
    feedback?: string;
    status: "submitted" | "graded" | "returned";
  };
}

interface UploadedFile {
  id?: string;
  name: string;
  url: string;
  size: number;
  type: string;
}

const AssignmentSubmission: React.FC = () => {
  const navigate = useNavigate();
  const { assignmentId, courseId: routeCourseId } = useParams<{
    assignmentId?: string;
    courseId?: string;
  }>();

  const [assignment, setAssignment] = useState<AssignmentData | null>(null);
  const [textContent, setTextContent] = useState("");
  const [files, setFiles] = useState<UploadedFile[]>([]);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [submitting, setSubmitting] = useState(false);
  const [loading, setLoading] = useState(true);
  const [, setCourseId] = useState<string | null>(null);

  // Load assignment data
  useEffect(() => {
    const loadAssignment = async () => {
      try {
        const { api } = await import("@/api/axios");

        // Extract numeric ID if it has a prefix like "assignment-3"
        const numericId = assignmentId?.replace(/^assignment-/, "");

        // Use courseId from route if available, otherwise fetch from assignment
        let targetCourseId = routeCourseId;
        if (!targetCourseId) {
          // Get the assignment first to find course_id
          const assignmentResponse = await api.get(`/assignments/${numericId}`);
          targetCourseId = assignmentResponse.data.course_id?.toString();
        }
        if (!targetCourseId)
          throw new Error("The assignment course could not be found");
        setCourseId(targetCourseId);

        // Get full assignment details
        const response = await api.get(
          `/courses/${targetCourseId}/assignments/${numericId}`,
        );
        const data = response.data;

        setAssignment({
          id: data.id,
          title: data.title,
          description: data.description,
          instructions: data.instructions,
          attachments: data.attachments || [],
          dueDate: data.dueDate,
          totalPoints: data.totalPoints,
          allowedFileTypes: data.allowedFileTypes,
          maxFileSize: data.maxFileSize,
          maxFiles: data.maxFiles,
          submissionType: data.submissionType,
          isSubmitted: data.isSubmitted,
          submission: data.submission,
        });

        // If already submitted, load submission data
        if (data.submission) {
          setTextContent(data.submission.textContent || "");
          setFiles(data.submission.files || []);
        }
      } catch (error) {
        toast.error("Failed to load assignment");
        console.error(error);
      } finally {
        setLoading(false);
      }
    };

    loadAssignment();
  }, [assignmentId, routeCourseId]);

  // Handle file upload
  const handleFileUpload = async (
    event: React.ChangeEvent<HTMLInputElement>,
  ) => {
    const selectedFiles = event.target.files;
    if (!selectedFiles || !assignment) return;

    // Check max files limit
    if (files.length + selectedFiles.length > assignment.maxFiles) {
      toast.error(`Maximum ${assignment.maxFiles} files allowed`);
      return;
    }

    setUploading(true);

    try {
      for (let i = 0; i < selectedFiles.length; i++) {
        const file = selectedFiles[i];

        // Check file size
        if (file.size > assignment.maxFileSize * 1024 * 1024) {
          toast.error(`${file.name} exceeds ${assignment.maxFileSize}MB limit`);
          continue;
        }

        // Check file type
        const fileExt = "." + file.name.split(".").pop()?.toLowerCase();
        if (!assignment.allowedFileTypes.includes(fileExt)) {
          toast.error(`${file.name} type not allowed`);
          continue;
        }

        // Upload file
        const response = await uploadDocument(file, (progress) => {
          setUploadProgress(progress);
        });

        // Add to files list
        setFiles((prev) => [
          ...prev,
          {
            id: response.filename,
            name: response.original_filename,
            url: response.file_url,
            size: response.size,
            type: response.content_type,
          },
        ]);

        toast.success(`${file.name} uploaded successfully`);
      }
    } catch (error) {
      toast.error("Failed to upload file");
      console.error(error);
    } finally {
      setUploading(false);
      setUploadProgress(0);
      event.target.value = ""; // Reset input
    }
  };

  // Remove file
  const removeFile = (index: number) => {
    setFiles((prev) => prev.filter((_, i) => i !== index));
    toast.success("File removed");
  };

  // Submit assignment
  const handleSubmit = async () => {
    if (!assignment) return;

    // Validation
    if (
      assignment.submissionType === "text" ||
      assignment.submissionType === "both"
    ) {
      if (!textContent.trim()) {
        toast.error("Please enter your submission text");
        return;
      }
    }

    if (
      assignment.submissionType === "file" ||
      assignment.submissionType === "both"
    ) {
      if (files.length === 0) {
        toast.error("Please upload at least one file");
        return;
      }
    }

    // Extract numeric ID if it has a prefix like "assignment-3"
    const numericId = assignmentId?.replace(/^assignment-/, "");
    if (!numericId) {
      toast.error("Invalid assignment ID");
      return;
    }

    setSubmitting(true);
    try {
      const { api } = await import("@/api/axios");
      await api.post(`/assignments/${numericId}/submit`, {
        textContent: textContent,
        files: files,
      });

      toast.success("Assignment submitted successfully!");
      navigate(-1);
    } catch (error) {
      toast.error("Failed to submit assignment");
      console.error(error);
    } finally {
      setSubmitting(false);
    }
  };

  // Format file size
  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return bytes + " B";
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
    return (bytes / (1024 * 1024)).toFixed(1) + " MB";
  };

  // Calculate time remaining
  const getTimeRemaining = (
    dueDate: string,
  ): { text: string; isOverdue: boolean; isSoon: boolean } => {
    const now = new Date();
    const due = new Date(dueDate);
    const diff = due.getTime() - now.getTime();

    if (diff < 0) {
      return { text: "Overdue", isOverdue: true, isSoon: false };
    }

    const days = Math.floor(diff / (1000 * 60 * 60 * 24));
    const hours = Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));

    if (days > 0) {
      return {
        text: `${days} day${days > 1 ? "s" : ""} remaining`,
        isOverdue: false,
        isSoon: days <= 3,
      };
    }

    return {
      text: `${hours} hour${hours > 1 ? "s" : ""} remaining`,
      isOverdue: false,
      isSoon: true,
    };
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-neutral-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto"></div>
          <p className="mt-4 text-neutral-600">Loading assignment...</p>
        </div>
      </div>
    );
  }

  if (!assignment) {
    return (
      <div className="min-h-screen bg-neutral-50 flex items-center justify-center">
        <div className="text-center">
          <AlertCircle className="w-16 h-16 text-danger-500 mx-auto mb-4" />
          <h2 className="text-2xl font-bold text-neutral-900 mb-2">
            Assignment Not Found
          </h2>
          <button onClick={() => navigate(-1)} className="btn btn-primary mt-4">
            Go Back
          </button>
        </div>
      </div>
    );
  }

  const timeRemaining = getTimeRemaining(assignment.dueDate);
  const isReturned = assignment.submission?.status === "returned";
  const isGraded = assignment.submission?.status === "graded";
  const isViewOnly =
    (assignment.isSubmitted && !isReturned) || timeRemaining.isOverdue;

  return (
    <div className="min-h-screen bg-neutral-50 py-8">
      <PageLayout
        header={
          <PageHeader>
            <div className="flex items-start justify-between mb-4">
              <div className="flex-1">
                <h1 className="text-2xl font-bold text-neutral-900 mb-2">
                  {assignment.title}
                </h1>
                <p className="text-neutral-600">{assignment.description}</p>
              </div>
              <div className="ml-6">
                <span className="badge badge-lg bg-primary-100 text-primary-700">
                  {assignment.totalPoints} points
                </span>
              </div>
            </div>

            <div className="flex items-center gap-6 text-sm">
              <div className="flex items-center gap-2 text-neutral-600">
                <Calendar className="w-4 h-4" />
                <span>
                  Due: {new Date(assignment.dueDate).toLocaleString()}
                </span>
              </div>
              <div
                className={`flex items-center gap-2 font-medium ${
                  timeRemaining.isOverdue
                    ? "text-danger-600"
                    : timeRemaining.isSoon
                      ? "text-warning-600"
                      : "text-success-600"
                }`}
              >
                <Clock className="w-4 h-4" />
                <span>{timeRemaining.text}</span>
              </div>
            </div>

            {assignment.isSubmitted && assignment.submission && !isReturned && (
              <div
                className={`mt-4 p-4 rounded-lg ${
                  isGraded
                    ? "bg-blue-50 border border-blue-200"
                    : "bg-success-50 border border-success-200"
                }`}
              >
                <div
                  className={`flex items-center gap-2 mb-2 ${
                    isGraded ? "text-blue-700" : "text-success-700"
                  }`}
                >
                  <CheckCircle2 className="w-5 h-5" />
                  <span className="font-semibold">
                    {isGraded ? "Graded" : "Submitted"}
                  </span>
                </div>
                <p
                  className={`text-sm ${isGraded ? "text-blue-600" : "text-success-600"}`}
                >
                  Submitted on{" "}
                  {new Date(assignment.submission.submittedAt).toLocaleString()}
                </p>
                {isGraded &&
                  assignment.submission.grade !== null &&
                  assignment.submission.grade !== undefined && (
                    <p className="text-sm text-blue-700 font-semibold mt-2">
                      Grade: {assignment.submission.grade} /{" "}
                      {assignment.totalPoints}
                    </p>
                  )}
              </div>
            )}

            {timeRemaining.isOverdue && !assignment.isSubmitted && (
              <div className="mt-4 p-4 bg-danger-50 border border-danger-200 rounded-lg">
                <div className="flex items-center gap-2 text-danger-700">
                  <AlertCircle className="w-5 h-5" />
                  <span className="font-semibold">
                    This assignment is overdue
                  </span>
                </div>
              </div>
            )}
          </PageHeader>
        }
        className="rd-screen rd-screen-assignment-submission"
      >
        {isReturned && (
          <div className="bg-red-50 border-l-4 border-red-500 rounded-xl shadow-soft p-6 mb-6">
            <div className="flex items-start gap-4">
              <div className="flex-shrink-0">
                <svg
                  className="w-8 h-8 text-red-600"
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
                <h3 className="text-lg font-semibold text-red-900 mb-2">
                  Assignment Returned for Revision
                </h3>
                <p className="text-red-800 mb-4">
                  Your submission has been returned by the instructor. Please
                  review the feedback below and resubmit your assignment.
                </p>
                {assignment.submission?.feedback && (
                  <div
                    className="bg-white rounded-lg p-4 border border-red-200"
                    data-glass="content"
                  >
                    <p className="text-sm font-semibold text-neutral-900 mb-2">
                      Instructor Feedback:
                    </p>
                    <p className="text-sm text-neutral-700">
                      {assignment.submission.feedback}
                    </p>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
        <div
          className="bg-white rounded-xl shadow-soft p-6 mb-6"
          data-glass="content"
        >
          <h2 className="text-xl font-semibold text-neutral-900 mb-4">
            Instructions
          </h2>
          <div
            className="prose prose-sm max-w-none text-neutral-700"
            dangerouslySetInnerHTML={{
              __html: sanitizeHtml(assignment.instructions),
            }}
          />
        </div>
        {assignment.attachments && assignment.attachments.length > 0 && (
          <div
            className="bg-white rounded-xl shadow-soft p-6 mb-6"
            data-glass="content"
          >
            <h2 className="text-xl font-semibold text-neutral-900 mb-4">
              Reference Files
            </h2>
            <div className="space-y-2">
              {assignment.attachments.map((file, index) => {
                const fileUrl = typeof file === "string" ? file : file.url;
                const fileName =
                  typeof file === "string" ? file.split("/").pop() : file.name;
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
                    className="flex items-center gap-3 p-3 bg-neutral-50 border border-neutral-200 rounded-lg hover:bg-neutral-100 transition-colors"
                  >
                    <FileText className="w-5 h-5 text-primary-600" />
                    <div className="flex-1">
                      <p className="text-sm font-medium text-neutral-900">
                        {fileName}
                      </p>
                    </div>
                  </a>
                );
              })}
            </div>
          </div>
        )}
        {!isViewOnly && (
          <>
            {/* Text Submission */}
            {(assignment.submissionType === "text" ||
              assignment.submissionType === "both") && (
              <div
                className="bg-white rounded-xl shadow-soft p-6 mb-6"
                data-glass="work"
              >
                <h2 className="text-xl font-semibold text-neutral-900 mb-4">
                  Your Submission
                </h2>
                <textarea
                  value={textContent}
                  onChange={(e) => setTextContent(e.target.value)}
                  placeholder="Enter your submission text here..."
                  className="input w-full min-h-[300px]"
                  rows={12}
                />
                <p className="text-sm text-neutral-500 mt-2">
                  {textContent.length} characters
                </p>
              </div>
            )}

            {/* File Upload */}
            {(assignment.submissionType === "file" ||
              assignment.submissionType === "both") && (
              <div
                className="bg-white rounded-xl shadow-soft p-6 mb-6"
                data-glass="work"
              >
                <h2 className="text-xl font-semibold text-neutral-900 mb-4">
                  Attachments
                </h2>

                {/* Upload Area */}
                <div className="border-2 border-dashed border-neutral-300 rounded-lg p-8 text-center mb-4">
                  <Upload className="w-12 h-12 text-neutral-400 mx-auto mb-4" />
                  <p className="text-neutral-700 mb-2">
                    Drag and drop files here, or click to browse
                  </p>
                  <p className="text-sm text-neutral-500 mb-4">
                    Allowed: {assignment.allowedFileTypes.join(", ")} • Max
                    size: {assignment.maxFileSize}MB • Max files:{" "}
                    {assignment.maxFiles}
                  </p>
                  <input
                    type="file"
                    multiple
                    accept={assignment.allowedFileTypes.join(",")}
                    onChange={handleFileUpload}
                    disabled={uploading || files.length >= assignment.maxFiles}
                    className="hidden"
                    id="file-upload"
                  />
                  <label
                    htmlFor="file-upload"
                    className={`btn btn-primary ${
                      uploading || files.length >= assignment.maxFiles
                        ? "opacity-50 cursor-not-allowed"
                        : ""
                    }`}
                  >
                    <Paperclip className="w-5 h-5 mr-2" />
                    {uploading ? "Uploading..." : "Choose Files"}
                  </label>
                </div>

                {/* Upload Progress */}
                {uploading && (
                  <div className="mb-4">
                    <div className="flex items-center justify-between text-sm mb-2">
                      <span className="text-neutral-600">Uploading...</span>
                      <span className="text-neutral-900 font-semibold">
                        {uploadProgress}%
                      </span>
                    </div>
                    <div className="h-2 bg-neutral-200 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-primary-500 transition-all duration-300"
                        style={{ width: `${uploadProgress}%` }}
                      />
                    </div>
                  </div>
                )}

                {/* Uploaded Files List */}
                {files.length > 0 && (
                  <div className="space-y-2">
                    {files.map((file, index) => (
                      <div
                        key={index}
                        className="flex items-center justify-between p-3 bg-neutral-50 border border-neutral-200 rounded-lg"
                      >
                        <div className="flex items-center gap-3 flex-1 min-w-0">
                          <FileText className="w-5 h-5 text-primary-600 flex-shrink-0" />
                          <div className="flex-1 min-w-0">
                            <p className="text-sm font-medium text-neutral-900 truncate">
                              {file.name}
                            </p>
                            <p className="text-xs text-neutral-500">
                              {formatFileSize(file.size)}
                            </p>
                          </div>
                        </div>
                        <button
                          onClick={() => removeFile(index)}
                          className="btn btn-ghost btn-sm text-danger-600 hover:bg-danger-50 ml-2"
                        >
                          <X className="w-4 h-4" />
                        </button>
                      </div>
                    ))}
                  </div>
                )}

                {files.length === 0 && (
                  <p className="text-center text-neutral-500 text-sm py-4">
                    No files uploaded yet
                  </p>
                )}
              </div>
            )}

            {/* Submit Button */}
            <div
              className="bg-white rounded-xl shadow-soft p-6"
              data-glass="content"
            >
              <div className="flex items-center justify-between">
                <button
                  onClick={() => navigate(-1)}
                  className="btn btn-outline"
                >
                  Cancel
                </button>
                <button
                  onClick={handleSubmit}
                  disabled={submitting}
                  className="btn btn-primary"
                >
                  <Send className="w-5 h-5 mr-2" />
                  {submitting ? "Submitting..." : "Submit Assignment"}
                </button>
              </div>
            </div>
          </>
        )}
        {assignment.isSubmitted && assignment.submission && (
          <>
            {/* Submitted Text */}
            {assignment.submission.textContent && (
              <div
                className="bg-white rounded-xl shadow-soft p-6 mb-6"
                data-glass="content"
              >
                <h2 className="text-xl font-semibold text-neutral-900 mb-4">
                  Your Submission
                </h2>
                <div className="prose prose-sm max-w-none text-neutral-700">
                  {assignment.submission.textContent}
                </div>
              </div>
            )}

            {/* Submitted Files */}
            {assignment.submission.files.length > 0 && (
              <div
                className="bg-white rounded-xl shadow-soft p-6 mb-6"
                data-glass="content"
              >
                <h2 className="text-xl font-semibold text-neutral-900 mb-4">
                  Submitted Files
                </h2>
                <div className="space-y-2">
                  {assignment.submission.files.map((file, index) => (
                    <a
                      key={index}
                      href={getBackendUrl(file.url)}
                      download
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center gap-3 p-3 bg-neutral-50 border border-neutral-200 rounded-lg hover:bg-neutral-100 transition-colors"
                    >
                      <FileText className="w-5 h-5 text-primary-600" />
                      <div className="flex-1">
                        <p className="text-sm font-medium text-neutral-900">
                          {file.name}
                        </p>
                        <p className="text-xs text-neutral-500">
                          {formatFileSize(file.size)}
                        </p>
                      </div>
                    </a>
                  ))}
                </div>
              </div>
            )}

            {/* Feedback */}
            {assignment.submission.feedback && (
              <div
                className="bg-white rounded-xl shadow-soft p-6"
                data-glass="content"
              >
                <h2 className="text-xl font-semibold text-neutral-900 mb-4">
                  Instructor Feedback
                </h2>
                <div className="prose prose-sm max-w-none text-neutral-700">
                  {assignment.submission.feedback}
                </div>
              </div>
            )}
          </>
        )}
      </PageLayout>
    </div>
  );
};

export default AssignmentSubmission;
