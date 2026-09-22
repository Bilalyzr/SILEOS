import { useCallback, useEffect, useState } from 'react'
import { Box, CheckCircle2, Cpu, MapPin, Plus, RefreshCw, ShieldCheck, Ticket } from 'lucide-react'
import { meiporulOperationsAPI, type ImmersiveDevice, type ImmersiveSite, type ImmersiveSiteSummary } from '@/api/meiporul-operations'
import { platformAPI, type PlatformTenantSummary } from '@/api/platform'
import { plannerError } from '@/api/planner'

const box = 'rounded-2xl border border-slate-200 bg-white p-5'
const input = 'mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm outline-none focus:border-orange-500'
const button = 'rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-medium disabled:opacity-40'
type DeviceDraft = { asset_tag: string; serial_number: string; device_type: string; vendor: string; model: string; assigned_room: string }
type TicketDraft = { category: string; priority: string; subject: string; description: string }

export function MeiporulOperationsPanel() {
  const [tenants, setTenants] = useState<PlatformTenantSummary[]>([])
  const [tenantId, setTenantId] = useState(0)
  const [sites, setSites] = useState<ImmersiveSiteSummary[]>([])
  const [site, setSite] = useState<ImmersiveSite | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [showNewSite, setShowNewSite] = useState(false)
  const [siteDraft, setSiteDraft] = useState({ code: '', name: '', city: '', room_count: 1, headset_capacity: 30 })
  const [deviceDraft, setDeviceDraft] = useState({ asset_tag: '', serial_number: '', device_type: 'headset', vendor: '', model: '', assigned_room: '' })
  const [ticketDraft, setTicketDraft] = useState({ category: 'hardware', priority: 'normal', subject: '', description: '' })

  const loadSites = useCallback(async (nextTenantId: number) => {
    if (!nextTenantId) { setSites([]); setSite(null); return }
    const rows = await meiporulOperationsAPI.sites(nextTenantId)
    setSites(rows)
    setSite((current) => current && rows.some((row) => row.id === current.id) ? current : null)
  }, [])

  useEffect(() => {
    let active = true
    Promise.all([platformAPI.tenants(), meiporulOperationsAPI.sites()]).then(([customerRows, siteRows]) => {
      if (!active) return
      setTenants(customerRows)
      setSites(siteRows)
      const initialTenant = customerRows[0]?.id || 0
      setTenantId(initialTenant)
      if (initialTenant) setSites(siteRows.filter((row) => row.tenant_id === initialTenant))
    }).catch((reason) => active && setError(plannerError(reason)))
    return () => { active = false }
  }, [])

  const run = async (action: () => Promise<unknown>, success: string, refresh = true) => {
    setBusy(true); setError(''); setMessage('')
    try {
      const result = await action()
      if (refresh) {
        await loadSites(tenantId)
        if (site) setSite(await meiporulOperationsAPI.site(site.id))
      }
      setMessage(success)
      return result
    } catch (reason) { setError(plannerError(reason)); return null }
    finally { setBusy(false) }
  }

  const selectSite = async (id: number) => {
    setBusy(true); setError('')
    try { setSite(await meiporulOperationsAPI.site(id)) }
    catch (reason) { setError(plannerError(reason)) }
    finally { setBusy(false) }
  }

  const changeTenant = async (id: number) => {
    setTenantId(id); setSite(null); setError(''); setMessage('')
    try { await loadSites(id) } catch (reason) { setError(plannerError(reason)) }
  }

  const createSite = async (event: React.FormEvent) => {
    event.preventDefault()
    const created = await run(() => meiporulOperationsAPI.createSite({
      tenant_id: tenantId, code: siteDraft.code, name: siteDraft.name,
      room_count: siteDraft.room_count, headset_capacity: siteDraft.headset_capacity,
      address: siteDraft.city ? { city: siteDraft.city } : {},
    }), 'Deployment site created with the five required go-live milestones.', false) as ImmersiveSite | null
    if (created) {
      setSite(created); setShowNewSite(false); setSiteDraft({ code: '', name: '', city: '', room_count: 1, headset_capacity: 30 }); await loadSites(tenantId)
    }
  }

  const addDevice = async (event: React.FormEvent) => {
    event.preventDefault(); if (!site) return
    const added = await run(() => meiporulOperationsAPI.addDevice(site.id, deviceDraft), 'Device added to the controlled fleet.')
    if (added) setDeviceDraft({ asset_tag: '', serial_number: '', device_type: 'headset', vendor: '', model: '', assigned_room: '' })
  }

  const createTicket = async (event: React.FormEvent) => {
    event.preventDefault(); if (!site) return
    const opened = await run(() => meiporulOperationsAPI.createTicket(site.id, ticketDraft), 'AMC service ticket opened with an SLA deadline.')
    if (opened) setTicketDraft({ category: 'hardware', priority: 'normal', subject: '', description: '' })
  }

  return <div className="space-y-5">
    <div className="flex flex-wrap items-center justify-between gap-3">
      <div><h2 className="text-xl font-bold text-slate-950">Meiporul deployment operations</h2><p className="mt-1 text-sm text-slate-600">Install, commission, monitor, and support immersive learning labs outside the course-authoring system.</p></div>
      <button className={`${button} inline-flex items-center gap-2`} disabled={busy || !tenantId} onClick={() => void loadSites(tenantId)}><RefreshCw className="h-4 w-4" />Refresh</button>
    </div>
    {error && <div role="alert" className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">{error}</div>}
    {message && <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-700">{message}</div>}

    <section className={box}>
      <div className="flex flex-wrap items-end gap-3">
        <label className="min-w-64 flex-1 text-sm font-medium">Customer tenant<select className={input} value={tenantId} onChange={(event) => void changeTenant(Number(event.target.value))}><option value={0}>Select a tenant</option>{tenants.map((tenant) => <option key={tenant.id} value={tenant.id}>{tenant.name} · {tenant.status}</option>)}</select></label>
        <button className={`${button} inline-flex items-center gap-2`} disabled={!tenantId} onClick={() => setShowNewSite((value) => !value)}><Plus className="h-4 w-4" />New deployment</button>
      </div>
      {showNewSite && <form onSubmit={(event) => void createSite(event)} className="mt-4 grid gap-3 rounded-xl bg-orange-50 p-4 md:grid-cols-5">
        <Field label="Site code" required value={siteDraft.code} onChange={(value) => setSiteDraft({ ...siteDraft, code: value })} />
        <Field label="Site name" required value={siteDraft.name} onChange={(value) => setSiteDraft({ ...siteDraft, name: value })} />
        <Field label="City" value={siteDraft.city} onChange={(value) => setSiteDraft({ ...siteDraft, city: value })} />
        <NumberField label="Rooms" min={1} value={siteDraft.room_count} onChange={(value) => setSiteDraft({ ...siteDraft, room_count: value })} />
        <NumberField label="Headset capacity" min={0} value={siteDraft.headset_capacity} onChange={(value) => setSiteDraft({ ...siteDraft, headset_capacity: value })} />
        <button disabled={busy} className="rounded-lg bg-orange-600 px-4 py-2 text-sm font-semibold text-white md:col-span-5">Create site</button>
      </form>}
    </section>

    <div className="grid items-start gap-5 xl:grid-cols-[330px_minmax(0,1fr)]">
      <aside className={box}>
        <div className="flex items-center justify-between"><h3 className="font-semibold">Deployment sites</h3><span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs">{sites.length}</span></div>
        <div className="mt-3 space-y-2">{sites.map((row) => <button key={row.id} onClick={() => void selectSite(row.id)} className={`w-full rounded-xl border p-3 text-left ${site?.id === row.id ? 'border-orange-400 bg-orange-50' : 'border-slate-200 hover:bg-slate-50'}`}><div className="flex items-center justify-between gap-2"><strong className="text-sm">{row.name}</strong><State value={row.status} /></div><p className="mt-1 text-xs text-slate-500">{row.code} · {row.counts.devices} devices · {row.counts.open_tickets} open tickets</p></button>)}{!sites.length && <p className="rounded-xl bg-slate-50 p-4 text-sm text-slate-500">No immersive deployments for this tenant.</p>}</div>
      </aside>
      {site ? <SiteDetail site={site} busy={busy} run={run} deviceDraft={deviceDraft} setDeviceDraft={setDeviceDraft} addDevice={addDevice} ticketDraft={ticketDraft} setTicketDraft={setTicketDraft} createTicket={createTicket} /> : <section className={`${box} py-14 text-center`}><MapPin className="mx-auto h-9 w-9 text-orange-500" /><h3 className="mt-3 font-semibold">Select a deployment site</h3><p className="mt-1 text-sm text-slate-500">Its fleet, readiness gates, safety checks, rollout milestones, and support tickets will appear here.</p></section>}
    </div>
  </div>
}

interface SiteDetailProps {
  site: ImmersiveSite; busy: boolean; run: (action: () => Promise<unknown>, success: string, refresh?: boolean) => Promise<unknown>
  deviceDraft: DeviceDraft; setDeviceDraft: React.Dispatch<React.SetStateAction<DeviceDraft>>; addDevice: (event: React.FormEvent) => Promise<void>
  ticketDraft: TicketDraft; setTicketDraft: React.Dispatch<React.SetStateAction<TicketDraft>>; createTicket: (event: React.FormEvent) => Promise<void>
}

function SiteDetail({ site, busy, run, deviceDraft, setDeviceDraft, addDevice, ticketDraft, setTicketDraft, createTicket }: SiteDetailProps) {
  const nextDeviceStatus = (device: ImmersiveDevice) => device.status === 'inventory' ? 'provisioning' : device.status === 'provisioning' ? 'ready' : device.status === 'ready' ? 'deployed' : null
  const passedMilestones = site.milestones.filter((row) => row.status === 'completed' || row.status === 'skipped').length
  return <div className="space-y-5">
    <section className={box}>
      <div className="flex flex-wrap items-start justify-between gap-4"><div><p className="text-xs font-semibold uppercase tracking-wider text-orange-700">{site.code}</p><h3 className="mt-1 text-2xl font-bold">{site.name}</h3><p className="mt-1 text-sm text-slate-500">{site.room_count} room{site.room_count === 1 ? '' : 's'} · planned capacity {site.headset_capacity} headsets</p></div><State value={site.status} /></div>
      <div className="mt-5 grid gap-3 sm:grid-cols-3"><Readiness icon={<Cpu />} label="Network" value={site.network_readiness} /><Readiness icon={<ShieldCheck />} label="Safety" value={site.safety_status} /><Readiness icon={<CheckCircle2 />} label="Milestones" value={`${passedMilestones}/${site.milestones.length}`} /></div>
      <div className="mt-4 flex flex-wrap gap-2"><button className={button} disabled={busy || site.network_readiness === 'ready'} onClick={() => void run(() => meiporulOperationsAPI.updateSite(site.id, { status: 'installing', network_readiness: 'ready', reason: 'Network acceptance completed by platform operations' }), 'Network marked ready.')}>Network ready</button><button className={button} disabled={busy || site.safety_status === 'passed'} onClick={() => void run(() => meiporulOperationsAPI.inspect(site.id, { inspection_type: 'pre_install', status: 'passed', scheduled_for: new Date().toISOString(), completed_at: new Date().toISOString(), checklist: [], findings: 'Safety checklist passed by platform operations.' }), 'Safety inspection passed.')}>Record safety pass</button><button className="rounded-lg bg-emerald-600 px-3 py-2 text-sm font-semibold text-white disabled:opacity-40" disabled={busy || site.status === 'active'} onClick={() => void run(() => meiporulOperationsAPI.updateSite(site.id, { status: 'active', reason: 'All Meiporul go-live controls verified' }), 'Immersive lab is live.')}>Go live</button></div>
    </section>

    <section className={box}><h3 className="font-semibold">Deployment milestones</h3><div className="mt-3 space-y-2">{site.milestones.map((milestone) => <div key={milestone.id} className="flex flex-wrap items-center justify-between gap-3 rounded-xl bg-slate-50 p-3"><div className="flex items-center gap-3"><span className="grid h-7 w-7 place-items-center rounded-full bg-white text-xs font-bold text-slate-600">{milestone.sequence}</span><div><p className="text-sm font-medium">{milestone.title}</p><State value={milestone.status} /></div></div>{milestone.status !== 'completed' && <button disabled={busy} className={button} onClick={() => void run(() => meiporulOperationsAPI.updateMilestone(milestone.id, { status: 'completed', evidence_urls: [], notes: '', reason: 'Milestone evidence reviewed by platform operations' }), `${milestone.title} completed.`)}>Complete</button>}</div>)}</div></section>

    <section className={box}><div className="flex items-center gap-2"><Box className="h-5 w-5 text-violet-600" /><h3 className="font-semibold">Device fleet</h3></div><div className="mt-3 overflow-x-auto"><table className="w-full text-left text-sm"><thead><tr className="border-b text-xs uppercase tracking-wider text-slate-500"><th className="py-2">Asset</th><th>Type</th><th>Room</th><th>Status</th><th /></tr></thead><tbody>{site.devices.map((device) => { const next = nextDeviceStatus(device); return <tr key={device.id} className="border-b"><td className="py-3"><strong>{device.asset_tag}</strong><span className="block text-xs text-slate-500">{device.vendor} {device.model}</span></td><td>{device.device_type}</td><td>{device.assigned_room || '—'}</td><td><State value={device.status} /></td><td className="text-right">{next && <button className={button} disabled={busy} onClick={() => void run(() => meiporulOperationsAPI.updateDevice(device.id, { status: next, reason: `Fleet workflow advanced to ${next}` }), `Device moved to ${next}.`)}>Move to {next}</button>}</td></tr>})}</tbody></table></div>
      <form onSubmit={(event) => void addDevice(event)} className="mt-4 grid gap-3 rounded-xl bg-violet-50 p-4 md:grid-cols-3"><Field required label="Asset tag" value={deviceDraft.asset_tag} onChange={(value) => setDeviceDraft({ ...deviceDraft, asset_tag: value })} /><Field label="Serial number" value={deviceDraft.serial_number} onChange={(value) => setDeviceDraft({ ...deviceDraft, serial_number: value })} /><label className="text-xs font-medium uppercase tracking-wider text-slate-600">Type<select className={input} value={deviceDraft.device_type} onChange={(event) => setDeviceDraft({ ...deviceDraft, device_type: event.target.value })}>{['headset','controller','workstation','router','haptic','other'].map((value) => <option key={value}>{value}</option>)}</select></label><Field label="Vendor" value={deviceDraft.vendor} onChange={(value) => setDeviceDraft({ ...deviceDraft, vendor: value })} /><Field label="Model" value={deviceDraft.model} onChange={(value) => setDeviceDraft({ ...deviceDraft, model: value })} /><Field label="Assigned room" value={deviceDraft.assigned_room} onChange={(value) => setDeviceDraft({ ...deviceDraft, assigned_room: value })} /><button disabled={busy} className="rounded-lg bg-violet-600 px-4 py-2 text-sm font-semibold text-white md:col-span-3">Add device</button></form>
    </section>

    <section className={box}><div className="flex items-center gap-2"><Ticket className="h-5 w-5 text-orange-600" /><h3 className="font-semibold">AMC & support tickets</h3></div><div className="mt-3 space-y-2">{site.tickets.map((ticket) => <div key={ticket.id} className="rounded-xl border border-slate-200 p-3"><div className="flex flex-wrap items-center justify-between gap-2"><div><p className="text-xs font-semibold text-orange-700">{ticket.reference}</p><p className="font-medium">{ticket.subject}</p></div><div className="flex items-center gap-2"><State value={ticket.priority} /><State value={ticket.status} /></div></div><p className="mt-2 text-sm text-slate-600">{ticket.description}</p>{!['resolved','closed'].includes(ticket.status) && <button className={`${button} mt-3`} disabled={busy} onClick={() => void run(() => meiporulOperationsAPI.updateTicket(ticket.id, { status: 'resolved', resolution: 'Issue resolved and verified by platform operations.', reason: 'Resolution validated' }), `${ticket.reference} resolved.`)}>Resolve ticket</button>}</div>)}{site.tickets.length === 0 && <p className="text-sm text-slate-500">No support tickets.</p>}</div>
      <form onSubmit={(event) => void createTicket(event)} className="mt-4 grid gap-3 rounded-xl bg-orange-50 p-4 md:grid-cols-2"><label className="text-xs font-medium uppercase tracking-wider text-slate-600">Category<select className={input} value={ticketDraft.category} onChange={(event) => setTicketDraft({ ...ticketDraft, category: event.target.value })}>{['hardware','software','network','content','safety','training','other'].map((value) => <option key={value}>{value}</option>)}</select></label><label className="text-xs font-medium uppercase tracking-wider text-slate-600">Priority<select className={input} value={ticketDraft.priority} onChange={(event) => setTicketDraft({ ...ticketDraft, priority: event.target.value })}>{['low','normal','high','critical'].map((value) => <option key={value}>{value}</option>)}</select></label><Field required label="Subject" value={ticketDraft.subject} onChange={(value) => setTicketDraft({ ...ticketDraft, subject: value })} /><label className="text-xs font-medium uppercase tracking-wider text-slate-600">Description<textarea required minLength={10} rows={3} className={input} value={ticketDraft.description} onChange={(event) => setTicketDraft({ ...ticketDraft, description: event.target.value })} /></label><button disabled={busy} className="rounded-lg bg-orange-600 px-4 py-2 text-sm font-semibold text-white md:col-span-2">Open support ticket</button></form>
    </section>
  </div>
}

function Field({ label, value, onChange, required = false }: { label: string; value: string; onChange: (value: string) => void; required?: boolean }) { return <label className="text-xs font-medium uppercase tracking-wider text-slate-600">{label}<input required={required} className={input} value={value} onChange={(event) => onChange(event.target.value)} /></label> }
function NumberField({ label, value, min, onChange }: { label: string; value: number; min: number; onChange: (value: number) => void }) { return <label className="text-xs font-medium uppercase tracking-wider text-slate-600">{label}<input required type="number" min={min} className={input} value={value} onChange={(event) => onChange(Number(event.target.value))} /></label> }
function State({ value }: { value: string }) { const healthy = ['active','ready','passed','completed','deployed','resolved','closed','low','normal'].includes(value); const risky = ['failed','blocked','critical','quarantined'].includes(value); return <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium capitalize ${risky ? 'bg-red-50 text-red-700' : healthy ? 'bg-emerald-50 text-emerald-700' : 'bg-amber-50 text-amber-700'}`}>{value.replace(/_/g, ' ')}</span> }
function Readiness({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) { return <div className="rounded-xl bg-slate-50 p-3"><div className="flex items-center gap-2 text-slate-500">{icon}<span className="text-xs font-semibold uppercase tracking-wider">{label}</span></div><p className="mt-2 font-semibold capitalize text-slate-900">{value.replace(/_/g, ' ')}</p></div> }
