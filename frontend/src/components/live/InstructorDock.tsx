import * as React from 'react'
import { Users, Vote, Timer as TimerIcon, Circle, MicOff, Lock, Unlock } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { AttendancePanel } from './AttendancePanel'
import { PollPanel } from './PollPanel'
import { RaiseHandList } from './RaiseHandList'
import { useLiveClassStore } from '@/store/liveClassStore'
import { startRecordingIntent, stopRecordingIntent, type LiveClassOut } from '@/api/liveClasses'

const PARTICIPANT_COUNT_POLL_MS = 10_000

type DockTab = 'people' | 'polls' | 'timer' | 'recording'

const TABS: { key: DockTab; label: string; icon: React.ComponentType<{ className?: string }> }[] = [
  { key: 'people', label: 'People', icon: Users },
  { key: 'polls', label: 'Polls', icon: Vote },
  { key: 'timer', label: 'Timer', icon: TimerIcon },
  { key: 'recording', label: 'Recording', icon: Circle },
]

function formatDuration(totalSeconds: number): string {
  const h = Math.floor(totalSeconds / 3600)
  const m = Math.floor((totalSeconds % 3600) / 60)
  const s = totalSeconds % 60
  const pad = (n: number) => String(n).padStart(2, '0')
  return h > 0 ? `${h}:${pad(m)}:${pad(s)}` : `${pad(m)}:${pad(s)}`
}

export interface InstructorDockProps {
  liveClass: LiveClassOut
  /** The live JitsiMeetExternalAPI instance, handed up from JitsiStage's
   * onApiReady — used for executeCommand calls (muteEveryone, toggleLobby,
   * startRecording/stopRecording, sendEndpointTextMessage). */
  jitsiApi: any
  className?: string
}

/**
 * Console dock: People (participant count + attendance + raise-hand +
 * mute-all/lobby toggle), Polls, Timer, Recording. All Jitsi moderation
 * commands go through the JitsiMeetExternalAPI instance passed down from
 * JitsiStage via onApiReady.
 */
export const InstructorDock: React.FC<InstructorDockProps> = ({ liveClass, jitsiApi, className = '' }) => {
  const [tab, setTab] = React.useState<DockTab>('people')
  const [participantCount, setParticipantCount] = React.useState(0)
  const [lobbyEnabled, setLobbyEnabled] = React.useState(
    Boolean(liveClass.settings?.lobby_enabled)
  )
  const [recordingBusy, setRecordingBusy] = React.useState(false)
  const [elapsedSeconds, setElapsedSeconds] = React.useState(0)

  const isRecording = useLiveClassStore((s) => s.isRecording)
  const connectionStatus = useLiveClassStore((s) => s.connectionStatus)

  // Participant count — 10s poll of the Jitsi API, per the plan's binding
  // behavior (getNumberOfParticipants), independent of the raise-hand store.
  React.useEffect(() => {
    if (!jitsiApi) return
    const poll = () => {
      try {
        const count = jitsiApi.getNumberOfParticipants?.()
        if (typeof count === 'number') setParticipantCount(count)
      } catch {
        // Jitsi API may be mid-teardown — ignore and retry next tick.
      }
    }
    poll()
    const id = window.setInterval(poll, PARTICIPANT_COUNT_POLL_MS)
    return () => window.clearInterval(id)
  }, [jitsiApi])

  // Elapsed-since-started timer, ticking every second.
  React.useEffect(() => {
    if (!liveClass.started_at) return
    const startedMs = new Date(liveClass.started_at).getTime()
    const tick = () => setElapsedSeconds(Math.max(0, Math.floor((Date.now() - startedMs) / 1000)))
    tick()
    const id = window.setInterval(tick, 1000)
    return () => window.clearInterval(id)
  }, [liveClass.started_at])

  const scheduledEndMs = new Date(liveClass.scheduled_end).getTime()
  const remainingToScheduledEnd = liveClass.started_at
    ? Math.max(0, Math.floor((scheduledEndMs - Date.now()) / 1000))
    : null

  const handleMuteAll = () => {
    try {
      jitsiApi?.executeCommand('muteEveryone', 'audio')
    } catch {
      // Best-effort — the conference may not be ready yet.
    }
  }

  const handleToggleLobby = () => {
    const next = !lobbyEnabled
    try {
      jitsiApi?.executeCommand('toggleLobby', next)
      setLobbyEnabled(next)
    } catch {
      // Best-effort — command may fail if not yet a moderator in the room.
    }
  }

  const handleToggleRecording = async () => {
    if (recordingBusy) return
    // Without a connected conference the Jitsi command throws internally
    // (null conference) — the old catch swallowed the API intent failure
    // but the executeCommand TypeError crashed the dock's event handler.
    if (!jitsiApi || connectionStatus !== 'connected') {
      window.console.warn('Recording: conference not connected yet')
      return
    }
    setRecordingBusy(true)
    try {
      if (isRecording) {
        await stopRecordingIntent(liveClass.id)
        jitsiApi?.executeCommand('stopRecording', 'file')
      } else {
        await startRecordingIntent(liveClass.id)
        jitsiApi?.executeCommand('startRecording', { mode: 'file' })
      }
    } catch {
      // Intent call failure surfaces via recordingStatusChanged not firing —
      // the switch simply won't flip; the instructor can retry.
    } finally {
      setRecordingBusy(false)
    }
  }

  return (
    <div className={`flex flex-col h-full rounded-lg border border-slate-200 bg-white overflow-hidden ${className}`}>
      <div className="flex border-b border-slate-100" role="tablist">
        {TABS.map(({ key, label, icon: Icon }) => (
          <button
            key={key}
            role="tab"
            aria-selected={tab === key}
            onClick={() => setTab(key)}
            className={`flex-1 flex items-center justify-center gap-1.5 px-2 py-2.5 text-xs font-medium border-b-2 transition-colors ${
              tab === key
                ? 'border-primary-500 text-primary-700'
                : 'border-transparent text-slate-500 hover:text-slate-700'
            }`}
          >
            <Icon className="h-3.5 w-3.5" />
            {label}
          </button>
        ))}
      </div>

      <div className="flex-1 overflow-y-auto p-4">
        {tab === 'people' && (
          <div className="flex flex-col gap-4">
            <div className="flex items-center justify-between">
              <p className="text-sm font-semibold text-secondary-900">
                {participantCount} in the room
              </p>
              <div className="flex gap-2">
                <Button size="sm" variant="outline" onClick={handleMuteAll}>
                  <MicOff className="h-3.5 w-3.5 mr-1" /> Mute all
                </Button>
                <Button size="sm" variant="outline" onClick={handleToggleLobby}>
                  {lobbyEnabled ? <Lock className="h-3.5 w-3.5 mr-1" /> : <Unlock className="h-3.5 w-3.5 mr-1" />}
                  {lobbyEnabled ? 'Lobby on' : 'Lobby off'}
                </Button>
              </div>
            </div>

            <div>
              <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">Raised hands</h4>
              <RaiseHandList />
            </div>

            <div>
              <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">Attendance</h4>
              <AttendancePanel classId={liveClass.id} />
            </div>
          </div>
        )}

        {tab === 'polls' && <PollPanel classId={liveClass.id} isModerator />}

        {tab === 'timer' && (
          <div className="flex flex-col items-center justify-center gap-4 py-8">
            <div className="text-center">
              <p className="text-xs text-slate-500 uppercase tracking-wide mb-1">Elapsed</p>
              <p className="text-3xl font-bold text-secondary-900 tabular-nums" data-testid="dock-elapsed">
                {formatDuration(elapsedSeconds)}
              </p>
            </div>
            {remainingToScheduledEnd !== null && (
              <div className="text-center">
                <p className="text-xs text-slate-500 uppercase tracking-wide mb-1">Scheduled end in</p>
                <p className="text-lg font-semibold text-slate-700 tabular-nums">
                  {formatDuration(remainingToScheduledEnd)}
                </p>
              </div>
            )}
          </div>
        )}

        {tab === 'recording' && (
          <div className="flex flex-col gap-4">
            <div className="flex items-center justify-between rounded-lg border border-slate-200 p-3">
              <div>
                <p className="text-sm font-semibold text-secondary-900">Recording</p>
                <p className="text-xs text-slate-500">
                  {isRecording ? 'This class is being recorded' : 'Not recording'}
                </p>
              </div>
              <button
                role="switch"
                aria-checked={isRecording}
                onClick={handleToggleRecording}
                disabled={recordingBusy}
                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors disabled:opacity-50 ${
                  isRecording ? 'bg-danger-500' : 'bg-slate-300'
                }`}
              >
                <span
                  className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                    isRecording ? 'translate-x-6' : 'translate-x-1'
                  }`}
                />
              </button>
            </div>
            {isRecording && (
              <p className="text-xs text-danger-700 bg-danger-50 border border-danger-200 rounded-md px-3 py-2 flex items-center gap-1.5">
                <Circle className="h-2.5 w-2.5 fill-danger-600 text-danger-600 animate-pulse" />
                Students see a "This class is being recorded" banner.
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

export default InstructorDock
