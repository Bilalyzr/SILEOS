/**
 * Virtual lab picker for the course editor — the admin-curated catalog
 * (GET /api/v1/virtual-labs): PhET sims, admin embeds and native gradeable
 * labs. Attaches a virtual_lab lesson by slug. Instructor preview is
 * previewOnly (never records a score).
 */
import { useEffect, useMemo, useState } from 'react'
import toast from 'react-hot-toast'
import { listLabs, type LabSummary } from '@/api/labs'
import { VirtualLabPlayer } from './VirtualLabPlayer'

const PROVIDER_BADGE: Record<string, { label: string; cls: string }> = {
  native: { label: 'Interactive', cls: 'bg-emerald-100 text-emerald-800' },
  phet: { label: 'PhET', cls: 'bg-blue-100 text-blue-800' },
  embed: { label: 'Embed', cls: 'bg-gray-100 text-gray-700' },
}

export function VirtualLabPicker({
  attachedSim,
  onAttach,
}: {
  attachedSim: string | null
  onAttach: (sim: string) => void
}) {
  const [labs, setLabs] = useState<LabSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [subject, setSubject] = useState('')
  const [query, setQuery] = useState('')

  useEffect(() => {
    setLoading(true)
    listLabs()
      .then(setLabs)
      .catch(() => toast.error('Failed to load the labs catalog'))
      .finally(() => setLoading(false))
  }, [])

  const subjects = useMemo(() => Array.from(new Set(labs.map((l) => l.subject))).sort(), [labs])
  const visible = labs.filter(
    (l) => (!subject || l.subject === subject) && (!query || l.title.toLowerCase().includes(query.toLowerCase())),
  )
  const attached = labs.find((l) => l.slug === attachedSim)

  return (
    <div className="mt-3 p-4 bg-teal-50 border border-teal-200 rounded-lg">
      <h5 className="font-medium text-gray-900 mb-1">🔬 Virtual Lab</h5>
      {attachedSim ? (
        <div>
          <div className="flex flex-wrap items-center gap-2 mb-2">
            <p className="text-sm font-medium text-emerald-700">✓ Attached: {attached?.title || attachedSim}</p>
            {attached && (
              <span className={`text-[11px] px-2 py-0.5 rounded-full ${PROVIDER_BADGE[attached.provider]?.cls || ''}`}>
                {PROVIDER_BADGE[attached.provider]?.label}
              </span>
            )}
            <button type="button" className="text-sm text-teal-700 hover:underline" onClick={() => onAttach('')}>
              Choose different
            </button>
          </div>
          <VirtualLabPlayer slug={attachedSim} height={360} previewOnly />
        </div>
      ) : loading ? (
        <p className="text-xs text-gray-500">Loading catalog…</p>
      ) : (
        <>
          <div className="flex flex-wrap items-center gap-1.5 mb-2">
            <button
              type="button"
              onClick={() => setSubject('')}
              className={`text-xs px-2 py-1 rounded-full border ${!subject ? 'bg-teal-600 text-white border-teal-600' : 'bg-white border-gray-300 text-gray-700'}`}
            >
              All
            </button>
            {subjects.map((s) => (
              <button
                key={s}
                type="button"
                onClick={() => setSubject(s)}
                className={`text-xs px-2 py-1 rounded-full border capitalize ${subject === s ? 'bg-teal-600 text-white border-teal-600' : 'bg-white border-gray-300 text-gray-700'}`}
              >
                {s}
              </button>
            ))}
            <input
              type="search"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search labs…"
              aria-label="Search labs"
              className="ml-auto text-xs px-2 py-1 border border-gray-300 rounded-md w-36"
            />
          </div>
          {visible.length === 0 ? (
            <p className="text-xs text-gray-400">No labs match. Admins add labs under Admin → Content Libraries.</p>
          ) : (
            <ul className="space-y-1 max-h-64 overflow-y-auto">
              {visible.map((l) => (
                <li key={l.slug}>
                  <button
                    type="button"
                    onClick={() => onAttach(l.slug)}
                    className="w-full text-left text-sm px-3 py-2 rounded-lg border border-gray-200 hover:border-teal-400 bg-white flex items-center gap-2"
                  >
                    <span>🔬</span>
                    <span className="flex-1 min-w-0">
                      <span className="block truncate">{l.title}</span>
                      {l.description && <span className="block text-[11px] text-gray-400 truncate">{l.description}</span>}
                    </span>
                    <span className="text-[11px] text-gray-400 capitalize">{l.subject}</span>
                    <span className={`text-[11px] px-2 py-0.5 rounded-full ${PROVIDER_BADGE[l.provider]?.cls || ''}`}>
                      {PROVIDER_BADGE[l.provider]?.label}
                      {l.provider === 'native' && l.max_score ? ` · ${l.max_score} pts` : ''}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </>
      )}
    </div>
  )
}

export default VirtualLabPicker
