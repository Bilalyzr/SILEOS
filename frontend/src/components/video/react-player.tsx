import { forwardRef } from 'react'
import { ReactVideoPlayer } from './react-video-player'
import { isYouTubeUrl } from './video-player'

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
}

/**
 * Smart video player wrapper that detects the video source type
 * and renders the appropriate react-player component.
 *
 * - YouTube URLs → ReactVideoPlayer with optimized YouTube embedding
 * - Direct video files → ReactVideoPlayer (HTML5 video via react-player)
 */
export const VideoPlayer = forwardRef<any, VideoPlayerProps>(
  function VideoPlayer({ src, title, poster, autoPlay, controls = true, className, onPlay, onPause, onEnded, onTimeUpdate, onDuration }, ref) {
    if (!src) {
      return (
        <div className={`flex items-center justify-center bg-black text-white/60 ${className ?? ''}`}>
          <div className="text-center p-8">
            <p className="text-lg font-medium mb-2">No Video Available</p>
            <p className="text-sm text-neutral-500">This lesson does not have a video attached.</p>
          </div>
        </div>
      )
    }

    // YouTube URL → use react-player with optimized YouTube parameters
    if (isYouTubeUrl(src)) {
      return (
        <ReactVideoPlayer
          ref={ref}
          src={src}
          title={title}
          poster={poster}
          autoPlay={autoPlay}
          controls={controls}
          className={className}
          onPlay={onPlay}
          onPause={onPause}
          onEnded={onEnded}
          onTimeUpdate={onTimeUpdate}
          onDuration={onDuration}
        />
      )
    }

    // Direct video file → use react-player
    return (
      <ReactVideoPlayer
        ref={ref}
        src={src}
        title={title}
        poster={poster}
        autoPlay={autoPlay}
        controls={controls}
        className={className}
        onPlay={onPlay}
        onPause={onPause}
        onEnded={onEnded}
        onTimeUpdate={onTimeUpdate}
        onDuration={onDuration}
      />
    )
  }
)

// Re-export the helper
export { isYouTubeUrl } from './video-player'