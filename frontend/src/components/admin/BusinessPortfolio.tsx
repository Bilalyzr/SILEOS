import { useCallback, useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { AlertTriangle, ArrowRight, RefreshCw, ShieldCheck } from "lucide-react";
import {
  operationsAPI,
  type BusinessPortfolioReport,
  type PortfolioCurrency,
} from "@/api/operations";
import { plannerError } from "@/api/planner";
import {
  BUSINESS_VERTICALS,
  type BusinessVerticalKey,
} from "@/config/businessVerticals";
import { businessDate } from "@/utils/businessTime";

const input = "rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm";
const box = "rounded-xl border bg-white p-5";
const today = () => businessDate();
const thirtyDaysAgo = () => businessDate(-30);

function money(amount: number, currency: string) {
  try {
    return new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency,
      maximumFractionDigits: 2,
    }).format(amount);
  } catch {
    return `${currency} ${amount.toFixed(2)}`;
  }
}

function CurrencyRows({ rows }: { rows: PortfolioCurrency[] }) {
  if (!rows.length) {
    return <p className="text-sm text-slate-500">No recorded revenue in this window.</p>;
  }
  return (
    <div className="space-y-2">
      {rows.map((row) => (
        <div key={row.currency} className="flex items-baseline justify-between gap-4">
          <span className="text-sm text-slate-600">{row.currency} net cash</span>
          <strong>{money(row.net_cash, row.currency)}</strong>
        </div>
      ))}
    </div>
  );
}

export function BusinessPortfolio({ focus }: { focus?: BusinessVerticalKey }) {
  const [start, setStart] = useState(thirtyDaysAgo);
  const [end, setEnd] = useState(today);
  const [report, setReport] = useState<BusinessPortfolioReport | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const request = useRef(0);

  const load = useCallback(async () => {
    const id = ++request.current;
    setBusy(true);
    setError("");
    try {
      const result = await operationsAPI.portfolio(start, end);
      if (id === request.current) setReport(result);
    } catch (cause) {
      if (id === request.current) setError(plannerError(cause));
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

  const verticals = focus
    ? report?.verticals.filter((vertical) => vertical.key === focus)
    : report?.verticals;

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-end gap-3">
        <label className="text-sm">
          From <input aria-label="Portfolio from" type="date" className={input} value={start} onChange={(event) => setStart(event.target.value)} />
        </label>
        <label className="text-sm">
          To <input aria-label="Portfolio to" type="date" className={input} value={end} onChange={(event) => setEnd(event.target.value)} />
        </label>
        <button className={input + " flex items-center gap-2 font-medium disabled:opacity-40"} disabled={busy} onClick={load}>
          <RefreshCw size={15} /> Refresh portfolio
        </button>
      </div>

      {error && <p role="alert" className="rounded-lg bg-rose-50 p-4 text-rose-800">{error}</p>}
      {busy && !report && <p role="status">Loading the consolidated business portfolio…</p>}

      {!focus && report?.resilience.length ? (
        <section className={box}>
          <div className="flex items-start gap-3">
            <ShieldCheck className="mt-0.5 text-indigo-600" size={22} />
            <div className="w-full">
              <h2 className="font-semibold">Pillar revenue concentration</h2>
              <p className="mt-1 text-sm text-slate-600">A collections-mix signal only: it shows whether one vertical carries more than 60% of positive net cash. It does not include costs, liabilities, or runway.</p>
              <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
                {report.resilience.map((row) => (
                  <div key={row.currency} className="rounded-lg bg-slate-50 p-4">
                    <p className="text-sm font-semibold">{row.currency} · {row.status.replace("_", " ")}</p>
                    <p className="mt-2 text-sm text-slate-600">Leader: {row.leader ? BUSINESS_VERTICALS[row.leader].label : "No revenue yet"}{row.largest_share_percent == null ? "" : ` (${row.largest_share_percent}%)`}</p>
                    <p className="mt-1 text-sm">Remaining: {money(row.remaining_if_leader_pauses, row.currency)}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </section>
      ) : null}

      {report && report.unallocated.payment_count > 0 && !focus ? (
        <section className="rounded-xl border border-amber-300 bg-amber-50 p-5 text-amber-950">
          <div className="flex gap-3">
            <AlertTriangle className="mt-0.5 shrink-0" size={20} />
            <div>
              <h2 className="font-semibold">{report.unallocated.payment_count} payment{report.unallocated.payment_count === 1 ? "" : "s"} need a pillar classification</h2>
              <p className="mt-1 text-sm">They stay visible here instead of being silently assigned to the wrong business. Add a source adapter when a new revenue flow is introduced.</p>
              <div className="mt-3"><CurrencyRows rows={report.unallocated.currencies} /></div>
            </div>
          </div>
        </section>
      ) : null}

      {report && report.unallocated.course_count > 0 && !focus ? (
        <section className="rounded-xl border border-amber-300 bg-amber-50 p-5 text-amber-950">
          <div className="flex gap-3">
            <AlertTriangle className="mt-0.5 shrink-0" size={20} />
            <div>
              <h2 className="font-semibold">{report.unallocated.course_count} course{report.unallocated.course_count === 1 ? "" : "s"} need a pillar classification</h2>
              <p className="mt-1 text-sm">These courses stay visible here until an administrator assigns Meiporul, Seyappaduporul, or Utporul.</p>
              <Link to="/admin/courses" className="mt-3 inline-flex items-center gap-1 text-sm font-semibold underline">Classify courses <ArrowRight size={14} /></Link>
            </div>
          </div>
        </section>
      ) : null}

      <div className="grid items-start gap-5 xl:grid-cols-3">
        {verticals?.map((vertical) => {
          const config = BUSINESS_VERTICALS[vertical.key];
          return (
            <section key={vertical.key} className={box + " space-y-5"}>
              <div>
                <p className="text-xs font-semibold uppercase tracking-widest text-slate-500">{vertical.code} · {vertical.tamil}</p>
                <h2 className="mt-2 text-2xl font-bold">{vertical.label}</h2>
                <p className="mt-2 text-sm leading-6 text-slate-600">{vertical.mission}</p>
                <Link to={config.route} className="mt-3 inline-flex items-center gap-1 text-sm font-semibold text-orange-700">Open public pillar <ArrowRight size={14} /></Link>
              </div>

              <div className="rounded-lg bg-slate-50 p-4">
                <h3 className="mb-3 text-sm font-semibold">Revenue</h3>
                <CurrencyRows rows={vertical.revenue.currencies} />
              </div>

              <div>
                <h3 className="text-sm font-semibold">Operational inventory</h3>
                <div className="mt-3 grid grid-cols-2 gap-2">
                  {vertical.inventory.map((item) => (
                    <div key={item.key} className="rounded-lg border p-3">
                      <p className="text-xl font-bold">{item.value.toLocaleString("en-IN")}</p>
                      <p className="mt-1 text-xs text-slate-500">{item.label}</p>
                    </div>
                  ))}
                </div>
              </div>

              <div>
                <h3 className="text-sm font-semibold">Revenue streams</h3>
                <div className="mt-2 divide-y">
                  {vertical.revenue.streams.map((stream) => (
                    <div key={stream.key} className="py-3">
                      <div className="flex items-center justify-between gap-3">
                        <span className="text-sm">{stream.label}</span>
                        <span className="rounded-full bg-slate-100 px-2 py-1 text-[11px] font-semibold text-slate-600">{stream.currencies.length ? "Reporting" : "Planned"}</span>
                      </div>
                      {stream.currencies.map((row) => <p key={row.currency} className="mt-1 text-xs text-slate-500">{money(row.net_cash, row.currency)} net</p>)}
                    </div>
                  ))}
                </div>
              </div>

              <div>
                <h3 className="text-sm font-semibold">Control workspaces</h3>
                <div className="mt-3 flex flex-wrap gap-2">
                  {config.workspaces.filter((workspace) => workspace.state === "live").map((workspace) => (
                    <Link key={workspace.title} to={workspace.adminHref ?? workspace.href} className="rounded-full border px-3 py-1.5 text-xs font-medium hover:bg-slate-50">{workspace.title}</Link>
                  ))}
                </div>
              </div>
            </section>
          );
        })}
      </div>

      {report && <p className="text-xs text-slate-500">{report.reporting_contract.rule} Sources: {report.reporting_contract.operating_sources.join(", ")}.</p>}
    </div>
  );
}

export default BusinessPortfolio;
