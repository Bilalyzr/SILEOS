import { create } from 'zustand'

/**
 * Live-class in-session state — participants, raise-hand, recording status,
 * connection status — populated by JitsiStage's IFrame API event wiring
 * (videoConferenceJoined/participantJoined/participantLeft/
 * endpointTextMessageReceived/recordingStatusChanged/readyToClose/
 * errorOccurred, per the plan's binding behavior for Task 7).
 *
 * Deliberately NOT React Query: this is live, event-driven, in-memory
 * session state for the single active JitsiStage instance, not server data
 * to be cached/revalidated — matches the repo's other Zustand stores
 * (store/course.ts, store/cartStore.ts) in shape and style.
 */

export interface LiveParticipant {
  participantId: string
  displayName: string
  raisedHand?: boolean
}

export type ConnectionStatus = 'idle' | 'connecting' | 'connected' | 'error' | 'left'

interface LiveClassState {
  // Session identity
  classId: number | null
  roomName: string | null
  isModerator: boolean

  // Connection
  connectionStatus: ConnectionStatus
  errorMessage: string | null

  // Participants
  participants: Record<string, LiveParticipant>
  raisedHands: string[]

  // Recording (mirrors Jitsi's recordingStatusChanged event; independent of
  // the server-truth `recording_status` on LiveClassOut, which is intent-only)
  isRecording: boolean

  // Actions
  startSession: (params: { classId: number; roomName: string; isModerator: boolean }) => void
  setConnectionStatus: (status: ConnectionStatus, errorMessage?: string | null) => void
  participantJoined: (participant: LiveParticipant) => void
  participantLeft: (participantId: string) => void
  setRaisedHand: (participantId: string, raised: boolean) => void
  setRecording: (isRecording: boolean) => void
  resetSession: () => void
}

const initialSessionState = {
  classId: null as number | null,
  roomName: null as string | null,
  isModerator: false,
  connectionStatus: 'idle' as ConnectionStatus,
  errorMessage: null as string | null,
  participants: {} as Record<string, LiveParticipant>,
  raisedHands: [] as string[],
  isRecording: false,
}

export const useLiveClassStore = create<LiveClassState>((set, get) => ({
  ...initialSessionState,

  startSession: ({ classId, roomName, isModerator }) => {
    set({
      ...initialSessionState,
      classId,
      roomName,
      isModerator,
      connectionStatus: 'connecting',
    })
  },

  setConnectionStatus: (status, errorMessage = null) => {
    set({ connectionStatus: status, errorMessage })
  },

  participantJoined: (participant) => {
    const { participants } = get()
    set({
      participants: { ...participants, [participant.participantId]: participant },
    })
  },

  participantLeft: (participantId) => {
    const { participants, raisedHands } = get()
    const next = { ...participants }
    delete next[participantId]
    set({
      participants: next,
      raisedHands: raisedHands.filter((id) => id !== participantId),
    })
  },

  setRaisedHand: (participantId, raised) => {
    const { raisedHands } = get()
    if (raised) {
      if (raisedHands.includes(participantId)) return
      set({ raisedHands: [...raisedHands, participantId] })
    } else {
      set({ raisedHands: raisedHands.filter((id) => id !== participantId) })
    }
  },

  setRecording: (isRecording) => set({ isRecording }),

  resetSession: () => set({ ...initialSessionState }),
}))
