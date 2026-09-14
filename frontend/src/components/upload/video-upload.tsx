import React from 'react'
import { X, Loader2, Video as VideoIcon } from 'lucide-react'
import { api } from '@/api/axios'
import { toast } from 'react-hot-toast'

interface VideoUploadProps {
  value?: string
  onChange: (url: string) => void
  onDurationChange?: (duration: number) => void
  description?: string
  label?: string
  className?: string
}

export const VideoUpload: React.FC<VideoUploadProps> = ({
  value, description, onChange, onDurationChange, label = 'Upload Video', className = ''
}) => {
  const [isUploading, setIsUploading] = React.useState(false)
  const [uploadProgress, setUploadProgress] = React.useState(0)
  const [videoUrl, setVideoUrl] = React.useState<string | null>(value || null)
  const [processing, setProcessing] = React.useState(false)
  const fileInputRef = React.useRef<HTMLInputElement>(null)

  const prevValue = React.useRef(value)
  React.useEffect(() => {
    // Only update if value changes from outside (not from our own upload)
    if (value !== prevValue.current && !value?.includes('bunny')) {
      setVideoUrl(value || null)
    }
    prevValue.current = value
  }, [value])

  const extractDuration = (file: File): Promise<number> => new Promise((resolve) => {
    const v = document.createElement('video')
    v.preload = 'metadata'
    v.onloadedmetadata = () => { URL.revokeObjectURL(v.src); resolve(Math.ceil(v.duration / 60)) }
    v.onerror = () => resolve(0)
    v.src = URL.createObjectURL(file)
  })

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    if (!file.type.startsWith('video/')) { toast.error('Please select a video file'); return }
    if (file.size > 2 * 1024 * 1024 * 1024) { toast.error('Video must be less than 2GB'); return }

    try {
      setIsUploading(true)
      setUploadProgress(0)

      if (onDurationChange) {
        const dur = await extractDuration(file)
        if (dur) onDurationChange(dur)
      }

      const formData = new FormData()
      formData.append('file', file)

      const response = await api.post('/bunny/video', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        timeout: 3600000, // 1 hour timeout for large videos
        maxBodyLength: Infinity,
        maxContentLength: Infinity,
        onUploadProgress: (e) => {
          if (e.total) setUploadProgress(Math.round((e.loaded * 100) / e.total))
        }
      })

      if (response.data.success) {
        setVideoUrl(response.data.file_url)
        onChange(response.data.file_url)
        setProcessing(true)
        toast.success('Video uploaded! Processing may take a few minutes.')
        // Poll until ready
        const videoId = response.data.video_id
        const poll = setInterval(async () => {
          try {
            const s = await api.get(`/bunny/video/${videoId}/status`)
            if (s.data.ready) { setProcessing(false); clearInterval(poll); toast.success('Video ready!') }
          } catch { clearInterval(poll) }
        }, 5000)
      }
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Upload failed')
      setVideoUrl(value || null)
    } finally {
      setIsUploading(false)
      setUploadProgress(0)
      if (fileInputRef.current) fileInputRef.current.value = ''
    }
  }

  return (
    <div className={`space-y-2 ${className}`}>
      {label && <label className="block text-sm font-medium text-gray-700">{label}</label>}
      {description && <p className="text-sm text-neutral-500">{description}</p>}
      <div className="relative">
        {videoUrl ? (
          <div className="relative aspect-video w-full rounded-lg overflow-hidden border-2 border-gray-200 bg-black flex items-center justify-center">
            {processing ? (
              <div className="text-center text-white p-4">
                <Loader2 className="w-8 h-8 animate-spin mx-auto mb-2" />
                <p className="text-sm">Processing video on Bunny CDN...</p>
                <p className="text-xs text-gray-400 mt-1">This may take a few minutes</p>
              </div>
            ) : (
              <div className="text-center text-white p-4">
                <VideoIcon className="w-12 h-12 mx-auto mb-2 text-green-400" />
                <p className="text-sm font-medium text-green-400">Video uploaded to Bunny CDN ✓</p>
                <p className="text-xs text-gray-400 mt-1 break-all px-4">{videoUrl}</p>
              </div>
            )}
            <button type="button" onClick={() => { setVideoUrl(null); onChange('') }}
              className="absolute top-2 right-2 p-2 bg-red-500 text-white rounded-full hover:bg-red-600 z-10">
              <X className="w-4 h-4" />
            </button>
          </div>
        ) : (
          <button type="button" onClick={() => fileInputRef.current?.click()}
            disabled={isUploading}
            className="aspect-video w-full border-2 border-dashed border-gray-300 rounded-lg hover:border-orange-500 transition-colors flex flex-col items-center justify-center space-y-2 bg-gray-50 hover:bg-gray-100 disabled:opacity-50">
            {isUploading ? (
              <div className="flex flex-col items-center space-y-3 w-full px-8">
                <Loader2 className="w-8 h-8 text-orange-500 animate-spin" />
                <p className="text-sm text-gray-700">Uploading to Bunny CDN... {uploadProgress}%</p>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div className="bg-orange-500 h-2 rounded-full transition-all" style={{ width: `${uploadProgress}%` }} />
                </div>
              </div>
            ) : (
              <>
                <VideoIcon className="w-8 h-8 text-gray-400" />
                <div className="text-center">
                  <span className="text-sm text-orange-600 font-medium">Click to upload to Bunny CDN</span>
                  <p className="text-xs text-gray-500 mt-1">MP4, WebM up to 2GB</p>
                </div>
              </>
            )}
          </button>
        )}
        <input ref={fileInputRef} type="file" accept="video/*" onChange={handleFileSelect} className="hidden" />
      </div>
    </div>
  )
}
