import { useCallback, useEffect, useMemo, useState } from 'react'
import { Check, ChevronRight, Eye, EyeOff, Plus, Rocket, Save, X } from 'lucide-react'
import { codingAPI, type CodingChallengeDefinition, type CodingCourse, type CodingLanguage, type CodingTestCaseDraft, type EditorChallenge } from '@/api/coding'
import { plannerError } from '@/api/planner'
import { PageHeader, PageLayout } from '@/components/design-system/PageLayout'

const LANGUAGES: Array<{ id: CodingLanguage; label: string }> = [
  { id: 'python', label: 'Python' }, { id: 'javascript', label: 'JavaScript' },
  { id: 'typescript', label: 'TypeScript' }, { id: 'java', label: 'Java' },
  { id: 'cpp', label: 'C++' }, { id: 'c', label: 'C' },
]
const inputClass = 'mt-1 w-full rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm outline-none focus:border-violet-500 focus:ring-2 focus:ring-violet-100'
const blankCase = (visibility: 'sample' | 'hidden' = 'hidden'): CodingTestCaseDraft => ({ visibility, input_text: '', expected_output: '', comparison: 'trimmed', weight: 1 })
const blankDefinition = (): CodingChallengeDefinition => ({
  title: '', problem_statement: '', input_format: '', output_format: '', constraints_text: '',
  allowed_languages: ['python'], starter_code: { python: '' }, time_limit_ms: 2000,
  memory_limit_mb: 256, max_source_bytes: 65536, max_attempts: 20,
  test_cases: [blankCase('sample'), blankCase('hidden')],
})

export default function CodingStudioPage() {
  const [courses, setCourses] = useState<CodingCourse[]>([])
  const [courseId, setCourseId] = useState(0)
  const [challenges, setChallenges] = useState<EditorChallenge[]>([])
  const [selected, setSelected] = useState<EditorChallenge | null>(null)
  const [draft, setDraft] = useState<CodingChallengeDefinition>(blankDefinition)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')

  useEffect(() => {
    let active = true
    codingAPI.editorCourses().then((data) => {
      if (!active) return
      setCourses(data)
      setCourseId(data[0]?.id || 0)
    }).catch((reason) => active && setError(plannerError(reason))).finally(() => active && setLoading(false))
    return () => { active = false }
  }, [])

  const reload = useCallback(async () => {
    if (!courseId) { setChallenges([]); return }
    setChallenges(await codingAPI.editorChallenges(courseId))
  }, [courseId])

  useEffect(() => {
    setSelected(null)
    setDraft(blankDefinition())
    setError('')
    if (courseId) void reload().catch((reason) => setError(plannerError(reason)))
  }, [courseId, reload])

  const edit = (challenge: EditorChallenge) => {
    setSelected(challenge)
    setDraft({
      title: challenge.title, problem_statement: challenge.problem_statement,
      input_format: challenge.input_format, output_format: challenge.output_format,
      constraints_text: challenge.constraints_text, allowed_languages: [...challenge.allowed_languages],
      starter_code: { ...challenge.starter_code }, time_limit_ms: challenge.time_limit_ms,
      memory_limit_mb: challenge.memory_limit_mb, max_source_bytes: challenge.max_source_bytes,
      max_attempts: challenge.max_attempts,
      test_cases: challenge.test_cases.map((test) => ({ ...test })),
    })
    setError('')
    setMessage('')
  }

  const reset = () => { setSelected(null); setDraft(blankDefinition()); setError(''); setMessage('') }
  const isLocked = Boolean(selected && selected.status !== 'draft')
  const hasHidden = useMemo(() => draft.test_cases.some((test) => test.visibility === 'hidden'), [draft.test_cases])

  const mutate = async (action: () => Promise<unknown>, success: string) => {
    setBusy(true); setError(''); setMessage('')
    try { await action(); await reload(); setMessage(success); return true }
    catch (reason) { setError(plannerError(reason)); return false }
    finally { setBusy(false) }
  }

  const save = async (event: React.FormEvent) => {
    event.preventDefault()
    const result = selected
      ? await mutate(() => codingAPI.update(selected.id, { ...draft, version: selected.version }), 'Challenge changes saved.')
      : await mutate(async () => { const created = await codingAPI.create(courseId, draft); setSelected(created) }, 'Draft challenge created.')
    if (result) {
      const fresh = await codingAPI.editorChallenges(courseId)
      setChallenges(fresh)
      const current = fresh.find((item) => item.id === selected?.id) || fresh[0]
      if (current) edit(current)
    }
  }

  const lifecycle = async (challenge: EditorChallenge, action: 'publish' | 'retire') => {
    if (await mutate(() => codingAPI.action(challenge.id, challenge.version, action), action === 'publish' ? 'Challenge published to enrolled learners.' : 'Challenge retired.')) {
      const fresh = await codingAPI.editorChallenges(courseId)
      setChallenges(fresh)
      const current = fresh.find((item) => item.id === challenge.id) || null
      if (current) edit(current)
    }
  }

  const toggleLanguage = (language: CodingLanguage) => {
    setDraft((current) => {
      if (current.allowed_languages.includes(language)) {
        if (current.allowed_languages.length === 1) return current
        const starter = { ...current.starter_code }; delete starter[language]
        return { ...current, allowed_languages: current.allowed_languages.filter((item) => item !== language), starter_code: starter }
      }
      return { ...current, allowed_languages: [...current.allowed_languages, language], starter_code: { ...current.starter_code, [language]: '' } }
    })
  }

  const patchCase = (index: number, patch: Partial<CodingTestCaseDraft>) => setDraft((current) => ({ ...current, test_cases: current.test_cases.map((test, testIndex) => testIndex === index ? { ...test, ...patch } : test) }))
  const removeCase = (index: number) => setDraft((current) => ({ ...current, test_cases: current.test_cases.filter((_, testIndex) => testIndex !== index) }))

  return <PageLayout
    className="rd-screen rd-screen-instructor-coding-studio"
    header={<PageHeader><div>
      <p className="text-xs font-semibold uppercase tracking-[0.2em] text-violet-600">Utporul · Assessment engine</p>
      <h1 className="dash-h1 mt-1">Coding Studio</h1>
      <p className="mt-2 max-w-3xl text-slate-600">Author versioned coding problems, keep hidden answers inside SashaInfinity, and publish to enrolled learners.</p>
    </div><button type="button" onClick={reset} disabled={!courseId} className="si-btn-primary inline-flex items-center gap-2"><Plus className="h-4 w-4" />New challenge</button></PageHeader>}
  >
    <div className="glass-panel mb-5 rounded-2xl p-4">
      <label className="text-sm font-medium text-slate-800">Utporul course
        <select value={courseId} onChange={(event) => setCourseId(Number(event.target.value))} className={`${inputClass} max-w-xl`}>
          {courses.length === 0 && <option value={0}>No editable Utporul courses</option>}
          {courses.map((course) => <option key={course.id} value={course.id}>{course.title} · {course.status}</option>)}
        </select>
      </label>
    </div>

    {error && <div role="alert" className="mb-4 rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</div>}
    {message && <div className="mb-4 rounded-xl border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-700">{message}</div>}

    <div className="grid gap-5 xl:grid-cols-[320px_minmax(0,1fr)]">
      <aside className="glass-panel h-fit rounded-2xl p-4">
        <div className="flex items-center justify-between"><h2 className="font-semibold text-slate-950">Challenges</h2><span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-600">{challenges.length}</span></div>
        <div className="mt-3 space-y-2">
          {loading && <p className="text-sm text-slate-500">Loading…</p>}
          {!loading && challenges.length === 0 && <p className="rounded-xl bg-slate-50 p-4 text-sm text-slate-500">Start with a draft. Publishing requires at least one hidden test.</p>}
          {challenges.map((challenge) => <button type="button" key={challenge.id} onClick={() => edit(challenge)} className={`w-full rounded-xl border p-3 text-left transition ${selected?.id === challenge.id ? 'border-violet-300 bg-violet-50' : 'border-slate-100 bg-white hover:border-slate-200'}`}>
            <div className="flex items-center justify-between gap-2"><span className="font-medium text-slate-900">{challenge.title}</span><ChevronRight className="h-4 w-4 text-slate-400" /></div>
            <div className="mt-2 flex items-center gap-2 text-xs"><StatusBadge status={challenge.status} /><span className="text-slate-500">v{challenge.version} · {challenge.test_cases.length} tests</span></div>
          </button>)}
        </div>
      </aside>

      <form onSubmit={(event) => void save(event)} className="glass-panel rounded-2xl p-5 sm:p-7">
        <div className="flex flex-wrap items-start justify-between gap-4 border-b border-slate-100 pb-5">
          <div><h2 className="text-xl font-semibold text-slate-950">{selected ? selected.title : 'New coding challenge'}</h2><p className="mt-1 text-sm text-slate-500">{isLocked ? 'Published definitions are immutable. Retire this version and create a new draft to change it.' : 'Save as draft, review every case, then publish.'}</p></div>
          <div className="flex gap-2">
            {selected?.status === 'draft' && <button type="button" disabled={busy || !hasHidden} onClick={() => void lifecycle(selected, 'publish')} className="inline-flex items-center gap-2 rounded-xl bg-emerald-600 px-4 py-2 text-sm font-semibold text-white disabled:opacity-40"><Rocket className="h-4 w-4" />Publish</button>}
            {selected?.status === 'published' && <button type="button" disabled={busy} onClick={() => void lifecycle(selected, 'retire')} className="rounded-xl border border-slate-200 px-4 py-2 text-sm font-semibold text-slate-700">Retire</button>}
          </div>
        </div>

        <fieldset disabled={isLocked || busy || !courseId} className="mt-6 space-y-6 disabled:opacity-70">
          <div className="grid gap-4 md:grid-cols-2">
            <label className="text-sm font-medium text-slate-800 md:col-span-2">Challenge title<input required minLength={3} maxLength={200} className={inputClass} value={draft.title} onChange={(event) => setDraft({ ...draft, title: event.target.value })} /></label>
            <label className="text-sm font-medium text-slate-800 md:col-span-2">Problem statement<textarea required minLength={10} rows={7} className={inputClass} value={draft.problem_statement} onChange={(event) => setDraft({ ...draft, problem_statement: event.target.value })} /></label>
            <label className="text-sm font-medium text-slate-800">Input format<textarea rows={3} className={inputClass} value={draft.input_format} onChange={(event) => setDraft({ ...draft, input_format: event.target.value })} /></label>
            <label className="text-sm font-medium text-slate-800">Output format<textarea rows={3} className={inputClass} value={draft.output_format} onChange={(event) => setDraft({ ...draft, output_format: event.target.value })} /></label>
            <label className="text-sm font-medium text-slate-800 md:col-span-2">Constraints<textarea rows={3} className={inputClass} value={draft.constraints_text} onChange={(event) => setDraft({ ...draft, constraints_text: event.target.value })} /></label>
          </div>

          <section>
            <h3 className="font-semibold text-slate-950">Languages & starter code</h3>
            <div className="mt-3 flex flex-wrap gap-2">{LANGUAGES.map((language) => {
              const active = draft.allowed_languages.includes(language.id)
              return <button type="button" key={language.id} onClick={() => toggleLanguage(language.id)} className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-sm ${active ? 'border-violet-300 bg-violet-50 text-violet-800' : 'border-slate-200 bg-white text-slate-500'}`}>{active && <Check className="h-3.5 w-3.5" />}{language.label}</button>
            })}</div>
            <div className="mt-4 grid gap-4 lg:grid-cols-2">{draft.allowed_languages.map((language) => <label key={language} className="text-sm font-medium text-slate-800">{LANGUAGES.find((item) => item.id === language)?.label} starter<textarea rows={5} spellCheck={false} className={`${inputClass} font-mono`} value={draft.starter_code[language] || ''} onChange={(event) => setDraft({ ...draft, starter_code: { ...draft.starter_code, [language]: event.target.value } })} /></label>)}</div>
          </section>

          <section>
            <h3 className="font-semibold text-slate-950">Execution limits</h3>
            <div className="mt-3 grid gap-4 sm:grid-cols-3">
              <NumberField label="Time limit (ms)" value={draft.time_limit_ms} min={100} max={15000} onChange={(value) => setDraft({ ...draft, time_limit_ms: value })} />
              <NumberField label="Memory (MB)" value={draft.memory_limit_mb} min={16} max={1024} onChange={(value) => setDraft({ ...draft, memory_limit_mb: value })} />
              <NumberField label="Attempts per learner" value={draft.max_attempts} min={1} max={500} onChange={(value) => setDraft({ ...draft, max_attempts: value })} />
            </div>
          </section>

          <section>
            <div className="flex flex-wrap items-center justify-between gap-3"><div><h3 className="font-semibold text-slate-950">Test cases</h3><p className="mt-1 text-sm text-slate-500">Hidden expected outputs remain inside the LMS trust boundary.</p></div><button type="button" onClick={() => setDraft({ ...draft, test_cases: [...draft.test_cases, blankCase()] })} className="inline-flex items-center gap-2 rounded-lg border border-slate-200 px-3 py-2 text-sm font-medium"><Plus className="h-4 w-4" />Add test</button></div>
            <div className="mt-4 space-y-4">{draft.test_cases.map((test, index) => <div key={index} className="rounded-2xl border border-slate-200 bg-slate-50/70 p-4">
              <div className="flex items-center justify-between gap-3"><div className="flex items-center gap-2 font-medium text-slate-900">{test.visibility === 'hidden' ? <EyeOff className="h-4 w-4 text-amber-600" /> : <Eye className="h-4 w-4 text-emerald-600" />}Test {index + 1}</div><button type="button" aria-label={`Remove test ${index + 1}`} disabled={draft.test_cases.length === 1} onClick={() => removeCase(index)} className="rounded-lg p-1.5 text-slate-400 hover:bg-red-50 hover:text-red-600 disabled:opacity-30"><X className="h-4 w-4" /></button></div>
              <div className="mt-3 grid gap-3 md:grid-cols-2"><label className="text-xs font-medium uppercase tracking-wider text-slate-500">Visibility<select className={inputClass} value={test.visibility} onChange={(event) => patchCase(index, { visibility: event.target.value as 'sample' | 'hidden' })}><option value="sample">Sample · visible</option><option value="hidden">Hidden · private</option></select></label><label className="text-xs font-medium uppercase tracking-wider text-slate-500">Comparison<select className={inputClass} value={test.comparison} onChange={(event) => patchCase(index, { comparison: event.target.value as CodingTestCaseDraft['comparison'] })}><option value="trimmed">Trim trailing whitespace</option><option value="tokens">Token comparison</option><option value="exact">Exact output</option></select></label><label className="text-xs font-medium uppercase tracking-wider text-slate-500">Input<textarea rows={4} className={`${inputClass} font-mono normal-case tracking-normal`} value={test.input_text} onChange={(event) => patchCase(index, { input_text: event.target.value })} /></label><label className="text-xs font-medium uppercase tracking-wider text-slate-500">Expected output<textarea required rows={4} className={`${inputClass} font-mono normal-case tracking-normal`} value={test.expected_output} onChange={(event) => patchCase(index, { expected_output: event.target.value })} /></label></div>
            </div>)}</div>
          </section>
        </fieldset>
        {!isLocked && <div className="mt-6 flex justify-end"><button type="submit" disabled={busy || !courseId} className="si-btn-primary inline-flex items-center gap-2"><Save className="h-4 w-4" />{busy ? 'Saving…' : selected ? 'Save changes' : 'Create draft'}</button></div>}
      </form>
    </div>
  </PageLayout>
}

function StatusBadge({ status }: { status: EditorChallenge['status'] }) {
  const classes = status === 'published' ? 'bg-emerald-50 text-emerald-700' : status === 'retired' ? 'bg-slate-100 text-slate-600' : 'bg-amber-50 text-amber-700'
  return <span className={`rounded-full px-2 py-0.5 font-medium capitalize ${classes}`}>{status}</span>
}

function NumberField({ label, value, min, max, onChange }: { label: string; value: number; min: number; max: number; onChange: (value: number) => void }) {
  return <label className="text-sm font-medium text-slate-800">{label}<input type="number" required value={value} min={min} max={max} className={inputClass} onChange={(event) => onChange(Number(event.target.value))} /></label>
}
