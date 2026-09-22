/**
 * H5PPicker — instructor lesson-editor widget (plan Task 5 deliverable 5):
 * pick one of the instructor's own H5P contents, or upload a new `.h5p`/
 * `.zip` package. Small files (<=20MB) use the direct-upload finalize path;
 * larger files (up to 100MB) go through the chunked-upload flow — both
 * implemented in api/h5p.ts against the documented backend contract.
 *
 * `value`/`onChange` operate on H5PContent's integer `id` (the value stored
 * as the lesson's `h5p_content_id` FK) — NOT `public_id`, which is only
 * used for the player URL and result endpoints.
 */
import * as React from 'react'
import { Loader2, UploadCloud, CheckCircle2, AlertTriangle, RefreshCw, Eye, X } from 'lucide-react'
import { toast } from 'react-hot-toast'
import {
  listH5PContents,
  uploadAndFinalizeH5P,
  H5P_CHUNKED_UPLOAD_MAX_BYTES,
  type H5PContent,
  type H5PUploadProgress,
} from '@/api/h5p'
import { H5PLesson } from './H5PLesson'

export interface H5PPickerProps {
  value?: number | null
  onChange: (contentId: number | null) => void
  className?: string
}

export const H5PPicker: React.FC<H5PPickerProps> = ({ value, onChange, className = '' }) => {
  const [contents, setContents] = React.useState<H5PContent[]>([])
  const [loading, setLoading] = React.useState(true)
  const [loadError, setLoadError] = React.useState<string | null>(null)
  const [uploading, setUploading] = React.useState(false)
  const [uploadProgress, setUploadProgress] = React.useState<H5PUploadProgress | null>(null)
  const [previewOpen, setPreviewOpen] = React.useState(false)
  const fileInputRef = React.useRef<HTMLInputElement>(null)

  const refreshList = React.useCallback(async () => {
    setLoading(true)
    setLoadError(null)
    try {
      const res = await listH5PContents()
      setContents(res.contents)
      return res.contents
    } catch (err: any) {
      setLoadError(err?.response?.data?.detail || 'Failed to load your H5P uploads')
      return []
    } finally {
      setLoading(false)
    }
  }, [])

  React.useEffect(() => {
    refreshList()
  }, [refreshList])

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    const ext = file.name.slice(file.name.lastIndexOf('.')).toLowerCase()
    if (ext !== '.h5p' && ext !== '.zip') {
      toast.error("Please select a '.h5p' or '.zip' package")
      if (fileInputRef.current) fileInputRef.current.value = ''
      return
    }
    if (file.size > H5P_CHUNKED_UPLOAD_MAX_BYTES) {
      toast.error('File exceeds the 100MB upload limit for H5P packages')
      if (fileInputRef.current) fileInputRef.current.value = ''
      return
    }

    setUploading(true)
    setUploadProgress({ phase: 'uploading', percentage: 0 })
    try {
      const created = await uploadAndFinalizeH5P(file, {
        title: file.name.replace(/\.(h5p|zip)$/i, ''),
        onProgress: setUploadProgress,
      })
      toast.success('H5P package uploaded and validated')
      await refreshList()
      // Auto-select the package that was just uploaded.
      onChange(created.id)
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || err?.message || 'Upload failed')
    } finally {
      setUploading(false)
      setUploadProgress(null)
      if (fileInputRef.current) fileInputRef.current.value = ''
    }
  }

  const selectedContent = contents.find((c) => c.id === value)

  return (
    <div className={`space-y-3 ${className}`}>
      <div className="space-y-2">
        <label className="block text-sm font-medium text-gray-700">Select H5P content</label>
        {loading ? (
          <div className="flex items-center gap-2 text-sm text-gray-500">
            <Loader2 className="w-4 h-4 animate-spin" /> Loading your uploads&hellip;
          </div>
        ) : loadError ? (
          <div className="flex items-center gap-2 text-sm text-red-600">
            <AlertTriangle className="w-4 h-4" /> {loadError}
            <button type="button" onClick={refreshList} className="ml-2 text-blue-600 hover:underline inline-flex items-center gap-1">
              <RefreshCw className="w-3 h-3" /> Retry
            </button>
          </div>
        ) : (
          <select
            value={value ?? ''}
            onChange={(e) => onChange(e.target.value ? Number(e.target.value) : null)}
            className="w-full px-3 py-2 text-sm border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            <option value="">— Choose an uploaded H5P package —</option>
            {contents.map((c) => (
              <option key={c.id} value={c.id} disabled={c.status !== 'ready'}>
                {c.title} {c.status !== 'ready' ? `(${c.status})` : ''}
              </option>
            ))}
          </select>
        )}
      </div>

      <div>
        <input
          ref={fileInputRef}
          type="file"
          accept=".h5p,.zip"
          onChange={handleFileSelect}
          className="hidden"
          id="h5p-upload-input"
        />
        <button
          type="button"
          onClick={() => fileInputRef.current?.click()}
          disabled={uploading}
          className="w-full flex items-center justify-center gap-2 px-4 py-2.5 text-sm border-2 border-dashed border-gray-300 rounded-lg hover:border-blue-500 transition-colors bg-gray-50 hover:bg-gray-100 disabled:opacity-50"
        >
          {uploading ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin text-blue-500" />
              <span>
                {uploadProgress?.phase === 'finalizing' ? 'Validating package…' : `Uploading… ${uploadProgress?.percentage ?? 0}%`}
              </span>
            </>
          ) : (
            <>
              <UploadCloud className="w-4 h-4 text-gray-400" />
              <span>Upload new H5P package (.h5p or .zip, up to 100MB)</span>
            </>
          )}
        </button>
      </div>

      {selectedContent && (
        <div className="flex items-center justify-between gap-2">
          <p className="text-xs text-gray-500 flex items-center gap-1">
            <CheckCircle2 className="w-3.5 h-3.5 text-green-600" /> Selected: {selectedContent.title}
            {selectedContent.status !== 'ready' && ` (${selectedContent.status})`}
          </p>
          {selectedContent.status === 'ready' && (
            <button
              type="button"
              onClick={() => setPreviewOpen(true)}
              className="inline-flex items-center gap-1 text-xs font-medium text-blue-600 hover:text-blue-700 hover:underline shrink-0"
            >
              <Eye className="w-3.5 h-3.5" /> Preview
            </button>
          )}
        </div>
      )}

      {previewOpen && selectedContent && (
        <div
          className="fixed inset-0 z-[100] bg-black/70 flex items-center justify-center p-4"
          onClick={() => setPreviewOpen(false)}
        >
          <div
            className="bg-white rounded-2xl max-w-3xl w-full overflow-hidden shadow-2xl"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between px-5 py-3 border-b border-gray-100">
              <p className="font-semibold text-gray-900">{selectedContent.title}</p>
              <button
                type="button"
                onClick={() => setPreviewOpen(false)}
                aria-label="Close preview"
                className="text-gray-400 hover:text-gray-700"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="bg-neutral-950" style={{ height: '70vh' }}>
              {/* previewOnly: same sandboxed iframe, but result-POST and
                  onCompleted side effects are suppressed — an instructor
                  play-through must never write an advisory result or mark
                  a real lesson complete. */}
              <H5PLesson
                contentId={selectedContent.public_id}
                title={selectedContent.title}
                previewOnly
              />
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default H5PPicker
