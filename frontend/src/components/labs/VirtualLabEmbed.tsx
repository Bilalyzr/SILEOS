/**
 * Back-compat wrapper: older call sites render a lab by `sim` slug. The
 * catalog-aware VirtualLabPlayer decides between the iframe (PhET / admin
 * embeds) and the native engines. Kept so existing imports keep working.
 */
import { VirtualLabPlayer } from './VirtualLabPlayer'

export function VirtualLabEmbed({
  sim,
  title,
  height = 560,
  previewOnly = false,
  onLessonComplete,
}: {
  sim: string
  title?: string
  height?: number
  previewOnly?: boolean
  onLessonComplete?: () => void
}) {
  return <VirtualLabPlayer slug={sim} title={title} height={height} previewOnly={previewOnly} onLessonComplete={onLessonComplete} />
}

export default VirtualLabEmbed
