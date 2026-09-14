import * as React from 'react'
import { Button } from '@/components/ui/button'
import { useLiveClassStore } from '@/store/liveClassStore'
import { sendHeartbeat } from '@/api/liveClasses'

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
}) => {
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
    startSession({ classId, roomName, isModerator })
    setLoadError(null)
    setIsReady(false)

    loadExternalApiScript(jitsiUrl)
      .then(() => {
        if (cancelled) return
        const JitsiMeetExternalAPI = (window as any).JitsiMeetExternalAPI
        if (!JitsiMeetExternalAPI) {
          throw new Error('JitsiMeetExternalAPI is not available on window')
        }

        const domain = jitsiUrl.replace(/^https?:\/\//, '').replace(/\/$/, '')
        const toolbarButtons = isModerator ? MODERATOR_TOOLBAR_BUTTONS : STUDENT_TOOLBAR_BUTTONS

        const api = new JitsiMeetExternalAPI(domain, {
          roomName,
          jwt,
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
        })

        api.addEventListener('readyToClose', () => {
          onLeft()
        })

        api.addEventListener('errorOccurred', (event: any) => {
          setConnectionStatus('error', event?.error?.message || 'A Jitsi conference error occurred')
          setLoadError(event?.error?.message || 'A Jitsi conference error occurred')
        })

        // 60s heartbeat cadence while the stage is mounted. Stops itself on
        // a terminal error (409 class ended / 403 access revoked) instead
        // of retrying forever — a lingering tab open past class-end would
        // otherwise 409-spam the backend every 60s indefinitely.
        heartbeatIntervalRef.current = setInterval(() => {
          sendHeartbeat(classId).catch((err) => {
            if (isTerminalHeartbeatError(err)) {
              if (heartbeatIntervalRef.current) {
                clearInterval(heartbeatIntervalRef.current)
                heartbeatIntervalRef.current = null
              }
              setConnectionStatus('error', 'This class has ended')
              return
            }
            // Transient network errors shouldn't tear down the call — the
            // next tick (or the final heartbeat on unmount) will retry.
          })
        }, HEARTBEAT_INTERVAL_MS)
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

  if (loadError) {
    return (
      <div className="flex flex-col items-center justify-center h-full min-h-[320px] rounded-lg border border-danger-200 bg-danger-50 text-center p-8">
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
    )
  }

  return (
    <div className="relative w-full h-full min-h-[320px] rounded-lg overflow-hidden bg-neutral-900">
      {!isReady && (
        <div className="absolute inset-0 flex items-center justify-center text-white/80 text-sm">
          Connecting to class…
        </div>
      )}
      <div ref={containerRef} className="w-full h-full" data-testid="jitsi-stage-container" />
      <button type="button" onClick={() => setLowBandwidth((v) => !v)} aria-pressed={lowBandwidth} data-testid="low-bandwidth-toggle"
        className={`absolute top-2 right-2 z-10 px-2 py-1 text-[11px] rounded-full border ${lowBandwidth ? 'bg-amber-400 text-black border-amber-500' : 'bg-black/50 text-white border-white/30'}`}>
        {lowBandwidth ? 'Low-bandwidth: on (180p)' : 'Low-bandwidth mode'}
      </button>
    </div>
  )
}
