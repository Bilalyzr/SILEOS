/**
 * TemplatePicker (roadmap R6): "Start from a template" on the course start
 * form. Templates are courses an owner flagged; using one deep-copies it into
 * the instructor's drafts and opens the editor.
 */
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'
import { courseOpsAPI, type TemplateOut } from '@/api/courseOps'
import { courseTypeLabel } from '@/config/courseTypes'

export function TemplatePicker() {
  const navigate = useNavigate()
  const [templates, setTemplates] = useState<TemplateOut[] | null>(null)
  const [busy, setBusy] = useState<number | null>(null)
  useEffect(() => { courseOpsAPI.templates().then(setTemplates).catch(() => setTemplates([])) }, [])
  if (!templates || templates.length === 0) return null
  const use = async (t: TemplateOut) => {
    setBusy(t.id)
    try {
      const c = await courseOpsAPI.useTemplate(t.id)
      toast.success(`Created from "${t.title}" — ${c.copied.lessons} lessons, ${c.copied.quizzes} quizzes copied`)
      navigate(`/instructor/courses/${c.id}/edit?tab=curriculum&face=1`, { replace: true })
    } catch (e: any) { toast.error(e?.response?.data?.detail || 'Could not use the template') }
    finally { setBusy(null) }
  }
  return (
    <div className="glass-panel rounded-2xl p-4 mb-6" data-testid="template-picker">
      <p className="text-[11px] uppercase tracking-wide text-orange-700 font-semibold">Or start from a template</p>
      <p className="text-sm text-gray-600 mb-3">A full copy — sections, lessons, quizzes and settings — in your drafts, ready to edit.</p>
      <div className="grid sm:grid-cols-2 gap-2">
        {templates.map((t) => (
          <button key={t.id} type="button" disabled={busy === t.id} onClick={() => use(t)} className="text-left rounded-xl bg-white/80 border border-white/80 p-3 hover:shadow-md hover:-translate-y-0.5 transition disabled:opacity-50">
            <p className="font-semibold text-gray-900">{t.title}</p>
            <p className="text-xs text-gray-500">{courseTypeLabel(t.course_type) || t.course_type || 'course'} · {t.lessons} lesson{t.lessons === 1 ? '' : 's'}</p>
            {t.excerpt && <p className="text-xs text-gray-600 mt-1 line-clamp-2">{t.excerpt}</p>}
            <span className="inline-block mt-2 text-xs text-primary-700 font-medium">{busy === t.id ? 'Copying…' : 'Use this template →'}</span>
          </button>
        ))}
      </div>
    </div>
  )
}

export default TemplatePicker
