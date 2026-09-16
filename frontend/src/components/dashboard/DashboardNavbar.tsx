/**
 * Unified dashboard top navigation. Replaces the public marketing
 * navbar (PublicHeader) on logged-in dashboard routes — those should
 * feel like a private workspace, not a marketing site.
 *
 * Layout:
 *   [Sasha logo] [role chip]                    [search?] [home] [user-menu]
 */
import * as React from 'react'
import { Link,useNavigate } from 'react-router-dom'
import { motion,AnimatePresence } from 'framer-motion'
import {
Home,LogOut,ChevronDown,Settings,User as UserIcon,ExternalLink,MessageCircle,
} from 'lucide-react'
import { useAuthStore } from '@/store/auth'
import { getAvatarUrl } from '@/utils/media'
import { NotificationBell } from '@/components/notifications/NotificationBell'

const SASHA_LOGO_URL = 'https://res.cloudinary.com/dkjvfskhn/image/upload/v1759753621/cropped-sasha-logo-small_ejpceq.png'

export type Role = 'parent' | 'student' | 'instructor' | 'admin' | 'superadmin' | 'spoc' | 'company' | 'company_manager'

const ROLE_LABELS: Record<Role, string> = {
  parent: 'Parent',
  student: 'Student',
  instructor: 'Instructor',
  admin: 'Admin',
  superadmin: 'SuperAdmin',
  spoc: 'SPOC',
  company: 'Company',
  company_manager: 'Manager',
}

const ROLE_TONES: Record<Role, string> = {
  parent: 'bg-orange-100 text-orange-700 ring-orange-200/40',
  student:         'bg-orange-100 text-orange-700 ring-orange-200/40',
  instructor:      'bg-purple-100 text-purple-700 ring-purple-200/40',
  admin:           'bg-secondary-100 text-secondary-800 ring-secondary-200/40',
  superadmin:      'bg-rose-100 text-rose-700 ring-rose-300/50',
  spoc:            'bg-emerald-100 text-emerald-700 ring-emerald-200/40',
  company:         'bg-sky-100 text-sky-700 ring-sky-200/40',
  company_manager: 'bg-amber-100 text-amber-700 ring-amber-200/40',
}

export interface DashboardNavbarProps {
  /** Override displayed role label (e.g. show "Manager" inside a company workspace). */
  role?: Role
  /** Override the dashboard home link target. Defaults per-role. */
  homeTo?: string
  /** Optional center slot — e.g. tab nav for company dashboard. */
  center?: React.ReactNode
  /** Optional right-side custom content rendered before the user menu. */
  extras?: React.ReactNode
  className?: string
}

const DEFAULT_HOME: Record<Role, string> = {
  parent: '/parent/dashboard',
  student: '/dashboard',
  instructor: '/instructor/dashboard',
  admin: '/admin/dashboard',
  superadmin: '/superadmin/dashboard',
  spoc: '/spoc/dashboard',
  company: '/company/dashboard',
  company_manager: '/company/dashboard',
}

export const DashboardNavbar: React.FC<DashboardNavbarProps> = ({
  role: roleOverride, homeTo, center, extras, className = '',
}) => {
  const user = useAuthStore((s) => s.user)
  const profile = useAuthStore((s) => s.profile)
  const logout = useAuthStore((s) => s.logout)
  const navigate = useNavigate()
  const role = (roleOverride || user?.role || 'student') as Role
  const dashTo = homeTo ?? DEFAULT_HOME[role] ?? '/'

  const getImpersonationType = useAuthStore((s) => s.getImpersonationType)
  const getTargetName = useAuthStore((s) => s.getTargetName)

  // Check if viewing as SPOC using auth store
  const isSpocView = getImpersonationType() === 'spoc'

  // Use SPOC data if viewing as SPOC, otherwise use logged-in user data
  const displayName = isSpocView ? getTargetName() || `${profile?.first_name || ''} ${profile?.last_name || ''}`.trim()
                      : `${profile?.first_name || ''} ${profile?.last_name || ''}`.trim()
                      || user?.display_name || user?.email || 'You'
  const displayEmail = user?.email || ''

  const fullName = displayName
  const initial = (fullName[0] || 'U').toUpperCase()
  const avatarUrl = getAvatarUrl(profile || user?.profile || {})

  const [menuOpen, setMenuOpen] = React.useState(false)
  const menuRef = React.useRef<HTMLDivElement>(null)
  React.useEffect(() => {
    if (!menuOpen) return
    const handler = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) setMenuOpen(false)
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [menuOpen])

  const handleLogout = () => {
    logout()
    navigate('/login', { replace: true })
  }

  return (
    <header className={`sticky top-0 z-30 bg-white/70 backdrop-blur-xl border-b border-orange-100/80 ${className}`}>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center gap-4">
        {/* Brand */}
        <Link to={dashTo} className="flex items-center gap-3 flex-shrink-0 group">
          <img
            src={SASHA_LOGO_URL}
            alt="SashaInfinity"
            className="h-9 w-auto group-hover:scale-105 transition-transform"
          />
          <span className="hidden md:inline-block text-lg font-bold text-secondary-900 tracking-tight">
            Sasha<span className="text-orange-500">Infinity</span>
          </span>
        </Link>

        {/* Role chip */}
        <span className={`hidden sm:inline-flex items-center gap-1 text-[10px] font-bold uppercase tracking-wider px-2.5 py-1 rounded-full ring-2 ${ROLE_TONES[role]}`}>
          {ROLE_LABELS[role]}
        </span>

        {/* Center slot (e.g., tab nav) */}
        {center && <div className="hidden lg:flex flex-1 justify-center">{center}</div>}
        {!center && <div className="flex-1" />}

        {/* Right cluster */}
        <div className="flex items-center gap-2">
          {extras}

          <NotificationBell />

          <Link
            to="/"
            className="hidden md:inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm text-secondary-800 hover:bg-slate-100 transition"
            title="Visit public site"
          >
            <Home className="w-4 h-4" /> Site
          </Link>

          {/* User menu */}
          <div className="relative" ref={menuRef}>
            <button
              onClick={() => setMenuOpen((v) => !v)}
              className="flex items-center gap-2 p-1 pr-2 rounded-full hover:bg-slate-100 transition"
            >
              <span className="w-8 h-8 rounded-full bg-gradient-to-br from-orange-400 to-orange-600 text-white text-sm font-semibold flex items-center justify-center overflow-hidden ring-2 ring-orange-100">
                {avatarUrl
                  ? <img src={avatarUrl} alt={fullName} className="w-full h-full object-cover" />
                  : initial}
              </span>
              <span className="hidden md:inline-block text-sm font-medium text-secondary-900 max-w-[120px] truncate">
                {fullName.split(' ')[0]}
              </span>
              <ChevronDown className={`hidden md:block w-4 h-4 text-slate-400 transition ${menuOpen ? 'rotate-180' : ''}`} />
            </button>

            <AnimatePresence>
              {menuOpen && (
                <motion.div
                  initial={{ opacity: 0, y: -8, scale: 0.96 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  exit={{ opacity: 0, y: -8, scale: 0.96 }}
                  transition={{ duration: 0.15 }}
                  className="absolute right-0 top-full mt-2 w-64 dash-card p-1 z-50"
                >
                  <div className="px-3 py-2 border-b border-slate-100">
                    <div className="font-semibold text-secondary-900 truncate text-sm">{fullName}</div>
                    <div className="text-xs text-slate-500 truncate">{displayEmail}</div>
                    <div className="mt-1.5">
                      <span className={`inline-flex text-[9px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full ${ROLE_TONES[role]}`}>
                        {ROLE_LABELS[role]}
                      </span>
                    </div>
                  </div>
                  <Link
                    to={dashTo}
                    onClick={() => setMenuOpen(false)}
                    className="flex items-center gap-2 px-3 py-2 text-sm text-secondary-800 rounded-md hover:bg-slate-50"
                  >
                    <UserIcon className="w-4 h-4 text-slate-500" /> My dashboard
                  </Link>
                  <Link
                    to={isSpocView ? `/spoc/${user?.id || 0}/profile` : '/profile'}
                    onClick={() => setMenuOpen(false)}
                    className="flex items-center gap-2 px-3 py-2 text-sm text-secondary-800 rounded-md hover:bg-slate-50"
                  >
                    <Settings className="w-4 h-4 text-slate-500" /> Profile settings
                  </Link>
                  <Link
                    to="/communication-preferences"
                    onClick={() => setMenuOpen(false)}
                    className="flex items-center gap-2 px-3 py-2 text-sm text-secondary-800 rounded-md hover:bg-orange-50"
                  >
                    <MessageCircle className="w-4 h-4 text-orange-600" /> Communication preferences
                  </Link>
                  <Link
                    to="/"
                    onClick={() => setMenuOpen(false)}
                    className="md:hidden flex items-center gap-2 px-3 py-2 text-sm text-secondary-800 rounded-md hover:bg-slate-50"
                  >
                    <ExternalLink className="w-4 h-4 text-slate-500" /> Public site
                  </Link>
                  <button
                    onClick={handleLogout}
                    className="w-full flex items-center gap-2 px-3 py-2 text-sm text-rose-600 rounded-md hover:bg-rose-50 mt-1"
                  >
                    <LogOut className="w-4 h-4" /> Log out
                  </button>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>
      </div>
    </header>
  )
}

export default DashboardNavbar
