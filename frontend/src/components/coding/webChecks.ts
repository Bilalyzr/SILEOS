/**
 * HTML and CSS challenges. Matches backend/app/services/web_checks.py and
 * code-judge-worker/web_check.py.
 *
 * A web test stores a check as JSON in `input_text` and the expected value in
 * `expected_output`. The judge renders the learner's page (scripts off, network
 * blocked) and reads the value the check asks for.
 */
import type { CodingLanguage } from '@/api/coding'

export const WEB_LANGUAGES: readonly CodingLanguage[] = ['html', 'css']

export type CheckKind = 'exists' | 'count' | 'text' | 'attr' | 'css'

export interface WebCheck {
  kind: CheckKind
  selector: string
  property?: string
  attribute?: string
}

export const CHECK_KINDS: Array<{ id: CheckKind; label: string; hint: string }> = [
  { id: 'text', label: 'Text of element', hint: 'Welcome' },
  { id: 'css', label: 'Style of element', hint: '#7c3aed or 32px' },
  { id: 'exists', label: 'Element exists', hint: 'true or false' },
  { id: 'count', label: 'Number of elements', hint: '3' },
  { id: 'attr', label: 'Attribute of element', hint: '/about' },
]

export function isWebLanguage(language: CodingLanguage): boolean {
  return WEB_LANGUAGES.includes(language)
}

export function isWebChallenge(languages: CodingLanguage[]): boolean {
  return languages.some(isWebLanguage)
}

export function encodeCheck(check: WebCheck): string {
  const out: WebCheck = { kind: check.kind, selector: check.selector.trim() }
  if (check.kind === 'css') out.property = (check.property || '').trim().toLowerCase()
  if (check.kind === 'attr') out.attribute = (check.attribute || '').trim()
  return JSON.stringify(out)
}

export function decodeCheck(text: string): WebCheck | null {
  try {
    const data = JSON.parse(text)
    if (!data || typeof data !== 'object' || typeof data.selector !== 'string') return null
    if (!CHECK_KINDS.some((kind) => kind.id === data.kind)) return null
    return data as WebCheck
  } catch {
    return null
  }
}

/** A plain-language line for a check, shown to learners for sample tests. */
export function describeCheck(check: WebCheck, expected: string): string {
  const target = `\`${check.selector}\``
  switch (check.kind) {
    case 'text': return `The text of ${target} is “${expected}”`
    case 'css': return `${target} has ${check.property}: ${expected}`
    case 'exists': return expected.trim() === 'false' ? `There is no ${target}` : `The page has ${target}`
    case 'count': return `The page has ${expected} × ${target}`
    case 'attr': return `${target} has ${check.attribute}="${expected}"`
  }
}

/** What is still missing from a check before it can be saved. Empty when complete. */
export function checkProblem(check: WebCheck | null): string {
  if (!check) return 'Choose what to check.'
  if (!check.selector.trim()) return 'Add a CSS selector, for example h1 or .btn.'
  if (check.kind === 'css' && !(check.property || '').trim()) return 'Add the CSS property, for example color.'
  if (check.kind === 'attr' && !(check.attribute || '').trim()) return 'Add the attribute name, for example href.'
  return ''
}

/**
 * The page the learner's work produces: their HTML, or the instructor's page
 * with their CSS added. Same rule the judge uses.
 */
export function buildPreviewDocument(language: CodingLanguage, source: string, pageHtml: string): string {
  if (language === 'html') return source
  const style = `<style>\n${source.replace(/<\/style/gi, '<\\/style')}\n</style>`
  const index = pageHtml.toLowerCase().indexOf('</head>')
  return index === -1 ? style + pageHtml : pageHtml.slice(0, index) + style + pageHtml.slice(index)
}
