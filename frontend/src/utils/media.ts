/**
 * Utility functions for handling media URLs (images, videos, etc.)
 */
import { getCertificateUrl,FRONTEND_URL,BACKEND_URL,API_BASE_URL } from '@/config/urls'

/**
 * Get the full URL for a media file
 * In development, Vite proxy handles /uploads requests
 * In production, uploads are served through nginx on main domain
 */
export const getMediaUrl = (url: string | null | undefined): string => {
  if (!url) return ''

  // Handle streaming endpoints (YouTube proxy)
  if (url.startsWith('stream/')) {
    const streamingUrl = `${API_BASE_URL}/${url}`
    return streamingUrl
  }

  // If it's already a full URL (http/https), check if it needs rewriting
  if (url.startsWith('http://') || url.startsWith('https://')) {
    const productionBackendUrl = 'https://backend.sashainfinity.com'
    if (url.startsWith(productionBackendUrl) && BACKEND_URL !== productionBackendUrl) {
      const relativePath = url.replace(productionBackendUrl, '')
      return `${BACKEND_URL}${relativePath}`
    }
    return url
  }

  // /uploads files are served through nginx on main domain in production
  if (url.startsWith('/uploads')) {
    // In development, Vite proxy handles it
    if (import.meta.env.DEV) {
      return url
    }
    // In production, use frontend URL (nginx serves /uploads on main domain)
    return `${FRONTEND_URL}${url.startsWith('/') ? url : '/' + url}`
  }

  // /certificate-files are served through backend
  if (url.startsWith('/certificate-files')) {
    if (import.meta.env.DEV) {
      return url
    }
    return getCertificateUrl(url)
  }

  return url
}

/**
 * Get avatar URL with fallback
 * Handles multiple field names across different user types:
 * - avatar_url (legacy/alias)
 * - profile_photo (UserProfile)
 * - logo_url (Company)
 * - photo (some API responses)
 */
export const getAvatarUrl = (profile: any): string => {
  const url = profile?.avatar_url
    || profile?.profile_photo
    || profile?.logo_url
    || profile?.photo
    || profile?.company_logo
    || ''
  return getMediaUrl(url)
}

/**
 * Get course thumbnail URL with fallback to placeholder
 */
export const getCourseThumbnailUrl = (thumbnail: string | null | undefined): string => {
  const url = getMediaUrl(thumbnail)
  return url || 'https://images.unsplash.com/photo-1516321318423-f06f85e504b3?w=800&h=600&fit=crop'
}

/**
 * Bundled 16:9 thumbnails (in frontend/public/course-thumbnails) matched to a
 * course by keywords in its title. Used to display the official artwork for
 * these courses even before/without a DB `course_thumbnail` value.
 * Returns a public path (e.g. `/course-thumbnails/react-js-mastery.png`) or ''.
 */
export const getLocalCourseThumbnail = (title: string | null | undefined): string => {
  if (!title) return ''
  const t = title.toLowerCase()
  const hasFullStack = /full[\s-]*stack/.test(t)
  // Both live full-stack courses carry "AI" in the title, so the advanced one
  // has to be split off first or it would take the other course's artwork.
  const isAdvanced = /advance/.test(t)

  if (hasFullStack && isAdvanced) return '/course-thumbnails/full-stack-development.png'
  if (hasFullStack) return '/course-thumbnails/full-stack-web-development-ai.png'
  if (t.includes('excel') || t.includes('data analytics')) return '/course-thumbnails/data-analytics-excel-beginner.png'
  if (t.includes('react') && !t.includes('native')) return '/course-thumbnails/react-js-mastery.png'
  return ''
}
