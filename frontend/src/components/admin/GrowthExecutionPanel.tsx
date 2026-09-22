import { useEffect, useState } from 'react';
import { growthAPI } from '@/api/growth';
import { plannerError } from '@/api/planner';

interface ExecutionData {
  leads: { id: number; name: string; company: string; version: number }[];
  unified_cash: { currency: string; captured: number; refunded: number; net_cash: number }[];
  recommendations: { id: number; tenant_id: number; status: string }[];
  analytics: { campaigns: { source: string; campaign: string; net_revenue: number; spend: number; new_customers: number; cac: number | null }[] };
}
export function GrowthExecutionPanel() {
  const [data, setData] = useState<ExecutionData | null>(null); const [error, setError] = useState(''); const [message, setMessage] = useState(''); const [busy, setBusy] = useState(false);
  const load = async () => setData(await growthAPI.get<ExecutionData>('/admin'));
  useEffect(() => { load().catch(e => setError(plannerError(e))); }, []);
  return <section className="space-y-4 rounded-2xl border border-orange-100 bg-white p-5"><h3 className="text-xl font-bold">Sales execution & unified cash</h3>
    {error && <p role="alert" className="text-red-700">{error}</p>}{message && <p role="status" className="rounded-xl bg-orange-50 p-3">{message}</p>}
    <p className="text-sm text-slate-500">90-day cash view across existing commerce, tuition, vouchers, commercial invoices and recorded campus charges. Cash is not profit. Historical campus events without monetary evidence require reconciliation.</p>
    {data?.unified_cash.map(c => <p key={c.currency} className="rounded-xl bg-orange-50 p-4 font-semibold">{c.currency} {c.net_cash.toLocaleString('en-IN')} net cash · {c.captured.toLocaleString('en-IN')} captured · {c.refunded.toLocaleString('en-IN')} refunded</p>)}
    <h4 className="font-semibold">Attributed commercial campaigns</h4><div className="overflow-x-auto"><table className="w-full text-left text-sm"><thead><tr>{['Source / campaign', 'Net revenue', 'Spend', 'New customers', 'CAC'].map(h => <th key={h} className="p-2">{h}</th>)}</tr></thead><tbody>{data?.analytics.campaigns.map((c, i) => <tr key={i} className="border-t"><td className="p-2">{c.source} / {c.campaign || '—'}</td><td className="p-2">₹{c.net_revenue}</td><td className="p-2">₹{c.spend}</td><td className="p-2">{c.new_customers}</td><td className="p-2">{c.cac == null ? 'Unknown' : `₹${c.cac.toFixed(2)}`}</td></tr>)}</tbody></table></div>
    <h4 className="font-semibold">Connect a lead to its customer workspace</h4>
    <form className="flex flex-wrap items-end gap-3" onSubmit={async e => {
      e.preventDefault(); const f = new FormData(e.currentTarget); const lead = data?.leads?.find(l => l.id === Number(f.get('lead_id'))); if (!lead) return;
      setBusy(true); setError(''); try { await growthAPI.put(`/leads/${lead.id}/workspace`, { tenant_id: Number(f.get('tenant_id')), version: lead.version }); await load(); setMessage('Customer workspace linked. You can now attach its contract in Sales pipeline.'); } catch (err) { setError(plannerError(err)); } finally { setBusy(false); }
    }}><label className="grid gap-1 text-sm">Lead<select name="lead_id" required className="rounded-xl border p-3">{data?.leads?.map(l => <option key={l.id} value={l.id}>#{l.id} · {l.company || l.name}</option>)}</select></label><label className="grid gap-1 text-sm">Customer workspace ID<input name="tenant_id" type="number" min="1" required className="rounded-xl border p-3" /></label><button className="rounded-xl border border-orange-200 px-4 py-3 text-sm font-semibold text-orange-800" disabled={busy}>Link workspace</button></form>
    <h4 className="font-semibold">Publish an approved offer</h4><p className="text-sm text-slate-500">Publishing makes the offer available in the customer's Services & billing page. In-app notifications go only to finance members who explicitly opted in. No email, WhatsApp or charge is triggered.</p>
    <form className="flex flex-wrap items-end gap-3" onSubmit={async e => { e.preventDefault(); const f = new FormData(e.currentTarget); setBusy(true); setError(''); try { const result = await growthAPI.post(`/recommendations/${f.get('id')}/publish`); setMessage(`Published. ${result.notified} opted-in member(s) notified.`); await load(); } catch (err) { setError(plannerError(err)); } finally { setBusy(false); } }}><label className="grid gap-1 text-sm">Approved recommendation<select name="id" required className="rounded-xl border p-3">{data?.recommendations.filter(r => ['approved', 'published'].includes(r.status)).map(r => <option key={r.id} value={r.id}>#{r.id} · Workspace {r.tenant_id} · {r.status}</option>)}</select></label><label className="text-sm"><input type="checkbox" required className="mr-2 accent-orange-500" />I reviewed the customer and offer terms.</label><button disabled={busy} className="rounded-xl bg-gradient-to-r from-orange-600 to-amber-500 px-4 py-3 text-sm font-semibold text-white disabled:opacity-50">Publish reviewed offer</button></form>
  </section>;
}
