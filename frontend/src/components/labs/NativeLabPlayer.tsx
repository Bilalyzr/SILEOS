/**
 * NativeLabPlayer — routes a native lab (already fetched) to its engine and
 * records the advisory score. previewOnly (instructor preview) never POSTs a
 * result and never marks a lesson complete — same rule as GamePlayer.
 */
import * as React from 'react'
import toast from 'react-hot-toast'
import { submitLabResult, type IdentifyLabConfig, type LabDetail, type ReactionLabConfig } from '@/api/labs'
import { ReactionLab } from './native/ReactionLab'
import { IdentifyLab } from './native/IdentifyLab'

interface Props {
  lab: LabDetail
  previewOnly?: boolean
  onLessonComplete?: () => void
}

export function NativeLabPlayer({ lab, previewOnly = false, onLessonComplete }: Props) {
  const startedAt = React.useRef(Date.now())
  const [result, setResult] = React.useState<{ score: number; max: number; best?: number } | null>(null)
  const [submitting, setSubmitting] = React.useState(false)
  const [runKey, setRunKey] = React.useState(0)

  const handleFinish = async (score: number, maxScore: number) => {
    setResult({ score, max: maxScore })
    if (previewOnly) return
    setSubmitting(true)
    try {
      const duration = Math.max(0, Math.round((Date.now() - startedAt.current) / 1000))
      const res = await submitLabResult(lab.slug, score, duration)
      setResult({ score, max: maxScore, best: res.best_score })
      if (score > 0) onLessonComplete?.()
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || 'Could not save your lab result')
    } finally {
      setSubmitting(false)
    }
  }

  const restart = () => {
    startedAt.current = Date.now()
    setResult(null)
    setRunKey((k) => k + 1)
  }

  const engine = (() => {
    if (lab.native_template === 'reaction_lab' && lab.config) {
      return <ReactionLab key={runKey} config={lab.config as ReactionLabConfig} onFinish={handleFinish} finished={!!result} />
    }
    if (lab.native_template === 'identify_lab' && lab.config) {
      return <IdentifyLab key={runKey} config={lab.config as IdentifyLabConfig} onFinish={handleFinish} finished={!!result} />
    }
    return <p className="text-sm text-red-600">This lab's template is not supported by this app version.</p>
  })()

  return (
    <div className="space-y-4">
      {previewOnly && (
        <p className="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded px-2 py-1">
          Preview mode — scores are not saved.
        </p>
      )}
      {engine}
      {result && (
        <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-4 flex flex-wrap items-center gap-3">
          <div>
            <p className="font-semibold text-emerald-900">
              Lab finished: {result.score} / {result.max}
            </p>
            <p className="text-xs text-emerald-800">
              {submitting ? 'Saving…' : previewOnly ? 'Preview only.' : result.best !== undefined ? `Best so far: ${result.best}. Saved.` : ''}
            </p>
          </div>
          <button type="button" onClick={restart} className="ml-auto text-sm font-medium text-emerald-700 hover:underline">
            Try again
          </button>
        </div>
      )}
    </div>
  )
}

export default NativeLabPlayer
