import { useEffect, useRef, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ArrowLeft, CheckCircle2, Clock3, Cpu, Loader2, Play, ShieldCheck, XCircle } from 'lucide-react'
import { codingAPI, type CodingLanguage, type CodingSubmission, type LearnerChallenge } from '@/api/coding'
import { plannerError } from '@/api/planner'

const terminal = new Set(['passed', 'failed', 'error', 'cancelled'])
const languageLabels: Record<CodingLanguage, string> = {
  python: 'Python', javascript: 'JavaScript', typescript: 'TypeScript', java: 'Java', cpp: 'C++', c: 'C',
}

export default function CodingWorkspacePage() {
  const { slug = '' } = useParams()
  const [challenge, setChallenge] = useState<LearnerChallenge | null>(null)
  const [language, setLanguage] = useState<CodingLanguage>('python')
  const [source, setSource] = useState('')
  const [submission, setSubmission] = useState<CodingSubmission | null>(null)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const pollRef = useRef<number | undefined>()

  useEffect(() => {
    let active = true
    codingAPI.learnerChallenge(slug)
      .then((data) => {
        if (!active) return
        setChallenge(data)
        const first = data.allowed_languages[0]
        setLanguage(first)
        setSource(data.starter_code[first] || '')
      })
      .catch((reason) => active && setError(plannerError(reason)))
      .finally(() => active && setLoading(false))
    return () => { active = false; window.clearTimeout(pollRef.current) }
  }, [slug])

  const chooseLanguage = (next: CodingLanguage) => {
    setLanguage(next)
    if (!source.trim() || source === challenge?.starter_code[language]) {
      setSource(challenge?.starter_code[next] || '')
    }
  }

  const poll = async (id: number) => {
    try {
      const next = await codingAPI.submission(id)
      setSubmission(next)
      if (!terminal.has(next.status)) pollRef.current = window.setTimeout(() => void poll(id), 1500)
      else setBusy(false)
    } catch (reason) {
      setError(plannerError(reason))
      setBusy(false)
    }
  }

  const submit = async () => {
    if (!source.trim()) return
    setBusy(true)
    setError('')
    setSubmission(null)
    try {
      const idempotencyKey = globalThis.crypto?.randomUUID?.() || `code-${Date.now()}-${Math.random()}`
      const queued = await codingAPI.submit(slug, language, source, idempotencyKey)
      setSubmission(queued)
      if (terminal.has(queued.status)) setBusy(false)
      else pollRef.current = window.setTimeout(() => void poll(queued.id), 700)
    } catch (reason) {
      setError(plannerError(reason))
      setBusy(false)
    }
  }

  if (loading) return <div className="min-h-screen bg-slate-950 p-8 text-slate-300">Loading coding workspace…</div>
  if (!challenge) return <div className="min-h-screen bg-slate-950 p-8 text-red-300">{error || 'Challenge not found.'}</div>
  const remaining = Math.max(0, challenge.max_attempts - challenge.attempts_used - (submission ? 1 : 0))

  return <main className="min-h-screen bg-[#080b12] text-slate-100">
    <header className="border-b border-white/10 bg-slate-950/90 px-4 py-3 backdrop-blur sm:px-6">
      <div className="mx-auto flex max-w-[1600px] flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <Link to="/coding" aria-label="Back to code practice" className="rounded-lg border border-white/10 p-2 text-slate-300 hover:bg-white/10"><ArrowLeft className="h-4 w-4" /></Link>
          <div><p className="text-xs font-semibold uppercase tracking-widest text-violet-400">Utporul judge</p><h1 className="font-semibold">{challenge.title}</h1></div>
        </div>
        <div className="flex gap-2 text-xs text-slate-300">
          <span className="rounded-full border border-white/10 px-3 py-1.5"><Clock3 className="mr-1 inline h-3.5 w-3.5" />{challenge.time_limit_ms} ms</span>
          <span className="rounded-full border border-white/10 px-3 py-1.5"><Cpu className="mr-1 inline h-3.5 w-3.5" />{challenge.memory_limit_mb} MB</span>
          <span className="rounded-full border border-white/10 px-3 py-1.5">{remaining} attempts left</span>
        </div>
      </div>
    </header>

    <div className="mx-auto grid max-w-[1600px] gap-0 lg:grid-cols-[minmax(320px,0.85fr)_minmax(500px,1.35fr)]">
      <section className="max-h-[calc(100vh-73px)] overflow-y-auto border-r border-white/10 p-5 sm:p-7">
        <h2 className="text-xl font-semibold">Problem</h2>
        <p className="mt-4 whitespace-pre-wrap text-sm leading-7 text-slate-300">{challenge.problem_statement}</p>
        {challenge.input_format && <InfoBlock title="Input format" text={challenge.input_format} />}
        {challenge.output_format && <InfoBlock title="Output format" text={challenge.output_format} />}
        {challenge.constraints_text && <InfoBlock title="Constraints" text={challenge.constraints_text} />}
        <div className="mt-7 space-y-4">
          <h3 className="font-semibold">Examples</h3>
          {challenge.sample_cases.map((sample, index) => <div key={sample.ordinal} className="rounded-xl border border-white/10 bg-black/25 p-4 text-sm">
            <p className="mb-3 text-xs font-semibold uppercase tracking-wider text-slate-500">Example {index + 1}</p>
            <pre className="overflow-x-auto text-emerald-300"><span className="text-slate-500">Input  </span>{sample.input_text || '(empty)'}</pre>
            <pre className="mt-2 overflow-x-auto text-violet-300"><span className="text-slate-500">Output </span>{sample.expected_output}</pre>
          </div>)}
        </div>
      </section>

      <section className="flex min-h-[calc(100vh-73px)] flex-col p-4 sm:p-6">
        <div className="mb-3 flex items-center justify-between gap-3">
          <select value={language} onChange={(event) => chooseLanguage(event.target.value as CodingLanguage)} className="rounded-lg border border-white/10 bg-slate-900 px-3 py-2 text-sm">
            {challenge.allowed_languages.map((item) => <option key={item} value={item}>{languageLabels[item]}</option>)}
          </select>
          <div className="flex items-center gap-2 text-xs text-emerald-300"><ShieldCheck className="h-4 w-4" />Network disabled · isolated execution</div>
        </div>
        <textarea aria-label="Source code" spellCheck={false} value={source} onChange={(event) => setSource(event.target.value)} className="min-h-[430px] flex-1 resize-none rounded-xl border border-white/10 bg-[#0d111a] p-5 font-mono text-sm leading-6 text-slate-100 outline-none focus:border-violet-500" />
        <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
          <p className="text-xs text-slate-500">Hidden expected outputs stay on the LMS and are never sent to the runner.</p>
          <button onClick={() => void submit()} disabled={busy || !source.trim() || remaining <= 0} className="inline-flex items-center gap-2 rounded-xl bg-violet-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-violet-500 disabled:cursor-not-allowed disabled:opacity-50">
            {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}{busy ? 'Evaluating…' : 'Submit attempt'}
          </button>
        </div>
        {error && <div role="alert" className="mt-4 rounded-xl border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-300">{error}</div>}
        {submission && <ResultPanel submission={submission} />}
      </section>
    </div>
  </main>
}

function InfoBlock({ title, text }: { title: string; text: string }) {
  return <div className="mt-6"><h3 className="text-sm font-semibold text-slate-100">{title}</h3><p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-slate-400">{text}</p></div>
}

function ResultPanel({ submission }: { submission: CodingSubmission }) {
  const waiting = submission.status === 'queued' || submission.status === 'running'
  const passed = submission.status === 'passed'
  return <div className={`mt-4 rounded-xl border p-4 ${passed ? 'border-emerald-500/30 bg-emerald-500/10' : waiting ? 'border-violet-500/30 bg-violet-500/10' : 'border-red-500/30 bg-red-500/10'}`}>
    <div className="flex items-center justify-between gap-3">
      <div className="flex items-center gap-2 font-semibold">{waiting ? <Loader2 className="h-5 w-5 animate-spin" /> : passed ? <CheckCircle2 className="h-5 w-5" /> : <XCircle className="h-5 w-5" />}<span className="capitalize">{submission.status.replace('_', ' ')}</span></div>
      {!waiting && <strong>{submission.score.toFixed(1)}%</strong>}
    </div>
    {!waiting && <p className="mt-2 text-sm opacity-80">Passed {submission.passed_cases} of {submission.total_cases} cases · attempt {submission.attempt_number}</p>}
    {submission.results.length > 0 && <div className="mt-3 flex flex-wrap gap-2">{submission.results.map((result, index) => <span key={`${result.test_case_id}-${index}`} className="rounded-full bg-black/20 px-2.5 py-1 text-xs">{result.visibility === 'hidden' ? `Hidden ${index + 1}` : `Sample ${index + 1}`}: {result.status.replace('_', ' ')}</span>)}</div>}
  </div>
}
