/**
 * Settings — account preferences. Themed to match the dashboard.
 *
 * Sections: Notifications, Privacy, Danger zone. Toggle values persist to
 * localStorage (keyed per account) so they survive a reload. There is no
 * dedicated preferences API yet; swap the localStorage calls for an endpoint
 * when one exists.
 */
import React, { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { Bell, Eye, EyeOff, Trash2, AlertTriangle, Key, MessageCircle, ArrowUpRight } from 'lucide-react'
import { toast } from 'react-hot-toast'
import { Greeting, SectionCard } from '@/components/dashboard/primitives'
import { TwoFactorSection } from '@/components/dashboard/two-factor-section'
import { useAuth } from '@/hooks/use-auth'
import { authAPI } from '@/api/auth'

interface Prefs {
  notifications: { courseUpdates: boolean; recommendations: boolean; promotional: boolean }
  privacy:       { profilePublic: boolean; showProgress: boolean }
}

const Toggle: React.FC<{ checked: boolean; onChange: () => void; label: string; description: string }> = ({
  checked, onChange, label, description,
}) => (
  <div className="flex items-center justify-between gap-4 dash-card-solid p-4 rounded-xl">
    <div className="min-w-0">
      <h3 className="font-semibold text-secondary-900 text-sm">{label}</h3>
      <p className="text-xs text-slate-500 mt-0.5">{description}</p>
    </div>
    <label className="relative inline-flex items-center cursor-pointer flex-shrink-0">
      <input
        type="checkbox"
        checked={checked}
        onChange={onChange}
        className="sr-only peer"
      />
      <div className="w-11 h-6 bg-slate-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-orange-200 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-orange-500" />
    </label>
  </div>
)

const DEFAULT_PREFS: Prefs = {
  notifications: { courseUpdates: true, recommendations: true, promotional: false },
  privacy:       { profilePublic: true, showProgress: true },
}

export function SettingsPage() {
  const { user, fullName } = useAuth()
  const storageKey = `sasha:prefs:${user?.id ?? 'me'}`

  const [prefs, setPrefs] = useState<Prefs>(() => {
    try {
      const saved = localStorage.getItem(storageKey)
      if (saved) return { ...DEFAULT_PREFS, ...JSON.parse(saved) }
    } catch { /* fall through to defaults */ }
    return DEFAULT_PREFS
  })
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)

  // S-H4: student change-password. auth.py:939 (POST /auth/change-password)
  // and api/auth.ts's authAPI.changePassword already existed — only the
  // ADMIN settings page (admin/settings.tsx:144) called them. Same
  // validation and request shape as that implementation.
  const [passwordData, setPasswordData] = useState({
    currentPassword: '', newPassword: '', confirmPassword: '',
  })
  const [showPasswords, setShowPasswords] = useState({ current: false, new: false, confirm: false })
  const [passwordLoading, setPasswordLoading] = useState(false)

  const togglePasswordVisibility = (field: 'current' | 'new' | 'confirm') => {
    setShowPasswords(prev => ({ ...prev, [field]: !prev[field] }))
  }

  const handlePasswordChange = async (e: React.FormEvent) => {
    e.preventDefault()
    if (passwordData.newPassword !== passwordData.confirmPassword) {
      toast.error('New passwords do not match')
      return
    }
    if (passwordData.newPassword.length < 8) {
      toast.error('Password must be at least 8 characters')
      return
    }
    if (!/[A-Z]/.test(passwordData.newPassword)) {
      toast.error('Password must contain at least one uppercase letter')
      return
    }
    if (!/[a-z]/.test(passwordData.newPassword)) {
      toast.error('Password must contain at least one lowercase letter')
      return
    }
    if (!/[0-9]/.test(passwordData.newPassword)) {
      toast.error('Password must contain at least one number')
      return
    }
    setPasswordLoading(true)
    try {
      await authAPI.changePassword({
        currentPassword: passwordData.currentPassword,
        newPassword: passwordData.newPassword,
      })
      toast.success('Password changed successfully')
      setPasswordData({ currentPassword: '', newPassword: '', confirmPassword: '' })
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to change password')
    } finally {
      setPasswordLoading(false)
    }
  }

  // Persist preferences whenever they change so they survive a reload.
  useEffect(() => {
    try { localStorage.setItem(storageKey, JSON.stringify(prefs)) } catch { /* ignore */ }
  }, [prefs, storageKey])

  const toggleNotif = (key: keyof Prefs['notifications']) => {
    setPrefs(p => ({ ...p, notifications: { ...p.notifications, [key]: !p.notifications[key] } }))
    toast.success('Preferences saved')
  }
  const togglePrivacy = (key: keyof Prefs['privacy']) => {
    setPrefs(p => ({ ...p, privacy: { ...p.privacy, [key]: !p.privacy[key] } }))
    toast.success('Preferences saved')
  }

  return (
    <div className="dash-bg relative min-h-screen">
      <div className="dash-bg-shape dash-bg-shape-1" aria-hidden />
      <div className="dash-bg-shape dash-bg-shape-2" aria-hidden />
      <div className="dash-bg-shape dash-bg-shape-3" aria-hidden />

      <div className="relative z-10 max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <Greeting
          name={fullName}
          chip="ACCOUNT"
          subtitle="Manage your notification preferences, privacy, and connected accounts."
          className="mb-6"
        />

        <div className="space-y-6">
          <SectionCard title="Notifications" icon={Bell} description="Choose what you want to hear about">
            <div className="space-y-3">
              <Link
                to="/communication-preferences"
                className="flex items-center justify-between gap-4 rounded-xl border border-orange-100 bg-gradient-to-r from-orange-50/90 to-white p-4 transition hover:border-orange-200 hover:shadow-sm"
              >
                <span className="flex min-w-0 items-start gap-3">
                  <span className="mt-0.5 grid h-9 w-9 flex-shrink-0 place-items-center rounded-xl bg-orange-100 text-orange-700">
                    <MessageCircle className="h-4 w-4" />
                  </span>
                  <span>
                    <strong className="block text-sm text-secondary-900">WhatsApp and communications</strong>
                    <span className="mt-0.5 block text-xs text-slate-500">Manage one WhatsApp preference for your whole SashaInfinity account.</span>
                  </span>
                </span>
                <ArrowUpRight className="h-4 w-4 flex-shrink-0 text-orange-600" />
              </Link>
              <Toggle
                checked={prefs.notifications.courseUpdates}
                onChange={() => toggleNotif('courseUpdates')}
                label="Course updates"
                description="Get notified when instructors add lessons or post announcements."
              />
              <Toggle
                checked={prefs.notifications.recommendations}
                onChange={() => toggleNotif('recommendations')}
                label="Course recommendations"
                description="Personalised suggestions based on your learning history."
              />
              <Toggle
                checked={prefs.notifications.promotional}
                onChange={() => toggleNotif('promotional')}
                label="Promotional offers"
                description="Discounts, seasonal sales, and bundle deals."
              />
            </div>
          </SectionCard>

          <SectionCard title="Privacy" icon={Eye} description="Control what other learners can see">
            <div className="space-y-3">
              <Toggle
                checked={prefs.privacy.profilePublic}
                onChange={() => togglePrivacy('profilePublic')}
                label="Public profile"
                description="Allow other learners to view your profile page."
              />
              <Toggle
                checked={prefs.privacy.showProgress}
                onChange={() => togglePrivacy('showProgress')}
                label="Show learning progress"
                description="Display your course progress and completion stats on your profile."
              />
            </div>
          </SectionCard>

          <SectionCard title="Change password" icon={Key} description="Update the password you use to sign in">
            <form onSubmit={handlePasswordChange} className="space-y-3 max-w-md">
              <div>
                <label htmlFor="settings-current-password" className="block text-xs font-medium text-slate-600 mb-1">Current password</label>
                <div className="relative">
                  <input
                    id="settings-current-password"
                    type={showPasswords.current ? 'text' : 'password'}
                    value={passwordData.currentPassword}
                    onChange={(e) => setPasswordData({ ...passwordData, currentPassword: e.target.value })}
                    required
                    className="w-full px-3 py-2 pr-10 border border-slate-300 rounded-lg focus:ring-2 focus:ring-orange-400 focus:border-transparent text-sm"
                  />
                  <button
                    type="button"
                    onClick={() => togglePasswordVisibility('current')}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                    aria-label={showPasswords.current ? 'Hide password' : 'Show password'}
                  >
                    {showPasswords.current ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>
              <div>
                <label htmlFor="settings-new-password" className="block text-xs font-medium text-slate-600 mb-1">New password</label>
                <div className="relative">
                  <input
                    id="settings-new-password"
                    type={showPasswords.new ? 'text' : 'password'}
                    value={passwordData.newPassword}
                    onChange={(e) => setPasswordData({ ...passwordData, newPassword: e.target.value })}
                    required
                    minLength={8}
                    className="w-full px-3 py-2 pr-10 border border-slate-300 rounded-lg focus:ring-2 focus:ring-orange-400 focus:border-transparent text-sm"
                  />
                  <button
                    type="button"
                    onClick={() => togglePasswordVisibility('new')}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                    aria-label={showPasswords.new ? 'Hide password' : 'Show password'}
                  >
                    {showPasswords.new ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
                <p className="text-[11px] text-slate-500 mt-1">Min 8 chars, uppercase, lowercase, number</p>
              </div>
              <div>
                <label htmlFor="settings-confirm-password" className="block text-xs font-medium text-slate-600 mb-1">Confirm new password</label>
                <div className="relative">
                  <input
                    id="settings-confirm-password"
                    type={showPasswords.confirm ? 'text' : 'password'}
                    value={passwordData.confirmPassword}
                    onChange={(e) => setPasswordData({ ...passwordData, confirmPassword: e.target.value })}
                    required
                    minLength={8}
                    className="w-full px-3 py-2 pr-10 border border-slate-300 rounded-lg focus:ring-2 focus:ring-orange-400 focus:border-transparent text-sm"
                  />
                  <button
                    type="button"
                    onClick={() => togglePasswordVisibility('confirm')}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                    aria-label={showPasswords.confirm ? 'Hide password' : 'Show password'}
                  >
                    {showPasswords.confirm ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>
              <div className="pt-1">
                <button
                  type="submit"
                  disabled={passwordLoading}
                  className="inline-flex items-center gap-2 px-4 py-2 bg-orange-500 text-white text-sm font-semibold rounded-lg hover:bg-orange-600 transition disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <Key className="w-4 h-4" />
                  {passwordLoading ? 'Changing…' : 'Change password'}
                </button>
              </div>
            </form>
          </SectionCard>

          <TwoFactorSection />

          <SectionCard title="Danger zone" icon={AlertTriangle} description="Irreversible account actions">
            <div className="dash-card-solid p-5 rounded-xl border border-rose-200 bg-rose-50/50">
              <div className="flex items-start gap-3">
                <div className="w-10 h-10 rounded-full bg-rose-100 text-rose-600 flex items-center justify-center flex-shrink-0">
                  <Trash2 className="w-5 h-5" />
                </div>
                <div className="flex-1 min-w-0">
                  <h3 className="font-semibold text-rose-900 text-sm">Delete account</h3>
                  <p className="text-xs text-rose-700 mt-0.5">
                    Permanently delete your account, your enrollments, and all related data. This action cannot be undone.
                  </p>

                  {!showDeleteConfirm ? (
                    <button
                      onClick={() => setShowDeleteConfirm(true)}
                      className="mt-3 text-xs font-semibold px-3 py-1.5 rounded-lg ring-1 ring-rose-300 text-rose-700 hover:bg-rose-100 transition"
                    >
                      Delete my account
                    </button>
                  ) : (
                    <div className="mt-3 space-y-2">
                      <p className="text-xs font-semibold text-rose-800">
                        Are you absolutely sure? Your certificates, progress and enrollments will be lost forever.
                      </p>
                      <div className="flex gap-2">
                        <button
                          onClick={() => {
                            toast.error('Account deletion is disabled in this preview.')
                            setShowDeleteConfirm(false)
                          }}
                          className="text-xs font-semibold px-3 py-1.5 rounded-lg bg-rose-600 text-white hover:bg-rose-700 transition"
                        >
                          Yes, delete my account
                        </button>
                        <button
                          onClick={() => setShowDeleteConfirm(false)}
                          className="text-xs font-semibold px-3 py-1.5 rounded-lg ring-1 ring-slate-300 text-slate-700 hover:bg-white transition"
                        >
                          Cancel
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </SectionCard>
        </div>
      </div>
    </div>
  )
}
