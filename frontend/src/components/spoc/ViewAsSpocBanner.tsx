/**
 * Banner component shown when admin is viewing as SPOC.
 * Displays info about the impersonated SPOC and provides an exit button.
 */
import React,{ useEffect,useState } from 'react'
import { LogOut,GraduationCap } from 'lucide-react'
import { useAuthStore } from '@/store/auth'
import { adminApi } from '@/api/admin'
import toast from 'react-hot-toast'

export const ViewAsSpocBanner: React.FC = () => {
  const getImpersonationType = useAuthStore((s) => s.getImpersonationType)
  const getTargetName = useAuthStore((s) => s.getTargetName)
  const endImpersonation = useAuthStore((s) => s.endImpersonation)

  const [impersonationType, setImpersonationType] = useState<'instructor' | 'company' | 'student' | 'spoc' | 'admin' | null>(null)
  const [targetName, setTargetName] = useState<string | null>(null)
  const [adminEmail, setAdminEmail] = useState<string | null>(null)
  const [exiting, setExiting] = useState(false)

  useEffect(() => {
    setImpersonationType(getImpersonationType())
    setTargetName(getTargetName())

    // Get admin email from sessionStorage (stashed during impersonation)
    try {
      const adminUserRaw = sessionStorage.getItem('sasha_admin_user')
      if (adminUserRaw) {
        const adminUser = JSON.parse(adminUserRaw)
        setAdminEmail(adminUser.user_email || adminUser.email || 'admin')
      }
    } catch {
      setAdminEmail('admin')
    }
  }, [getImpersonationType, getTargetName])

  const handleExit = async () => {
    if (exiting) return
    setExiting(true)
    try {
      // Close the audit log on the server
      try {
        await adminApi.endImpersonation()
      } catch (e) {
        console.warn('end-impersonation API call failed, continuing:', e)
      }

      // Restore admin session locally
      const restored = endImpersonation()
      if (restored) {
        toast.success('Exited impersonation — back on admin session')
      } else {
        toast.error('No admin session to restore — please sign in again')
      }
      window.location.href = '/admin/spocs'
    } finally {
      setExiting(false)
    }
  }

  if (impersonationType !== 'spoc' || !targetName) {
    return null
  }

  return (
    <div className="bg-indigo-50 border-b border-indigo-200">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3 text-sm">
          <GraduationCap className="w-4 h-4 text-indigo-600" />
          <span className="font-semibold text-indigo-900">Viewing as SPOC:</span>
          <span className="text-indigo-700 font-medium">{targetName}</span>
          <span className="text-indigo-300">|</span>
          <span className="text-xs text-indigo-500">Admin: {adminEmail}</span>
        </div>
        <button
          onClick={handleExit}
          disabled={exiting}
          className="flex items-center gap-1.5 px-3 py-1.5 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold rounded-md transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <LogOut className="w-3.5 h-3.5" />
          {exiting ? 'Exiting…' : 'Exit to Admin'}
        </button>
      </div>
    </div>
  )
}
