import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import SchoolWorkspace from '../school-workspace'
import { api } from '@/api/axios'

const state = vi.hoisted(() => ({user: {id: 1, role: 'student'}}))
vi.mock('@/store/auth', () => ({useAuthStore: (select: (s: typeof state) => unknown) => select(state)}))
vi.mock('@/api/axios', () => ({api: {get: vi.fn(), post: vi.fn(), delete: vi.fn()}}))
const chapter = {id: 'ch1', grade: 6, subject: 'math', edition: 'ncert-2024', title: 'Geometry', alignment: 'Needs edition review', coverage: 'content_needed', labs: [], courses: []}
function mount() {render(<QueryClientProvider client={new QueryClient({defaultOptions:{queries:{retry:false}}})}><MemoryRouter><SchoolWorkspace /></MemoryRouter></QueryClientProvider>)}
beforeEach(() => {
  vi.clearAllMocks(); state.user.role = 'student'
  vi.mocked(api.get).mockResolvedValue({data:{chapters:[chapter, {...chapter,id:'ch2',grade:12,title:'Calculus'}],courses:[],notice:'Coverage is incomplete'}})
})
afterEach(cleanup)
it('offers seven classes without inventing content or exposing author controls', async () => {
  mount(); await screen.findByText('Geometry')
  expect(screen.getAllByRole('button', {name:/^Class /})).toHaveLength(7)
  expect(screen.getByText('No published resource mapped yet.')).toBeTruthy()
  expect(screen.queryByText('Link / re-review course')).toBeNull()
  fireEvent.click(screen.getByRole('button',{name:'Class 12'}))
  expect(screen.getByText('Calculus')).toBeTruthy()
  expect(screen.queryByText('Geometry')).toBeNull()
})
it('submits a reviewed mapping only for editable courses', async () => {
  state.user.role = 'instructor'
  vi.mocked(api.get).mockResolvedValue({data:{chapters:[chapter],courses:[{id:42,title:'Published geometry',editable:true}],notice:'Review required'}})
  vi.mocked(api.post).mockResolvedValue({data:{id:1}})
  mount(); fireEvent.click(await screen.findByText('Link / re-review course'))
  fireEvent.change(screen.getByLabelText('Review evidence'), {target:{value:'Reviewed the geometry chapter coverage.'}})
  fireEvent.click(screen.getByRole('button',{name:'Save reviewed mapping'}))
  await waitFor(() => expect(api.post).toHaveBeenCalledWith('/curriculum-workspace/links',{chapter_key:'ch1',course_id:42,note:'Reviewed the geometry chapter coverage.'}))
  expect(await screen.findByText('Saved. The catalogue is up to date.')).toBeTruthy()
})
