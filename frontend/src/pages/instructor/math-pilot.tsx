import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { mathPilot, type MathData, type MathEvidence, type MathReview } from '@/api/math-pilot'
import { plannerError } from '@/api/planner'
import '@/styles/math-pilot.css'

export default function MathPilotTeacher() {
  const [data, setData] = useState<MathData | null>(null)
  const [course, setCourse] = useState(0)
  const [review, setReview] = useState<MathReview | null>(null)
  const [items, setItems] = useState<MathEvidence[]>([])
  const [note, setNote] = useState('')
  const [content, setContent] = useState(false)
  const [privacy, setPrivacy] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [offset, setOffset] = useState(0)
  useEffect(() => { void mathPilot.me().then(d => { setData(d); setCourse(d.courses[0]?.id || 0) }).catch(e => setError(plannerError(e))) }, [])
  const load = useCallback(async () => {
    if (!course) return
    const [r, e] = await Promise.all([mathPilot.review(course), mathPilot.evidence(course, offset)])
    setReview(r); setItems(e.items)
  }, [course, offset])
  useEffect(() => {
    let active = true
    setReview(null); setItems([]); setContent(false); setPrivacy(false); setNote('')
    if (course) void Promise.all([mathPilot.review(course), mathPilot.evidence(course, offset)]).then(([r, e]) => {
      if (active) { setReview(r); setItems(e.items) }
    }).catch(e => { if (active) setError(plannerError(e)) })
    return () => { active = false }
  }, [course, offset])
  const run = async (action: () => Promise<void>) => {
    setBusy(true); setError('')
    try { await action(); await load() } catch (e) { setError(plannerError(e)) } finally { setBusy(false) }
  }
  return <main className="sasha-math-page min-h-screen bg-gradient-to-br from-orange-50 via-white to-amber-50 p-5 text-slate-900 md:p-8"><div className="mx-auto max-w-5xl">
    <header className="math-hero mb-7 rounded-3xl bg-gradient-to-r from-orange-600 to-amber-500 p-7 text-white"><p className="font-semibold">SashaInfinity · Educator workspace</p><h1 className="mt-3 text-3xl font-bold">From answers to useful support</h1><p className="mt-3">Review the volume pilot. Inspect evidence. Keep the teaching decision yours.</p></header>
    <div className="mb-5 flex gap-5"><Link className="text-orange-700 underline" to="/instructor/interventions">Existing intervention queue</Link><Link className="text-orange-700 underline" to="/discover/volume">Preview & share public explorer</Link></div>
    {error && <p role="alert" className="my-4 rounded-xl bg-red-50 p-4 text-red-800">{error}</p>}
    <label htmlFor="review-course">Your course</label><select id="review-course" className="si-input my-3 w-full" disabled={busy} value={course} onChange={e => { setCourse(Number(e.target.value)); setOffset(0) }}>{data?.courses.map(c => <option key={c.id} value={c.id}>{c.title}</option>)}</select>
    {data && !data.courses.length && <p>Create a course or ask its owner to add you as a collaborator first.</p>}
    {review && <section className="rounded-2xl border border-orange-200 bg-white p-6">
      <h2 className="text-xl font-bold">Educator release gate · {review.approved ? 'Enabled' : 'Not enabled'}</h2>
      <p className="my-3">Pilot only: review mathematical correctness, wording, age suitability and school/parent data arrangements. Approval is your recorded review, not independent certification. Data expires after 90 days; deletion is available to learners.</p>
      <details className="my-4"><summary className="cursor-pointer font-semibold text-orange-800">Review the complete task sequence, rules and answer keys</summary><pre className="mt-3 max-h-96 overflow-auto whitespace-pre-wrap rounded-xl bg-orange-50 p-4 text-sm">{JSON.stringify(review.material, null, 2)}</pre></details>
      {review.review_note && <p className="my-3">Previous review: {review.review_note}</p>}
      <label className="my-3 flex gap-3"><input type="checkbox" checked={content} onChange={e => setContent(e.target.checked)} />I reviewed the tasks, answer keys, explanations and suitability for this class.</label>
      <label className="my-3 flex gap-3"><input type="checkbox" checked={privacy} onChange={e => setPrivacy(e.target.checked)} />Required school/parent arrangements and student-data handling have been reviewed.</label>
      <label className="block">Review note<textarea className="si-input my-2 w-full" value={note} maxLength={2000} onChange={e => setNote(e.target.value)} placeholder="Record suitability, restrictions and review context. Do not put student personal details here." /></label>
      <div className="flex flex-wrap gap-3"><button disabled={busy || !content || !privacy || note.trim().length < 10} className="rounded-xl bg-gradient-to-r from-orange-600 to-amber-600 px-5 py-3 font-semibold text-white disabled:opacity-50" onClick={() => void run(() => mathPilot.approve(course, review.version, note))}>Approve this version</button><button disabled={busy || !review.approved} className="rounded-xl border border-orange-300 px-5 py-3 disabled:opacity-50" onClick={() => void run(() => mathPilot.pause(course))}>Pause new learning steps</button></div>
    </section>}
    <section className="my-7"><div className="flex items-center justify-between"><h2 className="text-2xl font-bold">Learning evidence</h2><button disabled={busy} className="text-orange-700 underline" onClick={() => void run(async () => {})}>Refresh evidence</button></div><p className="my-3">Tentative hypotheses, not diagnoses. Confidence is not calibrated. Event counts are not independent learners; these results cannot establish that an intervention caused improvement.</p>
      {!items.length && <p className="rounded-xl bg-orange-50 p-5">No attempts on this page yet. Enable the pilot and direct enrolled students to /math-pilot.</p>}
      <div className="space-y-4">{items.map(row => <EvidenceCard key={`${row.id}:${row.sequence}`} row={row} busy={busy} onReview={(intervention, reason) => run(() => mathPilot.override(row, intervention, reason))} />)}</div>
      <div className="mt-4 flex gap-5"><button disabled={busy || offset === 0} onClick={() => setOffset(Math.max(0, offset-100))}>Previous</button><span>Records {offset+1}–{offset+items.length}</span><button disabled={busy || items.length < 100} onClick={() => setOffset(offset+100)}>Next</button></div>
    </section>
  </div></main>
}

function EvidenceCard({ row, busy, onReview }: { row: MathEvidence; busy: boolean; onReview: (intervention: string, reason: string) => Promise<void> }) {
  const [intervention, setIntervention] = useState(row.intervention || 'layers')
  const [note, setNote] = useState('')
  return <article className="rounded-2xl border border-orange-200 bg-white p-5">
    <h3 className="font-bold">Learner #{row.learner_id} · {row.stage}</h3><p className="my-2">{row.hypothesis_note || 'Diagnostic evidence pending.'}</p>
    <p>Independent transfer: {row.transfer_score === null ? 'Pending' : `${row.transfer_score}/2`} · Delayed check: {row.retention_score === null ? 'Pending' : `${row.retention_score}/2`}</p>
    {row.stage === 'build' && <div className="my-4 rounded-xl bg-orange-50 p-4"><label>Choose support<select className="si-input my-2 w-full" value={intervention} onChange={e => setIntervention(e.target.value)}><option value="layers">Counting layers</option><option value="multiplication">Equal groups / multiplication</option><option value="language">Wording and dimensions</option></select></label><label>Why change the recommendation?<textarea className="si-input my-2 w-full" maxLength={2000} value={note} onChange={e => setNote(e.target.value)} /></label><button disabled={busy || note.trim().length < 10} className="rounded-xl bg-orange-700 px-4 py-2 text-white disabled:opacity-50" onClick={() => void onReview(intervention, note)}>Save teacher override</button></div>}
    <details className="mt-4"><summary className="cursor-pointer text-orange-800">Inspect recorded answers and teacher decisions</summary><pre className="mt-3 overflow-auto whitespace-pre-wrap rounded-xl bg-slate-50 p-4 text-xs">{JSON.stringify(row.events, null, 2)}</pre></details>
  </article>
}
