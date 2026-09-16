import * as React from 'react'
import { Phone } from 'lucide-react'
import toast from 'react-hot-toast'
import { Button } from '@/components/ui/button'
import { cn } from '@/utils/cn'
import { useAuthStore } from '@/store/auth'
import { authAPI } from '@/api/auth'
import { isValidMobileNumber, normalizeMobileNumber, MOBILE_NUMBER_ERROR } from '@/utils/phone'

/**
 * Blocking prompt for students who have no mobile number on file.
 *
 * Accounts created with Google before the number became mandatory never
 * supplied one (Google doesn't return a phone number), so they're asked for it
 * once, on their next visit, before they can reach the dashboard or a lesson.
 * New Google signups collect it during signup (see RoleSelectionModal) and so
 * never see this. It is deliberately not dismissible — no close button, no
 * backdrop click, no Escape — the number is required to continue.
 */
export const MobileNumberGate: React.FC = () => {
  const { isAuthenticated, user, profile } = useAuthStore()
  const [phone, setPhone] = React.useState('')
  const [error, setError] = React.useState<string | null>(null)
  const [saving, setSaving] = React.useState(false)

  // Only students are gated: staff roles (instructor/admin/company/spoc) are
  // onboarded through flows that already capture contact details.
  const needsPhone =
    isAuthenticated &&
    !!user &&
    user.role === 'student' &&
    !((profile?.phone ?? '').trim())

  // Lock background scroll while the prompt is up.
  React.useEffect(() => {
    if (!needsPhone) return
    const previous = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => {
      document.body.style.overflow = previous
    }
  }, [needsPhone])

  if (!needsPhone) return null

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!isValidMobileNumber(phone)) {
      setError(MOBILE_NUMBER_ERROR)
      return
    }

    setSaving(true)
    try {
      const saved = await authAPI.setPhoneNumber(normalizeMobileNumber(phone))

      // Merge into the store directly rather than via setProfile(), which is a
      // no-op when the account has no profile object loaded — that would leave
      // the gate stuck open after a successful save.
      const current = useAuthStore.getState().profile
      useAuthStore.setState({ profile: { ...(current ?? {}), phone: saved } as any })

      toast.success('Mobile number saved')
    } catch (err: any) {
      const message = err?.response?.data?.detail || 'Could not save your number. Please try again.'
      setError(typeof message === 'string' ? message : MOBILE_NUMBER_ERROR)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div
      className="fixed inset-0 z-[100] flex items-center justify-center bg-black/60 backdrop-blur-sm p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="mobile-gate-title"
    >
      <div className="w-full max-w-md rounded-2xl bg-white shadow-2xl animate-in fade-in-0 zoom-in-95 duration-200">
        <form onSubmit={handleSubmit} className="p-8">
          <div className="text-center mb-6">
            <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-primary-100 text-primary-600">
              <Phone className="h-6 w-6" />
            </div>
            <h2 id="mobile-gate-title" className="text-xl font-bold text-neutral-900 mb-2">
              Add your mobile number
            </h2>
            <p className="text-sm text-neutral-600">
              We need a mobile number on your account before you continue learning.
            </p>
          </div>

          <label htmlFor="mobile-gate-phone" className="block text-sm font-medium text-neutral-800 mb-2">
            Mobile number <span className="text-red-500">*</span>
          </label>
          <div className="flex items-stretch">
            <span className="inline-flex items-center rounded-l-lg border border-r-0 border-neutral-300 bg-neutral-50 px-3 text-sm text-neutral-600">
              +91
            </span>
            <input
              id="mobile-gate-phone"
              type="tel"
              inputMode="numeric"
              autoComplete="tel"
              autoFocus
              maxLength={10}
              value={phone}
              disabled={saving}
              onChange={(e) => {
                setPhone(e.target.value.replace(/\D/g, '').slice(0, 10))
                if (error) setError(null)
              }}
              placeholder="9876543210"
              aria-invalid={!!error}
              aria-describedby={error ? 'mobile-gate-error' : undefined}
              className={cn(
                'min-w-0 flex-1 rounded-r-lg border px-3 py-2 text-neutral-900 outline-none transition-colors',
                'focus:border-primary-500 focus:ring-2 focus:ring-primary-100',
                error ? 'border-red-400' : 'border-neutral-300',
                saving && 'cursor-not-allowed bg-neutral-50'
              )}
            />
          </div>
          {error && (
            <p id="mobile-gate-error" className="mt-2 text-sm text-red-600">
              {error}
            </p>
          )}

          <Button
            type="submit"
            className="mt-6 w-full"
            size="lg"
            disabled={!isValidMobileNumber(phone) || saving}
            loading={saving}
          >
            {saving ? 'Saving...' : 'Save and continue'}
          </Button>
        </form>
      </div>
    </div>
  )
}
