import { describe, it, expect } from 'vitest'
import { snapToCenter, nudgeAmount, clampZoom, SNAP_THRESHOLD_PX } from '../designerSnap'

describe('snapToCenter', () => {
  const stageWidth = 1000
  const stageHeight = 800

  it('snaps to the horizontal+vertical center when within threshold', () => {
    // element 100x50 exactly centered: x = (1000-100)/2 = 450, y = (800-50)/2 = 375
    const result = snapToCenter(450, 375, 100, 50, stageWidth, stageHeight)
    expect(result.snappedX).toBe(true)
    expect(result.snappedY).toBe(true)
    expect(result.x).toBe(450)
    expect(result.y).toBe(375)
  })

  it('snaps when within threshold but not exactly centered', () => {
    const nearlyX = 450 + SNAP_THRESHOLD_PX - 1
    const result = snapToCenter(nearlyX, 375, 100, 50, stageWidth, stageHeight)
    expect(result.snappedX).toBe(true)
    expect(result.x).toBe(450) // snapped to true center, not the nearly-there position
  })

  it('does not snap outside the threshold', () => {
    const farX = 450 + SNAP_THRESHOLD_PX + 5
    const result = snapToCenter(farX, 375, 100, 50, stageWidth, stageHeight)
    expect(result.snappedX).toBe(false)
    expect(result.x).toBe(farX)
  })

  it('snaps X and Y independently', () => {
    // Centered horizontally, far off vertically.
    const result = snapToCenter(450, 10, 100, 50, stageWidth, stageHeight)
    expect(result.snappedX).toBe(true)
    expect(result.snappedY).toBe(false)
    expect(result.x).toBe(450)
    expect(result.y).toBe(10)
  })

  it('respects a custom threshold', () => {
    const x = 450 + 20
    const withDefault = snapToCenter(x, 375, 100, 50, stageWidth, stageHeight)
    expect(withDefault.snappedX).toBe(false)
    const withWideThreshold = snapToCenter(x, 375, 100, 50, stageWidth, stageHeight, 25)
    expect(withWideThreshold.snappedX).toBe(true)
  })
})

describe('nudgeAmount', () => {
  it('returns 1px by default', () => {
    expect(nudgeAmount(false)).toBe(1)
  })
  it('returns 10px with shift held', () => {
    expect(nudgeAmount(true)).toBe(10)
  })
})

describe('clampZoom', () => {
  it('clamps below the minimum', () => {
    expect(clampZoom(10)).toBe(50)
  })
  it('clamps above the maximum', () => {
    expect(clampZoom(999)).toBe(150)
  })
  it('passes through values in range', () => {
    expect(clampZoom(100)).toBe(100)
  })
  it('falls back to min for NaN', () => {
    expect(clampZoom(NaN)).toBe(50)
  })
  it('respects custom bounds', () => {
    expect(clampZoom(5, 10, 20)).toBe(10)
    expect(clampZoom(50, 10, 20)).toBe(20)
  })
})
