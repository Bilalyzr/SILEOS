import React from 'react'
import { useAuthStore } from '@/store/auth'
import { getAvatarUrl } from '@/utils/media'
import { normalizeRole } from '@/utils/role-routing'

export const useAuth = () => {
  const {
    user,
    profile,
    instructorProfile,
    isAuthenticated,
    isLoading,
    error,
    login,
    register,
    logout,
    updateProfile,
    checkAuth,
    clearError,
  } = useAuthStore()

  // Check authentication on mount once (no checkAuth in deps since it's stable from Zustand)
  React.useEffect(() => {
    if (!user && !isLoading) {
      checkAuth().catch(console.error)
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const isInstructor = React.useMemo(() => {
    return instructorProfile?.is_approved === true
  }, [instructorProfile])

  const isStudent = React.useMemo(() => {
    return isAuthenticated && !isInstructor
  }, [isAuthenticated, isInstructor])

  const userInitials = React.useMemo(() => {
    if (!user) return ''
    return user.display_name
      .split(' ')
      .map((name) => name[0])
      .join('')
      .toUpperCase()
      .slice(0, 2)
  }, [user])

  const fullName = React.useMemo(() => {
    if (!profile) return user?.display_name || ''
    const firstName = (profile.first_name || '').trim()
    const lastName = (profile.last_name || '').trim()
    if (!firstName && !lastName) {
      // No profile name data, use display_name
      return user?.display_name || ''
    }
    // Build full name from available parts
    return [firstName, lastName].filter(Boolean).join(' ') || user?.display_name || ''
  }, [user, profile])

  const avatarUrl = React.useMemo(() => {
    return getAvatarUrl(profile)
  }, [profile])

  return {
    // State
    user,
    profile,
    instructorProfile,
    isAuthenticated,
    isLoading,
    error,
    isInstructor,
    isStudent,
    userInitials,
    fullName,
    avatarUrl,

    // Actions
    login,
    register,
    logout,
    updateProfile,
    clearError,
  }
}

// Auth context for additional features
interface AuthContextType {
  hasPermission: (permission: string) => boolean
  hasRole: (role: string) => boolean
  canAccessRoute: (route: string) => boolean
}

const AuthContext = React.createContext<AuthContextType | undefined>(undefined)

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { user, instructorProfile, isInstructor } = useAuth()

  const hasPermission = React.useCallback((permission: string): boolean => {
    if (!user) return false

    // Admin has all permissions
    if (user.user_status === 1) return true // Assuming 1 is admin status

    // Check instructor permissions
    if (isInstructor && instructorProfile?.is_approved) {
      const instructorPermissions = [
        'create_course',
        'edit_own_course',
        'view_earnings',
        'create_quiz',
        'edit_own_quiz',
        'view_students',
      ]
      return instructorPermissions.includes(permission)
    }

    // Student permissions
    const studentPermissions = [
      'enroll_course',
      'take_quiz',
      'view_certificates',
      'leave_review',
    ]
    return studentPermissions.includes(permission)
  }, [user, isInstructor, instructorProfile])

  const hasRole = React.useCallback((role: string): boolean => {
    if (!user) return false

    // Normalise both sides so role-string drift (casing/whitespace) can't
    // lock an admin out of admin routes.
    const current = normalizeRole(user.role)
    // SuperAdmin is a superset of admin: it can reach every role's routes
    // (including /admin/* and /superadmin/*).
    if (current === "superadmin") return true
    // Admin can access all roles
    if (current === "admin") return true
    return current === normalizeRole(role)
  }, [user])

  const canAccessRoute = React.useCallback((route: string): boolean => {
    if (!user) {
      // Public routes
      const publicRoutes = ['/', '/courses', '/categories', '/about', '/contact', '/login', '/register']
      return publicRoutes.some(publicRoute => route.startsWith(publicRoute))
    }

    // Admin can access everything
    if (hasRole('admin')) return true

    // Instructor routes
    if (route.startsWith('/instructor')) {
      return hasRole('instructor')
    }

    // Student routes (most routes are accessible to students)
    return true
  }, [user, hasRole])

  const value = React.useMemo(() => ({
    hasPermission,
    hasRole,
    canAccessRoute,
  }), [hasPermission, hasRole, canAccessRoute])

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuthContext = () => {
  const context = React.useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuthContext must be used within an AuthProvider')
  }
  return context
}

// Higher-order component for route protection
export const withAuth = <P extends object>(
  Component: React.ComponentType<React.PropsWithoutRef<P> & React.RefAttributes<unknown>>,
  requiredRole?: string
) => {
  return React.forwardRef<unknown, P>((props, ref) => {
    const { isAuthenticated, isLoading } = useAuth()
    const { hasRole } = useAuthContext()

    if (isLoading) {
      return (
        <div className="flex items-center justify-center min-h-screen">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-500"></div>
        </div>
      )
    }

    if (!isAuthenticated) {
      // Redirect to login
      window.location.href = '/login'
      return null
    }

    if (requiredRole && !hasRole(requiredRole)) {
      return (
        <div className="flex items-center justify-center min-h-screen">
          <div className="text-center">
            <h1 className="text-2xl font-bold text-neutral-900 mb-2">Access Denied</h1>
            <p className="text-neutral-600">You don't have permission to access this page.</p>
          </div>
        </div>
      )
    }

    return <Component {...props} ref={ref} />
  })
}

// Hook for protected routes
export const useRequireAuth = (requiredRole?: string) => {
  const { isAuthenticated, isLoading } = useAuth()
  const { hasRole } = useAuthContext()

  React.useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      window.location.href = '/login'
    }
  }, [isAuthenticated, isLoading])

  React.useEffect(() => {
    if (!isLoading && isAuthenticated && requiredRole && !hasRole(requiredRole)) {
      window.location.href = '/unauthorized'
    }
  }, [isAuthenticated, isLoading, requiredRole, hasRole])

  return {
    isLoading: isLoading || (!isAuthenticated && !isLoading),
    isAuthorized: isAuthenticated && (!requiredRole || hasRole(requiredRole)),
  }
}