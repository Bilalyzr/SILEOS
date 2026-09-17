import { AstraSymbol } from "@/components/design-system/AstraSymbol";
import { PageLayout, PageHeader } from "@/components/design-system/PageLayout";
/**
 * Admin → Content Libraries (2026-09-05): three admin-curated libraries that
 * instructors pull into a curriculum.
 *   Labs      — virtual lab catalog (PhET / embed / native) + JSON pack import
 *   3D assets — shared GLB library (bulk import, share toggle)
 *   Games     — prebuilt learning games (shipped pack or JSON pack import)
 * All API calls go through src/api/labs.ts. Config JSON is never rendered
 * as HTML — text only.
 */
import React, { useCallback, useEffect, useRef, useState } from "react";
import { confirmDialog } from "@/components/ui/confirm";
import toast from "react-hot-toast";
import {
  FlaskConical,
  Box,
  Gamepad2,
  Upload,
  Trash2,
  Eye,
  EyeOff,
  Plus,
  RefreshCw,
} from "lucide-react";
import {
  contentLibraryAdmin,
  type AdminLabRow,
  type BuiltinLabRow,
  type LabCatalogEntryIn,
  type LibraryModel,
} from "@/api/labs";
import { VirtualLabPlayer } from "@/components/labs/VirtualLabPlayer";

type Tab = "labs" | "three-d" | "games";

const EMPTY_LAB: LabCatalogEntryIn = {
  slug: "",
  title: "",
  subject: "chemistry",
  description: "",
  provider: "embed",
  embed_url: "",
  native_template: null,
  config: null,
  attribution: "",
  thumbnail_url: null,
  is_published: true,
};

function errorDetail(err: any, fallback: string): string {
  const d = err?.response?.data?.detail;
  return typeof d === "string" ? d : fallback;
}

export function AdminContentLibrariesPage() {
  const [tab, setTab] = useState<Tab>("labs");
  return (
    <PageLayout
      header={
        <PageHeader>
          <h1 className="text-2xl font-bold text-gray-900">
            Content Libraries
          </h1>
          <p className="text-sm text-gray-500 mt-1">
            Curate what instructors can drop into a curriculum: virtual labs,
            shared 3D assets and prebuilt games.
          </p>
        </PageHeader>
      }
      className="rd-screen rd-screen-admin-content-libraries"
    >
      <div className="flex gap-2 border-b border-gray-200 mb-6" role="tablist">
        {(
          [
            ["labs", "Virtual Labs", FlaskConical],
            ["three-d", "3D Assets", Box],
            ["games", "Prebuilt Games", Gamepad2],
          ] as [Tab, string, React.FC<{ className?: string }>][]
        ).map(([key, label, Icon]) => (
          <button
            key={key}
            type="button"
            role="tab"
            aria-selected={tab === key}
            onClick={() => setTab(key)}
            className={`inline-flex items-center gap-2 px-4 py-2 text-sm font-medium border-b-2 -mb-px ${
              tab === key
                ? "border-orange-500 text-orange-700"
                : "border-transparent text-gray-500 hover:text-gray-800"
            }`}
          >
            <Icon className="w-4 h-4" /> {label}
          </button>
        ))}
      </div>
      {tab === "labs" && <LabsTab />}
      {tab === "three-d" && <ThreeDTab />}
      {tab === "games" && <GamesTab />}
    </PageLayout>
  );
}

// ============================================================ Labs

function LabsTab() {
  const [rows, setRows] = useState<AdminLabRow[]>([]);
  const [builtin, setBuiltin] = useState<BuiltinLabRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [form, setForm] = useState<LabCatalogEntryIn>(EMPTY_LAB);
  const [configText, setConfigText] = useState("");
  const [editingId, setEditingId] = useState<number | null>(null);
  const [saving, setSaving] = useState(false);
  const [previewSlug, setPreviewSlug] = useState<string | null>(null);
  const [packText, setPackText] = useState("");
  const [showForm, setShowForm] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const d = await contentLibraryAdmin.listLabs();
      setRows(d.labs);
      setBuiltin(d.builtin);
    } catch (err) {
      toast.error(errorDetail(err, "Failed to load the lab catalog"));
    } finally {
      setLoading(false);
    }
  }, []);
  useEffect(() => {
    load();
  }, [load]);

  const startEdit = (r: AdminLabRow) => {
    setEditingId(r.catalog_id);
    setForm({
      slug: r.slug,
      title: r.title,
      subject: r.subject,
      description: r.description || "",
      provider: r.provider,
      embed_url: r.embed_url || "",
      native_template: r.native_template || null,
      config: r.config || null,
      attribution: r.attribution || "",
      thumbnail_url: r.thumbnail_url || null,
      is_published: r.is_published,
    });
    setConfigText(r.config ? JSON.stringify(r.config, null, 2) : "");
    setShowForm(true);
  };

  const resetForm = () => {
    setEditingId(null);
    setForm(EMPTY_LAB);
    setConfigText("");
    setShowForm(false);
  };

  const save = async () => {
    let config: Record<string, unknown> | null = null;
    if (form.provider === "native") {
      try {
        config = configText ? JSON.parse(configText) : null;
      } catch {
        toast.error("Config is not valid JSON");
        return;
      }
    }
    const entry: LabCatalogEntryIn = {
      ...form,
      embed_url: form.provider === "native" ? null : form.embed_url || null,
      native_template:
        form.provider === "native"
          ? form.native_template || "reaction_lab"
          : null,
      config,
      description: form.description || null,
      attribution: form.attribution || null,
    };
    setSaving(true);
    try {
      if (editingId) await contentLibraryAdmin.updateLab(editingId, entry);
      else await contentLibraryAdmin.createLab(entry);
      toast.success(editingId ? "Lab updated" : "Lab added to the catalog");
      resetForm();
      load();
    } catch (err) {
      toast.error(errorDetail(err, "Could not save the lab"));
    } finally {
      setSaving(false);
    }
  };

  const togglePublish = async (r: AdminLabRow) => {
    try {
      await contentLibraryAdmin.updateLab(r.catalog_id, {
        slug: r.slug,
        title: r.title,
        subject: r.subject,
        description: r.description || null,
        provider: r.provider,
        embed_url: r.embed_url || null,
        native_template: r.native_template || null,
        config: r.config || null,
        attribution: r.attribution || null,
        thumbnail_url: r.thumbnail_url || null,
        is_published: !r.is_published,
      });
      load();
    } catch (err) {
      toast.error(errorDetail(err, "Could not update the lab"));
    }
  };

  const remove = async (r: AdminLabRow) => {
    if (!(await confirmDialog(`Delete "${r.title}" from the catalog?`))) return;
    try {
      await contentLibraryAdmin.deleteLab(r.catalog_id);
      toast.success("Deleted");
      load();
    } catch (err) {
      toast.error(errorDetail(err, "Could not delete the lab"));
    }
  };

  const importPack = async () => {
    let parsed: any;
    try {
      parsed = JSON.parse(packText);
    } catch {
      toast.error("Pack is not valid JSON");
      return;
    }
    const labs = Array.isArray(parsed) ? parsed : parsed?.labs;
    if (!Array.isArray(labs) || labs.length === 0) {
      toast.error('Pack must be {"labs": [...]}');
      return;
    }
    try {
      const res = await contentLibraryAdmin.importLabs(labs);
      toast.success(`Imported: ${res.created} created, ${res.updated} updated`);
      setPackText("");
      load();
    } catch (err) {
      toast.error(errorDetail(err, "Import failed"));
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center gap-2">
        <button
          type="button"
          onClick={() => {
            resetForm();
            setShowForm(true);
          }}
          className="inline-flex items-center gap-1 px-3 py-2 text-sm font-medium rounded-lg bg-orange-500 text-white hover:bg-orange-600"
        >
          <Plus className="w-4 h-4" /> Add lab
        </button>
        <button
          type="button"
          onClick={load}
          className="inline-flex items-center gap-1 px-3 py-2 text-sm rounded-lg border border-gray-300 text-gray-700 hover:bg-gray-50"
        >
          <RefreshCw className="w-4 h-4" /> Refresh
        </button>
        <span className="text-xs text-gray-500 ml-auto">
          {builtin.length} built-in · {rows.length} admin-added
        </span>
      </div>

      {showForm && (
        <div
          className="rounded-xl border border-gray-200 bg-white p-4 grid gap-3 sm:grid-cols-2"
          data-glass="work"
        >
          <label className="text-sm">
            <span className="block text-gray-600 mb-1">
              Slug (lowercase, dashes)
            </span>
            <input
              value={form.slug}
              onChange={(e) => setForm({ ...form, slug: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg"
              placeholder="acid-base-titration"
            />
          </label>
          <label className="text-sm">
            <span className="block text-gray-600 mb-1">Title</span>
            <input
              value={form.title}
              onChange={(e) => setForm({ ...form, title: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg"
            />
          </label>
          <label className="text-sm">
            <span className="block text-gray-600 mb-1">Subject</span>
            <input
              value={form.subject}
              onChange={(e) => setForm({ ...form, subject: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg"
              placeholder="chemistry"
            />
          </label>
          <label className="text-sm">
            <span className="block text-gray-600 mb-1">Provider</span>
            <select
              value={form.provider}
              onChange={(e) =>
                setForm({
                  ...form,
                  provider: e.target.value as LabCatalogEntryIn["provider"],
                })
              }
              className="w-full px-3 py-2 border border-gray-300 rounded-lg"
            >
              <option value="embed">Embed (any https lab URL)</option>
              <option value="native">Native gradeable lab (JSON config)</option>
            </select>
          </label>
          {form.provider !== "native" ? (
            <label className="text-sm sm:col-span-2">
              <span className="block text-gray-600 mb-1">
                Embed URL (https)
                {form.provider === "phet"
                  ? " — optional, derived from the slug"
                  : ""}
              </span>
              <input
                value={form.embed_url || ""}
                onChange={(e) =>
                  setForm({ ...form, embed_url: e.target.value })
                }
                className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                placeholder="https://…"
              />
            </label>
          ) : (
            <>
              <label className="text-sm">
                <span className="block text-gray-600 mb-1">Template</span>
                <select
                  value={form.native_template || "reaction_lab"}
                  onChange={(e) =>
                    setForm({
                      ...form,
                      native_template: e.target
                        .value as LabCatalogEntryIn["native_template"],
                    })
                  }
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                >
                  <option value="reaction_lab">
                    Reaction Lab (balance equations)
                  </option>
                  <option value="identify_lab">
                    Identify Lab (diagram hotspots)
                  </option>
                </select>
              </label>
              <label className="text-sm sm:col-span-2">
                <span className="block text-gray-600 mb-1">
                  Config JSON — validated on save (answer keys are checked:
                  unbalanced reactions are refused)
                </span>
                <textarea
                  value={configText}
                  onChange={(e) => setConfigText(e.target.value)}
                  rows={8}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg font-mono text-xs"
                  placeholder='{"reactions": [{"reactants": [...], "products": [...], "coefficients": [2,1,2]}]}'
                />
              </label>
            </>
          )}
          <label className="text-sm sm:col-span-2">
            <span className="block text-gray-600 mb-1">Description</span>
            <input
              value={form.description || ""}
              onChange={(e) =>
                setForm({ ...form, description: e.target.value })
              }
              className="w-full px-3 py-2 border border-gray-300 rounded-lg"
            />
          </label>
          <label className="text-sm">
            <span className="block text-gray-600 mb-1">Attribution</span>
            <input
              value={form.attribution || ""}
              onChange={(e) =>
                setForm({ ...form, attribution: e.target.value })
              }
              className="w-full px-3 py-2 border border-gray-300 rounded-lg"
            />
          </label>
          <label className="text-sm inline-flex items-center gap-2 self-end">
            <input
              type="checkbox"
              checked={form.is_published}
              onChange={(e) =>
                setForm({ ...form, is_published: e.target.checked })
              }
            />{" "}
            Published (visible to instructors)
          </label>
          <div className="sm:col-span-2 flex gap-2">
            <button
              type="button"
              disabled={saving}
              onClick={save}
              className="px-4 py-2 text-sm font-medium rounded-lg bg-gray-900 text-white hover:bg-black disabled:opacity-50"
            >
              {saving
                ? "Saving…"
                : editingId
                  ? "Save changes"
                  : "Add to catalog"}
            </button>
            <button
              type="button"
              onClick={resetForm}
              className="px-4 py-2 text-sm rounded-lg border border-gray-300"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      <div
        className="rounded-xl border border-gray-200 bg-white overflow-hidden"
        data-glass="work"
      >
        <div className="px-4 py-3 border-b border-gray-100 flex items-center justify-between">
          <h2 className="font-semibold text-gray-900">Admin-added labs</h2>
        </div>
        {loading ? (
          <p className="p-4 text-sm text-gray-500">Loading…</p>
        ) : rows.length === 0 ? (
          <p className="p-4 text-sm text-gray-500">
            No admin-added labs yet. Built-in labs are always available to
            instructors.
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 text-left text-xs text-gray-500">
                <tr>
                  <th className="px-4 py-2">Title</th>
                  <th className="px-4 py-2">Slug</th>
                  <th className="px-4 py-2">Subject</th>
                  <th className="px-4 py-2">Provider</th>
                  <th className="px-4 py-2">Status</th>
                  <th className="px-4 py-2 text-right">Actions</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((r) => (
                  <tr key={r.catalog_id} className="border-t border-gray-100">
                    <td className="px-4 py-2 font-medium text-gray-900">
                      {r.title}
                    </td>
                    <td className="px-4 py-2 font-mono text-xs text-gray-600">
                      {r.slug}
                    </td>
                    <td className="px-4 py-2 capitalize">{r.subject}</td>
                    <td className="px-4 py-2 capitalize">
                      {r.provider}
                      {r.native_template
                        ? ` · ${r.native_template.replace("_", " ")}`
                        : ""}
                    </td>
                    <td className="px-4 py-2">
                      {r.is_published ? (
                        <span className="text-emerald-700">Published</span>
                      ) : (
                        <span className="text-gray-400">Hidden</span>
                      )}
                    </td>
                    <td className="px-4 py-2 text-right whitespace-nowrap">
                      <button
                        type="button"
                        title="Preview"
                        onClick={() => setPreviewSlug(r.slug)}
                        className="p-1.5 text-gray-500 hover:text-gray-900"
                      >
                        <Eye className="w-4 h-4" />
                      </button>
                      <button
                        type="button"
                        title={r.is_published ? "Unpublish" : "Publish"}
                        onClick={() => togglePublish(r)}
                        className="p-1.5 text-gray-500 hover:text-gray-900"
                      >
                        {r.is_published ? (
                          <EyeOff className="w-4 h-4" />
                        ) : (
                          <Eye className="w-4 h-4" />
                        )}
                      </button>
                      <button
                        type="button"
                        onClick={() => startEdit(r)}
                        className="px-2 py-1 text-xs text-blue-600 hover:underline"
                      >
                        Edit
                      </button>
                      <button
                        type="button"
                        title="Delete"
                        onClick={() => remove(r)}
                        className="p-1.5 text-red-500 hover:text-red-700"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <div
        className="rounded-xl border border-gray-200 bg-white p-4"
        data-glass="content"
      >
        <h2 className="font-semibold text-gray-900 mb-1">
          Built-in labs ({builtin.length})
        </h2>
        <p className="text-xs text-gray-500 mb-3">
          Shipped with the platform. Add an entry with the same slug to retitle
          or hide one.
        </p>
        <div className="flex flex-wrap gap-1.5">
          {builtin.map((b) => (
            <button
              key={b.slug}
              type="button"
              onClick={() => setPreviewSlug(b.slug)}
              className={`text-xs px-2 py-1 rounded-full border ${b.provider === "native" ? "border-emerald-300 bg-emerald-50 text-emerald-800" : "border-gray-200 bg-gray-50 text-gray-700"} ${b.overridden ? "line-through" : ""}`}
              title={`${b.subject} · ${b.provider}`}
            >
              {b.title}
            </button>
          ))}
        </div>
      </div>

      <div
        className="rounded-xl border border-gray-200 bg-white p-4"
        data-glass="work"
      >
        <h2 className="font-semibold text-gray-900 mb-1">
          Import a lab pack (JSON)
        </h2>
        <p className="text-xs text-gray-500 mb-2">
          {
            '{"labs": [{"slug": "...", "title": "...", "subject": "...", "provider": "embed|native", ...}]}'
          }{" "}
          — upserts by slug; the whole pack is validated first.
        </p>
        <textarea
          value={packText}
          onChange={(e) => setPackText(e.target.value)}
          rows={5}
          className="w-full px-3 py-2 border border-gray-300 rounded-lg font-mono text-xs"
        />
        <button
          type="button"
          onClick={importPack}
          disabled={!packText.trim()}
          className="mt-2 inline-flex items-center gap-1 px-3 py-2 text-sm font-medium rounded-lg bg-gray-900 text-white hover:bg-black disabled:opacity-40"
        >
          <Upload className="w-4 h-4" /> Import pack
        </button>
      </div>

      {previewSlug && (
        <div
          className="fixed inset-0 z-[100] bg-black/70 flex items-center justify-center p-4"
          onClick={() => setPreviewSlug(null)}
        >
          <div
            className="bg-white rounded-2xl max-w-3xl w-full max-h-[90vh] overflow-y-auto p-4"
            onClick={(e) => e.stopPropagation()}
            data-glass="content"
          >
            <div className="flex items-center justify-between mb-2">
              <p className="text-xs text-gray-500 font-mono">{previewSlug}</p>
              <button
                type="button"
                onClick={() => setPreviewSlug(null)}
                className="text-sm text-gray-500 hover:text-gray-900"
              >
                Close
              </button>
            </div>
            <VirtualLabPlayer slug={previewSlug} previewOnly height={420} />
          </div>
        </div>
      )}
    </div>
  );
}

// ============================================================ 3D assets

function ThreeDTab() {
  const [models, setModels] = useState<LibraryModel[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setModels((await contentLibraryAdmin.listLibraryModels()).models);
    } catch (err) {
      toast.error(errorDetail(err, "Failed to load the 3D library"));
    } finally {
      setLoading(false);
    }
  }, []);
  useEffect(() => {
    load();
  }, [load]);

  const upload = async (files: FileList | null) => {
    if (!files || files.length === 0) return;
    setUploading(true);
    try {
      const res = await contentLibraryAdmin.importModels(Array.from(files));
      toast.success(
        `${res.models.length} model(s) added to the shared library`,
      );
      load();
    } catch (err) {
      toast.error(errorDetail(err, "Import failed"));
    } finally {
      setUploading(false);
    }
  };

  const toggle = async (m: LibraryModel) => {
    try {
      await contentLibraryAdmin.patchModel(m.id, { is_library: !m.is_library });
      load();
    } catch (err) {
      toast.error(errorDetail(err, "Could not update the model"));
    }
  };
  const remove = async (m: LibraryModel) => {
    if (!(await confirmDialog(`Delete "${m.title}"?`))) return;
    try {
      await contentLibraryAdmin.deleteModel(m.id);
      toast.success("Deleted");
      load();
    } catch (err) {
      toast.error(errorDetail(err, "Could not delete the model"));
    }
  };

  return (
    <div className="space-y-4">
      <div className="rounded-xl border border-dashed border-cyan-300 bg-cyan-50 p-6 text-center">
        <input
          ref={fileRef}
          type="file"
          accept=".glb"
          multiple
          className="hidden"
          onChange={(e) => {
            void upload(e.target.files);
            e.target.value = "";
          }}
        />
        <p className="text-sm text-gray-700 mb-2">
          Import .glb models into the shared library (max 50MB each, up to 50
          per batch). Every instructor can attach them to MP/UP course lessons.
        </p>
        <button
          type="button"
          disabled={uploading}
          onClick={() => fileRef.current?.click()}
          className="inline-flex items-center gap-1 px-4 py-2 text-sm font-medium rounded-lg bg-cyan-600 text-white hover:bg-cyan-700 disabled:opacity-50"
        >
          <Upload className="w-4 h-4" />{" "}
          {uploading ? "Importing…" : "Import GLB files"}
        </button>
      </div>
      <div
        className="rounded-xl border border-gray-200 bg-white overflow-hidden"
        data-glass="work"
      >
        {loading ? (
          <p className="p-4 text-sm text-gray-500">Loading…</p>
        ) : models.length === 0 ? (
          <p className="p-4 text-sm text-gray-500">
            The shared library is empty.
          </p>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-left text-xs text-gray-500">
              <tr>
                <th className="px-4 py-2">Title</th>
                <th className="px-4 py-2">Size</th>
                <th className="px-4 py-2">Shared</th>
                <th className="px-4 py-2 text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {models.map((m) => (
                <tr key={m.id} className="border-t border-gray-100">
                  <td className="px-4 py-2 font-medium text-gray-900">
                    <AstraSymbol value="🧊" /> {m.title}{" "}
                    <span className="text-xs text-gray-400">#{m.id}</span>
                  </td>
                  <td className="px-4 py-2">
                    {(m.file_size_bytes / 1048576).toFixed(1)} MB
                  </td>
                  <td className="px-4 py-2">
                    {m.is_library ? (
                      <span className="text-emerald-700">Yes</span>
                    ) : (
                      <span className="text-gray-400">No</span>
                    )}
                  </td>
                  <td className="px-4 py-2 text-right whitespace-nowrap">
                    <button
                      type="button"
                      onClick={() => toggle(m)}
                      className="px-2 py-1 text-xs text-blue-600 hover:underline"
                    >
                      {m.is_library ? "Unshare" : "Share"}
                    </button>
                    <button
                      type="button"
                      title="Delete"
                      onClick={() => remove(m)}
                      className="p-1.5 text-red-500 hover:text-red-700"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

// ============================================================ Games

function GamesTab() {
  const [games, setGames] = useState<
    {
      id: number;
      title: string;
      template: string;
      status: string;
      item_count: number;
      max_score: number;
      is_listed: boolean;
    }[]
  >([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [packText, setPackText] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setGames((await contentLibraryAdmin.listPrebuiltGames()).games);
    } catch (err) {
      toast.error(errorDetail(err, "Failed to load prebuilt games"));
    } finally {
      setLoading(false);
    }
  }, []);
  useEffect(() => {
    load();
  }, [load]);

  const importDefaults = async () => {
    setBusy(true);
    try {
      const res = await contentLibraryAdmin.importDefaultGames();
      toast.success(
        `Shipped pack: ${res.created.length} added, ${res.skipped.length} already present`,
      );
      load();
    } catch (err) {
      toast.error(errorDetail(err, "Import failed"));
    } finally {
      setBusy(false);
    }
  };

  const importPack = async () => {
    let parsed: any;
    try {
      parsed = JSON.parse(packText);
    } catch {
      toast.error("Pack is not valid JSON");
      return;
    }
    const list = Array.isArray(parsed) ? parsed : parsed?.games;
    if (!Array.isArray(list) || list.length === 0) {
      toast.error('Pack must be {"games": [...]}');
      return;
    }
    setBusy(true);
    try {
      const res = await contentLibraryAdmin.importGames(list);
      toast.success(
        `${res.created.length} game(s) added, ${res.skipped.length} skipped`,
      );
      setPackText("");
      load();
    } catch (err) {
      toast.error(errorDetail(err, "Import failed"));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-4">
      <div className="rounded-xl border border-violet-200 bg-violet-50 p-4 flex flex-wrap items-center gap-3">
        <div className="flex-1 min-w-[16rem]">
          <p className="font-medium text-gray-900">Shipped science pack</p>
          <p className="text-xs text-gray-600">
            7 games — chemical reactions, organelles, skeleton sorting, mitosis
            order, chemistry vocabulary, forces, periodic symbols. Published and
            listed for every instructor.
          </p>
        </div>
        <button
          type="button"
          disabled={busy}
          onClick={importDefaults}
          className="inline-flex items-center gap-1 px-4 py-2 text-sm font-medium rounded-lg bg-violet-600 text-white hover:bg-violet-700 disabled:opacity-50"
        >
          <Gamepad2 className="w-4 h-4" />{" "}
          {busy ? "Working…" : "Load shipped pack"}
        </button>
      </div>
      <div
        className="rounded-xl border border-gray-200 bg-white overflow-hidden"
        data-glass="work"
      >
        {loading ? (
          <p className="p-4 text-sm text-gray-500">Loading…</p>
        ) : games.length === 0 ? (
          <p className="p-4 text-sm text-gray-500">
            No prebuilt games yet — load the shipped pack or import your own.
          </p>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-left text-xs text-gray-500">
              <tr>
                <th className="px-4 py-2">Title</th>
                <th className="px-4 py-2">Template</th>
                <th className="px-4 py-2">Items</th>
                <th className="px-4 py-2">Max score</th>
                <th className="px-4 py-2">Marketplace</th>
              </tr>
            </thead>
            <tbody>
              {games.map((g) => (
                <tr key={g.id} className="border-t border-gray-100">
                  <td className="px-4 py-2 font-medium text-gray-900">
                    <AstraSymbol value="🎮" /> {g.title}
                  </td>
                  <td className="px-4 py-2 capitalize">
                    {g.template.replace("_", " ")}
                  </td>
                  <td className="px-4 py-2">{g.item_count}</td>
                  <td className="px-4 py-2">{g.max_score}</td>
                  <td className="px-4 py-2">
                    {g.is_listed && g.status === "published" ? (
                      <span className="text-emerald-700">Listed</span>
                    ) : (
                      <span className="text-gray-400">Not listed</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
      <div
        className="rounded-xl border border-gray-200 bg-white p-4"
        data-glass="work"
      >
        <h2 className="font-semibold text-gray-900 mb-1">
          Import a game pack (JSON)
        </h2>
        <p className="text-xs text-gray-500 mb-2">
          {
            '{"games": [{"title": "...", "template": "quiz_rush|match_pairs|drag_sort|word_builder|sequence", "config": {...}}]}'
          }{" "}
          — same validation as the game builder; duplicates by title are
          skipped.
        </p>
        <textarea
          value={packText}
          onChange={(e) => setPackText(e.target.value)}
          rows={5}
          className="w-full px-3 py-2 border border-gray-300 rounded-lg font-mono text-xs"
        />
        <button
          type="button"
          onClick={importPack}
          disabled={busy || !packText.trim()}
          className="mt-2 inline-flex items-center gap-1 px-3 py-2 text-sm font-medium rounded-lg bg-gray-900 text-white hover:bg-black disabled:opacity-40"
        >
          <Upload className="w-4 h-4" /> Import pack
        </button>
      </div>
    </div>
  );
}

export default AdminContentLibrariesPage;
