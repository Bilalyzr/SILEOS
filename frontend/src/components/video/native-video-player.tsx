import React, { useRef, useState, useEffect, useImperativeHandle, forwardRef, useCallback } from 'react'
import { Play, Pause, Volume2, VolumeX, Maximize, Minimize } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { getMediaUrl } from '@/utils/media'
import Hls from 'hls.js'

export interface VideoPlayerHandle {
    play: () => void
    pause: () => void
    seekTo: (seconds: number) => void
    getCurrentTime: () => number
    getDuration: () => number
}

interface NativeVideoPlayerProps {
    src: string
    title?: string
    poster?: string
    autoPlay?: boolean
    className?: string
    onPlay?: () => void
    onPause?: () => void
    onEnded?: () => void
    onTimeUpdate?: (state: { played: number; playedSeconds: number }) => void
    onDuration?: (duration: number) => void
    /** Intrinsic width/height of the loaded video, e.g. 1.7778 for 16:9. */
    onAspectRatio?: (ratio: number) => void
}

export const NativeVideoPlayer = forwardRef<VideoPlayerHandle, NativeVideoPlayerProps>(
    function NativeVideoPlayer(
        { src, poster, autoPlay = false, className = '', onPlay, onPause, onEnded, onTimeUpdate, onDuration, onAspectRatio },
        ref
    ) {
        const videoRef = useRef<HTMLVideoElement>(null)
        const containerRef = useRef<HTMLDivElement>(null)
        const [isPlaying, setIsPlaying] = useState(false)
        const [currentTime, setCurrentTime] = useState(0)
        const [duration, setDuration] = useState(0)
        const [volume, setVolume] = useState(1)
        const [isMuted, setIsMuted] = useState(false)
        const [isFullscreen, setIsFullscreen] = useState(false)
        const [showControls, setShowControls] = useState(true)
        const hideControlsTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
        // Touch devices get tap-to-reveal controls instead of hover-to-reveal.
        const [isTouch, setIsTouch] = useState(false)
        // Real width/height of the loaded stream. Not every lesson is filmed in
        // 16:9 — a 4:3 screen recording letterboxed into a 16:9 box renders far
        // smaller than it needs to, so the stage is told the true ratio instead.
        const [intrinsicRatio, setIntrinsicRatio] = useState<number | null>(null)

        // Resolve the src URL through media utilities
        const resolvedSrc = getMediaUrl(src)
        // HLS manifests are loaded by hls.js (or by Safari, in the effect below),
        // never by putting the .m3u8 on the element's src — most browsers can't
        // play it natively and would just raise a media error.
        const isHls = resolvedSrc.includes('.m3u8')

        // A new source has its own dimensions — drop the previous one so the
        // stage falls back to 16:9 until this stream's metadata arrives.
        useEffect(() => { setIntrinsicRatio(null) }, [resolvedSrc])

        // HLS setup for .m3u8 streams (Bunny CDN, etc.)
        useEffect(() => {
            const video = videoRef.current
            if (!video || !resolvedSrc) return
            if (!resolvedSrc.includes('.m3u8')) return

            let hls: Hls | null = null
            if (Hls.isSupported()) {
                hls = new Hls({ enableWorker: true, maxBufferLength: 30 })
                hls.loadSource(resolvedSrc)
                hls.attachMedia(video)
                // Network errors here are usually environmental rather than
                // recoverable — a CSP that blocks blob:/the CDN host, a missing
                // CORS header, or a 403 from an unsigned CDN URL. Surface them
                // so the caller can fall back instead of showing a dead player.
                hls.on(Hls.Events.ERROR, (_evt, data) => {
                    if (data?.fatal) console.warn('[video] fatal HLS error:', data.type, data.details)
                })
            } else if (video.canPlayType('application/vnd.apple.mpegurl')) {
                video.src = resolvedSrc
            }
            return () => hls?.destroy()
        }, [resolvedSrc])

        // Expose imperative API
        useImperativeHandle(ref, () => ({
            play: () => { videoRef.current?.play() },
            pause: () => { videoRef.current?.pause() },
            seekTo: (seconds: number) => {
                if (videoRef.current) {
                    videoRef.current.currentTime = Math.max(0, Math.min(seconds, videoRef.current.duration || Infinity))
                }
            },
            getCurrentTime: () => videoRef.current?.currentTime ?? 0,
            getDuration: () => videoRef.current?.duration ?? 0,
        }), [])

        // Auto-hide controls
        const resetHideTimer = useCallback(() => {
            setShowControls(true)
            if (hideControlsTimer.current) clearTimeout(hideControlsTimer.current)
            if (isPlaying) {
                // Touch users have to tap to bring the bar back, so give them longer.
                hideControlsTimer.current = setTimeout(() => setShowControls(false), isTouch ? 4000 : 3000)
            }
        }, [isPlaying, isTouch])

        useEffect(() => {
            return () => { if (hideControlsTimer.current) clearTimeout(hideControlsTimer.current) }
        }, [])

        // Event handlers
        const handlePlay = () => { setIsPlaying(true); onPlay?.(); resetHideTimer() }
        const handlePause = () => { setIsPlaying(false); onPause?.(); setShowControls(true) }
        const handleEnded = () => { setIsPlaying(false); onEnded?.() }

        const handleTimeUpdate = () => {
            if (!videoRef.current) return
            const t = videoRef.current.currentTime
            const d = videoRef.current.duration || 0
            setCurrentTime(t)
            onTimeUpdate?.({ played: d > 0 ? t / d : 0, playedSeconds: t })
        }

        const handleLoadedMetadata = () => {
            if (!videoRef.current) return
            const d = videoRef.current.duration
            setDuration(d)
            onDuration?.(d)

            const { videoWidth, videoHeight } = videoRef.current
            if (videoWidth > 0 && videoHeight > 0) {
                const ratio = videoWidth / videoHeight
                setIntrinsicRatio(ratio)
                onAspectRatio?.(ratio)
            }
        }

        const togglePlay = () => {
            if (!videoRef.current) return
            videoRef.current.paused ? videoRef.current.play() : videoRef.current.pause()
        }

        // Tapping the video surface. On touch there is no hover, so the first tap
        // while playing brings the controls back instead of pausing.
        const handleSurfaceClick = () => {
            if (isTouch && isPlaying && !showControls) {
                resetHideTimer()
                return
            }
            togglePlay()
            resetHideTimer()
        }

        const handleSeek = (e: React.ChangeEvent<HTMLInputElement>) => {
            const newTime = parseFloat(e.target.value)
            setCurrentTime(newTime)
            if (videoRef.current) videoRef.current.currentTime = newTime
        }

        const handleVolumeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
            const v = parseFloat(e.target.value)
            setVolume(v)
            setIsMuted(v === 0)
            if (videoRef.current) { videoRef.current.volume = v; videoRef.current.muted = v === 0 }
        }

        const toggleMute = () => {
            if (!videoRef.current) return
            const newMuted = !isMuted
            setIsMuted(newMuted)
            videoRef.current.muted = newMuted
            if (!newMuted && volume === 0) { setVolume(0.5); videoRef.current.volume = 0.5 }
        }

        // Rotate to landscape while fullscreen on phones. Unsupported everywhere
        // else (desktop, iOS) — the rejection is expected and ignored.
        const lockLandscape = () => {
            const orientation = window.screen?.orientation as any
            try { orientation?.lock?.('landscape').catch(() => { }) } catch { /* not supported */ }
        }
        const unlockOrientation = () => {
            const orientation = window.screen?.orientation as any
            try { orientation?.unlock?.() } catch { /* not supported */ }
        }

        const toggleFullscreen = async () => {
            const container = containerRef.current as any
            const video = videoRef.current as any
            const doc = document as any
            try {
                if (doc.fullscreenElement || doc.webkitFullscreenElement) {
                    await (doc.exitFullscreen?.() ?? doc.webkitExitFullscreen?.())
                    setIsFullscreen(false)
                    unlockOrientation()
                    return
                }

                if (container?.requestFullscreen) {
                    await container.requestFullscreen()
                } else if (container?.webkitRequestFullscreen) {
                    container.webkitRequestFullscreen()
                } else if (video?.webkitEnterFullscreen) {
                    // iPhone Safari cannot fullscreen an arbitrary element — only the
                    // <video> itself, which then uses the native iOS player chrome.
                    video.webkitEnterFullscreen()
                    return
                } else {
                    return
                }
                setIsFullscreen(true)
                lockLandscape()
            } catch (err) { console.warn('Fullscreen not supported:', err) }
        }

        // Listen for fullscreen changes (user pressing Esc, iOS native player, etc.)
        useEffect(() => {
            const doc = document as any
            const handler = () => {
                const active = !!(doc.fullscreenElement || doc.webkitFullscreenElement)
                setIsFullscreen(active)
                if (!active) unlockOrientation()
            }
            document.addEventListener('fullscreenchange', handler)
            document.addEventListener('webkitfullscreenchange', handler)
            return () => {
                document.removeEventListener('fullscreenchange', handler)
                document.removeEventListener('webkitfullscreenchange', handler)
            }
        }, [])

        const formatTime = (s: number) => {
            if (!isFinite(s)) return '0:00'
            const m = Math.floor(s / 60)
            const sec = Math.floor(s % 60)
            return `${m}:${sec.toString().padStart(2, '0')}`
        }

        // Progress percentage for the custom range track
        const progressPct = duration > 0 ? (currentTime / duration) * 100 : 0

        return (
            <div
                ref={containerRef}
                className={`relative bg-black w-full max-h-full group select-none ${className}`}
                // Fill the box the parent gives us (every call site wraps the player
                // in a sized stage). `aspectRatio` is only the fallback for a
                // parent with auto height, where `height: 100%` resolves to auto —
                // it follows the real stream once the metadata has loaded.
                style={{ height: '100%', aspectRatio: intrinsicRatio ?? 16 / 9, touchAction: 'manipulation' }}
                onPointerDown={(e) => { if (e.pointerType !== 'mouse') setIsTouch(true) }}
                onMouseMove={() => { if (!isTouch) resetHideTimer() }}
                onMouseLeave={() => { if (!isTouch && isPlaying) setShowControls(false) }}
                onContextMenu={(e) => { e.preventDefault(); return false }}
            >
                {/* Native video element */}
                <video
                    ref={videoRef}
                    src={isHls ? undefined : resolvedSrc}
                    poster={poster}
                    autoPlay={autoPlay}
                    playsInline
                    preload="metadata"
                    className="absolute inset-0 object-contain"
                    controlsList="nodownload"
                    onPlay={handlePlay}
                    onPause={handlePause}
                    onEnded={handleEnded}
                    onTimeUpdate={handleTimeUpdate}
                    onLoadedMetadata={handleLoadedMetadata}
                    onClick={handleSurfaceClick}
                    // Blocked source, unsupported codec, 403 from the CDN — the
                    // element gives no detail, but the log pins down which URL.
                    onError={() => { if (!isHls) console.warn('[video] media element failed to load:', resolvedSrc) }}
                    // Inline width/height beat Tailwind's preflight base rule
                    // (`video { height: auto; max-width: 100% }`), which can win
                    // over the h-full utility and collapse the video to its
                    // intrinsic size (small, letterboxed) instead of filling.
                    style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', objectFit: 'contain', cursor: 'pointer' }}
                />

                {/* Center play button when paused */}
                {!isPlaying && (
                    <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                        <button
                            onClick={togglePlay}
                            aria-label="Play"
                            className="pointer-events-auto w-14 h-14 sm:w-20 sm:h-20 rounded-full bg-white/20 backdrop-blur-sm border-2 border-white/40 flex items-center justify-center hover:bg-white/30 transition-all hover:scale-110"
                        >
                            <Play className="w-7 h-7 sm:w-10 sm:h-10 text-white ml-1" />
                        </button>
                    </div>
                )}

                {/* Controls overlay */}
                <div
                    className={`absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/90 to-transparent px-2 sm:px-4 pb-2 sm:pb-3 pt-8 sm:pt-10 transition-opacity duration-300 ${showControls ? 'opacity-100' : 'opacity-0 pointer-events-none'
                        }`}
                >
                    {/* Progress bar — `video-range` gives it a real thumb and a
                        finger-sized hit area (see globals.css). */}
                    <div className="mb-1 sm:mb-2 relative">
                        <input
                            type="range"
                            aria-label="Seek"
                            min={0}
                            max={duration || 100}
                            step={0.1}
                            value={currentTime}
                            onChange={handleSeek}
                            onPointerDown={resetHideTimer}
                            className="video-range w-full cursor-pointer"
                            style={{
                                background: `linear-gradient(to right, #f97316 ${progressPct}%, rgba(255,255,255,0.3) ${progressPct}%)`
                            }}
                        />
                    </div>

                    {/* Control buttons row */}
                    <div className="flex items-center justify-between gap-2">
                        <div className="flex items-center gap-1 sm:gap-2 min-w-0">
                            <Button variant="ghost" size="icon" aria-label={isPlaying ? 'Pause' : 'Play'} onClick={togglePlay} className="text-white hover:bg-white/20 h-10 w-10 sm:h-8 sm:w-8 flex-shrink-0">
                                {isPlaying ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
                            </Button>

                            <Button variant="ghost" size="icon" aria-label={isMuted ? 'Unmute' : 'Mute'} onClick={toggleMute} className="text-white hover:bg-white/20 h-10 w-10 sm:h-8 sm:w-8 flex-shrink-0">
                                {isMuted || volume === 0 ? <VolumeX className="h-4 w-4" /> : <Volume2 className="h-4 w-4" />}
                            </Button>

                            {/* Volume slider is dropped on narrow screens where it would
                                push the timer off-screen; mute button still works. */}
                            <input
                                type="range"
                                min={0}
                                max={1}
                                step={0.05}
                                value={isMuted ? 0 : volume}
                                onChange={handleVolumeChange}
                                aria-label="Volume"
                                className="video-range hidden sm:block w-16 bg-white/30 cursor-pointer flex-shrink-0"
                            />

                            <span className="text-white/80 text-[11px] sm:text-xs sm:ml-2 font-mono select-none whitespace-nowrap truncate">
                                {formatTime(currentTime)} / {formatTime(duration)}
                            </span>
                        </div>

                        <div className="flex items-center gap-1 flex-shrink-0">
                            <Button variant="ghost" size="icon" aria-label={isFullscreen ? 'Exit fullscreen' : 'Fullscreen'} onClick={toggleFullscreen} className="text-white hover:bg-white/20 h-10 w-10 sm:h-8 sm:w-8">
                                {isFullscreen ? <Minimize className="h-4 w-4" /> : <Maximize className="h-4 w-4" />}
                            </Button>
                        </div>
                    </div>
                </div>
            </div>
        )
    }
)
