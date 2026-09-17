/**
 * Centralised role → landing-route logic.
 *
 * Every role check in the app keys off `user.role`, and the value can drift
 * (casing/whitespace from imports or manual SQL). Normalising in one place
 * keeps the post-login redirect, the header "Dashboard" link, and the route
 * guards in agreement so an admin always reaches the admin dashboard.
 */

export type AppRole = string | null | undefined

/** Lower-case + trim a role string for safe comparison. */
export const normalizeRole = (role: AppRole): string =>
  (role ?? '').toString().trim().toLowerCase()

/** Role → its dashboard landing route. */
const ROLE_HOME: Record<string, string> = {
  superadmin: '/superadmin/dashboard',
  admin: '/admin/dashboard',
  instructor: '/instructor/dashboard',
  company: '/company/dashboard',
  company_manager: '/company/dashboard',
  spoc: '/spoc/dashboard',
}

/**
 * Dashboard landing path for a role. Students — and any unknown role — land on
 * the student dashboard (`/dashboard`).
 */
export const roleHomePath = (role: AppRole): string =>
  ROLE_HOME[normalizeRole(role)] ?? '/dashboard'

/** True for roles that have their own dashboard (i.e. NOT a student). */
export const isNonStudentRole = (role: AppRole): boolean =>
  normalizeRole(role) in ROLE_HOME
