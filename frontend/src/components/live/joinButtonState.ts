/**
 * Pure Join-button state machine shared by the student list/join pages
 * (Task 7) and the instructor console/dashboard (Task 8 reuses this exact
 * module — see the plan's "Reuse the joinButtonState helper" note).
 *
 * Covers: locked (student, more than 15 min before start) / opens-in-Xm /
 * join (window open or class is live) / live / ended-no-recording /
 * watch-recording.
 */

export type JoinButtonAction = 'none' | 'join' | 'recording'

export interface JoinButtonState {
  label: string
  disabled: boolean
  action: JoinButtonAction
}

export interface JoinButtonClassInput {
  status: 'scheduled' | 'live' | 'ended' | 'cancelled' | string
  scheduled_start: string
  recording_status?: 'none' | 'requested' | 'processing' | 'available' | 'failed' | string
}

const STUDENT_JOIN_WINDOW_MINUTES = 15

function minutesUntil(target: Date, now: Date): number {
  return Math.ceil((target.getTime() - now.getTime()) / 60000)
}

/**
 * @param cls the class summary (status/scheduled_start/recording_status)
 * @param now current time (inject for testability)
 * @param isStaff true for the assigned instructor/admin — staff can join
 *   any time before the class ends (mirrors the backend's join-token
 *   window rule: "SCHEDULED joins allowed from T-15min for students,
 *   anytime for the instructor").
 */
export function joinButtonState(
  cls: JoinButtonClassInput,
  now: Date,
  isStaff = false
): JoinButtonState {
  if (cls.status === 'cancelled') {
    return { label: 'Cancelled', disabled: true, action: 'none' }
  }

  if (cls.status === 'live') {
    return { label: 'Join — LIVE', disabled: false, action: 'join' }
  }

  if (cls.status === 'ended') {
    if (cls.recording_status === 'available') {
      return { label: 'Watch recording', disabled: false, action: 'recording' }
    }
    return { label: 'Class ended', disabled: true, action: 'none' }
  }

  // status === 'scheduled'
  const start = new Date(cls.scheduled_start)

  if (isStaff) {
    return { label: 'Start class', disabled: false, action: 'join' }
  }

  const joinOpensAt = new Date(start.getTime() - STUDENT_JOIN_WINDOW_MINUTES * 60000)
  if (now >= joinOpensAt) {
    return { label: 'Join', disabled: false, action: 'join' }
  }

  const minsToOpen = minutesUntil(joinOpensAt, now)
  if (minsToOpen <= 1) {
    return { label: 'Opens in <1m', disabled: true, action: 'none' }
  }
  return { label: `Opens in ${minsToOpen}m`, disabled: true, action: 'none' }
}
