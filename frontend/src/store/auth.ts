import {purgeOwner} from '@/offline/storage'
import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { User, UserProfile, InstructorProfile, LoginForm, RegisterForm } from '@/types'
import { authAPI } from '@/api/auth'

// sessionStorage keys used to stash the admin's original tokens while a
// "View as Instructor" impersonation session is active. Scoped per-tab so
// multiple admin tabs don't clobber each other's sessions.
export const ADMIN_STASH_KEYS = {
  access: 'sasha_admin_access',
  refresh: 'sasha_admin_refresh',
  user: 'sasha_admin_user',
  profile: 'sasha_admin_profile',
  instructorProfile: 'sasha_admin_instructorProfile',
  impersonationType: 'sasha_impersonation_type', // 'instructor' | 'company' | 'student' | 'spoc'
  targetName: 'sasha_target_name', // display name of impersonated entity
} as const

export const isImpersonating = (): boolean => {
  try {
    return typeof sessionStorage !== 'undefined' &&
      sessionStorage.getItem(ADMIN_STASH_KEYS.access) !== null
  } catch {
    return false
  }
}

interface ImpersonationTarget {
  id: number
  display_name: string
  role?: string
}

// Module-level single-flight guard for token refresh. When several authed
// requests 401 at the same time (e.g. the admin dashboard firing /admin/stats
// and /admin/revenue-timeseries on mount), every failed request calls
// refreshAccessToken(). Because the backend ROTATES the refresh token, the
// first refresh invalidates the token the others are still holding, so the
// 2nd+ refresh fails and logs the user out. Sharing one in-flight promise
// means concurrent callers all wait for the single refresh.
let refreshInFlight: Promise<void> | null = null

interface AuthState {
  // State
  user: User | null
  profile: UserProfile | null
  instructorProfile: InstructorProfile | null
  accessToken: string | null
  refreshToken: string | null
  isAuthenticated: boolean
  isLoading: boolean
  error: string | null

  // Actions
  login: (credentials: LoginForm) => Promise<void>
  register: (data: RegisterForm) => Promise<void>
  googleSignIn: (idToken: string) => Promise<Awaited<ReturnType<typeof authAPI.googleSignIn>> | void>
  logout: () => void
  refreshAccessToken: () => Promise<void>
  updateProfile: (profile: Partial<UserProfile>) => Promise<void>
  setProfile: (profile: Partial<UserProfile>) => void
  setAuthState: (authData: {
    user: User
    profile: UserProfile
    instructorProfile: InstructorProfile | null
    accessToken: string
    refreshToken: string
  }) => void
  checkAuth: () => Promise<void>
  clearError: () => void
  setLoading: (loading: boolean) => void

  // Impersonation
  startImpersonation: (target: ImpersonationTarget, impersonationToken: string) => Promise<void>
  startStudentImpersonation: (studentId: number, studentName: string, studentEmail: string, impersonationToken: string) => Promise<void>
  startCompanyImpersonation: (companyId: number, companyName: string, impersonationToken: string, ownerEmail?: string) => Promise<void>
  startSpocImpersonation: (spocId: number, spocName: string, impersonationToken: string, spocEmail?: string) => Promise<void>
  // SuperAdmin "view as admin". Mirrors the four start*Impersonation flows
  // above; the stash + restore path is identical, only the type label and
  // synthetic role differ. Used from the SuperAdmin admins dashboard.
  startAdminImpersonation: (adminId: number, adminName: string, adminEmail: string, impersonationToken: string) => Promise<void>
  getImpersonationType: () => 'instructor' | 'company' | 'student' | 'spoc' | 'admin' | null
  getTargetName: () => string | null
  endImpersonation: () => boolean
  isImpersonating: () => boolean
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      // Initial state
      user: null,
      profile: null,
      instructorProfile: null,
      accessToken: null,
      refreshToken: null,
      isAuthenticated: false,
      isLoading: false,
      error: null,

      // Actions
      login: async (credentials: LoginForm) => {
        try {
          set({ isLoading: true, error: null })

          const response = await authAPI.login(credentials)

          set({
            user: response.user,
            profile: response.profile,
            instructorProfile: response.instructorProfile,
            accessToken: response.accessToken,
            refreshToken: response.refreshToken,
            isAuthenticated: true,
            isLoading: false,
          })
        } catch (error: any) {
          // Extract error message from axios response
          const errorMessage = error.response?.data?.detail || error.message || 'Login failed'
          set({
            error: errorMessage,
            isLoading: false,
          })
          throw error
        }
      },

      register: async (data: RegisterForm) => {
        try {
          set({ isLoading: true, error: null })

          const response = await authAPI.register(data)

          set({
            user: response.user,
            profile: response.profile,
            instructorProfile: response.instructorProfile,
            accessToken: response.accessToken,
            refreshToken: response.refreshToken,
            isAuthenticated: true,
            isLoading: false,
          })
        } catch (error: any) {
          // Extract error message from axios response
          const errorMessage = error.response?.data?.detail || error.message || 'Registration failed'
          set({
            error: errorMessage,
            isLoading: false,
          })
          throw error
        }
      },

      googleSignIn: async (idToken: string) => {
        try {
          set({ isLoading: true, error: null })

          const response = await authAPI.googleSignIn(idToken)

          // Check if this is a new user that needs role selection
          if ('new_user' in response) {
            // Don't set auth state - let the component show the role selection modal
            set({ isLoading: false })
            return response // Return the response so the caller can handle it
          }

          // Existing user - set auth state
          set({
            user: response.user,
            profile: response.profile,
            instructorProfile: response.instructorProfile,
            accessToken: response.accessToken,
            refreshToken: response.refreshToken,
            isAuthenticated: true,
            isLoading: false,
          })
        } catch (error: any) {
          const errorMessage = error.response?.data?.detail || error.message || 'Google sign-in failed'
          set({
            error: errorMessage,
            isLoading: false,
          })
          throw error
        }
      },

      logout: () => {
        const offlineOwner = get().user?.id
        if (offlineOwner) void purgeOwner(offlineOwner).catch(()=>{})
        try {
          // Call logout API to invalidate tokens on server
          const { refreshToken } = get()
          if (refreshToken) {
            authAPI.logout(refreshToken).catch(console.error)
          }
        } catch (error) {
          console.error('Logout API error:', error)
        }

        set({
          user: null,
          profile: null,
          instructorProfile: null,
          accessToken: null,
          refreshToken: null,
          isAuthenticated: false,
          error: null,
        })
      },

      refreshAccessToken: async () => {
        // Reuse an in-flight refresh so concurrent 401s don't each spend
        // (and invalidate) the rotating refresh token — see refreshInFlight.
        if (refreshInFlight) return refreshInFlight

        refreshInFlight = (async () => {
          try {
            const { refreshToken } = get()
            const response = await authAPI.refreshToken(refreshToken)

            set({
              accessToken: response.accessToken,
              refreshToken: response.refreshToken,
            })
          } catch (error) {
            // If refresh fails, end the session — but only when THIS context
            // actually owned one. The boot-time cookie probe calls this with
            // no tokens at all (expected 401 for anonymous visitors), and a
            // second app instance (e.g. a lab iframe before that fix) could
            // lose the refresh-rotation race and wipe the shared storage out
            // from under the still-valid main session.
            if (get().isAuthenticated || get().accessToken || get().refreshToken) {
              get().logout()
            }
            throw error
          } finally {
            refreshInFlight = null
          }
        })()

        return refreshInFlight
      },

      updateProfile: async (profileData: Partial<UserProfile>) => {
        try {
          set({ isLoading: true, error: null })

          const { accessToken } = get()
          if (!accessToken) {
            throw new Error('Not authenticated')
          }

          const updatedProfile = await authAPI.updateProfile(profileData)

          set({
            profile: updatedProfile,
            isLoading: false,
          })
        } catch (error: any) {
          set({
            error: error.message || 'Profile update failed',
            isLoading: false,
          })
          throw error
        }
      },

      setProfile: (profileData: Partial<UserProfile>) => {
        const currentProfile = get().profile
        const currentUser = get().user
        if (currentProfile) {
          const updatedProfile = { ...currentProfile, ...profileData }

          // Create NEW user object so Zustand detects the change
          const updatedUser = profileData.profile_completed !== undefined && currentUser
            ? { ...currentUser, profile_completed: profileData.profile_completed }
            : currentUser

          set({
            profile: updatedProfile,
            user: updatedUser
          })
        }
      },

      setAuthState: (authData) => {
        set({
          user: authData.user,
          profile: authData.profile,
          instructorProfile: authData.instructorProfile,
          accessToken: authData.accessToken,
          refreshToken: authData.refreshToken,
          isAuthenticated: true,
          isLoading: false,
          error: null,
        })
      },

      checkAuth: async () => {
        // Prevent concurrent calls - if already loading or authenticated, skip
        const state = get()
        if (state.isLoading || (state.isAuthenticated && state.user)) {
          return
        }

        try {
          const { accessToken } = get()

          if (!accessToken) {
            // localStorage is origin-scoped. Restore a Sasha-wide session from
            // the HttpOnly refresh cookie when entering a sibling subdomain.
            try {
              await get().refreshAccessToken()
            } catch {
              set({ isLoading: false })
              return
            }
          }

          // Proceed even without a refresh token — /auth/me only needs the
          // access token, and bailing here used to leave `user` empty (the
          // dashboard then showed "You"). Impersonation sessions never carry a
          // refresh token either. If the access token is expired we attempt a
          // refresh below and only log out if that refresh fails.
          set({ isLoading: true })

          try {
            // Try to get current user with access token
            const response = await authAPI.getCurrentUser(get().accessToken || '')

            set({
              user: response.user,
              profile: response.profile,
              instructorProfile: response.instructorProfile,
              isAuthenticated: true,
              isLoading: false,
            })
          } catch (error: any) {
            // Axios puts the HTTP status on error.response.status (not
            // error.status); reading the wrong field meant a 401 never
            // triggered a refresh and instead fell through to logout.
            const status = error?.response?.status ?? error?.status
            if (status === 401) {
              // Access token expired, try refresh
              try {
                await get().refreshAccessToken()
                // Retry getting user data
                const response = await authAPI.getCurrentUser(get().accessToken!)

                set({
                  user: response.user,
                  profile: response.profile,
                  instructorProfile: response.instructorProfile,
                  isAuthenticated: true,
                  isLoading: false,
                })
              } catch (refreshError) {
                // Refresh genuinely failed → the session is dead, log out.
                get().logout()
                set({ isLoading: false })
              }
            } else {
              // Network / server error (e.g. 500). Do NOT log the user out —
              // wiping the session here is what blanked identity to "You" on a
              // transient backend hiccup. Keep the existing session + token.
              console.warn('checkAuth: keeping session despite fetch error', error)
              set({ isLoading: false })
            }
          }
        } catch (error: any) {
          // Unexpected error — preserve the session, just clear the loading
          // flag rather than logging the user out.
          console.warn('checkAuth failed; preserving session', error)
          set({ isLoading: false })
        }
      },

      clearError: () => set({ error: null }),
      setLoading: (loading: boolean) => set({ isLoading: loading }),

      // --- Impersonation ------------------------------------------------
      // startImpersonation: stash admin tokens + identity into
      // sessionStorage (per-tab, so it dies with the tab), then overwrite
      // the Zustand store with the impersonation token and fetch the
      // impersonated user's real data.
      startImpersonation: async (target, impersonationToken) => {
        const state = get()
        try {
          if (state.accessToken) sessionStorage.setItem(ADMIN_STASH_KEYS.access, state.accessToken)
          if (state.refreshToken) sessionStorage.setItem(ADMIN_STASH_KEYS.refresh, state.refreshToken)
          if (state.user) sessionStorage.setItem(ADMIN_STASH_KEYS.user, JSON.stringify(state.user))
          if (state.profile) sessionStorage.setItem(ADMIN_STASH_KEYS.profile, JSON.stringify(state.profile))
          if (state.instructorProfile) {
            sessionStorage.setItem(
              ADMIN_STASH_KEYS.instructorProfile,
              JSON.stringify(state.instructorProfile),
            )
          }
          // Store impersonation type and target name for banner display
          sessionStorage.setItem(ADMIN_STASH_KEYS.impersonationType, 'instructor')
          sessionStorage.setItem(ADMIN_STASH_KEYS.targetName, target.display_name)
        } catch (e) {
          console.error('Failed to stash admin session for impersonation:', e)
        }

        const impersonatedUser = {
          ...(state.user || ({} as any)),
          id: target.id,
          display_name: target.display_name,
          user_email: (target as any).email || '',
          email: (target as any).email || '',
          role: (target.role || 'instructor') as any,
        } as unknown as User

        // Set the impersonation token and synthetic user first
        set({
          user: impersonatedUser,
          profile: null,
          instructorProfile: null,
          accessToken: impersonationToken,
          refreshToken: null,
          isAuthenticated: true,
        })

        // Immediately fetch the real user data with the impersonation token
        try {
          const { authAPI } = await import('@/api/auth')
          const response = await authAPI.getCurrentUser(impersonationToken)
          set({
            user: response.user,
            profile: response.profile,
            instructorProfile: response.instructorProfile,
          })
        } catch (error) {
          console.error('Failed to fetch impersonated user data:', error)
        }
      },

      // startStudentImpersonation: similar to startImpersonation but for students.
      // The backend returns a token scoped to the student account.
      startStudentImpersonation: async (studentId, studentName, studentEmail, impersonationToken) => {
        const state = get()
        try {
          if (state.accessToken) sessionStorage.setItem(ADMIN_STASH_KEYS.access, state.accessToken)
          if (state.refreshToken) sessionStorage.setItem(ADMIN_STASH_KEYS.refresh, state.refreshToken)
          if (state.user) sessionStorage.setItem(ADMIN_STASH_KEYS.user, JSON.stringify(state.user))
          if (state.profile) sessionStorage.setItem(ADMIN_STASH_KEYS.profile, JSON.stringify(state.profile))
          if (state.instructorProfile) {
            sessionStorage.setItem(
              ADMIN_STASH_KEYS.instructorProfile,
              JSON.stringify(state.instructorProfile),
            )
          }
          // Store impersonation type and target name for banner display
          sessionStorage.setItem(ADMIN_STASH_KEYS.impersonationType, 'student')
          sessionStorage.setItem(ADMIN_STASH_KEYS.targetName, studentName)
        } catch (e) {
          console.error('Failed to stash admin session for student impersonation:', e)
        }

        // Create a synthetic user for the student
        const impersonatedUser = {
          ...(state.user || ({} as any)),
          id: studentId,
          display_name: studentName,
          user_email: studentEmail,
          email: studentEmail,
          role: 'student' as any,
        } as unknown as User

        // Set the impersonation token and synthetic user first
        set({
          user: impersonatedUser,
          profile: null,
          instructorProfile: null,
          accessToken: impersonationToken,
          refreshToken: null,
          isAuthenticated: true,
        })

        // Immediately fetch the real user data with the impersonation token
        try {
          const { authAPI } = await import('@/api/auth')
          const response = await authAPI.getCurrentUser(impersonationToken)
          set({
            user: response.user,
            profile: response.profile,
            instructorProfile: response.instructorProfile,
          })
        } catch (error) {
          console.error('Failed to fetch impersonated user data:', error)
        }
      },

      // startCompanyImpersonation: similar to startImpersonation but for companies.
      // The backend returns a token scoped to the company owner account.
      startCompanyImpersonation: async (companyId, companyName, impersonationToken, ownerEmail = '') => {
        const state = get()
        try {
          if (state.accessToken) sessionStorage.setItem(ADMIN_STASH_KEYS.access, state.accessToken)
          if (state.refreshToken) sessionStorage.setItem(ADMIN_STASH_KEYS.refresh, state.refreshToken)
          if (state.user) sessionStorage.setItem(ADMIN_STASH_KEYS.user, JSON.stringify(state.user))
          if (state.profile) sessionStorage.setItem(ADMIN_STASH_KEYS.profile, JSON.stringify(state.profile))
          if (state.instructorProfile) {
            sessionStorage.setItem(
              ADMIN_STASH_KEYS.instructorProfile,
              JSON.stringify(state.instructorProfile),
            )
          }
          // Store impersonation type and target name for banner display
          sessionStorage.setItem(ADMIN_STASH_KEYS.impersonationType, 'company')
          sessionStorage.setItem(ADMIN_STASH_KEYS.targetName, companyName)
        } catch (e) {
          console.error('Failed to stash admin session for company impersonation:', e)
        }

        // Create a synthetic user for the company owner
        const impersonatedUser = {
          ...(state.user || ({} as any)),
          id: companyId,
          display_name: companyName,
          user_email: ownerEmail,
          email: ownerEmail,
          role: 'company' as any,
        } as unknown as User

        // Set the impersonation token and synthetic user first
        set({
          user: impersonatedUser,
          profile: null,
          instructorProfile: null,
          accessToken: impersonationToken,
          refreshToken: null,
          isAuthenticated: true,
        })

        // Immediately fetch the real user data with the impersonation token
        try {
          const { authAPI } = await import('@/api/auth')
          const response = await authAPI.getCurrentUser(impersonationToken)
          set({
            user: response.user,
            profile: response.profile,
            instructorProfile: response.instructorProfile,
          })
        } catch (error) {
          console.error('Failed to fetch impersonated user data:', error)
        }
      },

      // startSpocImpersonation: similar to startImpersonation but for SPOCs.
      // The backend returns a token scoped to the SPOC account.
      startSpocImpersonation: async (spocId, spocName, impersonationToken, spocEmail = '') => {
        const state = get()
        try {
          if (state.accessToken) sessionStorage.setItem(ADMIN_STASH_KEYS.access, state.accessToken)
          if (state.refreshToken) sessionStorage.setItem(ADMIN_STASH_KEYS.refresh, state.refreshToken)
          if (state.user) sessionStorage.setItem(ADMIN_STASH_KEYS.user, JSON.stringify(state.user))
          if (state.profile) sessionStorage.setItem(ADMIN_STASH_KEYS.profile, JSON.stringify(state.profile))
          if (state.instructorProfile) {
            sessionStorage.setItem(
              ADMIN_STASH_KEYS.instructorProfile,
              JSON.stringify(state.instructorProfile),
            )
          }
          // Store impersonation type and target name for banner display
          sessionStorage.setItem(ADMIN_STASH_KEYS.impersonationType, 'spoc')
          sessionStorage.setItem(ADMIN_STASH_KEYS.targetName, spocName)
        } catch (e) {
          console.error('Failed to stash admin session for SPOC impersonation:', e)
        }

        // Create a synthetic user for the SPOC
        const impersonatedUser = {
          ...(state.user || ({} as any)),
          id: spocId,
          display_name: spocName,
          user_email: spocEmail,
          email: spocEmail,
          role: 'spoc' as any,
        } as unknown as User

        // Set the impersonation token and synthetic user first
        set({
          user: impersonatedUser,
          profile: null,
          instructorProfile: null,
          accessToken: impersonationToken,
          refreshToken: null,
          isAuthenticated: true,
        })

        // Immediately fetch the real user data with the impersonation token
        try {
          const { authAPI } = await import('@/api/auth')
          const response = await authAPI.getCurrentUser(impersonationToken)
          set({
            user: response.user,
            profile: response.profile,
            instructorProfile: response.instructorProfile,
          })
        } catch (error) {
          console.error('Failed to fetch impersonated user data:', error)
        }
      },

      // startAdminImpersonation: SuperAdmin "view as admin". Same stash +
      // restore mechanics as the other four flows; only the type label
      // ('admin') and synthetic role differ.
      startAdminImpersonation: async (adminId, adminName, adminEmail, impersonationToken) => {
        const state = get()
        try {
          if (state.accessToken) sessionStorage.setItem(ADMIN_STASH_KEYS.access, state.accessToken)
          if (state.refreshToken) sessionStorage.setItem(ADMIN_STASH_KEYS.refresh, state.refreshToken)
          if (state.user) sessionStorage.setItem(ADMIN_STASH_KEYS.user, JSON.stringify(state.user))
          if (state.profile) sessionStorage.setItem(ADMIN_STASH_KEYS.profile, JSON.stringify(state.profile))
          if (state.instructorProfile) {
            sessionStorage.setItem(
              ADMIN_STASH_KEYS.instructorProfile,
              JSON.stringify(state.instructorProfile),
            )
          }
          sessionStorage.setItem(ADMIN_STASH_KEYS.impersonationType, 'admin')
          sessionStorage.setItem(ADMIN_STASH_KEYS.targetName, adminName)
        } catch (e) {
          console.error('Failed to stash admin session for admin impersonation:', e)
        }

        const impersonatedUser = {
          ...(state.user || ({} as any)),
          id: adminId,
          display_name: adminName,
          user_email: adminEmail,
          email: adminEmail,
          role: 'admin' as any,
        } as unknown as User

        set({
          user: impersonatedUser,
          profile: null,
          instructorProfile: null,
          accessToken: impersonationToken,
          refreshToken: null,
          isAuthenticated: true,
        })

        try {
          const { authAPI } = await import('@/api/auth')
          const response = await authAPI.getCurrentUser(impersonationToken)
          set({
            user: response.user,
            profile: response.profile,
            instructorProfile: response.instructorProfile,
          })
        } catch (error) {
          console.error('Failed to fetch impersonated user data:', error)
        }
      },

      getImpersonationType: () => {
        try {
          return sessionStorage.getItem(ADMIN_STASH_KEYS.impersonationType) as 'instructor' | 'company' | 'student' | 'spoc' | 'admin' | null
        } catch {
          return null
        }
      },

      getTargetName: () => {
        try {
          return sessionStorage.getItem(ADMIN_STASH_KEYS.targetName)
        } catch {
          return null
        }
      },

      // endImpersonation: restore admin tokens from sessionStorage. Returns
      // true if an admin session was restored, false if nothing to restore.
      endImpersonation: () => {
        try {
          const access = sessionStorage.getItem(ADMIN_STASH_KEYS.access)
          const refresh = sessionStorage.getItem(ADMIN_STASH_KEYS.refresh)
          const userRaw = sessionStorage.getItem(ADMIN_STASH_KEYS.user)
          const profileRaw = sessionStorage.getItem(ADMIN_STASH_KEYS.profile)
          const instructorProfileRaw = sessionStorage.getItem(ADMIN_STASH_KEYS.instructorProfile)

          if (!access || !userRaw) {
            // Nothing stashed — treat as a plain logout-adjacent no-op so
            // the caller can still clear its local UI state.
            Object.values(ADMIN_STASH_KEYS).forEach((k) => sessionStorage.removeItem(k))
            return false
          }

          const user = JSON.parse(userRaw) as User
          const profile = profileRaw ? (JSON.parse(profileRaw) as UserProfile) : null
          const instructorProfile = instructorProfileRaw
            ? (JSON.parse(instructorProfileRaw) as InstructorProfile)
            : null

          set({
            user,
            profile,
            instructorProfile,
            accessToken: access,
            refreshToken: refresh,
            isAuthenticated: true,
          })

          Object.values(ADMIN_STASH_KEYS).forEach((k) => sessionStorage.removeItem(k))
          return true
        } catch (e) {
          console.error('Failed to restore admin session:', e)
          Object.values(ADMIN_STASH_KEYS).forEach((k) => {
            try { sessionStorage.removeItem(k) } catch {}
          })
          return false
        }
      },

      isImpersonating: () => isImpersonating(),
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({
        user: state.user,
        profile: state.profile,
        instructorProfile: state.instructorProfile,
        accessToken: state.accessToken,
        refreshToken: state.refreshToken,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
)
