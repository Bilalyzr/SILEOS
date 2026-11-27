import { describe, it, expect, afterEach } from 'vitest'
import { render, screen, fireEvent, cleanup } from '@testing-library/react'
import { useState } from 'react'
import type { CodingChallengeDefinition, CodingTestCaseDraft } from '@/api/coding'
import { blankChallenge } from '../ChallengeCreator'
import { WebCheckFields, toggleChallengeLanguage, webProblems } from '../WebCheckFields'
import { buildPreviewDocument, checkProblem, decodeCheck, describeCheck, encodeCheck } from '../webChecks'

const blankTests = (): CodingTestCaseDraft[] => [
  { visibility: 'sample', input_text: '', expected_output: '', comparison: 'trimmed', weight: 1 },
  { visibility: 'hidden', input_text: '', expected_output: '', comparison: 'trimmed', weight: 1 },
]

describe('web checks', () => {
  it('round-trips a check and keeps only the fields its kind needs', () => {
    const text = encodeCheck({ kind: 'css', selector: ' h1 ', property: 'Color', attribute: 'x' })
    expect(JSON.parse(text)).toEqual({ kind: 'css', selector: 'h1', property: 'color' })
    expect(decodeCheck(text)).toEqual({ kind: 'css', selector: 'h1', property: 'color' })
    expect(decodeCheck('2 3')).toBeNull()
    expect(decodeCheck('{"kind":"style","selector":"h1"}')).toBeNull()
  })

  it('describes checks for learners', () => {
    expect(describeCheck({ kind: 'text', selector: 'h1' }, 'Welcome')).toBe('The text of `h1` is “Welcome”')
    expect(describeCheck({ kind: 'css', selector: '.btn', property: 'color' }, '#fff')).toBe('`.btn` has color: #fff')
    expect(describeCheck({ kind: 'exists', selector: 'nav' }, 'true')).toBe('The page has `nav`')
    expect(describeCheck({ kind: 'attr', selector: 'a', attribute: 'href' }, '/about')).toBe('`a` has href="/about"')
  })

  it('reports what a check is missing', () => {
    expect(checkProblem({ kind: 'text', selector: '' })).toMatch(/selector/)
    expect(checkProblem({ kind: 'css', selector: 'h1' })).toMatch(/property/)
    expect(checkProblem({ kind: 'attr', selector: 'a' })).toMatch(/attribute/)
    expect(checkProblem({ kind: 'count', selector: 'li' })).toBe('')
  })

  it('builds the preview the way the judge does, and keeps CSS inside its style tag', () => {
    expect(buildPreviewDocument('html', '<h1>Hi</h1>', '')).toBe('<h1>Hi</h1>')
    const page = '<html><head><title>x</title></head><body><h1>Hi</h1></body></html>'
    const doc = buildPreviewDocument('css', 'h1{color:red}</style><script>alert(1)</script>', page)
    expect(doc).toContain('<style>\nh1{color:red}<\\/style><script>alert(1)</script>\n</style></head>')
    expect(doc.indexOf('<style>')).toBeLessThan(doc.indexOf('</head>'))
    expect(buildPreviewDocument('css', 'p{}', '<p>no head</p>')).toBe('<style>\np{}\n</style><p>no head</p>')
  })
})

describe('language switching', () => {
  it('replaces programming languages with HTML/CSS and resets the tests', () => {
    const start = { ...blankChallenge(), test_cases: [{ ...blankTests()[0], input_text: '2 3', expected_output: '5' }] }
    const web = toggleChallengeLanguage(start, 'css', blankTests)
    expect(web.allowed_languages).toEqual(['css'])
    expect(web.starter_code).toEqual({ css: '', html: '' })
    expect(web.test_cases).toHaveLength(2)
    expect(web.test_cases[0].input_text).toBe('')

    const both = toggleChallengeLanguage(web, 'html', blankTests)
    expect(both.allowed_languages).toEqual(['css', 'html'])
    const back = toggleChallengeLanguage(both, 'python', blankTests)
    expect(back.allowed_languages).toEqual(['python'])
  })

  it('keeps the page HTML while CSS is still selected', () => {
    let draft: CodingChallengeDefinition = toggleChallengeLanguage(blankChallenge(), 'css', blankTests)
    draft = toggleChallengeLanguage(draft, 'html', blankTests)
    draft = { ...draft, starter_code: { ...draft.starter_code, html: '<h1>Page</h1>' } }
    const cssOnly = toggleChallengeLanguage(draft, 'html', blankTests)
    expect(cssOnly.allowed_languages).toEqual(['css'])
    expect(cssOnly.starter_code.html).toBe('<h1>Page</h1>')
  })

  it('blocks publishing a CSS challenge without page HTML or with incomplete checks', () => {
    const draft = toggleChallengeLanguage(blankChallenge(), 'css', blankTests)
    const problems = webProblems(draft)
    expect(problems[0]).toMatch(/page HTML/)
    expect(problems).toContain('Test 1: Add a CSS selector, for example h1 or .btn.')
  })
})

describe('WebCheckFields', () => {
  afterEach(() => cleanup())

  function Harness() {
    const [test, setTest] = useState<CodingTestCaseDraft>(blankTests()[1])
    return <>
      <WebCheckFields test={test} index={0} onChange={(patch) => setTest((current) => ({ ...current, ...patch }))} />
      <output data-testid="stored">{test.input_text}|{test.expected_output}</output>
    </>
  }

  it('stores a style check as JSON and the expected value separately', () => {
    render(<Harness />)
    fireEvent.change(screen.getByLabelText('Test 1 checks'), { target: { value: 'css' } })
    fireEvent.change(screen.getByLabelText('Test 1 selector'), { target: { value: 'h1' } })
    fireEvent.change(screen.getByLabelText('Test 1 CSS property'), { target: { value: 'color' } })
    fireEvent.change(screen.getByLabelText('Test 1 expected value'), { target: { value: '#7c3aed' } })
    expect(screen.getByTestId('stored')).toHaveTextContent('{"kind":"css","selector":"h1","property":"color"}|#7c3aed')
  })
})
