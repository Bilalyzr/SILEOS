import type { CodingChallengeDefinition, CodingLanguage, CodingTestCaseDraft } from '@/api/coding'
import { CHECK_KINDS, checkProblem, decodeCheck, encodeCheck, isWebChallenge, isWebLanguage, type CheckKind, type WebCheck } from './webChecks'

const field = 'mt-1 w-full rounded-md border border-gray-300 px-2 py-1.5 text-sm text-gray-900'

export function checkOf(test: CodingTestCaseDraft): WebCheck {
  return decodeCheck(test.input_text) || { kind: 'text', selector: '' }
}

/** Editor for one HTML/CSS check: what to read from the page and the value it must have. */
export function WebCheckFields({ test, index, onChange }: {
  test: CodingTestCaseDraft
  index: number
  onChange: (patch: Partial<CodingTestCaseDraft>) => void
}) {
  const check = checkOf(test)
  const kind = CHECK_KINDS.find((item) => item.id === check.kind) || CHECK_KINDS[0]
  const update = (patch: Partial<WebCheck>) => onChange({ input_text: encodeCheck({ ...check, ...patch }) })
  return (
    <div className="mt-2 grid gap-2 sm:grid-cols-2">
      <label className="block text-xs font-medium text-gray-600">Test {index + 1} checks
        <select value={check.kind} onChange={(event) => update({ kind: event.target.value as CheckKind })} className={field}>
          {CHECK_KINDS.map((item) => <option key={item.id} value={item.id}>{item.label}</option>)}
        </select>
      </label>
      <label className="block text-xs font-medium text-gray-600">Test {index + 1} selector
        <input value={check.selector} placeholder="h1, .btn, nav a" onChange={(event) => update({ selector: event.target.value })} className={`${field} font-mono`} />
      </label>
      {check.kind === 'css' && (
        <label className="block text-xs font-medium text-gray-600">Test {index + 1} CSS property
          <input value={check.property || ''} placeholder="color" onChange={(event) => update({ property: event.target.value })} className={`${field} font-mono`} />
        </label>
      )}
      {check.kind === 'attr' && (
        <label className="block text-xs font-medium text-gray-600">Test {index + 1} attribute
          <input value={check.attribute || ''} placeholder="href" onChange={(event) => update({ attribute: event.target.value })} className={`${field} font-mono`} />
        </label>
      )}
      <label className="block text-xs font-medium text-gray-600">Test {index + 1} expected value
        <input value={test.expected_output} placeholder={kind.hint} onChange={(event) => onChange({ expected_output: event.target.value })} className={`${field} font-mono`} />
      </label>
      {check.kind === 'css' && <p className="text-xs text-gray-500 sm:col-span-2">Colours match in any form: #7c3aed, rgb(124, 58, 237) or a colour name.</p>}
    </div>
  )
}

/**
 * Language switch rule: HTML/CSS challenges are checked in a browser, so they
 * cannot be mixed with programming languages. Picking one kind clears the other
 * and resets the tests, because the test format differs.
 */
export function toggleChallengeLanguage(
  draft: CodingChallengeDefinition,
  language: CodingLanguage,
  blankTests: () => CodingTestCaseDraft[],
): CodingChallengeDefinition {
  const selected = draft.allowed_languages
  if (selected.includes(language)) {
    if (selected.length === 1) return draft
    const starter = { ...draft.starter_code }
    // Keep the page HTML while CSS is still selected.
    if (!(language === 'html' && selected.includes('css'))) delete starter[language]
    return { ...draft, allowed_languages: selected.filter((item) => item !== language), starter_code: starter }
  }
  const switchingKind = isWebLanguage(language) !== isWebChallenge(selected)
  if (switchingKind) {
    const starter: Partial<Record<CodingLanguage, string>> = { [language]: '' }
    if (language === 'css') starter.html = ''
    return { ...draft, allowed_languages: [language], starter_code: starter, test_cases: blankTests() }
  }
  const starter = { ...draft.starter_code, [language]: draft.starter_code[language] ?? '' }
  if (language === 'css' && starter.html === undefined) starter.html = ''
  return { ...draft, allowed_languages: [...selected, language], starter_code: starter }
}

/** Web-specific problems that block publishing. Empty when ready. */
export function webProblems(draft: CodingChallengeDefinition): string[] {
  if (!isWebChallenge(draft.allowed_languages)) return []
  const problems: string[] = []
  if (draft.allowed_languages.includes('css') && !(draft.starter_code.html || '').trim()) {
    problems.push('Add the page HTML that the learner’s CSS is applied to.')
  }
  draft.test_cases.forEach((test, index) => {
    const problem = checkProblem(checkOf(test))
    if (problem) problems.push(`Test ${index + 1}: ${problem}`)
  })
  return problems
}

/** Page HTML (and CSS starter) fields for a web challenge. */
export function WebStarterFields({ draft, onChange }: {
  draft: CodingChallengeDefinition
  onChange: (starter: Partial<Record<CodingLanguage, string>>) => void
}) {
  const hasCss = draft.allowed_languages.includes('css')
  const hasHtml = draft.allowed_languages.includes('html')
  const pageLabel = hasCss && hasHtml
    ? 'Page HTML (starting page for HTML answers; CSS answers are applied to it)'
    : hasCss ? 'Page HTML (the learner’s CSS is applied to this page)' : 'Starter HTML (optional)'
  return (
    <div className="mt-2 grid gap-2">
      <label className="block text-xs font-medium text-gray-600">{pageLabel}
        <textarea rows={6} spellCheck={false} value={draft.starter_code.html || ''} onChange={(event) => onChange({ ...draft.starter_code, html: event.target.value })} className={`${field} font-mono`} />
      </label>
      {hasCss && (
        <label className="block text-xs font-medium text-gray-600">CSS starter (optional)
          <textarea rows={3} spellCheck={false} value={draft.starter_code.css || ''} onChange={(event) => onChange({ ...draft.starter_code, css: event.target.value })} className={`${field} font-mono`} />
        </label>
      )}
    </div>
  )
}
