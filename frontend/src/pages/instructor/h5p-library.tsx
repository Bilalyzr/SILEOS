import { PageLayout, PageHeader } from "@/components/design-system/PageLayout";
/**
 * Instructor H5P Library — I-H4 (Batch 2).
 *
 * Until now H5P was upload-or-nothing: H5PPicker (lesson editor) could
 * upload a package but there was no page to see your uploads, and the
 * ref-safe DELETE /h5p/{public_id} (h5p.py:372, 409-guarded while any
 * lesson references it) had zero UI callers. This page lists the
 * instructor's own uploads (title / library / status / size / attached
 * lesson count), lets them delete (surfacing the 409 detail), preview
 * ready packages in the same sandboxed player, and upload new packages
 * via the exact same uploadAndFinalizeH5P flow H5PPicker uses.
 *
 * Renders inside InstructorLayout (no page shell), same as games.tsx.
 */
import * as React from "react";
import toast from "react-hot-toast";
import {
  UploadCloud,
  Trash2,
  Eye,
  X,
  Loader2,
  AlertTriangle,
  Puzzle,
  RefreshCw,
} from "lucide-react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  listH5PContents,
  deleteH5PContent,
  uploadAndFinalizeH5P,
  H5P_CHUNKED_UPLOAD_MAX_BYTES,
  type H5PContent,
  type H5PUploadProgress,
} from "@/api/h5p";
import { H5PLesson } from "@/components/h5p/H5PLesson";

function formatBytes(bytes: number): string {
  if (!bytes || bytes <= 0) return "0 B";
  const units = ["B", "KB", "MB", "GB"];
  const i = Math.min(
    units.length - 1,
    Math.floor(Math.log(bytes) / Math.log(1024)),
  );
  const value = bytes / Math.pow(1024, i);
  return `${value >= 10 || i === 0 ? Math.round(value) : value.toFixed(1)} ${units[i]}`;
}

function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleDateString("en-IN", {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  } catch {
    return iso;
  }
}

const STATUS_CLASS: Record<H5PContent["status"], string> = {
  ready: "bg-green-600",
  uploaded: "bg-amber-500",
  failed: "bg-red-600",
};

export function InstructorH5PLibraryPage() {
  const [contents, setContents] = React.useState<H5PContent[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [loadError, setLoadError] = React.useState<string | null>(null);
  const [uploading, setUploading] = React.useState(false);
  const [uploadProgress, setUploadProgress] =
    React.useState<H5PUploadProgress | null>(null);
  const [confirmDelete, setConfirmDelete] = React.useState<H5PContent | null>(
    null,
  );
  const [deletingId, setDeletingId] = React.useState<string | null>(null);
  const [preview, setPreview] = React.useState<H5PContent | null>(null);
  const fileInputRef = React.useRef<HTMLInputElement>(null);

  const refresh = React.useCallback(async () => {
    setLoading(true);
    setLoadError(null);
    try {
      const res = await listH5PContents();
      setContents(res.contents);
    } catch (err: any) {
      setLoadError(
        err?.response?.data?.detail || "Failed to load your H5P uploads",
      );
    } finally {
      setLoading(false);
    }
  }, []);

  React.useEffect(() => {
    refresh();
  }, [refresh]);

  // Same validation + upload path as components/h5p/H5PPicker.tsx.
  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const ext = file.name.slice(file.name.lastIndexOf(".")).toLowerCase();
    if (ext !== ".h5p" && ext !== ".zip") {
      toast.error("Please select a '.h5p' or '.zip' package");
      if (fileInputRef.current) fileInputRef.current.value = "";
      return;
    }
    if (file.size > H5P_CHUNKED_UPLOAD_MAX_BYTES) {
      toast.error("File exceeds the 100MB upload limit for H5P packages");
      if (fileInputRef.current) fileInputRef.current.value = "";
      return;
    }
    setUploading(true);
    setUploadProgress({ phase: "uploading", percentage: 0 });
    try {
      await uploadAndFinalizeH5P(file, {
        title: file.name.replace(/\.(h5p|zip)$/i, ""),
        onProgress: setUploadProgress,
      });
      toast.success("H5P package uploaded and validated");
      await refresh();
    } catch (err: any) {
      toast.error(
        err?.response?.data?.detail || err?.message || "Upload failed",
      );
    } finally {
      setUploading(false);
      setUploadProgress(null);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  const handleDelete = async (content: H5PContent) => {
    setDeletingId(content.public_id);
    try {
      await deleteH5PContent(content.public_id);
      toast.success(`"${content.title}" deleted`);
      setContents((prev) =>
        prev.filter((c) => c.public_id !== content.public_id),
      );
      setConfirmDelete(null);
    } catch (err: any) {
      // 409 carries the "N lesson(s) still reference this content" detail —
      // surface it verbatim so the instructor knows what to repoint.
      toast.error(
        err?.response?.data?.detail ||
          err?.message ||
          "Failed to delete package",
        { duration: 6000 },
      );
      setConfirmDelete(null);
    } finally {
      setDeletingId(null);
    }
  };

  return (
    <PageLayout
      header={
        <PageHeader>
          <div>
            <h1 className="dash-h1 mb-1">H5P Library</h1>
            <p className="text-slate-600 text-sm">
              Interactive packages you've uploaded. Attach them to lessons from
              the course editor.
            </p>
          </div>
          <div>
            <input
              ref={fileInputRef}
              type="file"
              accept=".h5p,.zip"
              onChange={handleFileSelect}
              className="hidden"
              data-testid="h5p-library-upload-input"
            />
            <Button
              onClick={() => fileInputRef.current?.click()}
              disabled={uploading}
            >
              {uploading ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  {uploadProgress?.phase === "finalizing"
                    ? "Validating…"
                    : `Uploading… ${uploadProgress?.percentage ?? 0}%`}
                </>
              ) : (
                <>
                  <UploadCloud className="h-4 w-4 mr-2" />
                  Upload package
                </>
              )}
            </Button>
          </div>
        </PageHeader>
      }
      className="rd-screen rd-screen-instructor-h5p-library"
    >
      {loading ? (
        <Card className="p-4 space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-8 w-full dash-skeleton" />
          ))}
        </Card>
      ) : loadError ? (
        <Card className="p-8 text-center">
          <p className="text-sm text-danger-600 mb-3 inline-flex items-center gap-2">
            <AlertTriangle className="h-4 w-4" /> {loadError}
          </p>
          <div>
            <Button variant="outline" onClick={refresh}>
              <RefreshCw className="h-4 w-4 mr-2" /> Try again
            </Button>
          </div>
        </Card>
      ) : contents.length === 0 ? (
        <Card className="p-12 text-center">
          <Puzzle className="h-12 w-12 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">
            No H5P packages yet
          </h3>
          <p className="text-gray-600 mb-6">
            Author interactive content externally (e.g. lumi.education), export
            it as a .h5p file, and upload it here.
          </p>
          <Button
            onClick={() => fileInputRef.current?.click()}
            disabled={uploading}
          >
            <UploadCloud className="h-4 w-4 mr-2" />
            Upload your first package
          </Button>
        </Card>
      ) : (
        <Card className="overflow-hidden">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200 text-sm">
              <thead className="bg-gray-50 text-xs uppercase tracking-wider text-gray-500">
                <tr>
                  <th className="px-4 py-3 text-left font-medium">Title</th>
                  <th className="px-4 py-3 text-left font-medium">Library</th>
                  <th className="px-4 py-3 text-left font-medium">Status</th>
                  <th className="px-4 py-3 text-right font-medium">Size</th>
                  <th className="px-4 py-3 text-right font-medium">Attached</th>
                  <th className="px-4 py-3 text-left font-medium">Uploaded</th>
                  <th className="px-4 py-3 text-right font-medium">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 bg-white">
                {contents.map((c) => {
                  const attached = c.attached_lesson_count ?? 0;
                  return (
                    <tr key={c.public_id} className="hover:bg-gray-50">
                      <td className="px-4 py-3 font-medium text-gray-900">
                        {c.title}
                      </td>
                      <td className="px-4 py-3 text-gray-600">
                        {c.library || "—"}
                      </td>
                      <td className="px-4 py-3">
                        <Badge className={STATUS_CLASS[c.status]}>
                          {c.status}
                        </Badge>
                      </td>
                      <td className="px-4 py-3 text-right text-gray-600">
                        {formatBytes(c.size_bytes)}
                      </td>
                      <td className="px-4 py-3 text-right text-gray-600">
                        {attached > 0
                          ? `${attached} lesson${attached === 1 ? "" : "s"}`
                          : "—"}
                      </td>
                      <td className="px-4 py-3 text-gray-600">
                        {formatDate(c.created_at)}
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center justify-end gap-1">
                          {c.status === "ready" && (
                            <button
                              type="button"
                              onClick={() => setPreview(c)}
                              className="p-1.5 rounded text-slate-500 hover:text-primary-700 hover:bg-slate-100"
                              title="Preview"
                              aria-label={`Preview ${c.title}`}
                            >
                              <Eye className="h-4 w-4" />
                            </button>
                          )}
                          <button
                            type="button"
                            onClick={() => setConfirmDelete(c)}
                            disabled={deletingId === c.public_id}
                            className="p-1.5 rounded text-slate-500 hover:text-red-600 hover:bg-red-50 disabled:opacity-50"
                            title={
                              attached > 0
                                ? `Still attached to ${attached} lesson(s) — deletion will be refused`
                                : "Delete"
                            }
                            aria-label={`Delete ${c.title}`}
                          >
                            <Trash2 className="h-4 w-4" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </Card>
      )}
      {confirmDelete && (
        <div
          className="fixed inset-0 z-modal bg-black/50 flex items-center justify-center p-4"
          onClick={() => setConfirmDelete(null)}
        >
          <div
            className="bg-white rounded-2xl max-w-sm w-full p-6 shadow-2xl"
            onClick={(e) => e.stopPropagation()}
            data-glass="content"
          >
            <div className="flex items-center gap-2 text-amber-600 mb-3">
              <AlertTriangle className="w-5 h-5" />
              <p className="font-semibold text-gray-900">
                Delete this package?
              </p>
            </div>
            <p className="text-sm text-gray-600 mb-2">
              &ldquo;{confirmDelete.title}&rdquo; and its learner results will
              be permanently removed.
            </p>
            {(confirmDelete.attached_lesson_count ?? 0) > 0 && (
              <p className="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded-md px-3 py-2 mb-3">
                This package is still attached to{" "}
                {confirmDelete.attached_lesson_count} lesson(s). The server will
                refuse the delete until those lessons are removed or repointed.
              </p>
            )}
            <div className="flex justify-end gap-2 mt-4">
              <Button
                variant="outline"
                onClick={() => setConfirmDelete(null)}
                disabled={!!deletingId}
              >
                Cancel
              </Button>
              <Button
                variant="destructive"
                onClick={() => handleDelete(confirmDelete)}
                disabled={!!deletingId}
              >
                {deletingId ? "Deleting…" : "Delete"}
              </Button>
            </div>
          </div>
        </div>
      )}
      {preview && (
        <div
          className="fixed inset-0 z-modal bg-black/70 flex items-center justify-center p-4"
          onClick={() => setPreview(null)}
        >
          <div
            className="bg-white rounded-2xl max-w-3xl w-full overflow-hidden shadow-2xl"
            onClick={(e) => e.stopPropagation()}
            data-glass="content"
          >
            <div className="flex items-center justify-between px-5 py-3 border-b border-gray-100">
              <p className="font-semibold text-gray-900">{preview.title}</p>
              <button
                type="button"
                onClick={() => setPreview(null)}
                aria-label="Close preview"
                className="text-gray-400 hover:text-gray-700"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="bg-neutral-950" style={{ height: "70vh" }}>
              {/* previewOnly: same sandboxed iframe as the lesson player, but
                  result-POST and completion side effects are suppressed. */}
              <H5PLesson
                contentId={preview.public_id}
                title={preview.title}
                previewOnly
              />
            </div>
          </div>
        </div>
      )}
    </PageLayout>
  );
}

export default InstructorH5PLibraryPage;
