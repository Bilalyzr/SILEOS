/**
 * A-H3 — admin "Generate reset link" action.
 *
 * Calls POST /admin/users/{id}/password-reset-link (admin.py) which mints
 * a ONE-TIME reset token (the same single-use jti mechanism as
 * auth.forgot_password) and returns the link exactly once. The link is
 * shown in a modal with a copy button and is NOT persisted anywhere on
 * the client — closing the modal discards it. The admin never sees or
 * sets the user's actual password; that stays self-service on the
 * /reset-password page the link points to.
 *
 * Shared by the admin Students and Instructors pages so both render the
 * same flow.
 */
import * as React from 'react'
import { confirmDialog } from '@/components/ui/confirm'
import { KeyRound, Copy, Check, X, Loader2 } from 'lucide-react'
import toast from 'react-hot-toast'
import { api } from '@/api/axios'

export interface PasswordResetLinkActionProps {
  userId: number
  userName: string
  /** Icon-only button (matches the students table's icon action row). */
  compact?: boolean
  className?: string
}

export const PasswordResetLinkAction: React.FC<PasswordResetLinkActionProps> = ({
  userId, userName, compact = false, className = '',
}) => {
  const [busy, setBusy] = React.useState(false)
  const [link, setLink] = React.useState<string | null>(null)
  const [copied, setCopied] = React.useState(false)

  const generate = async () => {
    if (!await confirmDialog(
      `Generate a one-time password reset link for ${userName}?\n\n` +
      'The link is shown once and expires in 1 hour. Share it with the user directly — ' +
      'it lets them set a new password themselves.'
    )) return
    setBusy(true)
    try {
      const r = await api.post(`/admin/users/${userId}/password-reset-link`)
      const value = r?.data?.reset_link
      if (!value) throw new Error('No reset link returned')
      setLink(value)
      setCopied(false)
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || err?.message || 'Failed to generate reset link')
    } finally {
      setBusy(false)
    }
  }

  const copy = async () => {
    if (!link) return
    try {
      await navigator.clipboard.writeText(link)
      setCopied(true)
      toast.success('Reset link copied')
    } catch {
      toast.error('Could not copy — select the link and copy it manually')
    }
  }

  const close = () => {
    setLink(null)
    setCopied(false)
  }

  return (
    <>
      <button
        type="button"
        onClick={generate}
        disabled={busy}
        className={
          compact
            ? `p-2 rounded-lg text-amber-600 hover:bg-amber-50 transition-colors disabled:opacity-50 ${className}`
            : `text-amber-600 hover:text-amber-800 flex items-center gap-1 disabled:opacity-50 ${className}`
        }
        title="Generate one-time password reset link"
        aria-label={`Generate password reset link for ${userName}`}
      >
        {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <KeyRound className="w-4 h-4" />}
        {!compact && <span>{busy ? 'Generating…' : 'Reset link'}</span>}
      </button>

      {link && (
        <div
          className="fixed inset-0 z-[100] bg-black/50 flex items-center justify-center p-4"
          onClick={close}
        >
          <div
            className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-2xl"
            onClick={(e) => e.stopPropagation()}
            role="dialog"
            aria-label="One-time password reset link"
          >
            <div className="flex items-start justify-between gap-3 mb-3">
              <div>
                <p className="font-semibold text-gray-900">Password reset link for {userName}</p>
                <p className="text-xs text-gray-600 mt-1">
                  Shown once. Expires in 1 hour and can only be used one time — copy it now and send it to
                  the user. It will not be displayed again.
                </p>
              </div>
              <button type="button" onClick={close} aria-label="Close" className="text-gray-400 hover:text-gray-700">
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="flex gap-2">
              <input
                type="text"
                readOnly
                value={link}
                onFocus={(e) => e.currentTarget.select()}
                aria-label="Reset link"
                className="flex-1 px-3 py-2 text-xs font-mono border border-gray-300 rounded-lg bg-gray-50"
              />
              <button
                type="button"
                onClick={copy}
                className="inline-flex items-center gap-1.5 px-3 py-2 text-sm font-medium rounded-lg bg-blue-600 text-white hover:bg-blue-700"
              >
                {copied ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
                {copied ? 'Copied' : 'Copy'}
              </button>
            </div>
            <div className="flex justify-end mt-4">
              <button
                type="button"
                onClick={close}
                className="px-4 py-2 text-sm font-medium rounded-lg ring-1 ring-gray-300 text-gray-700 hover:bg-gray-50"
              >
                Done
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}

export default PasswordResetLinkAction
