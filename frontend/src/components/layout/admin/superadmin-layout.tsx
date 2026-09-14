/**
 * SuperAdminLayout — mirrors AdminLayout but wires the SuperAdmin nav.
 * The impersonation banner is rendered INSIDE DashboardWorkspace (line ~98),
 * so it must not be repeated here — rendering it twice stacked two banners
 * on every superadmin route during impersonation.
 */
import React from 'react'
import { DashboardWorkspace } from '@/components/dashboard/DashboardWorkspace'
import { SUPERADMIN_NAV } from '@/components/dashboard/nav-configs'

interface SuperAdminLayoutProps {
  children: React.ReactNode
}

export const SuperAdminLayout: React.FC<SuperAdminLayoutProps> = ({ children }) => (
  <DashboardWorkspace items={SUPERADMIN_NAV} role="superadmin">
    {children}
  </DashboardWorkspace>
)

export default SuperAdminLayout
