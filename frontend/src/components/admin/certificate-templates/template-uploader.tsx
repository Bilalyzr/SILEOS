import React, { useState, useCallback } from 'react'
import { Upload, X, FileImage, FileText, AlertCircle } from 'lucide-react'
import { uploadCertificateTemplate } from '@/api/admin'

interface TemplateUploaderProps {
  onUploadComplete?: (template: { id: number; name: string }) => void
  onCancel?: () => void
}

const TemplateUploader: React.FC<TemplateUploaderProps> = ({
  onUploadComplete,
  onCancel
}) => {
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [file, setFile] = useState<File | null>(null)
  const [fileUrl, setFileUrl] = useState('')
  const [orientation, setOrientation] = useState<'landscape' | 'portrait'>('landscape')
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState('')
  const [dragActive, setDragActive] = useState(false)

  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true)
    } else if (e.type === 'dragleave') {
      setDragActive(false)
    }
  }, [])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setDragActive(false)

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const droppedFile = e.dataTransfer.files[0]
      validateAndSetFile(droppedFile)
    }
  }, [])

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      validateAndSetFile(e.target.files[0])
    }
  }

  const validateAndSetFile = (file: File) => {
    setError('')

    // Check file type
    const validTypes = ['image/jpeg', 'image/png', 'image/jpg', 'application/pdf']
    if (!validTypes.includes(file.type)) {
      setError('Please upload a JPEG, PNG, or PDF file')
      return
    }

    // Check file size (max 10MB)
    if (file.size > 10 * 1024 * 1024) {
      setError('File size must be less than 10MB')
      return
    }

    setFile(file)

    // Create preview for images
    if (file.type.startsWith('image/')) {
      const reader = new FileReader()
      reader.onloadend = () => {
        setFileUrl(reader.result as string)
      }
      reader.readAsDataURL(file)
    } else {
      setFileUrl('')
    }
  }

  const handleUpload = async () => {
    if (!name.trim()) {
      setError('Please enter a template name')
      return
    }

    if (!file && !fileUrl) {
      setError('Please select a file to upload')
      return
    }

    setUploading(true)
    setError('')

    try {
      let finalFileUrl = fileUrl

      // If we have a file, upload it first using the upload API
      if (file) {
        const formData = new FormData()
        formData.append('file', file)

        // Use the correct upload endpoint for images/PDFs
        const uploadEndpoint = file.type === 'application/pdf' ? '/upload/document' : '/upload/image'

        const token = localStorage.getItem('access_token')
        if (!token) {
          throw new Error('Authentication required')
        }

        const uploadResponse = await fetch(`/api/v1${uploadEndpoint}`, {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`
          },
          body: formData
        })

        if (!uploadResponse.ok) {
          const errorData = await uploadResponse.json().catch(() => ({ detail: 'Upload failed' }))
          throw new Error(errorData.detail || 'Failed to upload file')
        }

        const uploadData = await uploadResponse.json()
        if (!uploadData.success || !uploadData.file_url) {
          throw new Error('Invalid upload response')
        }

        finalFileUrl = uploadData.file_url
      }

      // Create the template
      const result = await uploadCertificateTemplate({
        name: name.trim(),
        description: description.trim(),
        file_url: finalFileUrl,
        file_type: file?.type === 'application/pdf' ? 'pdf' : 'image',
        orientation
      })

      onUploadComplete?.(result)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to upload template')
    } finally {
      setUploading(false)
    }
  }

  const removeFile = () => {
    setFile(null)
    setFileUrl('')
  }

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-6">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-xl font-semibold text-gray-900">Upload Certificate Template</h2>
        {onCancel && (
          <button
            onClick={onCancel}
            className="text-gray-400 hover:text-gray-600 transition-colors"
          >
            <X size={24} />
          </button>
        )}
      </div>

      <div className="space-y-6">
        {/* File Upload Area */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Template File
          </label>
          <div
            className={`relative border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
              dragActive
                ? 'border-blue-500 bg-blue-50'
                : 'border-gray-300 hover:border-gray-400'
            }`}
            onDragEnter={handleDrag}
            onDragLeave={handleDrag}
            onDragOver={handleDrag}
            onDrop={handleDrop}
          >
            {file ? (
              <div className="space-y-4">
                <div className="flex items-center justify-center gap-3">
                  {file.type === 'application/pdf' ? (
                    <FileText size={40} className="text-red-500" />
                  ) : (
                    <FileImage size={40} className="text-blue-500" />
                  )}
                  <div className="text-left">
                    <p className="font-medium text-gray-900">{file.name}</p>
                    <p className="text-sm text-gray-500">
                      {(file.size / 1024 / 1024).toFixed(2)} MB
                    </p>
                  </div>
                  <button
                    onClick={removeFile}
                    className="ml-auto text-gray-400 hover:text-red-500 transition-colors"
                  >
                    <X size={20} />
                  </button>
                </div>
                {fileUrl && (
                  <div className="mt-4">
                    <img
                      src={fileUrl}
                      alt="Preview"
                      className="max-h-48 mx-auto rounded border border-gray-200"
                    />
                  </div>
                )}
              </div>
            ) : (
              <div>
                <Upload size={40} className="mx-auto text-gray-400 mb-3" />
                <p className="text-gray-700 font-medium mb-1">
                  Drag and drop your template file here
                </p>
                <p className="text-sm text-gray-500 mb-3">or</p>
                <label className="inline-block px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors cursor-pointer">
                  Browse Files
                  <input
                    type="file"
                    accept=".jpg,.jpeg,.png,.pdf"
                    onChange={handleFileChange}
                    className="hidden"
                  />
                </label>
                <p className="text-xs text-gray-500 mt-3">
                  Supports: JPEG, PNG, PDF (max 10MB)
                </p>
              </div>
            )}
          </div>
        </div>

        {/* Template Name */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Template Name *
          </label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g., Professional Certificate 2025"
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>

        {/* Description */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Description
          </label>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Optional description of this template..."
            rows={3}
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
          />
        </div>

        {/* Orientation */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Orientation
          </label>
          <div className="flex gap-3">
            <label className={`flex items-center gap-2 px-4 py-2 border rounded-lg cursor-pointer transition-colors ${
              orientation === 'landscape'
                ? 'border-blue-500 bg-blue-50 text-blue-700'
                : 'border-gray-300 hover:border-gray-400'
            }`}>
              <input
                type="radio"
                name="orientation"
                value="landscape"
                checked={orientation === 'landscape'}
                onChange={() => setOrientation('landscape')}
                className="sr-only"
              />
              <span className="w-8 h-6 border-2 border-current rounded"></span>
              Landscape
            </label>
            <label className={`flex items-center gap-2 px-4 py-2 border rounded-lg cursor-pointer transition-colors ${
              orientation === 'portrait'
                ? 'border-blue-500 bg-blue-50 text-blue-700'
                : 'border-gray-300 hover:border-gray-400'
            }`}>
              <input
                type="radio"
                name="orientation"
                value="portrait"
                checked={orientation === 'portrait'}
                onChange={() => setOrientation('portrait')}
                className="sr-only"
              />
              <span className="h-8 w-6 border-2 border-current rounded"></span>
              Portrait
            </label>
          </div>
        </div>

        {/* Error Message */}
        {error && (
          <div className="flex items-center gap-2 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700">
            <AlertCircle size={18} />
            <span className="text-sm">{error}</span>
          </div>
        )}

        {/* Actions */}
        <div className="flex justify-end gap-3 pt-4 border-t">
          {onCancel && (
            <button
              onClick={onCancel}
              disabled={uploading}
              className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors disabled:opacity-50"
            >
              Cancel
            </button>
          )}
          <button
            onClick={handleUpload}
            disabled={uploading || !name.trim()}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {uploading ? (
              <>
                <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                Uploading...
              </>
            ) : (
              <>
                <Upload size={18} />
                Upload Template
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  )
}

export default TemplateUploader
