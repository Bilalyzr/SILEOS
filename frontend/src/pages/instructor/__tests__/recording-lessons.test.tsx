import { render, screen, fireEvent, waitFor, cleanup } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, it, expect, vi } from 'vitest'
import RecordingLessons from '../recording-lessons'
const mocks = vi.hoisted(() => ({list: vi.fn(), detail: vi.fn(), save: vi.fn(), action: vi.fn(), transcribe: vi.fn()}))
vi.mock('@/api/recording-lessons', () => ({recordingAPI: mocks}))
vi.mock('@/components/live/RecordingTranscript', () => ({default: () => <div>Transcript viewer</div>}))
vi.mock('@/api/planner', () => ({plannerError: (e: Error) => e.message}))
const work = {id: 1, class_id: 2, course_id: 3, status: 'draft', version: 1, language: 'en', title: 'Fractions', notes: 'Fractions describe equal parts of a whole.', segments: [{start: 0, end: 10, text: 'Fractions describe equal parts.'}], chapters: [{start: 0, title: 'Fractions'}], concepts: ['fractions'], question_ids: [], suggestions: [], lesson_id: null}
beforeEach(() => {vi.resetAllMocks(); mocks.list.mockResolvedValue({classes: [{class_id: 2, title: 'Fractions', status: 'draft'}], transcription: {configured: true}}); mocks.detail.mockResolvedValue({work, transcription: {configured: true}}); mocks.save.mockResolvedValue({...work, version: 2}); mocks.action.mockResolvedValue({...work, status: 'lesson_created', version: 2, lesson_id: 5, lesson_status: 'draft'})})
afterEach(cleanup)
const mount = () => render(<MemoryRouter initialEntries={['/?class_id=2']}><RecordingLessons /></MemoryRouter>)
it('requires saved corrections and explicit review before creating a draft lesson', async () => {
  mount(); const create = await screen.findByRole('button', {name: 'Create draft lesson'}); expect(create).toBeDisabled()
  fireEvent.click(screen.getByRole('checkbox')); expect(create).toBeEnabled()
  fireEvent.change(screen.getByLabelText('Lesson title'), {target: {value: 'Corrected fractions'}}); expect(create).toBeDisabled()
  fireEvent.click(screen.getByRole('button', {name: 'Save corrections'})); await waitFor(() => expect(mocks.save).toHaveBeenCalled())
  await waitFor(() => expect(screen.getByRole('checkbox')).toBeEnabled()); fireEvent.click(screen.getByRole('checkbox')); fireEvent.click(create)
  await waitFor(() => expect(mocks.action).toHaveBeenCalledWith(2, 2, 'create-lesson'))
  expect(await screen.findByRole('link', {name: 'Open course editor'})).toHaveAttribute('href', '/instructor/courses/3/edit')
})
it('shows failed processing and supports explicit retry with the current version', async () => {
  mocks.detail.mockResolvedValue({work: {...work, status: 'failed', error: 'Worker interrupted.', attempts: 1}, transcription: {configured: true}}); mocks.transcribe.mockResolvedValue({...work, status: 'queued'})
  mount(); fireEvent.click(await screen.findByRole('button', {name: 'Retry transcription'})); await waitFor(() => expect(mocks.transcribe).toHaveBeenCalledWith(2, 'auto', 1))
})
it('explains unavailable self-hosted setup and disables transcription', async () => {
  mocks.detail.mockResolvedValue({work: null, transcription: {configured: false, note: 'Install the local model.'}})
  mount(); expect(await screen.findByRole('button', {name: 'Transcribe recording'})).toBeDisabled(); expect(screen.getByText(/Install the local model/)).toBeInTheDocument()
})
