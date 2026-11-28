/**
 * Student join flow: DevicePrecheck -> requestJoinToken -> JitsiStage.
 * onLeft (readyToClose / hangup) routes back to the live-classes list.
 */
import * as React from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'
import { DevicePrecheck } from '@/components/live/DevicePrecheck'
import { JitsiStage } from '@/components/live/JitsiStage'
import { LiveChallengePanel } from '@/components/live/LiveChallengePanel'
import { RecordingBadge } from '@/components/live/RecordingBadge'
import { ErrorState } from '@/components/dashboard/primitives'
import { useAuth } from '@/hooks/use-auth'
import { useLiveClassStore } from '@/store/liveClassStore'
import { getLiveClass, requestJoinToken, type JoinTokenOut, type LiveClassOut } from '@/api/liveClasses'

type Stage = 'loading' | 'precheck' | 'connecting' | 'in-call' | 'error' | 'left' | 'ended'

export function StudentLiveClassJoinPage() {
  const { id } = useParams<{ id: string }>()
  const classId = Number(id)
  const navigate = useNavigate()
  const { fullName } = useAuth()

  const [stage, setStage] = React.useState<Stage>('loading')
  const [liveClass, setLiveClass] = React.useState<LiveClassOut | null>(null)
  const [tokenData, setTokenData] = React.useState<JoinTokenOut | null>(null)
  const [errorMessage, setErrorMessage] = React.useState<string | null>(null)
  const isRecording = useLiveClassStore((s) => s.isRecording)

  // Check the class first: an ended or cancelled class must not offer the
  // device check and a join button that can only fail afterwards.
  React.useEffect(() => {
    if (!Number.isFinite(classId)) return
    let active = true
    getLiveClass(classId)
      .then((cls) => {
        if (!active) return
        setLiveClass(cls)
        setStage(cls.status === 'ended' || cls.status === 'cancelled' ? 'ended' : 'precheck')
      })
      // If the status cannot be read, fall back to the old behaviour: the join
      // request below reports the real reason.
      .catch(() => active && setStage('precheck'))
    return () => { active = false }
  }, [classId])

  const handleContinue = React.useCallback(async () => {
    setStage('connecting')
    setErrorMessage(null)
    try {
      const data = await requestJoinToken(classId)
      setTokenData(data)
      setStage('in-call')
    } catch (err: any) {
      const detail = err?.response?.data?.detail || err?.message || 'Failed to join this class'
      setErrorMessage(typeof detail === 'string' ? detail : 'Failed to join this class')
      setStage('error')
    }
  }, [classId])

  const handleLeft = React.useCallback(() => {
    setStage('left')
    navigate('/student/live-classes')
  }, [navigate])

  // The call closed itself because the instructor ended the class: show that
  // clearly instead of silently dropping the learner on another page.
  const handleEnded = React.useCallback(() => {
    setTokenData(null)
    setLiveClass((cls) => (cls ? { ...cls, status: 'ended' } : cls))
    setStage('ended')
  }, [])

  if (!Number.isFinite(classId)) {
    return <ErrorState title="Invalid class" description="This live class link looks incorrect." />
  }

  return (
    <div className="flex flex-col gap-4">
      <button
        onClick={() => navigate('/student/live-classes')}
        className="inline-flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-700 w-fit"
      >
        <ArrowLeft className="h-4 w-4" />
        Back to live classes
      </button>

      {stage === 'loading' && (
        <div className="flex items-center justify-center min-h-[240px]" role="status" aria-label="Loading class">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-500" />
        </div>
      )}

      {stage === 'ended' && (
        <div className="max-w-lg mx-auto w-full rounded-xl border border-slate-200 bg-white p-6 text-center" role="status">
          <h2 className="text-lg font-semibold text-slate-900">
            {liveClass?.status === 'cancelled' ? 'This class was cancelled' : 'This class has ended'}
          </h2>
          <p className="mt-2 text-sm text-slate-600">
            {liveClass?.title ? `“${liveClass.title}” is no longer running. ` : ''}
            {liveClass?.recording_status === 'available'
              ? 'You can watch the recording.'
              : 'You can no longer join it.'}
          </p>
          <div className="mt-5 flex flex-wrap justify-center gap-2">
            {liveClass?.recording_status === 'available' && (
              <button
                onClick={() => navigate(`/student/live-classes/${classId}/recording`)}
                className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-semibold text-white"
              >
                Watch the recording
              </button>
            )}
            <button
              onClick={() => navigate('/student/live-classes')}
              className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700"
            >
              Back to live classes
            </button>
          </div>
        </div>
      )}

      {stage === 'precheck' && (
        <div className="max-w-lg mx-auto w-full">
          <DevicePrecheck onContinue={handleContinue} />
        </div>
      )}

      {stage === 'connecting' && (
        <div className="flex items-center justify-center min-h-[320px]">
          <div className="flex flex-col items-center gap-3 text-slate-500">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-500" />
            <p className="text-sm">Requesting your join token…</p>
          </div>
        </div>
      )}

      {stage === 'error' && (
        <ErrorState
          title="Couldn't join this class"
          description={errorMessage || undefined}
          onRetry={handleContinue}
        />
      )}

      {stage === 'in-call' && tokenData && (
        <>
        <div className="h-[70vh] min-h-[420px] flex flex-col gap-2">
          {isRecording && <RecordingBadge isRecording className="self-start" />}
          <div className="flex-1 min-h-0">
            <JitsiStage
              jitsiUrl={tokenData.jitsi_url}
              roomName={tokenData.room_name}
              jwt={tokenData.jwt}
              // This route is student-only (StudentRoute-guarded); the
              // join-token endpoint mints a moderator=false JWT for students
              // regardless (see live_class_session.join_token — `moderator =
              // is_staff`), and JoinTokenOut doesn't echo the flag back, so
              // the client-side toolbar config must agree with that: false.
              // The instructor console (Task 8) passes true from its own
              // staff-only route.
              isModerator={false}
              displayName={fullName || 'Student'}
              classId={classId}
              onLeft={handleLeft}
              onEnded={handleEnded}
            />
          </div>
        </div>
        <LiveChallengePanel classId={classId} className="mt-4" />
        </>
      )}
    </div>
  )
}

export default StudentLiveClassJoinPage
