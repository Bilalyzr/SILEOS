/**
 * Chunked Upload Service
 * Handles large file uploads by splitting them into chunks
 */
import axios from 'axios'
import { UploadResponse } from './upload'
import { useAuthStore } from '@/store/auth'

const API_BASE_URL = '/api/v1'
const CHUNK_SIZE = 1024 * 1024 * 1 // 1MB chunks (reduced from 2MB to avoid nginx limits)
const MAX_PARALLEL_UPLOADS = 3 // Maximum concurrent chunk uploads

/**
 * Get auth header from Zustand store
 */
const getAuthHeader = () => {
  const token = useAuthStore.getState().accessToken
  if (token) {
    return { Authorization: `Bearer ${token}` }
  }
  return {}
}

export interface ChunkedUploadProgress {
  uploadedBytes: number
  totalBytes: number
  percentage: number
  currentChunk: number
  totalChunks: number
  speed: number // bytes per second
  estimatedTimeRemaining: number // seconds
}

export interface ChunkUploadResponse {
  chunk_id: string
  chunk_number: number
  received: boolean
}

export interface CompleteUploadResponse extends UploadResponse {
  upload_id: string
}

/**
 * Initialize chunked upload
 */
const initializeUpload = async (
  filename: string,
  fileSize: number,
  fileType: string,
  totalChunks: number,
  uploadType: 'image' | 'video' | 'document'
): Promise<{ upload_id: string }> => {
  const formData = new FormData()
  formData.append('filename', filename)
  formData.append('file_size', fileSize.toString())
  formData.append('content_type', fileType)
  formData.append('total_chunks', totalChunks.toString())
  formData.append('upload_type', uploadType)

  const response = await axios.post(
    `${API_BASE_URL}/upload/chunked/init`,
    formData,
    {
      headers: getAuthHeader()
    }
  )
  return response.data
}

/**
 * Upload a single chunk
 */
const uploadChunk = async (
  uploadId: string,
  chunkNumber: number,
  chunkData: Blob,
  totalChunks: number
): Promise<ChunkUploadResponse> => {
  const formData = new FormData()
  formData.append('upload_id', uploadId)
  formData.append('chunk_number', chunkNumber.toString())
  formData.append('total_chunks', totalChunks.toString())
  formData.append('chunk', chunkData)

  const response = await axios.post<ChunkUploadResponse>(
    `${API_BASE_URL}/upload/chunked/chunk`,
    formData,
    {
      headers: getAuthHeader(),
      timeout: 60000 // 60 second timeout per chunk
    }
  )

  return response.data
}

/**
 * Complete chunked upload and assemble file
 */
const completeUpload = async (uploadId: string): Promise<CompleteUploadResponse> => {
  const formData = new FormData()
  formData.append('upload_id', uploadId)

  const response = await axios.post<CompleteUploadResponse>(
    `${API_BASE_URL}/upload/chunked/complete`,
    formData,
    {
      headers: getAuthHeader(),
      timeout: 120000 // 2 minute timeout for assembly
    }
  )
  return response.data
}

/**
 * Cancel chunked upload
 */
export const cancelChunkedUpload = async (uploadId: string): Promise<void> => {
  const formData = new FormData()
  formData.append('upload_id', uploadId)

  await axios.post(
    `${API_BASE_URL}/upload/chunked/cancel`,
    formData,
    {
      headers: getAuthHeader()
    }
  )
}

/**
 * Upload file with chunking
 */
export const uploadFileChunked = async (
  file: File,
  uploadType: 'image' | 'video' | 'document',
  onProgress?: (progress: ChunkedUploadProgress) => void,
  onChunkComplete?: (chunkNumber: number, totalChunks: number) => void
): Promise<UploadResponse> => {
  const totalChunks = Math.ceil(file.size / CHUNK_SIZE)

  // For small files (< 10MB), use regular upload to avoid chunking overhead
  if (file.size < 10 * 1024 * 1024) {
    // Delegate to regular upload with progress
    const formData = new FormData()
    formData.append('file', file)

    const response = await axios.post<UploadResponse>(
      `${API_BASE_URL}/upload/${uploadType}`,
      formData,
      {
        headers: getAuthHeader(),
        onUploadProgress: (progressEvent) => {
          if (onProgress && progressEvent.total) {
            const percentage = Math.round(
              (progressEvent.loaded * 100) / progressEvent.total
            )
            onProgress({
              uploadedBytes: progressEvent.loaded,
              totalBytes: progressEvent.total,
              percentage,
              currentChunk: 1,
              totalChunks: 1,
              speed: 0,
              estimatedTimeRemaining: 0
            })
          }
        }
      }
    )
    return response.data
  }

  // Initialize upload
  const { upload_id } = await initializeUpload(
    file.name,
    file.size,
    file.type,
    totalChunks,
    uploadType
  )

  let uploadedBytes = 0
  const startTime = Date.now()

  try {
    // Upload chunks in batches for parallel processing
    for (let i = 0; i < totalChunks; i += MAX_PARALLEL_UPLOADS) {
      const batchPromises: Promise<ChunkUploadResponse>[] = []

      // Create batch of chunk uploads
      for (let j = 0; j < MAX_PARALLEL_UPLOADS && i + j < totalChunks; j++) {
        const chunkNumber = i + j
        const start = chunkNumber * CHUNK_SIZE
        const end = Math.min(start + CHUNK_SIZE, file.size)
        const chunk = file.slice(start, end)

        batchPromises.push(
          uploadChunk(upload_id, chunkNumber, chunk, totalChunks).then(
            (response) => {
              uploadedBytes += chunk.size

              // Calculate speed and ETA
              const elapsedTime = (Date.now() - startTime) / 1000 // seconds
              const speed = uploadedBytes / elapsedTime
              const remainingBytes = file.size - uploadedBytes
              const estimatedTimeRemaining = remainingBytes / speed

              // Report progress
              if (onProgress) {
                onProgress({
                  uploadedBytes,
                  totalBytes: file.size,
                  percentage: Math.round((uploadedBytes * 100) / file.size),
                  currentChunk: chunkNumber + 1,
                  totalChunks,
                  speed,
                  estimatedTimeRemaining
                })
              }

              if (onChunkComplete) {
                onChunkComplete(chunkNumber + 1, totalChunks)
              }

              return response
            }
          )
        )
      }

      // Wait for batch to complete
      await Promise.all(batchPromises)
    }

    // Complete upload and assemble file
    const result = await completeUpload(upload_id)

    return {
      success: result.success,
      file_url: result.file_url,
      filename: result.filename,
      original_filename: result.original_filename,
      size: result.size,
      content_type: result.content_type
    }
  } catch (error) {
    // Cancel upload on error
    try {
      await cancelChunkedUpload(upload_id)
    } catch (cancelError) {
      console.error('Failed to cancel upload:', cancelError)
    }
    throw error
  }
}

/**
 * Upload image with chunking
 */
export const uploadImageChunked = async (
  file: File,
  onProgress?: (progress: ChunkedUploadProgress) => void
): Promise<UploadResponse> => {
  return uploadFileChunked(file, 'image', onProgress)
}

/**
 * Upload video with chunking
 */
export const uploadVideoChunked = async (
  file: File,
  onProgress?: (progress: ChunkedUploadProgress) => void,
  onChunkComplete?: (chunkNumber: number, totalChunks: number) => void
): Promise<UploadResponse> => {
  return uploadFileChunked(file, 'video', onProgress, onChunkComplete)
}

/**
 * Upload document with chunking
 */
export const uploadDocumentChunked = async (
  file: File,
  onProgress?: (progress: ChunkedUploadProgress) => void
): Promise<UploadResponse> => {
  return uploadFileChunked(file, 'document', onProgress)
}

/**
 * Format bytes to human readable
 */
export const formatBytes = (bytes: number): string => {
  if (bytes === 0) return '0 Bytes'
  const k = 1024
  const sizes = ['Bytes', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i]
}

/**
 * Format seconds to human readable time
 */
export const formatTime = (seconds: number): string => {
  if (seconds < 60) return `${Math.round(seconds)}s`
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ${Math.round(seconds % 60)}s`
  return `${Math.floor(seconds / 3600)}h ${Math.floor((seconds % 3600) / 60)}m`
}
