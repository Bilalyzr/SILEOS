/**
 * Instructor console: DevicePrecheck gate -> grid [JitsiStage | InstructorDock].
 * End class = confirm dialog -> end endpoint -> navigate to report.
 */
import * as React from 'react'
import { confirmDialog } from '@/components/ui/confirm'
import { useNavigate, useParams } from 'react-router-dom'
import { ArrowLeft, PhoneOff } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { DevicePrecheck } from '@/components/live/DevicePrecheck'
import { JitsiStage } from '@/components/live/JitsiStage'
import { InstructorDock } from '@/components/live/InstructorDock'
import { ErrorState } from '@/components/dashboard/primitives'
import { useAuth } from '@/hooks/use-auth'
import {
  getLiveClass, startLiveClass, endLiveClass, requestJoinToken,
  type LiveClassOut, type JoinTokenOut,
} from '@/api/liveClasses'

type Stage = 'loading' | 'precheck' | 'connecting' | 'in-call' | 'terminated' | 'error'

export function InstructorLiveClassConsolePage() {
  const { id } = useParams<{ id: string }>()
  const classId = Number(id)
  const navigate = useNavigate()
  const { fullName } = useAuth()

  const [stage, setStage] = React.useState<Stage>('loading')
  const [liveClass, setLiveClass] = React.useState<LiveClassOut | null>(null)
  const [tokenData, setTokenData] = React.useState<JoinTokenOut | null>(null)
  const [errorMessage, setErrorMessage] = React.useState<string | null>(null)
  const [ending, setEnding] = React.useState(false)
  const jitsiApiRef = React.useRef<any>(null)
  const [, forceRerender] = React.useState(0)

  React.useEffect(() => {
    const cancelled = false
    async function loadClass() {
      try {
        const data = await getLiveClass(classId)
        if (cancelled) return
        setLiveClass(data)
        // Ended/cancelled classes are terminal — walking the user through
        // the device check just to fail at /start with a raw 409
        // ("Cannot start a class in status ended") is a dead end.
        setStage(data.status === 'ended' || data.status === 'cancelled' ? 'terminated' : 'precheck')
      } catch (err: any) {
        if (cancelled) return
        setErrorMessage(err?.response?.data?.detail || err?.message || 'Failed to load this class')
        setStage('error')
      }
    }
    if (Number.isFinite(classId)) loadClass()
  }, [classId])

  const handleContinue = React.useCallback(async () => {
    setStage('connecting')
    setErrorMessage(null)
    try {
      // Idempotent — if already LIVE, the backend returns the current state.
      const started = await startLiveClass(classId)
      setLiveClass(started)
      const token = await requestJoinToken(classId)
      setTokenData(token)
      setStage('in-call')
    } catch (err: any) {
      const detail = err?.response?.data?.detail || err?.message || 'Failed to start this class'
      if (typeof detail === 'string' && /status (ended|cancelled)/i.test(detail)) {
        // The class ended while this console was open (ended elsewhere or
        // from another tab) — show the terminal state, not a raw 409.
        setLiveClass((c) => (c ? { ...c, status: /ended/i.test(detail) ? 'ended' : 'cancelled' } : c))
        setStage('terminated')
        return
      }
      setErrorMessage(typeof detail === 'string' ? detail : 'Failed to start this class')
      setStage('error')
    }
  }, [classId])

  const handleApiReady = React.useCallback((api: any) => {
    jitsiApiRef.current = api
    forceRerender((n) => n + 1) // trigger a render so InstructorDock receives the api instance
  }, [])

  const handleLeft = React.useCallback(() => {
    navigate('/instructor/live-classes')
  }, [navigate])

  const handleEndClass = React.useCallback(async () => {
    if (!await confirmDialog('End this class for everyone? Students will be disconnected and attendance will be finalized.')) {
      return
    }
    setEnding(true)
    try {
      await endLiveClass(classId)
      navigate(`/instructor/live-classes/${classId}/report`)
    } catch (err: any) {
      setErrorMessage(err?.response?.data?.detail || err?.message || 'Failed to end the class')
      setEnding(false)
    }
  }, [classId, navigate])

  if (!Number.isFinite(classId)) {
    return <ErrorState title="Invalid class" description="This live class link looks incorrect." />
  }

  if (stage === 'loading') {
    return (
      <div className="flex items-center justify-center min-h-[320px]">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-500" />
      </div>
    )
  }

  if (stage === 'terminated' && liveClass) {
    return (
      <div className="flex flex-col items-center justify-center gap-4 min-h-[320px] text-center">
        <h1 className="dash-h1 text-xl">{liveClass.title}</h1>
        <p className="text-sm text-slate-600">
          {liveClass.status === 'cancelled'
            ? 'This class was cancelled and can no longer be joined.'
            : 'This class has already ended.'}
        </p>
        <div className="flex gap-3">
          <Button variant="outline" onClick={() => navigate('/instructor/live-classes')}>
            <ArrowLeft className="h-4 w-4 mr-1.5" />
            Back to live classes
          </Button>
          <Button onClick={() => navigate(`/instructor/live-classes/${liveClass.id}/report`)}>
            View report
          </Button>
        </div>
      </div>
    )
  }

  if (stage === 'error') {
    return (
      <ErrorState
        title="Couldn't open the console"
        description={errorMessage || undefined}
        onRetry={() => window.location.reload()}
      />
    )
  }

  return (
    <div className="flex flex-col gap-4 h-full">
      <div className="flex items-center justify-between">
        <button
          onClick={() => navigate('/instructor/live-classes')}
          className="inline-flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-700 w-fit"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to live classes
        </button>
        {stage === 'in-call' && liveClass && (
          <Button variant="destructive" onClick={handleEndClass} disabled={ending}>
            <PhoneOff className="h-4 w-4 mr-1.5" />
            {ending ? 'Ending…' : 'End class'}
          </Button>
        )}
      </div>

      {liveClass && <h1 className="dash-h1 text-xl">{liveClass.title}</h1>}

      {stage === 'precheck' && (
        <div className="max-w-lg mx-auto w-full">
          <DevicePrecheck onContinue={handleContinue} />
        </div>
      )}

      {stage === 'connecting' && (
        <div className="flex items-center justify-center min-h-[320px]">
          <div className="flex flex-col items-center gap-3 text-slate-500">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-500" />
            <p className="text-sm">Starting the class…</p>
          </div>
        </div>
      )}

      {stage === 'in-call' && tokenData && liveClass && (
        <div className="grid grid-cols-1 lg:grid-cols-[1fr_360px] gap-4 h-[75vh] min-h-[480px]">
          <JitsiStage
            jitsiUrl={tokenData.jitsi_url}
            roomName={tokenData.room_name}
            jwt={tokenData.jwt}
            isModerator
            displayName={fullName || 'Instructor'}
            classId={classId}
            onApiReady={handleApiReady}
            onLeft={handleLeft}
          />
          <InstructorDock liveClass={liveClass} jitsiApi={jitsiApiRef.current} />
        </div>
      )}
    </div>
  )
}

export default InstructorLiveClassConsolePage
