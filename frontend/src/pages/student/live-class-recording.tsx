/**
 * S-H5 — recording playback. The "Watch recording" button on the student
 * live-classes list used to link to the JOIN page (live-class-join.tsx),
 * which has no recording handling at all — a dead end for ended classes.
 * The enrollment-gated playback endpoint
 * (live_class_recordings.py:101, GET .../recording-playback) was never
 * fetched by any UI. This page fetches it and renders the existing signed
 * video player (components/video/video-player.tsx, the same one lessons
 * use for Bunny-hosted playback).
 */
import * as React from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { ArrowLeft, Video as VideoIcon } from 'lucide-react'
import { ErrorState, EmptyState } from '@/components/dashboard/primitives'
import { VideoPlayer } from '@/components/video/video-player'
import { fetchRecordingPlayback, getLiveClass, type LiveClassOut, type RecordingPlaybackOut } from '@/api/liveClasses'

type Stage = 'loading' | 'ready' | 'no-recording' | 'error'

export function StudentLiveClassRecordingPage() {
  const { id } = useParams<{ id: string }>()
  const classId = Number(id)
  const navigate = useNavigate()

  const [stage, setStage] = React.useState<Stage>('loading')
  const [errorMessage, setErrorMessage] = React.useState<string | null>(null)
  const [playback, setPlayback] = React.useState<RecordingPlaybackOut | null>(null)
  const [liveClass, setLiveClass] = React.useState<LiveClassOut | null>(null)

  const load = React.useCallback(async () => {
    setStage('loading')
    setErrorMessage(null)
    try {
      const [classData, playbackData] = await Promise.all([
        getLiveClass(classId),
        fetchRecordingPlayback(classId),
      ])
      setLiveClass(classData)
      setPlayback(playbackData)
      setStage('ready')
    } catch (err: any) {
      if (err?.response?.status === 404) {
        // Still fetch the class itself so the empty state can show its
        // title, even though the recording call 404'd.
        try {
          const classData = await getLiveClass(classId)
          setLiveClass(classData)
        } catch { /* ignore — empty state falls back to a generic title */ }
        setStage('no-recording')
        return
      }
      const detail = err?.response?.data?.detail || err?.message || 'Failed to load the recording'
      setErrorMessage(typeof detail === 'string' ? detail : 'Failed to load the recording')
      setStage('error')
    }
  }, [classId])

  React.useEffect(() => {
    if (Number.isFinite(classId)) load()
  }, [classId, load])

  if (!Number.isFinite(classId)) {
    return <ErrorState title="Invalid class" description="This recording link looks incorrect." />
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

      {liveClass && (
        <div>
          <h1 className="dash-h1 mb-1">{liveClass.title}</h1>
          <p className="text-slate-600 text-sm">Recorded session</p>
        </div>
      )}

      {stage === 'loading' && (
        <div className="aspect-video w-full bg-slate-100 rounded-xl animate-pulse" />
      )}

      {stage === 'error' && (
        <ErrorState title="Couldn't load the recording" description={errorMessage ?? undefined} onRetry={load} />
      )}

      {stage === 'no-recording' && (
        <EmptyState
          icon={VideoIcon}
          title="No recording available"
          description="This class either wasn't recorded or the recording hasn't finished processing yet. Check back later."
        />
      )}

      {stage === 'ready' && playback && (
        <div className="aspect-video w-full bg-black rounded-xl overflow-hidden">
          <VideoPlayer src={playback.hls_url} title={liveClass?.title} className="w-full h-full" />
        </div>
      )}
    </div>
  )
}

export default StudentLiveClassRecordingPage
