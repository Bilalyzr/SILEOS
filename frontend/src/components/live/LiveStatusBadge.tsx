import * as React from 'react'
import { Badge } from '@/components/ui/badge'
import type { LiveClassStatus } from '@/api/liveClasses'

export interface LiveStatusBadgeProps {
  status: LiveClassStatus
  className?: string
}

const CONFIG: Record<LiveClassStatus, { label: string; variant: 'success' | 'neutral' | 'secondary' | 'danger'; pulse?: boolean }> = {
  live: { label: 'LIVE', variant: 'danger', pulse: true },
  scheduled: { label: 'Scheduled', variant: 'secondary' },
  ended: { label: 'Ended', variant: 'neutral' },
  cancelled: { label: 'Cancelled', variant: 'neutral' },
}

export const LiveStatusBadge: React.FC<LiveStatusBadgeProps> = ({ status, className = '' }) => {
  const cfg = CONFIG[status] ?? CONFIG.scheduled
  return (
    <Badge variant={cfg.variant} className={`inline-flex items-center gap-1 ${className}`}>
      {cfg.pulse && (
        <span className="relative flex h-1.5 w-1.5">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-white opacity-75" />
          <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-white" />
        </span>
      )}
      {cfg.label}
    </Badge>
  )
}
