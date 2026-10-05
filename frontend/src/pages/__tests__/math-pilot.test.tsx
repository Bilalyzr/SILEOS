import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import MathDiscovery from '../math-discovery'
import MathPilotPage from '../student/math-pilot'
import MathPilotTeacher from '../instructor/math-pilot'
import { mathPilot, type MathData, type MathSession } from '@/api/math-pilot'

vi.mock('@/api/math-pilot', () => ({ mathPilot: { me: vi.fn(), start: vi.fn(), answer: vi.fn(), review: vi.fn(), evidence: vi.fn(), approve: vi.fn(), pause: vi.fn(), override: vi.fn(), export: vi.fn(), remove: vi.fn() } }))
vi.mock('@/api/planner', () => ({ plannerError: () => 'Request failed. Retry safely.' }))
const row: MathSession = { id: 1, course_id: 2, version: 'v'.repeat(64), sequence: 0, stage: 'predict', due_at: null,
  expires_at: '2027-01-01T00:00:00Z', hypothesis_note: null, intervention: null, explanation: null, notice: 'Pilot evidence only.',
  transfer_score: null, retention_score: null, task: { prompt: 'What happens when height doubles?', options: ['Same', 'Doubles', 'Plus two', 'Four times'] } }
const data: MathData = { catalog: { version: row.version, topic: 'Volume', notice: 'Pilot' }, courses: [{ id: 2, title: 'Volume class', approved: true }], sessions: [] }
beforeEach(() => {
  vi.clearAllMocks()
  vi.mocked(mathPilot.me).mockResolvedValue(data)
  vi.mocked(mathPilot.start).mockResolvedValue(row)
  vi.mocked(mathPilot.review).mockResolvedValue({ version: row.version, material: { topic: 'Volume', key: [24] }, approved: false, review_note: null })
  vi.mocked(mathPilot.evidence).mockResolvedValue({ items: [], notice: 'Descriptive only.' })
})
afterEach(cleanup)
it('public explorer updates cubes without recording learning data', () => {
  render(<MemoryRouter><MathDiscovery /></MemoryRouter>)
  expect(screen.getByRole('img').getAttribute('aria-label')).toContain('12 unit cubes')
  fireEvent.change(screen.getByRole('slider'), { target: { value: '4' } })
  expect(screen.getByRole('img').getAttribute('aria-label')).toContain('24 unit cubes')
  expect(mathPilot.me).not.toHaveBeenCalled()
  expect(mathPilot.answer).not.toHaveBeenCalled()
  expect(screen.getByText(/Sharing is optional/)).toBeTruthy()
})
it('requires learner acknowledgement and submits a server-versioned prediction', async () => {
  vi.mocked(mathPilot.answer).mockResolvedValue({ ...row, sequence: 1, stage: 'diagnose', task: { prompt: 'Count', questions: ['One layer?', 'All layers?'] } })
  render(<MemoryRouter><MathPilotPage /></MemoryRouter>)
  const start = await screen.findByRole('button', { name: 'Start or resume' })
  expect((start as HTMLButtonElement).disabled).toBe(true)
  fireEvent.click(screen.getByRole('checkbox'))
  fireEvent.click(start)
  fireEvent.click(await screen.findByLabelText('Doubles'))
  fireEvent.click(screen.getByRole('button', { name: 'Save and continue' }))
  await waitFor(() => expect(mathPilot.answer).toHaveBeenCalledWith(row, [1], expect.any(String)))
  expect(await screen.findByLabelText('One layer?')).toBeTruthy()
  expect(screen.queryByRole('slider')).toBeNull()
})
it('hides cube helper and submission while waiting for retention', async () => {
  vi.mocked(mathPilot.start).mockResolvedValue({ ...row, stage: 'waiting', transfer_score: 1, due_at: '2027-01-01T00:00:00Z', task: {} })
  render(<MemoryRouter><MathPilotPage /></MemoryRouter>)
  await screen.findByRole('checkbox')
  fireEvent.click(screen.getByRole('checkbox'))
  fireEvent.click(screen.getByRole('button', { name: 'Start or resume' }))
  expect(await screen.findByText('Let the learning settle.')).toBeTruthy()
  expect(screen.queryByRole('slider')).toBeNull()
  expect(screen.queryByRole('button', { name: 'Save and continue' })).toBeNull()
})
it('educator approval needs both reviews and a meaningful note', async () => {
  render(<MemoryRouter><MathPilotTeacher /></MemoryRouter>)
  const approve = await screen.findByRole('button', { name: 'Approve this version' })
  expect((approve as HTMLButtonElement).disabled).toBe(true)
  screen.getAllByRole('checkbox').forEach(box => fireEvent.click(box))
  fireEvent.change(screen.getByRole('textbox'), { target: { value: 'Reviewed with classroom teacher.' } })
  fireEvent.click(approve)
  await waitFor(() => expect(mathPilot.approve).toHaveBeenCalledWith(2, row.version, 'Reviewed with classroom teacher.'))
})
it('retrying an uncertain answer reuses its request key', async () => {
  vi.mocked(mathPilot.answer).mockRejectedValue(new Error('network interrupted'))
  render(<MemoryRouter><MathPilotPage /></MemoryRouter>)
  await screen.findByRole('checkbox'); fireEvent.click(screen.getByRole('checkbox'))
  fireEvent.click(screen.getByRole('button', { name: 'Start or resume' }))
  fireEvent.click(await screen.findByLabelText('Doubles'))
  fireEvent.click(screen.getByRole('button', { name: 'Save and continue' }))
  await screen.findByRole('alert')
  fireEvent.click(screen.getByRole('button', { name: 'Save and continue' }))
  await waitFor(() => expect(mathPilot.answer).toHaveBeenCalledTimes(2))
  const calls = vi.mocked(mathPilot.answer).mock.calls
  expect(calls[0][2]).toBe(calls[1][2])
})
