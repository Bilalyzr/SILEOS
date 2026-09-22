import { PageBackButton } from '@/components/routing/PageBackButton';
import { PageLayout, PageHeader } from "@/components/design-system/PageLayout";
import { useCallback } from "react";
import React, { useState, useEffect, useRef } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";
import {
  Save,
  Calendar,
  FileText,
  Upload,
  X,
  Paperclip,
  Download,
} from "lucide-react";
import toast from "react-hot-toast";
import { api } from "@/api/axios";
import { uploadDocument } from "@/api/upload";
import { useAuthStore } from "@/store/auth";
import { RubricEditor } from "@/components/assess/RubricEditor";
import type { RubricCriterion } from "@/lib/gradebook";

interface UploadedFile {
  id: string;
  name: string;
  url: string;
  size: number;
  type: string;
}

interface AssignmentSettings {
  title: string;
  description: string;
  instructions: string;
  dueDate: string;
  totalPoints: number;
  allowedFileTypes: string[];
  maxFileSize: number;
  maxFiles: number;
  submissionType: "text" | "file" | "both";
  attachments: UploadedFile[];
  status: "draft" | "published" | "closed";
  latePolicy: "allow" | "block" | "penalty";
  latePenaltyPct: number;
  rubric: RubricCriterion[];
}

const AssignmentBuilder: React.FC = () => {
  const navigate = useNavigate();
  const { courseId, assignmentId } = useParams();
  const [searchParams] = useSearchParams();
  const sectionId = searchParams.get("sectionId");
  const { user } = useAuthStore();
  const isAdmin = user?.role === "admin";

  const [settings, setSettings] = useState<AssignmentSettings>({
    title: "",
    description: "",
    instructions: "",
    dueDate: "",
    totalPoints: 100,
    allowedFileTypes: [".pdf", ".doc", ".docx", ".zip"],
    maxFileSize: 10,
    maxFiles: 5,
    submissionType: "both",
    attachments: [],
    status: "published",
    latePolicy: "allow",
    latePenaltyPct: 0,
    rubric: [],
  });

  const [saving, setSaving] = useState(false);
  const [, setLoading] = useState(false);
  const [isEditingExisting, setIsEditingExisting] = useState(false);
  const [uploading, setUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Load existing assignment if editing
  const loadAssignment = useCallback(async () => {
    setLoading(true);
    try {
      const response = await api.get(
        `/courses/${courseId}/assignments/${assignmentId}`,
      );
      const data = response.data;

      setSettings({
        title: data.title,
        description: data.description,
        instructions: data.instructions,
        dueDate: data.dueDate || "",
        totalPoints: data.totalPoints,
        allowedFileTypes: data.allowedFileTypes,
        maxFileSize: data.maxFileSize,
        maxFiles: data.maxFiles,
        submissionType: data.submissionType,
        attachments: data.attachments || [],
        status: data.status || "published",
        latePolicy: data.latePolicy || "allow",
        latePenaltyPct: data.latePenaltyPct ?? 0,
        rubric: data.rubric || [],
      });
      setIsEditingExisting(true); // Mark as editing existing assignment
    } catch (error: any) {
      console.error("Error loading assignment:", error);
      setIsEditingExisting(false); // Mark as creating new assignment
      // 401 is handled by token refresh interceptor, 404 means new assignment - don't show toast
      if (
        error.response?.status !== 404 &&
        error.response?.status !== 401 &&
        !error.config?._retry
      ) {
        toast.error("Failed to load assignment");
      }
    } finally {
      setLoading(false);
    }
  }, [assignmentId, courseId]);
  useEffect(() => {
    if (assignmentId && courseId) {
      loadAssignment();
    }
  }, [assignmentId, courseId, loadAssignment]);

  // Available file types
  const fileTypeOptions = [
    { value: ".pdf", label: "PDF" },
    { value: ".doc", label: "Word (.doc)" },
    { value: ".docx", label: "Word (.docx)" },
    { value: ".zip", label: "ZIP Archive" },
    { value: ".txt", label: "Text File" },
    { value: ".jpg", label: "JPEG Image" },
    { value: ".png", label: "PNG Image" },
    { value: ".mp4", label: "MP4 Video" },
  ];

  // Toggle file type
  const toggleFileType = (fileType: string) => {
    setSettings((prev) => ({
      ...prev,
      allowedFileTypes: prev.allowedFileTypes.includes(fileType)
        ? prev.allowedFileTypes.filter((t) => t !== fileType)
        : [...prev.allowedFileTypes, fileType],
    }));
  };

  // Handle instructor file upload (reference materials)
  const handleFileUpload = async (
    event: React.ChangeEvent<HTMLInputElement>,
  ) => {
    const selectedFiles = event.target.files;
    if (!selectedFiles) return;

    setUploading(true);

    try {
      for (let i = 0; i < selectedFiles.length; i++) {
        const file = selectedFiles[i];

        // Upload file
        const response = await uploadDocument(file, () => {});

        // Add to attachments list
        setSettings((prev) => ({
          ...prev,
          attachments: [
            ...prev.attachments,
            {
              id: response.filename,
              name: response.original_filename,
              url: response.file_url,
              size: response.size,
              type: response.content_type,
            },
          ],
        }));

        toast.success(`${file.name} uploaded successfully`);
      }
    } catch (error) {
      toast.error("Failed to upload file");
      console.error(error);
    } finally {
      setUploading(false);
      event.target.value = ""; // Reset input
    }
  };

  // Remove attachment
  const removeAttachment = (index: number) => {
    setSettings((prev) => ({
      ...prev,
      attachments: prev.attachments.filter((_, i) => i !== index),
    }));
    toast.success("File removed");
  };

  // Format file size
  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return bytes + " B";
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
    return (bytes / (1024 * 1024)).toFixed(1) + " MB";
  };

  // Export assignment to JSON
  const handleExportAssignment = () => {
    const exportData = {
      version: "1.0",
      title: settings.title,
      description: settings.description,
      instructions: settings.instructions,
      dueDate: settings.dueDate,
      totalPoints: settings.totalPoints,
      allowedFileTypes: settings.allowedFileTypes,
      maxFileSize: settings.maxFileSize,
      maxFiles: settings.maxFiles,
      submissionType: settings.submissionType,
      attachments: settings.attachments,
      status: settings.status,
      latePolicy: settings.latePolicy,
      latePenaltyPct: settings.latePenaltyPct,
      rubric: settings.rubric,
    };

    const blob = new Blob([JSON.stringify(exportData, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${settings.title.replace(/[^a-z0-9]/gi, "_").toLowerCase()}_assignment.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    toast.success("Assignment exported successfully!");
  };

  // Download template
  const handleDownloadTemplate = () => {
    const template = {
      version: "1.0",
      title: "Sample Assignment Title",
      description: "Assignment description goes here",
      instructions: "Detailed instructions for students...",
      dueDate: "",
      totalPoints: 100,
      allowedFileTypes: [".pdf", ".doc", ".docx", ".zip"],
      maxFileSize: 10,
      maxFiles: 5,
      submissionType: "both",
      attachments: [],
    };

    const blob = new Blob([JSON.stringify(template, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "assignment_template.json";
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    toast.success("Template downloaded!");
  };

  // Import assignment from JSON
  const handleImportAssignment = (
    event: React.ChangeEvent<HTMLInputElement>,
  ) => {
    const file = event.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const data = JSON.parse(e.target?.result as string);

        // Validate basic structure
        const validSubmissionTypes = ["text", "file", "both"];

        // Update settings if provided
        if (data.title) setSettings((prev) => ({ ...prev, title: data.title }));
        if (data.description !== undefined)
          setSettings((prev) => ({ ...prev, description: data.description }));
        if (data.instructions !== undefined)
          setSettings((prev) => ({ ...prev, instructions: data.instructions }));
        if (data.dueDate !== undefined)
          setSettings((prev) => ({ ...prev, dueDate: data.dueDate }));
        if (data.totalPoints !== undefined)
          setSettings((prev) => ({ ...prev, totalPoints: data.totalPoints }));
        if (data.allowedFileTypes && Array.isArray(data.allowedFileTypes)) {
          setSettings((prev) => ({
            ...prev,
            allowedFileTypes: data.allowedFileTypes,
          }));
        }
        if (data.maxFileSize !== undefined)
          setSettings((prev) => ({ ...prev, maxFileSize: data.maxFileSize }));
        if (data.maxFiles !== undefined)
          setSettings((prev) => ({ ...prev, maxFiles: data.maxFiles }));
        if (
          data.submissionType &&
          validSubmissionTypes.includes(data.submissionType)
        ) {
          setSettings((prev) => ({
            ...prev,
            submissionType: data.submissionType,
          }));
        }
        if (data.attachments && Array.isArray(data.attachments)) {
          setSettings((prev) => ({ ...prev, attachments: data.attachments }));
        }
        if (["draft", "published", "closed"].includes(data.status)) {
          setSettings((prev) => ({ ...prev, status: data.status }));
        }
        if (["allow", "block", "penalty"].includes(data.latePolicy)) {
          setSettings((prev) => ({ ...prev, latePolicy: data.latePolicy }));
        }
        if (data.latePenaltyPct !== undefined) {
          setSettings((prev) => ({
            ...prev,
            latePenaltyPct: data.latePenaltyPct,
          }));
        }
        if (data.rubric && Array.isArray(data.rubric)) {
          setSettings((prev) => ({ ...prev, rubric: data.rubric }));
        }

        toast.success("Assignment imported successfully!");
      } catch (error) {
        console.error("Import error:", error);
        toast.error(
          "Failed to parse assignment file. Please check the format.",
        );
      }
    };

    reader.readAsText(file);

    // Reset input
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  // Save assignment
  const handleSave = async () => {
    if (!settings.title.trim()) {
      toast.error("Please enter an assignment title");
      return;
    }

    if (!settings.description.trim()) {
      toast.error("Please enter a description");
      return;
    }

    if (
      settings.submissionType === "file" ||
      settings.submissionType === "both"
    ) {
      if (settings.allowedFileTypes.length === 0) {
        toast.error("Please select at least one allowed file type");
        return;
      }
    }

    setSaving(true);
    try {
      const assignmentData = {
        title: settings.title,
        description: settings.description,
        instructions: settings.instructions,
        dueDate: settings.dueDate,
        totalPoints: settings.totalPoints,
        allowedFileTypes: settings.allowedFileTypes,
        maxFileSize: settings.maxFileSize,
        maxFiles: settings.maxFiles,
        submissionType: settings.submissionType,
        attachments: settings.attachments,
        status: settings.status,
        latePolicy: settings.latePolicy,
        latePenaltyPct: settings.latePenaltyPct,
        rubric: settings.rubric,
      };

      let savedAssignId: string | undefined;
      if (isEditingExisting) {
        // Update existing assignment
        await api.put(
          `/courses/${courseId}/assignments/${assignmentId}`,
          assignmentData,
        );
        savedAssignId = assignmentId;
        toast.success("Assignment updated successfully!");
      } else {
        // Create new assignment
        const aResp = await api.post(
          `/courses/${courseId}/assignments`,
          assignmentData,
        );
        savedAssignId = aResp?.data?.id?.toString() || assignmentId;
        toast.success("Assignment created successfully!");
      }

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
          const newAssignId = `assignment-${savedAssignId}`;
          const inSection = sections.some((s: any) =>
            s.lectureIds?.includes(newAssignId),
          );
          if (!inSection) {
            sections = sections.map((s: any) =>
              s.id === sectionId
                ? { ...s, lectureIds: [...(s.lectureIds || []), newAssignId] }
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
      toast.error(error.response?.data?.detail || "Failed to save assignment");
      console.error(error);
    } finally {
      setSaving(false);
    }
  };

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
                    {assignmentId ? "Edit Assignment" : "Create New Assignment"}
                  </h1>
                </div>
              </div>
              <div className="flex items-center gap-3">
                {/* Export/Import Buttons */}
                <button
                  onClick={handleExportAssignment}
                  className="btn btn-outline"
                  title="Export assignment"
                >
                  <Download className="w-4 h-4 mr-2" />
                  Export
                </button>
                <button
                  onClick={handleDownloadTemplate}
                  className="btn btn-outline"
                  title="Download template"
                >
                  <Download className="w-4 h-4 mr-2" />
                  Template
                </button>
                <button
                  onClick={() => fileInputRef.current?.click()}
                  className="btn btn-outline"
                  title="Import assignment"
                >
                  <Upload className="w-4 h-4 mr-2" />
                  Import
                </button>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".json"
                  onChange={handleImportAssignment}
                  className="hidden"
                />
                <button
                  onClick={handleSave}
                  disabled={saving}
                  className="btn btn-primary"
                >
                  <Save className="w-5 h-5 mr-2" />
                  {saving ? "Saving..." : "Save Assignment"}
                </button>
              </div>
            </div>
          </PageHeader>
        }
        className="rd-screen rd-screen-instructor-assignment-builder"
      >
        <div
          className="bg-white rounded-xl shadow-soft p-6 mb-6"
          data-glass="work"
        >
          <h2 className="text-xl font-semibold text-neutral-900 mb-4">
            Basic Information
          </h2>

          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-neutral-700 mb-2">
                Assignment Title *
              </label>
              <input
                type="text"
                value={settings.title}
                onChange={(e) =>
                  setSettings({ ...settings, title: e.target.value })
                }
                placeholder="e.g., Project 1: Build a Landing Page"
                className="input w-full"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-neutral-700 mb-2">
                Description *
              </label>
              <textarea
                value={settings.description}
                onChange={(e) =>
                  setSettings({ ...settings, description: e.target.value })
                }
                placeholder="Brief description of the assignment..."
                className="input w-full"
                rows={3}
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-neutral-700 mb-2">
                Instructions
              </label>
              <textarea
                value={settings.instructions}
                onChange={(e) =>
                  setSettings({ ...settings, instructions: e.target.value })
                }
                placeholder="Detailed instructions for students..."
                className="input w-full min-h-[200px]"
                rows={8}
              />
              <p className="text-sm text-neutral-500 mt-1">
                You can use HTML formatting in the instructions
              </p>
            </div>

            {/* Reference Files for Students */}
            <div>
              <label className="block text-sm font-medium text-neutral-700 mb-2">
                <Paperclip className="w-4 h-4 inline mr-1" />
                Reference Files (Optional)
              </label>
              <p className="text-sm text-neutral-600 mb-3">
                Upload reference materials, templates, or examples for students
                to download
              </p>

              <div className="border-2 border-dashed border-neutral-300 rounded-lg p-4 text-center">
                <input
                  type="file"
                  multiple
                  onChange={handleFileUpload}
                  disabled={uploading}
                  className="hidden"
                  id="reference-files-upload"
                />
                <label
                  htmlFor="reference-files-upload"
                  className={`btn btn-outline ${uploading ? "opacity-50 cursor-not-allowed" : "cursor-pointer"}`}
                >
                  <Upload className="w-4 h-4 mr-2" />
                  {uploading ? "Uploading..." : "Upload Reference Files"}
                </label>
                <p className="text-xs text-neutral-500 mt-2">
                  PDF, Word documents, images, or other helpful materials
                </p>
              </div>

              {/* Uploaded Files List */}
              {settings.attachments.length > 0 && (
                <div className="mt-4 space-y-2">
                  {settings.attachments.map((file, index) => (
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
                        onClick={() => removeAttachment(index)}
                        className="btn btn-ghost btn-sm text-danger-600 hover:bg-danger-50 ml-2"
                      >
                        <X className="w-4 h-4" />
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
        <div
          className="bg-white rounded-xl shadow-soft p-6 mb-6"
          data-glass="work"
        >
          <h2 className="text-xl font-semibold text-neutral-900 mb-4">
            Assignment Settings
          </h2>

          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-neutral-700 mb-2">
                  <Calendar className="w-4 h-4 inline mr-1" />
                  Due Date
                </label>
                <input
                  type="datetime-local"
                  min={new Date().toISOString().slice(0, 16)}
                  value={settings.dueDate}
                  onChange={(e) =>
                    setSettings({ ...settings, dueDate: e.target.value })
                  }
                  className="input w-full"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-neutral-700 mb-2">
                  Total Points
                </label>
                <input
                  type="number"
                  min="0"
                  value={settings.totalPoints}
                  onChange={(e) =>
                    setSettings({
                      ...settings,
                      totalPoints: parseInt(e.target.value) || 0,
                    })
                  }
                  className="input w-full"
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-neutral-700 mb-2">
                Submission Type
              </label>
              <div className="flex gap-4">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="radio"
                    name="submissionType"
                    value="text"
                    checked={settings.submissionType === "text"}
                    onChange={() =>
                      setSettings({ ...settings, submissionType: "text" })
                    }
                    className="radio"
                  />
                  <span>Text Only</span>
                </label>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="radio"
                    name="submissionType"
                    value="file"
                    checked={settings.submissionType === "file"}
                    onChange={() =>
                      setSettings({ ...settings, submissionType: "file" })
                    }
                    className="radio"
                  />
                  <span>File Upload Only</span>
                </label>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="radio"
                    name="submissionType"
                    value="both"
                    checked={settings.submissionType === "both"}
                    onChange={() =>
                      setSettings({ ...settings, submissionType: "both" })
                    }
                    className="radio"
                  />
                  <span>Text & File Upload</span>
                </label>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-neutral-700 mb-2">
                  Status
                </label>
                <select
                  value={settings.status}
                  onChange={(e) =>
                    setSettings({
                      ...settings,
                      status: e.target.value as AssignmentSettings["status"],
                    })
                  }
                  className="input w-full"
                >
                  <option value="draft">Draft (hidden from students)</option>
                  <option value="published">
                    Published (visible + submittable)
                  </option>
                  <option value="closed">
                    Closed (visible, no new submissions)
                  </option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-neutral-700 mb-2">
                  Late submission policy
                </label>
                <select
                  value={settings.latePolicy}
                  onChange={(e) =>
                    setSettings({
                      ...settings,
                      latePolicy: e.target
                        .value as AssignmentSettings["latePolicy"],
                    })
                  }
                  className="input w-full"
                >
                  <option value="allow">
                    Allow (flagged as late, no penalty)
                  </option>
                  <option value="penalty">
                    Penalty (flagged as late, grade reduced)
                  </option>
                  <option value="block">Block (rejected after due date)</option>
                </select>
              </div>
            </div>

            {settings.latePolicy === "penalty" && (
              <div>
                <label className="block text-sm font-medium text-neutral-700 mb-2">
                  Late penalty (% deducted from the raw grade)
                </label>
                <input
                  type="number"
                  min="0"
                  max="100"
                  value={settings.latePenaltyPct}
                  onChange={(e) =>
                    setSettings({
                      ...settings,
                      latePenaltyPct: Math.max(
                        0,
                        Math.min(100, parseInt(e.target.value) || 0),
                      ),
                    })
                  }
                  className="input w-32"
                />
              </div>
            )}
          </div>
        </div>
        <div
          className="bg-white rounded-xl shadow-soft p-6 mb-6"
          data-glass="content"
        >
          <h2 className="text-xl font-semibold text-neutral-900 mb-4">
            Grading Rubric
          </h2>
          <RubricEditor
            rubric={settings.rubric}
            onChange={(rubric) => setSettings({ ...settings, rubric })}
          />
        </div>
        {(settings.submissionType === "file" ||
          settings.submissionType === "both") && (
          <div
            className="bg-white rounded-xl shadow-soft p-6 mb-6"
            data-glass="work"
          >
            <h2 className="text-xl font-semibold text-neutral-900 mb-4">
              <Upload className="w-5 h-5 inline mr-2" />
              File Upload Settings
            </h2>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-neutral-700 mb-2">
                  Allowed File Types *
                </label>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                  {fileTypeOptions.map((option) => (
                    <label
                      key={option.value}
                      className="flex items-center gap-2 cursor-pointer"
                    >
                      <input
                        type="checkbox"
                        checked={settings.allowedFileTypes.includes(
                          option.value,
                        )}
                        onChange={() => toggleFileType(option.value)}
                        className="checkbox"
                      />
                      <span className="text-sm">{option.label}</span>
                    </label>
                  ))}
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-neutral-700 mb-2">
                    Maximum File Size (MB)
                  </label>
                  <input
                    type="number"
                    min="1"
                    max="100"
                    value={settings.maxFileSize}
                    onChange={(e) =>
                      setSettings({
                        ...settings,
                        maxFileSize: parseInt(e.target.value) || 1,
                      })
                    }
                    className="input w-full"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-neutral-700 mb-2">
                    Maximum Number of Files
                  </label>
                  <input
                    type="number"
                    min="1"
                    max="20"
                    value={settings.maxFiles}
                    onChange={(e) =>
                      setSettings({
                        ...settings,
                        maxFiles: parseInt(e.target.value) || 1,
                      })
                    }
                    className="input w-full"
                  />
                </div>
              </div>
            </div>
          </div>
        )}
        <div
          className="bg-white rounded-xl shadow-soft p-6"
          data-glass="content"
        >
          <h2 className="text-xl font-semibold text-neutral-900 mb-4">
            Preview
          </h2>

          <div className="border border-neutral-200 rounded-lg p-6">
            <div className="flex items-start justify-between mb-4">
              <div className="flex-1">
                <h3 className="text-lg font-bold text-neutral-900 mb-2">
                  {settings.title || "Untitled Assignment"}
                </h3>
                <p className="text-neutral-600">
                  {settings.description || "No description provided"}
                </p>
              </div>
              <div className="ml-6">
                <span className="badge badge-lg bg-primary-100 text-primary-700">
                  {settings.totalPoints} points
                </span>
              </div>
            </div>

            <div className="flex items-center gap-6 text-sm text-neutral-600 mb-4">
              {settings.dueDate && (
                <div className="flex items-center gap-2">
                  <Calendar className="w-4 h-4" />
                  <span>
                    Due: {new Date(settings.dueDate).toLocaleString()}
                  </span>
                </div>
              )}
              <div className="flex items-center gap-2">
                <FileText className="w-4 h-4" />
                <span>
                  {settings.submissionType === "text" && "Text submission"}
                  {settings.submissionType === "file" && "File upload"}
                  {settings.submissionType === "both" && "Text & file upload"}
                </span>
              </div>
            </div>

            {settings.instructions && (
              <div className="border-t border-neutral-200 pt-4">
                <h4 className="font-semibold text-neutral-900 mb-2">
                  Instructions
                </h4>
                <div className="prose prose-sm max-w-none text-neutral-700 whitespace-pre-wrap">
                  {settings.instructions}
                </div>
              </div>
            )}

            {(settings.submissionType === "file" ||
              settings.submissionType === "both") && (
              <div className="border-t border-neutral-200 pt-4 mt-4">
                <h4 className="font-semibold text-neutral-900 mb-2">
                  File Upload Requirements
                </h4>
                <ul className="text-sm text-neutral-600 space-y-1">
                  <li>
                    • Allowed types: {settings.allowedFileTypes.join(", ")}
                  </li>
                  <li>• Maximum file size: {settings.maxFileSize}MB</li>
                  <li>• Maximum number of files: {settings.maxFiles}</li>
                </ul>
              </div>
            )}
          </div>
        </div>
      </PageLayout>
    </div>
  );
};

export default AssignmentBuilder;
