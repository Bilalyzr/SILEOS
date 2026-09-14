/**
 * TwoFactorSection — 2FA (TOTP) management card.
 *
 * Three states:
 *   1. ENABLED  — green badge, "Disable" button (requires a live code).
 *   2. PENDING  — after /2fa/setup, before /2fa/enable. Shows QR + secret
 *                 and a code field to confirm + enable.
 *   3. DISABLED — "Enable 2FA" button to kick off enrolment.
 *
 * Mandatory reminder for admin/superadmin: login is refused entirely if
 * totp_enabled is ever false (see routers/auth.py), so disabling shows a
 * strong warning for those roles.
 */
import React, { useState } from 'react'
import { confirmDialog } from '@/components/ui/confirm'
import { ShieldCheck, KeyRound, AlertTriangle, Copy, Check } from 'lucide-react'
import toast from 'react-hot-toast'
import { SectionCard } from '@/components/dashboard/primitives'
import { authAPI } from '@/api/auth'
import { useAuth } from '@/hooks/use-auth'

type Status = 'enabled' | 'pending' | 'disabled'

export const TwoFactorSection: React.FC = () => {
  const { user } = useAuth()
  const isAdminLike = user?.role === 'admin' || user?.role === 'superadmin'

  // Derive initial status from the user object (best-effort; backend is the
  // source of truth and a fresh /setup flips us to 'pending').
  const [status, setStatus] = useState<Status>(
    user?.totp_enabled ? 'enabled' : 'disabled',
  )
  const [secret, setSecret] = useState<string | null>(null)
  const [code, setCode] = useState('')
  const [busy, setBusy] = useState(false)
  const [copied, setCopied] = useState(false)

  const handleSetup = async () => {
    setBusy(true)
    try {
      const res = await authAPI.setupTwoFactor()
      setSecret(res.secret)
      setStatus('pending')
      toast.success('Scan the QR, then confirm a code below.')
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || 'Could not start 2FA setup.')
    } finally {
      setBusy(false)
    }
  }

  const handleEnable = async () => {
    if (!/^\d{6}$/.test(code.trim())) {
      toast.error('Enter the 6-digit code from your authenticator.')
      return
    }
    setBusy(true)
    try {
      await authAPI.enableTwoFactor(code.trim())
      setStatus('enabled')
      setSecret(null)
      setCode('')
      toast.success('Two-factor authentication enabled.')
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || 'That code did not match.')
    } finally {
      setBusy(false)
    }
  }

  const handleDisable = async () => {
    if (!/^\d{6}$/.test(code.trim())) {
      toast.error('Enter your current 6-digit code to disable.')
      return
    }
    if (isAdminLike) {
      const ok = await confirmDialog(
        'WARNING: you are an admin/superadmin. Login will be REFUSED until ' +
          '2FA is re-enabled. Continue?',
        { confirmLabel: 'Disable 2FA', danger: true },
      )
      if (!ok) return
    }
    setBusy(true)
    try {
      await authAPI.disableTwoFactor(code.trim())
      setStatus('disabled')
      setCode('')
      toast.success('Two-factor authentication disabled.')
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || 'Could not disable 2FA.')
    } finally {
      setBusy(false)
    }
  }

  const copySecret = async () => {
    if (!secret) return
    try {
      await navigator.clipboard.writeText(secret)
      setCopied(true)
      setTimeout(() => setCopied(false), 1500)
    } catch {
      toast.error('Copy failed — select and copy manually.')
    }
  }

  return (
    <SectionCard
      title="Two-factor authentication"
      icon={ShieldCheck}
      description="Add a second factor (authenticator app) to protect your account."
    >
      <div className="p-5 space-y-4">
        {/* Status badge */}
        <div className="flex items-center gap-3">
          <span
            className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-semibold ${
              status === 'enabled'
                ? 'bg-emerald-100 text-emerald-700'
                : status === 'pending'
                  ? 'bg-amber-100 text-amber-700'
                  : 'bg-slate-100 text-slate-600'
            }`}
          >
            <ShieldCheck className="h-3.5 w-3.5" />
            {status === 'enabled'
              ? 'Enabled'
              : status === 'pending'
                ? 'Pending confirmation'
                : 'Not enabled'}
          </span>
          {isAdminLike && (
            <span className="text-xs text-slate-500">
              Required for your role
            </span>
          )}
        </div>

        {/* DISABLED state */}
        {status === 'disabled' && (
          <div className="space-y-3">
            <p className="text-sm text-slate-600">
              With 2FA on, you'll enter a 6-digit code from an authenticator
              app (Google Authenticator, Microsoft Authenticator, Authy, 1Password)
              each time you sign in.
            </p>
            <button
              onClick={handleSetup}
              disabled={busy}
              className="inline-flex items-center gap-2 rounded-lg bg-orange-500 px-4 py-2 text-sm font-semibold text-white hover:bg-orange-600 disabled:opacity-50"
            >
              <KeyRound className="h-4 w-4" />
              Enable 2FA
            </button>
          </div>
        )}

        {/* PENDING state — QR + confirm */}
        {status === 'pending' && (
          <div className="space-y-4">
            <div className="flex flex-col sm:flex-row gap-4">
              {/* QR image from the backend (no client QR dep) */}
              <div className="flex-shrink-0">
                <img
                  src="/api/v1/auth/2fa/qr"
                  alt="2FA QR code"
                  className="w-40 h-40 rounded-lg border border-slate-200 bg-white p-2"
                  onError={(e) => {
                    (e.target as HTMLImageElement).style.display = 'none'
                  }}
                />
              </div>
              <div className="flex-1 min-w-0 space-y-2">
                <p className="text-sm text-slate-600">
                  Scan the QR with your authenticator app, or enter the secret
                  manually:
                </p>
                <div className="flex items-center gap-2">
                  <code className="block flex-1 truncate rounded-md bg-slate-100 px-3 py-2 font-mono text-xs text-slate-800">
                    {secret}
                  </code>
                  <button
                    onClick={copySecret}
                    className="flex-shrink-0 rounded-md border border-slate-300 bg-white p-2 text-slate-600 hover:bg-slate-50"
                    title="Copy secret"
                  >
                    {copied ? (
                      <Check className="h-4 w-4 text-emerald-600" />
                    ) : (
                      <Copy className="h-4 w-4" />
                    )}
                  </button>
                </div>
              </div>
            </div>

            <div className="space-y-2">
              <label className="block text-xs font-semibold text-slate-700">
                Enter the 6-digit code from your app to confirm
              </label>
              <div className="flex gap-2">
                <input
                  value={code}
                  onChange={(e) =>
                    setCode(e.target.value.replace(/\D/g, '').slice(0, 6))
                  }
                  placeholder="123456"
                  inputMode="numeric"
                  className="w-32 rounded-lg border border-slate-300 px-3 py-2 font-mono text-sm tracking-widest focus:border-orange-400 focus:outline-none focus:ring-1 focus:ring-orange-400"
                />
                <button
                  onClick={handleEnable}
                  disabled={busy || code.length !== 6}
                  className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-700 disabled:opacity-50"
                >
                  {busy ? 'Verifying…' : 'Confirm & enable'}
                </button>
              </div>
            </div>
          </div>
        )}

        {/* ENABLED state */}
        {status === 'enabled' && (
          <div className="space-y-3">
            <p className="text-sm text-slate-600">
              Your account is protected. You'll need a code from your
              authenticator app to sign in.
            </p>
            {isAdminLike && (
              <div className="flex items-start gap-2 rounded-md border border-rose-200 bg-rose-50 p-3">
                <AlertTriangle className="mt-0.5 h-4 w-4 flex-shrink-0 text-rose-600" />
                <p className="text-xs text-rose-700">
                  Disabling 2FA will <strong>lock you out</strong> — login is
                  refused for your role until it's re-enabled.
                </p>
              </div>
            )}
            <details className="text-sm">
              <summary className="cursor-pointer font-semibold text-slate-700 hover:text-slate-900">
                Disable 2FA
              </summary>
              <div className="mt-3 space-y-2">
                <label className="block text-xs font-semibold text-slate-700">
                  Enter your current 6-digit code to disable
                </label>
                <div className="flex gap-2">
                  <input
                    value={code}
                    onChange={(e) =>
                      setCode(e.target.value.replace(/\D/g, '').slice(0, 6))
                    }
                    placeholder="123456"
                    inputMode="numeric"
                    className="w-32 rounded-lg border border-slate-300 px-3 py-2 font-mono text-sm tracking-widest focus:border-rose-400 focus:outline-none focus:ring-1 focus:ring-rose-400"
                  />
                  <button
                    onClick={handleDisable}
                    disabled={busy || code.length !== 6}
                    className="rounded-lg border border-rose-300 bg-white px-4 py-2 text-sm font-semibold text-rose-700 hover:bg-rose-50 disabled:opacity-50"
                  >
                    {busy ? 'Disabling…' : 'Disable'}
                  </button>
                </div>
              </div>
            </details>
          </div>
        )}
      </div>
    </SectionCard>
  )
}

export default TwoFactorSection
