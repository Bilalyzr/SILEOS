/**
 * DigiLockerButton (v2.0 §10 — WP8): push an issued certificate to DigiLocker /
 * APAAR. Honest: shows the 503 detail (missing issuer credentials) instead of
 * pretending. `issuedId` is IssuedCertificate.id.
 */
import { useState } from 'react'
import { flywheelAPI } from '@/api/flywheel'

export function DigiLockerButton({ issuedId }: { issuedId: number }) {
  const [msg, setMsg] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const push = async () => {
    setBusy(true); setMsg(null)
    try {
      const r = await flywheelAPI.pushDigilocker(issuedId)
      setMsg(r.status === 'prepared' ? 'Prepared for DigiLocker — the issuer push completes on the server.' : 'Done')
    } catch (e: any) {
      setMsg(e?.response?.data?.detail || 'DigiLocker push failed')
    } finally { setBusy(false) }
  }
  return (
    <div className="mt-2" data-testid="digilocker">
      <button type="button" disabled={busy} onClick={push} className="px-3 py-1.5 text-xs rounded-lg border border-gray-300 hover:bg-gray-50 disabled:opacity-40">
        {busy ? 'Contacting DigiLocker…' : 'Add to DigiLocker / APAAR'}
      </button>
      {msg && <p className="text-[11px] text-amber-800 mt-1" role="status">{msg}</p>}
    </div>
  )
}

export default DigiLockerButton
