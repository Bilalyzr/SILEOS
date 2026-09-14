import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { campusApi, type ImportResult, type Branding } from "@/api/campus";
import type { InstitutionOverview } from "@/api/institutions";
import { useAuthStore } from "@/store/auth";
import { Button } from "@/components/ui/button";
import { GlassDialog } from "@/components/ui/dialog";
import { BrandBanner } from "@/components/design-system/BrandBanner";
import { apiError } from "./InstitutionDialog";
import toast from "react-hot-toast";

export function BulkInvites({
  id,
  saved,
}: {
  id: number;
  saved: () => Promise<unknown>;
}) {
  const [open, setOpen] = useState(false);
  const [csv, setCsv] = useState("");
  const [result, setResult] = useState<ImportResult>();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function run(commit: boolean) {
    setBusy(true);
    setError("");
    try {
      const r = await campusApi.importPeople(id, csv, commit);
      setResult(r);
      if (commit) {
        toast.success(`${r.created} invitations created`);
        await saved();
      }
    } catch (e) {
      setError(apiError(e));
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <Button variant="outline" onClick={() => setOpen(true)}>
        Import people from CSV
      </Button>
      <GlassDialog
        open={open}
        onOpenChange={setOpen}
        title="Bring your campus together"
        size="lg"
      >
        <p className="brand-share-note">
          Upload up to 500 rows using email,role,department. Review first, then
          create account-inbox invitations. Students accept with their own
          verified accounts. Existing members and pending invitations are
          skipped.
        </p>
        <label className="brand-share-upload">
          CSV file
          <input
            type="file"
            accept=".csv,text/csv"
            onChange={async (e) => {
              const file = e.target.files?.[0];
              if (!file) return;
              if (file.size > 100_000) {
                setError("Use a CSV file under 100 KB.");
                return;
              }
              setCsv(await file.text());
              setResult(undefined);
            }}
          />
        </label>
        <label className="campus-form">
          CSV content
          <textarea
            aria-label="CSV content"
            rows={7}
            value={csv}
            placeholder={
              "email,role,department\nstudent@example.org,student,Science"
            }
            onChange={(e) => {
              setCsv(e.target.value);
              setResult(undefined);
            }}
          />
        </label>
        {error && (
          <p role="alert" className="campus-error my-3">
            {error}
          </p>
        )}
        {result && (
          <>
            <p className="campus-notice my-3">
              {result.committed
                ? `${result.created} invitations created`
                : `${result.ready} ready · ${result.available_seats} seats available · ${result.errors} errors`}
            </p>
            <div className="campus-table-wrap max-h-64 overflow-auto">
              <table className="campus-table">
                <thead>
                  <tr>
                    <th>Row</th>
                    <th>Email</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {result.rows.map((r) => (
                    <tr key={r.row}>
                      <td>{r.row}</td>
                      <td>{r.email}</td>
                      <td>
                        {r.status}
                        <small>{r.message}</small>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}
        <div className="brand-share-options">
          <Button
            variant="outline"
            disabled={busy || !csv}
            onClick={() => run(false)}
          >
            Preview import
          </Button>
          <Button
            disabled={
              busy ||
              !result ||
              result.errors > 0 ||
              result.ready === 0 ||
              result.committed
            }
            onClick={() => run(true)}
          >
            Create {result?.ready || 0} invitations
          </Button>
        </div>
      </GlassDialog>
    </>
  );
}

export function SendInviteEmail({
  id,
  invite,
}: {
  id: number;
  invite: number;
}) {
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");
  return (
    <div>
      <Button
        size="sm"
        variant="outline"
        disabled={busy || status === "queued" || status === "sent"}
        onClick={async () => {
          setBusy(true);
          setError("");
          try {
            const r = await campusApi.sendInvite(id, invite);
            setStatus(r.data.status);
            toast.success("Delivery request recorded");
          } catch (e) {
            setError(apiError(e));
          } finally {
            setBusy(false);
          }
        }}
      >
        {status === "queued"
          ? "Email queued"
          : status === "sent"
            ? "Email sent"
            : "Send email"}
      </Button>
      {error && (
        <p role="alert" className="campus-error mt-2">
          {error}
        </p>
      )}
    </div>
  );
}

export function CampusResources({ data }: { data: InstitutionOverview }) {
  const { institution: inst } = data;
  const user = useAuthStore((s) => s.user);
  const staff = ["owner", "admin", "teacher"].includes(inst.role);
  const manager = ["owner", "admin"].includes(inst.role);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [remove, setRemove] = useState<number>();
  const q = useQuery({
    queryKey: ["campus-resources", user?.id, inst.id],
    queryFn: () => campusApi.resources(inst.id),
  });
  async function download(id: number, filename: string) {
    try {
      const blob = await campusApi.resource(inst.id, id);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      a.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (e) {
      setError(apiError(e));
    }
  }
  return (
    <>
      <BrandBanner
        compact
        title="Good resources keep discovery going."
        description="A private library for your institution. Share lesson notes, worksheets and reference material with the right batch."
      />
      {staff && (
        <form
          className="campus-panel campus-form"
          onSubmit={async (e) => {
            e.preventDefault();
            const form = e.currentTarget;
            const f = new FormData(form);
            if (!f.get("batch_id")) f.delete("batch_id");
            setBusy(true);
            setError("");
            try {
              await campusApi.upload(inst.id, f);
              form.reset();
              await q.refetch();
              toast.success("Resource uploaded");
            } catch (err) {
              setError(apiError(err));
            } finally {
              setBusy(false);
            }
          }}
        >
          <h2>Upload a private resource</h2>
          <div className="campus-form-grid">
            <label>
              Resource title
              <input name="title" required minLength={2} maxLength={160} />
            </label>
            <label>
              Share with
              <select name="batch_id">
                <option value="">All institution members</option>
                {data.batches.map((b) => (
                  <option key={b.id} value={b.id}>
                    {b.name}
                  </option>
                ))}
              </select>
            </label>
          </div>
          <label>
            PDF, text or CSV · maximum 5 MB
            <input name="file" type="file" accept=".pdf,.txt,.csv" required />
          </label>
          <Button type="submit" disabled={busy}>
            Upload resource
          </Button>
        </form>
      )}
      {error && (
        <p className="campus-error" role="alert">
          {error}
        </p>
      )}
      {q.isError && (
        <Button variant="outline" onClick={() => q.refetch()}>
          Retry loading resources
        </Button>
      )}
      <div className="campus-grid">
        {q.data?.map((r) => (
          <article className="campus-panel" key={r.id}>
            <span className="campus-chip">
              {r.batch_id
                ? data.batches.find((b) => b.id === r.batch_id)?.name ||
                  "Assigned batch"
                : "Institution library"}
            </span>
            <h3>{r.title}</h3>
            <p className="campus-muted">
              {new Date(r.created_at).toLocaleDateString()}
            </p>
            <div className="campus-actions mt-4">
              <Button
                variant="outline"
                onClick={() => download(r.id, r.filename)}
              >
                Download
              </Button>
              {manager && (
                <Button variant="ghost" onClick={() => setRemove(r.id)}>
                  Remove
                </Button>
              )}
            </div>
          </article>
        ))}
      </div>
      {q.data?.length === 0 && (
        <p className="campus-panel campus-muted">
          Your library is ready for its first resource.
        </p>
      )}
      <GlassDialog
        open={!!remove}
        onOpenChange={(v) => {
          if (!v) setRemove(undefined);
        }}
        title="Remove this resource?"
      >
        <p>
          Members will no longer be able to download it from the campus library.
        </p>
        {error && (
          <p role="alert" className="campus-error">
            {error}
          </p>
        )}
        <Button
          className="mt-4"
          disabled={busy}
          onClick={async () => {
            setBusy(true);
            try {
              await campusApi.removeResource(inst.id, remove!);
              await q.refetch();
              setRemove(undefined);
            } catch (e) {
              setError(apiError(e));
            } finally {
              setBusy(false);
            }
          }}
        >
          Remove resource
        </Button>
      </GlassDialog>
    </>
  );
}

export function CampusBrandedHero({
  id,
  compact = false,
}: {
  id: number;
  compact?: boolean;
}) {
  const user = useAuthStore((s) => s.user);
  const q = useQuery({
    queryKey: ["campus-branding", user?.id, id],
    queryFn: () => campusApi.branding(id),
  });
  const [image, setImage] = useState<string>();
  useEffect(() => {
    let active = true;
    let url: string | undefined;
    setImage(undefined);
    if (q.data?.has_image)
      campusApi
        .image(id)
        .then((blob) => {
          url = URL.createObjectURL(blob);
          if (active) setImage(url);
          else URL.revokeObjectURL(url);
        })
        .catch(() => undefined);
    return () => {
      active = false;
      if (url) URL.revokeObjectURL(url);
    };
  }, [id, user?.id, q.dataUpdatedAt, q.data?.has_image]);
  return (
    <BrandBanner
      compact={compact}
      title={q.data?.title || "Your campus. Every possibility."}
      description={q.data?.subtitle || "Learn, connect and grow together."}
      image={image}
    />
  );
}

export function CampusBranding({ id }: { id: number }) {
  const user = useAuthStore((s) => s.user);
  const q = useQuery({
    queryKey: ["campus-branding", user?.id, id],
    queryFn: () => campusApi.branding(id),
  });
  return q.data ? (
    <BrandingEditor
      key={q.dataUpdatedAt}
      id={id}
      data={q.data}
      saved={() => q.refetch()}
    />
  ) : q.isError ? (
    <Button onClick={() => q.refetch()}>Retry banner settings</Button>
  ) : null;
}
function BrandingEditor({
  id,
  data,
  saved,
}: {
  id: number;
  data: Branding;
  saved: () => Promise<unknown>;
}) {
  const [title, setTitle] = useState(data.title);
  const [subtitle, setSubtitle] = useState(data.subtitle);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function run(fn: () => Promise<unknown>) {
    setBusy(true);
    setError("");
    try {
      await fn();
      await saved();
      toast.success("Campus banner saved");
    } catch (e) {
      setError(apiError(e));
    } finally {
      setBusy(false);
    }
  }
  return (
    <section className="campus-panel">
      <h2 className="mb-5">Your campus banner</h2>
      <BrandBanner compact title={title} description={subtitle} />
      <form
        className="campus-form mt-5"
        onSubmit={(e) => {
          e.preventDefault();
          run(() => campusApi.saveBranding(id, { title, subtitle }));
        }}
      >
        <label>
          Banner headline
          <input
            required
            minLength={2}
            maxLength={160}
            value={title}
            onChange={(e) => setTitle(e.target.value)}
          />
        </label>
        <label>
          Supporting message
          <textarea
            maxLength={320}
            value={subtitle}
            onChange={(e) => setSubtitle(e.target.value)}
          />
        </label>
        <Button type="submit" disabled={busy}>
          Save banner text
        </Button>
      </form>
      <label className="brand-share-upload">
        Upload campus artwork · PNG, JPEG or WebP under 5 MB
        <input
          disabled={busy}
          type="file"
          accept="image/png,image/jpeg,image/webp"
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) run(() => campusApi.uploadImage(id, file));
          }}
        />
      </label>
      {data.has_image && (
        <Button
          variant="outline"
          disabled={busy}
          onClick={() => run(() => campusApi.removeImage(id))}
        >
          Remove uploaded artwork
        </Button>
      )}
      <p className="brand-share-note">
        Your banner is visible to institution members. Uploaded files are
        protected by campus membership.
      </p>
      {error && (
        <p className="campus-error" role="alert">
          {error}
        </p>
      )}
    </section>
  );
}
