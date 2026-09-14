/**
 * H5P API client — typed wrapper around /api/v1/h5p/* (see
 * backend/app/routers/h5p.py) plus the h5p-specific chunked upload flow
 * (backend/app/routers/chunked_upload.py's `upload_type=h5p` path).
 *
 * Upload contract (read from the backend source, not guessed):
 *  - Small packages (<=20MB): POST /api/v1/h5p/finalize as multipart with a
 *    `file` field (+ optional `title`). No chunked session involved.
 *  - Large packages (up to 100MB): chunked upload via /upload/chunked/{init,
 *    chunk,complete} with upload_type="h5p", THEN POST /api/v1/h5p/finalize
 *    with `chunked_session_id` (+ optional `title`). Per chunked_upload.py's
 *    /complete handler, for upload_type="h5p" the assembled blob is written
 *    OUTSIDE the static /uploads root (h5p_temp/{user_id}/{unique_filename})
 *    and /complete's `file_url` response field is the opaque, NON-servable
 *    string `"h5p_temp/{user_id}/{unique_filename}"` — never a real URL.
 *    /finalize resolves `chunked_session_id` as a FILENAME looked up inside
 *    H5P_TEMP_DIR/{current_user.id}/, so the session id we must send is the
 *    `filename` field from /complete's response (the trailing path segment),
 *    NOT the chunked-upload `upload_id`.
 */
import { api } from './axios'

export interface H5PContent {
  /** Integer PK — the value to store as a Lesson's h5p_content_id FK. */
  id: number
  public_id: string
  owner_id: number
  title: string
  library: string | null
  size_bytes: number
  status: 'uploaded' | 'ready' | 'failed'
  created_at: string
  updated_at: string
  /** Lessons still referencing this package (list endpoint only; I-H4).
   * DELETE 409s while this is > 0. */
  attached_lesson_count?: number
}

export interface H5PContentListResponse {
  contents: H5PContent[]
  count: number
}

export interface H5PResult {
  content_public_id: string
  user_id: number
  score: number | null
  max_score: number | null
  completed: boolean
  updated_at: string
}

export interface H5PResultRow {
  user_id: number
  user_name: string
  user_email: string | null
  score: number | null
  max_score: number | null
  completed: boolean
  updated_at: string
}

export interface H5PResultsListResponse {
  content_public_id: string
  results: H5PResultRow[]
  count: number
}

export interface SubmitH5PResultPayload {
  score?: number | null
  max_score?: number | null
  completed: boolean
}

/** Direct-upload cap enforced server-side too (h5p.py DIRECT_UPLOAD_MAX_BYTES). */
export const H5P_DIRECT_UPLOAD_MAX_BYTES = 20 * 1024 * 1024
/** Chunked-upload cap enforced server-side too (chunked_upload.py /init). */
export const H5P_CHUNKED_UPLOAD_MAX_BYTES = 100 * 1024 * 1024

const CHUNK_SIZE = 1024 * 1024 // 1MB, matches chunked-upload.ts's convention

export interface H5PUploadProgress {
  phase: 'uploading' | 'finalizing'
  percentage: number
}

/** List the caller's own H5P contents (instructor); admin sees all. */
export async function listH5PContents(): Promise<H5PContentListResponse> {
  const response = await api.get<H5PContentListResponse>('/h5p/')
  return response.data
}

/** Fetch metadata for one H5P content item. */
export async function getH5PContent(publicId: string): Promise<H5PContent> {
  const response = await api.get<H5PContent>(`/h5p/${publicId}`)
  return response.data
}

/** Delete an H5P content item (blocked with 409 while a lesson references it). */
export async function deleteH5PContent(publicId: string): Promise<{ success: boolean; public_id: string }> {
  const response = await api.delete(`/h5p/${publicId}`)
  return response.data
}

/** Upsert the caller's advisory result for one H5P content item. */
export async function submitH5PResult(
  publicId: string,
  payload: SubmitH5PResultPayload
): Promise<H5PResult> {
  const response = await api.post<H5PResult>(`/h5p/${publicId}/result`, payload)
  return response.data
}

/** Instructor/admin: per-user rollup of results for one content item. */
export async function listH5PResults(publicId: string): Promise<H5PResultsListResponse> {
  const response = await api.get<H5PResultsListResponse>(`/h5p/${publicId}/results`)
  return response.data
}

/** Finalize a small (<=20MB) direct upload into an H5PContent row. */
async function finalizeDirectUpload(file: File, title?: string): Promise<H5PContent> {
  const formData = new FormData()
  formData.append('file', file)
  if (title) formData.append('title', title)
  const response = await api.post<H5PContent>('/h5p/finalize', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 120000,
  })
  return response.data
}

/** Finalize an already-completed chunked-upload session into an H5PContent row. */
async function finalizeChunkedUpload(chunkedSessionId: string, title?: string): Promise<H5PContent> {
  const formData = new FormData()
  formData.append('chunked_session_id', chunkedSessionId)
  if (title) formData.append('title', title)
  const response = await api.post<H5PContent>('/h5p/finalize', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 120000,
  })
  return response.data
}

/**
 * Extract the chunked-upload session's opaque `filename` (the value
 * /finalize needs as `chunked_session_id`) from /complete's non-servable
 * `file_url` field ("h5p_temp/{user_id}/{unique_filename}"). Falls back to
 * the sibling `filename` field the endpoint also returns, which is the same
 * value — kept for defensiveness against either field being relied on.
 */
function extractChunkedFilename(completeResponse: { file_url?: string; filename?: string }): string {
  if (completeResponse.filename) return completeResponse.filename
  const url = completeResponse.file_url || ''
  const parts = url.split('/')
  return parts[parts.length - 1] || ''
}

/**
 * Upload an `.h5p`/`.zip` package and finalize it into an H5PContent row.
 * Routes to the direct multipart path for files <=20MB, otherwise the
 * chunked-upload path (up to 100MB). `onProgress` reports 0-100 within each
 * phase; callers that just want a single bar can ignore `phase`.
 */
export async function uploadAndFinalizeH5P(
  file: File,
  options?: { title?: string; onProgress?: (progress: H5PUploadProgress) => void }
): Promise<H5PContent> {
  const title = options?.title
  const onProgress = options?.onProgress

  const ext = file.name.slice(file.name.lastIndexOf('.')).toLowerCase()
  if (ext !== '.h5p' && ext !== '.zip') {
    throw new Error("Invalid file type. Only '.h5p' or '.zip' packages are supported.")
  }

  if (file.size > H5P_CHUNKED_UPLOAD_MAX_BYTES) {
    throw new Error('File exceeds the 100MB upload limit for H5P packages.')
  }

  if (file.size <= H5P_DIRECT_UPLOAD_MAX_BYTES) {
    onProgress?.({ phase: 'uploading', percentage: 0 })
    const result = await finalizeDirectUpload(file, title)
    onProgress?.({ phase: 'finalizing', percentage: 100 })
    return result
  }

  // Chunked path.
  const totalChunks = Math.ceil(file.size / CHUNK_SIZE)

  const initForm = new FormData()
  initForm.append('filename', file.name)
  initForm.append('file_size', String(file.size))
  initForm.append('content_type', file.type || 'application/octet-stream')
  initForm.append('total_chunks', String(totalChunks))
  initForm.append('upload_type', 'h5p')
  const initResponse = await api.post<{ upload_id: string }>('/upload/chunked/init', initForm)
  const uploadId = initResponse.data.upload_id

  try {
    for (let chunkNumber = 0; chunkNumber < totalChunks; chunkNumber++) {
      const start = chunkNumber * CHUNK_SIZE
      const end = Math.min(start + CHUNK_SIZE, file.size)
      const chunk = file.slice(start, end)

      const chunkForm = new FormData()
      chunkForm.append('upload_id', uploadId)
      chunkForm.append('chunk_number', String(chunkNumber))
      chunkForm.append('total_chunks', String(totalChunks))
      chunkForm.append('chunk', chunk)

      await api.post('/upload/chunked/chunk', chunkForm, { timeout: 60000 })

      onProgress?.({
        phase: 'uploading',
        percentage: Math.round(((chunkNumber + 1) * 100) / totalChunks),
      })
    }

    const completeForm = new FormData()
    completeForm.append('upload_id', uploadId)
    const completeResponse = await api.post<{ file_url: string; filename: string }>(
      '/upload/chunked/complete',
      completeForm,
      { timeout: 120000 }
    )

    const chunkedSessionId = extractChunkedFilename(completeResponse.data)
    if (!chunkedSessionId) {
      throw new Error('Upload completed but no session file could be resolved for finalize.')
    }

    onProgress?.({ phase: 'finalizing', percentage: 0 })
    const result = await finalizeChunkedUpload(chunkedSessionId, title)
    onProgress?.({ phase: 'finalizing', percentage: 100 })
    return result
  } catch (error) {
    try {
      const cancelForm = new FormData()
      cancelForm.append('upload_id', uploadId)
      await api.post('/upload/chunked/cancel', cancelForm)
    } catch {
      // best-effort cleanup only
    }
    throw error
  }
}
