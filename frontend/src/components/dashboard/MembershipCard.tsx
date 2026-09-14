import * as React from 'react'
import { confirmDialog } from '@/components/ui/confirm'
import toast from 'react-hot-toast'
import { Crown, AlertTriangle } from 'lucide-react'
import { SectionCard, EmptyState, ErrorState, Spinner } from '@/components/dashboard/primitives'
import {
  fetchMyMembership,
  cancelMembership,
  MyMembership,
} from '@/api/membership'

const formatDate = (value: string | null): string =>
  value ? new Date(value).toLocaleDateString() : '—'

const STATUS_LABEL: Record<string, string> = {
  pending: 'Pending',
  active: 'Active',
  grace: 'Payment issue',
  suspended: 'Suspended',
  cancelled: 'Cancelled',
  completed: 'Completed',
}

const STATUS_CLASS: Record<string, string> = {
  pending: 'bg-amber-100 text-amber-800',
  active: 'bg-emerald-100 text-emerald-800',
  grace: 'bg-amber-100 text-amber-800',
  suspended: 'bg-rose-100 text-rose-800',
  cancelled: 'bg-slate-100 text-slate-700',
  completed: 'bg-slate-100 text-slate-700',
}

export const MembershipCard: React.FC = () => {
  const [membership, setMembership] = React.useState<MyMembership | null>(null)
  const [loading, setLoading] = React.useState(true)
  const [loadError, setLoadError] = React.useState(false)
  const [cancelling, setCancelling] = React.useState(false)

  const load = React.useCallback(async () => {
    setLoading(true)
    setLoadError(false)
    try {
      const m = await fetchMyMembership()
      setMembership(m)
    } catch {
      // Non-404 failure (500 / network) — do NOT fall back to the
      // no-membership empty state, that would hide an existing
      // membership's Cancel button and status during an outage.
      setLoadError(true)
    } finally {
      setLoading(false)
    }
  }, [])

  React.useEffect(() => { load() }, [load])

  const handleCancel = async () => {
    if (!await confirmDialog('Cancel your membership? You will keep access until the end of the current period.')) {
      return
    }
    setCancelling(true)
    try {
      await cancelMembership()
      toast.success('Membership cancelled')
      await load()
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || 'Could not cancel membership')
    } finally {
      setCancelling(false)
    }
  }

  return (
    <SectionCard title="My membership" icon={Crown}>
      {loading ? (
        <div className="flex items-center justify-center py-8">
          <Spinner />
        </div>
      ) : loadError ? (
        <ErrorState
          title="Couldn't load membership status"
          description="Refresh to retry."
          onRetry={load}
        />
      ) : !membership ? (
        <EmptyState
          icon={Crown}
          title="No active membership"
          description="Subscribe to get ongoing access to courses."
          action={{ label: 'Explore memberships', to: '/membership' }}
        />
      ) : (
        <div className="space-y-4">
          <div className="flex items-start justify-between gap-3">
            <div>
              <h3 className="font-semibold text-secondary-900">{membership.plan_name}</h3>
              <span className={`inline-block mt-1 text-xs font-medium px-2 py-0.5 rounded-full ${STATUS_CLASS[membership.status] || 'bg-slate-100 text-slate-700'}`}>
                {STATUS_LABEL[membership.status] || membership.status}
              </span>
            </div>
          </div>

          {membership.status === 'grace' && (
            <div className="flex items-start gap-2 text-sm text-amber-800 bg-amber-50 border border-amber-200 rounded-lg p-3">
              <AlertTriangle className="w-4 h-4 flex-shrink-0 mt-0.5" />
              <span>
                Payment issue — access ends {formatDate(membership.grace_until)} unless payment succeeds.
              </span>
            </div>
          )}

          {membership.status === 'cancelled' && (
            <p className="text-sm text-slate-600">
              Ends {formatDate(membership.current_period_end)}
            </p>
          )}

          {(membership.status === 'active' || membership.status === 'pending') && (
            <p className="text-sm text-slate-600">
              {membership.cancel_at_period_end
                ? `Ends ${formatDate(membership.current_period_end)}`
                : `Renews ${formatDate(membership.current_period_end)}`}
            </p>
          )}

          {['pending', 'active', 'grace'].includes(membership.status) && !membership.cancel_at_period_end && (
            <button
              className="dash-cta-ghost text-xs px-3 py-1.5"
              onClick={handleCancel}
              disabled={cancelling}
            >
              {cancelling ? 'Cancelling...' : 'Cancel membership'}
            </button>
          )}
        </div>
      )}
    </SectionCard>
  )
}

export default MembershipCard
