import { useEffect, useRef, useState } from 'react'
import * as monaco from 'monaco-editor/editor/editor.api.js'
import * as Y from 'yjs'
import { MonacoBinding } from 'y-monaco'
import { codingCollabAPI, type CollabRoom } from '@/api/codingCollab'
import { API_BASE_URL } from '@/config/urls'
// Side effect: sets up Monaco's web workers for this page.
import './CodeEditor'
import { MONACO_LANGUAGE } from './editorConfig'
import { KIND_SNAPSHOT, KIND_UPDATE, collabSocketUrl, decodeFrame, encodeFrame } from './collabFrames'

const SNAPSHOT_DEBOUNCE_MS = 1500
const SEED_WAIT_MS = 1500
const MAX_RETRIES = 5
const REMOTE = 'remote'

type LinkState = 'connecting' | 'live' | 'reconnecting' | 'offline'

const statusText: Record<LinkState, string> = {
  connecting: 'Connecting…',
  live: 'Live. Changes sync to your partners.',
  reconnecting: 'Connection lost. Reconnecting…',
  offline: 'Offline. Your edits stay here until you reload.',
}

interface CollabEditorProps {
  room: CollabRoom
  /** Used only by the room owner, when the room has no saved text yet. */
  starterCode: string
}

/**
 * Shared Monaco editor for a pair room. The document is a Yjs text; updates
 * travel over the room socket. The latest full snapshot is stored on the server,
 * so a learner who joins later starts from the current text.
 */
export default function CollabEditor({ room, starterCode }: CollabEditorProps) {
  const hostRef = useRef<HTMLDivElement | null>(null)
  const [state, setState] = useState<LinkState>('connecting')
  const starterRef = useRef(starterCode)
  starterRef.current = starterCode

  useEffect(() => {
    if (!hostRef.current) return
    let disposed = false
    const doc = new Y.Doc()
    const ytext = doc.getText('source')
    const editor = monaco.editor.create(hostRef.current, {
      value: '',
      language: MONACO_LANGUAGE[room.language],
      automaticLayout: true,
      minimap: { enabled: false },
      fontSize: 13,
      tabSize: 4,
      scrollBeyondLastLine: false,
    })
    const model = editor.getModel()
    if (!model) {
      editor.dispose()
      return
    }
    const binding = new MonacoBinding(ytext, model, new Set([editor]))

    let socket: WebSocket | null = null
    let sawSnapshot = false
    let seeded = false
    let retries = 0
    let snapshotTimer: number | undefined
    let seedTimer: number | undefined
    let retryTimer: number | undefined

    const send = (kind: typeof KIND_UPDATE | typeof KIND_SNAPSHOT, payload: Uint8Array) => {
      if (socket && socket.readyState === WebSocket.OPEN) socket.send(encodeFrame(kind, payload))
    }
    const scheduleSnapshot = () => {
      window.clearTimeout(snapshotTimer)
      snapshotTimer = window.setTimeout(() => send(KIND_SNAPSHOT, Y.encodeStateAsUpdate(doc)), SNAPSHOT_DEBOUNCE_MS)
    }
    const onUpdate = (update: Uint8Array, origin: unknown) => {
      if (origin === REMOTE) return
      send(KIND_UPDATE, update)
      scheduleSnapshot()
    }
    doc.on('update', onUpdate)

    const connect = async () => {
      setState(retries ? 'reconnecting' : 'connecting')
      try {
        const { ticket } = await codingCollabAPI.ticket(room.id)
        if (disposed) return
        const ws = new WebSocket(collabSocketUrl(API_BASE_URL, window.location.origin, room.id, ticket))
        ws.binaryType = 'arraybuffer'
        socket = ws
        ws.onopen = () => {
          retries = 0
          setState('live')
          if (ytext.length > 0) send(KIND_SNAPSHOT, Y.encodeStateAsUpdate(doc))
          // Only the owner seeds starter code, and only if no saved text arrives.
          if (room.is_owner && !seeded) {
            seedTimer = window.setTimeout(() => {
              if (disposed || sawSnapshot || ytext.length > 0 || !starterRef.current) return
              seeded = true
              doc.transact(() => ytext.insert(0, starterRef.current))
            }, SEED_WAIT_MS)
          }
        }
        ws.onmessage = (event) => {
          const frame = decodeFrame(event.data as ArrayBuffer)
          if (!frame) return
          if (frame.kind === KIND_SNAPSHOT) sawSnapshot = true
          Y.applyUpdate(doc, frame.payload, REMOTE)
        }
        ws.onclose = (event) => {
          socket = null
          if (disposed) return
          if (event.code === 4401) {
            setState('offline')
            return
          }
          if (retries < MAX_RETRIES) {
            retries += 1
            retryTimer = window.setTimeout(() => void connect(), 1000 * 2 ** retries)
          } else {
            setState('offline')
          }
        }
      } catch {
        if (!disposed) setState('offline')
      }
    }

    void connect()

    return () => {
      disposed = true
      doc.off('update', onUpdate)
      window.clearTimeout(snapshotTimer)
      window.clearTimeout(seedTimer)
      window.clearTimeout(retryTimer)
      socket?.close()
      socket = null
      binding.destroy()
      editor.dispose()
      doc.destroy()
    }
  }, [room.id, room.language, room.is_owner])

  return (
    <div className="space-y-2">
      <p className="text-xs text-violet-200" role="status">{statusText[state]}</p>
      <div ref={hostRef} aria-label="Shared code editor" className="h-[320px] overflow-hidden rounded-xl border border-white/10" />
    </div>
  )
}
