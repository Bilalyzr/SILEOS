import * as React from 'react'
import { Mic, MicOff, VideoOff, Volume2 } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'

export type PermissionState = 'pending' | 'granted' | 'denied' | 'unavailable'

export interface DevicePrecheckProps {
  onContinue: () => void
  /** Called with the resolved states when the user leaves this screen, so a
   * caller can decide whether to start muted/camera-off. Optional — most
   * callers only need onContinue. */
  onResolved?: (state: { micGranted: boolean; camGranted: boolean }) => void
  className?: string
}

/**
 * Mic level meter (AnalyserNode), camera preview, speaker test tone, and a
 * Continue button gated on permission resolution — but never fully blocked:
 * per the plan's binding behavior, "allow continue-without-cam" means a
 * denied/unavailable camera must not trap the student on this screen.
 */
export const DevicePrecheck: React.FC<DevicePrecheckProps> = ({ onContinue, onResolved, className = '' }) => {
  const videoRef = React.useRef<HTMLVideoElement>(null)
  const streamRef = React.useRef<MediaStream | null>(null)
  const audioCtxRef = React.useRef<AudioContext | null>(null)
  const analyserRef = React.useRef<AnalyserNode | null>(null)
  const rafRef = React.useRef<number | null>(null)

  const [micState, setMicState] = React.useState<PermissionState>('pending')
  const [camState, setCamState] = React.useState<PermissionState>('pending')
  const [micLevel, setMicLevel] = React.useState(0)
  const [testingSpeaker, setTestingSpeaker] = React.useState(false)

  React.useEffect(() => {
    let cancelled = false

    async function init() {
      if (typeof navigator === 'undefined' || !navigator.mediaDevices?.getUserMedia) {
        setMicState('unavailable')
        setCamState('unavailable')
        return
      }

      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true, video: true })
        if (cancelled) {
          stream.getTracks().forEach((t) => t.stop())
          return
        }
        streamRef.current = stream
        setMicState(stream.getAudioTracks().length > 0 ? 'granted' : 'unavailable')
        setCamState(stream.getVideoTracks().length > 0 ? 'granted' : 'unavailable')

        // srcObject is attached by the effect below once the <video>
        // element mounts (it only renders after camState flips to
        // 'granted' — assigning here ran before that re-render, when
        // videoRef.current was still null, so the preview never showed).

        if (stream.getAudioTracks().length > 0 && typeof AudioContext !== 'undefined') {
          const audioCtx = new AudioContext()
          const source = audioCtx.createMediaStreamSource(stream)
          const analyser = audioCtx.createAnalyser()
          analyser.fftSize = 256
          source.connect(analyser)
          audioCtxRef.current = audioCtx
          analyserRef.current = analyser

          const data = new Uint8Array(analyser.frequencyBinCount)
          const tick = () => {
            analyser.getByteFrequencyData(data)
            const avg = data.reduce((sum, v) => sum + v, 0) / data.length
            setMicLevel(Math.min(100, Math.round((avg / 255) * 100)))
            rafRef.current = requestAnimationFrame(tick)
          }
          tick()
        }
      } catch {
        // Try audio-only fallback so a camera-only denial doesn't also fail
        // the mic (and vice versa is handled by the constraints call above
        // failing outright — browsers reject the whole call on any denial).
        if (cancelled) return
        setMicState('denied')
        setCamState('denied')
      }
    }

    init()

    return () => {
      cancelled = true
      if (rafRef.current) cancelAnimationFrame(rafRef.current)
      if (audioCtxRef.current) audioCtxRef.current.close().catch(() => {})
      if (streamRef.current) streamRef.current.getTracks().forEach((t) => t.stop())
    }
  }, [])

  // Attach the granted stream once the <video> element exists.
  React.useEffect(() => {
    if (camState === 'granted' && videoRef.current && streamRef.current) {
      videoRef.current.srcObject = streamRef.current
      videoRef.current.play().catch(() => {
        // autoplay can reject before user gesture; muted+playsInline
        // makes this rare — the poster simply stays until it plays.
      })
    }
  }, [camState])

  const playTestTone = () => {
    if (testingSpeaker) return
    setTestingSpeaker(true)
    try {
      const ctx = new AudioContext()
      const oscillator = ctx.createOscillator()
      const gain = ctx.createGain()
      oscillator.frequency.value = 440
      gain.gain.value = 0.15
      oscillator.connect(gain)
      gain.connect(ctx.destination)
      oscillator.start()
      window.setTimeout(() => {
        oscillator.stop()
        ctx.close().catch(() => {})
        setTestingSpeaker(false)
      }, 800)
    } catch {
      setTestingSpeaker(false)
    }
  }

  const isResolved = micState !== 'pending' && camState !== 'pending'

  const handleContinue = () => {
    onResolved?.({ micGranted: micState === 'granted', camGranted: camState === 'granted' })
    onContinue()
  }

  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle>Device check</CardTitle>
        <CardDescription>Make sure your camera, mic and speaker are working before you join.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="rounded-lg overflow-hidden bg-neutral-900 aspect-video relative flex items-center justify-center">
          {camState === 'granted' ? (
            <video ref={videoRef} autoPlay muted playsInline className="w-full h-full object-cover" />
          ) : (
            <div className="text-white/70 text-sm flex flex-col items-center gap-2">
              <VideoOff className="h-8 w-8" />
              {camState === 'denied' && 'Camera access denied'}
              {camState === 'unavailable' && 'No camera detected'}
              {camState === 'pending' && 'Checking camera…'}
            </div>
          )}
        </div>

        <div className="flex items-center gap-3">
          {micState === 'granted' ? <Mic className="h-4 w-4 text-success-600" /> : <MicOff className="h-4 w-4 text-danger-500" />}
          <div className="flex-1">
            <div className="h-2 rounded-full bg-neutral-200 overflow-hidden">
              <div
                className="h-full bg-success-500 transition-all"
                style={{ width: `${micState === 'granted' ? micLevel : 0}%` }}
                data-testid="mic-level-bar"
              />
            </div>
          </div>
          <span className="text-xs text-neutral-500 w-24">
            {micState === 'granted' && 'Mic working'}
            {micState === 'denied' && 'Mic denied'}
            {micState === 'unavailable' && 'No mic'}
            {micState === 'pending' && 'Checking…'}
          </span>
        </div>

        <div className="flex items-center gap-3">
          <Volume2 className="h-4 w-4 text-neutral-500" />
          <Button variant="outline" size="sm" onClick={playTestTone} disabled={testingSpeaker}>
            {testingSpeaker ? 'Playing…' : 'Test speaker'}
          </Button>
        </div>

        {(micState === 'denied' || camState === 'denied') && (
          <p className="text-xs text-warning-700 bg-warning-50 border border-warning-200 rounded-md px-3 py-2">
            {camState === 'denied' && micState === 'denied'
              ? 'Camera and mic are blocked — you can still join, but others won\'t see or hear you until you enable them in your browser settings.'
              : camState === 'denied'
              ? 'Camera is blocked — you can still join without video.'
              : 'Mic is blocked — you can still join, but you\'ll need to enable it to speak.'}
          </p>
        )}

        <Button className="w-full" size="lg" disabled={!isResolved} onClick={handleContinue}>
          Continue to class
        </Button>
      </CardContent>
    </Card>
  )
}
