import { forwardRef } from 'react'
import { NativeVideoPlayer, type VideoPlayerHandle } from './native-video-player'
import { YouTubeExtractedPlayer } from './youtube-extracted-player'

interface VideoPlayerProps {
  src: string
  title?: string
  duration?: number
  poster?: string
  autoPlay?: boolean
  controls?: boolean
  className?: string
  onPlay?: () => void
  onPause?: () => void
  onEnded?: () => void
  onTimeUpdate?: (state: { played: number; playedSeconds: number }) => void
  onDuration?: (duration: number) => void
  /** Real width/height of the stream, so the caller can size its stage to match. */
  onAspectRatio?: (ratio: number) => void
  lessonId?: number
  courseId?: number
}

/**
 * Detect if a URL points at Bunny.net video hosting.
 */
export function isBunnyUrl(url: string): boolean {
  if (!url) return false
  return url.includes('mediadelivery.net') || url.includes('b-cdn.net/play')
}

/**
 * Detect if a URL is a YouTube URL
 */
export function isYouTubeUrl(url: string): boolean {
  if (!url) return false
  const patterns = [
    /(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([^&\n?#]+)/,
    /youtube\.com\/shorts\/([^&\n?#]+)/
  ]
  return patterns.some(p => p.test(url))
}

/**
 * Smart video player wrapper that detects the video source type
 * and renders the appropriate player component.
 *
 * - YouTube URLs → YouTubeExtractedPlayer (extracts direct MP4 via backend, plays natively — no YouTube branding)
 * - Direct video files → NativeVideoPlayer (HTML5 <video>)
 */
export const VideoPlayer = forwardRef<VideoPlayerHandle, VideoPlayerProps>(
  function VideoPlayer({ src, title, poster, autoPlay, className, onPlay, onPause, onEnded, onTimeUpdate, onDuration, onAspectRatio }, ref) {
    if (!src) {
      return (
        <div className={`flex items-center justify-center w-full h-full bg-black text-white/60 ${className ?? ''}`}>
          <div className="text-center p-4 sm:p-8">
            <p className="text-lg font-medium mb-2">No Video Available</p>
            <p className="text-sm text-neutral-500">This lesson does not have a video attached.</p>
          </div>
        </div>
      )
    }

    // Bunny.net player URL → iframe embed.
    // The URL is used exactly as stored. Rewriting it to Bunny's /embed/ route
    // was tried and reverted: that route returns Bunny's 403 page when the
    // library has token auth or referrer restrictions enabled.
    if (isBunnyUrl(src)) {
      return (
        <div
          className={`relative w-full overflow-hidden bg-black ${className ?? ''}`}
          style={{ height: '100%', aspectRatio: '16 / 9' }}
        >
          <iframe
            src={src}
            title={title ?? 'Video'}
            className="absolute inset-0 w-full h-full"
            allow="accelerometer; gyroscope; autoplay; encrypted-media; picture-in-picture; fullscreen"
            allowFullScreen
            style={{ border: 'none' }}
          />
        </div>
      )
    }
    // YouTube URL → extract direct stream via backend, play natively (no branding)
    if (isYouTubeUrl(src)) {
      return (
        <YouTubeExtractedPlayer
          ref={ref}
          src={src}
          title={title}
          poster={poster}
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

    // Direct video file → native HTML5 player
    return (
      <NativeVideoPlayer
        ref={ref}
        src={src}
        title={title}
        poster={poster}
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

// Re-export the handle type and the helper
export type { VideoPlayerHandle } from './native-video-player'