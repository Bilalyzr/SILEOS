/**
 * Standalone student play route — /games/:id/play (spec §6). The backend's
 * play gate (games.py:_gate_play) does all authorization; this page hosts
 * GamePlayer and translates the two gated failure modes into friendly
 * guidance instead of a raw error string:
 *   - 403 "not enrolled" -> guidance + a link back to the course, when the
 *     link carries a course-context ?courseId= (there is no student-facing
 *     endpoint that maps a game back to its course, so the breadcrumb is
 *     only shown when the caller supplied one).
 *   - 404 "not found" (also returned for drafts, spec: 404 hides drafts
 *     entirely) -> a generic "not found" message, no enrollment wording.
 * GamePlayer itself keeps handling the loading/generic-error/game states;
 * this page only intercepts the play-fetch failure to add the guidance.
 */
import * as React from 'react'
import { useParams, useSearchParams, Link } from 'react-router-dom'
import { ChevronLeft, Lock, SearchX } from 'lucide-react'
import { GamePlayer } from '@/components/games/GamePlayer'
import { getGamePlay } from '@/api/games'
import { courseAPI } from '@/api/course'

type GateState = 'checking' | 'ok' | 'forbidden' | 'not_found'

export const GamePlayPage: React.FC = () => {
  const { id } = useParams<{ id: string }>()
  const [searchParams] = useSearchParams()
  const courseId = searchParams.get('courseId')
  const gameId = Number(id)
  const validId = Number.isInteger(gameId) && gameId > 0

  const [gate, setGate] = React.useState<GateState>('checking')
  const [courseTitle, setCourseTitle] = React.useState<string | null>(null)

  // Probe the play gate once up front so a 403/404 can be replaced with
  // friendly guidance instead of GamePlayer's generic error string.
  // GamePlayer re-fetches the same payload itself when the gate passes —
  // a second call to the same idempotent GET, not a behavior change.
  React.useEffect(() => {
    if (!validId) return
    let cancelled = false
    setGate('checking')
    getGamePlay(gameId)
      .then(() => { if (!cancelled) setGate('ok') })
      .catch((err: any) => {
        if (cancelled) return
        const status = err?.response?.status
        setGate(status === 403 ? 'forbidden' : 'not_found')
      })
    return () => { cancelled = true }
  }, [gameId, validId])

  React.useEffect(() => {
    if (!courseId) return
    let cancelled = false
    courseAPI.getCourse(courseId)
      .then((course: any) => {
        if (!cancelled) setCourseTitle(course?.post_title || course?.title || null)
      })
      .catch(() => {
        // Breadcrumb is a nice-to-have — fall back to a generic course link.
      })
    return () => { cancelled = true }
  }, [courseId])

  if (!validId) {
    return <div className="p-8 text-center text-red-600">Invalid game link.</div>
  }

  return (
    <div className="max-w-3xl mx-auto min-h-[70vh] py-6 px-4">
      {courseId && (
        <Link
          to={`/courses/${courseId}/learn`}
          className="inline-flex items-center gap-1 text-sm text-gray-500 hover:text-gray-800 mb-4"
        >
          <ChevronLeft className="w-4 h-4" />
          Back to {courseTitle || 'course'}
        </Link>
      )}

      {gate === 'forbidden' ? (
        <div className="flex flex-col items-center justify-center text-center p-8 min-h-[50vh]">
          <Lock className="w-10 h-10 text-amber-500 mb-3" />
          <h2 className="text-lg font-semibold text-gray-900 mb-1">You're not enrolled in this game's course</h2>
          <p className="text-sm text-gray-500 mb-4">
            Enroll in the course that offers this game to play it.
          </p>
          {courseId ? (
            <Link
              to={`/courses/${courseId}`}
              className="inline-flex items-center gap-1 text-sm font-medium text-blue-600 hover:text-blue-800"
            >
              Go to course
            </Link>
          ) : (
            <Link
              to="/my-courses"
              className="inline-flex items-center gap-1 text-sm font-medium text-blue-600 hover:text-blue-800"
            >
              View my courses
            </Link>
          )}
        </div>
      ) : gate === 'not_found' ? (
        <div className="flex flex-col items-center justify-center text-center p-8 min-h-[50vh]">
          <SearchX className="w-10 h-10 text-gray-400 mb-3" />
          <h2 className="text-lg font-semibold text-gray-900 mb-1">Game not found</h2>
          <p className="text-sm text-gray-500">
            This game may have been removed or is no longer available.
          </p>
        </div>
      ) : gate === 'checking' ? (
        <div className="min-h-[60vh]" />
      ) : (
        <GamePlayer gameId={gameId} className="min-h-[60vh]" />
      )}
    </div>
  )
}

export default GamePlayPage
