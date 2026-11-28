import * as React from "react"
import { Navigate, useLocation } from "react-router-dom"
import { useAuth } from "@/hooks/use-auth"
import { roleHomePath, normalizeRole } from "@/utils/role-routing"
import { InfinityTrace } from "@/components/loading/InfinityTrace"

/**
 * Guard for every Campus workspace route (/institutions/*).
 *
 * Campus has its own sign-in (/campus/login) and its own administrators
 * (`campus_admin`). LMS admin/superadmin are sent back to their own dashboard,
 * so the two products never share an administrator or bounce into each other.
 */
export const CampusRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { isAuthenticated, isLoading, hasResolvedAuth, user } = useAuth()
  const location = useLocation()

  if (isLoading || !hasResolvedAuth) {
    return <InfinityTrace label="Checking your session" fullscreen />
  }
  if (!isAuthenticated) {
    return <Navigate to="/campus/login" state={{ from: location }} replace />
  }
  const role = normalizeRole(user?.role)
  if (role === "admin" || role === "superadmin") {
    return <Navigate to={roleHomePath(role)} replace />
  }
  return <>{children}</>
}
