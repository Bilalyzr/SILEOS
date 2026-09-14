/**
 * Shared "Impersonate" action for the SuperAdmin monitoring tables.
 *
 * SuperAdmin can view-as any non-superadmin user via
 * POST /superadmin/impersonate/{id}. When the target is an admin, the
 * backend REQUIRES a reason (compliance); for everyone else it's optional
 * but recommended. This hook centralises:
 *   - prompting for a reason (required for admins),
 *   - the re-auth/confirmation gate (Phase 4) before admin targets,
 *   - calling the API + the correct store start*Impersonation variant,
 *   - navigating to the target's home dashboard after the swap.
 */
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'
import { superadminApi } from '@/api/superadmin'
import { useAuthStore } from '@/store/auth'
import { roleHomePath } from '@/utils/role-routing'

export interface ImpersonateTarget {
  id: number
  display_name: string
  email: string
  role: string
}

export function useSuperadminImpersonate() {
  const navigate = useNavigate()
  const [busyId, setBusyId] = useState<number | null>(null)
  const startStudentImpersonation = useAuthStore((s) => s.startStudentImpersonation)
  const startImpersonation = useAuthStore((s) => s.startImpersonation)
  const startAdminImpersonation = useAuthStore((s) => s.startAdminImpersonation)

  const impersonate = async (target: ImpersonateTarget) => {
    if (busyId !== null) return
    if (target.role === 'superadmin') {
      toast.error('SuperAdmin accounts cannot be impersonated.')
      return
    }

    // Compliance + Phase 4 re-auth gate: impersonating an admin is sensitive,
    // so we (a) require a written reason and (b) ask the operator to confirm
    // with a deliberate OK on a window.confirm prompt. For other roles the
    // reason is optional but pre-filled so the audit row is never blank.
    const requiresReason = target.role === 'admin'
    const defaultReason = `SuperAdmin support review — ${target.role} ${target.display_name}`
    let reason = defaultReason
    if (requiresReason) {
      const entered = window.prompt(
        `Impersonating an ADMIN is a sensitive action.\n` +
          `A reason is REQUIRED and will be recorded in the audit log.\n\n` +
          `Target: ${target.display_name} (${target.email})\n` +
          `Enter a reason:`,
        defaultReason,
      )
      if (entered == null) return // cancelled
      if (!entered.trim()) {
        toast.error('A reason is required to impersonate an admin.')
        return
      }
      reason = entered.trim()
      const ok = window.confirm(
        `Confirm: start an impersonation session as admin "${target.display_name}"?\n` +
          `This will be logged with actor_role=superadmin and is time-limited to 30 minutes.`,
      )
      if (!ok) return
    }

    setBusyId(target.id)
    try {
      const res = await superadminApi.impersonate(target.id, reason)
      // Pick the right store flow based on target role so the banner +
      // restore path match what we stashed.
      if (target.role === 'student') {
        await startStudentImpersonation(
          target.id,
          target.display_name,
          target.email,
          res.access_token,
        )
      } else if (target.role === 'admin') {
        await startAdminImpersonation(
          target.id,
          target.display_name,
          target.email,
          res.access_token,
        )
      } else {
        // instructor / spoc / company / company_manager — generic flow.
        // ImpersonationTarget only carries id/display_name/role; the store's
        // startImpersonation reads email via `(target as any).email` but the
        // real profile is fetched right after via getCurrentUser anyway.
        await startImpersonation(
          {
            id: target.id,
            display_name: target.display_name,
            role: target.role,
          },
          res.access_token,
        )
      }
      toast.success(`Now viewing as ${target.display_name}`)
      // Land on the impersonated user's own dashboard.
      navigate(roleHomePath(target.role))
    } catch (e: any) {
      const detail = e?.response?.data?.detail || e?.message || 'Unknown error'
      toast.error(`Impersonation failed: ${detail}`)
    } finally {
      setBusyId(null)
    }
  }

  return { impersonate, busyId }
}
