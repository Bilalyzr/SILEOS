/**
 * RewardDesigner (v2.0 §4.2 / §10 Reward System Designer — WP6): per-course
 * points overrides, custom badges (rule + threshold + points), streak-freeze
 * allowance and the course leaderboard switch. Saved as one `rewards` object
 * via PUT /api/v1/studio/courses/{id}/settings; the backend validates every
 * field (unknown activities / rules → 422) and gamification.award() reads it.
 */
import * as React from 'react'
import toast from 'react-hot-toast'
import { BADGE_RULE_LABELS, POINT_ACTIVITIES, studioAPI, type BadgeRule, type CourseBadge, type Rewards, type StudioSettings } from '@/api/studio'

export function RewardDesigner({ courseId, settings, onChange }: { courseId: number; settings: StudioSettings; onChange: (s: StudioSettings) => void }) {
  const [draft, setDraft] = React.useState<Rewards>(settings.rewards)
  const [saving, setSaving] = React.useState(false)
  React.useEffect(() => { setDraft(settings.rewards) }, [settings])

  const setPoint = (k: string, v: string) => {
    const points = { ...draft.points }
    if (v === '') delete points[k]
    else points[k] = Math.max(0, Math.min(1000, Number(v) || 0))
    setDraft({ ...draft, points })
  }
  const setBadge = (i: number, patch: Partial<CourseBadge>) => setDraft({ ...draft, badges: draft.badges.map((b, j) => (j === i ? { ...b, ...patch } : b)) })
  const addBadge = () => setDraft({ ...draft, badges: [...draft.badges, { name: '', rule: 'lessons_completed', threshold: 5, points: 25 }] })
  const removeBadge = (i: number) => setDraft({ ...draft, badges: draft.badges.filter((_, j) => j !== i) })

  const save = async () => {
    setSaving(true)
    try {
      const next = await studioAPI.update(courseId, { rewards: { ...draft, badges: draft.badges.map(({ slug: _s, ...b }) => b) } })
      onChange(next)
      toast.success('Rewards saved')
    } catch (e: any) { toast.error(e?.response?.data?.detail || 'Could not save rewards') }
    finally { setSaving(false) }
  }

  return (
    <div className="border border-gray-200 rounded-xl p-6 bg-amber-50" data-testid="reward-designer">
      <div className="flex items-center gap-3 mb-3">
        <div className="w-10 h-10 bg-amber-100 rounded-lg flex items-center justify-center"><span className="text-amber-700 text-xl">🎯</span></div>
        <div>
          <h3 className="text-lg font-semibold text-gray-900">Reward system</h3>
          <p className="text-sm text-gray-500">Points per activity, custom badges, streak freezes and the course leaderboard — for this course only.</p>
        </div>
      </div>

      <div className="grid md:grid-cols-2 gap-4">
        <div className="bg-white rounded-lg border border-gray-200 p-3">
          <p className="text-sm font-semibold text-gray-900 mb-2">Points per activity <span className="font-normal text-gray-400">(blank = platform default)</span></p>
          <div className="grid grid-cols-2 gap-x-3 gap-y-1.5">
            {POINT_ACTIVITIES.map(([k, label]) => (
              <label key={k} className="flex items-center justify-between gap-2 text-xs text-gray-700">
                <span>{label}</span>
                <input type="number" min={0} max={1000} value={draft.points[k] ?? ''} placeholder="—" onChange={(e) => setPoint(k, e.target.value)} className="w-16 px-1.5 py-1 border border-gray-300 rounded text-xs text-right" aria-label={`Points for ${label}`} />
              </label>
            ))}
          </div>
        </div>

        <div className="bg-white rounded-lg border border-gray-200 p-3 space-y-2">
          <p className="text-sm font-semibold text-gray-900">Custom badges</p>
          {draft.badges.length === 0 && <p className="text-xs text-gray-500">No course badges yet.</p>}
          {draft.badges.map((b, i) => (
            <div key={i} className="grid grid-cols-[1fr_auto] gap-1.5 items-center text-xs border border-gray-100 rounded-lg p-2">
              <input value={b.name} onChange={(e) => setBadge(i, { name: e.target.value })} placeholder="Badge name" maxLength={60} className="px-2 py-1 border border-gray-300 rounded" aria-label="Badge name" />
              <button type="button" onClick={() => removeBadge(i)} className="text-red-600 hover:underline">remove</button>
              <div className="col-span-2 flex flex-wrap items-center gap-1.5">
                <span className="text-gray-500">after</span>
                <input type="number" min={1} max={1000} value={b.threshold} onChange={(e) => setBadge(i, { threshold: Number(e.target.value) || 1 })} className="w-14 px-1.5 py-1 border border-gray-300 rounded text-right" aria-label="Threshold" />
                <select value={b.rule} onChange={(e) => setBadge(i, { rule: e.target.value as BadgeRule })} className="px-1.5 py-1 border border-gray-300 rounded" aria-label="Badge rule">
                  {(Object.keys(BADGE_RULE_LABELS) as BadgeRule[]).map((r) => <option key={r} value={r}>{BADGE_RULE_LABELS[r]}</option>)}
                </select>
                <span className="text-gray-500">award</span>
                <input type="number" min={0} max={1000} value={b.points} onChange={(e) => setBadge(i, { points: Number(e.target.value) || 0 })} className="w-14 px-1.5 py-1 border border-gray-300 rounded text-right" aria-label="Badge points" />
                <span className="text-gray-500">XP</span>
              </div>
            </div>
          ))}
          {draft.badges.length < 12 && <button type="button" onClick={addBadge} className="text-xs text-blue-600 hover:underline">+ Add badge</button>}
        </div>
      </div>

      <div className="mt-3 flex flex-wrap items-center gap-4 text-sm">
        <label className="flex items-center gap-2 text-gray-800">
          Streak freezes per month
          <input type="number" min={0} max={10} value={draft.streak_freeze_days_per_month} onChange={(e) => setDraft({ ...draft, streak_freeze_days_per_month: Math.max(0, Math.min(10, Number(e.target.value) || 0)) })} className="w-16 px-2 py-1 border border-gray-300 rounded text-right" />
        </label>
        <label className="flex items-center gap-2 text-gray-800">
          <input type="checkbox" checked={draft.leaderboard_opt_out} onChange={(e) => setDraft({ ...draft, leaderboard_opt_out: e.target.checked })} />
          Switch off the course leaderboard
        </label>
        <button type="button" disabled={saving} onClick={save} className="ml-auto px-4 py-1.5 rounded-lg bg-gray-900 text-white hover:bg-black disabled:opacity-40">{saving ? 'Saving…' : 'Save rewards'}</button>
      </div>
      <p className="text-[11px] text-gray-500 mt-2">A missed day is covered by a freeze automatically (learner-level streak, allowance = the most generous of their enrolled courses). Leaderboards never show emails.</p>
    </div>
  )
}

export default RewardDesigner
