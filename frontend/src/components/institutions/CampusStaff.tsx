import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import toast from "react-hot-toast";
import type { InstitutionOverview } from "@/api/institutions";
import {
  staffApi,
  type LeaveRequest,
  type LeaveStatus,
  type Substitution,
  type SubstitutionStatus,
} from "@/api/campus-staff";
import { openBlob } from "@/api/campus-exams";
import { Button } from "@/components/ui/button";
import { GlassDialog } from "@/components/ui/dialog";
import { BrandBanner } from "@/components/design-system/BrandBanner";
import {
  CampusOsBadge,
  CampusOsEmpty,
  CampusOsError,
  CampusOsLoading,
  errorMessage,
  formatDate,
  formatTime,
  readable,
} from "./CampusOsPrimitives";

const LEAVE_TONE: Record<LeaveStatus, "warning" | "success" | "danger" | "neutral"> = {
  pending: "warning",
  approved: "success",
  rejected: "danger",
  cancelled: "neutral",
};
const SUB_TONE: Record<SubstitutionStatus, "warning" | "success" | "neutral"> = {
  open: "warning",
  assigned: "success",
  released: "neutral",
};

type Tab = "mine" | "approvals" | "substitutions" | "types" | "report";

export function CampusStaff({ data }: { data: InstitutionOverview }) {
  const { institution: inst } = data;
  const manager = ["owner", "admin"].includes(inst.role);
  const [tab, setTab] = useState<Tab>("mine");
  const queryClient = useQueryClient();
  const invalidate = () => queryClient.invalidateQueries({ queryKey: ["campus-staff", inst.id] });
  const tabs: { key: Tab; label: string; manager?: boolean }[] = [
    { key: "mine", label: "My leave" },
    { key: "approvals", label: "Approvals", manager: true },
    { key: "substitutions", label: "Substitutions" },
    { key: "types", label: "Leave types", manager: true },
    { key: "report", label: "Report", manager: true },
  ];
  return (
    <>
      <BrandBanner
        compact
        title="Time off, covered."
        description={
          manager
            ? "Approve leave against quotas, then assign a free colleague to every class the absent teacher owns."
            : "Apply for leave, track your balances, and see the classes you are covering for colleagues."
        }
      />
      <div className="campus-tabs" role="tablist">
        {tabs
          .filter((t) => !t.manager || manager)
          .map((t) => (
            <button key={t.key} role="tab" type="button" aria-selected={tab === t.key} className="campus-chip" onClick={() => setTab(t.key)}>
              {t.label}
            </button>
          ))}
      </div>
      {tab === "mine" && <MyLeave institutionId={inst.id} invalidate={invalidate} />}
      {tab === "approvals" && manager && <Approvals institutionId={inst.id} invalidate={invalidate} />}
      {tab === "substitutions" && <Substitutions institutionId={inst.id} manager={manager} invalidate={invalidate} />}
      {tab === "types" && manager && <LeaveTypes institutionId={inst.id} academicYear={inst.academic_year} invalidate={invalidate} />}
      {tab === "report" && manager && <Report institutionId={inst.id} />}
    </>
  );
}

function LeaveTable({ rows, actions }: { rows: LeaveRequest[]; actions?: (row: LeaveRequest) => React.ReactNode }) {
  return (
    <div className="campus-table-wrap">
      <table className="campus-table">
        <thead>
          <tr>
            <th>Staff</th>
            <th>Type</th>
            <th>Dates</th>
            <th>Days</th>
            <th>Status</th>
            <th>Cover</th>
            {actions && <th />}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.id}>
              <td>{row.member_name ?? "—"}</td>
              <td>{row.type_name ?? row.type_code}</td>
              <td>
                {formatDate(row.starts_on)} – {formatDate(row.ends_on)}
                {row.note && <small>{row.note}</small>}
              </td>
              <td>{row.days}</td>
              <td>
                <CampusOsBadge tone={LEAVE_TONE[row.status]}>{readable(row.status)}</CampusOsBadge>
                {row.decision_note && <small>{row.decision_note}</small>}
                {row.override && <small>Quota overridden</small>}
              </td>
              <td>
                {row.substitutions.total ? `${row.substitutions.assigned} / ${row.substitutions.total} assigned` : "—"}
              </td>
              {actions && <td>{actions(row)}</td>}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function MyLeave({ institutionId, invalidate }: { institutionId: number; invalidate: () => Promise<void> }) {
  const types = useQuery({ queryKey: ["campus-staff", institutionId, "types"], queryFn: () => staffApi.types(institutionId) });
  const balances = useQuery({ queryKey: ["campus-staff", institutionId, "balances"], queryFn: () => staffApi.balances(institutionId) });
  const mine = useQuery({ queryKey: ["campus-staff", institutionId, "leave", "mine"], queryFn: () => staffApi.leave(institutionId) });
  const [open, setOpen] = useState(false);
  const [error, setError] = useState("");
  const create = useMutation({
    mutationFn: (input: { type_id: number; starts_on: string; ends_on: string; note: string }) => staffApi.createLeave(institutionId, input),
    onSuccess: () => {
      setOpen(false);
      setError("");
      toast.success("Leave request sent for approval");
      void invalidate();
    },
    onError: (cause) => setError(errorMessage(cause, "The leave request couldn’t be sent.")),
  });
  const cancel = useMutation({
    mutationFn: (leaveId: number) => staffApi.cancel(institutionId, leaveId),
    onSuccess: () => {
      toast.success("Leave cancelled");
      void invalidate();
    },
    onError: (cause) => toast.error(errorMessage(cause, "The leave couldn’t be cancelled.")),
  });
  return (
    <>
      <div className="campus-panel">
        <div className="campus-panel-heading">
          <div>
            <h2>Balances</h2>
            <p className="campus-muted">{balances.data?.academic_year}</p>
          </div>
          <Button disabled={!types.data?.types.length} onClick={() => setOpen(true)}>
            Apply for leave
          </Button>
        </div>
        {balances.isLoading && <CampusOsLoading label="Loading balances" />}
        {balances.data && !balances.data.balances.length && (
          <p className="campus-muted">No leave types are set up for this year yet. Ask a campus manager.</p>
        )}
        <div className="campus-actions">
          {balances.data?.balances.map((b) => (
            <span className="campus-chip" key={b.type_id}>
              {b.name}: {b.remaining} of {b.quota} left
            </span>
          ))}
        </div>
      </div>
      <section className="campus-panel">
        <h2>My requests</h2>
        {mine.isLoading && <CampusOsLoading label="Loading leave requests" />}
        {mine.isError && <CampusOsError message="Leave requests couldn’t be loaded." retry={() => void mine.refetch()} />}
        {mine.data && !mine.data.length && <CampusOsEmpty title="No leave requests yet" description="Apply for leave and a manager will review it." />}
        {!!mine.data?.length && (
          <LeaveTable
            rows={mine.data}
            actions={(row) =>
              ["pending", "approved"].includes(row.status) ? (
                <Button size="sm" variant="outline" loading={cancel.isPending} onClick={() => cancel.mutate(row.id)}>
                  Cancel
                </Button>
              ) : null
            }
          />
        )}
      </section>
      <GlassDialog open={open} onOpenChange={setOpen} title="Apply for leave">
        <form
          className="campus-form-grid"
          onSubmit={(event) => {
            event.preventDefault();
            const form = new FormData(event.currentTarget);
            create.mutate({
              type_id: Number(form.get("type_id")),
              starts_on: String(form.get("starts_on")),
              ends_on: String(form.get("ends_on")),
              note: String(form.get("note") || "").trim(),
            });
          }}
        >
          {error && (
            <p role="alert" className="campus-error">
              {error}
            </p>
          )}
          <label className="campus-form">
            Leave type
            <select className="campus-select" name="type_id" required defaultValue={types.data?.types[0]?.id}>
              {types.data?.types.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.name}
                </option>
              ))}
            </select>
          </label>
          <label className="campus-form">
            From
            <input className="campus-select" name="starts_on" type="date" required />
          </label>
          <label className="campus-form">
            To
            <input className="campus-select" name="ends_on" type="date" required />
          </label>
          <label className="campus-form">
            Note
            <input className="campus-select" name="note" maxLength={500} placeholder="Reason (optional)" />
          </label>
          <Button type="submit" loading={create.isPending}>
            Send request
          </Button>
        </form>
      </GlassDialog>
    </>
  );
}

function Approvals({ institutionId, invalidate }: { institutionId: number; invalidate: () => Promise<void> }) {
  const [status, setStatus] = useState<LeaveStatus>("pending");
  const list = useQuery({ queryKey: ["campus-staff", institutionId, "leave", status], queryFn: () => staffApi.leave(institutionId, { status }) });
  const [decision, setDecision] = useState<{ row: LeaveRequest; kind: "approve" | "reject" } | null>(null);
  const [note, setNote] = useState("");
  const [override, setOverride] = useState(false);
  const [error, setError] = useState("");
  const decide = useMutation({
    mutationFn: async () => {
      if (!decision) return null;
      return decision.kind === "approve"
        ? staffApi.approve(institutionId, decision.row.id, { override, note })
        : staffApi.reject(institutionId, decision.row.id, note);
    },
    onSuccess: (row) => {
      setDecision(null);
      setNote("");
      setOverride(false);
      setError("");
      if (row) toast.success(row.status === "approved" ? `Approved · ${row.substitutions.total} class${row.substitutions.total === 1 ? "" : "es"} need cover` : "Request rejected");
      void invalidate();
    },
    onError: (cause) => setError(errorMessage(cause, "The decision couldn’t be saved.")),
  });
  return (
    <section className="campus-panel">
      <div className="campus-panel-heading">
        <h2>Leave approvals</h2>
        <label className="campus-form">
          Status
          <select className="campus-select" aria-label="Leave status" value={status} onChange={(e) => setStatus(e.target.value as LeaveStatus)}>
            {(["pending", "approved", "rejected", "cancelled"] as LeaveStatus[]).map((s) => (
              <option key={s} value={s}>
                {readable(s)}
              </option>
            ))}
          </select>
        </label>
      </div>
      {list.isLoading && <CampusOsLoading label="Loading leave requests" />}
      {list.isError && <CampusOsError message="Leave requests couldn’t be loaded." retry={() => void list.refetch()} />}
      {list.data && !list.data.length && <CampusOsEmpty title={`No ${status} requests`} description="Requests from teachers appear here." />}
      {!!list.data?.length && (
        <LeaveTable
          rows={list.data}
          actions={(row) =>
            row.status === "pending" ? (
              <div className="campus-actions">
                <Button size="sm" onClick={() => setDecision({ row, kind: "approve" })}>
                  Approve
                </Button>
                <Button size="sm" variant="outline" onClick={() => setDecision({ row, kind: "reject" })}>
                  Reject
                </Button>
              </div>
            ) : null
          }
        />
      )}
      <GlassDialog
        open={!!decision}
        onOpenChange={(v) => {
          if (!v) setDecision(null);
        }}
        title={decision?.kind === "approve" ? "Approve leave" : "Reject leave"}
      >
        {decision && (
          <form
            className="campus-form-grid"
            onSubmit={(e) => {
              e.preventDefault();
              decide.mutate();
            }}
          >
            <p className="campus-muted">
              {decision.row.member_name} · {decision.row.type_name} · {formatDate(decision.row.starts_on)} – {formatDate(decision.row.ends_on)} ({decision.row.days} day{decision.row.days === 1 ? "" : "s"})
            </p>
            {error && (
              <p role="alert" className="campus-error">
                {error}
              </p>
            )}
            <label className="campus-form">
              {decision.kind === "approve" ? "Note (required when overriding the quota)" : "Reason"}
              <input className="campus-select" aria-label="Decision note" value={note} maxLength={500} onChange={(e) => setNote(e.target.value)} required={decision.kind === "reject"} />
            </label>
            {decision.kind === "approve" && (
              <div className="flex items-center gap-2 text-sm">
                <input id="leave-override" type="checkbox" className="campus-check" checked={override} onChange={(e) => setOverride(e.target.checked)} />
                <label htmlFor="leave-override" className="m-0">
                  Override the quota
                </label>
              </div>
            )}
            <Button type="submit" loading={decide.isPending}>
              {decision.kind === "approve" ? "Approve" : "Reject"}
            </Button>
          </form>
        )}
      </GlassDialog>
    </section>
  );
}

function Substitutions({ institutionId, manager, invalidate }: { institutionId: number; manager: boolean; invalidate: () => Promise<void> }) {
  const [status, setStatus] = useState<SubstitutionStatus | "">(manager ? "open" : "");
  const list = useQuery({
    queryKey: ["campus-staff", institutionId, "substitutions", status],
    queryFn: () => staffApi.substitutions(institutionId, status || undefined),
  });
  const [assigning, setAssigning] = useState<Substitution | null>(null);
  const candidates = useQuery({
    queryKey: ["campus-staff", institutionId, "candidates", assigning?.id],
    queryFn: () => staffApi.candidates(institutionId, assigning!.id),
    enabled: manager && !!assigning,
  });
  const [chosen, setChosen] = useState<number>(0);
  const assign = useMutation({
    mutationFn: () => staffApi.assign(institutionId, assigning!.id, chosen),
    onSuccess: (row) => {
      toast.success(`${row.substitute_name} will cover ${row.title}`);
      setAssigning(null);
      setChosen(0);
      void invalidate();
    },
    onError: (cause) => toast.error(errorMessage(cause, "The substitute couldn’t be assigned.")),
  });
  const unassign = useMutation({
    mutationFn: (subId: number) => staffApi.unassign(institutionId, subId),
    onSuccess: () => {
      toast.success("Substitution reopened");
      void invalidate();
    },
    onError: (cause) => toast.error(errorMessage(cause, "The substitution couldn’t be reopened.")),
  });
  return (
    <section className="campus-panel">
      <div className="campus-panel-heading">
        <div>
          <h2>{manager ? "Classes needing cover" : "My substitutions"}</h2>
          <p className="campus-muted">{manager ? "Only colleagues who are free at that time are offered." : "Classes you are covering, and your own classes being covered."}</p>
        </div>
        <label className="campus-form">
          Status
          <select className="campus-select" aria-label="Substitution status" value={status} onChange={(e) => setStatus(e.target.value as SubstitutionStatus | "")}>
            <option value="">All</option>
            <option value="open">Open</option>
            <option value="assigned">Assigned</option>
            <option value="released">Released</option>
          </select>
        </label>
      </div>
      {list.isLoading && <CampusOsLoading label="Loading substitutions" />}
      {list.isError && <CampusOsError message="Substitutions couldn’t be loaded." retry={() => void list.refetch()} />}
      {list.data && !list.data.length && <CampusOsEmpty title="Nothing to cover" description="Approved leave creates a row here for each timetable slot." />}
      {!!list.data?.length && (
        <div className="campus-table-wrap">
          <table className="campus-table">
            <thead>
              <tr>
                <th>Class</th>
                <th>When</th>
                <th>Absent</th>
                <th>Substitute</th>
                <th>Status</th>
                {manager && <th />}
              </tr>
            </thead>
            <tbody>
              {list.data.map((row) => (
                <tr key={row.id}>
                  <td>
                    {row.title}
                    <small>{[row.batch_name, row.room].filter(Boolean).join(" · ")}</small>
                  </td>
                  <td>{row.starts_at ? `${formatDate(row.starts_at)} · ${formatTime(row.starts_at)}` : "—"}</td>
                  <td>{row.absent_name ?? "—"}</td>
                  <td>{row.substitute_name ?? "—"}</td>
                  <td>
                    <CampusOsBadge tone={SUB_TONE[row.status]}>{readable(row.status)}</CampusOsBadge>
                  </td>
                  {manager && (
                    <td>
                      {row.status === "open" && (
                        <Button size="sm" onClick={() => setAssigning(row)}>
                          Assign
                        </Button>
                      )}
                      {row.status === "assigned" && (
                        <Button size="sm" variant="outline" loading={unassign.isPending} onClick={() => unassign.mutate(row.id)}>
                          Unassign
                        </Button>
                      )}
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <GlassDialog
        open={!!assigning}
        onOpenChange={(v) => {
          if (!v) setAssigning(null);
        }}
        title="Assign a substitute"
      >
        {assigning && (
          <form
            className="campus-form-grid"
            onSubmit={(e) => {
              e.preventDefault();
              if (chosen) assign.mutate();
            }}
          >
            <p className="campus-muted">
              {assigning.title} · {assigning.starts_at ? `${formatDate(assigning.starts_at)} ${formatTime(assigning.starts_at)}` : ""} · covering {assigning.absent_name}
            </p>
            {candidates.isLoading && <CampusOsLoading label="Finding free colleagues" />}
            {candidates.data && !candidates.data.length && <p className="campus-error">No colleague is free at this time.</p>}
            {!!candidates.data?.length && (
              <label className="campus-form">
                Free colleague
                <select className="campus-select" aria-label="Substitute" value={chosen} onChange={(e) => setChosen(Number(e.target.value))}>
                  <option value={0}>Choose…</option>
                  {candidates.data.map((c) => (
                    <option key={c.member_id} value={c.member_id}>
                      {c.name} · {readable(c.role)}
                    </option>
                  ))}
                </select>
              </label>
            )}
            <Button type="submit" disabled={!chosen} loading={assign.isPending}>
              Assign
            </Button>
          </form>
        )}
      </GlassDialog>
    </section>
  );
}

function LeaveTypes({ institutionId, academicYear, invalidate }: { institutionId: number; academicYear: string; invalidate: () => Promise<void> }) {
  const types = useQuery({ queryKey: ["campus-staff", institutionId, "types"], queryFn: () => staffApi.types(institutionId) });
  const [rows, setRows] = useState<{ code: string; name: string; annual_quota: number }[] | null>(null);
  const current = rows ?? types.data?.types.map((t) => ({ code: t.code, name: t.name, annual_quota: t.annual_quota })) ?? [];
  const save = useMutation({
    mutationFn: () => staffApi.saveTypes(institutionId, types.data?.academic_year ?? academicYear, current.filter((r) => r.code && r.name)),
    onSuccess: () => {
      setRows(null);
      toast.success("Leave types saved");
      void invalidate();
    },
    onError: (cause) => toast.error(errorMessage(cause, "Leave types couldn’t be saved.")),
  });
  function update(index: number, patch: Partial<{ code: string; name: string; annual_quota: number }>) {
    setRows(current.map((r, i) => (i === index ? { ...r, ...patch } : r)));
  }
  return (
    <section className="campus-panel">
      <div className="campus-panel-heading">
        <div>
          <h2>Leave types</h2>
          <p className="campus-muted">Annual quotas for {types.data?.academic_year ?? academicYear}. Types with requests cannot be removed.</p>
        </div>
        <Button variant="outline" onClick={() => setRows([...current, { code: "", name: "", annual_quota: 0 }])}>
          Add type
        </Button>
      </div>
      {types.isLoading && <CampusOsLoading label="Loading leave types" />}
      <form
        className="campus-form"
        onSubmit={(e) => {
          e.preventDefault();
          save.mutate();
        }}
      >
        {current.map((row, index) => (
          <div className="campus-form-grid" key={index}>
            <label>
              Code
              <input aria-label={`Type ${index + 1} code`} value={row.code} maxLength={20} onChange={(e) => update(index, { code: e.target.value })} />
            </label>
            <label>
              Name
              <input aria-label={`Type ${index + 1} name`} value={row.name} maxLength={80} onChange={(e) => update(index, { name: e.target.value })} />
            </label>
            <label>
              Annual quota (days)
              <input aria-label={`Type ${index + 1} quota`} type="number" min={0} max={366} value={row.annual_quota} onChange={(e) => update(index, { annual_quota: Number(e.target.value) })} />
            </label>
            <Button type="button" variant="ghost" onClick={() => setRows(current.filter((_, i) => i !== index))}>
              Remove
            </Button>
          </div>
        ))}
        {!current.length && <p className="campus-muted">Add casual, sick or earned leave with an annual quota to let staff apply.</p>}
        <Button type="submit" loading={save.isPending} disabled={!current.length}>
          Save leave types
        </Button>
      </form>
    </section>
  );
}

function Report({ institutionId }: { institutionId: number }) {
  const report = useQuery({ queryKey: ["campus-staff", institutionId, "report"], queryFn: () => staffApi.report(institutionId) });
  return (
    <section className="campus-panel">
      <div className="campus-panel-heading">
        <div>
          <h2>Leave and substitution report</h2>
          <p className="campus-muted">{report.data?.academic_year}</p>
        </div>
        <Button
          variant="outline"
          onClick={() =>
            staffApi
              .reportCsv(institutionId)
              .then((blob) => openBlob(blob, `leave-report-${report.data?.academic_year ?? "campus"}.csv`))
              .catch((e) => toast.error(errorMessage(e, "The report couldn’t be downloaded.")))
          }
        >
          Download CSV
        </Button>
      </div>
      {report.isLoading && <CampusOsLoading label="Loading report" />}
      {report.isError && <CampusOsError message="The report couldn’t be loaded." retry={() => void report.refetch()} />}
      {report.data && (
        <div className="campus-table-wrap">
          <table className="campus-table">
            <thead>
              <tr>
                <th>Staff</th>
                {report.data.types.map((t) => (
                  <th key={t.id}>{t.code} used / quota</th>
                ))}
                <th>Hours covered</th>
              </tr>
            </thead>
            <tbody>
              {report.data.rows.map((row) => (
                <tr key={row.member_id}>
                  <td>
                    {row.name}
                    <small>{readable(row.role)}</small>
                  </td>
                  {report.data!.types.map((t) => (
                    <td key={t.id}>
                      {row.balances[t.code]?.used ?? 0} / {row.balances[t.code]?.quota ?? 0}
                    </td>
                  ))}
                  <td>{row.substitution_hours}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
