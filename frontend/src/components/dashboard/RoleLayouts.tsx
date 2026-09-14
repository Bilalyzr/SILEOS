/**
 * Per-role workspace layouts. Each is a thin wrapper around
 * DashboardWorkspace with the correct nav config + role chip baked in.
 *
 * Use these in App.tsx to wrap any private route that should show the
 * left sidebar (instead of the public MainLayout marketing nav).
 */
import * as React from 'react'
import { DashboardWorkspace } from './DashboardWorkspace'
import { STUDENT_NAV, INSTRUCTOR_NAV, SPOC_NAV, ADMIN_NAV, SUPERADMIN_NAV, PARENT_NAV, ACCOUNT_NAV } from './nav-configs'
import { useAuthStore } from '@/store/auth'
import type { Role } from './DashboardSidebar'

export const StudentLayout: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <DashboardWorkspace items={STUDENT_NAV} role="student">
    {children}
  </DashboardWorkspace>
)

export const InstructorLayout: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <DashboardWorkspace items={INSTRUCTOR_NAV} role="instructor">
    {children}
  </DashboardWorkspace>
)

export const SpocLayout: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <DashboardWorkspace items={SPOC_NAV} role="spoc">
    {children}
  </DashboardWorkspace>
)

/**
 * Auto-pick the role layout based on the currently logged-in user.
 * Used for shared private routes (/profile, /settings, etc.) so an
 * instructor sees the instructor sidebar, a student sees the student
 * sidebar, etc. Falls back to StudentLayout if role is missing.
 */
export const AutoRoleLayout: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const role = useAuthStore((s) => s.user?.role) as Role | undefined
  switch (role) {
    case 'instructor':
      return <DashboardWorkspace items={INSTRUCTOR_NAV} role="instructor">{children}</DashboardWorkspace>
    case 'spoc':
      return <DashboardWorkspace items={SPOC_NAV} role="spoc">{children}</DashboardWorkspace>
    case 'admin':
      return <DashboardWorkspace items={ADMIN_NAV} role="admin">{children}</DashboardWorkspace>
    case 'superadmin':
      return <DashboardWorkspace items={SUPERADMIN_NAV} role="superadmin">{children}</DashboardWorkspace>
    case 'company':
    case 'company_manager':
      // Company users have their own dashboard with in-page tabs; their
      // /profile page just gets a thin sidebar so they're not stranded
      // outside their workspace. Re-use the admin shell to keep it simple.
      return <DashboardWorkspace items={ACCOUNT_NAV} role={role}>{children}</DashboardWorkspace>
    case 'parent':
      return <DashboardWorkspace items={PARENT_NAV} role="parent">{children}</DashboardWorkspace>
    case 'student':
    default:
      return <DashboardWorkspace items={STUDENT_NAV} role="student">{children}</DashboardWorkspace>
  }
}
