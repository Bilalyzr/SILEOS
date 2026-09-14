import { render, screen, fireEvent, waitFor, within, cleanup } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import AssessmentStudio from '../assessment-studio'

const mocks = vi.hoisted(() => ({ courses: vi.fn(), detail: vi.fn(), banks: vi.fn(), save: vi.fn(), action: vi.fn(), link: vi.fn(), import: vi.fn() }))
vi.mock('@/api/assessment-studio', () => ({ studioAPI: mocks }))
vi.mock('@/api/planner', () => ({ plannerError: (e: Error) => e.message }))
const question = { id: 9, bank_question_id: 4, title: 'Which fraction equals one half?', type: 'multiple_choice', options: ['2/4', '3/4'], answer: 0, explanation: 'Divide both parts by two.', difficulty: 'medium', concept: 'fractions', purpose: 'practice', status: 'draft', version: 1, history: [] }
const base = { course_id: 1, questions: [], lessons: [{ id: 4, title: 'Fractions lesson', published: true, concepts: [] }], live_questions: [], concepts: [{ concept: 'fractions', lessons: 1, practice_questions: 0, reserved_followups: 0, practice_ready: false, followup_ready: false, needs_support: 1, outcomes: { interventions: 1, completed_checks: 0, graded_questions: 0, valid_followups: 0, followups_passed: 0, paired_learners: 0, mean_practice_to_followup_change: null } }] }
const mount = () => render(<MemoryRouter initialEntries={['/instructor/assessment-studio?course_id=1&concept=fractions']}><AssessmentStudio /></MemoryRouter>)
beforeEach(() => { vi.resetAllMocks(); mocks.courses.mockResolvedValue([{ id: 1, title: 'Maths' }]); mocks.banks.mockResolvedValue([]); mocks.detail.mockResolvedValue(base); mocks.save.mockResolvedValue(question); mocks.action.mockResolvedValue(question) })
afterEach(cleanup)

describe('Assessment Studio', () => {
  it('shows real coverage gaps and keeps unknown outcome evidence explicit', async () => {
    mount()
    expect(await screen.findByRole('button', { name: 'Fix this gap' })).toBeInTheDocument()
    expect(screen.getAllByText('0 · Needs questions')).toHaveLength(2)
    fireEvent.click(screen.getByRole('button', { name: 'outcomes' }))
    expect(screen.getByText('Not enough evidence')).toBeInTheDocument()
  })
  it('requires an explicit review note while showing the correct option and explanation', async () => {
    mocks.detail.mockResolvedValue({ ...base, questions: [question] }); mount()
    await screen.findByRole('button', { name: 'Create question' })
    fireEvent.click(screen.getByRole('button', { name: 'questions' }))
    fireEvent.click(screen.getByRole('button', { name: 'Review question' }))
    const dialog = screen.getByRole('dialog')
    expect(within(dialog).getByText('1. 2/4 — Correct')).toBeInTheDocument()
    expect(within(dialog).getByRole('button', { name: 'Approve review' })).toBeDisabled()
    fireEvent.change(within(dialog).getByLabelText('Decision note'), { target: { value: 'Checked the fraction and explanation.' } })
    fireEvent.click(within(dialog).getByRole('button', { name: 'Approve review' }))
    await waitFor(() => expect(mocks.action).toHaveBeenCalledWith(9, 1, 'review', 'Checked the fraction and explanation.'))
  })
  it('saves a draft without publishing it and preserves the selected concept', async () => {
    mount(); await screen.findByRole('button', { name: 'Create question' })
    fireEvent.click(screen.getByRole('button', { name: 'Create question' }))
    const dialog = screen.getByRole('dialog')
    expect(within(dialog).getByLabelText('Concept')).toHaveValue('fractions')
    fireEvent.change(within(dialog).getByLabelText('Question', { exact: true }), { target: { value: 'What equals one half?' } })
    fireEvent.change(within(dialog).getByLabelText('Options (one per line)'), { target: { value: '2/4\n3/4' } })
    fireEvent.change(within(dialog).getByLabelText('Answer explanation'), { target: { value: 'Divide both parts by two.' } })
    fireEvent.click(within(dialog).getByRole('button', { name: 'Save draft' }))
    await waitFor(() => expect(mocks.save).toHaveBeenCalledWith(1, expect.objectContaining({ concept: 'fractions', options: ['2/4', '3/4'], answer: 0 }), undefined))
    expect(mocks.action).not.toHaveBeenCalled()
  })
  it('retains the review dialog when publication has a version conflict', async () => {
    mocks.detail.mockResolvedValue({ ...base, questions: [{ ...question, status: 'reviewed', version: 2 }] }); mocks.action.mockRejectedValue(new Error('This question changed. Refresh before reviewing or saving.')); mount()
    await screen.findByRole('button', { name: 'Create question' }); fireEvent.click(screen.getByRole('button', { name: 'questions' })); fireEvent.click(screen.getByRole('button', { name: 'Publish practice' }))
    const dialog = screen.getByRole('dialog'); fireEvent.change(within(dialog).getByLabelText('Decision note'), { target: { value: 'Ready for practice.' } }); fireEvent.click(within(dialog).getByRole('button', { name: 'Publish question' }))
    await waitFor(() => expect(within(screen.getByRole('dialog')).getByRole('alert')).toHaveTextContent('This question changed'))
  })
})
