import { FormEvent, useCallback, useEffect, useState } from "react";
import { BadgeIndianRupee, FileCheck2, RefreshCw, WalletCards } from "lucide-react";

import {
  platformAPI,
  type CommercialContract,
  type CommercialInvoice,
  type CommercialOffer,
  type PlatformTenantSummary,
  type RevenueLedgerEvent,
  type VerticalKey,
} from "@/api/platform";
import { plannerError } from "@/api/planner";
import { BUSINESS_VERTICALS } from "@/config/businessVerticals";
import { businessDate } from "@/utils/businessTime";

const box = "rounded-xl border bg-white p-5";
const input = "rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm";
const button = input + " font-medium disabled:opacity-40";

function money(amount: number, currency: string) {
  return new Intl.NumberFormat("en-IN", { style: "currency", currency }).format(amount);
}

export function CommercialControlPlane() {
  const [tenants, setTenants] = useState<PlatformTenantSummary[]>([]);
  const [offers, setOffers] = useState<CommercialOffer[]>([]);
  const [ledger, setLedger] = useState<RevenueLedgerEvent[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [vertical, setVertical] = useState<VerticalKey>("meiporul");
  const [sku, setSku] = useState("");
  const [name, setName] = useState("");
  const [amount, setAmount] = useState("");
  const [billingModel, setBillingModel] = useState<CommercialOffer["billing_model"]>("one_time");
  const [stream, setStream] = useState(BUSINESS_VERTICALS.meiporul.revenueModels[0].key);
  const [tenantId, setTenantId] = useState("");
  const [offerId, setOfferId] = useState("");
  const [contract, setContract] = useState<CommercialContract | null>(null);
  const [invoice, setInvoice] = useState<CommercialInvoice | null>(null);
  const [tax, setTax] = useState("0");
  const [dueOn, setDueOn] = useState(businessDate(7));

  const load = useCallback(async () => {
    setBusy(true);
    try {
      const end = new Date();
      const start = new Date(end.getTime() - 30 * 24 * 60 * 60 * 1000);
      const [tenantRows, offerRows, ledgerRows] = await Promise.all([
        platformAPI.tenants(),
        platformAPI.offers(),
        platformAPI.ledger(start.toISOString(), end.toISOString()),
      ]);
      setTenants(tenantRows.filter((row) => row.kind !== "platform"));
      setOffers(offerRows);
      setTenantId((current) => current || String(tenantRows.find((row) => row.kind !== "platform")?.id ?? ""));
      setOfferId((current) => current || String(offerRows[0]?.id ?? ""));
      setLedger(ledgerRows);
      setError("");
    } catch (cause) {
      setError(plannerError(cause));
    } finally {
      setBusy(false);
    }
  }, []);

  useEffect(() => void load(), [load]);

  const chooseVertical = (next: VerticalKey) => {
    setVertical(next);
    setStream(BUSINESS_VERTICALS[next].revenueModels[0].key);
  };

  const createOffer = async (event: FormEvent) => {
    event.preventDefault();
    setBusy(true);
    try {
      const created = await platformAPI.createOffer({
        sku,
        business_vertical: vertical,
        revenue_stream: stream,
        name,
        billing_model: billingModel,
        currency: "INR",
        unit_amount: amount,
        entitlement_grants: [],
      });
      setOffers((rows) => [...rows, created].sort((a, b) => a.sku.localeCompare(b.sku)));
      setOfferId(String(created.id));
      setSku("");
      setName("");
      setAmount("");
      setError("");
    } catch (cause) {
      setError(plannerError(cause));
    } finally {
      setBusy(false);
    }
  };

  const createContract = async () => {
    if (!tenantId || !offerId) return;
    setBusy(true);
    try {
      const offer = offers.find((row) => row.id === Number(offerId));
      const created = await platformAPI.createContract({
        tenant_id: Number(tenantId),
        offer_id: Number(offerId),
        starts_on: businessDate(),
        billing_interval: offer?.billing_model === "subscription" ? "annual" : null,
      });
      setContract(created);
      setInvoice(null);
      setError("");
    } catch (cause) {
      setError(plannerError(cause));
    } finally {
      setBusy(false);
    }
  };

  const createInvoice = async () => {
    if (!contract) return;
    setBusy(true);
    try {
      const created = await platformAPI.createInvoice({
        contract_id: contract.id,
        tax_amount: tax || "0",
        due_on: dueOn,
      });
      setInvoice(created);
      setError("");
    } catch (cause) {
      setError(plannerError(cause));
    } finally {
      setBusy(false);
    }
  };

  const recordPayment = async () => {
    if (!invoice) return;
    setBusy(true);
    try {
      await platformAPI.recordPayment(invoice.id, {
        source_event_key: `manual:${invoice.id}:${crypto.randomUUID()}`,
        payment_reference: `MANUAL-${invoice.invoice_number.replace(/\//g, "-")}`,
        occurred_at: new Date().toISOString(),
        reason: "Settlement verified by Sasha platform operations",
      });
      setInvoice({ ...invoice, status: "paid" });
      await load();
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
          <h2 className="text-xl font-bold">Commercial control plane</h2>
          <p className="mt-1 text-sm text-slate-600">Operate every business model through one catalog, contract, invoice, and immutable revenue-event workflow.</p>
        </div>
        <button className={button + " flex items-center gap-2"} disabled={busy} onClick={load}><RefreshCw size={15} /> Refresh</button>
      </div>
      {error && <p role="alert" className="rounded-lg bg-rose-50 p-4 text-rose-800">{error}</p>}
      <div className="grid items-start gap-5 xl:grid-cols-2">
        <form className={box + " space-y-4"} onSubmit={createOffer}>
          <div className="flex items-center gap-2"><WalletCards size={19} className="text-orange-700" /><h3 className="font-semibold">Create a commercial offer</h3></div>
          <div className="grid gap-3 sm:grid-cols-2">
            <label className="text-sm">Pillar<select className={input + " mt-1 w-full"} value={vertical} onChange={(event) => chooseVertical(event.target.value as VerticalKey)}>{Object.values(BUSINESS_VERTICALS).map((row) => <option value={row.key} key={row.key}>{row.label}</option>)}</select></label>
            <label className="text-sm">Revenue stream<select className={input + " mt-1 w-full"} value={stream} onChange={(event) => setStream(event.target.value)}>{BUSINESS_VERTICALS[vertical].revenueModels.map((row) => <option value={row.key} key={row.key}>{row.label}</option>)}</select></label>
            <label className="text-sm">SKU<input required className={input + " mt-1 w-full"} value={sku} onChange={(event) => setSku(event.target.value)} placeholder="MA1-LAB-40" /></label>
            <label className="text-sm">Offer name<input required className={input + " mt-1 w-full"} value={name} onChange={(event) => setName(event.target.value)} /></label>
            <label className="text-sm">Billing model<select className={input + " mt-1 w-full"} value={billingModel} onChange={(event) => setBillingModel(event.target.value as CommercialOffer["billing_model"])}><option value="one_time">One time</option><option value="subscription">Subscription</option><option value="usage">Usage</option><option value="royalty">Royalty</option><option value="milestone">Milestone</option></select></label>
            <label className="text-sm">Unit amount (INR)<input required min="0" step="0.01" type="number" className={input + " mt-1 w-full"} value={amount} onChange={(event) => setAmount(event.target.value)} /></label>
          </div>
          <button className={button} disabled={busy}>Create offer</button>
        </form>

        <section className={box + " space-y-4"}>
          <div className="flex items-center gap-2"><FileCheck2 size={19} className="text-indigo-600" /><h3 className="font-semibold">Contract → invoice → collection</h3></div>
          <div className="grid gap-3 sm:grid-cols-2">
            <label className="text-sm">Customer<select className={input + " mt-1 w-full"} value={tenantId} onChange={(event) => { setTenantId(event.target.value); setContract(null); setInvoice(null); }}><option value="">Choose tenant</option>{tenants.map((row) => <option key={row.id} value={row.id}>{row.name}</option>)}</select></label>
            <label className="text-sm">Offer<select className={input + " mt-1 w-full"} value={offerId} onChange={(event) => { setOfferId(event.target.value); setContract(null); setInvoice(null); }}><option value="">Choose offer</option>{offers.map((row) => <option key={row.id} value={row.id}>{row.sku} · {row.name}</option>)}</select></label>
          </div>
          <button className={button} disabled={busy || !tenantId || !offerId} onClick={createContract}>{contract ? `Contract #${contract.id} active` : "Create contract"}</button>
          {contract && (
            <div className="grid gap-3 rounded-lg bg-slate-50 p-4 sm:grid-cols-[1fr_1fr_auto]">
              <label className="text-sm">Tax amount<input min="0" step="0.01" type="number" className={input + " mt-1 w-full"} value={tax} onChange={(event) => setTax(event.target.value)} /></label>
              <label className="text-sm">Due date<input type="date" className={input + " mt-1 w-full"} value={dueOn} onChange={(event) => setDueOn(event.target.value)} /></label>
              <button className={button + " self-end"} disabled={busy} onClick={createInvoice}>Issue invoice</button>
            </div>
          )}
          {invoice && (
            <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-4">
              <p className="font-semibold">{invoice.invoice_number}</p>
              <p className="mt-1 text-sm">{money(invoice.total_amount, invoice.currency)} · {invoice.status}</p>
              {invoice.status !== "paid" && <button className={button + " mt-3 bg-white"} disabled={busy} onClick={recordPayment}>Record verified settlement</button>}
            </div>
          )}
        </section>
      </div>

      <section className={box}>
        <div className="flex items-center gap-2"><BadgeIndianRupee size={19} /><h3 className="font-semibold">Revenue ledger · last 30 days</h3></div>
        <div className="mt-4 overflow-x-auto">
          <table className="w-full min-w-[720px] text-left text-sm">
            <thead className="border-b text-xs uppercase tracking-wide text-slate-500"><tr><th className="py-2">When</th><th>Pillar</th><th>Stream</th><th>Event</th><th>Gross</th><th>Net</th><th>Source key</th></tr></thead>
            <tbody className="divide-y">{ledger.map((row) => <tr key={row.id}><td className="py-3">{new Date(row.occurred_at).toLocaleString()}</td><td>{BUSINESS_VERTICALS[row.business_vertical].label}</td><td>{row.revenue_stream.replace(/_/g, " ")}</td><td>{row.event_type}</td><td>{money(row.gross_amount, row.currency)}</td><td>{money(row.net_amount, row.currency)}</td><td className="max-w-48 truncate text-xs text-slate-500">{row.source_event_key}</td></tr>)}</tbody>
          </table>
          {!ledger.length && <p className="py-6 text-sm text-slate-500">No commercial ledger events in this period.</p>}
        </div>
      </section>
    </div>
  );
}
