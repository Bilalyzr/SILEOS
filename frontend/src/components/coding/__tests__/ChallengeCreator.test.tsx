import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, cleanup, fireEvent, waitFor } from '@testing-library/react'
import { codingAPI } from '@/api/coding'
import ChallengeCreator, { blankChallenge, publishProblems } from '../ChallengeCreator'

vi.mock('@/api/coding', async () => {
  const actual = await vi.importActual<typeof import('@/api/coding')>('@/api/coding')
  return { ...actual, codingAPI: { ...actual.codingAPI, create: vi.fn(), update: vi.fn(), action: vi.fn() } }
})

const api = codingAPI as unknown as Record<string, ReturnType<typeof vi.fn>>

const challenge = (status: 'draft' | 'published', version: number) => ({
  ...blankChallenge(),
  id: 11,
  course_id: 5,
  tenant_id: null,
  slug: 'sum-two',
  status,
  version,
  published_at: null,
  title: 'Sum two',
})

describe('publishProblems', () => {
  it('lists what is missing before publishing', () => {
    const problems = publishProblems(blankChallenge())
    expect(problems).toContain('Add a title of at least 3 characters.')
    expect(problems).toContain('Every test needs an expected output.')
  })

  it('requires a hidden test', () => {
    const draft = { ...blankChallenge(), title: 'Sum two', problem_statement: 'Add the two numbers given.' }
    draft.test_cases = [{ ...draft.test_cases[0], expected_output: '5' }]
    expect(publishProblems(draft)).toEqual(['Add at least one hidden test.'])
  })
})

describe('ChallengeCreator', () => {
  beforeEach(() => {
    api.create.mockReset(); api.update.mockReset(); api.action.mockReset()
  })
  afterEach(() => cleanup())

  function fillValid() {
    fireEvent.change(screen.getByLabelText('Title'), { target: { value: 'Sum two' } })
    fireEvent.change(screen.getByLabelText('Problem statement'), { target: { value: 'Read two integers and print the sum.' } })
    fireEvent.change(screen.getByLabelText('Test 1 expected output'), { target: { value: '5' } })
    fireEvent.change(screen.getByLabelText('Test 2 expected output'), { target: { value: '42' } })
  }

  it('shows what is missing and does not call the API', async () => {
    render(<ChallengeCreator courseId={5} onClose={() => {}} onCreated={() => {}} />)
    fireEvent.click(screen.getByRole('button', { name: 'Create and publish' }))
    expect(await screen.findByText('Add a title of at least 3 characters.')).toBeInTheDocument()
    expect(api.create).not.toHaveBeenCalled()
  })

  it('creates, publishes and hands back the published challenge', async () => {
    api.create.mockResolvedValue(challenge('draft', 1))
    api.action.mockResolvedValue(challenge('published', 2))
    const onCreated = vi.fn()
    render(<ChallengeCreator courseId={5} onClose={() => {}} onCreated={onCreated} />)
    fillValid()
    fireEvent.click(screen.getByRole('button', { name: 'Create and publish' }))
    await waitFor(() => expect(onCreated).toHaveBeenCalledWith(expect.objectContaining({ status: 'published' })))
    expect(api.create).toHaveBeenCalledWith(5, expect.objectContaining({ title: 'Sum two' }))
    expect(api.action).toHaveBeenCalledWith(11, 1, 'publish')
  })

  it('retries publishing the saved draft instead of creating a second one', async () => {
    api.create.mockResolvedValue(challenge('draft', 1))
    api.action.mockRejectedValueOnce(new Error('network'))
    api.update.mockResolvedValue(challenge('draft', 2))
    api.action.mockResolvedValueOnce(challenge('published', 3))
    const onCreated = vi.fn()
    render(<ChallengeCreator courseId={5} onClose={() => {}} onCreated={onCreated} />)
    fillValid()
    fireEvent.click(screen.getByRole('button', { name: 'Create and publish' }))
    await screen.findByText('This request could not be completed. Please try again.')
    fireEvent.click(screen.getByRole('button', { name: 'Create and publish' }))
    await waitFor(() => expect(onCreated).toHaveBeenCalled())
    expect(api.create).toHaveBeenCalledTimes(1)
    expect(api.update).toHaveBeenCalledWith(11, expect.objectContaining({ version: 1 }))
    expect(api.action).toHaveBeenLastCalledWith(11, 2, 'publish')
  })
})
