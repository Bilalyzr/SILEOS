import { render, screen, fireEvent, cleanup } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import RecordingTranscript from '../RecordingTranscript'
const mocks = vi.hoisted(() => ({get: vi.fn()}))
vi.mock('@/api/axios', () => ({api: mocks}))
vi.mock('@/api/planner', () => ({plannerError: (e: Error) => e.message}))
vi.mock('@/components/video/native-video-player', () => ({NativeVideoPlayer: () => <div>Recording player</div>}))
afterEach(cleanup)
it('searches the transcript and retains notes when playback is unavailable', async () => {
  mocks.get.mockRejectedValue(new Error('No recording is available for this class'))
  render(<RecordingTranscript classId={16} chapters={[{start: 0, title: 'Fractions'}]} segments={[{start: 0, end: 5, text: 'Fractions describe equal parts.'}, {start: 6, end: 10, text: 'Tamil transcript search also works: தமிழ்'}]} />)
  fireEvent.change(screen.getByLabelText('Search transcript'), {target: {value: 'தமிழ்'}})
  expect(screen.getByText('Tamil transcript search also works: தமிழ்')).toBeInTheDocument()
  expect(screen.queryByText('Fractions describe equal parts.')).not.toBeInTheDocument()
  fireEvent.click(screen.getByRole('button', {name: 'Jump to 0:06'}))
  expect(await screen.findByRole('alert')).toHaveTextContent('Transcript and notes remain available.')
  expect(mocks.get).toHaveBeenCalledWith('/live/classes/16/recording-playback')
})
