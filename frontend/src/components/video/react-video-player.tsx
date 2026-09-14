import React, { useState, useCallback, forwardRef } from 'react'
import ReactPlayer from 'react-player'
import type { VideoPlayerHandle } from './native-video-player'

interface ReactVideoPlayerProps {
  src: string
  title?: string
  poster?: string
  autoPlay?: boolean
  controls?: boolean
  className?: string
  onPlay?: () => void
  onPause?: () => void
  onEnded?: () => void
  onTimeUpdate?: (state: { played: number; playedSeconds: number }) => void
  onDuration?: (duration: number) => void
  width?: string | number
  height?: string | number
}

/**
 * ReactPlayer-based video component with YouTube optimization
 * Uses react-player library with reduced YouTube branding
 */
export const ReactVideoPlayer = forwardRef<VideoPlayerHandle, ReactVideoPlayerProps>(
  function ReactVideoPlayer(
    {
      src,
      poster,
      autoPlay = false,
      controls = true,
      className = '',
      onPlay,
      onPause,
      onEnded,
      onTimeUpdate,
      onDuration,
      width = '100%',
      height = '100%'
    },
    _ref
  ) {
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)

    // Handle play state
    const handlePlay = useCallback(() => {
      setLoading(false)
      onPlay?.()
    }, [onPlay])

    // Handle pause state
    const handlePause = useCallback(() => {
      onPause?.()
    }, [onPause])

    // Handle video ended
    const handleEnded = useCallback(() => {
      onEnded?.()
    }, [onEnded])

    // Handle time update
    const handleTimeUpdate = useCallback((progress: { played: number; playedSeconds: number }) => {
      setLoading(false)
      onTimeUpdate?.(progress)
    }, [onTimeUpdate])

    // Handle duration loaded
    const handleDuration = useCallback((duration: number) => {
      onDuration?.(duration)
      setLoading(false)
    }, [onDuration])

    // Handle error
    const handleError = useCallback((error: any) => {
      console.error('Video error:', error)
      setError('Failed to load video')
      setLoading(false)
    }, [])

    // Reset loading state when src changes
    React.useEffect(() => {
      setLoading(true)
      setError(null)
    }, [src])

    return (
      <div className={`relative bg-black overflow-hidden aspect-video ${className}`} style={{ width, height: height || 'auto' }}>
        {/* Loading state */}
        {loading && (
          <div className="absolute inset-0 flex items-center justify-center z-20">
            <div className="text-center">
              <div className="animate-spin rounded-full h-12 w-12 border-4 border-white/20 border-t-blue-500 mx-auto mb-4" />
              <p className="text-white/80 text-sm font-medium">Loading video...</p>
            </div>
          </div>
        )}

        {/* Error state */}
        {error && (
          <div className="absolute inset-0 flex items-center justify-center z-20">
            <div className="text-center p-6 max-w-md">
              <div className="w-16 h-16 rounded-full bg-red-500/20 flex items-center justify-center mx-auto mb-4">
                <svg className="w-8 h-8 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                </svg>
              </div>
              <p className="text-lg font-medium text-white mb-2">Video Error</p>
              <p className="text-sm text-white/70 mb-4">{error}</p>
              <button
                onClick={() => window.location.reload()}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-medium transition-colors"
              >
                Try Again
              </button>
            </div>
          </div>
        )}

        {/* ReactPlayer */}
        <ReactPlayer
          url={src}
          width="100%"
          height="100%"
          playing={autoPlay}
          controls={controls}
          muted={autoPlay} // Auto-play videos are muted by browsers
          light={poster || false}
          playIcon={<></>} // Hide custom play icon
          preview={poster}
          onPlay={handlePlay}
          onPause={handlePause}
          onEnded={handleEnded}
          onProgress={handleTimeUpdate}
          onDuration={handleDuration}
          onError={handleError}
          config={{
            youtube: {
              playerVars: {
                modestbranding: 1,      // Minimal YouTube branding
                rel: 0,                // No related videos
                showinfo: 0,          // Hide video info
                controls: controls ? 1 : 0, // Show/hide controls
                autoplay: autoPlay ? 1 : 0, // Auto-play
                mute: autoPlay ? 1 : 0,    // Auto-mute required for autoplay
                playsinline: 1,       // Mobile compatibility
              },
            },
            vimeo: {
              playerOptions: {
                byline: false,
                portrait: false,
                title: false,
                controls: controls,
                autoplay: autoPlay,
              },
            },
          }}
        />
      </div>
    )
  }
)

export default ReactVideoPlayer