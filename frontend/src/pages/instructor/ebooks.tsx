import { Link } from "react-router-dom";
import {
  PageLayout,
  PageHeading,
  MetricStrip,
  WorkPanel,
} from "@/components/design-system/PageLayout";
/**
 * Instructor Ebooks manager — full lifecycle over GET/POST/PUT /library:
 * create draft, edit metadata, upload the sellable file + free sample,
 * publish/unpublish, delete. Backend enforces the real rules (PDF/EPUB
 * only, size caps, discount < price); this UI surfaces those errors via
 * toasts and never pre-validates differently than the server.
 */
import { useEffect, useRef, useState } from "react";
import { confirmDialog } from "@/components/ui/confirm";
import {
  BookOpen,
  Plus,
  Trash2,
  Upload,
  Search,
  FileText,
  CheckCircle2,
  ArrowUpRight,
} from "lucide-react";
import toast from "react-hot-toast";
import { Button } from "@/components/ui/button";
import { EBOOK_CATEGORY_LABELS, libraryAPI, type Ebook } from "@/api/library";

interface DraftForm {
  title: string;
  description: string;
  category: Ebook["category"];
  price_inr: number;
  discount_price_inr: number | null;
  page_count: number | null;
  cover_image: string;
  concept_tags: string;
}

const emptyForm: DraftForm = {
  title: "",
  description: "",
  category: "book",
  price_inr: 0,
  discount_price_inr: null,
  page_count: null,
  cover_image: "",
  concept_tags: "",
};

export default function InstructorEbooksPage() {
  const [ebooks, setEbooks] = useState<Ebook[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState<DraftForm>(emptyForm);
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("all");
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [loadError, setLoadError] = useState("");
  const [saving, setSaving] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const fileRefs = useRef<Record<string, HTMLInputElement | null>>({});

  const reload = () => {
    setLoadError("");
    setLoading(true);
    libraryAPI
      .mine()
      .then((d) => setEbooks(d.ebooks))
      .catch(() =>
        setLoadError("Your ebooks could not be loaded. Please try again."),
      )
      .finally(() => setLoading(false));
  };
  useEffect(reload, []);

  function startEdit(e: Ebook) {
    setEditingId(e.id);
    setForm({
      title: e.title,
      description: e.description,
      category: e.category,
      price_inr: e.price_inr,
      discount_price_inr: e.discount_price_inr,
      page_count: e.page_count,
      cover_image: e.cover_image,
      concept_tags: e.concept_tags.join(", "),
    });
    setShowForm(true);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  async function save() {
    setSaving(true);
    const payload = {
      title: form.title,
      description: form.description,
      category: form.category,
      price_inr: Number(form.price_inr) || 0,
      discount_price_inr:
        form.discount_price_inr === null ||
        (form.discount_price_inr as number) < 0
          ? null
          : Number(form.discount_price_inr),
      page_count:
        form.page_count === null || form.page_count === ("" as unknown)
          ? null
          : Number(form.page_count),
      cover_image: form.cover_image,
      concept_tags: form.concept_tags
        .split(",")
        .map((t) => t.trim())
        .filter(Boolean),
    };
    try {
      if (editingId) {
        await libraryAPI.update(editingId, payload);
        toast.success("Ebook updated");
      } else {
        await libraryAPI.create(payload);
        toast.success("Draft created — now upload the PDF");
      }
      setShowForm(false);
      setEditingId(null);
      setForm(emptyForm);
      reload();
    } catch (e: unknown) {
      const detail = (e as { response?: { data?: { detail?: string } } })
        ?.response?.data?.detail;
      toast.error(typeof detail === "string" ? detail : "Save failed");
    } finally {
      setSaving(false);
    }
  }

  async function upload(
    kind: "file" | "sample",
    id: number,
    f: File | undefined,
  ) {
    if (!f) return;
    const t = toast.loading(`Uploading ${kind}…`);
    try {
      await (kind === "file"
        ? libraryAPI.uploadFile(id, f)
        : libraryAPI.uploadSample(id, f));
      toast.success(`${kind === "file" ? "Ebook file" : "Sample"} uploaded`, {
        id: t,
      });
      reload();
    } catch (e: unknown) {
      const detail = (e as { response?: { data?: { detail?: string } } })
        ?.response?.data?.detail;
      toast.error(typeof detail === "string" ? detail : "Upload failed", {
        id: t,
      });
    }
  }

  async function togglePublish(e: Ebook) {
    try {
      if (e.status === "published") {
        await libraryAPI.unpublish(e.id);
        toast.success("Unpublished (buyers keep their downloads)");
      } else {
        await libraryAPI.publish(e.id);
        toast.success("Published to the store 🎉");
      }
      reload();
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })
        ?.response?.data?.detail;
      toast.error(typeof detail === "string" ? detail : "Action failed");
    }
  }

  async function remove(e: Ebook) {
    if (!(await confirmDialog(`Delete "${e.title}"? This cannot be undone.`)))
      return;
    try {
      await libraryAPI.remove(e.id);
      toast.success("Deleted");
      reload();
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })
        ?.response?.data?.detail;
      toast.error(
        typeof detail === "string"
          ? detail
          : "Delete failed (sold ebooks are protected)",
      );
    }
  }

  const visible = ebooks.filter(
    (e) =>
      (status === "all" || e.status === status) &&
      [e.title, e.description, ...e.concept_tags]
        .join(" ")
        .toLowerCase()
        .includes(query.toLowerCase()),
  );
  const selected = visible.find((e) => e.id === selectedId) || visible[0];
  const newDraft = () => {
    setEditingId(null);
    setForm(emptyForm);
    setShowForm(true);
  };

  return (
    <div className="rd-ebooks">
      <PageHeading
        eyebrow="Content Studio"
        title="Your publishing desk"
        description="Turn your knowledge into books, notes and learning resources."
        actions={
          <>
            <Link to="/library" className="rd-text-link">
              View library <ArrowUpRight size={15} />
            </Link>
            <Button onClick={newDraft}>
              <Plus size={16} /> New Ebook
            </Button>
          </>
        }
      />
      <MetricStrip
        items={[
          {
            label: "All resources",
            value: loading ? "—" : ebooks.length,
            note: "Books, notes and guides",
          },
          {
            label: "Published",
            value: loading
              ? "—"
              : ebooks.filter((e) => e.status === "published").length,
            note: "Available in the library",
          },
          {
            label: "Drafts",
            value: loading
              ? "—"
              : ebooks.filter((e) => e.status !== "published").length,
            note: "Your work in progress",
          },
          {
            label: "Files to upload",
            value: loading ? "—" : ebooks.filter((e) => !e.has_file).length,
            note: "Add a PDF or EPUB",
          },
        ]}
      />
      {showForm && (
        <div className="rd-panel rd-ebook-editor space-y-4">
          <h2 className="font-semibold text-gray-900">
            {editingId ? `Edit ebook #${editingId}` : "Create draft"}
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <label className="text-sm font-medium text-gray-700 md:col-span-2">
              Title *
              <input
                value={form.title}
                onChange={(e) => setForm({ ...form, title: e.target.value })}
                className="mt-1 w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
                placeholder="e.g., Class 10 Physics — Complete Notes"
              />
            </label>
            <label className="text-sm font-medium text-gray-700 md:col-span-2">
              Description
              <textarea
                value={form.description}
                onChange={(e) =>
                  setForm({ ...form, description: e.target.value })
                }
                rows={3}
                className="mt-1 w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
                placeholder="What's inside? Who is it for?"
              />
            </label>
            <label className="text-sm font-medium text-gray-700">
              Category
              <select
                value={form.category}
                onChange={(e) =>
                  setForm({
                    ...form,
                    category: e.target.value as Ebook["category"],
                  })
                }
                className="mt-1 w-full px-3 py-2 border border-gray-300 rounded-lg text-sm bg-white"
              >
                {Object.entries(EBOOK_CATEGORY_LABELS).map(([v, l]) => (
                  <option key={v} value={v}>
                    {l}
                  </option>
                ))}
              </select>
            </label>
            <label className="text-sm font-medium text-gray-700">
              Pages
              <input
                type="number"
                min="0"
                value={form.page_count ?? ""}
                onChange={(e) =>
                  setForm({
                    ...form,
                    page_count:
                      e.target.value === "" ? null : Number(e.target.value),
                  })
                }
                className="mt-1 w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
              />
            </label>
            <label className="text-sm font-medium text-gray-700">
              Price (₹, 0 = free)
              <input
                type="number"
                min="0"
                step="1"
                value={form.price_inr}
                onChange={(e) =>
                  setForm({ ...form, price_inr: Number(e.target.value) })
                }
                className="mt-1 w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
              />
            </label>
            <label className="text-sm font-medium text-gray-700">
              Discount price (₹, optional)
              <input
                type="number"
                min="0"
                step="1"
                value={form.discount_price_inr ?? ""}
                onChange={(e) =>
                  setForm({
                    ...form,
                    discount_price_inr:
                      e.target.value === "" ? null : Number(e.target.value),
                  })
                }
                className="mt-1 w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
                placeholder="must be less than price"
              />
            </label>
            <label className="text-sm font-medium text-gray-700">
              Cover image URL
              <input
                value={form.cover_image}
                onChange={(e) =>
                  setForm({ ...form, cover_image: e.target.value })
                }
                className="mt-1 w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
                placeholder="https://… (optional)"
              />
            </label>
            <label className="text-sm font-medium text-gray-700">
              Concept tags (comma-separated)
              <input
                value={form.concept_tags}
                onChange={(e) =>
                  setForm({ ...form, concept_tags: e.target.value })
                }
                className="mt-1 w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
                placeholder="kinematics, thermodynamics"
              />
            </label>
          </div>
          <div className="flex gap-3">
            <Button onClick={save} disabled={saving || !form.title.trim()}>
              {saving ? "Saving…" : editingId ? "Save changes" : "Create draft"}
            </Button>
            <Button
              variant="outline"
              onClick={() => {
                setShowForm(false);
                setEditingId(null);
              }}
            >
              Cancel
            </Button>
          </div>
        </div>
      )}

      <PageLayout
        className="rd-ebook-layout"
        toolbar={
          <>
            <div
              className="rd-filter-tabs"
              role="group"
              aria-label="Publication status"
            >
              {["all", "published", "draft"].map((value) => (
                <button
                  key={value}
                  aria-pressed={status === value}
                  onClick={() => setStatus(value)}
                >
                  {value === "all"
                    ? "All resources"
                    : value === "draft"
                      ? "Drafts"
                      : "Published"}
                </button>
              ))}
            </div>
            <label className="rd-search">
              <Search size={16} />
              <input
                aria-label="Search your ebooks"
                placeholder="Search title or concept..."
                value={query}
                onChange={(e) => setQuery(e.target.value)}
              />
            </label>
          </>
        }
        aside={
          <>
            <WorkPanel
              title={selected ? "Resource details" : "Publishing checklist"}
            >
              {selected ? (
                <>
                  <div className="rd-book-cover">
                    {selected.cover_image ? (
                      <img src={selected.cover_image} alt="" />
                    ) : (
                      <BookOpen size={42} />
                    )}
                    <span>{EBOOK_CATEGORY_LABELS[selected.category]}</span>
                  </div>
                  <h3>{selected.title}</h3>
                  <p className="rd-description">
                    {selected.description ||
                      "Add a description to help learners discover this resource."}
                  </p>
                  <dl className="rd-detail-list">
                    <div>
                      <dt>Price</dt>
                      <dd>
                        {selected.effective_price_inr
                          ? "₹" + selected.effective_price_inr
                          : "Free"}
                      </dd>
                    </div>
                    <div>
                      <dt>Pages</dt>
                      <dd>{selected.page_count || "Not set"}</dd>
                    </div>
                    <div>
                      <dt>Status</dt>
                      <dd>{selected.status}</dd>
                    </div>
                  </dl>
                  <ul className="rd-checklist">
                    <li data-ready={selected.has_file}>
                      <CheckCircle2 size={16} />
                      {selected.has_file
                        ? "Main file uploaded"
                        : "Upload the main PDF or EPUB"}
                    </li>
                    <li data-ready={selected.has_sample}>
                      <FileText size={16} />
                      {selected.has_sample
                        ? "Free sample available"
                        : "Add a free sample (optional)"}
                    </li>
                  </ul>
                  <div className="rd-resource-actions">
                    <Button
                      variant="outline"
                      onClick={() => startEdit(selected)}
                    >
                      Edit details
                    </Button>
                    <Button
                      disabled={
                        !selected.has_file && selected.status !== "published"
                      }
                      onClick={() => togglePublish(selected)}
                    >
                      {selected.status === "published"
                        ? "Unpublish"
                        : "Publish"}
                    </Button>
                  </div>
                  <div className="rd-resource-actions">
                    <input
                      ref={(el) => {
                        fileRefs.current["selected-file"] = el;
                      }}
                      type="file"
                      accept=".pdf,.epub"
                      hidden
                      onChange={(e) => {
                        void upload("file", selected.id, e.target.files?.[0]);
                        e.target.value = "";
                      }}
                    />
                    <Button
                      variant="outline"
                      onClick={() => fileRefs.current["selected-file"]?.click()}
                    >
                      <Upload size={14} /> Upload file
                    </Button>
                    <input
                      ref={(el) => {
                        fileRefs.current["selected-sample"] = el;
                      }}
                      type="file"
                      accept=".pdf"
                      hidden
                      onChange={(e) => {
                        void upload("sample", selected.id, e.target.files?.[0]);
                        e.target.value = "";
                      }}
                    />
                    <Button
                      variant="outline"
                      onClick={() =>
                        fileRefs.current["selected-sample"]?.click()
                      }
                    >
                      Upload sample
                    </Button>
                  </div>
                  <button
                    className="rd-delete-link"
                    onClick={() => remove(selected)}
                  >
                    <Trash2 size={14} /> Delete resource
                  </button>
                </>
              ) : (
                <ol className="rd-publishing-steps">
                  <li>
                    <span>01</span>
                    <div>
                      <strong>Create a draft</strong>
                      <p>Add a title, description and concept tags.</p>
                    </div>
                  </li>
                  <li>
                    <span>02</span>
                    <div>
                      <strong>Upload your resource</strong>
                      <p>Attach the PDF or EPUB and an optional sample.</p>
                    </div>
                  </li>
                  <li>
                    <span>03</span>
                    <div>
                      <strong>Review and publish</strong>
                      <p>Set the price, check your details, then publish.</p>
                    </div>
                  </li>
                </ol>
              )}
            </WorkPanel>
          </>
        }
      >
        <WorkPanel
          title="Resource library"
          description={
            loading
              ? "Loading your resources..."
              : visible.length + " resources in this view"
          }
        >
          {loadError ? (
            <div role="alert" className="rd-empty">
              <p>{loadError}</p>
              <Button variant="outline" onClick={reload}>
                Try again
              </Button>
            </div>
          ) : loading ? (
            <div role="status" className="rd-empty">
              Loading ebooks...
            </div>
          ) : !visible.length ? (
            <div className="rd-empty">
              <BookOpen size={36} />
              <h3>
                {ebooks.length
                  ? "No matching resources"
                  : "Your next chapter starts here"}
              </h3>
              <p>
                {ebooks.length
                  ? "Try a different search or publication status."
                  : "Create your first ebook, add a file, and share it with your learners."}
              </p>
              {!ebooks.length && (
                <Button onClick={newDraft}>Create your first draft</Button>
              )}
            </div>
          ) : (
            <div className="rd-resource-table">
              <table>
                <thead>
                  <tr>
                    <th>Resource</th>
                    <th>Status</th>
                    <th>Price</th>
                  </tr>
                </thead>
                <tbody>
                  {visible.map((e) => (
                    <tr key={e.id} data-selected={selected?.id === e.id}>
                      <td>
                        <button
                          className="rd-resource-select"
                          onClick={() => {
                            setSelectedId(e.id);
                            setShowForm(false);
                          }}
                          aria-pressed={selected?.id === e.id}
                        >
                          <span className="rd-resource-icon">
                            <BookOpen size={21} />
                          </span>
                          <span>
                            <strong>{e.title}</strong>
                            <small>
                              {EBOOK_CATEGORY_LABELS[e.category]} ·{" "}
                              {e.has_file ? "File ready" : "File needed"}
                            </small>
                          </span>
                        </button>
                      </td>
                      <td>
                        <span className="rd-status" data-status={e.status}>
                          {e.status}
                        </span>
                      </td>
                      <td>
                        {e.effective_price_inr
                          ? "₹" + e.effective_price_inr
                          : "Free"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </WorkPanel>
      </PageLayout>
    </div>
  );
}
