import type { LessonCodingBlock } from '@/api/coding'

/**
 * The first timed block that playback has reached and the learner has not
 * finished yet. Blocks with no timestamp are listed after the lesson instead.
 */
export function dueBlock(
  blocks: LessonCodingBlock[],
  currentTime: number,
  finished: ReadonlySet<number>,
): LessonCodingBlock | null {
  const due = blocks
    .filter((block) => block.position_seconds !== null && !finished.has(block.id))
    .filter((block) => currentTime >= (block.position_seconds as number))
    .sort((a, b) => (a.position_seconds as number) - (b.position_seconds as number))
  return due[0] ?? null
}

export function formatPosition(seconds: number): string {
  const total = Math.max(0, Math.floor(seconds))
  const minutes = Math.floor(total / 60)
  const rest = String(total % 60).padStart(2, '0')
  return `${minutes}:${rest}`
}
