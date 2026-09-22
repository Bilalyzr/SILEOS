import { type FormEvent, useEffect, useMemo, useState } from 'react'
import {
  Activity, AlertTriangle, Check, ChevronDown, CircleOff, CloudCog, Eye,
  EyeOff, KeyRound, Loader2, Plus, RefreshCw, ShieldCheck, Sparkles, Trash2, X,
} from 'lucide-react'
import toast from 'react-hot-toast'
import { api } from '@/api/axios'
import { PageHeader, PageLayout } from '@/components/design-system/PageLayout'
import '@/styles/ai-experience.css'

type ProviderName = 'glm' | 'gemini'
type Credential = {
  id: number
  label: string
  provider: ProviderName
  model: string
  key_hint: string
  priority: number
  is_active: boolean
  health_status: 'untested' | 'healthy' | 'degraded' | 'failing'
  failure_count: number
  last_error: string
  last_used_at: string | null
  last_tested_at: string | null
}
type UsageAggregate = {
  scope: string
  provider: string
  model: string
  feature: string | null
  attempts: number
  success: number
  failure: number
  success_rate: number
  avg_latency_ms: number | null
  last_used_at: string | null
}
type RecentFailure = {
  id: number
  credential_id: number | null
  provider: string
  model: string
  feature: string
  error: string
  created_at: string
}
type UsageReport = {
  period_days: number
  total_attempts: number
  total_success: number
  total_failures: number
  success_rate: number
  by_provider: UsageAggregate[]
  by_feature: UsageAggregate[]
  recent_failures: RecentFailure[]
}

const MODEL_OPTIONS: Record<ProviderName, string[]> = {
  glm: ['glm-5.2', 'glm-5.1', 'glm-5-turbo', 'glm-5', 'glm-4.7', 'glm-4.7-flash', 'glm-4.7-flashx', 'glm-4.6', 'glm-4.5-air', 'glm-4.5-airx', 'glm-4.5-flash'],
  gemini: ['gemini-2.5-flash', 'gemini-2.5-pro', 'gemini-2.0-flash'],
}
const DEFAULTS: Record<ProviderName, string> = { glm: 'glm-5.2', gemini: 'gemini-2.5-flash' }
const emptyForm = { label: '', provider: 'glm' as ProviderName, api_key: '', api_keys: '', multiple: false, model: DEFAULTS.glm, priority: 100, is_active: true }

const tone = {
  healthy: 'border-emerald-200 bg-emerald-50 text-emerald-700',
  degraded: 'border-amber-200 bg-amber-50 text-amber-700',
  failing: 'border-rose-200 bg-rose-50 text-rose-700',
  untested: 'border-slate-200 bg-slate-50 text-slate-600',
}

export default function AdminAiProvidersPage() {
  const [credentials, setCredentials] = useState<Credential[]>([])
  const [loading, setLoading] = useState(true)
  const [usageLoading, setUsageLoading] = useState(true)
  const [usageReport, setUsageReport] = useState<UsageReport | null>(null)
  const [showForm, setShowForm] = useState(false)
  const [showKey, setShowKey] = useState(false)
  const [saving, setSaving] = useState(false)
  const [workingId, setWorkingId] = useState<number | null>(null)
  const [deleteId, setDeleteId] = useState<number | null>(null)
  const [form, setForm] = useState(emptyForm)

  const load = async () => {
    setLoading(true)
    try {
      const response = await api.get<Credential[]>('/ai/providers')
      setCredentials(response.data)
    } catch (error: unknown) {
      const detail = (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      toast.error(detail || 'Could not load the AI provider vault')
    } finally { setLoading(false) }

    setUsageLoading(true)
    try {
      const response = await api.get<UsageReport>('/ai/providers/usage', { params: { days: 14 } })
      setUsageReport(response.data)
    } catch (error: unknown) {
      const detail = (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      console.error('Could not load provider usage report', detail || error)
      setUsageReport(null)
    } finally {
      setUsageLoading(false)
    }
  }
  useEffect(() => { void load() }, [])

  const stats = useMemo(() => ({
    active: credentials.filter((item) => item.is_active).length,
    healthy: credentials.filter((item) => item.health_status === 'healthy').length,
    providers: new Set(credentials.map((item) => item.provider)).size,
  }), [credentials])

  const usageStats = useMemo(() => ({
    attempts: usageReport?.total_attempts || 0,
    successRate: usageReport?.success_rate || 0,
    failures: usageReport?.total_failures || 0,
    window: usageReport?.period_days || 14,
  }), [usageReport])

  const topProvider = usageReport?.by_provider?.[0]

  const hasValidKeyInput = form.multiple
    ? form.api_keys.split(/\r?\n/).map((value) => value.trim()).some((value) => value.length >= 8)
    : form.api_key.trim().length >= 8

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const label = form.label.trim()
    const rawKeys = form.multiple
      ? form.api_keys.split(/\r?\n/).map((value) => value.trim()).filter((value) => value.length >= 8)
      : [form.api_key.trim()].filter((value) => value.length >= 8)
    if (!label || rawKeys.length === 0) return
    setSaving(true)
    try {
      const created: Credential[] = []
      const failures: string[] = []
      for (let index = 0; index < rawKeys.length; index += 1) {
        const key = rawKeys[index]
        const derivedLabel = rawKeys.length === 1 ? label : `${label} #${index + 1}`
        try {
          const response = await api.post<Credential>('/ai/providers', {
            label: derivedLabel,
            provider: form.provider,
            api_key: key,
            model: form.model.trim(),
            priority: form.priority,
            is_active: form.is_active,
          })
          created.push(response.data)
        } catch (error: unknown) {
          const detail = (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail
          failures.push(`${derivedLabel}: ${detail || 'Could not add key'}`)
        }
      }
      if (created.length > 0) {
        setCredentials((current) => [...created, ...current].sort((a, b) => a.priority - b.priority))
      }
      await load()
      setForm(emptyForm)
      setShowForm(false)
      setShowKey(false)
      if (created.length > 0 && failures.length === 0) {
        toast.success(`Added ${created.length} key${created.length === 1 ? '' : 's'} successfully`)
      } else if (created.length > 0) {
        toast.success(`Added ${created.length} key${created.length === 1 ? '' : 's'}; ${failures.length} failed`)
      } else {
        toast.error(failures[0] || 'Could not add provider key')
      }
    } catch (error: unknown) {
      const detail = (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      toast.error(detail || 'Could not add provider key')
    } finally { setSaving(false) }
  }

  const patchCredential = async (id: number, payload: Partial<Pick<Credential, 'is_active' | 'priority' | 'model'>>) => {
    setWorkingId(id)
    try {
      const response = await api.patch<Credential>(`/ai/providers/${id}`, payload)
      setCredentials((current) => current.map((item) => item.id === id ? response.data : item).sort((a, b) => a.priority - b.priority))
    } catch { toast.error('Could not update provider') }
    finally { setWorkingId(null) }
  }

  const testProvider = async (id: number) => {
    setWorkingId(id)
    try {
      const response = await api.post<Credential>(`/ai/providers/${id}/test`)
      setCredentials((current) => current.map((item) => item.id === id ? response.data : item))
      toast[response.data.health_status === 'healthy' ? 'success' : 'error'](
        response.data.health_status === 'healthy' ? 'Provider answered successfully' : (response.data.last_error || 'Provider check failed'),
        { duration: response.data.health_status === 'healthy' ? 3000 : 7000 },
      )
    } catch { toast.error('Provider check could not run') }
    finally { setWorkingId(null) }
  }

  const remove = async () => {
    if (deleteId === null) return
    setWorkingId(deleteId)
    try {
      await api.delete(`/ai/providers/${deleteId}`)
      setCredentials((current) => current.filter((item) => item.id !== deleteId))
      toast.success('Provider key permanently removed')
      setDeleteId(null)
    } catch { toast.error('Could not remove provider key') }
    finally { setWorkingId(null) }
  }

  return (
    <PageLayout
      className="rd-screen rd-screen-admin-ai-providers"
      header={<PageHeader><div><h1 className="text-3xl font-bold text-slate-950">AI Provider Vault</h1><p className="mt-1 text-slate-600">Secure multi-key routing for Sasha, generation tools, and learning intelligence.</p></div></PageHeader>}
    >
      <section className="relative mb-7 overflow-hidden rounded-[2rem] bg-[#1b100b] p-6 text-white shadow-xl shadow-orange-950/10 md:p-8">
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_85%_0%,rgba(249,115,22,.36),transparent_30%),radial-gradient(circle_at_12%_110%,rgba(251,191,36,.24),transparent_34%)]" />
        <div className="pointer-events-none absolute -right-8 -top-16 h-64 w-64 rounded-full border border-orange-200/10" />
        <div className="relative flex flex-col justify-between gap-8 lg:flex-row lg:items-end">
          <div className="max-w-2xl">
            <span className="inline-flex items-center gap-2 rounded-full border border-orange-200/20 bg-orange-300/10 px-3 py-1.5 text-xs font-semibold text-orange-100"><ShieldCheck className="h-3.5 w-3.5" /> Server-side encrypted</span>
            <h2 className="ai-vault-hero-title mt-5 text-3xl font-semibold tracking-tight md:text-4xl">One intelligence layer.<br /><span className="ai-vault-gradient">Many resilient keys.</span></h2>
            <p className="mt-3 max-w-xl text-sm leading-6 text-[#cbd5e1]">Sasha automatically tries active credentials in priority order. Secrets are encrypted before storage and are never returned to the browser.</p>
          </div>
          <button onClick={() => setShowForm(true)} className="inline-flex items-center justify-center gap-2 rounded-2xl bg-gradient-to-r from-orange-500 to-amber-300 px-5 py-3 text-sm font-bold text-slate-950 shadow-lg shadow-orange-950/20 transition hover:-translate-y-0.5 hover:from-orange-400 hover:to-amber-200"><Plus className="h-4 w-4" /> Add API key</button>
        </div>
        <div className="relative mt-8 grid grid-cols-3 gap-3">
          {[['Active keys', stats.active], ['Healthy', stats.healthy], ['Providers', stats.providers]].map(([label, value]) => <div key={label} className="rounded-2xl border border-white/10 bg-white/[0.055] p-4 backdrop-blur"><p className="text-2xl font-semibold text-[#f8fafc]">{value}</p><p className="mt-1 text-xs text-[#cbd5e1]">{label}</p></div>)}
        </div>
      </section>

      <section className="mb-7 rounded-[1.75rem] border border-slate-200 bg-white p-5 shadow-sm md:p-6">
        <div className="mb-5 flex items-center justify-between">
          <div><h3 className="text-lg font-semibold text-slate-950">AI routing health ({usageStats.window}d)</h3><p className="mt-1 text-sm text-slate-500">Provider health across feature-aware call attempts.</p></div>
          <button onClick={() => void load()} disabled={loading || usageLoading} className="grid h-10 w-10 place-items-center rounded-xl border border-slate-200 text-slate-500 transition hover:bg-slate-50" aria-label="Refresh provider usage"><RefreshCw className={`h-4 w-4 ${(loading || usageLoading) ? 'animate-spin' : ''}`} /></button>
        </div>

        {usageLoading ? (
          <div className="grid min-h-28 place-items-center"><Loader2 className="h-6 w-6 animate-spin text-orange-500" /></div>
        ) : (
          <div className="space-y-5">
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
              <div className="rounded-2xl border border-slate-100 bg-slate-50 p-4">
                <p className="text-2xl font-semibold text-slate-900">{usageStats.attempts}</p>
                <p className="mt-1 text-xs text-slate-500">Attempted calls</p>
              </div>
              <div className="rounded-2xl border border-emerald-100 bg-emerald-50 p-4">
                <p className="text-2xl font-semibold text-emerald-700">{usageStats.successRate}%</p>
                <p className="mt-1 text-xs text-emerald-700">Success rate</p>
              </div>
              <div className="rounded-2xl border border-rose-100 bg-rose-50 p-4">
                <p className="text-2xl font-semibold text-rose-700">{usageStats.failures}</p>
                <p className="mt-1 text-xs text-rose-700">Failed attempts</p>
              </div>
            </div>
            {topProvider ? <p className="text-sm text-slate-600">Top provider this window: <span className="font-semibold text-slate-900">{topProvider.provider} · {topProvider.model}</span> ({topProvider.success_rate}% success)</p> : null}
            <div className="overflow-x-auto rounded-2xl border border-slate-200">
              <table className="min-w-full divide-y divide-slate-100 text-sm">
                <thead className="bg-slate-50 text-slate-600">
                  <tr>
                    <th className="px-4 py-3 text-left font-semibold">Provider / Model</th>
                    <th className="px-4 py-3 text-left font-semibold">Attempts</th>
                    <th className="px-4 py-3 text-left font-semibold">Success</th>
                    <th className="px-4 py-3 text-left font-semibold">Failure</th>
                    <th className="px-4 py-3 text-left font-semibold">Success Rate</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {(usageReport?.by_provider || []).slice(0, 6).map((entry) => (
                    <tr key={`${entry.provider}-${entry.scope}-${entry.model}`}>
                      <td className="px-4 py-3 text-slate-900">{entry.provider} / {entry.model}</td>
                      <td className="px-4 py-3 text-slate-600">{entry.attempts}</td>
                      <td className="px-4 py-3 text-emerald-700">{entry.success}</td>
                      <td className="px-4 py-3 text-rose-700">{entry.failure}</td>
                      <td className="px-4 py-3 text-slate-800">{entry.success_rate}%</td>
                    </tr>
                  ))}
                  {(usageReport?.by_provider || []).length === 0 && (
                    <tr><td colSpan={5} className="px-4 py-6 text-center text-sm text-slate-500">No attempts were recorded in the selected window.</td></tr>
                  )}
                </tbody>
              </table>
            </div>
            <div>
              <h4 className="mb-2 text-sm font-semibold text-slate-700">Recent failures</h4>
              <div className="overflow-x-auto rounded-2xl border border-rose-200 bg-rose-50/40">
                <table className="min-w-full divide-y divide-rose-100 text-sm">
                  <thead className="bg-rose-100/70 text-rose-700">
                    <tr>
                      <th className="px-4 py-2.5 text-left font-semibold">Feature</th>
                      <th className="px-4 py-2.5 text-left font-semibold">Provider</th>
                      <th className="px-4 py-2.5 text-left font-semibold">Model</th>
                      <th className="px-4 py-2.5 text-left font-semibold">Error</th>
                      <th className="px-4 py-2.5 text-left font-semibold">Time</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-rose-100">
                    {(usageReport?.recent_failures || []).map((failure) => (
                      <tr key={failure.id}>
                        <td className="px-4 py-2.5 text-slate-700">{failure.feature}</td>
                        <td className="px-4 py-2.5 text-slate-700">{failure.provider}</td>
                        <td className="px-4 py-2.5 text-slate-700">{failure.model}</td>
                        <td className="max-w-md px-4 py-2.5 text-rose-700">{failure.error}</td>
                        <td className="px-4 py-2.5 text-slate-500">{new Date(failure.created_at).toLocaleString()}</td>
                      </tr>
                    ))}
                    {(usageReport?.recent_failures || []).length === 0 && (
                      <tr><td colSpan={5} className="px-4 py-4 text-center text-sm text-slate-500">No recent failures in the selected window.</td></tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}
      </section>

      <section className="rounded-[1.75rem] border border-slate-200 bg-white p-5 shadow-sm md:p-6">
        <div className="mb-5 flex items-center justify-between">
          <div><h3 className="text-lg font-semibold text-slate-950">Routing pool</h3><p className="mt-1 text-sm text-slate-500">Lower priority numbers are attempted first.</p></div>
          <button onClick={() => void load()} disabled={loading} className="grid h-10 w-10 place-items-center rounded-xl border border-slate-200 text-slate-500 transition hover:bg-slate-50" aria-label="Refresh providers"><RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} /></button>
        </div>

        {loading ? <div className="grid min-h-56 place-items-center"><Loader2 className="h-7 w-7 animate-spin text-orange-500" /></div> : credentials.length === 0 ? (
          <div className="grid min-h-64 place-items-center rounded-3xl border border-dashed border-slate-200 bg-slate-50/70 p-8 text-center">
            <div><div className="mx-auto grid h-14 w-14 place-items-center rounded-2xl bg-orange-100 text-orange-700"><KeyRound className="h-6 w-6" /></div><h4 className="mt-4 font-semibold text-slate-900">No provider keys yet</h4><p className="mt-2 max-w-sm text-sm leading-6 text-slate-500">Add more than one key to remove a single point of failure from Sasha’s AI services.</p><button onClick={() => setShowForm(true)} className="mt-5 rounded-xl bg-gradient-to-r from-orange-600 to-amber-500 px-4 py-2.5 text-sm font-semibold text-white">Add your first key</button></div>
          </div>
        ) : (
          <div className="space-y-3">
            {credentials.map((item, index) => (
              <article key={item.id} className={`group grid gap-4 rounded-2xl border p-4 transition md:grid-cols-[minmax(0,1fr)_140px_150px_auto] md:items-center ${item.is_active ? 'border-slate-200 hover:border-orange-200 hover:shadow-md' : 'border-slate-100 bg-slate-50/70 opacity-70'}`}>
                <div className="flex min-w-0 items-center gap-4">
                  <div className={`grid h-12 w-12 shrink-0 place-items-center rounded-2xl ${item.provider === 'gemini' ? 'bg-gradient-to-br from-amber-100 to-orange-100 text-orange-700' : 'bg-gradient-to-br from-orange-100 to-amber-50 text-orange-800'}`}><Sparkles className="h-5 w-5" /></div>
                  <div className="min-w-0"><div className="flex flex-wrap items-center gap-2"><h4 className="truncate font-semibold text-slate-950">{item.label}</h4>{index === 0 && item.is_active && <span className="rounded-full bg-orange-100 px-2 py-1 text-xs font-bold uppercase tracking-wide text-orange-700">Primary</span>}</div><div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-slate-500"><span className="capitalize">{item.provider}</span><span>·</span><select aria-label={`Model for ${item.label}`} value={item.model} onChange={(event) => void patchCredential(item.id, { model: event.target.value })} disabled={workingId === item.id} className="rounded-md border border-orange-100 bg-orange-50 px-1.5 py-1 text-xs font-semibold text-orange-800 outline-none focus:ring-2 focus:ring-orange-300">{MODEL_OPTIONS[item.provider].map((model) => <option key={model} value={model}>{model}</option>)}{!MODEL_OPTIONS[item.provider].includes(item.model) && <option value={item.model}>{item.model} · unsupported</option>}</select><span>·</span><span className="font-mono">{item.key_hint}</span></div></div>
                </div>
                <label className="relative"><span className="sr-only">Priority</span><select value={item.priority} onChange={(event) => void patchCredential(item.id, { priority: Number(event.target.value) })} disabled={workingId === item.id} className="w-full appearance-none rounded-xl border border-slate-200 bg-white px-3 py-2.5 pr-8 text-xs font-medium text-slate-700 outline-none focus:border-orange-400"><option value={10}>Priority 10</option><option value={50}>Priority 50</option><option value={100}>Priority 100</option><option value={250}>Priority 250</option><option value={500}>Priority 500</option></select><ChevronDown className="pointer-events-none absolute right-3 top-3 h-3.5 w-3.5 text-slate-400" /></label>
                <div><span className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1.5 text-xs font-semibold capitalize ${tone[item.health_status]}`}>{item.health_status === 'healthy' ? <Check className="h-3.5 w-3.5" /> : item.health_status === 'failing' ? <CircleOff className="h-3.5 w-3.5" /> : item.health_status === 'degraded' ? <AlertTriangle className="h-3.5 w-3.5" /> : <Activity className="h-3.5 w-3.5" />}{item.health_status}</span>{item.last_error && <p className="mt-1 line-clamp-2 text-xs leading-5 text-rose-600" title={item.last_error}>{item.last_error}</p>}</div>
                <div className="flex items-center justify-end gap-1">
                  <button onClick={() => void patchCredential(item.id, { is_active: !item.is_active })} disabled={workingId === item.id} className={`rounded-lg px-2.5 py-2 text-xs font-semibold transition ${item.is_active ? 'text-emerald-700 hover:bg-emerald-50' : 'text-slate-500 hover:bg-slate-100'}`}>{item.is_active ? 'Active' : 'Paused'}</button>
                  <button onClick={() => void testProvider(item.id)} disabled={workingId === item.id || !item.is_active} className="rounded-lg p-2 text-slate-500 transition hover:bg-orange-50 hover:text-orange-700 disabled:opacity-30" aria-label={`Test ${item.label}`}>{workingId === item.id ? <Loader2 className="h-4 w-4 animate-spin" /> : <CloudCog className="h-4 w-4" />}</button>
                  <button onClick={() => setDeleteId(item.id)} className="rounded-lg p-2 text-slate-400 transition hover:bg-rose-50 hover:text-rose-600" aria-label={`Delete ${item.label}`}><Trash2 className="h-4 w-4" /></button>
                </div>
              </article>
            ))}
          </div>
        )}
      </section>

      {showForm && <div className="fixed inset-0 z-modal grid place-items-center bg-slate-950/55 p-4 backdrop-blur-sm" role="dialog" aria-modal="true" aria-labelledby="provider-form-title">
        <form onSubmit={submit} className="ai-vault-modal w-full max-w-xl overflow-hidden rounded-[2rem] bg-[#ffffff] shadow-2xl">
          <div className="flex items-start justify-between bg-[#1b100b] p-6 text-white"><div><p className="text-xs font-semibold uppercase tracking-[0.18em] text-orange-300">Secure credential</p><h3 id="provider-form-title" className="ai-vault-modal-title mt-2 text-2xl font-semibold">Add an AI provider key</h3><p className="mt-2 text-sm text-[#cbd5e1]">The plaintext value is discarded immediately after encryption.</p></div><button type="button" onClick={() => setShowForm(false)} className="rounded-xl border border-white/10 p-2 text-[#cbd5e1] hover:bg-white/10 hover:text-white"><X className="h-4 w-4" /></button></div>
          <div className="grid gap-5 p-6 md:grid-cols-2">
            <label className="md:col-span-2">
              <span className="mb-1.5 block text-sm font-medium text-slate-700">Friendly label</span>
              <input
                value={form.label}
                onChange={(event) => setForm({ ...form, label: event.target.value })}
                placeholder="Production Gemini · key 01"
                className="w-full rounded-xl border border-slate-200 px-3.5 py-3 text-sm outline-none focus:border-orange-400 focus:ring-4 focus:ring-orange-100"
                required
              />
            </label>
            <label>
              <span className="mb-1.5 block text-sm font-medium text-slate-700">Provider</span>
              <select
                value={form.provider}
                onChange={(event) => {
                  const provider = event.target.value as ProviderName
                  setForm({ ...form, provider, model: DEFAULTS[provider] })
                }}
                className="w-full rounded-xl border border-slate-200 bg-white px-3.5 py-3 text-sm outline-none focus:border-orange-400"
              >
                <option value="glm">Zhipu GLM</option>
                <option value="gemini">Google Gemini</option>
              </select>
            </label>
            <label>
              <span className="mb-1.5 block text-sm font-medium text-slate-700">Model</span>
              <select
                value={form.model}
                onChange={(event) => setForm({ ...form, model: event.target.value })}
                className="w-full rounded-xl border border-slate-200 bg-white px-3.5 py-3 text-sm outline-none focus:border-orange-400"
                required
              >
                {MODEL_OPTIONS[form.provider].map((model) => <option key={model} value={model}>{model}</option>)}
              </select>
            </label>
            <label className="flex items-center gap-3 self-end rounded-xl border border-slate-200 px-3.5 py-3">
              <input
                type="checkbox"
                checked={form.multiple}
                onChange={(event) => setForm({ ...form, multiple: event.target.checked })}
                className="h-4 w-4 accent-orange-600"
              />
              <span className="text-sm font-medium text-slate-700">Add multiple keys (one per line)</span>
            </label>
            {form.multiple ? (
              <label className="relative md:col-span-2">
                <span className="mb-1.5 block text-sm font-medium text-slate-700">API keys (one per line)</span>
                <textarea
                  value={form.api_keys}
                  onChange={(event) => setForm({ ...form, api_keys: event.target.value })}
                  rows={5}
                  autoComplete="off"
                  placeholder="Paste one key per line"
                  className="w-full rounded-xl border border-slate-200 px-3.5 py-3 font-mono text-sm outline-none focus:border-orange-400 focus:ring-4 focus:ring-orange-100"
                  required={form.multiple}
                />
                <p className="mt-1.5 text-xs text-slate-500">Empty lines are ignored.</p>
              </label>
            ) : (
              <label className="relative md:col-span-2">
                <span className="mb-1.5 block text-sm font-medium text-slate-700">API key</span>
                <input
                  type={showKey ? 'text' : 'password'}
                  value={form.api_key}
                  onChange={(event) => setForm({ ...form, api_key: event.target.value })}
                  autoComplete="off"
                  placeholder="Paste the provider key"
                  className="w-full rounded-xl border border-slate-200 px-3.5 py-3 pr-12 font-mono text-sm outline-none focus:border-orange-400 focus:ring-4 focus:ring-orange-100"
                  required={!form.multiple}
                  minLength={8}
                />
                <button type="button" onClick={() => setShowKey((value) => !value)} className="absolute bottom-2 right-2 rounded-lg p-2 text-slate-400 hover:bg-slate-100" aria-label={showKey ? 'Hide API key' : 'Show API key'}>
                  {showKey ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </label>
            )}
            <label>
              <span className="mb-1.5 block text-sm font-medium text-slate-700">Routing priority</span>
              <select
                value={form.priority}
                onChange={(event) => setForm({ ...form, priority: Number(event.target.value) })}
                className="w-full rounded-xl border border-slate-200 bg-white px-3.5 py-3 text-sm outline-none focus:border-orange-400"
              >
                <option value={10}>10 · First</option>
                <option value={50}>50 · High</option>
                <option value={100}>100 · Normal</option>
                <option value={250}>250 · Fallback</option>
                <option value={500}>500 · Last resort</option>
              </select>
            </label>
            <label className="flex items-center gap-3 self-end rounded-xl border border-slate-200 px-3.5 py-3">
              <input
                type="checkbox"
                checked={form.is_active}
                onChange={(event) => setForm({ ...form, is_active: event.target.checked })}
                className="h-4 w-4 accent-orange-600"
              />
              <span className="text-sm font-medium text-slate-700">Activate immediately</span>
            </label>
          </div>
          <div className="flex justify-end gap-3 border-t border-slate-100 bg-[#f8fafc] px-6 py-4">
            <button type="button" onClick={() => setShowForm(false)} className="rounded-xl px-4 py-2.5 text-sm font-semibold text-slate-600 hover:bg-slate-200">Cancel</button>
            <button
              type="submit"
              disabled={saving || !form.label.trim() || !hasValidKeyInput}
              className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-orange-600 to-amber-500 px-5 py-2.5 text-sm font-semibold text-white disabled:opacity-40"
            >
              {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <ShieldCheck className="h-4 w-4" />} Encrypt & add
            </button>
          </div>
        </form>
      </div>}

      {deleteId !== null && <div className="fixed inset-0 z-modal grid place-items-center bg-slate-950/55 p-4 backdrop-blur-sm" role="alertdialog" aria-modal="true" aria-labelledby="delete-provider-title"><div className="ai-vault-delete-modal w-full max-w-md rounded-3xl bg-[#ffffff] p-6 shadow-2xl"><div className="grid h-12 w-12 place-items-center rounded-2xl bg-rose-100 text-rose-700"><Trash2 className="h-5 w-5" /></div><h3 id="delete-provider-title" className="mt-4 text-xl font-semibold text-slate-950">Remove this API key?</h3><p className="mt-2 text-sm leading-6 text-slate-500">The encrypted credential will be permanently deleted. Other active keys will remain available for automatic failover.</p><div className="mt-6 flex justify-end gap-3"><button onClick={() => setDeleteId(null)} className="rounded-xl px-4 py-2.5 text-sm font-semibold text-slate-600 hover:bg-slate-100">Cancel</button><button onClick={() => void remove()} disabled={workingId !== null} className="rounded-xl bg-rose-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-rose-700">Remove key</button></div></div></div>}
    </PageLayout>
  )
}

