/**
 * ThreeDTaskPlayer — plays a 3D match-and-verify task (v2.0 §6).
 *
 * Two interfaces, identical marks (§6.2 tier parity):
 *   T1 "3D"  — the ThreeDViewer with numbered anchor markers; clicking a
 *              marker selects it; parameters are sliders.
 *   T4 "List" — no WebGL: anchors are neutral "Region N" buttons with their
 *              descriptions, parameters are numeric inputs. Auto-selected when
 *              WebGL is unavailable; always switchable by the learner
 *              (sasha-tier-ladder: show the tier honestly, manual override).
 *
 * Grading is SERVER-SIDE from the submitted state; the evidence trail
 * (rotations, zooms, resets, parameter changes, selections incl. wrong ones,
 * hesitations) is sent alongside and comes back as a confidence signal.
 * previewOnly (instructor) never stores an attempt (backend decides by owner).
 * All strings come from instructor config and render as React text only.
 */
import * as React from 'react'
import toast from 'react-hot-toast'
import {
  threeDTasksAPI, type AssembleConfig, type AttemptResult, type EvidenceEvent, type IdentifyConfig,
  type ManipulateConfig, type MatchConfig, type MeasureConfig, type SequenceConfig, type TaskPlay,
  type VerifyConfig, type Anchor, type Parameter,
} from '@/api/threeDTasks'
import { ThreeDViewer } from '../ThreeDViewer'

type Mode = 'T1' | 'T4'

function webglAvailable(): boolean {
  try {
    const c = document.createElement('canvas')
    return !!(c.getContext('webgl2') || c.getContext('webgl'))
  } catch {
    return false
  }
}

const CONF_LABEL: Record<string, string> = {
  clean: 'Clean path — you reasoned your way there.',
  mixed: 'Mixed path — some exploring, some guessing.',
  trial_and_error: 'The path suggests trial and error — review the concept once more.',
  unknown: '',
}

// ---------------------------------------------------------------- shared bits

function AnchorList({ anchors, selected, onSelect, disabled }: { anchors: Anchor[]; selected: string[]; onSelect: (id: string) => void; disabled?: boolean }) {
  return (
    <ul className="grid sm:grid-cols-2 gap-2" aria-label="Regions of the object">
      {anchors.map((a, i) => (
        <li key={a.id}>
          <button
            type="button"
            disabled={disabled}
            onClick={() => onSelect(a.id)}
            aria-pressed={selected.includes(a.id)}
            className={`w-full text-left px-3 py-2 rounded-lg border text-sm ${selected.includes(a.id) ? 'border-emerald-500 bg-emerald-50' : 'border-gray-200 bg-white hover:border-gray-400'}`}
          >
            <span className="inline-block w-5 h-5 mr-2 rounded-full bg-blue-600 text-white text-[11px] text-center leading-5">{i + 1}</span>
            <span className="font-medium">{a.region || `Region ${i + 1}`}</span>
            {a.description && <span className="block text-xs text-gray-500 mt-0.5">{a.description}</span>}
          </button>
        </li>
      ))}
    </ul>
  )
}

function ParamControls({ params, values, mode, onChange }: { params: Parameter[]; values: Record<string, number>; mode: Mode; onChange: (id: string, v: number) => void }) {
  return (
    <div className="space-y-3">
      {params.map((p) => (
        <label key={p.id} className="block text-sm">
          <span className="flex justify-between text-gray-700">
            <span>{p.label}</span>
            <span className="font-mono">{values[p.id] ?? p.default ?? p.min}{p.unit ? ` ${p.unit}` : ''}</span>
          </span>
          {mode === 'T1' ? (
            <input type="range" min={p.min} max={p.max} step={p.step || (p.max - p.min) / 100} value={values[p.id] ?? p.default ?? p.min}
              onChange={(e) => onChange(p.id, Number(e.target.value))} className="w-full" aria-label={p.label} />
          ) : (
            <input type="number" min={p.min} max={p.max} step={p.step || 'any'} value={values[p.id] ?? p.default ?? p.min}
              onChange={(e) => onChange(p.id, Number(e.target.value))} className="w-full px-2 py-1 border border-gray-300 rounded" aria-label={p.label} />
          )}
          <span className="text-[11px] text-gray-400">{p.min} – {p.max}</span>
        </label>
      ))}
    </div>
  )
}

// ---------------------------------------------------------------- player

export interface ThreeDTaskPlayerProps {
  taskId: number
  previewOnly?: boolean
  onLessonComplete?: () => void
  className?: string
}

export const ThreeDTaskPlayer: React.FC<ThreeDTaskPlayerProps> = ({ taskId, previewOnly = false, onLessonComplete, className = '' }) => {
  const [task, setTask] = React.useState<TaskPlay | null>(null)
  const [error, setError] = React.useState<string | null>(null)
  const [mode, setMode] = React.useState<Mode>(() => (webglAvailable() ? 'T1' : 'T4'))
  const [result, setResult] = React.useState<AttemptResult | null>(null)
  const [submitting, setSubmitting] = React.useState(false)
  const evidence = React.useRef<EvidenceEvent[]>([])
  const startedAt = React.useRef(Date.now())
  const lastAction = React.useRef(Date.now())
  const [runKey, setRunKey] = React.useState(0)

  // answers state (per type)
  const [pairs, setPairs] = React.useState<Record<string, string>>({})          // match: pair index → anchor id
  const [activePair, setActivePair] = React.useState<number>(0)
  const [selections, setSelections] = React.useState<string[]>([])            // identify: per prompt
  const [promptIdx, setPromptIdx] = React.useState(0)
  const [params, setParams] = React.useState<Record<string, number>>({})       // verify / manipulate
  const [verdict, setVerdict] = React.useState<boolean | null>(null)
  const [placements, setPlacements] = React.useState<Record<string, string>>({})
  const [values, setValues] = React.useState<string[]>([])                     // measure
  const [order, setOrder] = React.useState<string[]>([])                       // sequence

  React.useEffect(() => {
    let cancelled = false
    threeDTasksAPI.play(taskId)
      .then((t) => {
        if (cancelled) return
        setTask(t)
        const cfg = t.config as SequenceConfig
        if (t.task_type === 'sequence') setOrder(cfg.steps.map((s) => s.id).sort(() => Math.random() - 0.5))
        const pc = t.config as VerifyConfig
        if (pc.parameters) {
          const init: Record<string, number> = {}
          pc.parameters.forEach((p) => { init[p.id] = p.default ?? p.min })
          setParams(init)
        }
      })
      .catch((err: any) => { if (!cancelled) setError(err?.response?.data?.detail || 'Could not load the 3D task') })
    return () => { cancelled = true }
  }, [taskId, runKey])

  const log = (e: { type: string; [key: string]: string | number | boolean | null | undefined }) => {
    const now = Date.now()
    if (now - lastAction.current > 15000) evidence.current.push({ type: 'hesitate', t: now, gap_ms: now - lastAction.current })
    lastAction.current = now
    if (evidence.current.length < 900) evidence.current.push({ ...e, t: now })
  }

  React.useEffect(() => { log({ type: 'mode', value: mode }) }, [mode])

  if (error) return <div role="alert" className="p-4 border border-red-200 bg-red-50 rounded-lg text-sm text-red-700">{error}</div>
  if (!task) return <p className="text-sm text-gray-500 p-4">Loading 3D task…</p>

  const cfg = task.config
  const anchors: Anchor[] = (cfg as MatchConfig).anchors || []
  const finished = !!result

  const answers = (): Record<string, unknown> => {
    switch (task.task_type) {
      case 'match': return { pairs }
      case 'identify': return { selections }
      case 'verify': return { claim_holds: verdict, final_state: params }
      case 'assemble': return { placements }
      case 'measure': return { values: values.map((v) => (v === '' ? null : Number(v))) }
      case 'manipulate': return { final_state: params }
      case 'sequence': return { order }
      default: return {}
    }
  }

  const submit = async () => {
    setSubmitting(true)
    try {
      const res = await threeDTasksAPI.submit(task.id, {
        answers: answers(), evidence: evidence.current,
        duration_s: Math.max(0, Math.round((Date.now() - startedAt.current) / 1000)), mode,
      })
      setResult(res)
      if (!res.preview && res.score > 0) onLessonComplete?.()
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || 'Could not submit your attempt')
    } finally {
      setSubmitting(false)
    }
  }

  const restart = () => {
    evidence.current = []
    startedAt.current = Date.now()
    setResult(null); setPairs({}); setActivePair(0); setSelections([]); setPromptIdx(0)
    setVerdict(null); setPlacements({}); setValues([]); setRunKey((k) => k + 1)
  }

  // ---- anchor selection dispatcher (T1 marker click or T4 list button)
  const selectedIds: string[] = task.task_type === 'match' ? Object.values(pairs)
    : task.task_type === 'identify' ? selections.filter(Boolean) : []
  const onAnchor = (id: string) => {
    if (finished) return
    if (task.task_type === 'match') {
      const c = cfg as MatchConfig
      const correct = c.pairs[activePair]?.anchor_id === id
      log({ type: 'select', anchor_id: id, correct, pair: activePair })
      setPairs((p) => ({ ...p, [String(activePair)]: id }))
      setActivePair((i) => Math.min(c.pairs.length - 1, i + 1))
    } else if (task.task_type === 'identify') {
      const c = cfg as IdentifyConfig
      const correct = c.prompts[promptIdx]?.anchor_id === id
      log({ type: 'select', anchor_id: id, correct, prompt: promptIdx })
      setSelections((s) => { const n = s.slice(); n[promptIdx] = id; return n })
      setPromptIdx((i) => Math.min(c.prompts.length - 1, i + 1))
    }
  }
  const setParam = (id: string, v: number) => {
    log({ type: 'param', param_id: id, value: v })
    setParams((p) => ({ ...p, [id]: v }))
  }

  const viewer = mode === 'T1' && (
    <ThreeDViewer
      modelId={task.model_id}
      height={380}
      anchors={anchors}
      selectedIds={selectedIds}
      onAnchorClick={onAnchor}
      onEvidence={(e) => log(e)}
    />
  )

  // ---- per-type panels
  let panel: React.ReactNode = null
  if (task.task_type === 'match') {
    const c = cfg as MatchConfig
    panel = (
      <div className="space-y-3">
        <p className="text-sm text-gray-700">Match each label to the region of the object. Pick a label, then click its region.</p>
        <div className="flex flex-wrap gap-2">
          {c.pairs.map((p, i) => (
            <button key={i} type="button" disabled={finished} onClick={() => setActivePair(i)}
              className={`px-3 py-1.5 rounded-full text-sm border ${activePair === i ? 'border-emerald-600 bg-emerald-50' : 'border-gray-300 bg-white'}`}>
              {p.label}{pairs[String(i)] ? ` → ${anchors.find((a) => a.id === pairs[String(i)])?.region ?? '?'}` : ''}
            </button>
          ))}
        </div>
        {mode === 'T4' && <AnchorList anchors={anchors} selected={pairs[String(activePair)] ? [pairs[String(activePair)]] : []} onSelect={onAnchor} disabled={finished} />}
      </div>
    )
  } else if (task.task_type === 'identify') {
    const c = cfg as IdentifyConfig
    panel = (
      <div className="space-y-3">
        <p className="text-sm text-gray-900" role="status" aria-live="polite">
          Find: <strong className="text-emerald-700">{c.prompts[promptIdx]?.condition}</strong>
          <span className="text-xs text-gray-500 ml-2">({promptIdx + 1} of {c.prompts.length})</span>
        </p>
        <div className="flex flex-wrap gap-1.5">
          {c.prompts.map((_, i) => (
            <button key={i} type="button" onClick={() => setPromptIdx(i)} className={`w-7 h-7 rounded-full text-xs border ${selections[i] ? 'bg-emerald-600 text-white border-emerald-600' : 'bg-white border-gray-300'} ${promptIdx === i ? 'ring-2 ring-emerald-500' : ''}`}>{i + 1}</button>
          ))}
        </div>
        {mode === 'T4' && <AnchorList anchors={anchors} selected={selections[promptIdx] ? [selections[promptIdx]] : []} onSelect={onAnchor} disabled={finished} />}
      </div>
    )
  } else if (task.task_type === 'verify') {
    const c = cfg as VerifyConfig
    panel = (
      <div className="space-y-3">
        <p className="text-sm text-gray-900">Claim: <strong>{c.claim}</strong></p>
        <p className="text-xs text-gray-500">Adjust the parameters to test it, leave them at the state that shows your answer, then give your verdict.</p>
        <ParamControls params={c.parameters} values={params} mode={mode} onChange={setParam} />
        <div className="flex gap-2">
          {[true, false].map((v) => (
            <button key={String(v)} type="button" disabled={finished} onClick={() => { setVerdict(v); log({ type: 'select', verdict: v }) }}
              className={`px-3 py-1.5 rounded-lg text-sm border ${verdict === v ? 'border-emerald-600 bg-emerald-50' : 'border-gray-300 bg-white'}`}>
              {v ? 'The claim holds' : 'The claim is false'}
            </button>
          ))}
        </div>
      </div>
    )
  } else if (task.task_type === 'assemble') {
    const c = cfg as AssembleConfig
    panel = (
      <div className="space-y-2">
        <p className="text-sm text-gray-700">Put each part into its slot.</p>
        {c.parts.map((p) => (
          <label key={p.id} className="flex items-center gap-2 text-sm">
            <span className="w-40 font-medium">{p.label}</span>
            <select value={placements[p.id] || ''} disabled={finished}
              onChange={(e) => { setPlacements((s) => ({ ...s, [p.id]: e.target.value })); log({ type: 'place', part: p.id, slot: e.target.value, correct: e.target.value === p.slot_id }) }}
              className="px-2 py-1 border border-gray-300 rounded">
              <option value="">— slot —</option>
              {c.slots.map((s) => <option key={s.id} value={s.id}>{s.label}</option>)}
            </select>
          </label>
        ))}
      </div>
    )
  } else if (task.task_type === 'measure') {
    const c = cfg as MeasureConfig
    panel = (
      <div className="space-y-2">
        <p className="text-xs text-gray-500">{mode === 'T1' ? 'Use the numbered markers to identify the points, then enter each value.' : 'Enter each value.'}</p>
        {c.questions.map((q, i) => (
          <label key={i} className="block text-sm">
            <span className="text-gray-800">{q.prompt}{q.unit ? ` (${q.unit})` : ''}</span>
            <input type="number" step="any" value={values[i] ?? ''} disabled={finished}
              onChange={(e) => setValues((v) => { const n = v.slice(); n[i] = e.target.value; return n })}
              onBlur={() => log({ type: 'param', param_id: `q${i}`, value: Number(values[i]) })}
              className="mt-1 w-40 px-2 py-1 border border-gray-300 rounded" />
          </label>
        ))}
      </div>
    )
  } else if (task.task_type === 'manipulate') {
    const c = cfg as ManipulateConfig
    panel = (
      <div className="space-y-3">
        <ul className="text-sm text-gray-800 list-disc pl-5">{c.targets.map((t, i) => <li key={i}>{t.prompt}</li>)}</ul>
        <ParamControls params={c.parameters} values={params} mode={mode} onChange={setParam} />
      </div>
    )
  } else if (task.task_type === 'sequence') {
    const c = cfg as SequenceConfig
    const byId = Object.fromEntries(c.steps.map((s) => [s.id, s.text]))
    const move = (i: number, d: number) => {
      const j = i + d
      if (j < 0 || j >= order.length) return
      setOrder((o) => { const n = o.slice(); [n[i], n[j]] = [n[j], n[i]]; return n })
      log({ type: 'order', from: i, to: j })
    }
    panel = (
      <ol className="space-y-1" aria-label="Steps in your order">
        {order.map((id, i) => (
          <li key={id} className="flex items-center gap-2 text-sm bg-white border border-gray-200 rounded-lg px-3 py-2">
            <span className="w-5 text-gray-400">{i + 1}.</span>
            <span className="flex-1">{byId[id]}</span>
            <button type="button" disabled={finished || i === 0} onClick={() => move(i, -1)} aria-label="Move up" className="px-2 text-gray-600 disabled:opacity-30">↑</button>
            <button type="button" disabled={finished || i === order.length - 1} onClick={() => move(i, 1)} aria-label="Move down" className="px-2 text-gray-600 disabled:opacity-30">↓</button>
          </li>
        ))}
      </ol>
    )
  }

  return (
    <div className={`space-y-4 ${className}`}>
      <div className="flex flex-wrap items-center gap-2">
        <h3 className="font-semibold text-gray-900 flex-1">{task.title}</h3>
        <span className="text-[11px] px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800">{task.max_score} pts · {task.task_type}</span>
        <div className="inline-flex rounded-full border border-gray-300 overflow-hidden text-xs" role="group" aria-label="Interface tier">
          <button type="button" onClick={() => setMode('T1')} className={`px-3 py-1 ${mode === 'T1' ? 'bg-gray-900 text-white' : 'bg-white text-gray-700'}`}>3D view</button>
          <button type="button" onClick={() => setMode('T4')} className={`px-3 py-1 ${mode === 'T4' ? 'bg-gray-900 text-white' : 'bg-white text-gray-700'}`}>List view (any phone)</button>
        </div>
      </div>
      {previewOnly && <p className="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded px-2 py-1">Instructor preview — attempts are not saved.</p>}
      {(cfg as MatchConfig).intro && <p className="text-sm text-gray-600">{(cfg as MatchConfig).intro}</p>}
      {viewer}
      {mode === 'T4' && anchors.length > 0 && task.task_type !== 'match' && task.task_type !== 'identify' && (
        <AnchorList anchors={anchors} selected={[]} onSelect={() => undefined} disabled />
      )}
      {panel}
      {!finished ? (
        <div className="flex items-center justify-between">
          <p className="text-xs text-gray-500">Same marks in both views — the grade comes from your answers, never from the 3D interaction.</p>
          <button type="button" disabled={submitting} onClick={submit} className="px-4 py-2 text-sm font-semibold rounded-lg bg-gray-900 text-white hover:bg-black disabled:opacity-50">
            {submitting ? 'Grading…' : 'Submit'}
          </button>
        </div>
      ) : (
        <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-4 space-y-1">
          <p className="font-semibold text-emerald-900">Score: {result!.score} / {result!.max_score}{result!.preview ? ' (preview, not saved)' : ` · best ${result!.best_score}`}</p>
          {CONF_LABEL[result!.confidence] && <p className="text-xs text-emerald-800">{CONF_LABEL[result!.confidence]}</p>}
          <button type="button" onClick={restart} className="text-sm font-medium text-emerald-700 hover:underline">Try again</button>
        </div>
      )}
    </div>
  )
}

export default ThreeDTaskPlayer
