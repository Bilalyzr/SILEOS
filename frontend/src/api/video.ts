import { api } from './axios'

export interface VideoData {
  videoId: string
  title: string
  url: string
  duration: number
  quality: string
  thumbnail: string
  description: string
  author: string
  upload_date: string
  view_count: number
  expires: number
  cached: boolean
}

export interface VideoExtractionResponse {
  success: boolean
  data: VideoData
  error?: string
}

export class VideoService {
  /**
   * Extract video URL from YouTube URL
   */
  static async extractVideoUrl(
    url: string,
    quality: string = '720'
  ): Promise<VideoExtractionResponse> {
    try {
      const response = await api.get('/stream/extract', {
        params: {
          url,
          quality
        }
      })

      return {
        success: response.data.success,
        data: response.data.data,
        error: response.data.error
      }
    } catch (error: any) {
      return {
        success: false,
        data: {} as VideoData,
        error: error.response?.data?.detail || 'Failed to extract video URL'
      }
    }
  }

  /**
   * Extract video ID from various YouTube URL formats
   */
  static extractVideoId(url: string): string | null {
    const patterns = [
      /(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([^&\n?#]+)/,
      /youtube\.com\/shorts\/([^&\n?#]+)/
    ]

    for (const pattern of patterns) {
      const match = url.match(pattern)
      if (match) {
        return match[1]
      }
    }
    return null
  }

  /**
   * Check if URL is a YouTube URL
   */
  static isYouTubeUrl(url: string): boolean {
    const patterns = [
      /youtube\.com\/watch\?v=/,
      /youtu\.be\//,
      /youtube\.com\/embed\//,
      /youtube\.com\/shorts\//
    ]

    return patterns.some(pattern => pattern.test(url))
  }

  /**
   * Clear video cache
   */
  static clearVideoCache(videoId?: string): void {
    if (videoId) {
      localStorage.removeItem(`video_${videoId}`)
    } else {
      // Clear all video cache
      const keys = Object.keys(localStorage)
      keys.forEach(key => {
        if (key.startsWith('video_')) {
          localStorage.removeItem(key)
        }
      })
    }
  }

  /**
   * Get cache status
   */
  static getCacheStatus(): { totalVideos: number; cachedVideos: string[] } {
    const keys = Object.keys(localStorage)
    const cachedVideos = keys.filter(key => key.startsWith('video_'))

    return {
      totalVideos: cachedVideos.length,
      cachedVideos
    }
  }
}