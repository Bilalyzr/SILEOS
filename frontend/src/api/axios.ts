import axios, { AxiosResponse, AxiosError } from 'axios'
import toast from 'react-hot-toast'
import { useAuthStore, isImpersonating } from '@/store/auth'

// Use environment variable for backend URL, fallback to relative path for development
const API_BASE_URL = import.meta.env.VITE_API_URL || '/api/v1'

// Create axios instance
export const api = axios.create({
  baseURL: API_BASE_URL,
  withCredentials: true,
  timeout: 300000,
  headers: {
    'Content-Type': 'application/json',
    'Cache-Control': 'no-cache, no-store, must-revalidate',
    'Pragma': 'no-cache',
    'Expires': '0',
    'X-Build-Timestamp': new Date().toISOString(),
  },
})

// Request interceptor to add auth token and handle trailing slashes
api.interceptors.request.use(
  (config) => {
    const token = useAuthStore.getState().accessToken
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }

    // FormData bodies must NEVER carry our instance-default JSON
    // Content-Type (or any manual one without a boundary) — the browser
    // sets multipart/form-data with the generated boundary itself.
    // Without this, every FormData post that didn't set an explicit
    // multipart header shipped as application/json and the backend saw
    // "Field required" for every Form() field (H5P chunked init bug).
    if (typeof FormData !== 'undefined' && config.data instanceof FormData) {
      delete config.headers['Content-Type']
      delete config.headers['content-type']
      try { config.headers.delete?.('Content-Type') } catch { /* older axios */ }
    }

    // Handle trailing slashes intelligently based on endpoint patterns
    if (config.url && !config.url.endsWith('/')) {

      // Comprehensive list of endpoints that don't need trailing slashes
      const noSlashEndpoints = [
        // User endpoints
        '/users/profile', '/users/stats', '/users/avatar',

        // Dashboard endpoints
        '/dashboard/student', '/dashboard/instructor', '/dashboard/admin',

        // Admin endpoints
        '/admin/stats', '/admin/courses', '/admin/users',
        '/templates',

        // Auth endpoints
        '/auth/logout', '/auth/refresh', '/auth/me', '/auth/profile',
        '/auth/change-password', '/auth/forgot-password', '/auth/reset-password',
        '/auth/verify-email', '/auth/resend-verification', '/auth/check-email',
        '/auth/roles', '/auth/instructor-profile',

        // Upload endpoints
        '/upload/image', '/upload/video', '/upload/document', '/upload/file', '/upload/info',
        '/upload/chunked/init', '/upload/chunked',

        // Nested course endpoints (no trailing slashes)
        '/courses/publish', '/courses/unpublish', '/courses/featured', '/courses/popular',
        '/courses/search', '/courses/my-courses', '/courses/pending', '/wishlist',

        // Certificate endpoints (no trailing slashes)
        '/certificates/generate', '/certificates/regenerate', '/certificates/verify',
        '/certificates/download', '/certificates/templates', '/certificates/admin',

        // Admin internship override endpoints (attendance, assign-company)
        '/admin/internships',

        // Content endpoints
        '/categories', '/tags', '/instructors',

        // Static files and other endpoints
        '/payments', '/quizzes', '/assignments', '/coupons',

        // Video extraction endpoint
        '/stream/extract',
        '/bunny/video', '/bunny',

        // Digital Library (backend/app/routers/library.py): create is
        // POST /api/v1/library with NO trailing slash — same rule as h5p.
        '/library',
        '/geogebra',
        // Content libraries (2026-09-05): labs catalog, 3D library, admin imports
        '/virtual-labs', '/three-d', '/admin/content-library',
        // Scorable-item registry (WP1) — bare prefix, no sub-path, so the hyphen rule misses it
        '/scorable-items',
        // 3D match-and-verify tasks (WP2)
        '/three-d-tasks',
        // Learner mastery graph (WP3)
        '/mastery',
        '/studio',
        '/ai',
        '/flywheel',
        '/funnel',
        '/course-ops',
        '/signals',
        '/planner',
        '/assessment-studio',
        '/recording-lessons',
        '/course-packages',
        '/exam-papers', '/courses/slug-availability',
        '/admin/operations',
        // Education OS control planes. Their FastAPI routers use @router.get("")
        // and redirect_slashes is disabled, so adding a slash makes every new
        // vertical/control-plane collection look like a missing endpoint.
        '/platform', '/meiporul', '/seyappaduporul', '/utporul',
        '/institutions',
        '/parents',
        // Account-wide WhatsApp self-service and admin communications.
        // Every route is declared without a trailing slash.
        '/whatsapp',
        '/question-banks',   // legacy SILEOS router declares @router.get("") — trailing slash 404s (found 2026-09-05)
        // Emergent taxonomy (WP4)
        '/tag-taxonomy',
        // Chunked upload endpoints (init/chunk/complete/cancel) are all
        // declared WITHOUT trailing slashes.
        '/upload/chunked',

        // H5P endpoints (plan Task 5). Backend runs with redirect_slashes=False
        // and only the list endpoint (GET /api/v1/h5p/) declares a trailing
        // slash — /h5p/finalize, /h5p/{public_id}, /h5p/{public_id}/result and
        // /h5p/{public_id}/results all 404 if one gets appended. This matches
        // on substring (see isStaticNoSlashEndpoint below), so '/h5p/' alone
        // is enough to cover every non-list h5p path.
        '/h5p/',

        // Gamification endpoints (plan Task 10). Same redirect_slashes=False
        // story: /gamification/me, /me/unseen, /me/unseen/mark-seen,
        // /leaderboard and /me/settings all 404 with an appended slash.
        '/gamification',

        // Analytics + internships
        '/analytics', '/internships',
        // Notifications mark-all-read: backend declares POST /read-all with
        // NO trailing slash and redirect_slashes=False — appending one 404s.
        '/notifications/read-all',

        // Internship-portal subsystems (SS1/SS2/SS3). Backend runs with
        // redirect_slashes=False and none of these routes declare a trailing
        // slash, so appending one produces a 404.
        '/candidates', '/companies', '/cohorts', '/checkout',
        '/admin/spocs', '/admin/companies', '/admin/colleges', '/admin/cohorts',

        // Company dashboard endpoints (SS3) - MUST NOT have trailing slashes
        '/companies/me',

        // Paid-internship-program SPOC + admin paths.
        '/spoc/my-internships', '/spoc/internships', '/admin/internships',
        '/internships/my-vouchers', '/internships/purchase',

        // SPOC-scoped export endpoints (export_import.py's
        // GET /spoc/export/{section}). Backend runs with
        // redirect_slashes=False and this route declares no trailing slash.
        '/spoc/export',

        // SuperAdmin monitoring + impersonation endpoints. Backend declares
        // no trailing slash and runs with redirect_slashes=False.
        '/superadmin',

        // Wall of Fame endpoints (backend declares both / and no-slash).
        '/hall-of-fame',

        // Membership endpoints. Backend router declares no trailing slash and
        // runs with redirect_slashes=False.
        '/memberships/plans', '/memberships/subscribe', '/memberships/me', '/memberships/cancel',

        // Bundle endpoints. Backend router declares no trailing slash and
        // runs with redirect_slashes=False. /bundles/{slug} uses a string
        // slug (not \d+), so it isn't caught by isDynamicNoSlashEndpoint below.
        '/bundles',

        // Company billing portal endpoints (SS3 invoicing). Backend router
        // is mounted at /api/v1/companies/billing with redirect_slashes=False.
        // Multi-segment paths like /companies/billing/invoices/5/pdf aren't
        // caught by isDynamicNoSlashEndpoint's single-segment \d+ pattern.
        '/companies/billing',

        // Live Classes endpoints (all live_class_*.py routers, mounted at
        // /api/v1/live and /api/v1/internal/live with redirect_slashes=False).
        // Multi-segment paths like /live/classes/5/join-token or
        // /live/classes/5/polls/3/vote aren't caught by
        // isDynamicNoSlashEndpoint's single-segment \d+ pattern.
        '/live',

        // Learning Games endpoints (spec §3). redirect_slashes=False and no
        // games route declares a trailing slash — /games, /games/mine,
        // /games/{id}, /games/{id}/play, /games/{id}/results,
        // /games/{id}/publish, /games/{id}/unpublish all 404 with one appended.
        '/games'
      ]

      // Endpoints that MUST have trailing slashes (based on backend FastAPI schema)
      const trailingSlashEndpoints = [
        '/blog',
        '/courses',
        '/auth/login',
        '/auth/register',
        '/auth/register-instructor',
        // S-H1: GET/POST /wishlist declare a trailing slash on the backend
        // (wishlist.py:19,45 — @router.get("/") / @router.post("/")) and
        // redirect_slashes=False means a slash-less call 404s. '/wishlist'
        // is ALSO in noSlashEndpoints below for DELETE /wishlist/{course_id}
        // (no trailing slash there), but this exact-match check runs first
        // so it only forces the slash for the bare collection endpoint.
        '/wishlist'
      ]

      // Check if this is a static no-slash endpoint
      const isStaticNoSlashEndpoint = noSlashEndpoints.some(endpoint => config.url?.includes(endpoint))

      // Check if this endpoint requires a trailing slash
      const isTrailingSlashEndpoint = trailingSlashEndpoints.some(endpoint =>
        config.url === endpoint || (config.url?.startsWith(endpoint + '?'))
      )

      // Dynamic endpoints that shouldn't have trailing slashes
      const isDynamicNoSlashEndpoint =
        // All admin operations
        config.url?.includes('/admin/') ||
        // All superadmin operations (mirrors admin)
        config.url?.includes('/superadmin/') ||
        // All course operations with IDs (excluding /courses/ exact match)
        (config.url?.includes('/courses/') && config.url !== '/courses/') ||
        // All certificate operations with IDs
        (config.url?.includes('/certificates/') && config.url !== '/certificates') ||
        // All blog operations with slugs (excluding /blog/ exact match)
        (config.url?.includes('/blog/') && config.url !== '/blog/') ||
        // All user operations (including nested)
        config.url?.includes('/users/') ||
        // All instructor operations
        config.url?.includes('/instructor/') ||
        // All auth operations
        config.url?.includes('/auth/') ||
        // All upload operations
        config.url?.includes('/upload/') ||
        // Resource ID patterns: /resource/123 or /resource/123/action
        config.url?.match(/^\/\w+\/\d+($|\/\w+$)/) ||
        // Hyphenated resource patterns: /chunked-upload/init
        config.url?.match(/^\/\w+-\w+\/\w+/)

      // Explicit check for admin endpoints that should never have trailing slashes
      const isAdminNoSlashEndpoint = [
        '/admin/stats',
        '/admin/courses',
        '/admin/users',
        '/admin/revenue',
        '/admin/instructor-applications',
        '/admin/enrollments',
        '/admin/categories',
        '/admin/tags',
        '/admin/certificates',
        '/admin/orders'
      ].some(endpoint => config.url === endpoint)

      if (isTrailingSlashEndpoint) {
        // Always add trailing slash for these endpoints
        // Check if URL has query parameters
        const hasQueryParams = config.url.includes('?')
        if (hasQueryParams) {
          // Insert trailing slash before query parameters
          const [basePath, queryString] = config.url.split('?')
          config.url = basePath + '/?' + queryString
        } else {
          // Simply add trailing slash
          config.url = config.url + '/'
        }
      } else if (!isStaticNoSlashEndpoint && !isDynamicNoSlashEndpoint && !isAdminNoSlashEndpoint) {
        // Check if URL has query parameters
        const hasQueryParams = config.url.includes('?')
        if (hasQueryParams) {
          // Insert trailing slash before query parameters
          const [basePath, queryString] = config.url.split('?')
          config.url = basePath + '/?' + queryString
        } else {
          // Simply add trailing slash
          config.url = config.url + '/'
        }
      }
    }

    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Production-grade response interceptor with enhanced error handling
api.interceptors.response.use(
  (response: AxiosResponse) => {
    // Log successful responses in development
    if (import.meta.env.DEV && import.meta.env.VITE_DEBUG_API === 'true') {
      console.log(`✅ API Success: ${response.config.method?.toUpperCase()} ${response.config.url}`, {
        status: response.status,
        data: response.data
      })
    }
    return response
  },
  async (error: AxiosError) => {
    const originalRequest = error.config as any

    // Production-grade error logging
    const errorInfo = {
      url: originalRequest?.url,
      method: originalRequest?.method?.toUpperCase(),
      status: error.response?.status,
      statusText: error.response?.statusText,
      message: error.message,
      timestamp: new Date().toISOString(),
      userAgent: navigator.userAgent,
      pathname: window.location.pathname
    }

    // Only attempt token refresh for non-auth endpoints
    // Skip token refresh for auth endpoints to prevent infinite loops
    const isAuthEndpoint = originalRequest.url?.includes('/auth/login') ||
      originalRequest.url?.includes('/auth/refresh') ||
      originalRequest.url?.includes('/auth/register') ||
      originalRequest.url?.includes('/auth/google')

    // A 401 on a normal endpoint is expected when the access token has just
    // expired — the interceptor below silently refreshes and retries it. Don't
    // scare the console with a red "API Error" for those; only log 401s we
    // won't recover from (auth endpoints / already-retried). Genuine refresh
    // failures are still logged in the catch below.
    const isRecoverable401 =
      error.response?.status === 401 && !isAuthEndpoint && !originalRequest._retry

    // The boot-time session probe (initializeAuth) POSTs /auth/refresh before
    // we know whether a token/cookie exists; for anonymous visitors that call
    // is EXPECTED to 401 and is handled silently in the store. Don't dump it
    // to the console as a "Production API Error" on every page load.
    const isSilentRefreshProbe =
      error.response?.status === 401 &&
      originalRequest?.url?.includes('/auth/refresh')

    // Log errors in development and production (with different levels)
    if (!isRecoverable401 && !isSilentRefreshProbe) {
      if (import.meta.env.DEV) {
        console.error('❌ API Error:', errorInfo)
        console.error('Full error:', error)
      } else {
        // Production logging - send to monitoring service (can be integrated with Sentry, etc.)
        console.error('Production API Error:', JSON.stringify(errorInfo))

        // Optional: Send to error monitoring service
        // if (window.Sentry) {
        //   window.Sentry.captureException(error, { extra: errorInfo })
        // }
      }
    }

    if (error.response?.status === 401) {
      // Public screens may offer sign-in-only content. Let the page explain
      // that state instead of turning a visitor's Back action into a login loop.
      const session = useAuthStore.getState()
      if (!session.isAuthenticated && !session.accessToken) return Promise.reject(error)
      // For auth endpoints, just reject without retry
      if (isAuthEndpoint || originalRequest._retry) {
        return Promise.reject(error)
      }

      // If we're inside an admin "View as Instructor" session, a 401
      // almost certainly means the 30-minute impersonation token expired.
      // Impersonation tokens CANNOT be refreshed, so we silently restore
      // the admin session from sessionStorage and bounce the user back to
      // their console with a toast — no login redirect. The destination
      // depends on the actor role: superadmin → /superadmin/*, admin →
      // /admin/*. We look at the *restored* user to decide, because while
      // impersonating the store user is the target.
      if (isImpersonating()) {
        try {
          const restored = useAuthStore.getState().endImpersonation()
          if (restored) {
            const restoredRole = useAuthStore.getState().user?.role
            const backHome =
              restoredRole === 'superadmin' ? '/superadmin/dashboard' : '/admin/instructors'
            toast('Impersonation expired — back on admin session', { icon: 'ℹ️' })
            if (window.location.pathname !== backHome) {
              window.location.href = backHome
            }
            return Promise.reject(error)
          }
        } catch (restoreErr) {
          console.error('Failed to restore admin session after 401:', restoreErr)
        }
      }

      // For other endpoints, try to refresh token
      originalRequest._retry = true

      try {
        // Try to refresh token
        await useAuthStore.getState().refreshAccessToken()

        // Retry original request with new token
        const token = useAuthStore.getState().accessToken
        if (token) {
          originalRequest.headers.Authorization = `Bearer ${token}`
          return api(originalRequest)
        }
      } catch (refreshError) {
        // Refresh failed, logout user
        console.error('Token refresh failed:', refreshError)
        useAuthStore.getState().logout()

        // Redirect to login page
        if (window.location.pathname !== '/login') {
          window.location.href = '/login'
        }

        return Promise.reject(refreshError)
      }
    }

    // Handle network errors
    if (!error.response) {
      const networkError = {
        ...errorInfo,
        type: 'NETWORK_ERROR',
        message: 'Network connection failed. Please check your internet connection.'
      }

      if (import.meta.env.DEV) {
        console.error('Network Error:', networkError)
      }

      return Promise.reject({
        ...error,
        message: 'Network connection failed. Please check your internet connection.',
        type: 'NETWORK_ERROR'
      })
    }

    return Promise.reject(error)
  }
)

// Helper function to handle API errors
export const handleApiError = (error: any) => {
  if (error.response) {
    // Server responded with error status
    const message = error.response.data?.message || error.response.statusText
    return new Error(message)
  } else if (error.request) {
    // Request made but no response received
    return new Error('Network error. Please check your connection.')
  } else {
    // Something else happened
    return new Error('An unexpected error occurred.')
  }
}

// API response wrapper
export const apiRequest = async <T>(
  request: Promise<AxiosResponse<any>>
): Promise<T> => {
  let response: AxiosResponse<any>
  try {
    response = await request
  } catch (error) {
    throw handleApiError(error)
  }

  // Handle both {success, data} pattern and direct data responses
  if (response.data && typeof response.data === 'object' && 'success' in response.data) {
    if (response.data.success) {
      return response.data.data
    }
    // A 200 with {success: false} is a failed request — surface it as an
    // error instead of returning the envelope to callers expecting data.
    // (Thrown outside the catch above so the body message survives.)
    throw new Error(response.data.message || 'Request failed')
  }
  return response.data
}

export default api
