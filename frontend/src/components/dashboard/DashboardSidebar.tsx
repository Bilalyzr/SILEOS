/**
 * Unified light side rail used across all role dashboards.
 *
 * Style: Notion / GitHub-esque — white surface, navy ink, orange accent
 * on active. Animations:
 *   - Sliding orange "active" indicator (layoutId animation between items)
 *   - Stagger mount of nav items
 *   - Logo subtle bounce on mount
 *   - Submenu accordion (animated height/opacity)
 *   - Collapse/expand sidebar width transition with label fade
 *   - User menu pop-up
 */
import * as React from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { motion, AnimatePresence, type Variants } from 'framer-motion'
import {
  ChevronRight, ChevronDown, LogOut, Settings, User as UserIcon, MessageCircle,
  PanelLeftClose, PanelLeftOpen, ExternalLink, type LucideIcon,
} from 'lucide-react'
import { useAuthStore } from '@/store/auth'
import { useNavBadges } from '@/hooks/useNavBadges'
import { getAvatarUrl } from '@/utils/media'

const SASHA_LOGO_URL = '/brand/sasha-logo-small.png'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type SidebarItemKind = 'link' | 'group'

export interface SidebarLink {
  kind?: 'link'
  to: string
  label: string
  icon: LucideIcon
  /** match path prefix even if exact `to` differs (e.g. /admin/courses/*). */
  matchPrefix?: string
  exact?: boolean
  badge?: number | string
}

export interface SidebarGroup {
  kind: 'group'
  label: string
  icon: LucideIcon
  children: SidebarLink[]
}

export type SidebarItem = SidebarLink | SidebarGroup

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

// ---------------------------------------------------------------------------
// Animation variants
// ---------------------------------------------------------------------------

const navStagger: Variants = {
  hidden: {},
  show: { transition: { staggerChildren: 0.04, delayChildren: 0.1 } },
}
const navItem: Variants = {
  hidden: { opacity: 0, x: -16 },
  show:   { opacity: 1, x: 0, transition: { duration: 0.35, ease: [0.16, 1, 0.3, 1] } },
}
const submenu: Variants = {
  collapsed: { opacity: 0 },
  open:      { opacity: 1, transition: { duration: 0.16, ease: [0.2, 0.7, 0.3, 1] } },
}

// ---------------------------------------------------------------------------
// Hook for active matching
// ---------------------------------------------------------------------------

function isActive(item: SidebarLink, pathname: string): boolean {
  if (item.exact) return pathname === item.to
  if (item.to === '/dashboard') return pathname === item.to
  if (item.matchPrefix) return pathname === item.matchPrefix || pathname.startsWith(item.matchPrefix + '/')
  return pathname === item.to || pathname.startsWith(item.to + '/')
}

// ---------------------------------------------------------------------------
// Sidebar
// ---------------------------------------------------------------------------

export interface DashboardSidebarProps {
  items: SidebarItem[]
  /** Override the default role read from auth. */
  role?: Role
  /** Override the dashboard "home" link target. Defaults per-role. */
  homeTo?: string
  /** Width when expanded. Default 240. */
  width?: number
  /** Width when collapsed. Default 72. */
  collapsedWidth?: number
  /** Initial collapsed state — useful if a parent persists it. */
  initialCollapsed?: boolean
  /** When provided, sidebar is fully controlled. */
  collapsed?: boolean
  onCollapsedChange?: (v: boolean) => void
  /** Mobile: slide the rail off-canvas (drawer closed) when true. */
  offCanvas?: boolean
  /** Hide the desktop collapse toggle (e.g. on mobile where the rail is a drawer). */
  showCollapseToggle?: boolean
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

export const DashboardSidebar: React.FC<DashboardSidebarProps> = ({
  items,
  role: roleOverride,
  homeTo,
  width = 224,
  collapsedWidth = 72,
  initialCollapsed = false,
  collapsed: collapsedProp,
  onCollapsedChange,
  offCanvas = false,
  showCollapseToggle = true,
  className = '',
}) => {
  const { pathname } = useLocation()
  const navigate = useNavigate()
  const user = useAuthStore((s) => s.user)
  const profile = useAuthStore((s) => s.profile)
  const logout = useAuthStore((s) => s.logout)
  const role = (roleOverride || user?.role || 'student') as Role
  const dashTo = homeTo ?? DEFAULT_HOME[role] ?? '/'
  const navItems = useNavBadges(role, items)   // R2: live review-queue count

  const [internalCollapsed, setInternalCollapsed] = React.useState(initialCollapsed)
  const collapsed = collapsedProp !== undefined ? collapsedProp : internalCollapsed
  const setCollapsed = (v: boolean) => {
    if (onCollapsedChange) onCollapsedChange(v)
    if (collapsedProp === undefined) setInternalCollapsed(v)
  }
  const [openGroups, setOpenGroups] = React.useState<Record<string, boolean>>({})
  const [menuOpen, setMenuOpen] = React.useState(false)
  const menuRef = React.useRef<HTMLDivElement>(null)
  const getImpersonationType = useAuthStore((s) => s.getImpersonationType)
  const getTargetName = useAuthStore((s) => s.getTargetName)

  // Check if viewing as SPOC using auth store
  const isSpocView = getImpersonationType() === 'spoc'

  React.useEffect(() => {
    if (!menuOpen) return
    const onClick = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) setMenuOpen(false)
    }
    document.addEventListener('mousedown', onClick)
    return () => document.removeEventListener('mousedown', onClick)
  }, [menuOpen])

  // Auto-expand groups whose children are active
  React.useEffect(() => {
    setOpenGroups((prev) => {
      const next = { ...prev }
      for (const item of items) {
        if (item.kind === 'group' && item.children.some(c => isActive(c, pathname))) {
          next[item.label] = true
        }
      }
      return next
    })
  }, [pathname, items])

  // Use SPOC data if viewing as SPOC, otherwise use logged-in user data
  const displayName = isSpocView ? getTargetName() || `${profile?.first_name || ''} ${profile?.last_name || ''}`.trim()
                      : `${profile?.first_name || ''} ${profile?.last_name || ''}`.trim()
                      || user?.display_name || user?.email || 'You'
  const displayEmail = user?.email || ''

  const fullName = displayName
  const initial = (fullName[0] || 'U').toUpperCase()
  // profile.photo may be null, check profile.profile_photo or user.profile.profile_photo
  const avatarUrl = getAvatarUrl(profile || user?.profile || {})

  const handleLogout = () => {
    logout()
    navigate('/login', { replace: true })
  }

  return (
    <motion.aside
      id="workspace-sidebar"
      aria-hidden={offCanvas || undefined}
      initial={false}
      style={{ width: collapsed ? collapsedWidth : width, visibility: offCanvas ? 'hidden' : 'visible' }}
      className={`rd-sidebar fixed top-0 left-0 h-screen bg-white/80 backdrop-blur-xl border-r border-orange-100/80 z-40 flex flex-col shadow-[2px_0_24px_rgba(8,23,58,0.04)] transition-transform duration-300 ${offCanvas ? '-translate-x-full' : 'translate-x-0'} ${className}`}
    >
      {/* Brand */}
      <div className="h-16 flex items-center justify-between px-3 border-b border-slate-100 flex-shrink-0">
        <Link to={dashTo} className="flex items-center gap-2.5 min-w-0 group">
          <motion.img
            initial={{ rotate: -8, scale: 0.85, opacity: 0 }}
            animate={{ rotate: 0, scale: 1, opacity: 1 }}
            transition={{ type: 'spring', stiffness: 220, damping: 14, delay: 0.05 }}
            whileHover={{ rotate: [0, -6, 6, 0], transition: { duration: 0.5 } }}
            src={SASHA_LOGO_URL}
            alt="SashaInfinity"
            className="h-9 w-9 object-contain flex-shrink-0"
          />
          <AnimatePresence initial={false}>
            {!collapsed && (
              <motion.span
                key="brand-text"
                initial={{ opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -8 }}
                transition={{ duration: 0.18 }}
                className="font-bold text-secondary-900 tracking-tight whitespace-nowrap"
              >
                Sasha<span className="text-orange-500">Infinity</span>
              </motion.span>
            )}
          </AnimatePresence>
        </Link>
        {!collapsed && showCollapseToggle && (
          <button
            onClick={() => setCollapsed(true)}
            className="p-1.5 rounded-md text-slate-400 hover:text-secondary-700 hover:bg-slate-100 transition"
            title="Collapse sidebar"
            aria-label="Collapse sidebar"
          >
            <PanelLeftClose className="w-4 h-4" />
          </button>
        )}
      </div>

      {/* Role chip */}
      <AnimatePresence initial={false}>
        {!collapsed && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.18 }}
            className="overflow-hidden"
          >
            <div className="px-4 py-3">
              <span className={`inline-flex items-center gap-1 text-[10px] font-bold uppercase tracking-wider px-2.5 py-1 rounded-full ring-2 ${ROLE_TONES[role]}`}>
                {ROLE_LABELS[role]} workspace
              </span>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Nav */}
      <motion.nav
        variants={navStagger}
        initial="hidden"
        animate="show"
        className="flex-1 overflow-y-auto px-2 py-2 space-y-0.5"
      >
        {navItems.map((item, idx) => (
          <motion.div key={item.kind === 'group' ? `g-${item.label}` : `l-${item.to}-${idx}`} variants={navItem}>
            {item.kind === 'group' ? (
              <SidebarGroupNode
                group={item}
                pathname={pathname}
                collapsed={collapsed}
                isOpen={!!openGroups[item.label]}
                onToggle={() => {
                  if (collapsed) setCollapsed(false)
                  setOpenGroups((p) => ({ ...p, [item.label]: collapsed || !p[item.label] }))
                }}
              />
            ) : (
              <SidebarLinkNode link={item} pathname={pathname} collapsed={collapsed} />
            )}
          </motion.div>
        ))}
      </motion.nav>

      {/* Expand button when collapsed */}
      {collapsed && (
        <button
          onClick={() => setCollapsed(false)}
          className="mx-auto mb-2 p-2 rounded-md text-slate-400 hover:text-secondary-700 hover:bg-slate-100 transition"
          title="Expand sidebar"
          aria-label="Expand sidebar"
        >
          <PanelLeftOpen className="w-4 h-4" />
        </button>
      )}

      {/* User card / menu */}
      <div className="border-t border-slate-100 p-2 flex-shrink-0" ref={menuRef}>
        <button
          onClick={() => setMenuOpen((v) => !v)}
          className={`w-full flex items-center gap-2.5 p-2 rounded-lg hover:bg-slate-50 transition ${collapsed ? 'justify-center' : ''}`}
        >
          <span className="w-8 h-8 rounded-full bg-gradient-to-br from-orange-400 to-orange-600 text-white text-sm font-semibold flex items-center justify-center overflow-hidden ring-2 ring-orange-100 flex-shrink-0">
            {avatarUrl
              ? <img src={avatarUrl} alt={fullName} className="w-full h-full object-cover" />
              : initial}
          </span>
          <AnimatePresence initial={false}>
            {!collapsed && (
              <motion.span
                initial={{ opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -8 }}
                transition={{ duration: 0.15 }}
                className="flex-1 min-w-0 text-left"
              >
                <span className="block text-sm font-semibold text-secondary-900 truncate">{fullName.split(' ')[0]}</span>
                <span className="block text-xs text-slate-500 truncate">{displayEmail}</span>
              </motion.span>
            )}
          </AnimatePresence>
          {!collapsed && <ChevronDown className={`w-4 h-4 text-slate-400 transition flex-shrink-0 ${menuOpen ? 'rotate-180' : ''}`} />}
        </button>

        <AnimatePresence>
          {menuOpen && (
            <motion.div
              initial={{ opacity: 0, y: 8, scale: 0.96 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: 8, scale: 0.96 }}
              transition={{ duration: 0.15 }}
              className="absolute bottom-16 left-2 right-2 mb-1 dash-card p-1 z-50"
              style={{ width: collapsed ? 220 : undefined }}
            >
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
                className="flex items-center gap-2 px-3 py-2 text-sm text-secondary-800 rounded-md hover:bg-slate-50"
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
    </motion.aside>
  )
}

// ---------------------------------------------------------------------------
// Single link node — animated active pill via layoutId
// ---------------------------------------------------------------------------

const SidebarLinkNode: React.FC<{
  link: SidebarLink
  pathname: string
  collapsed: boolean
  /** When inside a group submenu, indents and trims styling. */
  inGroup?: boolean
}> = ({ link, pathname, collapsed, inGroup = false }) => {
  const active = isActive(link, pathname)
  const Icon = link.icon
  return (
    <Link
      to={link.to}
      aria-current={active ? 'page' : undefined}
      className={`relative group flex items-center gap-3 ${inGroup ? 'pl-9 pr-3' : 'px-3'} py-2 rounded-lg text-sm transition ${
        active
          ? 'text-orange-700 font-semibold'
          : 'text-secondary-800 hover:text-orange-700 hover:bg-orange-50/50'
      } ${collapsed && !inGroup ? 'justify-center' : ''}`}
      title={collapsed ? link.label : undefined}
    >
      <Icon className={`w-4 h-4 flex-shrink-0 relative z-10 ${active ? 'text-orange-600' : 'text-slate-500 group-hover:text-orange-600 transition'}`} />
      <AnimatePresence initial={false}>
        {(!collapsed || inGroup) && (
          <motion.span
            initial={{ opacity: 0, x: -6 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -6 }}
            transition={{ duration: 0.15 }}
            className="relative z-10 flex-1 truncate"
          >
            {link.label}
          </motion.span>
        )}
      </AnimatePresence>
      {link.badge != null && (!collapsed || inGroup) && (
        <span className="relative z-10 text-[10px] font-bold uppercase tracking-wider bg-orange-500 text-white px-1.5 py-0.5 rounded-full">
          {link.badge}
        </span>
      )}
    </Link>
  )
}

// ---------------------------------------------------------------------------
// Group node — collapsible submenu
// ---------------------------------------------------------------------------

const SidebarGroupNode: React.FC<{
  group: SidebarGroup
  pathname: string
  collapsed: boolean
  isOpen: boolean
  onToggle: () => void
}> = ({ group, pathname, collapsed, isOpen, onToggle }) => {
  const Icon = group.icon
  const anyChildActive = group.children.some((c) => isActive(c, pathname))
  return (
    <div>
      <button
        onClick={onToggle}
        aria-label={group.label}
        aria-expanded={isOpen && !collapsed}
        className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition ${
          anyChildActive
            ? 'text-orange-700 font-semibold'
            : 'text-secondary-800 hover:text-orange-700 hover:bg-orange-50/50'
        } ${collapsed ? 'justify-center' : ''}`}
        title={collapsed ? group.label : undefined}
      >
        <Icon className={`w-4 h-4 flex-shrink-0 ${anyChildActive ? 'text-orange-600' : 'text-slate-500'}`} />
        <AnimatePresence initial={false}>
          {!collapsed && (
            <motion.span
              initial={{ opacity: 0, x: -6 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -6 }}
              transition={{ duration: 0.15 }}
              className="flex-1 text-left whitespace-normal leading-5"
            >
              {group.label}
            </motion.span>
          )}
        </AnimatePresence>
        {!collapsed && (
          <ChevronRight className={`w-3.5 h-3.5 text-slate-400 transition ${isOpen ? 'rotate-90' : ''}`} />
        )}
      </button>
      <AnimatePresence initial={false}>
        {isOpen && !collapsed && (
          <motion.div
            variants={submenu}
            initial="collapsed"
            animate="open"
            exit="collapsed"
            className="overflow-hidden mt-0.5 space-y-0.5"
          >
            {group.children.map((c) => (
              <SidebarLinkNode key={c.to} link={c} pathname={pathname} collapsed={false} inGroup />
            ))}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

export default DashboardSidebar
