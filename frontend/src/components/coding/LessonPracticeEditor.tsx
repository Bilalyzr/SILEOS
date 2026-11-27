import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { codingAPI, type EditorChallenge, type LessonCodingBlock, type LessonCodingBlockInput } from '@/api/coding'
import { plannerError } from '@/api/planner'
import ChallengeCreator from './ChallengeCreator'

interface LessonPracticeEditorProps {
  courseId: number
  lessonId: number
}

interface Row {
  key: string
  challenge_slug: string
  /** Seconds as typed, or empty for "after the lesson". */
  position: string
  instructions: string
}

let rowCounter = 0
const newKey = () => `row-${++rowCounter}`

function toRow(block: LessonCodingBlock): Row {
  return {
    key: newKey(),
    challenge_slug: block.challenge_slug,
    position: block.position_seconds === null ? '' : String(block.position_seconds),
    instructions: block.instructions || '',
  }
}

/**
 * Curriculum editor section: attach published coding challenges to a lesson.
 * A timestamp (in seconds) makes the lesson pause there for practice. An empty
 * timestamp lists the challenge after the lesson.
 */
export default function LessonPracticeEditor({ courseId, lessonId }: LessonPracticeEditorProps) {
  const [challenges, setChallenges] = useState<EditorChallenge[]>([])
  const [rows, setRows] = useState<Row[]>([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState<{ kind: 'ok' | 'error'; text: string } | null>(null)
  const [loadError, setLoadError] = useState('')
  const [creating, setCreating] = useState(false)

  useEffect(() => {
    let active = true
    setLoading(true)
    setLoadError('')
    Promise.all([
      codingAPI.editorChallenges(courseId).catch((reason) => {
        // Show why the list is empty (for example, the course is not a Utporul course)
        // instead of implying there are simply no challenges.
        if (active) setLoadError(plannerError(reason))
        return [] as EditorChallenge[]
      }),
      codingAPI.lessonBlocks(courseId, lessonId).catch(() => [] as LessonCodingBlock[]),
    ]).then(([available, blocks]) => {
      if (!active) return
      setChallenges(available)
      setRows(blocks.map(toRow))
    }).finally(() => active && setLoading(false))
    return () => { active = false }
  }, [courseId, lessonId])

  const published = challenges.filter((challenge) => challenge.status === 'published')

  const update = (key: string, patch: Partial<Row>) => {
    setRows((prev) => prev.map((row) => (row.key === key ? { ...row, ...patch } : row)))
  }

  const add = () => {
    const first = published[0]
    if (!first) return
    setRows((prev) => [...prev, { key: newKey(), challenge_slug: first.slug, position: '', instructions: '' }])
  }

  const remove = (key: string) => setRows((prev) => prev.filter((row) => row.key !== key))

  const save = async () => {
    setMessage(null)
    const payload: LessonCodingBlockInput[] = []
    for (const [index, row] of rows.entries()) {
      const trimmed = row.position.trim()
      let position: number | null = null
      if (trimmed !== '') {
        const seconds = Number(trimmed)
        if (!Number.isInteger(seconds) || seconds < 0) {
          setMessage({ kind: 'error', text: `Practice ${index + 1}: the time must be a whole number of seconds, or empty.` })
          return
        }
        position = seconds
      }
      payload.push({ challenge_slug: row.challenge_slug, position_seconds: position, instructions: row.instructions.trim() })
    }
    setSaving(true)
    try {
      const saved = await codingAPI.saveLessonBlocks(courseId, lessonId, payload)
      setRows(saved.map(toRow))
      setMessage({ kind: 'ok', text: 'Practice blocks saved.' })
    } catch (reason) {
      setMessage({ kind: 'error', text: plannerError(reason) })
    } finally {
      setSaving(false)
    }
  }

  return <section className="space-y-3 rounded-lg border border-gray-200 bg-white p-4" aria-labelledby={`practice-editor-${lessonId}`}>
    <div className="flex flex-wrap items-center justify-between gap-2">
      <div>
        <h4 id={`practice-editor-${lessonId}`} className="text-sm font-semibold text-gray-900">Coding practice</h4>
        <p className="text-xs text-gray-500">Attach a published challenge. Add a time to pause the video there, or leave it empty to list it after the lesson.</p>
      </div>
      <div className="flex gap-2">
        <button type="button" onClick={() => setCreating(true)} disabled={loading || Boolean(loadError)} className="rounded-md bg-violet-600 px-3 py-1.5 text-sm font-semibold text-white hover:bg-violet-500 disabled:opacity-50">
          New challenge
        </button>
        <button type="button" onClick={add} disabled={loading || published.length === 0} className="rounded-md border border-gray-300 px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50">
          Add practice
        </button>
      </div>
    </div>
    {creating && (
      <ChallengeCreator
        courseId={courseId}
        onClose={() => setCreating(false)}
        onCreated={(challenge) => {
          setCreating(false)
          setChallenges((prev) => [...prev.filter((item) => item.id !== challenge.id), challenge])
          setRows((prev) => [...prev, { key: newKey(), challenge_slug: challenge.slug, position: '', instructions: '' }])
          setMessage({ kind: 'ok', text: `"${challenge.title}" is published and added below. Set a time if the video should pause there, then click Save practice.` })
        }}
      />
    )}

    {loading && <p className="text-sm text-gray-500">Loading…</p>}
    {!loading && loadError && <p role="alert" className="text-sm text-red-600">{loadError}</p>}
    {!loading && !loadError && published.length === 0 && (
      <p className="text-sm text-gray-500">
        This course has no published coding challenge yet. Click <strong>New challenge</strong> to create one here, or use{' '}
        <Link to={`/instructor/coding-studio?course=${courseId}`} className="font-medium text-violet-700 underline">
          Coding Studio
        </Link>{' '}
        for reports and editing.
      </p>
    )}

    {rows.map((row, index) => <div key={row.key} className="grid gap-2 rounded-md border border-gray-200 p-3 sm:grid-cols-[1fr_120px_auto]">
      <label className="text-xs font-medium text-gray-600">
        Challenge
        <select value={row.challenge_slug} onChange={(event) => update(row.key, { challenge_slug: event.target.value })} className="mt-1 w-full rounded-md border border-gray-300 px-2 py-1.5 text-sm text-gray-900">
          {published.map((challenge) => <option key={challenge.slug} value={challenge.slug}>{challenge.title}</option>)}
          {!published.some((challenge) => challenge.slug === row.challenge_slug) && <option value={row.challenge_slug}>{row.challenge_slug} (not published)</option>}
        </select>
      </label>
      <label className="text-xs font-medium text-gray-600">
        Time (seconds)
        <input inputMode="numeric" value={row.position} onChange={(event) => update(row.key, { position: event.target.value })} placeholder="After lesson" className="mt-1 w-full rounded-md border border-gray-300 px-2 py-1.5 text-sm text-gray-900" />
      </label>
      <div className="flex items-end">
        <button type="button" onClick={() => remove(row.key)} aria-label={`Remove practice ${index + 1}`} className="rounded-md px-2 py-1.5 text-sm text-red-600 hover:bg-red-50">Remove</button>
      </div>
      <label className="text-xs font-medium text-gray-600 sm:col-span-3">
        Instructions for the learner (optional)
        <textarea value={row.instructions} onChange={(event) => update(row.key, { instructions: event.target.value })} maxLength={2000} rows={2} className="mt-1 w-full rounded-md border border-gray-300 px-2 py-1.5 text-sm text-gray-900" />
      </label>
    </div>)}

    <div className="flex items-center justify-between gap-3">
      <p role="status" className={`text-sm ${message?.kind === 'error' ? 'text-red-600' : 'text-green-700'}`}>{message?.text ?? ''}</p>
      <button type="button" onClick={() => void save()} disabled={saving || loading} className="rounded-md bg-violet-600 px-4 py-2 text-sm font-semibold text-white hover:bg-violet-500 disabled:opacity-50">
        {saving ? 'Saving…' : 'Save practice'}
      </button>
    </div>
  </section>
}
