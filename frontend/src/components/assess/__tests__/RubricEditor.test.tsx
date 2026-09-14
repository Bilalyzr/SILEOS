import * as React from 'react'
import { describe, it, expect, afterEach } from 'vitest'
import { render, screen, cleanup } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { RubricEditor } from '../RubricEditor'
import type { RubricCriterion } from '@/lib/gradebook'

afterEach(() => cleanup())

/** Small controlled-state harness so tests can interact with the editor
 * like a real caller (assignment-builder.tsx) would — the component itself
 * takes rubric+onChange as props, no internal state. */
function Harness({ initial = [] as RubricCriterion[] }) {
  const [rubric, setRubric] = React.useState<RubricCriterion[]>(initial)
  return <RubricEditor rubric={rubric} onChange={setRubric} />
}

describe('RubricEditor', () => {
  it('renders an empty state with no criteria', () => {
    render(<Harness />)
    expect(screen.getByText(/no rubric yet/i)).toBeInTheDocument()
    expect(screen.getByText(/0\/20 criteria/i)).toBeInTheDocument()
  })

  it('adds a criterion on "Add criterion"', async () => {
    const user = userEvent.setup()
    render(<Harness />)
    await user.click(screen.getByRole('button', { name: /add criterion/i }))
    expect(screen.getByLabelText('Criterion 1 name')).toBeInTheDocument()
    expect(screen.getByText(/1\/20 criteria/i)).toBeInTheDocument()
  })

  it('renames a criterion', async () => {
    const user = userEvent.setup()
    render(<Harness initial={[{ criterion: '', max_points: 10 }]} />)
    const nameInput = screen.getByLabelText('Criterion 1 name') as HTMLInputElement
    await user.type(nameInput, 'Clarity')
    expect(nameInput.value).toBe('Clarity')
  })

  it('updates max_points and reflects the total', async () => {
    const user = userEvent.setup()
    render(<Harness initial={[{ criterion: 'Clarity', max_points: 10 }]} />)
    const pointsInput = screen.getByLabelText('Criterion 1 max points') as HTMLInputElement
    await user.clear(pointsInput)
    await user.type(pointsInput, '25')
    expect(screen.getByText(/25 pts total/i)).toBeInTheDocument()
  })

  it('removes a criterion', async () => {
    const user = userEvent.setup()
    render(
      <Harness
        initial={[
          { criterion: 'Clarity', max_points: 10 },
          { criterion: 'Correctness', max_points: 20 },
        ]}
      />
    )
    expect(screen.getByText(/2\/20 criteria/i)).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: /remove criterion 1/i }))
    expect(screen.getByText(/1\/20 criteria/i)).toBeInTheDocument()
    // Correctness should now be the sole remaining criterion.
    expect((screen.getByLabelText('Criterion 1 name') as HTMLInputElement).value).toBe('Correctness')
  })

  it('caps at 20 criteria — Add criterion disables and no 21st row appears', async () => {
    const user = userEvent.setup()
    const twenty: RubricCriterion[] = Array.from({ length: 20 }, (_, i) => ({
      criterion: `C${i + 1}`,
      max_points: 5,
    }))
    render(<Harness initial={twenty} />)
    expect(screen.getByText(/20\/20 criteria/i)).toBeInTheDocument()
    const addButton = screen.getByRole('button', { name: /add criterion/i })
    expect(addButton).toBeDisabled()
    await user.click(addButton)
    expect(screen.getByText(/20\/20 criteria/i)).toBeInTheDocument()
    expect(screen.queryByLabelText('Criterion 21 name')).not.toBeInTheDocument()
    expect(screen.getByText(/maximum of 20 criteria reached/i)).toBeInTheDocument()
  })
})
