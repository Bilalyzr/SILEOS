import * as React from "react"
import { Navigate, useLocation } from "react-router-dom"
import { useAuth, useAuthContext } from "@/hooks/use-auth"
import { roleHomePath, isNonStudentRole } from "@/utils/role-routing"

interface ProtectedRouteProps {
  children: React.ReactNode
  requiredRole?: string
  requiredPermission?: string
  fallback?: React.ReactNode
}

export const ProtectedRoute: React.FC<ProtectedRouteProps> = ({
  children,
  requiredRole,
  requiredPermission,
  fallback,
}) => {
  const { isAuthenticated, isLoading, hasResolvedAuth } = useAuth()
  const { hasRole, hasPermission } = useAuthContext()
  const location = useLocation()

  // Wait until auth resolution concludes — including the first render,
  // before checkAuth() has started (hasResolvedAuth false) and while it is
  // in flight (isLoading). Without this, a cross-subdomain cookie restore
  // gets bounced to /login before the async restore finishes.
  if (isLoading || !hasResolvedAuth) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="flex flex-col items-center space-y-4">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-500"></div>
          <p className="text-neutral-600">Loading...</p>
        </div>
      </div>
    )
  }

  // Redirect to login if not authenticated
  if (!isAuthenticated) {
    return (
      <Navigate
        to="/login"
        state={{ from: location }}
        replace
      />
    )
  }

  // Check role requirement
  if (requiredRole && !hasRole(requiredRole)) {
    if (fallback) {
      return <>{fallback}</>
    }

    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center max-w-md mx-auto p-6">
          <div className="w-16 h-16 mx-auto mb-4 bg-danger-100 rounded-full flex items-center justify-center">
            <svg
              className="w-8 h-8 text-danger-600"
              fill="none"
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth="2"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5C2.962 18.333 3.924 20 5.464 20z" />
            </svg>
          </div>
          <h1 className="text-2xl font-bold text-neutral-900 mb-2">Access Denied</h1>
          <p className="text-neutral-600 mb-4">
            You don't have the required permissions to access this page.
            {requiredRole && (
              <span className="block mt-1">
                Required role: <span className="font-medium">{requiredRole}</span>
              </span>
            )}
          </p>
          <button
            onClick={() => window.history.back()}
            className="text-primary-600 hover:text-primary-700 font-medium"
          >
            Go back
          </button>
        </div>
      </div>
    )
  }

  // Check permission requirement
  if (requiredPermission && !hasPermission(requiredPermission)) {
    if (fallback) {
      return <>{fallback}</>
    }

    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center max-w-md mx-auto p-6">
          <div className="w-16 h-16 mx-auto mb-4 bg-warning-100 rounded-full flex items-center justify-center">
            <svg
              className="w-8 h-8 text-warning-600"
              fill="none"
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth="2"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <h1 className="text-2xl font-bold text-neutral-900 mb-2">Permission Required</h1>
          <p className="text-neutral-600 mb-4">
            You need additional permissions to access this feature.
            {requiredPermission && (
              <span className="block mt-1">
                Required permission: <span className="font-medium">{requiredPermission}</span>
              </span>
            )}
          </p>
          <button
            onClick={() => window.history.back()}
            className="text-primary-600 hover:text-primary-700 font-medium"
          >
            Go back
          </button>
        </div>
      </div>
    )
  }

  // All checks passed, render children
  return <>{children}</>
}

/**
 * Wraps the student dashboard. A real admin / instructor / company / spoc
 * session that lands here (e.g. via a stale `/dashboard` link) is bounced to
 * its own dashboard — the student view isn't meaningful for them. During
 * impersonation the synthetic user's role is `student`, so it stays put.
 */
export const StudentRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { user } = useAuth()
  if (user && isNonStudentRole(user.role)) {
    return <Navigate to={roleHomePath(user.role)} replace />
  }
  return <>{children}</>
}

// Higher-order component version
export const withProtectedRoute = <P extends object>(
  Component: React.ComponentType<React.PropsWithoutRef<P> & React.RefAttributes<unknown>>,
  options?: {
    requiredRole?: string
    requiredPermission?: string
    fallback?: React.ReactNode
  }
) => {
  return React.forwardRef<unknown, P>((props, ref) => (
    <ProtectedRoute {...options}>
      <Component {...props} ref={ref} />
    </ProtectedRoute>
  ))
}