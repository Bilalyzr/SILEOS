/**
 * ScorableItemsEditor — the quiz builder's single "Add item" palette (v2.0
 * §5.2). One row per inserted module with the four universal fields
 * (max score is derived server-side and shown read-only; weight; attempts;
 * practice-only) plus tier floor. A graded item with a tier floor better
 * than T4 shows a blocking warning — the backend refuses to publish it.
 */
import * as React from 'react'
import { AlertTriangle, Plus, Trash2 } from 'lucide-react'
import {
  blocksPublication,
  defaultsFor,
  listScorableItems,
  normalizeItem,
  TIER_LABELS,
  TIERS,
  type RegistryEntry,
  type ScorableItem,
} from '@/api/scorable'

const KIND_ICON: Record<string, string> = { h5p: '🧩', game: '🎮', lab: '🔬', three_d_task: '🧊' }
const KIND_LABEL: Record<string, string> = { h5p: 'H5P module', game: 'Game', lab: 'Lab', three_d_task: '3D task' }

export interface ScorableItemsEditorProps {
  items: ScorableItem[]
  onChange: (items: ScorableItem[]) => void
}

export const ScorableItemsEditor: React.FC<ScorableItemsEditorProps> = ({ items, onChange }) => {
  const [registry, setRegistry] = React.useState<RegistryEntry[]>([])
  const [loading, setLoading] = React.useState(true)
  const [error, setError] = React.useState<string | null>(null)
  const [pick, setPick] = React.useState('')

  React.useEffect(() => {
    let cancelled = false
    listScorableItems()
      .then((r) => { if (!cancelled) setRegistry(r.items) })
      .catch(() => { if (!cancelled) setError('Could not load the item palette') })
      .finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [])

  // Legacy entries (pre-contract `{kind,id,title}`) arrive without the universal
  // fields; the quiz may load AFTER the palette, so normalise whenever items change.
  const isLegacy = (it: ScorableItem) => it.max_score === undefined || it.tier_floor === undefined || it.weight === undefined
  React.useEffect(() => {
    if (loading) return
    if (items.some(isLegacy)) onChange(items.map((it) => normalizeItem(it, registry)))
  }, [items, loading, registry]) // eslint-disable-line react-hooks/exhaustive-deps

  const key = (kind: string, id: number | string) => `${kind}:${id}`
  const inserted = new Set(items.map((i) => key(i.kind, i.id)))
  const available = registry.filter((e) => !inserted.has(key(e.kind, e.id)))

  const add = () => {
    const entry = registry.find((e) => key(e.kind, e.id) === pick)
    if (!entry) return
    onChange([...items, defaultsFor(entry)])
    setPick('')
  }
  const update = (idx: number, patch: Partial<ScorableItem>) =>
    onChange(items.map((it, i) => (i === idx ? { ...normalizeItem(it, registry), ...patch } : it)))
  const remove = (idx: number) => onChange(items.filter((_, i) => i !== idx))

  const rows = items.map((it) => normalizeItem(it, registry))
  const blocked = rows.filter(blocksPublication)
  const totalGradedWeight = rows.filter((i) => !i.practice_only).reduce((s, i) => s + (Number(i.weight) || 0), 0)

  return (
    <div className="bg-white rounded-xl border border-neutral-200 p-6 mb-6">
      <h3 className="font-semibold text-neutral-900 mb-1">Scored items</h3>
      <p className="text-xs text-neutral-500 mb-3">
        A quiz is a container of scorable items (v2.0 §5): questions plus games, H5P modules, labs and 3D tasks.
        Max score is derived from the module; weight sets its share; practice-only items are played but never graded.
      </p>

      {items.length > 0 && (
        <div className="overflow-x-auto mb-3">
          <table className="w-full text-sm">
            <thead className="text-xs text-neutral-500 text-left">
              <tr>
                <th className="py-1 pr-2">Item</th>
                <th className="py-1 pr-2">Max</th>
                <th className="py-1 pr-2">Weight</th>
                <th className="py-1 pr-2">Attempts</th>
                <th className="py-1 pr-2">Tier floor</th>
                <th className="py-1 pr-2">Practice</th>
                <th className="py-1" />
              </tr>
            </thead>
            <tbody>
              {rows.map((it, idx) => {
                const isBlocked = blocksPublication(it)
                return (
                  <tr key={key(it.kind, it.id)} className={`border-t border-neutral-100 ${isBlocked ? 'bg-amber-50' : ''}`}>
                    <td className="py-2 pr-2">
                      <span className="mr-1">{KIND_ICON[it.kind]}</span>
                      <span className="font-medium text-neutral-900">{it.title}</span>
                      <span className="block text-[11px] text-neutral-400">{KIND_LABEL[it.kind]} · {it.grading_mode}</span>
                    </td>
                    <td className="py-2 pr-2 text-neutral-700">{it.max_score}</td>
                    <td className="py-2 pr-2">
                      <input
                        type="number" min={0} max={100} step={0.5} value={it.weight}
                        aria-label={`Weight for ${it.title}`}
                        onChange={(e) => update(idx, { weight: Math.max(0, Math.min(100, Number(e.target.value) || 0)) })}
                        className="w-20 px-2 py-1 border border-neutral-300 rounded"
                      />
                    </td>
                    <td className="py-2 pr-2">
                      <input
                        type="number" min={0} max={99} value={it.attempts_allowed}
                        aria-label={`Attempts allowed for ${it.title} (0 = unlimited)`}
                        onChange={(e) => update(idx, { attempts_allowed: Math.max(0, Math.min(99, parseInt(e.target.value, 10) || 0)) })}
                        className="w-16 px-2 py-1 border border-neutral-300 rounded"
                        title="0 = unlimited"
                      />
                    </td>
                    <td className="py-2 pr-2">
                      <select
                        value={it.tier_floor}
                        aria-label={`Tier floor for ${it.title}`}
                        onChange={(e) => update(idx, { tier_floor: e.target.value as ScorableItem['tier_floor'] })}
                        className="px-2 py-1 border border-neutral-300 rounded text-xs"
                      >
                        {TIERS.map((t) => <option key={t} value={t}>{TIER_LABELS[t]}</option>)}
                      </select>
                    </td>
                    <td className="py-2 pr-2">
                      <label className="inline-flex items-center gap-1 text-xs">
                        <input type="checkbox" checked={it.practice_only} onChange={(e) => update(idx, { practice_only: e.target.checked })} />
                        not graded
                      </label>
                    </td>
                    <td className="py-2 text-right">
                      <button type="button" onClick={() => remove(idx)} className="text-red-500 hover:text-red-700" aria-label={`Remove ${it.title}`}>
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}

      {blocked.length > 0 && (
        <p className="flex items-start gap-2 text-xs text-amber-800 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2 mb-3" role="alert">
          <AlertTriangle className="w-4 h-4 shrink-0" />
          <span>
            Publishing is blocked: graded items must be completable at tier T4 (still images on a low-end phone).
            Mark {blocked.map((b) => `“${b.title}”`).join(', ')} practice-only or lower the tier floor.
          </span>
        </p>
      )}

      <div className="flex flex-wrap items-center gap-2">
        <select
          value={pick}
          onChange={(e) => setPick(e.target.value)}
          aria-label="Add item"
          className="flex-1 min-w-[16rem] px-3 py-2 border border-neutral-300 rounded-lg text-sm"
          disabled={loading || !!error}
        >
          <option value="">{loading ? 'Loading palette…' : error ? error : '— Add item: game, H5P module, lab, 3D task —'}</option>
          {(['game', 'h5p', 'lab', 'three_d_task'] as const).map((kind) => {
            const group = available.filter((e) => e.kind === kind)
            if (group.length === 0) return null
            return (
              <optgroup key={kind} label={`${KIND_ICON[kind]} ${KIND_LABEL[kind]}s`}>
                {group.map((e) => (
                  <option key={key(e.kind, e.id)} value={key(e.kind, e.id)}>
                    {e.title} · {e.max_score} pts{e.source === 'marketplace' ? ' · marketplace' : ''}{e.subject ? ` · ${e.subject}` : ''}
                  </option>
                ))}
              </optgroup>
            )
          })}
        </select>
        <button
          type="button"
          onClick={add}
          disabled={!pick}
          className="inline-flex items-center gap-1 px-3 py-2 text-sm font-medium rounded-lg bg-neutral-900 text-white hover:bg-black disabled:opacity-40"
        >
          <Plus className="w-4 h-4" /> Add item
        </button>
        {items.length > 0 && (
          <span className="text-xs text-neutral-500 ml-auto">graded weight total {totalGradedWeight}</span>
        )}
      </div>
    </div>
  )
}

export default ScorableItemsEditor
