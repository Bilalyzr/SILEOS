/**
 * Deterministic scoring functions for the 5 game templates (spec §1's
 * table, BINDING). Pure and unit-tested; the engine components call these
 * and never inline score math. The server clamps whatever we report to
 * its own derived max, so these functions are UX truth, not security.
 */

/** Uniform rule: max_score = 10 x item count (server derives the same). */
export function deriveMaxScore(itemCount: number): number {
  return itemCount * 10
}

/** Clamp a running total into [0, maxScore] (quiz_rush streak cap etc.). */
export function capScore(total: number, maxScore: number): number {
  return Math.max(0, Math.min(total, maxScore))
}

/** Streak length at which the x1.5 multiplier kicks in (resolved ambiguity:
 * from the 3rd consecutive correct answer onward). */
export const QUIZ_RUSH_STREAK_THRESHOLD = 3

/**
 * quiz_rush: faster answer = more of the 10 pts. Linear 4 + 6 x
 * (timeRemaining / secondsPerQuestion), rounded — floor 4 on correct,
 * 0 on wrong. `streakBefore` = consecutive correct answers BEFORE this
 * one, so the multiplier applies ON the 3rd consecutive correct
 * (streakBefore >= 2 — streakBefore=2 means this answer is the 3rd in a
 * row): the answer's points are multiplied by 1.5 (total capped at
 * max_score by the caller via capScore).
 */
export function scoreQuizRushAnswer(
  correct: boolean,
  timeRemainingS: number,
  secondsPerQuestion: number,
  streakBefore: number
): number {
  if (!correct) return 0
  const fraction = secondsPerQuestion > 0
    ? Math.max(0, Math.min(1, timeRemainingS / secondsPerQuestion))
    : 0
  let points = Math.round(4 + 6 * fraction)
  if (streakBefore >= QUIZ_RUSH_STREAK_THRESHOLD - 1) {
    points = Math.round(points * 1.5)
  }
  return points
}

/** match_pairs: 10 pts per pair minus 1 per miss on that pair (no free
 * first miss), floor 3. */
export function scoreMatchPair(misses: number): number {
  return Math.max(3, 10 - misses)
}

/** drag_sort: 10 pts per correctly placed item; each wrong placement
 * bounces back at -3, floor 2. `wrongAttempts` = bounce-backs before the
 * correct placement. */
export function scoreDragSortItem(wrongAttempts: number): number {
  return Math.max(2, 10 - 3 * wrongAttempts)
}

/** word_builder: 10 pts, -2 per hint used (hints_allowed <= 3), floor 0. */
export function scoreWordBuilderItem(hintsUsed: number): number {
  return Math.max(0, 10 - 2 * hintsUsed)
}

/** sequence: 10 pts per item in correct final position on the accepted
 * submit — 7 per item when that submit is the one allowed retry (-3). */
export function scoreSequenceSubmit(correctCount: number, isRetry: boolean): number {
  return correctCount * (isRetry ? 7 : 10)
}
