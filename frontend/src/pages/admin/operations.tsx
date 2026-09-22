import { PageLayout, PageHeader } from "@/components/design-system/PageLayout";
import {LaunchReadiness} from '@/components/admin/LaunchReadiness';
import { RuntimeMonitor } from '@/components/admin/RuntimeMonitor';
import { BusinessPortfolio } from "@/components/admin/BusinessPortfolio";
import { CommercialControlPlane } from "@/components/admin/CommercialControlPlane";
import { GrowthControlPlane } from "@/components/admin/GrowthControlPlane";
import { TenantControlPlane } from "@/components/admin/TenantControlPlane";
import { MeiporulOperationsPanel } from "@/components/admin/MeiporulOperationsPanel";
import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { Activity, Download, RefreshCw } from "lucide-react";
import {
  operationsAPI,
  downloadBlob,
  type OperationsSummary,
  type RevenueReport,
  type AdminRows,
} from "@/api/operations";
import { plannerError } from "@/api/planner";
import { businessDate } from "@/utils/businessTime";

const input = "rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm";
const button = input + " font-medium disabled:opacity-40";
const box = "rounded-xl border bg-white p-5";

export default function OperationsCenter() {
  const [params, setParams] = useSearchParams();
  const view = params.get("view") || "portfolio";
  const [summary, setSummary] = useState<OperationsSummary | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const request = useRef(0);
  const load = useCallback(async () => {
    const id = (request.current += 1);
    setBusy(true);
    try {
      const data = await operationsAPI.summary();
      if (id === request.current) {
        setSummary(data);
        setError("");
      }
    } catch (e) {
      if (id === request.current) setError(plannerError(e));
    } finally {
      if (id === request.current) setBusy(false);
    }
  }, []);
  useEffect(() => {
    load();
    const timer = setInterval(load, 60000);
    return () => {
      clearInterval(timer);
      request.current += 1;
    };
  }, [load]);
  const tabs = [
    ["portfolio", "Business portfolio"],
    ["tenants", "Tenants & access"],
    ["commercial", "Commercial"],
    ["growth", "Growth OS"],
    ["meiporul", "Meiporul"],
    ["seyappaduporul", "Seyappaduporul"],
    ["utporul", "Utporul"],
    ["daily", "Daily operations"],
    ["tables", "Platform inventory"],
    ["outcomes", "Learning outcomes"],
    ["revenue", "Revenue"],
    ["health", "System health"],
    ["runtime", "Runtime monitor"],
    ["readiness", "Launch readiness"],
  ];
  return (
    <PageLayout
      header={
        <PageHeader>
          <div>
            <p className="text-xs font-semibold uppercase tracking-widest text-orange-700">
              Administration
            </p>
            <h1 className="mt-2 text-3xl font-bold">Sasha Control Center</h1>
            <p className="mt-2 text-slate-600">
              Control all three business pillars with one reporting, people,
              content, revenue, and service-health layer.
            </p>
          </div>
          <button
            className={button + " flex items-center gap-2"}
            disabled={busy}
            onClick={load}
          >
            <RefreshCw size={16} />
            Refresh
          </button>
        </PageHeader>
      }
      className="rd-screen rd-screen-admin-operations"
    >
      <nav aria-label="Operations segments" className="flex flex-wrap gap-2">
        {tabs.map(([id, label]) => (
          <button
            key={id}
            onClick={() => setParams({ view: id })}
            aria-pressed={view === id}
            className={
              button +
              (view === id
                ? " border-orange-500 bg-orange-50 text-orange-800"
                : "")
            }
          >
            {label}
          </button>
        ))}
      </nav>
      {error && (
        <p role="alert" className="rounded-lg bg-rose-50 p-4 text-rose-800">
          {error}
        </p>
      )}
      {summary && (
        <p className="text-xs text-slate-500">
          Updated {new Date(summary.as_of).toLocaleString()} · Refreshes every
          minute
        </p>
      )}
      {view === "growth" ? <GrowthControlPlane /> : view === "runtime" ? <RuntimeMonitor /> : view === "portfolio" ? <BusinessPortfolio /> : view === "tenants" ? (
        <TenantControlPlane />
      ) : view === "commercial" ? (
        <CommercialControlPlane />
      ) : view === "meiporul" ? (
        <div className="space-y-6">
          <BusinessPortfolio focus="meiporul" />
          <MeiporulOperationsPanel />
        </div>
      ) : view === "seyappaduporul" ? (
        <BusinessPortfolio focus="seyappaduporul" />
      ) : view === "utporul" ? (
        <BusinessPortfolio focus="utporul" />
      ) : view === "readiness" ? <LaunchReadiness/> : view === "tables" ? (
        <AdminDataTable />
      ) : view === "revenue" ? (
        <RevenueView />
      ) : !summary ? (
        <p role="status">
          {busy
            ? "Loading operational data…"
            : "Operational data is unavailable. Retry refresh."}
        </p>
      ) : (
        <>
          {view === "daily" && (
            <>
              <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
                {summary.queues.map((queue) => (
                  <a
                    key={queue.key}
                    href={`#queue-${queue.key}`}
                    className={box}
                  >
                    <p className="text-sm text-slate-600">{queue.label}</p>
                    <p className="mt-2 text-3xl font-bold">{queue.count}</p>
                  </a>
                ))}
              </div>
              <div className="grid items-start gap-5 lg:grid-cols-2">
                {summary.queues.map((queue) => (
                  <section
                    id={`queue-${queue.key}`}
                    className={box}
                    key={queue.key}
                  >
                    <h2 className="text-lg font-semibold">{queue.label}</h2>
                    {queue.items.length ? (
                      <ul className="mt-3 divide-y">
                        {queue.items.map((item) => (
                          <li
                            className="flex items-start justify-between gap-4 py-3"
                            key={item.id}
                          >
                            <div>
                              <p className="text-sm font-medium">
                                {item.title}
                              </p>
                              <p className="mt-1 text-xs text-slate-500">
                                {item.age_hours == null
                                  ? "Age unavailable"
                                  : `${item.age_hours} hours waiting`}
                              </p>
                            </div>
                            <Link
                              className="text-sm font-medium text-orange-700 underline"
                              to={item.href}
                            >
                              Review
                            </Link>
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <p className="mt-4 text-sm text-slate-500">
                        Nothing waiting in this queue.
                      </p>
                    )}
                    {queue.count > queue.items.length && (
                      <p className="mt-3 text-xs text-slate-500">
                        Showing the oldest {queue.items.length} of {queue.count}
                        .
                      </p>
                    )}
                  </section>
                ))}
              </div>
            </>
          )}
          {view === "outcomes" && (
            <>
              <div className="grid gap-4 sm:grid-cols-2">
                <div className={box}>
                  <p className="text-sm text-slate-600">
                    Paired practice and delayed checks
                  </p>
                  <p className="mt-2 text-3xl font-bold">
                    {summary.outcomes.paired_interventions}
                  </p>
                </div>
                <div className={box}>
                  <p className="text-sm text-slate-600">
                    Mean delayed score change
                  </p>
                  <p className="mt-2 text-3xl font-bold">
                    {summary.outcomes.mean_delayed_change == null
                      ? "Not enough evidence"
                      : `${summary.outcomes.mean_delayed_change > 0 ? "+" : ""}${summary.outcomes.mean_delayed_change} points`}
                  </p>
                  <p className="mt-2 text-xs text-slate-500">
                    Observed score change; this does not establish that an
                    intervention caused improvement.
                  </p>
                </div>
              </div>
              <section className={box + " overflow-x-auto"}>
                <h2 className="mb-4 text-lg font-semibold">
                  Course completion
                </h2>
                <table className="w-full text-left text-sm">
                  <thead>
                    <tr className="border-b">
                      <th className="p-3">Course</th>
                      <th>Learners</th>
                      <th>Completed</th>
                      <th>Completion</th>
                      <th>Mean progress</th>
                    </tr>
                  </thead>
                  <tbody>
                    {summary.outcomes.courses.map((c) => (
                      <tr className="border-b" key={c.course_id}>
                        <td className="p-3">{c.title}</td>
                        <td>{c.learners}</td>
                        <td>{c.completed}</td>
                        <td>{c.completion_rate}%</td>
                        <td>{c.mean_progress}%</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                {!summary.outcomes.courses.length && (
                  <p className="p-4 text-slate-500">
                    No active or completed enrollments yet.
                  </p>
                )}
              </section>
              <section className={box}>
                <h2 className="mb-3 font-semibold">Concepts needing support</h2>
                {summary.outcomes.struggling_concepts.map((c) => (
                  <div
                    key={c.concept}
                    className="flex justify-between border-b py-3 text-sm"
                  >
                    <span>{c.concept}</span>
                    <span>{c.open_interventions} open interventions</span>
                  </div>
                ))}
                {!summary.outcomes.struggling_concepts.length && (
                  <p className="text-sm text-slate-500">
                    No open concept interventions.
                  </p>
                )}
              </section>
            </>
          )}
          {view === "health" && (
            <>
              <div className="grid gap-4 sm:grid-cols-3">
                <div className={box}>
                  <Activity className="text-emerald-600" />
                  <h2 className="mt-2 font-semibold">Database</h2>
                  <p>{summary.health.database}</p>
                </div>
                <div className={box}>
                  <h2 className="font-semibold">Local transcription</h2>
                  <p className="mt-2">
                    {summary.health.transcription.configured
                      ? "Configured"
                      : "Needs setup"}
                  </p>
                  <p className="mt-2 text-xs text-slate-500">
                    {summary.health.transcription.note}
                  </p>
                </div>
                <div className={box}>
                  <h2 className="font-semibold">Storage available</h2>
                  <p className="mt-2 text-2xl">
                    {summary.health.storage.free_bytes == null ? "Unavailable" : `${(summary.health.storage.free_bytes / 1024 ** 3).toFixed(1)} GB`}
                  </p>
                  <p className="text-sm text-slate-500">
                    {summary.health.storage.free_percent == null ? "Check the configured upload directory or storage mount." : `${summary.health.storage.free_percent}% free`}
                  </p>
                </div>
              </div>
              <section className={box}>
                <h2 className="font-semibold">Background services</h2>
                {summary.health.services.map((s) => (
                  <div
                    className="flex flex-wrap justify-between gap-3 border-b py-4"
                    key={s.name}
                  >
                    <div>
                      <p>{s.name.replace(/_/g, " ")}</p>
                      <p className="mt-1 text-xs text-slate-500">
                        {s.last_seen
                          ? `Last seen ${new Date(s.last_seen).toLocaleString()}`
                          : "No heartbeat recorded"}
                      </p>
                    </div>
                    <span className="text-sm font-semibold">{s.status}</span>
                  </div>
                ))}
                <p className="mt-4 text-xs text-slate-500">
                  {summary.health.note}
                </p>
              </section>
              <section className={box}>
                <h2 className="font-semibold">Recording pipeline</h2>
                <div className="mt-4 flex flex-wrap gap-3">
                  {Object.entries(summary.health.recording_jobs).map(
                    ([s, n]) => (
                      <span
                        key={s}
                        className="rounded-lg bg-slate-100 px-3 py-2 text-sm"
                      >
                        {s.replace(/_/g, " ")}: {n}
                      </span>
                    ),
                  )}
                </div>
              </section>
            </>
          )}
        </>
      )}
    </PageLayout>
  );
}

function AdminDataTable() {
  const [dataset, setDataset] = useState("courses");
  const [q, setQ] = useState("");
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");
  const [page, setPage] = useState(1);
  const [sort, setSort] = useState("created");
  const [order, setOrder] = useState("desc");
  const [data, setData] = useState<AdminRows | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    let alive = true;
    setBusy(true);
    setData(null);
    operationsAPI
      .rows(dataset, { q: search, status, page, page_size: 25, sort, order })
      .then((r) => {
        if (alive) {
          setData(r);
          setError("");
        }
      })
      .catch((e) => {
        if (alive) setError(plannerError(e));
      })
      .finally(() => {
        if (alive) setBusy(false);
      });
    return () => {
      alive = false;
    };
  }, [dataset, search, status, page, sort, order]);
  const statuses =
    dataset === "courses"
      ? ["draft", "pending", "publish", "published"]
      : dataset === "orders"
        ? [
            "pending",
            "processing",
            "completed",
            "failed",
            "refunded",
            "cancelled",
          ]
        : dataset === "enrollments"
          ? ["enrolled", "completed", "cancelled", "suspended"]
          : dataset === "students" || dataset === "instructors"
            ? ["active", "inactive"]
            : dataset === "ebooks"
              ? ["draft", "published"]
              : dataset === "three_d_models"
                ? ["library", "private"]
                : dataset === "virtual_labs"
                  ? ["published", "draft"]
                  : dataset === "geogebra"
                    ? ["available"]
                    : dataset === "certificates"
                      ? ["valid", "invalid"]
                      : dataset === "live_classes"
                        ? ["scheduled", "live", "ended", "cancelled"]
                        : dataset === "exam_papers"
                          ? ["awaiting_payment", "queued", "processing", "ready", "failed"]
                          : ["draft", "pending", "publish", "published"];
  async function exportCsv() {
    try {
      downloadBlob(
        await operationsAPI.csv(dataset, { q: search, status, sort, order }),
        `${dataset}.csv`,
      );
    } catch (e) {
      setError(plannerError(e));
    }
  }
  return (
    <section className={box + " space-y-5"}>
      <div className="flex flex-wrap items-end gap-3">
        <label className="text-sm">
          Dataset
          <select
            className={input + " ml-2"}
            value={dataset}
            onChange={(e) => {
              setDataset(e.target.value);
              setPage(1);
              setStatus("");
            }}
          >
            {[
              "courses",
              "lessons",
              "ebooks",
              "three_d_models",
              "virtual_labs",
              "geogebra",
              "live_classes",
              "quizzes",
              "certificates",
              "exam_papers",
              "students",
              "instructors",
              "orders",
              "enrollments",
            ].map((s) => (
              <option key={s}>{s}</option>
            ))}
          </select>
        </label>
        <form
          className="flex gap-2"
          onSubmit={(e) => {
            e.preventDefault();
            setSearch(q);
            setPage(1);
          }}
        >
          <input
            aria-label="Search records"
            className={input}
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Search records…"
          />
          <button className={button}>Search</button>
        </form>
        <select
          aria-label="Status filter"
          className={input}
          value={status}
          onChange={(e) => {
            setStatus(e.target.value);
            setPage(1);
          }}
        >
          <option value="">All statuses</option>
          {statuses.map((s) => (
            <option key={s}>{s}</option>
          ))}
        </select>
        <select
          aria-label="Sort records"
          className={input}
          value={sort}
          onChange={(e) => {
            setSort(e.target.value);
            setPage(1);
          }}
        >
          {["created", "name", "status", "id"].map((s) => (
            <option key={s}>{s}</option>
          ))}
        </select>
        <select
          aria-label="Sort direction"
          className={input}
          value={order}
          onChange={(e) => {
            setOrder(e.target.value);
            setPage(1);
          }}
        >
          <option value="desc">Descending</option>
          <option value="asc">Ascending</option>
        </select>
        <button
          className={button + " flex items-center gap-2"}
          disabled={busy}
          onClick={exportCsv}
        >
          <Download size={16} />
          Export filtered CSV
        </button>
      </div>
      {error && (
        <p role="alert" className="text-rose-700">
          {error}
        </p>
      )}
      <div className="overflow-x-auto" aria-busy={busy}>
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b">
              <th className="p-3">Name</th>
              <th>Details</th>
              <th>Status</th>
              <th>Created</th>
              <th>Amount</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {data?.items.map((r) => (
              <tr key={r.id} className="border-b">
                <td className="p-3 font-medium">{r.name}</td>
                <td className="p-2">{r.detail}</td>
                <td className="p-2">{r.status}</td>
                <td className="p-2">
                  {r.created ? new Date(r.created).toLocaleDateString() : "—"}
                </td>
                <td className="p-2">
                  {r.amount?.toLocaleString("en-IN") ?? "—"}
                </td>
                <td>
                  <Link className="text-orange-700 underline" to={r.href}>
                    Open
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {busy ? (
          <p className="p-4 text-sm">Loading records…</p>
        ) : (
          !data?.items.length && (
            <p className="p-4 text-sm text-slate-500">
              No records match these filters.
            </p>
          )
        )}
      </div>
      <div className="flex items-center justify-between">
        <p className="text-sm text-slate-500">
          {data?.total || 0} records · Page {page}
        </p>
        <div className="flex gap-2">
          <button
            className={button}
            disabled={busy || page === 1}
            onClick={() => setPage((p) => p - 1)}
          >
            Previous
          </button>
          <button
            className={button}
            disabled={busy || !data || page * data.page_size >= data.total}
            onClick={() => setPage((p) => p + 1)}
          >
            Next
          </button>
        </div>
      </div>
    </section>
  );
}

function RevenueView() {
  const [start, setStart] = useState(
    businessDate(-30),
  );
  const [end, setEnd] = useState(businessDate());
  const [report, setReport] = useState<RevenueReport | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const request = useRef(0);
  const load = useCallback(async () => {
    const id = (request.current += 1);
    setBusy(true);
    setReport(null);
    setError("");
    try {
      const data = await operationsAPI.revenue(start, end);
      if (id === request.current) setReport(data);
    } catch (e) {
      if (id === request.current) setError(plannerError(e));
    } finally {
      if (id === request.current) setBusy(false);
    }
  }, [start, end]);
  useEffect(() => {
    load();
    return () => {
      request.current += 1;
    };
  }, [load]);
  const money = (n: number, currency = "INR") => {
    try {
      return new Intl.NumberFormat("en-IN", {
        style: "currency",
        currency,
      }).format(n);
    } catch {
      return `${currency} ${n.toFixed(2)}`;
    }
  };
  return (
    <div className="space-y-5">
      <div className="flex flex-wrap gap-3">
        <label className="text-sm">
          From{" "}
          <input
            type="date"
            className={input}
            value={start}
            onChange={(e) => setStart(e.target.value)}
          />
        </label>
        <label className="text-sm">
          To{" "}
          <input
            type="date"
            className={input}
            value={end}
            onChange={(e) => setEnd(e.target.value)}
          />
        </label>
        <button className={button} disabled={busy} onClick={load}>
          Refresh revenue
        </button>
      </div>
      {error && (
        <p role="alert" className="text-rose-700">
          {error}
        </p>
      )}
      {report && (
        <>
          <div className="grid gap-4 sm:grid-cols-3">
            {report.currencies.map((c) => (
              <section className={box} key={c.currency}>
                <p className="font-semibold">{c.currency} cash flow</p>
                <p className="mt-3 text-sm">
                  Captured: {money(c.captured, c.currency)}
                </p>
                <p className="mt-2 text-sm">
                  Refunded: {money(c.refunded, c.currency)}
                </p>
                <p className="mt-3 text-xl font-bold">
                  Net: {money(c.net_cash, c.currency)}
                </p>
              </section>
            ))}
            {!report.currencies.length && (
              <p className={box}>No captured payments in this period.</p>
            )}
            <section className={box}>
              <p className="text-sm text-slate-600">
                Estimated active subscription MRR
              </p>
              <p className="mt-3 text-2xl font-bold">
                {money(report.estimated_active_mrr_inr)}
              </p>
            </section>
          </div>
          <div className={box}>
            <h2 className="font-semibold">Payment operations</h2>
            <p className="mt-3 text-sm">
              {report.failed_payments} failed payments ·{" "}
              {report.refunds_needing_attention} refunds needing attention ·{" "}
              {report.refunds_missing_timestamp} refunds without a processing
              timestamp
            </p>
            <Link
              to="/admin/orders"
              className="mt-3 inline-block text-sm text-orange-700 underline"
            >
              Open payments and reconciliation
            </Link>
            <p className="mt-4 text-xs text-slate-500">{report.note}</p>
          </div>
        </>
      )}
    </div>
  );
}
