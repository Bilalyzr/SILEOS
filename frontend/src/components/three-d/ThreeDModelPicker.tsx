/**
 * 3D model authoring card for the course editor (MP/UP courses).
 * Upload a GLB or pick from your library — attached models show an INLINE
 * live preview so the instructor sees exactly what students will see.
 */
import { lazy, Suspense, useEffect, useRef, useState } from "react";
import toast from "react-hot-toast";
const ThreeDViewer = lazy(() =>
  import("./ThreeDViewer").then((m) => ({ default: m.ThreeDViewer })),
);
import { threeDAPI, type ThreeDModel } from "@/api/threeD";
import { useAuthStore } from "@/store/auth";

export function ThreeDModelPicker({
  title,
  attachedId,
  onAttach,
}: {
  title: string;
  attachedId: number | null;
  onAttach: (modelId: number) => void;
}) {
  const [models, setModels] = useState<ThreeDModel[]>([]);
  const [library, setLibrary] = useState<ThreeDModel[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [restoring, setRestoring] = useState(false);
  const role = useAuthStore(state => state.user?.role);
  const fileRef = useRef<HTMLInputElement>(null);

  const reload = () => {
    threeDAPI
      .list()
      .then((d) => {
        setModels(d.models);
        setLibrary(d.library || []);
      })
      .catch(() => toast.error("Failed to load your 3D models"))
      .finally(() => setLoading(false));
  };
  useEffect(reload, []);

  async function upload(f: File | undefined) {
    if (!f) return;
    setUploading(true);
    try {
      const m = await threeDAPI.upload(title || "3D Model", f);
      toast.success("GLB uploaded");
      reload();
      onAttach(m.id);
    } catch (e: unknown) {
      const detail = (e as { response?: { data?: { detail?: string } } })
        ?.response?.data?.detail;
      toast.error(typeof detail === "string" ? detail : "Upload failed");
    } finally {
      setUploading(false);
    }
  }

  async function restoreLibrary() {
    setRestoring(true);
    try {
      const result = await threeDAPI.restoreLibrary();
      toast.success(`${result.models.length} included models are available`);
      reload();
    } catch {
      toast.error("Could not restore the included models. Check the release assets.");
    } finally { setRestoring(false); }
  }

  return (
    <div className="mt-3 p-4 astra-work border border-orange-200 rounded-lg">
      <h5 className="font-medium text-gray-900 mb-1">3D Model (GLB)</h5>
      {attachedId ? (
        <div>
          <div className="flex items-center gap-3 mb-3">
            <span className="text-sm font-medium text-emerald-700">
              ✓ Attached (model #{attachedId})
            </span>
            <button
              type="button"
              className="text-sm text-orange-600 hover:underline"
              onClick={() => onAttach(0)}
            >
              Choose different
            </button>
          </div>
          <Suspense fallback={<p role="status">Loading model preview…</p>}>
            <ThreeDViewer modelId={attachedId} height={320} />
          </Suspense>
        </div>
      ) : (
        <>
          <p className="text-xs text-gray-500 mb-3">
            Upload a .glb file (max 50MB), pick one of yours, or use a shared
            library model.
          </p>
          <input
            ref={fileRef}
            type="file"
            accept=".glb"
            aria-label="Upload GLB model"
            className="hidden"
            onChange={(e) => {
              void upload(e.target.files?.[0]);
              e.target.value = "";
            }}
          />
          <div className="flex flex-wrap items-center gap-2 mb-3">
            <button
              type="button"
              onClick={() => fileRef.current?.click()}
              disabled={uploading}
              className="px-3 py-1.5 text-xs font-medium rounded-full bg-orange-600 text-white hover:bg-orange-700 disabled:opacity-40"
            >
              {uploading ? "Uploading…" : "Upload .glb"}
            </button>
            {(role === 'admin' || role === 'superadmin') && (
              <button type="button" className="sf-secondary text-xs" disabled={restoring} onClick={() => void restoreLibrary()}>
                {restoring ? 'Restoring models…' : 'Restore included 3D library'}
              </button>
            )}
          </div>
          {loading ? (
            <p className="text-xs text-gray-500">Loading your library…</p>
          ) : models.length > 0 ? (
            <ul className="space-y-1">
              {models.map((m) => (
                <li key={m.id}>
                  <button
                    type="button"
                    onClick={() => onAttach(m.id)}
                    className="w-full text-left text-sm px-3 py-2 rounded-lg border border-gray-200 hover:border-orange-400 bg-white"
                  >
                    {m.title}{" "}
                    <span className="text-xs text-gray-400">
                      ({(m.file_size_bytes / 1048576).toFixed(1)} MB)
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-xs text-gray-400">
              No uploads yet — upload a .glb above or pick a shared library
              model.
            </p>
          )}
          {library.length > 0 && (
            <div className="mt-3 border border-orange-200 bg-white/60 rounded-lg p-2">
              <p className="text-xs font-semibold text-orange-800 mb-1">
                Shared library (added by admin)
              </p>
              <ul className="space-y-1 max-h-40 overflow-y-auto">
                {library.map((m) => (
                  <li key={m.id}>
                    <button
                      type="button"
                      onClick={() => onAttach(m.id)}
                      className="w-full text-left text-sm px-3 py-2 rounded-lg border border-gray-200 hover:border-orange-400 bg-white"
                    >
                      {m.title}{" "}
                      <span className="text-xs text-gray-400">
                        ({(m.file_size_bytes / 1048576).toFixed(1)} MB · shared)
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </>
      )}
    </div>
  );
}

export default ThreeDModelPicker;
