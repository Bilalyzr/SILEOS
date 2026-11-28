import * as React from 'react'
import { Button } from '@/components/ui/button'
import { useLiveClassStore } from '@/store/liveClassStore'
import { getLiveClass, reportRecordingFailed, sendHeartbeat } from '@/api/liveClasses'

// ---------------------------------------------------------------------------
// external_api.js loader — lazy-injected once, cached promise so repeated
// mounts (e.g. re-join after a drop) never inject the script twice.
// ---------------------------------------------------------------------------

let externalApiScriptPromise: Promise<void> | null = null

function loadExternalApiScript(jitsiUrl: string): Promise<void> {
  if (typeof window !== 'undefined' && (window as any).JitsiMeetExternalAPI) {
    return Promise.resolve()
  }
  if (externalApiScriptPromise) return externalApiScriptPromise

  externalApiScriptPromise = new Promise<void>((resolve, reject) => {
    const existing = document.querySelector<HTMLScriptElement>('script[data-jitsi-external-api]')
    if (existing) {
      existing.addEventListener('load', () => resolve())
      existing.addEventListener('error', () => reject(new Error('Failed to load Jitsi external_api.js')))
      return
    }
    const script = document.createElement('script')
    script.src = `${jitsiUrl.replace(/\/$/, '')}/external_api.js`
    script.async = true
    script.dataset.jitsiExternalApi = 'true'
    script.onload = () => resolve()
    script.onerror = () => reject(new Error('Failed to load Jitsi external_api.js'))
    document.head.appendChild(script)
  }).catch((err) => {
    // Allow a later mount to retry after a failed load instead of caching
    // the rejection forever.
    externalApiScriptPromise = null
    throw err
  })

  return externalApiScriptPromise
}

// ---------------------------------------------------------------------------
// Toolbar / config per spec §6.3
// ---------------------------------------------------------------------------

const STUDENT_TOOLBAR_BUTTONS = [
  'microphone',
  'camera',
  'chat',
  'raisehand',
  'tileview',
  'fullscreen',
  'hangup',
]

const MODERATOR_TOOLBAR_BUTTONS = [
  ...STUDENT_TOOLBAR_BUTTONS,
  'desktop',
  'whiteboard',
  'recording',
  'mute-everyone',
  'security',
  'participants-pane',
]

const HEARTBEAT_INTERVAL_MS = 60_000
/** How often a learner's call checks whether the instructor has ended the class.
 * Heartbeats only run once a minute, so without this a learner stayed in the room
 * for up to a minute (or forever, before the heartbeat error was handled). */
const CLASS_STATUS_POLL_MS = 10_000

/** True for an axios error whose response status is 409 (class ended) or
 * 403 (access revoked) — both mean the server will never accept another
 * heartbeat for this session, so retrying on a timer is pointless and just
 * spams the backend from a lingering tab. Any other failure (network blip,
 * 5xx) is treated as transient and the interval keeps retrying. */
function isTerminalHeartbeatError(err: unknown): boolean {
  const status = (err as { response?: { status?: number } })?.response?.status
  return status === 409 || status === 403
}

export interface JitsiStageProps {
  jitsiUrl: string
  roomName: string
  jwt: string
  isModerator: boolean
  displayName: string
  classId: number
  onApiReady?: (api: any) => void
  onLeft: () => void
  /** Called after the call has been closed because the class ended (or access
   * was revoked). Defaults to `onLeft`. */
  onEnded?: () => void
  /** Moderator only: the room was closed from the call's own toolbar ("End meeting for all"),
   * so the class itself is still open on the server. The page should end the class. */
  onMeetingClosed?: () => void
}

export const JitsiStage: React.FC<JitsiStageProps> = ({
  jitsiUrl,
  roomName,
  jwt,
  isModerator,
  displayName,
  classId,
  onApiReady,
  onLeft,
  onEnded,
  onMeetingClosed,
}) => {
  const onLeftRef = React.useRef(onLeft)
  const onEndedRef = React.useRef(onEnded)
  const onMeetingClosedRef = React.useRef(onMeetingClosed)
  onLeftRef.current = onLeft
  onEndedRef.current = onEnded
  onMeetingClosedRef.current = onMeetingClosed
  const statusIntervalRef = React.useRef<ReturnType<typeof setInterval> | null>(null)
  const containerRef = React.useRef<HTMLDivElement>(null)
  const apiRef = React.useRef<any>(null)
  const heartbeatIntervalRef = React.useRef<ReturnType<typeof setInterval> | null>(null)
  const [loadError, setLoadError] = React.useState<string | null>(null)
  const [isReady, setIsReady] = React.useState(false)
  // WP8: low-bandwidth mode — 180p receive quality, remembered per browser
  const [lowBandwidth, setLowBandwidth] = React.useState<boolean>(() => { try { return localStorage.getItem('live.lowBandwidth') === '1' } catch { return false } })
  React.useEffect(() => {
    if (!isReady || !apiRef.current) return
    try { apiRef.current.executeCommand('setVideoQuality', lowBandwidth ? 180 : 720) } catch { /* older Jitsi builds */ }
    try { localStorage.setItem('live.lowBandwidth', lowBandwidth ? '1' : '0') } catch { /* private mode */ }
  }, [lowBandwidth, isReady])

  const startSession = useLiveClassStore((s) => s.startSession)
  const setConnectionStatus = useLiveClassStore((s) => s.setConnectionStatus)
  const participantJoined = useLiveClassStore((s) => s.participantJoined)
  const participantLeft = useLiveClassStore((s) => s.participantLeft)
  const setRecording = useLiveClassStore((s) => s.setRecording)
  const setRecordingError = useLiveClassStore((s) => s.setRecordingError)
  const resetSession = useLiveClassStore((s) => s.resetSession)

  const sendFinalHeartbeat = React.useCallback(() => {
    // Guard on apiRef: if the Jitsi API was never actually constructed
    // (e.g. a StrictMode dev double-invoke unmounts before the
    // loadExternalApiScript().then() callback ran), there's nothing to
    // send a "final" heartbeat for — skip the phantom call.
    if (!apiRef.current) return
    sendHeartbeat(classId).catch(() => {
      // Best-effort — the class may already be ended, or the network may be
      // gone on the way out. Never block teardown on this.
    })
  }, [classId])

  const retryKeyRef = React.useRef(0)
  const [retryKey, setRetryKey] = React.useState(0)

  React.useEffect(() => {
    let cancelled = false
    let endedHandled = false
    // Set once the call has been left or closed (instructor ended the room, learner hung up).
    // The video server then reports errors while it tears the room down; those are not
    // connection failures and must not replace the page with "Couldn't connect to the class".
    let callClosed = false

    /** The class is over (ended by the instructor, cancelled, or access revoked):
     * stop the timers, hang up so the learner is really out of the room and no
     * longer heard, then tell the page so it can show an ended message. */
    const closeBecauseClassEnded = () => {
      if (endedHandled || cancelled) return
      endedHandled = true
      callClosed = true
      if (heartbeatIntervalRef.current) {
        clearInterval(heartbeatIntervalRef.current)
        heartbeatIntervalRef.current = null
      }
      if (statusIntervalRef.current) {
        clearInterval(statusIntervalRef.current)
        statusIntervalRef.current = null
      }
      setConnectionStatus('error', 'This class has ended')
      if (apiRef.current) {
        try { apiRef.current.executeCommand('hangup') } catch { /* already closed */ }
        try { apiRef.current.dispose() } catch { /* iframe already torn down */ }
        apiRef.current = null
      }
      ;(onEndedRef.current ?? onLeftRef.current)()
    }

    startSession({ classId, roomName, isModerator })
    setLoadError(null)
    setIsReady(false)

    loadExternalApiScript(jitsiUrl)
      .then(() => {
        if (cancelled) return
        // The container is always rendered, but guard anyway: constructing the API with
        // no parent node throws "Cannot read properties of null (reading 'appendChild')".
        if (!containerRef.current) return
        const JitsiMeetExternalAPI = (window as any).JitsiMeetExternalAPI
        if (!JitsiMeetExternalAPI) {
          throw new Error('JitsiMeetExternalAPI is not available on window')
        }

        const domain = jitsiUrl.replace(/^https?:\/\//, '').replace(/\/$/, '')
        const toolbarButtons = isModerator ? MODERATOR_TOOLBAR_BUTTONS : STUDENT_TOOLBAR_BUTTONS

        const api = new JitsiMeetExternalAPI(domain, {
          roomName,
          ...(jwt ? { jwt } : {}),
          parentNode: containerRef.current,
          userInfo: { displayName },
          configOverwrite: {
            prejoinConfig: { enabled: false },
            startWithAudioMuted: !isModerator,
            disableDeepLinking: true,
            toolbarButtons,
            resolution: lowBandwidth ? 180 : 720,
            constraints: { video: { height: { ideal: lowBandwidth ? 180 : 720, max: lowBandwidth ? 180 : 720 } } },
            whiteboard: { enabled: true },
          },
          interfaceConfigOverwrite: {
            TOOLBAR_BUTTONS: toolbarButtons,
          },
        })

        apiRef.current = api
        onApiReady?.(api)

        // Fullscreen: the ExternalAPI iframe's `allow` attribute does not
        // include fullscreen by default, so the toolbar's fullscreen button
        // silently did nothing (the browser blocks the request from an
        // iframe without the permission). Append it, plus allowfullscreen.
        const iframe: HTMLIFrameElement | undefined =
          api._iframe ??
          (containerRef.current?.querySelector('iframe') as HTMLIFrameElement | undefined)
        if (iframe) {
          const perms = iframe.getAttribute('allow') ?? ''
          if (!iframe.allowFullscreen) iframe.setAttribute('allowfullscreen', 'true')
          if (!/fullscreen/i.test(perms)) {
            iframe.setAttribute('allow', `${perms ? perms + '; ' : ''}fullscreen`)
          }
        }

        api.addEventListener('videoConferenceJoined', () => {
          setConnectionStatus('connected')
          setIsReady(true)
        })

        api.addEventListener('participantJoined', (event: any) => {
          participantJoined({
            participantId: event.id,
            displayName: event.displayName || 'Participant',
          })
        })

        api.addEventListener('participantLeft', (event: any) => {
          participantLeft(event.id)
        })

        api.addEventListener('endpointTextMessageReceived', () => {
          // Dock signaling (raise-hand / moderation) consumed by
          // InstructorDock / RaiseHandList (Task 8) via the store.
        })

        api.addEventListener('recordingStatusChanged', (event: any) => {
          setRecording(Boolean(event?.on))
          if (event?.error) {
            // The recorder could not start (for example the recording service is
            // unavailable). Say so, and correct the server: the instructor's start
            // request was already stored as "requested" before the call tried.
            setRecordingError('Recording could not start. The recording service is unavailable, so this class is not being recorded.')
            if (isModerator) reportRecordingFailed(classId).catch(() => { /* best effort */ })
          } else if (event?.on) {
            setRecordingError(null)
          }
        })

        api.addEventListener('videoConferenceLeft', () => { callClosed = true })

        api.addEventListener('readyToClose', () => {
          callClosed = true
          onLeft()
        })

        api.addEventListener('errorOccurred', (event: any) => {
          if (callClosed || endedHandled) return
          const message = event?.error?.message || 'A Jitsi conference error occurred'
          const showError = () => {
            if (cancelled || callClosed || endedHandled) return
            setConnectionStatus('error', message)
            setLoadError(message)
          }
          // When the instructor ends the class the video server closes the room and reports
          // an error to everyone still in it, a few seconds before a learner's own status
          // check would notice. That is the class ending, not a connection failure: ask the
          // server before showing "Couldn't connect to the class".
          // "conference.destroyed / The meeting has been terminated": the room was closed on
          // purpose (the instructor used End meeting for all). Not a connection failure.
          const meetingTerminated = /destroyed|terminated/i.test(`${event?.error?.name ?? ''} ${event?.error?.message ?? ''} ${event?.name ?? ''}`)
          getLiveClass(classId)
            .then((cls) => {
              if (cls.status === 'ended' || cls.status === 'cancelled') {
                // The instructor's console navigates to the report by itself; learners leave now.
                if (!isModerator) closeBecauseClassEnded()
                return
              }
              if (meetingTerminated || callClosed) {
                callClosed = true
                // Learners: the room is gone, so they are out. The instructor: closing the
                // room from the toolbar must also end the class, or it stays "live" with nobody in it.
                if (isModerator) (onMeetingClosedRef.current ?? onLeftRef.current)()
                else closeBecauseClassEnded()
                return
              }
              showError()
            })
            .catch(() => { if (meetingTerminated) { callClosed = true; (isModerator ? (onMeetingClosedRef.current ?? onLeftRef.current) : onEndedRef.current ?? onLeftRef.current)() } else showError() })
        })

        // 60s heartbeat cadence while the stage is mounted. Stops itself on
        // a terminal error (409 class ended / 403 access revoked) instead
        // of retrying forever — a lingering tab open past class-end would
        // otherwise 409-spam the backend every 60s indefinitely.
        heartbeatIntervalRef.current = setInterval(() => {
          sendHeartbeat(classId).catch((err) => {
            if (isTerminalHeartbeatError(err)) {
              closeBecauseClassEnded()
              return
            }
            // Transient network errors shouldn't tear down the call — the
            // next tick (or the final heartbeat on unmount) will retry.
          })
        }, HEARTBEAT_INTERVAL_MS)

        // Learners also check the class status every few seconds, so ending the
        // class closes their call promptly. The instructor ends the class
        // themselves, so their console does not poll.
        if (!isModerator) {
          statusIntervalRef.current = setInterval(() => {
            getLiveClass(classId)
              .then((cls) => {
                if (cls.status === 'ended' || cls.status === 'cancelled') closeBecauseClassEnded()
              })
              .catch((err) => {
                if (isTerminalHeartbeatError(err)) closeBecauseClassEnded()
                // Anything else is a transient network error: try again next tick.
              })
          }, CLASS_STATUS_POLL_MS)
        }
      })
      .catch((err: Error) => {
        if (cancelled) return
        setConnectionStatus('error', err.message)
        setLoadError(err.message)
      })

    return () => {
      cancelled = true
      if (heartbeatIntervalRef.current) {
        clearInterval(heartbeatIntervalRef.current)
        heartbeatIntervalRef.current = null
      }
      if (statusIntervalRef.current) {
        clearInterval(statusIntervalRef.current)
        statusIntervalRef.current = null
      }
      sendFinalHeartbeat()
      if (apiRef.current) {
        try {
          apiRef.current.dispose()
        } catch {
          // dispose() can throw if the iframe was already torn down.
        }
        apiRef.current = null
      }
      resetSession()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [jitsiUrl, roomName, jwt, isModerator, displayName, classId, retryKey])

  return (
    <div className="relative w-full h-full min-h-[320px] rounded-lg overflow-hidden bg-neutral-900">
      {!isReady && !loadError && (
        <div className="absolute inset-0 flex items-center justify-center text-white/80 text-sm">
          Connecting to class…
        </div>
      )}
      <div ref={containerRef} className="w-full h-full" data-testid="jitsi-stage-container" />
      {loadError && (
        <div className="absolute inset-0 z-20 flex flex-col items-center justify-center rounded-lg border border-danger-200 bg-danger-50 text-center p-8">
          <p className="font-semibold text-danger-700 mb-1">Couldn't connect to the class</p>
          <p className="text-sm text-danger-600 mb-4 max-w-sm">{loadError}</p>
          <Button
            variant="destructive"
            onClick={() => {
              retryKeyRef.current += 1
              setRetryKey(retryKeyRef.current)
            }}
          >
            Retry
          </Button>
        </div>
      )}
      <button type="button" onClick={() => setLowBandwidth((v) => !v)} aria-pressed={lowBandwidth} data-testid="low-bandwidth-toggle"
        className={`absolute top-2 right-2 z-10 px-2 py-1 text-[11px] rounded-full border ${lowBandwidth ? 'bg-amber-400 text-black border-amber-500' : 'bg-black/50 text-white border-white/30'}`}>
        {lowBandwidth ? 'Low-bandwidth: on (180p)' : 'Low-bandwidth mode'}
      </button>
    </div>
  )
}
