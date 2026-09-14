import React from 'react'
import { X,Loader2,Image as ImageIcon } from 'lucide-react'
import { uploadImage,deleteFile } from '@/api/upload'
import { uploadImageChunked,ChunkedUploadProgress } from '@/api/chunked-upload'
import { toast } from 'react-hot-toast'
import { BACKEND_URL } from '@/config/urls'

interface ImageUploadProps {
  value?: string
  onChange: (url: string) => void
  description?: string
  label?: string
  className?: string
  aspectRatio?: string
}

export const ImageUpload: React.FC<ImageUploadProps> = ({
  value,
  description,
  onChange,
  label = 'Upload Image',
  className = '',
  aspectRatio = 'aspect-video'
}) => {
  const [isUploading, setIsUploading] = React.useState(false)
  const [uploadProgress, setUploadProgress] = React.useState(0)
  const [preview, setPreview] = React.useState<string | null>(value || null)
  const fileInputRef = React.useRef<HTMLInputElement>(null)
  const isUploadingRef = React.useRef(false)

  React.useEffect(() => {
    setPreview(value || null)
  }, [value])

  const handleFileSelect = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) return

    // Prevent double upload from React Strict Mode or double events
    if (isUploading || isUploadingRef.current) {
      event.target.value = ''
      return
    }

    // Validate file type
    if (!file.type.startsWith('image/')) {
      toast.error('Please select an image file')
      return
    }

    // Validate file size (10MB max)
    const maxSize = 10 * 1024 * 1024
    if (file.size > maxSize) {
      toast.error('Image must be less than 10MB')
      return
    }

    try {
      setIsUploading(true)
      isUploadingRef.current = true

      // Create preview
      const reader = new FileReader()
      reader.onloadend = () => {
        setPreview(reader.result as string)
      }
      reader.readAsDataURL(file)

      // Upload to server - use chunked upload for large files, regular for small
      let response

      // For images < 5MB, use regular upload (faster and simpler)
      if (file.size < 5 * 1024 * 1024) {
        response = await uploadImage(file)
      } else {
        // For large images, use chunked upload
        response = await uploadImageChunked(file, (progress: ChunkedUploadProgress) => {
          setUploadProgress(progress.percentage)
        })
      }

      if (response.success) {
        // Convert relative URL to full URL for preview
        const fullUrl = response.file_url.startsWith('http')
          ? response.file_url
          : `${BACKEND_URL}${response.file_url}`
        onChange(fullUrl)
        toast.success('Image uploaded successfully')
      } else {
        throw new Error('Upload failed')
      }
    } catch (error: any) {
      console.error('Upload error:', error)
      // Handle different error formats
      let errorMessage = 'Failed to upload image'
      try {
        if (error?.response?.data?.detail) {
          const detail = error.response.data.detail
          if (typeof detail === 'string') {
            errorMessage = detail
          } else if (Array.isArray(detail)) {
            errorMessage = detail.map((e: any) => e?.msg || e?.message || JSON.stringify(e)).join(', ')
          } else if (typeof detail === 'object' && detail !== null) {
            errorMessage = detail.message || detail.msg || 'Validation error'
          }
        } else if (error?.message) {
          errorMessage = error.message
        } else if (typeof error === 'string') {
          errorMessage = error
        }
      } catch (_) {
        errorMessage = 'Upload failed - please try again'
      }
      toast.error(errorMessage)
      setPreview(value || null)
    } finally {
      setIsUploading(false)
      isUploadingRef.current = false
      if (fileInputRef.current) {
        fileInputRef.current.value = ''
      }
    }
  }

  const handleRemove = async () => {
    if (!value) return

    try {
      // Convert full URL back to relative path for delete API
      const relativeUrl = value.includes(BACKEND_URL)
        ? value.replace(BACKEND_URL, '')
        : value.includes('backend.sashainfinity.com')
          ? value.replace('https://backend.sashainfinity.com', '')
          : value
      await deleteFile(relativeUrl)
      setPreview(null)
      onChange('')
      toast.success('Image removed')
    } catch (error) {
      console.error('Delete error:', error)
      toast.error('Failed to remove image')
    }
  }

  return (
    <div className={`space-y-2 ${className}`}>
      {description && <p className="text-sm text-neutral-500">{description}</p>}
      {label && (
        <label className="block text-sm font-medium text-gray-700">
          {label}
        </label>
      )}

      <div className="relative">
        {preview ? (
          <div className={`relative ${aspectRatio} w-full rounded-lg overflow-hidden border-2 border-gray-200 bg-gray-50`}>
            <img
              src={preview}
              alt="Preview"
              className="w-full h-full object-cover"
            />
            {!isUploading && (
              <button
                type="button"
                onClick={handleRemove}
                className="absolute top-2 right-2 p-2 bg-red-500 text-white rounded-full hover:bg-red-600 transition-colors shadow-lg"
              >
                <X className="w-4 h-4" />
              </button>
            )}
            {isUploading && (
              <div className="absolute inset-0 bg-black bg-opacity-50 flex items-center justify-center">
                <div className="flex flex-col items-center space-y-3 px-8 max-w-xs w-full">
                  <Loader2 className="w-8 h-8 text-white animate-spin" />
                  <div className="w-full">
                    <div className="flex justify-between text-white text-sm mb-2">
                      <span>Uploading...</span>
                      <span>{uploadProgress}%</span>
                    </div>
                    <div className="w-full bg-gray-700 rounded-full h-2">
                      <div
                        className="bg-blue-500 h-2 rounded-full transition-all duration-300"
                        style={{ width: `${uploadProgress}%` }}
                      />
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        ) : (
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            disabled={isUploading}
            className={`${aspectRatio} w-full border-2 border-dashed border-gray-300 rounded-lg hover:border-blue-500 transition-colors flex flex-col items-center justify-center space-y-2 bg-gray-50 hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed`}
          >
            {isUploading ? (
              <>
                <Loader2 className="w-8 h-8 text-blue-500 animate-spin" />
                <span className="text-sm text-gray-600">Uploading...</span>
              </>
            ) : (
              <>
                <ImageIcon className="w-8 h-8 text-gray-400" />
                <div className="text-center">
                  <span className="text-sm text-blue-600 font-medium">Click to upload</span>
                  <p className="text-xs text-gray-500 mt-1">PNG, JPG, GIF up to 10MB</p>
                </div>
              </>
            )}
          </button>
        )}

        <input
          ref={fileInputRef}
          type="file"
          accept="image/*"
          onChange={handleFileSelect}
          className="hidden"
        />
      </div>
    </div>
  )
}
