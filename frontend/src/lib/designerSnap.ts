/**
 * Snap-to-center guide math for the certificate designer canvas (plan
 * Task 7 binding: "snap-to-center guides (vertical+horizontal center lines
 * appear when near)"). Pure functions — DesignerCanvas calls these during a
 * drag to decide (a) whether to show a guide line and (b) the snapped x/y
 * to actually apply.
 */

export const SNAP_THRESHOLD_PX = 8

export interface SnapResult {
  x: number
  y: number
  snappedX: boolean
  snappedY: boolean
}

/**
 * Given a candidate top-left (x, y) for an element of size (width, height)
 * moving inside a stage of size (stageWidth, stageHeight), returns the
 * position snapped to the stage's horizontal/vertical center when the
 * element's own center is within SNAP_THRESHOLD_PX of that center — else
 * the original position, unchanged.
 */
export function snapToCenter(
  x: number,
  y: number,
  width: number,
  height: number,
  stageWidth: number,
  stageHeight: number,
  threshold: number = SNAP_THRESHOLD_PX
): SnapResult {
  const centerX = x + width / 2
  const centerY = y + height / 2
  const stageCenterX = stageWidth / 2
  const stageCenterY = stageHeight / 2

  const snappedX = Math.abs(centerX - stageCenterX) <= threshold
  const snappedY = Math.abs(centerY - stageCenterY) <= threshold

  return {
    x: snappedX ? stageCenterX - width / 2 : x,
    y: snappedY ? stageCenterY - height / 2 : y,
    snappedX,
    snappedY,
  }
}

/** Nudge amount for arrow-key movement (plan Task 7 binding: "arrow-key
 * nudge"). Shift held = larger step, matching common design-tool conventions. */
export function nudgeAmount(shiftKey: boolean): number {
  return shiftKey ? 10 : 1
}

/** Clamp a zoom percentage to the designer's allowed 50-150% range. */
export function clampZoom(zoom: number, min: number = 50, max: number = 150): number {
  if (Number.isNaN(zoom)) return min
  return Math.min(max, Math.max(min, zoom))
}
