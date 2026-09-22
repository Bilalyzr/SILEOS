import { useState,useEffect,forwardRef,useCallback } from 'react'
import { NativeVideoPlayer,type VideoPlayerHandle } from './native-video-player'
import { api } from '@/api/axios'
import { useQuery } from '@tanstack/react-query'
import { getMediaUrl } from '@/utils/media'

// Save progress to backend every 5 seconds
async function saveProgress(lessonId: number, courseId: number, watchedSeconds: number, totalSeconds: number) {
    if (!lessonId || watchedSeconds < 2) return
    try {
        const token = localStorage.getItem('access_token')
        await fetch('/api/v1/progress/save', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
            body: JSON.stringify({ lesson_id: lessonId, course_id: courseId,
                watched_seconds: watchedSeconds, total_seconds: totalSeconds })
        })
    } catch (_) {}
}

async function getResumePosition(lessonId: number): Promise<number> {
    try {
        const token = localStorage.getItem('access_token')
        const r = await fetch(`/api/v1/progress/get/${lessonId}`, {
            headers: { Authorization: `Bearer ${token}` }
        }).then(r => r.json())
        return r.watched_seconds || 0
    } catch (_) { return 0 }
}

// React Query hook for fetching video extraction data
function useVideoExtraction(videoId: string | null, src: string) {
    return useQuery({
        queryKey: ['video-extraction', videoId],
        queryFn: async () => {
            const response = await api.get('/extract/video', {
                params: { url: src, quality: '720' },
                // The backend spawns yt-dlp with a 90s timeout; when YouTube
                // throttles it (bot checks, common in production) every lesson
                // open sat on the "Preparing Video" spinner for that whole
                // window before falling back to the embed. Bound the client
                // wait so the always-working YouTube embed takes over fast;
                // a successful server-side extraction still lands in the
                // shared cache for the next open.
                timeout: 8000,
            })
            return response.data
        },
        enabled: !!videoId,
        staleTime: 4 * 60 * 60 * 1000, // 4 hours
        gcTime: 4 * 60 * 60 * 1000,
        retry: false
    })
}

interface YouTubeExtractedPlayerProps {
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
    onAspectRatio?: (ratio: number) => void
    lessonId?: number
    courseId?: number
}

interface CachedVideo {
    url: string
    expires: number
    title?: string
    thumbnail?: string
    duration?: number
}

/**
 * Extract YouTube video ID from various URL formats
 */
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

/**
 * YouTubeExtractedPlayer - Extracts a direct MP4 stream URL from YouTube
 * via the backend yt-dlp endpoint and plays it through the NativeVideoPlayer.
 *
 * This eliminates all YouTube branding, iframe, and watermarks — the video
 * looks and behaves exactly like a regular uploaded video.
 */
export const YouTubeExtractedPlayer = forwardRef<VideoPlayerHandle, YouTubeExtractedPlayerProps>(
    function YouTubeExtractedPlayer(
        { src, title, poster, autoPlay = false, className = '', onPlay, onPause, onEnded, onTimeUpdate, onDuration, onAspectRatio, lessonId, courseId },
        ref
    ) {
        const [directUrl, setDirectUrl] = useState<string | null>(null)
        const [loading, setLoading] = useState(true)
        const [error, setError] = useState<string | null>(null)
        const [extractedTitle, setExtractedTitle] = useState<string | undefined>(title)
        const [extractedPoster, setExtractedPoster] = useState<string | undefined>(poster)

        const videoId = extractYouTubeId(src)

        // Check localStorage cache
        const getCached = useCallback((): CachedVideo | null => {
            if (!videoId) return null
            try {
                const cached = localStorage.getItem(`yt_extracted_${videoId}`)
                if (cached) {
                    const parsed: CachedVideo = JSON.parse(cached)
                    if (parsed.expires > Date.now()) {
                        return parsed
                    }
                    // Expired — remove
                    localStorage.removeItem(`yt_extracted_${videoId}`)
                }
            } catch {
                // Ignore parse errors
            }
            return null
        }, [videoId])

        // Save to localStorage cache
        const setCache = useCallback((data: CachedVideo) => {
            if (!videoId) return
            try {
                localStorage.setItem(`yt_extracted_${videoId}`, JSON.stringify(data))
            } catch {
                // Ignore storage errors (quota etc.)
            }
        }, [videoId])

        // Extract video URL from backend using React Query
        const { data: extractionData, isLoading: extractionLoading, error: extractionError } = useVideoExtraction(videoId, src)

        useEffect(() => {
            if (!videoId) {
                setError('Invalid YouTube URL')
                setLoading(false)
                return
            }

            // Check cache first (before React Query kicks in)
            const cached = getCached()
            if (cached) {
                setDirectUrl(cached.url)
                if (cached.title) setExtractedTitle(cached.title)
                if (cached.thumbnail) setExtractedPoster(cached.thumbnail)
                setLoading(false)
                return
            }

            // Handle React Query results
            if (extractionLoading) {
                setLoading(true)
                setError(null)
                return
            }

            if (extractionError) {
                setError((extractionError as any)?.response?.data?.error || (extractionError as any)?.message || 'Failed to extract video')
                setLoading(false)
                return
            }

            if (extractionData?.success && extractionData?.data?.url) {
                const videoData = extractionData.data
                const cacheEntry: CachedVideo = {
                    url: videoData.url,
                    expires: Date.now() + (4 * 60 * 60 * 1000), // 4 hours
                    title: videoData.title,
                    thumbnail: videoData.thumbnail,
                    duration: videoData.duration
                }

                setDirectUrl(cacheEntry.url)
                if (videoData.title && !title) setExtractedTitle(videoData.title)
                if (videoData.thumbnail && !poster) setExtractedPoster(videoData.thumbnail)
                if (videoData.duration && onDuration) onDuration(videoData.duration)
                setCache(cacheEntry)
                setLoading(false)

                // Resume from last position - use the URL directly since directUrl isn't set yet
                if (lessonId) {
                    const targetUrl = cacheEntry.url
                    const resolvedUrl = getMediaUrl(targetUrl)
                    getResumePosition(lessonId).then(secs => {
                        if (secs > 5) {
                            // Find the video element after it's mounted and set currentTime
                            setTimeout(() => {
                                const videos = document.querySelectorAll('video')
                                for (const vid of Array.from(videos)) {
                                    if (vid.src === resolvedUrl || vid.currentSrc === resolvedUrl ||
                                        vid.src === targetUrl || vid.currentSrc === targetUrl) {
                                        vid.currentTime = secs
                                        break
                                    }
                                }
                            }, 100)
                        }
                    })
                }
            } else if (extractionData && !extractionData.success) {
                setError(extractionData?.error || 'Failed to extract video URL')
                setLoading(false)
            }
        }, [src, videoId, getCached, setCache, extractionLoading, extractionError, extractionData, title, poster, onDuration, lessonId, directUrl])

        // Periodically persist watch position.
        // NOTE: must stay above the early returns below — a hook after a
        // conditional `return` changes the hook count between renders and React
        // throws "Rendered more hooks than during the previous render".
        useEffect(() => {
            if (!lessonId || !directUrl) return

            // Resolve the URL the same way NativeVideoPlayer does
            const resolvedUrl = getMediaUrl(directUrl)

            // Find the video element that matches our resolved URL
            const findOurVideo = (): HTMLVideoElement | null => {
                const videos = document.querySelectorAll('video')
                for (const vid of Array.from(videos)) {
                    if (vid.src === resolvedUrl || vid.currentSrc === resolvedUrl ||
                        vid.src === directUrl || vid.currentSrc === directUrl) {
                        return vid
                    }
                }
                return null
            }

            // Cache the video element reference after first successful find
            let cachedVideo: HTMLVideoElement | null = null

            const interval = setInterval(() => {
                const vid = cachedVideo ?? findOurVideo()
                if (vid) {
                    cachedVideo = vid
                    if (!vid.paused && vid.currentTime > 0) {
                        saveProgress(lessonId, courseId || 0, vid.currentTime, vid.duration || 0)
                    }
                }
            }, 5000)
            return () => clearInterval(interval)
        }, [lessonId, courseId, directUrl])

        // Loading state — fills the stage the parent sized, no nested aspect box
        if (loading) {
            return (
                <div className={`flex items-center justify-center bg-black text-white w-full h-full ${className}`}>
                    <div className="text-center p-8">
                        <div className="relative mb-6">
                            <div className="animate-spin rounded-full h-14 w-14 border-4 border-white/20 border-t-primary-500 mx-auto" />
                            <div className="absolute inset-0 flex items-center justify-center">
                                <svg className="w-6 h-6 text-white/60" viewBox="0 0 24 24" fill="currentColor">
                                    <path d="M8 5v14l11-7z" />
                                </svg>
                            </div>
                        </div>
                        <p className="text-lg font-medium text-white/80 mb-1">Preparing Video</p>
                        <p className="text-sm text-neutral-500">Extracting stream from source...</p>
                    </div>
                </div>
            )
        }

        // Error state — fall back to a plain YouTube iframe embed so the
        // lesson still plays when stream extraction is unavailable (bot
        // checks, yt-dlp breakage, rate limits). Only show the error panel
        // when we cannot even build an embed URL.
        if (error || !directUrl) {
            if (videoId) {
                return (
                    <div className={`relative bg-black w-full aspect-video ${className}`}>
                        <iframe
                            src={`https://www.youtube.com/embed/${videoId}?rel=0&modestbranding=1`}
                            title={title || 'YouTube Video'}
                            className="w-full h-full"
                            frameBorder="0"
                            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
                            allowFullScreen
                            referrerPolicy="strict-origin-when-cross-origin"
                        />
                    </div>
                )
            }
            return (
                <div className={`flex items-center justify-center bg-black text-white w-full h-full ${className}`}>
                    <div className="text-center p-4 sm:p-8 max-w-md">
                        <div className="w-16 h-16 rounded-full bg-red-500/20 flex items-center justify-center mx-auto mb-4">
                            <svg className="w-8 h-8 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                            </svg>
                        </div>
                        <p className="text-lg font-medium mb-2">Video Unavailable</p>
                        <p className="text-sm text-neutral-400 mb-4">{error || 'Could not load video stream.'}</p>
                        <button
                            onClick={() => window.location.reload()}
                            className="px-4 py-2 bg-primary-600 hover:bg-primary-700 rounded-lg text-sm font-medium transition-colors"
                        >
                            Try Again
                        </button>
                    </div>
                </div>
            )
        }

        // Success — render through native player (no YouTube branding)
        return (
            <NativeVideoPlayer
                ref={ref}
                src={directUrl}
                title={extractedTitle}
                poster={extractedPoster}
                autoPlay={autoPlay}
                className={className}
                onPlay={onPlay}
                onPause={onPause}
                onEnded={onEnded}
                onTimeUpdate={onTimeUpdate}
                onDuration={onDuration}
                onAspectRatio={onAspectRatio}
            />
        )
    }
)

export { extractYouTubeId as extractYouTubeIdFromUrl }
