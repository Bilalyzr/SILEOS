import React,{ useState,useRef,useEffect,useCallback,useLayoutEffect } from 'react'
import { createPortal } from 'react-dom'
import { Download,Upload,FileSpreadsheet,FileText,X,CheckCircle,AlertCircle,Loader2,File,Calendar,Filter,BarChart3 } from 'lucide-react'
import toast from 'react-hot-toast'
import { importData,downloadTemplate } from '@/api/admin'
import type { ExportSection,ExportFormat } from '@/api/admin'
import { api } from '@/api/axios'

// Sections that support import (data can be created/updated from file)
const IMPORTABLE_SECTIONS: Set<ExportSection> = new Set([
  'students',
  'instructors',
  'spocs',
  'courses',
  'companies',
  'coupons'
])

// Format icons with colors
const FORMAT_ICONS = {
  csv: { icon: FileSpreadsheet, color: 'text-emerald-600', bg: 'bg-emerald-100', hover: 'hover:bg-emerald-200', name: 'CSV' },
  excel: { icon: FileSpreadsheet, color: 'text-emerald-600', bg: 'bg-emerald-100', hover: 'hover:bg-emerald-200', name: 'Excel' },
  pdf: { icon: File, color: 'text-red-600', bg: 'bg-red-100', hover: 'hover:bg-red-200', name: 'PDF' }
} as const

// Required columns for each import section (only for importable sections)
const REQUIRED_COLUMNS: Record<string, string[]> = {
  students: ['id', 'user_login', 'user_email', 'display_name', 'is_active', 'is_verified', 'phone', 'first_name', 'last_name'],
  instructors: ['id', 'user_login', 'user_email', 'display_name', 'is_active', 'is_verified', 'phone', 'first_name', 'last_name', 'bio', 'expertise'],
  spocs: ['id', 'user_login', 'user_email', 'display_name', 'is_active', 'is_verified', 'phone', 'first_name', 'last_name', 'college_name', 'designation'],
  companies: ['id', 'name', 'slug', 'owner_email', 'contact_email', 'website', 'industry', 'team_size', 'description'],
  courses: ['id', 'title', 'slug', 'post_status', 'course_type', 'price', 'sale_price', 'category', 'level'],
  coupons: ['id', 'code', 'discount_type', 'discount_value', 'max_uses', 'used_count', 'is_active', 'valid_from', 'valid_until']
}

function getRequiredColumns(section: ExportSection): string {
  return REQUIRED_COLUMNS[section]?.join(', ') || 'id, name, email'
}

/**
 * Pull a usable message out of a failed export.
 *
 * The request is made with `responseType: 'blob'`, so an error response body
 * arrives as a Blob rather than parsed JSON — without this the toast could only
 * ever say "Request failed with status code 404", which is what hid a broken
 * export URL for so long.
 */
async function describeExportError(error: any): Promise<string> {
  const status = error?.response?.status
  const body = error?.response?.data

  if (body instanceof Blob) {
    try {
      const text = await body.text()
      const detail = JSON.parse(text)?.detail
      if (detail) return typeof detail === 'string' ? detail : JSON.stringify(detail)
    } catch {
      // Not JSON (HTML error page, empty body) — fall through to the status.
    }
  } else if (typeof body?.detail === 'string') {
    return body.detail
  }

  if (status === 404) return 'Export endpoint not found (404)'
  if (status === 401 || status === 403) return 'You are not allowed to export this report'
  if (status) return `Export failed (HTTP ${status})`
  return error?.message || 'Failed to export data'
}

interface ExportImportPanelProps {
  section: ExportSection
  onImportComplete?: () => void
  filters?: Record<string, any>
  role?: 'admin' | 'instructor' | 'spoc' | 'company' | 'student'
  /**
   * Button text. Only needed when a page renders more than one panel side by
   * side — without it every button just reads "Export" and they can't be told
   * apart.
   */
  label?: string
  /**
   * `dark` restyles the trigger for a coloured hero band (translucent white on
   * the gradient) instead of the default white-on-grey table toolbar.
   */
  tone?: 'light' | 'dark'
}

// Width of the dropdown panel (w-80). Needed in JS because the menu is
// portalled to <body> and positioned from the trigger's viewport rect.
const MENU_WIDTH = 320
const VIEWPORT_MARGIN = 8

interface ImportResult {
  success_count: number
  error_count: number
  errors?: Array<{ row: number; message: string }>
  message?: string
}

interface RecordCount {
  count: number
  loading: boolean
}

export const ExportImportPanel: React.FC<ExportImportPanelProps> = ({
  section,
  onImportComplete,
  filters = {},
  role = 'admin',
  label,
  tone = 'light'
}) => {
  const [showExportMenu, setShowExportMenu] = useState(false)
  const [showImportModal, setShowImportModal] = useState(false)
  const [exporting, setExporting] = useState(false)
  const [importing, setImporting] = useState(false)
  const [importFile, setImportFile] = useState<File | null>(null)
  const [importFormat, setImportFormat] = useState<ExportFormat>('excel')
  const [importResult, setImportResult] = useState<ImportResult | null>(null)
  const [previewData, setPreviewData] = useState<any[] | null>(null)
  const [recordCount, setRecordCount] = useState<RecordCount>({ count: 0, loading: true })
  const [exportProgress, setExportProgress] = useState(0)
  const [showSuccessAnimation, setShowSuccessAnimation] = useState(false)
  const [showExportOptions, setShowExportOptions] = useState(false)
  const [dateRangeFilter, setDateRangeFilter] = useState({ from: '', to: '' })
  const [statusFilter, setStatusFilter] = useState('')
  const fileInputRef = useRef<HTMLInputElement>(null)
  const triggerRef = useRef<HTMLButtonElement>(null)
  const [menuPos, setMenuPos] = useState<{ top: number; left: number } | null>(null)

  // The menu is portalled to <body> so an `overflow-hidden` ancestor (the
  // gradient hero on the analytics page) can no longer clip it. That means its
  // position has to be recomputed from the trigger rect whenever the page moves.
  const positionMenu = useCallback(() => {
    const rect = triggerRef.current?.getBoundingClientRect()
    if (!rect) return
    const left = Math.min(
      Math.max(rect.right - MENU_WIDTH, VIEWPORT_MARGIN),
      window.innerWidth - MENU_WIDTH - VIEWPORT_MARGIN
    )
    setMenuPos({ top: rect.bottom + VIEWPORT_MARGIN, left })
  }, [])

  useLayoutEffect(() => {
    if (!showExportMenu) {
      setMenuPos(null)
      return
    }
    positionMenu()
    window.addEventListener('scroll', positionMenu, true)
    window.addEventListener('resize', positionMenu)
    return () => {
      window.removeEventListener('scroll', positionMenu, true)
      window.removeEventListener('resize', positionMenu)
    }
  }, [showExportMenu, showExportOptions, positionMenu])

  const sectionLabel: Record<ExportSection, string> = {
    students: 'Students',
    instructors: 'Instructors',
    spocs: 'SPOCs',
    companies: 'Companies',
    courses: 'Courses',
    blogs: 'Blogs',
    certificates: 'Certificates',
    orders: 'Orders',
    coupons: 'Coupons',
    dashboard: 'Dashboard',
    internships: 'Internships',
    internship_roster: 'Internship Roster',
    enrollments: 'Enrollments',
    reviews: 'Reviews',
    cohorts: 'Cohorts',
    lessons: 'Lessons',
    quizzes: 'Quizzes',
    internship_requests: 'Internship Requests',
    // Role-specific sections
    instructor_courses: 'My Courses',
    instructor_students: 'My Students',
    instructor_quiz_results: 'Quiz Results',
    instructor_assignment_results: 'Assignment Results',
    spoc_students: 'College Students',
    spoc_internships: 'College Internships',
    spoc_placements: 'Student Placements',
    company_positions: 'Open Positions',
    company_interns: 'Assigned Interns',
    company_performance: 'Performance Reviews',
    // Student sections
    student_courses: 'My Courses',
    student_certificates: 'My Certificates',
    student_quiz_results: 'My Quiz Results',
    student_assignment_results: 'My Assignments'
  }

  // Fetch record count on mount and when export menu opens
    const fetchRecordCount = useCallback(async () => {
    setRecordCount({ count: 0, loading: true })
    try {
      const queryParams = new URLSearchParams({
        ...(dateRangeFilter.from && { date_from: dateRangeFilter.from }),
        ...(dateRangeFilter.to && { date_to: dateRangeFilter.to }),
        ...(statusFilter && { status: statusFilter })
      }).toString()

      const endpoint = role === 'admin' ? '/admin' : `/${role}`
      const response = await api.get(`${endpoint}/export/${section}/count?${queryParams}`)
      setRecordCount({
        count: response.data.count || 0,
        loading: false
      })
    } catch {
      setRecordCount({ count: 0, loading: false })
    }
  }, [dateRangeFilter.from, dateRangeFilter.to, role, section, statusFilter])
useEffect(() => {
    if (showExportMenu) {
      fetchRecordCount()
    }
  }, [showExportMenu, section, dateRangeFilter, statusFilter, fetchRecordCount])



  const handleExport = async (format: ExportFormat) => {
    setExporting(true)
    setExportProgress(0)
    setShowSuccessAnimation(false)

    // Simulate progress for better UX
    const progressInterval = setInterval(() => {
      setExportProgress(prev => Math.min(prev + 10, 90))
    }, 200)

    try {
      const exportFilters = {
        ...filters,
        ...(dateRangeFilter.from && { date_from: dateRangeFilter.from }),
        ...(dateRangeFilter.to && { date_to: dateRangeFilter.to }),
        ...(statusFilter && { status: statusFilter })
      }

      const endpoint = role === 'admin' ? '/admin' : `/${role}`

      // Use internship_roster for internships section
      const exportSection = section === 'internships' ? 'internship_roster' : section

      const response = await api.get(`${endpoint}/export/${exportSection}?format=${format}&${new URLSearchParams(exportFilters as any).toString()}`, {
        responseType: 'blob'
      })

      const blob: Blob = response.data

      clearInterval(progressInterval)
      setExportProgress(100)

      // A zero-byte body would otherwise be saved as a corrupt file that only
      // fails when the user opens it.
      if (!blob || blob.size === 0) {
        throw new Error('The server returned an empty file')
      }

      const url = window.URL.createObjectURL(blob)
      const timestamp = new Date().toISOString().slice(0, 10)
      const extension = format === 'excel' ? 'xlsx' : 'pdf'
      const filename = `${section}_${timestamp}.${extension}`

      // For PDF, open in new tab; for others, download
      if (format === 'pdf') {
        const newWindow = window.open(url, '_blank')
        if (newWindow) {
          newWindow.location.href = url
          // The new tab still needs the blob URL, so release it late rather
          // than never — leaving it allocated pinned the whole PDF in memory
          // for the rest of the session.
          setTimeout(() => window.URL.revokeObjectURL(url), 60_000)
        } else {
          // Fallback if popup is blocked
          const a = document.createElement('a')
          a.href = url
          a.download = filename
          a.target = '_blank'
          document.body.appendChild(a)
          a.click()
          document.body.removeChild(a)
          window.URL.revokeObjectURL(url)
        }
      } else {
        const a = document.createElement('a')
        a.href = url
        a.download = filename
        document.body.appendChild(a)
        a.click()
        window.URL.revokeObjectURL(url)
        document.body.removeChild(a)
      }

      // Show success animation
      setShowSuccessAnimation(true)
      toast.success(`${sectionLabel[section]} exported as ${FORMAT_ICONS[format].name}`)
      setShowExportMenu(false)
      setShowExportOptions(false)

      setTimeout(() => setShowSuccessAnimation(false), 2000)
    } catch (error: any) {
      console.error('Export error:', error)
      toast.error(await describeExportError(error))
    } finally {
      clearInterval(progressInterval)
      setExporting(false)
      setExportProgress(0)
    }
  }

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    const validExtensions = importFormat === 'excel'
      ? ['.xlsx', '.xls']
      : ['.csv']

    const isValidFile = validExtensions.some(ext => file.name.toLowerCase().endsWith(ext))

    if (!isValidFile) {
      toast.error(`Please select a valid ${importFormat.toUpperCase()} file`)
      return
    }

    setImportFile(file)
    setImportResult(null)

    // Parse preview for CSV
    if (importFormat === 'csv') {
      const reader = new FileReader()
      reader.onload = (e) => {
        const text = e.target?.result as string
        const lines = text.split('\n').filter(line => line.trim())
        const headers = lines[0]?.split(',').map(h => h.trim().replace(/"/g, '')) || []
        const previewRows = lines.slice(1, 6).map(line => {
          const values = line.split(',').map(v => v.trim().replace(/"/g, ''))
          return headers.reduce((obj, header, i) => {
            obj[header] = values[i] || ''
            return obj
          }, {} as Record<string, string>)
        })
        setPreviewData(previewRows)
      }
      reader.readAsText(file)
    } else {
      setPreviewData(null)
    }
  }

  const handleImport = async () => {
    if (!importFile) {
      toast.error('Please select a file to import')
      return
    }

    setImporting(true)
    setImportResult(null)

    try {
      const data = await importData(section, importFile, importFormat)
      setImportResult(data)

      if (data.error_count === 0) {
        toast.success(`Successfully imported ${data.success_count} ${sectionLabel[section]}`)
        setTimeout(() => {
          setShowImportModal(false)
          setImportFile(null)
          setPreviewData(null)
          setImportResult(null)
          onImportComplete?.()
        }, 2000)
      } else if (data.success_count > 0) {
        toast(`Imported ${data.success_count} records with ${data.error_count} errors`, { icon: '⚠️' })
      } else {
        toast.error('Import failed. Please check the errors below.')
      }
    } catch (error: any) {
      console.error('Import error:', error)
      const errorData = error.response?.data || {
        success_count: 0,
        error_count: 1,
        errors: [{ row: 0, message: error.message || 'Failed to import data' }]
      }
      setImportResult(errorData)
      toast.error(errorData.message || error.message || 'Failed to import data')
    } finally {
      setImporting(false)
    }
  }

  const resetImport = () => {
    setImportFile(null)
    setImportResult(null)
    setPreviewData(null)
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  const handleDownloadTemplate = async () => {
    try {
      const blob = await downloadTemplate(section)
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${section}_template.xlsx`
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)
      toast.success(`Template downloaded for ${sectionLabel[section]}`)
    } catch (error: any) {
      console.error('Template download error:', error)
      toast.error('Failed to download template')
    }
  }

  return (
    <div className="relative">
      {/* Export/Import Button */}
      <div className="relative">
        <button
          ref={triggerRef}
          onClick={() => setShowExportMenu(!showExportMenu)}
          className={`inline-flex items-center gap-2 px-4 py-2 rounded-lg transition-colors text-sm font-medium ${
            tone === 'dark'
              ? 'bg-white/15 backdrop-blur text-white border border-white/25 hover:bg-white/25'
              : 'bg-white border border-gray-300 text-gray-900 hover:bg-gray-50 shadow-sm'
          }`}
        >
          <Download className="w-4 h-4" />
          {label || `Export${IMPORTABLE_SECTIONS.has(section) ? ' / Import' : ''}`}
        </button>

        {/* Export Dropdown Menu — portalled so an overflow-hidden ancestor
            (e.g. the analytics hero band) cannot clip it. */}
        {showExportMenu && menuPos && createPortal(
          <>
            <div
              className="fixed inset-0 z-[90]"
              onClick={() => setShowExportMenu(false)}
            />
            <div
              className="fixed w-80 bg-white rounded-xl shadow-xl border border-gray-200 z-[91] overflow-hidden max-h-[80vh] overflow-y-auto"
              style={{ top: menuPos.top, left: menuPos.left }}
            >
              <div className="p-4">
                {/* Header with record count */}
                <div className="flex items-center justify-between mb-3">
                  <div className="px-2 py-1.5 text-xs font-bold text-gray-400 uppercase tracking-wider">
                    Export {sectionLabel[section]}
                  </div>
                  {!recordCount.loading && (
                    <div className="flex items-center gap-1 text-xs text-gray-500">
                      <BarChart3 className="w-3 h-3" />
                      {recordCount.count} records
                    </div>
                  )}
                </div>

                {/* Export format buttons with icons */}
                <div className="space-y-1.5">
                  {(Object.keys(FORMAT_ICONS) as ExportFormat[]).map((format) => {
                    const { icon: Icon, color, bg, hover, name } = FORMAT_ICONS[format]
                    return (
                      <button
                        key={format}
                        onClick={() => handleExport(format)}
                        disabled={exporting}
                        className="w-full flex items-center gap-3 px-3 py-2.5 text-sm rounded-lg hover:bg-blue-50 hover:border-blue-200 border border-transparent disabled:opacity-50 disabled:cursor-not-allowed transition-all group"
                      >
                        <div className={`w-9 h-9 rounded-lg ${bg} flex items-center justify-center ${hover} transition-colors`}>
                          <Icon className={`w-4 h-4 ${color}`} />
                        </div>
                        <div className="flex-1 text-left">
                          <div className="font-medium text-gray-900">{name}</div>
                          <div className="text-xs text-gray-500">
                            {format === 'excel' && '.xlsx with styling'}
                            {format === 'pdf' && 'Printable document'}
                          </div>
                        </div>
                        {showSuccessAnimation && exportProgress === 100 && (
                          <CheckCircle className="w-5 h-5 text-green-500 animate-in fade-in zoom-in duration-300" />
                        )}
                      </button>
                    )
                  })}
                </div>

                {/* Export Options Toggle */}
                <button
                  onClick={() => setShowExportOptions(!showExportOptions)}
                  className="mt-3 w-full flex items-center justify-center gap-2 px-3 py-2 text-xs text-gray-600 hover:text-gray-900 hover:bg-gray-50 rounded-lg transition-colors"
                >
                  <Filter className="w-3 h-3" />
                  {showExportOptions ? 'Hide' : 'Show'} export options
                </button>

                {/* Export Options */}
                {showExportOptions && (
                  <div className="mt-3 p-3 bg-gray-50 rounded-lg space-y-3">
                    <div>
                      <label className="flex items-center gap-2 text-xs font-medium text-gray-700 mb-1.5">
                        <Calendar className="w-3 h-3" />
                        Date Range
                      </label>
                      <div className="flex gap-2">
                        <input
                          type="date"
                          value={dateRangeFilter.from}
                          onChange={(e) => setDateRangeFilter({ ...dateRangeFilter, from: e.target.value })}
                          className="flex-1 px-2 py-1.5 text-xs border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                        />
                        <input
                          type="date"
                          value={dateRangeFilter.to}
                          onChange={(e) => setDateRangeFilter({ ...dateRangeFilter, to: e.target.value })}
                          className="flex-1 px-2 py-1.5 text-xs border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                        />
                      </div>
                    </div>
                    <div>
                      <label className="text-xs font-medium text-gray-700 mb-1.5 block">Status Filter</label>
                      <select
                        value={statusFilter}
                        onChange={(e) => setStatusFilter(e.target.value)}
                        className="w-full px-2 py-1.5 text-xs border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                      >
                        <option value="">All</option>
                        {section === 'students' || section === 'instructors' || section === 'spocs' ? (
                          <>
                            <option value="active">Active</option>
                            <option value="inactive">Inactive</option>
                          </>
                        ) : section === 'companies' ? (
                          <>
                            <option value="approved">Approved</option>
                            <option value="pending">Pending</option>
                          </>
                        ) : section === 'courses' ? (
                          <>
                            <option value="published">Published</option>
                            <option value="draft">Draft</option>
                          </>
                        ) : section === 'orders' ? (
                          <>
                            <option value="completed">Completed</option>
                            <option value="pending">Pending</option>
                            <option value="failed">Failed</option>
                          </>
                        ) : section === 'coupons' ? (
                          <>
                            <option value="active">Active</option>
                            <option value="inactive">Inactive</option>
                          </>
                        ) : section === 'internships' ? (
                          <>
                            <option value="active">Published</option>
                            <option value="inactive">Draft</option>
                          </>
                        ) : null}
                      </select>
                    </div>
                  </div>
                )}

                {IMPORTABLE_SECTIONS.has(section) && (
                  <>
                    <div className="border-t border-gray-200 my-3" />
                    <div className="px-2 py-1.5 text-xs font-bold text-gray-400 uppercase tracking-wider">
                      Import
                    </div>
                    <button
                      onClick={() => {
                        setShowExportMenu(false)
                        setShowImportModal(true)
                      }}
                      className="w-full flex items-center gap-3 px-3 py-2.5 text-sm rounded-lg hover:bg-purple-50 hover:border-purple-200 border border-transparent transition-all group"
                    >
                      <div className="w-9 h-9 rounded-lg bg-purple-100 flex items-center justify-center group-hover:bg-purple-200 transition-colors">
                        <Upload className="w-4 h-4 text-purple-700" />
                      </div>
                      <div className="flex-1 text-left">
                        <div className="font-medium text-gray-900">Import Data</div>
                        <div className="text-xs text-gray-500">CSV or Excel file</div>
                      </div>
                    </button>
                  </>
                )}
              </div>

              {/* Export Progress Bar */}
              {exporting && (
                <div className="px-4 py-3 bg-blue-50 border-t border-blue-100">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2 text-xs text-blue-700">
                      <Loader2 className="w-3 h-3 animate-spin" />
                      Preparing your export...
                    </div>
                    <span className="text-xs font-medium text-blue-700">{exportProgress}%</span>
                  </div>
                  <div className="w-full bg-blue-200 rounded-full h-1.5">
                    <div
                      className="bg-blue-600 h-1.5 rounded-full transition-all duration-300"
                      style={{ width: `${exportProgress}%` }}
                    />
                  </div>
                </div>
              )}
            </div>
          </>,
          document.body
        )}
      </div>

      {/* Import Modal */}
      {showImportModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
            {/* Header */}
            <div className="flex items-center justify-between p-6 border-b border-gray-200">
              <div>
                <h2 className="text-xl font-bold text-gray-900">Import {sectionLabel[section]}</h2>
                <p className="text-sm text-gray-600 mt-1">
                  Upload a file to import {sectionLabel[section].toLowerCase()} data
                </p>
              </div>
              <button
                onClick={() => {
                  setShowImportModal(false)
                  resetImport()
                }}
                className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
              >
                <X className="w-5 h-5 text-gray-500" />
              </button>
            </div>

            {/* Content */}
            <div className="p-6 space-y-6">
              {/* Format Requirements */}
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                <div className="flex items-start justify-between mb-2">
                  <h3 className="text-sm font-semibold text-blue-900">Format Requirements</h3>
                  <button
                    onClick={handleDownloadTemplate}
                    className="flex items-center gap-1.5 px-3 py-1.5 bg-white border border-blue-300 rounded-lg hover:bg-blue-100 transition-colors text-xs font-medium text-blue-700"
                  >
                    <Download className="w-3.5 h-3.5" />
                    Download Template
                  </button>
                </div>
                <p className="text-sm text-blue-800 mb-2">
                  Your file must include the following columns in the exact order shown below.
                </p>
                <div className="bg-white rounded border border-blue-100 p-3">
                  <code className="text-xs text-blue-900 break-all">
                    {getRequiredColumns(section)}
                  </code>
                </div>
                <p className="text-xs text-blue-700 mt-2">
                  💡 Tip: Download the template above or export data first to see the correct format, then edit and re-import.
                </p>
              </div>

              {/* Format Selection */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  File Format
                </label>
                <div className="flex gap-4">
                  <label className={`flex items-center gap-2 px-4 py-3 border rounded-lg cursor-pointer transition-colors ${
                    importFormat === 'csv'
                      ? 'border-blue-500 bg-blue-50 text-blue-700'
                      : 'border-gray-300 hover:border-gray-400'
                  }`}>
                    <input
                      type="radio"
                      name="importFormat"
                      value="csv"
                      checked={importFormat === 'csv'}
                      onChange={() => {
                        setImportFormat('csv')
                        resetImport()
                      }}
                      className="sr-only"
                    />
                    <FileText className="w-5 h-5" />
                    <span className="font-medium">CSV</span>
                  </label>
                  <label className={`flex items-center gap-2 px-4 py-3 border rounded-lg cursor-pointer transition-colors ${
                    importFormat === 'excel'
                      ? 'border-blue-500 bg-blue-50 text-blue-700'
                      : 'border-gray-300 hover:border-gray-400'
                  }`}>
                    <input
                      type="radio"
                      name="importFormat"
                      value="excel"
                      checked={importFormat === 'excel'}
                      onChange={() => {
                        setImportFormat('excel')
                        resetImport()
                      }}
                      className="sr-only"
                    />
                    <FileSpreadsheet className="w-5 h-5" />
                    <span className="font-medium">Excel</span>
                  </label>
                </div>
              </div>

              {/* File Upload */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Select File
                </label>
                <div
                  onClick={() => fileInputRef.current?.click()}
                  className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors ${
                    importFile
                      ? 'border-green-300 bg-green-50'
                      : 'border-gray-300 hover:border-gray-400'
                  }`}
                >
                  {importFile ? (
                    <div className="space-y-2">
                      <CheckCircle className="w-12 h-12 text-green-500 mx-auto" />
                      <p className="font-medium text-gray-900">{importFile.name}</p>
                      <p className="text-sm text-gray-500">
                        {(importFile.size / 1024).toFixed(1)} KB
                      </p>
                    </div>
                  ) : (
                    <div className="space-y-2">
                      <Upload className="w-12 h-12 text-gray-400 mx-auto" />
                      <p className="text-gray-900 font-medium">
                        Click to upload or drag and drop
                      </p>
                      <p className="text-sm text-gray-500">
                        {importFormat === 'csv' ? 'CSV files (.csv)' : 'Excel files (.xlsx, .xls)'}
                      </p>
                    </div>
                  )}
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept={importFormat === 'excel' ? '.xlsx,.xls' : '.csv'}
                    onChange={handleFileSelect}
                    className="hidden"
                  />
                </div>
                {importFile && (
                  <button
                    onClick={resetImport}
                    className="mt-2 text-sm text-red-600 hover:text-red-700"
                  >
                    Remove file
                  </button>
                )}
              </div>

              {/* Preview Table */}
              {previewData && previewData.length > 0 && (
                <div>
                  <h3 className="text-sm font-medium text-gray-700 mb-2">Preview</h3>
                  <div className="border border-gray-200 rounded-lg overflow-hidden max-h-48 overflow-y-auto">
                    <table className="min-w-full divide-y divide-gray-200">
                      <thead className="bg-gray-50">
                        <tr>
                          {Object.keys(previewData[0]).map(header => (
                            <th
                              key={header}
                              className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase"
                            >
                              {header}
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody className="bg-white divide-y divide-gray-200">
                        {previewData.map((row, i) => (
                          <tr key={i}>
                            {Object.values(row).map((value, j) => (
                              <td key={j} className="px-4 py-2 text-sm text-gray-900">
                                {String(value).slice(0, 50)}
                                {String(value).length > 50 && '...'}
                              </td>
                            ))}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* Import Results */}
              {importResult && (
                <div className={`p-4 rounded-lg ${
                  importResult.error_count === 0
                    ? 'bg-green-50 border border-green-200'
                    : 'bg-amber-50 border border-amber-200'
                }`}>
                  <div className="flex items-start gap-3">
                    {importResult.error_count === 0 ? (
                      <CheckCircle className="w-5 h-5 text-green-600 flex-shrink-0 mt-0.5" />
                    ) : (
                      <AlertCircle className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
                    )}
                    <div className="flex-1">
                      <h4 className={`font-medium ${
                        importResult.error_count === 0 ? 'text-green-900' : 'text-amber-900'
                      }`}>
                        Import {importResult.error_count === 0 ? 'Completed' : 'Completed with Errors'}
                      </h4>
                      <p className={`text-sm mt-1 ${
                        importResult.error_count === 0 ? 'text-green-700' : 'text-amber-700'
                      }`}>
                        {importResult.success_count} records imported successfully
                        {importResult.error_count > 0 && `, ${importResult.error_count} errors`}
                      </p>

                      {importResult.errors && importResult.errors.length > 0 && (
                        <div className="mt-3 space-y-1">
                          <p className="text-xs font-medium text-amber-800">Errors:</p>
                          {importResult.errors.slice(0, 5).map((error, i) => (
                            <p key={i} className="text-xs text-amber-700">
                              Row {error.row}: {error.message}
                            </p>
                          ))}
                          {importResult.errors.length > 5 && (
                            <p className="text-xs text-amber-600">
                              ...and {importResult.errors.length - 5} more errors
                            </p>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Footer */}
            <div className="flex items-center justify-end gap-3 p-6 border-t border-gray-200">
              <button
                onClick={() => {
                  setShowImportModal(false)
                  resetImport()
                }}
                className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors text-sm font-medium"
              >
                Cancel
              </button>
              <button
                onClick={handleImport}
                disabled={!importFile || importing}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
              >
                {importing ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Importing...
                  </>
                ) : (
                  <>
                    <Upload className="w-4 h-4" />
                    Import Data
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default ExportImportPanel
