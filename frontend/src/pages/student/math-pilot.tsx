import { useCallback, useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { mathPilot, type MathData, type MathSession } from '@/api/math-pilot'
import { plannerError } from '@/api/planner'
import VolumeExplorer from '@/components/labs/VolumeExplorer'
import '@/styles/math-pilot.css'

const button = 'rounded-xl bg-gradient-to-r from-orange-600 to-amber-600 px-5 py-3 font-semibold text-white disabled:opacity-50'
export default function MathPilotPage() {
  const [data, setData] = useState<MathData | null>(null)
  const [row, setRow] = useState<MathSession | null>(null)
  const [course, setCourse] = useState(0)
  const [answers, setAnswers] = useState<string[]>([])
  const [layers, setLayers] = useState(1)
  const [acknowledge, setAcknowledge] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const pending = useRef<{ fingerprint: string; key: string } | null>(null)
  const load = useCallback(async () => {
    const next = await mathPilot.me()
    setData(next)
    setCourse(current => current || next.courses[0]?.id || 0)
  }, [])
  useEffect(() => { void load().catch(e => setError(plannerError(e))) }, [load])
  const run = async (action: () => Promise<void>) => {
    setBusy(true); setError('')
    try { await action() } catch (e) { setError(plannerError(e)) } finally { setBusy(false) }
  }
  const choose = (next: MathSession) => { setRow(next); setAnswers([]); setLayers(1) }
  const submit = () => run(async () => {
    if (!row) return
    const values = row.stage === 'build' ? [layers, Number(answers[0])] : answers.map(Number)
    const fingerprint = JSON.stringify([row.id, row.sequence, values])
    if (pending.current?.fingerprint !== fingerprint) pending.current = { fingerprint, key: crypto.randomUUID() }
    choose(await mathPilot.answer(row, values, pending.current.key))
    pending.current = null
    await load()
  })
  const exportRecord = () => run(async () => {
    if (!row) return
    const result = await mathPilot.export(row.id)
    const url = URL.createObjectURL(new Blob([JSON.stringify(result, null, 2)], { type: 'application/json' }))
    const a = document.createElement('a'); a.href = url; a.download = 'my-private-math-evidence.json'; a.click(); URL.revokeObjectURL(url)
  })
  const remove = () => run(async () => {
    if (!row || !window.confirm('Delete this pilot attempt, its answers and its contribution to your mastery estimate? This cannot be undone.')) return
    await mathPilot.remove(row.id); setRow(null); await load()
  })
  const expected = row?.stage === 'predict' || row?.stage === 'build' ? 1 : 2
  const valid = answers.length === expected && answers.every(a => a !== '' && /^\d+$/.test(a) && Number(a) <= 1000)
  return <main className="sasha-math-page min-h-screen bg-gradient-to-br from-orange-50 via-white to-amber-50 p-5 text-slate-900 md:p-10"><div className="mx-auto max-w-4xl">
    <Link to="/my-mastery" className="text-orange-700">← My mastery</Link>
    <header className="math-hero my-7 rounded-3xl bg-gradient-to-r from-orange-600 to-amber-500 p-7 text-white"><p className="text-sm font-semibold">SashaInfinity · Meiporul × Seyappaduporul × Utporul</p><h1 className="mt-3 text-3xl font-bold">Make sense of volume</h1><p className="mt-3">Predict. Build. Explain. Check what stays with you.</p></header>
    {error && <p role="alert" className="mb-4 rounded-xl bg-red-50 p-4 text-red-800">{error} <button className="underline" onClick={() => void run(async () => { const next = await mathPilot.me(); setData(next); if (row) setRow(next.sessions.find(s => s.id === row.id) || null) })}>Reload saved activity</button></p>}
    {!data && !error && <p role="status">Loading your courses…</p>}
    {!row && data && <section className="rounded-2xl border border-orange-200 bg-white p-6">
      <h2 className="text-xl font-semibold">Your classroom pilot</h2>
      <p className="my-3">Your answers and task steps are visible to authorized course educators and you, retained for up to 90 days. You can export or delete this pilot record. Two correct answers are not a permanent mastery label.</p>
      <label htmlFor="math-course">Course</label><select id="math-course" value={course} onChange={e => setCourse(Number(e.target.value))} className="si-input my-2 w-full">{data.courses.map(c => <option key={c.id} value={c.id}>{c.title}{c.approved ? '' : ' — awaiting educator review'}</option>)}</select>
      {!data.courses.length && <p>You need an active course enrollment. You can still <Link className="text-orange-700 underline" to="/discover/volume">explore the public demo</Link>.</p>}
      <label className="my-4 flex gap-3"><input type="checkbox" checked={acknowledge} onChange={e => setAcknowledge(e.target.checked)} />I understand how this pilot records my answers.</label>
      <button className={button} disabled={busy || !acknowledge || !data.courses.find(c => c.id === course)?.approved} onClick={() => void run(async () => choose(await mathPilot.start(course)))}>Start or resume</button>
      {data.sessions.map(s => <button className="ml-3 mt-3 rounded-xl border border-orange-200 p-3" key={s.id} disabled={busy} onClick={() => choose(s)}>Resume course {s.course_id}: {s.stage}</button>)}
    </section>}
    {row && <section className="rounded-2xl border border-orange-200 bg-white p-6">
      <div className="flex items-center justify-between"><p className="font-semibold uppercase tracking-widest text-orange-700">{row.stage}</p><button onClick={() => setRow(null)} className="text-sm underline">Choose another course</button></div>
      {row.task.prompt && <h2 className="my-5 text-xl font-semibold">{row.task.prompt}</h2>}
      {row.stage === 'build' && <><p className="mb-4 rounded-xl bg-amber-50 p-4">{row.explanation}</p><VolumeExplorer layers={layers} onChange={setLayers} /></>}
      {row.task.options && <fieldset className="my-4 space-y-3"><legend className="sr-only">Your prediction</legend>{row.task.options.map((option, i) => <label key={option} className="flex gap-3 rounded-xl border border-orange-100 p-4"><input type="radio" name="prediction" value={i} checked={answers[0] === String(i)} onChange={() => setAnswers([String(i)])} />{option}</label>)}</fieldset>}
      {(row.stage === 'build' ? ['Total number of unit cubes'] : row.task.questions || []).map((q, i) => <label className="my-4 block" key={q}>{q}<input className="si-input mt-2 w-full" type="number" min="0" max="1000" step="1" value={answers[i] ?? ''} onChange={e => setAnswers(old => Array.from({ length: expected }, (_, n) => n === i ? e.target.value : old[n] ?? ''))} /></label>)}
      {row.feedback && <p role="status" className="my-3 text-orange-800">{row.feedback}</p>}
      {!['waiting', 'complete'].includes(row.stage) && <button className={button} disabled={busy || !valid} onClick={() => void submit()}>Save and continue</button>}
      {row.stage === 'waiting' && <div className="my-6"><h2 className="text-2xl font-bold">Let the learning settle.</h2><p className="mt-3">Your independent check: {row.transfer_score}/2. A different check unlocks {row.due_at && new Date(row.due_at).toLocaleString()}. A low score is a reason to ask your teacher for support, not a label.</p><button className="mt-4 underline" disabled={busy} onClick={() => void run(async () => { const d = await mathPilot.me(); setData(d); const saved = d.sessions.find(s => s.id === row.id); if (saved) choose(saved) })}>Check availability</button></div>}
      {row.stage === 'complete' && <div className="my-6"><h2 className="text-2xl font-bold">Your evidence, not just a completion badge.</h2><p className="my-3">Independent transfer: {row.transfer_score}/2 · Delayed check: {row.retention_score}/2</p><p>{row.notice} Review the result with your teacher.</p></div>}
      <div className="mt-6 flex flex-wrap gap-5 border-t pt-5 text-sm"><button disabled={busy} onClick={() => void exportRecord()} className="underline">Export private evidence</button><button disabled={busy} onClick={() => void remove()} className="text-red-700 underline">Delete pilot data</button><span>Expires {new Date(row.expires_at).toLocaleDateString()}</span></div>
    </section>}
    <footer className="mt-7 rounded-2xl border border-orange-100 p-5"><h2 className="font-bold">Worth sharing? Let someone discover it too.</h2><p className="my-2">Share the activity—not your scores or personal information. No rewards or learning access depend on sharing.</p><Link className="font-semibold text-orange-700 underline" to="/discover/volume">Open the shareable discovery →</Link></footer>
  </div></main>
}
