import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Activity, ArrowUpRight, RefreshCw, ShieldCheck, Server, AlertTriangle } from "lucide-react";
import { api } from "@/api/axios";
import { plannerError } from "@/api/planner";

interface Job {
  name: string; label: string; status: string; attempts: number; max_attempts: number;
  next_run_at: string | null; last_finished_at: string | null; last_error: string | null; lease_expired: boolean;
}
interface Runtime {
  mode: string; worker: { status: string; last_seen: string | null }; jobs: Job[];
  runs: { id: string; job_name: string; status: string; attempt: number; started_at: string; error_code: string | null }[];
  delivery_semantics: string;
  queues?: Record<string, Record<string, number>>;
  providers?: { provider: string; label: string; status: string; failures: number; last_tested_at: string | null }[];
}
interface Metrics {
  status: string; requests?: number; errors?: number; slow_requests?: number;
  average_ms?: number | null; error_percent?: number | null;
}
const stamp = (value: string | null) => value ? new Date(value).toLocaleString() : "No evidence yet";
const panel = "rounded-2xl border border-orange-200/30 bg-[var(--pb,#ffffff)] p-5 text-slate-900 shadow-sm";
const action = "aurum-secondary inline-flex items-center gap-2 rounded-xl border border-orange-200 bg-white px-4 py-2 text-sm font-semibold disabled:opacity-50";

export function RuntimeMonitor() {
  const [runtime, setRuntime] = useState<Runtime | null>(null);
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [error, setError] = useState("");
  const [pending, setPending] = useState<string | null>(null);
  const [message, setMessage] = useState("");
  const load = useCallback(async (signal?: AbortSignal) => {
    try {
      const [state, counters] = await Promise.all([
        api.get<Runtime>("/admin/operations/runtime", { signal }),
        api.get<Metrics>("/admin/operations/telemetry", { signal }),
      ]);
      if (!signal?.aborted) { setRuntime(state.data); setMetrics(counters.data); setError(""); }
    } catch (e) { if (!signal?.aborted) setError(plannerError(e)); }
  }, []);
  useEffect(() => {
    const controller = new AbortController();
    void load(controller.signal);
    const timer = setInterval(() => void load(controller.signal), 15000);
    return () => { controller.abort(); clearInterval(timer); };
  }, [load]);
  async function retry(name: string) {
    setPending(name); setMessage("");
    try {
      await api.post(`/admin/operations/runtime/${encodeURIComponent(name)}/retry`);
      setMessage("Retry queued. It will be processed when a maintenance worker is running. Your action is recorded in the audit trail.");
      await load();
    } catch (e) { setError(plannerError(e)); }
    finally { setPending(null); }
  }
  const dead = runtime?.jobs.filter(j => j.status === "dead").length ?? 0;
  return <section className="space-y-6" aria-label="Production runtime">
    <div className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-orange-600 via-orange-500 to-amber-400 p-7 text-white">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div><p className="text-xs font-bold uppercase tracking-[0.2em] text-orange-100">SashaInfinity · Operations</p>
          <h2 className="mt-3 text-3xl font-bold">Keep every learning journey moving</h2>
          <p className="mt-3 max-w-2xl text-orange-50">Monitor background work across all three pillars, spot interruptions, and recover failed jobs with a recorded retry.</p></div>
        <button className={action} onClick={() => void load()}><RefreshCw size={16} />Refresh runtime</button>
      </div>
    </div>
    {error && <div className="rounded-xl bg-red-50 p-4 text-red-800" role="alert">{error}</div>}
    {message && <p className="rounded-xl bg-orange-50 p-4 text-orange-900" role="status">{message}</p>}
    {!runtime ? <p role="status">Loading runtime evidence…</p> : <>
      {runtime.mode !== "worker" && <p className={panel} role="status">Maintenance mode: {runtime.mode}. Queued retries require a dedicated worker; the isolated demo does not run one automatically.</p>}
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {[
          { label: "Maintenance worker", value: runtime.worker.status, icon: Server, note: stamp(runtime.worker.last_seen) },
          { label: "Needs attention", value: String(dead), icon: AlertTriangle, note: "Jobs awaiting an operator retry" },
          { label: "Requests · last 15 minutes", value: metrics?.status === "available" ? String(metrics.requests) : "Unavailable", icon: Activity, note: "Shared across API replicas" },
          { label: "Average response", value: metrics?.average_ms != null ? `${metrics.average_ms} ms` : "No measurement", icon: ShieldCheck, note: metrics?.error_percent != null ? `${metrics.error_percent}% server errors` : "Redis metrics required" },
        ].map(card => <div key={card.label} className={panel}><card.icon className="text-orange-600" size={22} /><p className="mt-3 text-sm text-slate-600">{card.label}</p><p className="mt-1 text-2xl font-bold capitalize text-slate-900">{card.value}</p><p className="mt-2 text-xs text-slate-500">{card.note}</p></div>)}
      </div>
      <div className="grid gap-4 lg:grid-cols-3">{runtime.jobs.map(job => <article className={panel} key={job.name}>
        <div className="flex items-center justify-between gap-3"><h3 className="font-bold text-slate-900">{job.label}</h3><span className="rounded-full bg-orange-50 px-3 py-1 text-xs font-semibold text-orange-900">{job.status.replace(/_/g, " ")}</span></div>
        <dl className="mt-4 space-y-3 text-sm"><div><dt className="text-slate-500">Last finished</dt><dd>{stamp(job.last_finished_at)}</dd></div><div><dt className="text-slate-500">Next scheduled run</dt><dd>{job.status === "dead" ? "Waiting for retry" : stamp(job.next_run_at)}</dd></div><div><dt className="text-slate-500">Consecutive attempts</dt><dd>{job.attempts} / {job.max_attempts}</dd></div></dl>
        {job.lease_expired && <p className="mt-3 text-sm text-amber-800">Interrupted worker. Recovery will occur on the next available worker pass.</p>}
        {job.last_error && <p className="mt-3 text-sm text-red-700">Failure: {job.last_error}</p>}
        {["retry", "dead"].includes(job.status) && <button className={action + " mt-4"} disabled={pending !== null} onClick={() => void retry(job.name)}><RefreshCw size={14} />{pending === job.name ? "Queuing…" : "Queue safe retry"}</button>}
      </article>)}</div>
      <div className={panel}><h3 className="font-bold">Delivery & processing queues</h3><p className="mt-1 text-sm text-slate-500">Recorded states across the platform. An empty queue is not proof that a provider is connected.</p>
        <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-5">{Object.entries(runtime.queues ?? {}).map(([name, counts]) => <article key={name} className="rounded-xl bg-[var(--wb,#fff7ed)] p-4"><h4 className="font-semibold capitalize">{name.replace(/_/g, " ")}</h4>{Object.keys(counts).length ? <dl className="mt-3 space-y-2">{Object.entries(counts).map(([state, count]) => <div key={state} className="flex justify-between gap-2 text-sm"><dt className="capitalize text-slate-600">{state.replace(/_/g, " ")}</dt><dd className="font-bold">{count}</dd></div>)}</dl> : <p className="mt-3 text-sm text-slate-500">No records yet</p>}</article>)}</div>
      </div>
      <div className={panel}><h3 className="font-bold">AI provider evidence</h3><p className="mt-1 text-sm text-slate-500">Last recorded tests and failures, not a live quota guarantee. Keys stay in the server-side vault.</p>
        {!runtime.providers?.length ? <p className="mt-4 text-sm text-slate-600">No active AI providers configured.</p> : <div className="mt-4 grid gap-3 md:grid-cols-2">{runtime.providers.map(provider => <article key={`${provider.provider}:${provider.label}`} className="rounded-xl border border-orange-100 p-4"><h4 className="font-semibold">{provider.label} · {provider.provider}</h4><p className="mt-2 text-sm">{provider.status || "Untested"} · {provider.failures} recorded failures</p><p className="mt-1 text-xs text-slate-500">Last tested: {stamp(provider.last_tested_at)}</p></article>)}</div>}
      </div>
      <div className={panel}><h3 className="font-bold">Connected service controls</h3><div className="mt-4 flex flex-wrap gap-3">{[
        ["/admin/operations?view=health", "Recordings & storage"], ["/admin/operations?view=readiness", "Provider readiness"],
        ["/admin/ai-providers", "AI provider keys & usage"], ["/admin/operations?view=revenue", "Payment reconciliation"],
        ["/admin/operations?view=utporul", "Coding assessments"], ["/admin/operations?view=seyappaduporul", "Communication delivery"],
      ].map(([to, label]) => <Link className={action} to={to} key={to}>{label}<ArrowUpRight size={14} /></Link>)}</div></div>
      <div className={panel}><h3 className="font-bold">Execution history</h3><p className="mt-1 text-sm text-slate-500">Most recent 100 events. Completed runs and operator retries retain their evidence.</p>
        {!runtime.runs.length ? <p className="mt-5 text-sm text-slate-600">No executions recorded. Start the maintenance worker to collect live evidence.</p> : <div className="mt-4 overflow-x-auto"><table className="w-full text-left text-sm"><thead><tr className="border-b text-slate-500"><th className="p-3">Job</th><th className="p-3">State</th><th className="p-3">Attempt</th><th className="p-3">Started</th><th className="p-3">Error</th></tr></thead><tbody>{runtime.runs.map(run => <tr className="border-b border-orange-50" key={run.id}><td className="p-3">{runtime.jobs.find(j => j.name === run.job_name)?.label ?? run.job_name}</td><td className="p-3">{run.status.replace(/_/g, " ")}</td><td className="p-3">{run.attempt}</td><td className="p-3">{stamp(run.started_at)}</td><td className="p-3">{run.error_code || "—"}</td></tr>)}</tbody></table></div>}
      </div>
    </>}
  </section>;
}
