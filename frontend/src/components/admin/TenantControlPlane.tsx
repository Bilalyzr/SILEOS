import { useCallback, useEffect, useState } from "react";
import { Building2, Globe2, RefreshCw, ShieldCheck, Users } from "lucide-react";

import {
  platformAPI,
  type PlatformTenantDetail,
  type PlatformTenantSummary,
  type TenantStatus,
  type VerticalKey,
} from "@/api/platform";
import { plannerError } from "@/api/planner";
import { BUSINESS_VERTICALS } from "@/config/businessVerticals";

const box = "rounded-xl border bg-white p-5";
const input = "rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm";
const button = input + " font-medium disabled:opacity-40";

export function TenantControlPlane() {
  const [tenants, setTenants] = useState<PlatformTenantSummary[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [detail, setDetail] = useState<PlatformTenantDetail | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [reason, setReason] = useState("Approved by Sasha platform operations");
  const [status, setStatus] = useState<TenantStatus>("active");
  const [hostname, setHostname] = useState("");
  const [domainVertical, setDomainVertical] = useState<VerticalKey | "">("");

  const load = useCallback(async () => {
    setBusy(true);
    try {
      const rows = await platformAPI.tenants();
      setTenants(rows);
      setSelectedId((current) => current ?? rows[0]?.id ?? null);
      setError("");
    } catch (cause) {
      setError(plannerError(cause));
    } finally {
      setBusy(false);
    }
  }, []);

  const loadDetail = useCallback(async (tenantId: number) => {
    setBusy(true);
    try {
      const row = await platformAPI.tenant(tenantId);
      setDetail(row);
      setStatus(row.status);
      setError("");
    } catch (cause) {
      setError(plannerError(cause));
    } finally {
      setBusy(false);
    }
  }, []);

  useEffect(() => void load(), [load]);
  useEffect(() => {
    if (selectedId) void loadDetail(selectedId);
  }, [loadDetail, selectedId]);

  const changeStatus = async () => {
    if (!detail) return;
    setBusy(true);
    try {
      await platformAPI.setTenantStatus(detail.id, status, reason);
      await Promise.all([load(), loadDetail(detail.id)]);
    } catch (cause) {
      setError(plannerError(cause));
    } finally {
      setBusy(false);
    }
  };

  const toggleEntitlement = async (
    vertical: VerticalKey,
    featureKey: string,
    enabled: boolean,
    quota: Record<string, unknown>,
  ) => {
    if (!detail) return;
    setBusy(true);
    try {
      await platformAPI.setEntitlement(
        detail.id,
        vertical,
        featureKey,
        enabled,
        quota,
        reason,
      );
      await loadDetail(detail.id);
    } catch (cause) {
      setError(plannerError(cause));
    } finally {
      setBusy(false);
    }
  };

  const addDomain = async () => {
    if (!detail || !hostname.trim()) return;
    setBusy(true);
    try {
      await platformAPI.addDomain(
        detail.id,
        hostname,
        domainVertical || null,
      );
      setHostname("");
      await loadDetail(detail.id);
    } catch (cause) {
      setError(plannerError(cause));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-xl font-bold">Tenant control plane</h2>
          <p className="mt-1 text-sm text-slate-600">
            Customers are isolated here; each can activate capabilities from any of the three business pillars.
          </p>
        </div>
        <button className={button + " flex items-center gap-2"} disabled={busy} onClick={load}>
          <RefreshCw size={15} /> Refresh
        </button>
      </div>
      {error && <p role="alert" className="rounded-lg bg-rose-50 p-4 text-rose-800">{error}</p>}
      <div className="grid items-start gap-5 xl:grid-cols-[320px_minmax(0,1fr)]">
        <section className={box}>
          <p className="text-xs font-semibold uppercase tracking-widest text-slate-500">Customers</p>
          <div className="mt-3 space-y-2">
            {tenants.map((tenant) => (
              <button
                key={tenant.id}
                className={`w-full rounded-lg border p-3 text-left ${selectedId === tenant.id ? "border-orange-400 bg-orange-50" : "hover:bg-slate-50"}`}
                onClick={() => setSelectedId(tenant.id)}
              >
                <span className="flex items-center justify-between gap-2">
                  <strong className="text-sm">{tenant.name}</strong>
                  <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[11px]">{tenant.status}</span>
                </span>
                <span className="mt-1 block text-xs text-slate-500">{tenant.kind} · {tenant.counts.members} members</span>
              </button>
            ))}
            {!tenants.length && !busy && <p className="text-sm text-slate-500">No tenants have been provisioned.</p>}
          </div>
        </section>

        {detail ? (
          <div className="space-y-5">
            <section className={box}>
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-widest text-orange-700">{detail.kind} · {detail.slug}</p>
                  <h3 className="mt-2 text-2xl font-bold">{detail.name}</h3>
                  <p className="mt-1 text-sm text-slate-500">Tenant #{detail.id} · {detail.timezone} · data region {detail.data_region.toUpperCase()}</p>
                </div>
                <div className="flex flex-wrap gap-2">
                  <select aria-label="Tenant status" className={input} value={status} onChange={(event) => setStatus(event.target.value as TenantStatus)}>
                    <option value="trial">Trial</option>
                    <option value="active">Active</option>
                    <option value="suspended">Suspended</option>
                    <option value="archived">Archived</option>
                  </select>
                  <button className={button} disabled={busy || status === detail.status || reason.trim().length < 3} onClick={changeStatus}>Apply status</button>
                </div>
              </div>
              <label className="mt-4 block text-sm">
                Audit reason
                <input className={input + " mt-1 w-full"} value={reason} onChange={(event) => setReason(event.target.value)} />
              </label>
            </section>

            <section className={box}>
              <div className="flex items-center gap-2"><ShieldCheck size={19} className="text-indigo-600" /><h3 className="font-semibold">Vertical entitlements</h3></div>
              <div className="mt-4 grid gap-3 lg:grid-cols-3">
                {(["meiporul", "seyappaduporul", "utporul"] as VerticalKey[]).map((vertical) => {
                  const rows = detail.entitlements.filter((item) => item.vertical === vertical);
                  return (
                    <div key={vertical} className="rounded-lg border p-4">
                      <p className="font-semibold">{BUSINESS_VERTICALS[vertical].label}</p>
                      <div className="mt-3 space-y-2">
                        {rows.map((row) => (
                          <div key={row.id} className="flex items-center justify-between gap-3 text-sm">
                            <span>{row.feature_key.replace(/_/g, " ")}</span>
                            <button
                              className={`rounded-full px-2 py-1 text-xs font-semibold ${row.enabled ? "bg-emerald-100 text-emerald-800" : "bg-slate-100 text-slate-600"}`}
                              disabled={busy || reason.trim().length < 3}
                              onClick={() => toggleEntitlement(vertical, row.feature_key, !row.enabled, row.quota)}
                            >
                              {row.enabled ? "Enabled" : "Disabled"}
                            </button>
                          </div>
                        ))}
                      </div>
                    </div>
                  );
                })}
              </div>
            </section>

            <div className="grid gap-5 lg:grid-cols-2">
              <section className={box}>
                <div className="flex items-center gap-2"><Users size={18} /><h3 className="font-semibold">Members</h3></div>
                <div className="mt-3 divide-y">
                  {detail.members.map((member) => (
                    <div key={member.id} className="flex justify-between gap-3 py-2 text-sm">
                      <span>User #{member.user_id}</span><span className="text-slate-500">{member.role} · {member.status}</span>
                    </div>
                  ))}
                </div>
              </section>
              <section className={box}>
                <div className="flex items-center gap-2"><Globe2 size={18} /><h3 className="font-semibold">Domains</h3></div>
                <div className="mt-3 space-y-2">
                  {detail.domains.map((domain) => <p key={domain.id} className="text-sm">{domain.hostname} <span className="text-slate-500">· {domain.vertical ?? "shared"} · {domain.status}</span></p>)}
                </div>
                <div className="mt-4 grid gap-2 sm:grid-cols-[1fr_180px_auto]">
                  <input aria-label="Domain hostname" className={input} placeholder="learning.customer.org" value={hostname} onChange={(event) => setHostname(event.target.value)} />
                  <select aria-label="Domain vertical" className={input} value={domainVertical} onChange={(event) => setDomainVertical(event.target.value as VerticalKey | "")}>
                    <option value="">Shared</option>
                    <option value="meiporul">Meiporul</option>
                    <option value="seyappaduporul">Seyappaduporul</option>
                    <option value="utporul">Utporul</option>
                  </select>
                  <button className={button} disabled={busy || !hostname.trim()} onClick={addDomain}>Request</button>
                </div>
              </section>
            </div>
          </div>
        ) : (
          <section className={box}><Building2 className="text-slate-400" /><p className="mt-3 text-sm text-slate-500">Select a customer to inspect its platform boundary.</p></section>
        )}
      </div>
    </div>
  );
}
