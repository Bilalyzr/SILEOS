/**
 * Client-side mirror of backend/app/schemas/lab_config.parse_formula.
 * Used by ReactionLab to count atoms live as the student edits coefficients.
 * Grading is parameter-based: element totals equal on both sides AND the
 * coefficient set is in lowest terms (which is exactly the stored key).
 */
export type ElementCounts = Record<string, number>

export function parseFormula(formula: string): ElementCounts {
  const stack: ElementCounts[] = [{}]
  let i = 0
  const n = formula.length
  while (i < n) {
    const c = formula[i]
    if (c === '(') {
      stack.push({})
      i += 1
    } else if (c === ')') {
      if (stack.length === 1) throw new Error(`unbalanced ')' in ${formula}`)
      i += 1
      const m = /^\d+/.exec(formula.slice(i))
      const mult = m ? parseInt(m[0], 10) : 1
      i += m ? m[0].length : 0
      const top = stack.pop() as ElementCounts
      const parent = stack[stack.length - 1]
      for (const [el, cnt] of Object.entries(top)) parent[el] = (parent[el] || 0) + cnt * mult
    } else {
      const m = /^([A-Z][a-z]?)(\d*)/.exec(formula.slice(i))
      if (!m) throw new Error(`cannot parse ${formula} at ${i}`)
      const el = m[1]
      const num = m[2] ? parseInt(m[2], 10) : 1
      const cur = stack[stack.length - 1]
      cur[el] = (cur[el] || 0) + num
      i += m[0].length
    }
  }
  if (stack.length !== 1) throw new Error(`unbalanced '(' in ${formula}`)
  return stack[0]
}

export function elementTotals(formulas: string[], coefficients: number[]): ElementCounts {
  const totals: ElementCounts = {}
  formulas.forEach((f, idx) => {
    const coef = coefficients[idx] || 0
    for (const [el, cnt] of Object.entries(parseFormula(f))) totals[el] = (totals[el] || 0) + cnt * coef
  })
  return totals
}

export function gcdAll(nums: number[]): number {
  const gcd = (a: number, b: number): number => (b === 0 ? a : gcd(b, a % b))
  return nums.reduce((g, x) => gcd(g, Math.abs(x)), 0)
}

export interface BalanceCheck {
  balanced: boolean
  lowestTerms: boolean
  left: ElementCounts
  right: ElementCounts
  /** elements whose counts differ, for feedback */
  off: string[]
}

export function checkBalance(
  reactants: string[],
  products: string[],
  coefficients: number[],
): BalanceCheck {
  const left = elementTotals(reactants, coefficients.slice(0, reactants.length))
  const right = elementTotals(products, coefficients.slice(reactants.length))
  const elements = Array.from(new Set([...Object.keys(left), ...Object.keys(right)])).sort()
  const off = elements.filter((el) => (left[el] || 0) !== (right[el] || 0))
  const balanced = off.length === 0 && coefficients.every((c) => Number.isInteger(c) && c >= 1)
  return { balanced, lowestTerms: gcdAll(coefficients) === 1, left, right, off }
}

/** Pretty subscript formula for display: H2O -> H₂O (digits only; parentheses kept). */
export function subscriptFormula(formula: string): string {
  const subs: Record<string, string> = { '0': '₀', '1': '₁', '2': '₂', '3': '₃', '4': '₄', '5': '₅', '6': '₆', '7': '₇', '8': '₈', '9': '₉' }
  return formula.replace(/\d/g, (d) => subs[d] || d)
}
