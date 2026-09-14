/**
 * CollaboratorsBlock (roadmap R6): co-instructors for a course. Owner adds by
 * email (instructor accounts only) and removes; co-instructors edit
 * everything but cannot manage this list, delete the course or take revenue.
 */
import { useCallback, useEffect, useState } from 'react'
import toast from 'react-hot-toast'
import { courseOpsAPI, type Collaborator } from '@/api/courseOps'
import { confirmDialog } from '@/components/ui/confirm'
import { useAuthStore } from '@/store/auth'

export function CollaboratorsBlock({ courseId }: { courseId: number }) {
  const user = useAuthStore((s) => s.user)
  const [rows, setRows] = useState<Collaborator[] | null>(null)
  const [ownerId, setOwnerId] = useState<number | null>(null)
  const [email, setEmail] = useState('')
  const [busy, setBusy] = useState(false)
  const load = useCallback(() => {
    courseOpsAPI.collaborators(courseId).then((d) => { setRows(d.collaborators); setOwnerId(d.owner_id) }).catch(() => setRows([]))
  }, [courseId])
  useEffect(() => { load() }, [load])
  const isOwner = ownerId != null && (user?.id === ownerId || user?.role === 'admin')

  const add = async () => {
    if (!email.trim()) return
    setBusy(true)
    try {
      const d = await courseOpsAPI.addCollaborator(courseId, email.trim())
      setRows(d.collaborators); setEmail('')
      toast.success(d.created ? 'Co-instructor added — they have been notified' : 'Already a co-instructor')
    } catch (e: any) { toast.error(e?.response?.data?.detail || 'Could not add') }
    finally { setBusy(false) }
  }
  const remove = async (c: Collaborator) => {
    if (!(await confirmDialog(`Remove ${c.name} as co-instructor? They keep nothing; the course stays yours.`))) return
    try { const d = await courseOpsAPI.removeCollaborator(courseId, c.user_id); setRows(d.collaborators); toast.success('Removed') }
    catch (e: any) { toast.error(e?.response?.data?.detail || 'Could not remove') }
  }

  return (
    <div className="border border-gray-200 rounded-xl p-6 bg-violet-50/60" data-testid="collaborators-block">
      <div className="flex items-center gap-3 mb-3">
        <div className="w-10 h-10 bg-violet-100 rounded-lg flex items-center justify-center"><span className="text-violet-700 text-xl">👥</span></div>
        <div>
          <h3 className="text-lg font-semibold text-gray-900">Co-instructors</h3>
          <p className="text-sm text-gray-500">They can edit the curriculum, quizzes, assignments, live classes and grades. Ownership and revenue stay with you.</p>
        </div>
      </div>
      {rows === null ? <p className="text-sm text-gray-500">Loading…</p> : rows.length === 0 ? <p className="text-sm text-gray-600">No co-instructors yet.</p> : (
        <ul className="space-y-1 mb-3">
          {rows.map((c) => (
            <li key={c.id} className="flex items-center gap-2 text-sm bg-white/80 rounded-lg border border-white/80 px-3 py-2">
              <span className="font-medium text-gray-900">{c.name}</span><span className="text-gray-500 flex-1 truncate">{c.email}</span>
              {isOwner && <button type="button" onClick={() => remove(c)} className="text-xs text-red-600 hover:underline">Remove</button>}
            </li>
          ))}
        </ul>
      )}
      {isOwner && (
        <div className="flex gap-2">
          <input value={email} onChange={(e) => setEmail(e.target.value)} placeholder="instructor@example.com" className="si-input flex-1" aria-label="Co-instructor email" onKeyDown={(e) => { if (e.key === 'Enter') add() }} />
          <button type="button" disabled={busy || !email.trim()} onClick={add} className="si-btn-primary">Add co-instructor</button>
        </div>
      )}
    </div>
  )
}

export default CollaboratorsBlock
