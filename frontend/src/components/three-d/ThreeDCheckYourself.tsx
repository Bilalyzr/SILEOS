/**
 * ThreeDCheckYourself (2026-09-05): under a 3D lesson in the course player.
 * Lists the published match-and-verify tasks built on the lesson's model and
 * plays one inline — explore first, then prove it. Scores go to the task's
 * own attempt endpoint (server-graded, path-aware) and into the mastery graph.
 */
import * as React from 'react'
import { threeDTasksAPI, TASK_TYPE_INFO, type ThreeDTask } from '@/api/threeDTasks'
import { ThreeDTaskPlayer } from './tasks/ThreeDTaskPlayer'

export function ThreeDCheckYourself({ modelId }: { modelId: number }) {
  const [tasks, setTasks] = React.useState<ThreeDTask[] | null>(null)
  const [active, setActive] = React.useState<number | null>(null)
  React.useEffect(() => { threeDTasksAPI.forModel(modelId).then(setTasks).catch(() => setTasks([])) }, [modelId])
  if (!tasks || tasks.length === 0) return null
  return (
    <div className="mt-4 rounded-xl border border-orange-200 bg-gradient-to-br from-orange-50 via-white to-amber-50 p-4" data-testid="check-yourself">
      <p className="text-sm font-semibold text-gray-900">Check yourself on this model</p>
      <p className="text-xs text-gray-600 mb-2">Explore first, then prove it — your path (reasoned vs trial-and-error) is part of the picture.</p>
      <div className="flex flex-wrap gap-2">
        {tasks.map((t) => (
          <button key={t.id} type="button" onClick={() => setActive(active === t.id ? null : t.id)}
            className={`px-3 py-1.5 rounded-full text-xs border ${active === t.id ? 'si-gradient text-white border-transparent' : 'glass-panel text-gray-800 hover:bg-white'}`}>
            {t.title} · {TASK_TYPE_INFO[t.task_type]?.label || t.task_type} · {t.max_score} marks
          </button>
        ))}
      </div>
      {active && <div className="mt-3"><ThreeDTaskPlayer taskId={active} /></div>}
    </div>
  )
}

export default ThreeDCheckYourself
