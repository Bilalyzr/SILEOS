/**
 * AdminLayout — re-implemented on the unified DashboardWorkspace.
 *
 * Replaces the old dark sidebar with the light side-rail used across all
 * role dashboards. Same nav structure (auto-grouped where the legacy menu
 * had submenus); admin-specific impersonation banner is preserved.
 */
import React from 'react'
import { DashboardWorkspace } from '@/components/dashboard/DashboardWorkspace'
import { ADMIN_NAV } from '@/components/dashboard/nav-configs'

interface AdminLayoutProps {
  children: React.ReactNode
}

export const AdminLayout: React.FC<AdminLayoutProps> = ({ children }) => (
  <DashboardWorkspace items={ADMIN_NAV} role="admin">
    {children}
  </DashboardWorkspace>
)

export default AdminLayout
