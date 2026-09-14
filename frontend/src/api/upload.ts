/**
 * Upload API - File upload service
 */
import axios from 'axios'
import { useAuthStore } from '@/store/auth'

/**
 * Join the API base with an endpoint path.
 *
 * The previous form was `${baseURL}${path}`.replace(/\/+/g, '/'), which
 * collapsed EVERY run of slashes in the string — including the "//" in the
 * scheme. VITE_API_URL is absolute by default (docker-compose.yml sets
 * https://backend.sashainfinity.com/api/v1), so that rewrote "https://" to
 * "https:/" and every upload went to a malformed URL. That is the image error
 * hit when creating a blog post; it broke uploads on any deployment where the
 * base is absolute rather than the relative "/api/v1" used in local dev.
 *
 * Only the join needs normalising: trim trailing slashes off the base and
 * guarantee exactly one leading slash on the path.
 */
const uploadUrl = (path: string): string => {
  const base = (import.meta.env.VITE_API_URL || '/api/v1').replace(/\/+$/, '')
  return `${base}/${path.replace(/^\/+/, '')}`
}

// Create a separate axios instance for file uploads without default Content-Type
const uploadApi = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api/v1',
  timeout: 300000,
  headers: {
    // Don't set Content-Type - let browser set it with boundary for FormData
  }
})

// Add auth token interceptor for upload API
uploadApi.interceptors.request.use((config) => {
  const token = useAuthStore.getState().accessToken
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

export interface UploadResponse {
  success: boolean
  file_url: string
  filename: string
  original_filename: string
  size: number
  content_type: string
}

export interface UploadInfo {
  max_image_size_mb: number
  max_video_size_mb: number
  max_document_size_mb: number
  allowed_image_types: string[]
  allowed_video_types: string[]
  allowed_document_types: string[]
}

/**
 * Upload image file - using fetch API for proper multipart handling
 */
export const uploadImage = async (file: File): Promise<UploadResponse> => {
  const formData = new FormData()
  formData.append('file', file)

  const token = useAuthStore.getState().accessToken
  const url = uploadUrl('/upload/image')

  const response = await fetch(url, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      // Note: NOT setting Content-Type - let browser set it with boundary
    },
    body: formData
  })

  if (!response.ok) {
    throw new Error(`Upload failed: ${response.status}`)
  }

  return await response.json()
}

/**
 * Upload video file - using fetch API for proper multipart handling
 */
export const uploadVideo = async (
  file: File,
  _onProgress?: (progress: number) => void
): Promise<UploadResponse> => {
  const formData = new FormData()
  formData.append('file', file)

  const token = useAuthStore.getState().accessToken
  const url = uploadUrl('/upload/video')

  const response = await fetch(url, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
    },
    body: formData
  })

  if (!response.ok) {
    throw new Error(`Upload failed: ${response.status}`)
  }

  return await response.json()
}

/**
 * Upload document file - using fetch API for proper multipart handling
 */
export const uploadDocument = async (
  file: File,
  _onProgress?: (progress: number) => void,
  context?: string
): Promise<UploadResponse> => {
  const formData = new FormData()
  formData.append('file', file)

  const token = useAuthStore.getState().accessToken
  // Build URL with context query parameter
  const url = new URL(uploadUrl('/upload/document'), window.location.origin)
  if (context) {
    url.searchParams.set('context', context)
  }

  const response = await fetch(url.toString(), {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
    },
    body: formData
  })

  if (!response.ok) {
    throw new Error(`Upload failed: ${response.status}`)
  }

  return await response.json()
}

/**
 * Delete uploaded file - using fetch API
 */
export const deleteFile = async (fileUrl: string): Promise<{ success: boolean; message: string }> => {
  const token = useAuthStore.getState().accessToken
  const url = uploadUrl('/upload/file')

  const response = await fetch(`${url}?file_url=${encodeURIComponent(fileUrl)}`, {
    method: 'DELETE',
    headers: {
      'Authorization': `Bearer ${token}`,
    }
  })

  if (!response.ok) {
    throw new Error(`Delete failed: ${response.status}`)
  }

  return await response.json()
}

/**
 * Get upload configuration info - using fetch API
 */
export const getUploadInfo = async (): Promise<UploadInfo> => {
  const token = useAuthStore.getState().accessToken
  const url = uploadUrl('/upload/info')

  const response = await fetch(url, {
    headers: {
      'Authorization': `Bearer ${token}`,
    }
  })

  if (!response.ok) {
    throw new Error(`Get upload info failed: ${response.status}`)
  }

  return await response.json()
}
