import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, act, cleanup } from '@testing-library/react'
import { JitsiStage } from '../JitsiStage'
import * as liveClassesApi from '@/api/liveClasses'

// Mock the heartbeat API module — the test asserts the exact call count and
// args around unmount without hitting the network.
vi.mock('@/api/liveClasses', async () => {
  const actual = await vi.importActual<typeof liveClassesApi>('@/api/liveClasses')
  return {
    ...actual,
    sendHeartbeat: vi.fn().mockResolvedValue({ accumulated_seconds: 60, delta: 60 }),
  }
})

const sendHeartbeatMock = liveClassesApi.sendHeartbeat as unknown as ReturnType<typeof vi.fn>

/** Flushes the microtask queue (the `loadExternalApiScript(...).then(...)`
 * chain JitsiStage's effect awaits) under fake timers, where
 * @testing-library's `waitFor` cannot poll because its own setTimeout-based
 * retries are faked too. */
async function flushMicrotasks() {
  await act(async () => {
    await Promise.resolve()
    await Promise.resolve()
  })
}

/** Captures constructor calls so tests can assert on the exact config passed
 * to JitsiMeetExternalAPI. Mimics the real class's addEventListener/dispose
 * surface used by JitsiStage. */
class MockJitsiMeetExternalAPI {
  static instances: MockJitsiMeetExternalAPI[] = []
  domain: string
  options: any
  listeners: Record<string, Array<(event: any) => void>> = {}
  dispose = vi.fn()

  constructor(domain: string, options: any) {
    this.domain = domain
    this.options = options
    MockJitsiMeetExternalAPI.instances.push(this)
  }

  addEventListener(event: string, cb: (event: any) => void) {
    this.listeners[event] = this.listeners[event] || []
    this.listeners[event].push(cb)
  }

  emit(event: string, payload: any = {}) {
    (this.listeners[event] || []).forEach((cb) => cb(payload))
  }
}

describe('JitsiStage', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    MockJitsiMeetExternalAPI.instances = []
    sendHeartbeatMock.mockClear()
    ;(window as any).JitsiMeetExternalAPI = MockJitsiMeetExternalAPI
    // Script is already "loaded" since window.JitsiMeetExternalAPI exists —
    // loadExternalApiScript resolves synchronously via Promise.resolve() in
    // that branch, so no need to fake a <script> load event.
  })

  afterEach(() => {
    cleanup()
    vi.useRealTimers()
    delete (window as any).JitsiMeetExternalAPI
    // Reset any script tags injected by a prior test run.
    document.querySelectorAll('script[data-jitsi-external-api]').forEach((el) => el.remove())
  })

  it('constructs JitsiMeetExternalAPI with the jwt and roomName', async () => {
    render(
      <JitsiStage
        jitsiUrl="https://live.example.com"
        roomName="si-abc12345"
        jwt="test-jwt-token"
        isModerator={false}
        displayName="Test Student"
        classId={42}
        onLeft={() => {}}
      />
    )

    await flushMicrotasks()
    expect(MockJitsiMeetExternalAPI.instances.length).toBe(1)

    const instance = MockJitsiMeetExternalAPI.instances[0]
    expect(instance.options.roomName).toBe('si-abc12345')
    expect(instance.options.jwt).toBe('test-jwt-token')
    expect(instance.options.userInfo.displayName).toBe('Test Student')
    // Student config: muted by default, restricted toolbar (no recording/desktop).
    expect(instance.options.configOverwrite.startWithAudioMuted).toBe(true)
    expect(instance.options.configOverwrite.toolbarButtons).not.toContain('recording')
  })

  it('gives the moderator an expanded toolbar (desktop/recording/mute-everyone)', async () => {
    render(
      <JitsiStage
        jitsiUrl="https://live.example.com"
        roomName="si-mod12345"
        jwt="mod-jwt"
        isModerator
        displayName="Instructor"
        classId={7}
        onLeft={() => {}}
      />
    )

    await flushMicrotasks()
    expect(MockJitsiMeetExternalAPI.instances.length).toBe(1)

    const instance = MockJitsiMeetExternalAPI.instances[0]
    expect(instance.options.configOverwrite.startWithAudioMuted).toBe(false)
    expect(instance.options.configOverwrite.toolbarButtons).toEqual(
      expect.arrayContaining(['desktop', 'whiteboard', 'recording', 'mute-everyone'])
    )
  })

  it('sends a heartbeat every 60s while mounted', async () => {
    render(
      <JitsiStage
        jitsiUrl="https://live.example.com"
        roomName="si-hb00001"
        jwt="jwt"
        isModerator={false}
        displayName="Student"
        classId={99}
        onLeft={() => {}}
      />
    )

    await flushMicrotasks()
    expect(MockJitsiMeetExternalAPI.instances.length).toBe(1)

    expect(sendHeartbeatMock).not.toHaveBeenCalled()

    await vi.advanceTimersByTimeAsync(60_000)
    expect(sendHeartbeatMock).toHaveBeenCalledTimes(1)
    expect(sendHeartbeatMock).toHaveBeenCalledWith(99)

    await vi.advanceTimersByTimeAsync(60_000)
    expect(sendHeartbeatMock).toHaveBeenCalledTimes(2)
  })

  it('stops retrying the heartbeat interval once the server returns 409 (class ended)', async () => {
    render(
      <JitsiStage
        jitsiUrl="https://live.example.com"
        roomName="si-ended001"
        jwt="jwt"
        isModerator={false}
        displayName="Student"
        classId={17}
        onLeft={() => {}}
      />
    )

    await flushMicrotasks()
    expect(MockJitsiMeetExternalAPI.instances.length).toBe(1)

    sendHeartbeatMock.mockRejectedValue({ response: { status: 409 } })

    await vi.advanceTimersByTimeAsync(60_000)
    expect(sendHeartbeatMock).toHaveBeenCalledTimes(1)

    // The interval must have been cleared after the terminal 409 — advancing
    // well past further tick boundaries must not produce any more calls.
    await vi.advanceTimersByTimeAsync(180_000)
    expect(sendHeartbeatMock).toHaveBeenCalledTimes(1)
  })

  it('stops retrying the heartbeat interval once the server returns 403 (access revoked)', async () => {
    render(
      <JitsiStage
        jitsiUrl="https://live.example.com"
        roomName="si-revoked01"
        jwt="jwt"
        isModerator={false}
        displayName="Student"
        classId={18}
        onLeft={() => {}}
      />
    )

    await flushMicrotasks()
    expect(MockJitsiMeetExternalAPI.instances.length).toBe(1)

    sendHeartbeatMock.mockRejectedValue({ response: { status: 403 } })

    await vi.advanceTimersByTimeAsync(60_000)
    expect(sendHeartbeatMock).toHaveBeenCalledTimes(1)

    await vi.advanceTimersByTimeAsync(180_000)
    expect(sendHeartbeatMock).toHaveBeenCalledTimes(1)
  })

  it('keeps retrying the heartbeat interval on a transient (non-terminal) error', async () => {
    render(
      <JitsiStage
        jitsiUrl="https://live.example.com"
        roomName="si-flaky0001"
        jwt="jwt"
        isModerator={false}
        displayName="Student"
        classId={19}
        onLeft={() => {}}
      />
    )

    await flushMicrotasks()
    expect(MockJitsiMeetExternalAPI.instances.length).toBe(1)

    sendHeartbeatMock.mockRejectedValue(new Error('network error'))

    await vi.advanceTimersByTimeAsync(60_000)
    expect(sendHeartbeatMock).toHaveBeenCalledTimes(1)

    // A plain network error is not terminal — the next tick still fires.
    await vi.advanceTimersByTimeAsync(60_000)
    expect(sendHeartbeatMock).toHaveBeenCalledTimes(2)
  })

  it('on unmount: clears the interval, sends exactly one final heartbeat, and calls dispose', async () => {
    const { unmount } = render(
      <JitsiStage
        jitsiUrl="https://live.example.com"
        roomName="si-unmount1"
        jwt="jwt"
        isModerator={false}
        displayName="Student"
        classId={5}
        onLeft={() => {}}
      />
    )

    await flushMicrotasks()
    expect(MockJitsiMeetExternalAPI.instances.length).toBe(1)
    const instance = MockJitsiMeetExternalAPI.instances[0]

    sendHeartbeatMock.mockClear()

    unmount()

    expect(instance.dispose).toHaveBeenCalledTimes(1)
    expect(sendHeartbeatMock).toHaveBeenCalledTimes(1)
    expect(sendHeartbeatMock).toHaveBeenCalledWith(5)

    // Advancing timers after unmount must not produce any further heartbeats
    // — the interval was cleared before the final beat was sent.
    await vi.advanceTimersByTimeAsync(120_000)
    expect(sendHeartbeatMock).toHaveBeenCalledTimes(1)
  })

  it('calls onLeft when the readyToClose event fires', async () => {
    const onLeft = vi.fn()
    render(
      <JitsiStage
        jitsiUrl="https://live.example.com"
        roomName="si-leave001"
        jwt="jwt"
        isModerator={false}
        displayName="Student"
        classId={11}
        onLeft={onLeft}
      />
    )

    await flushMicrotasks()
    expect(MockJitsiMeetExternalAPI.instances.length).toBe(1)
    const instance = MockJitsiMeetExternalAPI.instances[0]

    act(() => {
      instance.emit('readyToClose')
    })

    expect(onLeft).toHaveBeenCalledTimes(1)
  })

  it('shows a retryable error panel when errorOccurred fires', async () => {
    render(
      <JitsiStage
        jitsiUrl="https://live.example.com"
        roomName="si-err00001"
        jwt="jwt"
        isModerator={false}
        displayName="Student"
        classId={3}
        onLeft={() => {}}
      />
    )

    await flushMicrotasks()
    expect(MockJitsiMeetExternalAPI.instances.length).toBe(1)
    const instance = MockJitsiMeetExternalAPI.instances[0]

    act(() => {
      instance.emit('errorOccurred', { error: { message: 'connection lost' } })
    })

    expect(screen.getByText(/couldn't connect/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /retry/i })).toBeInTheDocument()
  })
})
