import React from 'react'
import { X,Loader2,FileText } from 'lucide-react'
import { uploadDocument,deleteFile } from '@/api/upload'
import { toast } from 'react-hot-toast'
import { BACKEND_URL } from '@/config/urls'

interface DocumentUploadProps {
  value?: string
  onChange: (url: string) => void
  label?: string
  className?: string
  accept?: string // e.g., ".pdf,.doc,.docx,.ppt,.pptx"
}

export const DocumentUpload: React.FC<DocumentUploadProps> = ({
  value,
  onChange,
  label = 'Upload Document',
  className = '',
  accept = '.pdf,.doc,.docx,.ppt,.pptx,.txt'
}) => {
  const [isUploading, setIsUploading] = React.useState(false)
  const [uploadProgress, setUploadProgress] = React.useState(0)
  const [documentUrl, setDocumentUrl] = React.useState<string | null>(value || null)
  const [fileName, setFileName] = React.useState<string>('')
  const fileInputRef = React.useRef<HTMLInputElement>(null)

  React.useEffect(() => {
    setDocumentUrl(value || null)
    if (value) {
      const name = value.split('/').pop() || 'document'
      setFileName(name)
    }
  }, [value])


  const getFileExtension = (filename: string): string => {
    return filename.split('.').pop()?.toUpperCase() || 'FILE'
  }

  const handleFileSelect = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) return

    // Validate file size (100MB max)
    const maxSize = 100 * 1024 * 1024
    if (file.size > maxSize) {
      toast.error('File must be less than 100MB')
      return
    }

    try {
      setIsUploading(true)
      setUploadProgress(0)
      setFileName(file.name)

      // Upload to server with progress tracking
      const response = await uploadDocument(file, (progress) => {
        setUploadProgress(progress)
      })

      if (response.success) {
        // Convert relative URL to full URL for preview
        const fullUrl = response.file_url.startsWith('http')
          ? response.file_url
          : `${BACKEND_URL}${response.file_url}`
        setDocumentUrl(fullUrl)
        onChange(fullUrl)
        toast.success('Document uploaded successfully')
      } else {
        throw new Error('Upload failed')
      }
    } catch (error: any) {
      console.error('Upload error:', error)
      toast.error(error.response?.data?.detail || 'Failed to upload document')
      setDocumentUrl(value || null)
    } finally {
      setIsUploading(false)
      setUploadProgress(0)
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
      setDocumentUrl(null)
      setFileName('')
      onChange('')
      toast.success('Document removed')
    } catch (error) {
      console.error('Delete error:', error)
      toast.error('Failed to remove document')
    }
  }

  return (
    <div className={`space-y-2 ${className}`}>
      {label && (
        <label className="block text-sm font-medium text-gray-700">
          {label}
        </label>
      )}

      <div className="relative">
        {documentUrl ? (
          <div className="relative p-4 rounded-lg border-2 border-gray-200 bg-gray-50">
            <div className="flex items-center space-x-3">
              <div className="flex-shrink-0 w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center">
                <FileText className="w-6 h-6 text-blue-600" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-gray-900 truncate">{fileName}</p>
                <p className="text-xs text-gray-500">{getFileExtension(fileName)}</p>
              </div>
              {!isUploading && (
                <button
                  type="button"
                  onClick={handleRemove}
                  className="p-2 bg-red-500 text-white rounded-full hover:bg-red-600 transition-colors shadow-lg"
                >
                  <X className="w-4 h-4" />
                </button>
              )}
            </div>
            {isUploading && (
              <div className="mt-3">
                <div className="flex justify-between text-sm mb-2">
                  <span className="text-gray-600">Uploading...</span>
                  <span className="text-gray-600 font-medium">{uploadProgress}%</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div
                    className="bg-blue-500 h-2 rounded-full transition-all duration-300"
                    style={{ width: `${uploadProgress}%` }}
                  />
                </div>
              </div>
            )}
          </div>
        ) : (
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            disabled={isUploading}
            className="w-full p-6 border-2 border-dashed border-gray-300 rounded-lg hover:border-blue-500 transition-colors flex flex-col items-center justify-center space-y-2 bg-gray-50 hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isUploading ? (
              <div className="flex flex-col items-center space-y-4 w-full max-w-sm px-8">
                <Loader2 className="w-8 h-8 text-blue-500 animate-spin" />
                <div className="w-full">
                  <div className="flex justify-between text-gray-700 text-sm mb-2">
                    <span>Uploading...</span>
                    <span>{uploadProgress}%</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div
                      className="bg-blue-500 h-2 rounded-full transition-all duration-300"
                      style={{ width: `${uploadProgress}%` }}
                    />
                  </div>
                </div>
              </div>
            ) : (
              <>
                <FileText className="w-8 h-8 text-gray-400" />
                <div className="text-center">
                  <span className="text-sm text-blue-600 font-medium">Click to upload</span>
                  <p className="text-xs text-gray-500 mt-1">PDF, DOC, PPT up to 100MB</p>
                </div>
              </>
            )}
          </button>
        )}

        <input
          ref={fileInputRef}
          type="file"
          accept={accept}
          onChange={handleFileSelect}
          className="hidden"
        />
      </div>
    </div>
  )
}
