/**
 * Frame format for pair-room sockets. Matches backend/app/services/collab_hub.py.
 *   byte 0 = 0 (incremental Yjs update) or 1 (full snapshot), then the Yjs bytes.
 */

export const KIND_UPDATE = 0
export const KIND_SNAPSHOT = 1
export const MAX_FRAME_BYTES = 512 * 1024

export type FrameKind = typeof KIND_UPDATE | typeof KIND_SNAPSHOT

export function encodeFrame(kind: FrameKind, payload: Uint8Array): Uint8Array {
  const frame = new Uint8Array(payload.length + 1)
  frame[0] = kind
  frame.set(payload, 1)
  return frame
}

export function decodeFrame(data: ArrayBuffer | Uint8Array): { kind: FrameKind; payload: Uint8Array } | null {
  const bytes = data instanceof Uint8Array ? data : new Uint8Array(data)
  if (bytes.length < 2 || bytes.length > MAX_FRAME_BYTES) return null
  if (bytes[0] !== KIND_UPDATE && bytes[0] !== KIND_SNAPSHOT) return null
  return { kind: bytes[0], payload: bytes.subarray(1) }
}

/**
 * Builds the socket URL from the API base (relative like "/api/v1", or absolute)
 * and the page origin, switching http to ws and https to wss.
 */
export function collabSocketUrl(apiBase: string, origin: string, roomId: number, ticket: string): string {
  const path = `/utporul/coding/collab-rooms/${roomId}/ws?ticket=${encodeURIComponent(ticket)}`
  const base = /^https?:\/\//.test(apiBase) ? apiBase : `${origin}${apiBase.startsWith('/') ? '' : '/'}${apiBase}`
  return `${base.replace(/^http/, 'ws').replace(/\/$/, '')}${path}`
}
