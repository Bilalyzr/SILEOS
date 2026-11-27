import { describe, expect, it } from 'vitest'
import { KIND_SNAPSHOT, KIND_UPDATE, collabSocketUrl, decodeFrame, encodeFrame } from '../collabFrames'

describe('pair room frames', () => {
  it('round-trips update and snapshot frames', () => {
    const payload = new Uint8Array([1, 2, 3])
    const update = decodeFrame(encodeFrame(KIND_UPDATE, payload))
    expect(update?.kind).toBe(KIND_UPDATE)
    expect(Array.from(update!.payload)).toEqual([1, 2, 3])

    const snapshot = decodeFrame(encodeFrame(KIND_SNAPSHOT, payload))
    expect(snapshot?.kind).toBe(KIND_SNAPSHOT)
  })

  it('rejects unknown kinds, empty frames and oversized frames', () => {
    expect(decodeFrame(new Uint8Array([9, 1, 2]))).toBeNull()
    expect(decodeFrame(new Uint8Array([0]))).toBeNull()
    expect(decodeFrame(new Uint8Array(512 * 1024 + 2))).toBeNull()
  })
})

describe('collabSocketUrl', () => {
  it('uses ws on http origins and wss on https origins', () => {
    expect(collabSocketUrl('/api/v1', 'http://localhost:3000', 4, 'abc'))
      .toBe('ws://localhost:3000/api/v1/utporul/coding/collab-rooms/4/ws?ticket=abc')
    expect(collabSocketUrl('/api/v1', 'https://sashainfinity.com', 4, 'abc'))
      .toBe('wss://sashainfinity.com/api/v1/utporul/coding/collab-rooms/4/ws?ticket=abc')
  })

  it('converts an absolute API base and encodes the ticket', () => {
    expect(collabSocketUrl('https://api.example.com/api/v1/', 'https://app.example.com', 9, 'a b'))
      .toBe('wss://api.example.com/api/v1/utporul/coding/collab-rooms/9/ws?ticket=a%20b')
  })
})
