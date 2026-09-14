import { useState, useImperativeHandle, forwardRef } from 'react'
import type { VideoPlayerHandle } from './native-video-player'

interface YouTubePlayerProps {
    src: string
    title?: string
    autoPlay?: boolean
    className?: string
}

// Utility: extract YouTube video ID from various URL formats
function extractYouTubeId(url: string): string | null {
    if (!url) return null
    const patterns = [
        /(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([^&\n?#]+)/,
        /youtube\.com\/shorts\/([^&\n?#]+)/
    ]
    for (const p of patterns) {
        const m = url.match(p)
        if (m) return m[1]
    }
    return null
}

export function isYouTubeUrl(url: string): boolean {
    return extractYouTubeId(url) !== null
}

export const YouTubePlayer = forwardRef<VideoPlayerHandle, YouTubePlayerProps>(
    function YouTubePlayer(
        { src, title, autoPlay = false, className = '' },
        ref
    ) {
        const videoId = extractYouTubeId(src)
        const [iframeLoaded, setIframeLoaded] = useState(false)

        // Build embed URL with relevant params
        const embedUrl = videoId
            ? `https://www.youtube.com/embed/${videoId}?rel=0&modestbranding=1&showinfo=0&autoplay=${autoPlay ? 1 : 0}&enablejsapi=1`
            : ''

        // For YouTube iframe embeds, we have limited programmatic control
        // The YouTube IFrame API would be needed for full control, but for now
        // the iframe's native controls handle play/pause/seek
        useImperativeHandle(ref, () => ({
            play: () => { /* YouTube iframe handles its own playback */ },
            pause: () => { /* YouTube iframe handles its own playback */ },
            seekTo: () => { /* YouTube iframe handles its own seeking */ },
            getCurrentTime: () => 0,
            getDuration: () => 0,
        }), [])

        if (!videoId) {
            return (
                <div className={`flex items-center justify-center bg-black text-white aspect-video ${className}`}>
                    <div className="text-center p-8">
                        <p className="text-lg font-medium mb-2">Invalid YouTube URL</p>
                        <p className="text-sm text-neutral-400">The provided URL could not be recognized as a YouTube video.</p>
                    </div>
                </div>
            )
        }

        return (
            <div className={`relative bg-black w-full aspect-video ${className}`}>
                {/* Loading state */}
                {!iframeLoaded && (
                    <div className="absolute inset-0 flex items-center justify-center z-10">
                        <div className="text-center">
                            <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-white mx-auto mb-3" />
                            <p className="text-white/70 text-sm">Loading YouTube video...</p>
                        </div>
                    </div>
                )}

                {/* YouTube iframe */}
                <iframe
                    src={embedUrl}
                    title={title || 'YouTube Video'}
                    className="w-full h-full"
                    frameBorder="0"
                    allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
                    allowFullScreen
                    referrerPolicy="strict-origin-when-cross-origin"
                    onLoad={() => setIframeLoaded(true)}
                />

                {/* YouTube info badge */}
                <div className="absolute top-3 left-3 z-10 pointer-events-none">
                    <div className="bg-red-600/90 backdrop-blur-sm rounded px-2 py-1 flex items-center gap-1.5">
                        <svg className="w-4 h-4 text-white" viewBox="0 0 24 24" fill="currentColor">
                            <path d="M23.498 6.094a2.996 2.996 0 00-2.107-2.117C19.502 3.5 12 3.5 12 3.5s-7.502 0-9.391.477A2.996 2.996 0 00.502 6.094C0 7.97 0 12 0 12s0 4.03.502 5.906a2.996 2.996 0 002.107 2.117C4.498 20.5 12 20.5 12 20.5s7.502 0 9.391-.477a2.996 2.996 0 002.107-2.117C24 16.03 24 12 24 12s0-4.03-.502-5.906zM9.545 15.568V8.432L15.818 12l-6.273 3.568z" />
                        </svg>
                        <span className="text-white text-xs font-medium">YouTube</span>
                    </div>
                </div>
            </div>
        )
    }
)
