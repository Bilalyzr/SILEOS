/**
 * TagClustersPanel — the emergent taxonomy nobody authored (v2.0 §3).
 * Lists clusters of instructor tags that search treats as one thing; an
 * admin may give a cluster a display label (optional) or rebuild clusters
 * now. Read-only otherwise: tags themselves stay the instructors' words.
 */
import * as React from 'react'
import toast from 'react-hot-toast'
import { RefreshCw, Tag } from 'lucide-react'
import { api } from '@/api/axios'

interface Cluster { id: number; label: string | null; member_tags: string[]; size: number }

export const TagClustersPanel: React.FC = () => {
  const [clusters, setClusters] = React.useState<Cluster[]>([])
  const [loading, setLoading] = React.useState(true)
  const [busy, setBusy] = React.useState(false)
  const [labels, setLabels] = React.useState<Record<number, string>>({})

  const load = React.useCallback(async () => {
    setLoading(true)
    try {
      const r = await api.get('/tag-taxonomy/clusters')
      const rows: Cluster[] = r.data?.clusters || []
      setClusters(rows)
      const l: Record<number, string> = {}
      rows.forEach((c) => { l[c.id] = c.label || '' })
      setLabels(l)
    } catch { toast.error('Could not load tag clusters') } finally { setLoading(false) }
  }, [])
  React.useEffect(() => { load() }, [load])

  const recluster = async () => {
    setBusy(true)
    try { const r = await api.post('/tag-taxonomy/clusters/recluster'); toast.success(`Rebuilt ${r.data.clusters} clusters from ${r.data.tags} tags`); load() }
    catch { toast.error('Recluster failed') } finally { setBusy(false) }
  }
  const saveLabel = async (c: Cluster) => {
    try { await api.put(`/tag-taxonomy/clusters/${c.id}`, { label: labels[c.id] || null }); toast.success('Label saved'); load() }
    catch { toast.error('Could not save the label') }
  }

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4">
      <div className="flex flex-wrap items-center gap-2 mb-2">
        <Tag className="w-4 h-4 text-gray-500" />
        <h2 className="font-semibold text-gray-900 flex-1">Emergent tag clusters</h2>
        <button type="button" disabled={busy} onClick={recluster} className="inline-flex items-center gap-1 px-3 py-1.5 text-xs rounded-lg border border-gray-300 hover:bg-gray-50 disabled:opacity-50">
          <RefreshCw className="w-3.5 h-3.5" /> {busy ? 'Rebuilding…' : 'Rebuild now'}
        </button>
      </div>
      <p className="text-xs text-gray-500 mb-3">
        Instructors tag freely; the platform groups spellings and synonyms (trigonometry, Trig, maths-trig) so learners never miss content. Search expands across a cluster automatically. A label is optional.
      </p>
      {loading ? <p className="text-sm text-gray-500">Loading…</p> : clusters.length === 0 ? <p className="text-sm text-gray-500">No tags on published courses yet.</p> : (
        <ul className="divide-y divide-gray-100">
          {clusters.map((c) => (
            <li key={c.id} className="py-2 flex flex-wrap items-center gap-2">
              <div className="flex-1 min-w-[14rem] flex flex-wrap gap-1">
                {c.member_tags.map((t) => <span key={t} className="px-2 py-0.5 rounded-full bg-gray-100 text-xs text-gray-700">{t}</span>)}
              </div>
              <input value={labels[c.id] ?? ''} onChange={(e) => setLabels((l) => ({ ...l, [c.id]: e.target.value }))} placeholder="optional label" className="w-40 px-2 py-1 border border-gray-300 rounded text-xs" aria-label={`Label for cluster ${c.id}`} />
              <button type="button" onClick={() => saveLabel(c)} className="px-2 py-1 text-xs text-blue-600 hover:underline">Save</button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

export default TagClustersPanel
