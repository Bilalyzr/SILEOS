import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, cleanup, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import * as liveClassesApi from '@/api/liveClasses'
import StudentLiveClassJoinPage from '@/pages/student/live-class-join'

// getLiveClass is a plain function, not a vi.fn(): the spy library re-wraps every
// promise a mock returns, and reports a rejected one as a test failure even when
// the page under test handles it.
const status = vi.hoisted(() => ({
  impl: (async () => ({})) as () => Promise<unknown>,
}))

vi.mock('@/api/liveClasses', async () => {
  const actual = await vi.importActual<typeof liveClassesApi>('@/api/liveClasses')
  return { ...actual, getLiveClass: () => status.impl(), requestJoinToken: vi.fn() }
})
vi.mock('@/hooks/use-auth', () => ({ useAuth: () => ({ fullName: 'Test Student' }) }))
vi.mock('@/components/live/DevicePrecheck', () => ({
  DevicePrecheck: () => <button>Continue to class</button>,
}))
vi.mock('@/components/live/JitsiStage', () => ({ JitsiStage: () => <div data-testid="call" /> }))
vi.mock('@/components/live/LiveChallengePanel', () => ({ LiveChallengePanel: () => null }))

const classWith = (state: string, recording = 'none') => async () => ({ id: 9, title: 'Loops', status: state, recording_status: recording })

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/student/live-classes/9/join']}>
      <Routes>
        <Route path="/student/live-classes/:id/join" element={<StudentLiveClassJoinPage />} />
        <Route path="/student/live-classes" element={<div>class list</div>} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('student join page', () => {
  beforeEach(() => { status.impl = classWith('live') })
  afterEach(() => cleanup())

  it('offers the device check for a class that is live', async () => {
    renderPage()
    expect(await screen.findByRole('button', { name: 'Continue to class' })).toBeInTheDocument()
  })

  it('shows "This class has ended" and no join button for an ended class', async () => {
    status.impl = classWith('ended')
    renderPage()
    expect(await screen.findByText('This class has ended')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Continue to class' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Watch the recording' })).not.toBeInTheDocument()
  })

  it('offers the recording when one is available', async () => {
    status.impl = classWith('ended', 'available')
    renderPage()
    expect(await screen.findByRole('button', { name: 'Watch the recording' })).toBeInTheDocument()
  })

  it('says a cancelled class was cancelled', async () => {
    status.impl = classWith('cancelled')
    renderPage()
    expect(await screen.findByText('This class was cancelled')).toBeInTheDocument()
  })

  it('still offers the device check if the class status cannot be read', async () => {
    status.impl = async () => { throw new Error('network') }
    renderPage()
    await waitFor(() => expect(screen.getByRole('button', { name: 'Continue to class' })).toBeInTheDocument())
  })
})
