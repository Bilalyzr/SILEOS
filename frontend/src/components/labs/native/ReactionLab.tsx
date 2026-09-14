/**
 * Reaction Lab engine — balance chemical equations.
 * Parameter-based grading: a reaction scores 10 when the coefficient set is
 * element-balanced AND in lowest terms (that is exactly the stored key), no
 * matter how the student got there. Works with keyboard only; no WebGL.
 * All strings come from admin/instructor config and render as React text.
 */
import * as React from 'react'
import type { ReactionLabConfig } from '@/api/labs'
import { checkBalance, subscriptFormula } from './chemistry'

interface Props {
  config: ReactionLabConfig
  onFinish: (score: number, maxScore: number) => void
  finished?: boolean
}

type Status = 'idle' | 'wrong' | 'solved'

export function ReactionLab({ config, onFinish, finished = false }: Props) {
  const reactions = config.reactions
  const maxScore = reactions.length * 10
  const [coefs, setCoefs] = React.useState<number[][]>(() => reactions.map((r) => r.coefficients.map(() => 1)))
  const [status, setStatus] = React.useState<Status[]>(() => reactions.map(() => 'idle'))
  const [feedback, setFeedback] = React.useState<string[]>(() => reactions.map(() => ''))
  const [hintsShown, setHintsShown] = React.useState<boolean[]>(() => reactions.map(() => false))
  const [current, setCurrent] = React.useState(0)

  const solvedCount = status.filter((s) => s === 'solved').length
  const score = solvedCount * 10

  const setCoef = (ri: number, ci: number, value: number) => {
    if (status[ri] === 'solved' || finished) return
    const v = Number.isFinite(value) ? Math.max(1, Math.min(20, Math.round(value))) : 1
    setCoefs((prev) => prev.map((row, i) => (i === ri ? row.map((c, j) => (j === ci ? v : c)) : row)))
    setStatus((prev) => prev.map((s, i) => (i === ri && s === 'wrong' ? 'idle' : s)))
  }

  const check = (ri: number) => {
    const r = reactions[ri]
    const res = checkBalance(r.reactants.map((s) => s.formula), r.products.map((s) => s.formula), coefs[ri])
    if (res.balanced && res.lowestTerms) {
      setStatus((prev) => prev.map((s, i) => (i === ri ? 'solved' : s)))
      setFeedback((prev) => prev.map((f, i) => (i === ri ? 'Balanced! Every atom is accounted for.' : f)))
      return
    }
    let msg: string
    if (res.balanced && !res.lowestTerms) {
      msg = 'Balanced, but not in lowest terms — divide all coefficients by their common factor.'
    } else {
      msg = `Not balanced yet — check ${res.off.map((el) => `${el} (left ${res.left[el] || 0}, right ${res.right[el] || 0})`).join(', ')}.`
    }
    setStatus((prev) => prev.map((s, i) => (i === ri ? 'wrong' : s)))
    setFeedback((prev) => prev.map((f, i) => (i === ri ? msg : f)))
  }

  const r = reactions[current]
  const res = checkBalance(r.reactants.map((s) => s.formula), r.products.map((s) => s.formula), coefs[current])
  const elements = Array.from(new Set([...Object.keys(res.left), ...Object.keys(res.right)])).sort()

  const renderSide = (species: { formula: string; name: string }[], offset: number) =>
    species.map((sp, j) => {
      const ci = offset + j
      return (
        <React.Fragment key={`${sp.formula}-${ci}`}>
          {j > 0 && <span className="text-gray-400 mx-1">+</span>}
          <label className="inline-flex items-center gap-1">
            <span className="sr-only">Coefficient for {sp.name}</span>
            <input
              type="number"
              min={1}
              max={20}
              value={coefs[current][ci]}
              disabled={status[current] === 'solved' || finished}
              onChange={(e) => setCoef(current, ci, parseInt(e.target.value, 10))}
              className="w-12 px-1 py-1 text-center text-sm border border-gray-300 rounded-md focus:ring-2 focus:ring-emerald-500 disabled:bg-emerald-50"
            />
            <span className="font-mono text-lg" title={sp.name}>{subscriptFormula(sp.formula)}</span>
          </label>
        </React.Fragment>
      )
    })

  return (
    <div className="space-y-4">
      {config.intro && <p className="text-sm text-gray-600">{config.intro}</p>}

      <div className="flex flex-wrap gap-1.5" role="tablist" aria-label="Reactions">
        {reactions.map((_, i) => (
          <button
            key={i}
            type="button"
            role="tab"
            aria-selected={i === current}
            onClick={() => setCurrent(i)}
            className={`w-8 h-8 rounded-full text-xs font-semibold border ${
              i === current ? 'ring-2 ring-emerald-500' : ''
            } ${
              status[i] === 'solved'
                ? 'bg-emerald-600 text-white border-emerald-600'
                : status[i] === 'wrong'
                  ? 'bg-amber-100 text-amber-800 border-amber-300'
                  : 'bg-white text-gray-700 border-gray-300'
            }`}
          >
            {i + 1}
          </button>
        ))}
        <span className="ml-auto self-center text-sm text-gray-600">
          Score <strong>{score}</strong> / {maxScore}
        </span>
      </div>

      <div className="rounded-xl border border-gray-200 bg-white p-4">
        {r.description && <p className="text-xs text-gray-500 mb-2">{r.description}</p>}
        <div className="flex flex-wrap items-center gap-1 text-gray-900">
          {renderSide(r.reactants, 0)}
          <span className="mx-2 text-2xl text-emerald-600">→</span>
          {renderSide(r.products, r.reactants.length)}
        </div>

        <div className="mt-3 overflow-x-auto">
          <table className="text-xs text-gray-700">
            <thead>
              <tr>
                <th className="text-left pr-3 font-medium">Element</th>
                {elements.map((el) => <th key={el} className="px-2 font-mono">{el}</th>)}
              </tr>
            </thead>
            <tbody>
              <tr>
                <td className="pr-3">Left</td>
                {elements.map((el) => <td key={el} className="px-2 text-center">{res.left[el] || 0}</td>)}
              </tr>
              <tr>
                <td className="pr-3">Right</td>
                {elements.map((el) => (
                  <td key={el} className={`px-2 text-center ${(res.left[el] || 0) === (res.right[el] || 0) ? 'text-emerald-700' : 'text-red-600'}`}>
                    {res.right[el] || 0}
                  </td>
                ))}
              </tr>
            </tbody>
          </table>
        </div>

        <div className="mt-3 flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={() => check(current)}
            disabled={status[current] === 'solved' || finished}
            className="px-3 py-1.5 text-sm font-medium rounded-lg bg-emerald-600 text-white hover:bg-emerald-700 disabled:opacity-50"
          >
            {status[current] === 'solved' ? 'Solved' : 'Check balance'}
          </button>
          {r.hint && status[current] !== 'solved' && (
            <button
              type="button"
              onClick={() => setHintsShown((p) => p.map((h, i) => (i === current ? true : h)))}
              className="text-xs text-blue-600 hover:underline"
            >
              Show hint
            </button>
          )}
          {current < reactions.length - 1 && (
            <button type="button" onClick={() => setCurrent(current + 1)} className="ml-auto text-xs text-gray-600 hover:underline">
              Next reaction →
            </button>
          )}
        </div>
        {hintsShown[current] && r.hint && <p className="mt-2 text-xs text-blue-700">Hint: {r.hint}</p>}
        {feedback[current] && (
          <p className={`mt-2 text-sm ${status[current] === 'solved' ? 'text-emerald-700' : 'text-amber-700'}`} role="status">
            {feedback[current]}
          </p>
        )}
      </div>

      {!finished && (
        <div className="flex items-center justify-between">
          <p className="text-xs text-gray-500">{solvedCount} of {reactions.length} balanced</p>
          <button
            type="button"
            onClick={() => onFinish(score, maxScore)}
            className="px-4 py-2 text-sm font-semibold rounded-lg bg-gray-900 text-white hover:bg-black"
          >
            Finish lab
          </button>
        </div>
      )}
    </div>
  )
}

export default ReactionLab
