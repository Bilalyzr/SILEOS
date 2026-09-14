import * as React from 'react'
import { Hand } from 'lucide-react'
import { useLiveClassStore } from '@/store/liveClassStore'

export interface RaiseHandListProps {
  className?: string
}

/**
 * Reads raised hands straight from the live-class store (populated by
 * JitsiStage's endpointTextMessageReceived / raise-hand event wiring).
 * Falls back to the participant id when no display name is known yet.
 */
export const RaiseHandList: React.FC<RaiseHandListProps> = ({ className = '' }) => {
  const raisedHands = useLiveClassStore((s) => s.raisedHands)
  const participants = useLiveClassStore((s) => s.participants)

  if (raisedHands.length === 0) {
    return (
      <div className={`text-xs text-slate-400 flex items-center gap-1.5 ${className}`}>
        <Hand className="h-3.5 w-3.5" />
        No raised hands
      </div>
    )
  }

  return (
    <ul className={`flex flex-col gap-1.5 ${className}`} data-testid="raise-hand-list">
      {raisedHands.map((participantId) => {
        const participant = participants[participantId]
        return (
          <li
            key={participantId}
            className="flex items-center gap-2 rounded-md bg-warning-50 border border-warning-200 px-2.5 py-1.5 text-xs"
          >
            <Hand className="h-3.5 w-3.5 text-warning-600 flex-shrink-0" />
            <span className="text-secondary-900 font-medium truncate">
              {participant?.displayName || 'Participant'}
            </span>
          </li>
        )
      })}
    </ul>
  )
}

export default RaiseHandList
