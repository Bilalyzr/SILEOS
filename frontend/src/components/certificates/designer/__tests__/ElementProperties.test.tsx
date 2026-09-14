import { describe, it, expect, vi, afterEach } from 'vitest'
import { render, screen, cleanup } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ElementProperties } from '../ElementProperties'
import type { DesignerElement } from '@/lib/certificateDesignerTypes'

vi.mock('@/api/upload', () => ({
  uploadImage: vi.fn().mockResolvedValue({
    success: true,
    file_url: '/uploads/certificates/logo.png',
    filename: 'logo.png',
    original_filename: 'logo.png',
    size: 100,
    content_type: 'image/png',
  }),
}))

afterEach(() => cleanup())

function textEl(overrides: Partial<DesignerElement> = {}): DesignerElement {
  return {
    id: 'el-1',
    type: 'text',
    x: 10,
    y: 20,
    width: 200,
    height: 40,
    z_index: 0,
    content: 'Hello',
    font_family: null,
    font_size: 24,
    font_color: '#000000',
    font_weight: 'normal',
    text_align: 'left',
    ...overrides,
  }
}

describe('ElementProperties', () => {
  it('shows a placeholder when nothing is selected', () => {
    render(<ElementProperties element={null} onChange={() => {}} />)
    expect(screen.getByText(/select an element/i)).toBeInTheDocument()
  })

  it('renders position/size/rotation/z fields for any element', () => {
    render(<ElementProperties element={textEl()} onChange={() => {}} />)
    expect(screen.getByText('X')).toBeInTheDocument()
    expect(screen.getByText('Y')).toBeInTheDocument()
    expect(screen.getByText('Width')).toBeInTheDocument()
    expect(screen.getByText('Height')).toBeInTheDocument()
    expect(screen.getByText(/rotation/i)).toBeInTheDocument()
    expect(screen.getByText(/layer/i)).toBeInTheDocument()
  })

  it('renders font/color/weight/align fields for a text element', () => {
    render(<ElementProperties element={textEl()} onChange={() => {}} />)
    expect(screen.getByText('Font')).toBeInTheDocument()
    expect(screen.getByText('Font size')).toBeInTheDocument()
    expect(screen.getByText('Text color')).toBeInTheDocument()
    expect(screen.getByText('Align')).toBeInTheDocument()
    expect(screen.getByText(/letter spacing/i)).toBeInTheDocument()
  })

  it('renders a free-text content field only for the plain "text" type', () => {
    render(<ElementProperties element={textEl({ type: 'text' })} onChange={() => {}} />)
    expect(screen.getByText(/text content/i)).toBeInTheDocument()
  })

  it('does not render a content field for a typed token like student_name', () => {
    render(<ElementProperties element={textEl({ type: 'student_name' })} onChange={() => {}} />)
    expect(screen.queryByText(/text content/i)).not.toBeInTheDocument()
    expect(screen.getByText(/typed token/i)).toBeInTheDocument()
  })

  it('renders an image src field + upload button for image elements', () => {
    render(
      <ElementProperties
        element={{ id: 'el-2', type: 'image', x: 0, y: 0, width: 100, height: 100, z_index: 0 }}
        onChange={() => {}}
      />
    )
    expect(screen.getByText(/image source/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /upload/i })).toBeInTheDocument()
  })

  it('flags an unsafe image src inline', () => {
    render(
      <ElementProperties
        element={{
          id: 'el-2',
          type: 'image',
          x: 0,
          y: 0,
          width: 100,
          height: 100,
          z_index: 0,
          image_url: 'https://attacker.example/beacon.png',
        }}
        onChange={() => {}}
      />
    )
    expect(screen.getByText(/must be an uploaded asset path/i)).toBeInTheDocument()
  })

  it('renders border editor fields for a rect element', () => {
    render(
      <ElementProperties
        element={{ id: 'el-3', type: 'rect', x: 0, y: 0, width: 100, height: 100, z_index: 0 }}
        onChange={() => {}}
      />
    )
    expect(screen.getByText(/fill color/i)).toBeInTheDocument()
    expect(screen.getByText(/corner radius/i)).toBeInTheDocument()
    expect(screen.getByText('Border')).toBeInTheDocument()
    expect(screen.getByText('Style')).toBeInTheDocument()
  })

  it('renders line color/thickness fields for a line element', () => {
    render(
      <ElementProperties
        element={{ id: 'el-4', type: 'line', x: 0, y: 0, width: 200, height: 2, z_index: 0 }}
        onChange={() => {}}
      />
    )
    expect(screen.getByText(/line color/i)).toBeInTheDocument()
    expect(screen.getByText(/thickness/i)).toBeInTheDocument()
  })

  it('renders a QR sizing note instead of editable style fields for qr_code', () => {
    render(
      <ElementProperties
        element={{ id: 'el-5', type: 'qr_code', x: 0, y: 0, width: 120, height: 120, z_index: 0 }}
        onChange={() => {}}
      />
    )
    expect(screen.getByText(/generated server-side/i)).toBeInTheDocument()
  })

  it('calls onChange when a numeric field is edited', async () => {
    const user = userEvent.setup()
    const onChange = vi.fn()
    render(<ElementProperties element={textEl()} onChange={onChange} />)
    const widthInputs = screen.getAllByDisplayValue('200')
    await user.clear(widthInputs[0])
    await user.type(widthInputs[0], '250')
    expect(onChange).toHaveBeenCalled()
  })

  it('disables inputs when disabled=true (read-only global template)', () => {
    render(<ElementProperties element={textEl()} onChange={() => {}} disabled />)
    const contentField = screen.getByText(/text content/i).parentElement?.querySelector('textarea')
    expect(contentField).toBeDisabled()
  })
})
