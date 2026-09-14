import * as React from 'react'
import { Circle } from 'lucide-react'

export interface RecordingBadgeProps {
  /** True while the class is actively being recorded — surfaces the
   * "This class is being recorded" consent banner for students, per the
   * brief's UX principles. */
  isRecording: boolean
  className?: string
}

export const RecordingBadge: React.FC<RecordingBadgeProps> = ({ isRecording, className = '' }) => {
  if (!isRecording) return null
  return (
    <div
      role="status"
      className={`flex items-center gap-2 rounded-md bg-danger-50 border border-danger-200 text-danger-700 text-xs font-semibold px-3 py-1.5 ${className}`}
    >
      <Circle className="h-2.5 w-2.5 fill-danger-600 text-danger-600 animate-pulse" />
      This class is being recorded
    </div>
  )
}
