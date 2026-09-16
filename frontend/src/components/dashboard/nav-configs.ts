/**
 * Per-role sidebar navigation configurations.
 * Each role gets a tailored set of links (and groups).
 */
import {
  LayoutDashboard, BookOpen, Award, Users, Briefcase, Heart, ShoppingCart,
  CreditCard, Settings, BarChart3, Tag, FolderOpen, Inbox,
  Building2, GraduationCap, PenSquare, MessageSquare, MessageCircle,
  UserCog, FileText, Send, CheckCircle,
  ShieldCheck, ScrollText, Gauge, Trophy, Layers, Package, Receipt, Video,
  ClipboardList, Gamepad2, Puzzle, Library, BookMarked, History,
  FlaskConical, Box, Brain } from 'lucide-react'
import type { SidebarItem } from './DashboardSidebar'

export const ACCOUNT_NAV: SidebarItem[] = [
  { kind: 'link', to: '/communication-preferences', label: 'Communication preferences', icon: MessageCircle },
  { kind: 'link', to: '/profile', label: 'Profile', icon: Settings },
]

export const STUDENT_NAV: SidebarItem[] = [
  { to: '/exam-papers', label: 'Practice papers', icon: FileText },
  { kind: 'link', to: '/labs', label: 'Learning labs', icon: FlaskConical },
  { kind: 'link', to: '/dashboard',         label: 'Dashboard',       icon: LayoutDashboard, matchPrefix: '/dashboard' },
  { kind: 'group', label: 'Learning', icon: BookOpen, children: [
    { kind: 'link', to: '/my-courses',        label: 'My courses',      icon: BookOpen },
    { kind: 'link', to: '/my-plan', label: 'My Learning Plan', icon: Brain, matchPrefix: '/my-plan' },
    { kind: 'link', to: '/student/live-classes', label: 'Live classes', icon: Video, matchPrefix: '/student/live-classes' },
    { kind: 'link', to: '/my-library',       label: 'My Library',    icon: Library },
  ]},
  { kind: 'group', label: 'Progress', icon: BarChart3, children: [
    { kind: 'link', to: '/my-grades',         label: 'My Grades',     icon: GraduationCap },
    { kind: 'link', to: '/my-mastery',        label: 'My Mastery',    icon: Brain, matchPrefix: '/my-mastery' },
    { kind: 'link', to: '/dashboard/analytics', label: 'Analytics',     icon: BarChart3, matchPrefix: '/dashboard/analytics' },
    { kind: 'link', to: '/leaderboard',       label: 'Leaderboard',     icon: Trophy, matchPrefix: '/leaderboard' },
  ]},
  { kind: 'group', label: 'Explore', icon: GraduationCap, children: [
    { kind: 'link', to: '/courses',           label: 'Browse',          icon: GraduationCap, matchPrefix: '/courses' },
    { kind: 'link', to: '/library',           label: 'eBooks',         icon: BookMarked, matchPrefix: '/library' },
    { kind: 'link', to: '/wishlist',          label: 'Wishlist',        icon: Heart },
    { kind: 'link', to: '/cart',              label: 'Cart',            icon: ShoppingCart },
  ]},
  { kind: 'group', label: 'Career & Community', icon: Briefcase, children: [
    { kind: 'link', to: '/dashboard/my-internships', label: 'Internships', icon: Briefcase, matchPrefix: '/dashboard/my-internships' },
    { kind: 'link', to: '/dashboard/internship-inbox', label: 'Internship Inbox',  icon: Inbox },
    { kind: 'link', to: '/dashboard/messages', label: 'Messages',      icon: MessageSquare },
    { kind: 'link', to: '/student/blog/create', label: 'Write Blog',    icon: PenSquare, matchPrefix: '/student/blog' },
  ]},
  { kind: 'link', to: '/communication-preferences', label: 'Communication preferences', icon: MessageCircle },
  { kind: 'link', to: '/profile',           label: 'Profile',         icon: Settings },
]

export const PARENT_NAV: SidebarItem[] = [
  { kind: 'link', to: '/parent', label: 'My Children', icon: Heart },
  { kind: 'link', to: '/communication-preferences', label: 'Communication preferences', icon: MessageCircle },
  { kind: 'link', to: '/profile', label: 'Profile', icon: Settings },
]

export const INSTRUCTOR_NAV: SidebarItem[] = [
  { kind: 'link', to: '/instructor/dashboard',   label: 'Dashboard',     icon: LayoutDashboard },
  { kind: 'group', label: 'Teaching', icon: Video, children: [
    { kind: 'link', to: '/instructor/courses',     label: 'My courses',    icon: BookOpen, matchPrefix: '/instructor/courses' },
    { kind: 'link', to: '/instructor/live-classes', label: 'Live classes', icon: Video, matchPrefix: '/instructor/live-classes' },
    { kind: 'link', to: '/instructor/past-classes', label: 'Past classes', icon: History, matchPrefix: '/instructor/past-classes' },
  ]},
  { kind: 'group', label: 'Content Studio', icon: Layers, children: [
    { to: '/instructor/lab-studio', label: 'Lab Studio', icon: FlaskConical },
    { to: '/instructor/course-packages', label: 'Course Upload & Backup', icon: Package },
    { to: '/instructor/recording-lessons', label: 'Recording Lessons', icon: Video },
    { kind: 'link', to: '/instructor/ebooks',      label: 'My Ebooks',     icon: BookMarked, matchPrefix: '/instructor/ebooks' },
    { kind: 'link', to: '/instructor/games',       label: 'Games',         icon: Gamepad2, matchPrefix: '/instructor/games' },
    { kind: 'link', to: '/instructor/three-d-tasks', label: '3D Tasks',    icon: Box, matchPrefix: '/instructor/three-d-tasks' },
    { kind: 'link', to: '/instructor/h5p',         label: 'H5P Library',   icon: Puzzle, matchPrefix: '/instructor/h5p' },
    { kind: 'link', to: '/instructor/blog',        label: 'Blog',          icon: PenSquare, matchPrefix: '/instructor/blog' },
  ]},
  { kind: 'group', label: 'Assessment & Support', icon: ClipboardList, children: [
    { to: '/exam-papers', label: 'Paper generator', icon: FileText },
    { kind: 'link', to: '/instructor/assessment-studio', label: 'Assessment Studio', icon: Brain, matchPrefix: '/instructor/assessment-studio' },
    { kind: 'link', to: '/instructor/grading',     label: 'Grading',       icon: ClipboardList, matchPrefix: '/instructor/grading' },
    { kind: 'link', to: '/instructor/review-queue', label: 'Review Queue', icon: ClipboardList, matchPrefix: '/instructor/review-queue' },
    { kind: 'link', to: '/instructor/interventions', label: 'Interventions', icon: Brain, matchPrefix: '/instructor/interventions' },
  ]},
  { kind: 'group', label: 'Learners & Insights', icon: Users, children: [
    { kind: 'link', to: '/instructor/students',    label: 'Students',      icon: Users },
    { kind: 'link', to: '/instructor/insights',     label: 'Insights',    icon: BarChart3, matchPrefix: '/instructor/insights' },
    { kind: 'link', to: '/instructor/analytics',   label: 'Analytics',     icon: BarChart3 },
    { kind: 'link', to: '/instructor/certificate-designer', label: 'Certificates', icon: Award, matchPrefix: '/instructor/certificate-designer' },
  ]},
  { kind: 'link', to: '/communication-preferences', label: 'Communication preferences', icon: MessageCircle },
  { kind: 'link', to: '/profile',                label: 'Profile',       icon: Settings },
]

export const SPOC_NAV: SidebarItem[] = [
  { kind: 'link', to: '/spoc/dashboard', label: 'Dashboard',     icon: LayoutDashboard },
  { kind: 'link', to: '/spoc/dashboard', label: 'My internships', icon: Briefcase, matchPrefix: '/spoc' },
  { kind: 'link', to: '/spoc/blog',      label: 'Blog',          icon: PenSquare, matchPrefix: '/spoc/blog' },
  { kind: 'link', to: '/communication-preferences', label: 'Communication preferences', icon: MessageCircle },
  { kind: 'link', to: '/profile',        label: 'Profile',        icon: Settings },
]

// NOTE — Company nav lives inside the company dashboard itself (the
// existing in-page tab nav). That tab nav now uses the same sidebar
// component, configured separately in dashboard.tsx.

export const ADMIN_NAV: SidebarItem[] = [
  { kind: 'link', to: '/admin/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/admin/operations', label: 'Operations Center', icon: Gauge },
  { kind: 'group', label: 'Learning & Content', icon: BookOpen, children: [
    { to: '/exam-papers', label: 'Paper generator', icon: FileText },
    { to: '/admin/lab-studio', label: 'Lab Studio', icon: FlaskConical },
    { to: '/admin/course-packages', label: 'Course Upload & Backup', icon: Package },
    { to: '/admin/courses',            label: 'All courses',   icon: BookOpen, matchPrefix: '/admin/courses' },
    { to: '/admin/courses/categories', label: 'Categories',    icon: FolderOpen },
    { to: '/admin/courses/tags',       label: 'Tags',          icon: Tag },
    { to: '/admin/course-reviews',     label: 'Reviews',       icon: MessageSquare },
    { kind: 'link', to: '/admin/content-libraries', label: 'Content Libraries', icon: FlaskConical },
    { kind: 'link', to: '/admin/certificates', label: 'Certificates', icon: Award },
  ]},
  { kind: 'group', label: 'People & Access', icon: Users, children: [
    { kind: 'link', to: '/admin/students',    label: 'Students',    icon: Users },
    { kind: 'link', to: '/admin/instructors', label: 'Instructors', icon: GraduationCap },
    { kind: 'link', to: '/admin/approvals',   label: 'Approvals',   icon: CheckCircle },
    { kind: 'link', to: '/admin/manage',      label: 'Manage',      icon: Settings },
    { kind: 'link', to: '/admin/enrollments', label: 'Enrollments', icon: FolderOpen },
  ]},
  { kind: 'group', label: 'Commerce', icon: CreditCard, children: [
    { to: '/admin/exam-pricing', label: 'Exam paper pricing', icon: Receipt },
    { kind: 'link', to: '/admin/orders',      label: 'Orders',      icon: CreditCard },
    { kind: 'link', to: '/admin/coupons',     label: 'Coupons',     icon: Tag },
    { kind: 'link', to: '/admin/memberships', label: 'Memberships', icon: Layers },
    { kind: 'link', to: '/admin/bundles',     label: 'Bundles',     icon: Package },
    { kind: 'link', to: '/admin/company-invoices', label: 'Invoices', icon: Receipt },
  ]},
  { kind: 'group', label: 'Internships', icon: Briefcase, children: [
    { to: '/admin/internships',          label: 'Listings',  icon: Briefcase, matchPrefix: '/admin/internships' },
    { to: '/admin/internship-requests',  label: 'Requests',  icon: Inbox },
    { to: '/admin/companies',            label: 'Companies', icon: Building2 },
    { to: '/admin/colleges',             label: 'Colleges',  icon: GraduationCap },
    { to: '/admin/spocs',                label: 'SPOCs',     icon: UserCog },
  ]},
  { kind: 'group', label: 'Insights & Community', icon: BarChart3, children: [
    { kind: 'link', to: '/admin/analytics',   label: 'Analytics',   icon: BarChart3 },
    { kind: 'link', to: '/admin/communications', label: 'Communications Center', icon: MessageCircle },
    { kind: 'link', to: '/admin/messages',     label: 'Messages',     icon: Send },
    { kind: 'link', to: '/admin/blogs',        label: 'Blogs',        icon: FileText },
    { kind: 'link', to: '/admin/hall-of-fame',  label: 'Wall of Fame', icon: Trophy },
  ]},
  { kind: 'link', to: '/communication-preferences', label: 'Communication preferences', icon: MessageCircle },
  { kind: 'link', to: '/admin/settings',     label: 'Settings',     icon: Settings },
]

// SuperAdmin nav. SuperAdmin is a supervisory role above admin: its primary
// job is monitoring (the four dashboards) and impersonation audit. It can
// still reach the full admin console via the last link.
export const SUPERADMIN_NAV: SidebarItem[] = [
  { kind: 'link', to: '/superadmin/dashboard',   label: 'Overview',         icon: Gauge,         matchPrefix: '/superadmin/dashboard' },
  { kind: 'link', to: '/superadmin/students',    label: 'Students',         icon: Users,         matchPrefix: '/superadmin/students' },
  { kind: 'link', to: '/superadmin/instructors', label: 'Instructors',      icon: GraduationCap, matchPrefix: '/superadmin/instructors' },
  { kind: 'link', to: '/superadmin/admins',      label: 'Admins',           icon: UserCog,       matchPrefix: '/superadmin/admins' },
  { kind: 'link', to: '/superadmin/audit',       label: 'Impersonation audit', icon: ScrollText, matchPrefix: '/superadmin/audit' },
  { kind: 'link', to: '/admin/communications',   label: 'Communications Center', icon: MessageCircle },
  { kind: 'link', to: '/admin/dashboard',        label: 'Admin console',    icon: ShieldCheck },
  { kind: 'link', to: '/communication-preferences', label: 'Communication preferences', icon: MessageCircle },
  { kind: 'link', to: '/profile',                label: 'Profile',          icon: Settings },
]
