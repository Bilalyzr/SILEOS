import { useRef, useState } from "react";
import { api } from "@/api/axios";
import { downloadLabFile } from "@/api/lab-studio";
import { useAuthStore } from "@/store/auth";

interface Pack {
  format: string;
  version: number;
  name: string;
  labs: {
    slug: string;
    title: string;
    description: string;
    published: boolean;
  }[];
}
export function SuppliedLabPack() {
  const role = useAuthStore((s) => s.user?.role);
  const admin = role === "admin" || role === "superadmin";
  const file = useRef<File | null>(null);
  const [pack, setPack] = useState<Pack | null>(null);
  const [name, setName] = useState("Sasha Virtual Labs");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  async function inspect(upload?: File) {
    if (!upload) return;
    file.current = null;
    setPack(null);
    setBusy(true);
    setMessage("");
    try {
      const form = new FormData();
      form.append("file", upload);
      const { data } = await api.post<Pack>(
        "/lab-studio/supplied-pack/inspect",
        form,
      );
      file.current = upload;
      setPack(data);
      setName(data.name);
      setMessage(
        `${data.labs.length} supplied labs verified. Review their names and visibility, then import.`,
      );
    } catch (e: any) {
      setMessage(e.response?.data?.detail || "Could not inspect this ZIP.");
    } finally {
      setBusy(false);
    }
  }
  async function restore() {
    if (!pack || !file.current) return;
    setBusy(true);
    try {
      const form = new FormData();
      form.append("file", file.current);
      form.append("manifest", JSON.stringify({ ...pack, name }));
      const { data } = await api.post("/lab-studio/supplied-pack/import", form);
      setMessage(
        `${data.imported} labs imported. Names and visibility now apply to the library and course picker.`,
      );
      setPack(null);
      file.current = null;
    } catch (e: any) {
      setMessage(
        e.response?.data?.detail ||
          "Import failed. No partial import was saved.",
      );
    } finally {
      setBusy(false);
    }
  }
  async function download() {
    setBusy(true);
    try {
      const { data } = await api.get("/lab-studio/supplied-pack/export", {
        params: { name },
        responseType: "blob",
      });
      downloadLabFile(data, "sasha-virtual-labs.zip");
    } catch {
      setMessage("Could not export the lab pack.");
    } finally {
      setBusy(false);
    }
  }
  return (
    <section className="sf-surface" aria-label="Sasha Virtual Lab Pack">
      <span className="sf-eyebrow">Your lab collection</span>
      <h2>Sasha Virtual Lab Pack</h2>
      <p>
        Import your CBSE Virtual Labs ZIP, review the 59 simulations, then
        publish their names and visibility. Export includes the original assets
        and a restore manifest.
      </p>
      <fieldset disabled={busy} className="space-y-4">
        <label className="block">
          Collection name
          <input
            className="sf-input"
            maxLength={120}
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
        </label>
        <div className="sf-actions">
          <button type="button" className="sf-secondary" onClick={download}>
            Export lab ZIP
          </button>
          {admin && (
            <label className="sf-secondary">
              Inspect & import ZIP
              <input
                type="file"
                accept=".zip"
                aria-label="Import supplied lab ZIP"
                onChange={(e) => {
                  void inspect(e.target.files?.[0]);
                  e.target.value = "";
                }}
              />
            </label>
          )}
        </div>
        {pack && (
          <details open>
            <summary>{pack.labs.length} labs ready to import</summary>
            <div className="max-h-96 overflow-y-auto space-y-3 p-2">
              {pack.labs.map((entry, i) => (
                <div
                  key={entry.slug}
                  className="flex flex-wrap gap-3 items-center"
                >
                  <input
                    aria-label={`Name for ${entry.slug}`}
                    maxLength={200}
                    value={entry.title}
                    onChange={(e) =>
                      setPack({
                        ...pack,
                        labs: pack.labs.map((v, j) =>
                          i === j ? { ...v, title: e.target.value } : v,
                        ),
                      })
                    }
                  />
                  <label>
                    <input
                      type="checkbox"
                      checked={entry.published}
                      onChange={(e) =>
                        setPack({
                          ...pack,
                          labs: pack.labs.map((v, j) =>
                            i === j ? { ...v, published: e.target.checked } : v,
                          ),
                        })
                      }
                    />{" "}
                    Visible to learners
                  </label>
                </div>
              ))}
            </div>
            <button type="button" className="sf-primary" onClick={restore}>
              Import reviewed labs
            </button>
          </details>
        )}
      </fieldset>
      <p role="status">{busy ? "Processing lab pack…" : message}</p>
      {!admin && (
        <p className="sf-muted">
          Admins manage imports and public visibility. You can export the
          collection for backup.
        </p>
      )}
    </section>
  );
}
