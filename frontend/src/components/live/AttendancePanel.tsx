import * as React from 'react'
import { CheckCircle2, XCircle, MinusCircle } from 'lucide-react'
import { fetchAttendance, type AttendanceRowOut } from '@/api/liveClasses'

const ATTENDANCE_POLL_INTERVAL_MS = 15_000

export interface AttendancePanelProps {
  classId: number
  className?: string
}

function presentIcon(present: boolean | null) {
  if (present === true) return <CheckCircle2 className="h-3.5 w-3.5 text-success-600 flex-shrink-0" />
  if (present === false) return <XCircle className="h-3.5 w-3.5 text-danger-500 flex-shrink-0" />
  return <MinusCircle className="h-3.5 w-3.5 text-slate-300 flex-shrink-0" />
}

/**
 * Instructor dock "People" attendance rows — refreshed every 15s while the
 * console is open, per the plan's binding behavior. Rows come from
 * GET .../attendance (AttendanceSummaryOut.rows), which reflects
 * server-computed heartbeat accumulation live during the class.
 */
export const AttendancePanel: React.FC<AttendancePanelProps> = ({ classId, className = '' }) => {
  const [rows, setRows] = React.useState<AttendanceRowOut[]>([])
  const [totalParticipants, setTotalParticipants] = React.useState(0)
  const [loading, setLoading] = React.useState(true)
  const [error, setError] = React.useState<string | null>(null)

  const load = React.useCallback(async () => {
    try {
      setError(null)
      const summary = await fetchAttendance(classId)
      setRows(summary.rows)
      setTotalParticipants(summary.total_participants)
    } catch (err: any) {
      setError(err?.message || 'Failed to load attendance')
    } finally {
      setLoading(false)
    }
  }, [classId])

  React.useEffect(() => {
    load()
    const id = window.setInterval(load, ATTENDANCE_POLL_INTERVAL_MS)
    return () => window.clearInterval(id)
  }, [load])

  if (loading) {
    return <p className={`text-xs text-slate-400 ${className}`}>Loading attendance…</p>
  }

  if (error) {
    return <p className={`text-xs text-danger-600 ${className}`}>{error}</p>
  }

  return (
    <div className={`flex flex-col gap-2 ${className}`} data-testid="attendance-panel">
      <p className="text-xs text-slate-500">{totalParticipants} participant{totalParticipants !== 1 ? 's' : ''}</p>
      {rows.length === 0 ? (
        <p className="text-xs text-slate-400">No one has joined yet.</p>
      ) : (
        <ul className="flex flex-col gap-1 max-h-64 overflow-y-auto">
          {rows.map((row) => (
            <li
              key={row.user_id}
              className="flex items-center justify-between gap-2 rounded-md px-2 py-1.5 hover:bg-slate-50 text-xs"
            >
              <span className="flex items-center gap-1.5 min-w-0">
                {presentIcon(row.present)}
                <span className="truncate font-medium text-secondary-900">{row.name}</span>
              </span>
              <span className="text-slate-500 flex-shrink-0">{row.accumulated_minutes}m</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

export default AttendancePanel
