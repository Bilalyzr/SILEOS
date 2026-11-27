import { useEffect, useState } from 'react'
import { createPortal } from 'react-dom'
import {
  codingAPI,
  type CodingChallengeDefinition,
  type CodingLanguage,
  type CodingTestCaseDraft,
  type EditorChallenge,
} from '@/api/coding'
import { plannerError } from '@/api/planner'

const LANGUAGES: Array<{ id: CodingLanguage; label: string }> = [
  { id: 'python', label: 'Python' },
  { id: 'javascript', label: 'JavaScript' },
  { id: 'typescript', label: 'TypeScript' },
  { id: 'cpp', label: 'C++' },
  { id: 'c', label: 'C' },
  { id: 'java', label: 'Java' },
]

const field = 'mt-1 w-full rounded-md border border-gray-300 px-2 py-1.5 text-sm text-gray-900'

const blankCase = (visibility: 'sample' | 'hidden'): CodingTestCaseDraft => ({
  visibility,
  input_text: '',
  expected_output: '',
  comparison: 'trimmed',
  weight: 1,
})

export function blankChallenge(): CodingChallengeDefinition {
  return {
    title: '',
    problem_statement: '',
    input_format: '',
    output_format: '',
    constraints_text: '',
    allowed_languages: ['python'],
    starter_code: { python: '' },
    time_limit_ms: 2000,
    memory_limit_mb: 256,
    max_source_bytes: 65536,
    max_attempts: 20,
    test_cases: [blankCase('sample'), blankCase('hidden')],
  }
}

/** What must be fixed before the challenge can be published. Empty when ready. */
export function publishProblems(draft: CodingChallengeDefinition): string[] {
  const problems: string[] = []
  if (draft.title.trim().length < 3) problems.push('Add a title of at least 3 characters.')
  if (draft.problem_statement.trim().length < 10) problems.push('Describe the problem in at least 10 characters.')
  if (draft.allowed_languages.length === 0) problems.push('Choose at least one language.')
  if (draft.test_cases.some((test) => test.expected_output.trim() === '')) problems.push('Every test needs an expected output.')
  if (!draft.test_cases.some((test) => test.visibility === 'hidden')) problems.push('Add at least one hidden test.')
  return problems
}

interface ChallengeCreatorProps {
  courseId: number
  onClose: () => void
  /** Called with the published challenge. */
  onCreated: (challenge: EditorChallenge) => void
}

/**
 * Create and publish a coding challenge without leaving the course builder.
 * Coding Studio remains the place for editing existing challenges and reports.
 */
export default function ChallengeCreator({ courseId, onClose, onCreated }: ChallengeCreatorProps) {
  const [draft, setDraft] = useState<CodingChallengeDefinition>(blankChallenge)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [showProblems, setShowProblems] = useState(false)
  const [savedDraft, setSavedDraft] = useState<EditorChallenge | null>(null)

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && !busy) onClose()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [busy, onClose])

  const problems = publishProblems(draft)

  const patchCase = (index: number, patch: Partial<CodingTestCaseDraft>) =>
    setDraft((current) => ({
      ...current,
      test_cases: current.test_cases.map((test, i) => (i === index ? { ...test, ...patch } : test)),
    }))

  const toggleLanguage = (language: CodingLanguage) =>
    setDraft((current) => {
      if (current.allowed_languages.includes(language)) {
        if (current.allowed_languages.length === 1) return current
        const starter = { ...current.starter_code }
        delete starter[language]
        return { ...current, allowed_languages: current.allowed_languages.filter((item) => item !== language), starter_code: starter }
      }
      return { ...current, allowed_languages: [...current.allowed_languages, language], starter_code: { ...current.starter_code, [language]: '' } }
    })

  const createAndPublish = async () => {
    setShowProblems(true)
    if (problems.length) return
    setBusy(true)
    setError('')
    try {
      // If an earlier attempt saved the draft but publishing failed, update that
      // draft instead of creating a second one.
      const saved = savedDraft
        ? await codingAPI.update(savedDraft.id, { ...draft, version: savedDraft.version })
        : await codingAPI.create(courseId, draft)
      setSavedDraft(saved)
      const published = await codingAPI.action(saved.id, saved.version, 'publish')
      onCreated(published)
    } catch (reason) {
      setError(plannerError(reason))
    } finally {
      setBusy(false)
    }
  }

  return createPortal(
    <div className="fixed inset-0 z-[1000] flex items-center justify-center bg-black/50 p-4" onMouseDown={(event) => { if (event.target === event.currentTarget && !busy) onClose() }}>
      <div role="dialog" aria-modal="true" aria-labelledby="challenge-creator-title" className="max-h-[92vh] w-full max-w-3xl overflow-y-auto rounded-xl bg-white p-5 shadow-xl">
        <div className="flex items-start justify-between gap-3">
          <div>
            <h3 id="challenge-creator-title" className="text-lg font-semibold text-gray-900">New coding challenge</h3>
            <p className="text-sm text-gray-500">It is published to this course and added to the lesson. Learners never see hidden tests.</p>
          </div>
          <button type="button" onClick={onClose} disabled={busy} className="rounded-md px-2 py-1 text-sm text-gray-500 hover:bg-gray-100">Close</button>
        </div>

        <div className="mt-4 space-y-4">
          <label className="block text-sm font-medium text-gray-700">Title
            <input value={draft.title} maxLength={200} onChange={(event) => setDraft({ ...draft, title: event.target.value })} className={field} />
          </label>
          <label className="block text-sm font-medium text-gray-700">Problem statement
            <textarea rows={4} value={draft.problem_statement} onChange={(event) => setDraft({ ...draft, problem_statement: event.target.value })} className={field} />
          </label>
          <div className="grid gap-3 sm:grid-cols-2">
            <label className="block text-sm font-medium text-gray-700">Input format (optional)
              <textarea rows={2} value={draft.input_format} onChange={(event) => setDraft({ ...draft, input_format: event.target.value })} className={field} />
            </label>
            <label className="block text-sm font-medium text-gray-700">Output format (optional)
              <textarea rows={2} value={draft.output_format} onChange={(event) => setDraft({ ...draft, output_format: event.target.value })} className={field} />
            </label>
          </div>

          <fieldset>
            <legend className="text-sm font-medium text-gray-700">Languages</legend>
            <div className="mt-1 flex flex-wrap gap-2">
              {LANGUAGES.map((language) => {
                const active = draft.allowed_languages.includes(language.id)
                return (
                  <button key={language.id} type="button" aria-pressed={active} onClick={() => toggleLanguage(language.id)} className={`rounded-full border px-3 py-1 text-sm ${active ? 'border-violet-400 bg-violet-50 text-violet-800' : 'border-gray-300 text-gray-600'}`}>
                    {language.label}
                  </button>
                )
              })}
            </div>
            <div className="mt-2 grid gap-2 sm:grid-cols-2">
              {draft.allowed_languages.map((language) => (
                <label key={language} className="block text-xs font-medium text-gray-600">
                  {LANGUAGES.find((item) => item.id === language)?.label} starter code (optional)
                  <textarea rows={3} spellCheck={false} value={draft.starter_code[language] || ''} onChange={(event) => setDraft({ ...draft, starter_code: { ...draft.starter_code, [language]: event.target.value } })} className={`${field} font-mono`} />
                </label>
              ))}
            </div>
          </fieldset>

          <div>
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-gray-700">Tests</span>
              <button type="button" onClick={() => setDraft({ ...draft, test_cases: [...draft.test_cases, blankCase('hidden')] })} className="rounded-md border border-gray-300 px-2 py-1 text-xs font-medium text-gray-700">Add test</button>
            </div>
            <div className="mt-2 space-y-2">
              {draft.test_cases.map((test, index) => (
                <div key={index} className="rounded-md border border-gray-200 p-3">
                  <div className="flex items-center justify-between gap-2">
                    <label className="text-xs font-medium text-gray-600">Test {index + 1}
                      <select value={test.visibility} onChange={(event) => patchCase(index, { visibility: event.target.value as 'sample' | 'hidden' })} className="ml-2 rounded-md border border-gray-300 px-2 py-1 text-xs">
                        <option value="sample">Sample (learners see it)</option>
                        <option value="hidden">Hidden (used for grading)</option>
                      </select>
                    </label>
                    <button type="button" disabled={draft.test_cases.length === 1} onClick={() => setDraft({ ...draft, test_cases: draft.test_cases.filter((_, i) => i !== index) })} className="text-xs text-red-600 disabled:opacity-40">Remove</button>
                  </div>
                  <div className="mt-2 grid gap-2 sm:grid-cols-2">
                    <label className="block text-xs font-medium text-gray-600">Test {index + 1} input
                      <textarea rows={2} spellCheck={false} value={test.input_text} onChange={(event) => patchCase(index, { input_text: event.target.value })} className={`${field} font-mono`} />
                    </label>
                    <label className="block text-xs font-medium text-gray-600">Test {index + 1} expected output
                      <textarea rows={2} spellCheck={false} value={test.expected_output} onChange={(event) => patchCase(index, { expected_output: event.target.value })} className={`${field} font-mono`} />
                    </label>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {showProblems && problems.length > 0 && (
            <ul role="alert" className="list-disc space-y-1 rounded-md bg-amber-50 p-3 pl-7 text-sm text-amber-800">
              {problems.map((problem) => <li key={problem}>{problem}</li>)}
            </ul>
          )}
          {error && <p role="alert" className="rounded-md bg-red-50 p-3 text-sm text-red-700">{error}</p>}

          <div className="flex justify-end gap-2">
            <button type="button" onClick={onClose} disabled={busy} className="rounded-md border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700">Cancel</button>
            <button type="button" onClick={() => void createAndPublish()} disabled={busy} className="rounded-md bg-violet-600 px-4 py-2 text-sm font-semibold text-white hover:bg-violet-500 disabled:opacity-50">
              {busy ? 'Publishing…' : 'Create and publish'}
            </button>
          </div>
        </div>
      </div>
    </div>,
    document.body,
  )
}
