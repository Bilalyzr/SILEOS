/**
 * QuizCsvImport (roadmap R6): one button + a glass dialog that turns a CSV
 * into a quiz (all-or-nothing; row errors are shown, nothing half-imported).
 */
import { useEffect, useState } from 'react'
import toast from 'react-hot-toast'
import { courseOpsAPI } from '@/api/courseOps'
import { GlassDialog } from '@/components/ui/dialog'

export function QuizCsvImport({ courseId, onImported, className = '' }: { courseId: number; onImported?: (quizId: number) => void; className?: string }) {
  const [open, setOpen] = useState(false)
  const [file, setFile] = useState<File | null>(null)
  const [title, setTitle] = useState('')
  const [passing, setPassing] = useState(50)
  const [busy, setBusy] = useState(false)
  const [errors, setErrors] = useState<string[]>([])
  const [help, setHelp] = useState<{ help: string; example: string } | null>(null)
  useEffect(() => { if (open && !help) courseOpsAPI.csvHelp().then(setHelp).catch(() => {}) }, [open, help])

  const run = async () => {
    if (!file) return
    setBusy(true); setErrors([])
    try {
      const r = await courseOpsAPI.importQuizCsv(courseId, file, title, passing)
      toast.success(`Quiz "${r.title}" created with ${r.questions} questions`)
      setOpen(false); setFile(null); setTitle('')
      onImported?.(r.quiz_id)
    } catch (e: any) {
      const d = e?.response?.data?.detail
      setErrors(Array.isArray(d?.errors) ? d.errors : [typeof d === 'string' ? d : 'Import failed'])
    } finally { setBusy(false) }
  }

  return (
    <>
      <button type="button" onClick={() => setOpen(true)} className={`px-3 py-1.5 text-sm rounded-lg border border-emerald-300 text-emerald-700 hover:bg-emerald-50 ${className}`} data-testid="csv-import-btn">⇪ Import quiz CSV</button>
      <GlassDialog open={open} onOpenChange={setOpen} size="md" eyebrow="Bulk import" title="Create a quiz from a CSV file"
        description="One question per row. Nothing is imported if any row has an error."
        actions={<><button type="button" className="si-btn-secondary" onClick={() => setOpen(false)}>Cancel</button><button type="button" className="si-btn-primary" disabled={busy || !file} onClick={run}>{busy ? 'Importing…' : 'Import'}</button></>}>
        <div className="space-y-3 text-sm">
          <label className="block"><span className="block text-xs font-medium text-gray-600 mb-1">Quiz title</span>
            <input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="e.g. Unit 3 — Motion" className="si-input w-full" /></label>
          <div className="flex gap-3 items-end">
            <label className="block flex-1"><span className="block text-xs font-medium text-gray-600 mb-1">CSV file</span>
              <input type="file" accept=".csv,text/csv" onChange={(e) => setFile(e.target.files?.[0] || null)} className="text-sm" /></label>
            <label className="block"><span className="block text-xs font-medium text-gray-600 mb-1">Pass mark %</span>
              <input type="number" min={0} max={100} value={passing} onChange={(e) => setPassing(Number(e.target.value))} className="si-input w-24" /></label>
          </div>
          {help && (
            <details className="text-xs text-gray-600"><summary className="cursor-pointer">Column format and example</summary>
              <p className="mt-1">{help.help}</p>
              <pre className="mt-1 bg-gray-50 rounded p-2 overflow-x-auto">{help.example}</pre>
            </details>
          )}
          {errors.length > 0 && (
            <ul className="text-xs text-red-700 bg-red-50 border border-red-200 rounded-lg p-2 list-disc pl-5" role="alert">{errors.map((e, i) => <li key={i}>{e}</li>)}</ul>
          )}
        </div>
      </GlassDialog>
    </>
  )
}

export default QuizCsvImport
