import React, { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { LogOut, AlertTriangle, Building2, User, GraduationCap, BookOpen, ShieldCheck } from 'lucide-react'
import toast from 'react-hot-toast'
import { useAuthStore } from '@/store/auth'
import { adminApi } from '@/api/admin'

/**
 * Fixed banner that appears on every page while an admin is inside an
 * impersonation session (either "View as Instructor" or "View as Company").
 * Mounted once in the route layout; reads state from the auth store +
 * sessionStorage so it stays in sync across tabs/navigations.
 *
 * Clicking "Exit impersonation":
 *   1. Calls POST /admin/impersonate/end so the audit row is closed.
 *      (If the token has already expired the backend returns 200 with
 *      closed=false — fine, this is idempotent.)
 *   2. Restores the admin access+refresh tokens from sessionStorage.
 *   3. Navigates back to the appropriate admin page.
 */
export const ImpersonationBanner: React.FC = () => {
  const navigate = useNavigate()
  const user = useAuthStore((s) => s.user)
  const endImpersonation = useAuthStore((s) => s.endImpersonation)
  const getImpersonationType = useAuthStore((s) => s.getImpersonationType)
  const getTargetName = useAuthStore((s) => s.getTargetName)

  const [active, setActive] = useState<boolean>(() => {
    try {
      return sessionStorage.getItem('sasha_admin_access') !== null
    } catch {
      return false
    }
  })
  const [exiting, setExiting] = useState(false)

  // Re-check on mount + whenever user object flips (start/end of session).
  useEffect(() => {
    try {
      setActive(sessionStorage.getItem('sasha_admin_access') !== null)
    } catch {
      setActive(false)
    }
  }, [user])

  if (!active) return null

  const impersonationType = getImpersonationType()
  const targetName = getTargetName() || user?.display_name || 'user'

  // Determine redirect path based on impersonation type AND the *restored*
  // actor's role (superadmin lands back on /superadmin/*, admin on /admin/*).
  // The actor role is read from the stashed user because while impersonating
  // the live `user` is the *target*, not the actor.
  const actorIsSuperadmin = (() => {
    try {
      const raw = sessionStorage.getItem('sasha_admin_user')
      if (!raw) return false
      return JSON.parse(raw)?.role === 'superadmin'
    } catch {
      return false
    }
  })()

  // Determine redirect path based on impersonation type. SuperAdmin-initiated
  // sessions route back to the SuperAdmin console; admin-initiated to /admin/*.
  const getRedirectPath = () => {
    const base = actorIsSuperadmin ? '/superadmin' : '/admin'
    if (impersonationType === 'company') {
      return actorIsSuperadmin ? '/superadmin/instructors' : '/admin/companies'
    }
    if (impersonationType === 'spoc') {
      return actorIsSuperadmin ? '/superadmin/instructors' : '/admin/spocs'
    }
    if (impersonationType === 'student') {
      return `${base}/students`
    }
    if (impersonationType === 'admin') {
      // "View as admin" — only SuperAdmin can do this; return to admins list.
      return '/superadmin/admins'
    }
    return `${base}/instructors`
  }

  const handleExit = async () => {
    if (exiting) return
    setExiting(true)
    try {
      // Best-effort server close. If this fails (network / already expired)
      // we still restore the admin session locally — the audit row will be
      // lazily closed next time the admin impersonates or hits /end.
      try {
        await adminApi.endImpersonation()
      } catch (e) {
        console.warn('end-impersonation API call failed, continuing:', e)
      }

      const restored = endImpersonation()
      if (restored) {
        const backRole = actorIsSuperadmin ? 'superadmin' : 'admin'
        toast.success(`Exited impersonation — back on ${backRole} session`)
        navigate(getRedirectPath())
      } else {
        toast.error('No admin session to restore — please sign in again')
        navigate('/login')
      }
    } finally {
      setExiting(false)
    }
  }

  const isCompany = impersonationType === 'company'
  const isSpoc = impersonationType === 'spoc'
  const isStudent = impersonationType === 'student'
  const isAdmin = impersonationType === 'admin'

  const Icon = isCompany
    ? Building2
    : isSpoc
      ? GraduationCap
      : isStudent
        ? BookOpen
        : isAdmin
          ? ShieldCheck
          : User
  const entityLabel = isCompany
    ? 'company'
    : isSpoc
      ? 'SPOC'
      : isStudent
        ? 'student'
        : isAdmin
          ? 'admin'
          : 'instructor'
  const sessionLabel = actorIsSuperadmin ? 'superadmin session' : 'admin session'

  return (
    <div
      role="alert"
      className="fixed top-0 left-0 right-0 z-banner bg-red-600 text-white shadow-lg"
      style={{ minHeight: '44px' }}
    >
      <div className="max-w-7xl mx-auto px-4 py-2 flex items-center justify-between gap-4">
        <div className="flex items-center gap-2 text-sm sm:text-base font-medium">
          <AlertTriangle className="w-5 h-5 flex-shrink-0" />
          <Icon className="w-4 h-4 flex-shrink-0" />
          <span>
            Viewing as {entityLabel} <span className="font-semibold">{targetName}</span>
            <span className="hidden sm:inline"> — {sessionLabel}</span>
          </span>
        </div>
        <button
          onClick={handleExit}
          disabled={exiting}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-white text-red-700 text-sm font-semibold hover:bg-red-50 transition-colors disabled:opacity-60 disabled:cursor-not-allowed"
        >
          <LogOut className="w-4 h-4" />
          <span>{exiting ? 'Exiting…' : 'Exit impersonation'}</span>
        </button>
      </div>
    </div>
  )
}

export default ImpersonationBanner
