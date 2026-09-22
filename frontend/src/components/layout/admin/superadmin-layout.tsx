/**
 * SuperAdminLayout — mirrors AdminLayout but wires the SuperAdmin nav and
 * the (shared) impersonation banner. SuperAdmin inherits admin endpoints,
 * so it reuses the same ImpersonationBanner, which now also handles the
 * `admin` impersonation type added for "view as any user".
 */
import React from 'react'
import { ImpersonationBanner } from '@/components/admin/ImpersonationBanner'
import { DashboardWorkspace } from '@/components/dashboard/DashboardWorkspace'
import { SUPERADMIN_NAV } from '@/components/dashboard/nav-configs'

interface SuperAdminLayoutProps {
  children: React.ReactNode
}

export const SuperAdminLayout: React.FC<SuperAdminLayoutProps> = ({ children }) => (
  <>
    <ImpersonationBanner />
    <DashboardWorkspace items={SUPERADMIN_NAV} role="superadmin">
      {children}
    </DashboardWorkspace>
  </>
)

export default SuperAdminLayout
