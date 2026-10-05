import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '@/api/axios'
import { useAuthStore } from '@/store/auth'
import { roleHomePath } from '@/utils/role-routing'
import '@/styles/school-workspace.css'

interface Chapter {
  id: string; grade: number; subject: string; title: string; edition: string; alignment: string;
  coverage: string; labs: {slug: string; title: string}[];
  courses: {link_id: number; title: string; url: string; ready: boolean; editable: boolean; enrolled: boolean}[];
}
interface Catalogue {chapters: Chapter[]; courses: {id: number; title: string; editable: boolean}[]; notice: string}

export default function SchoolWorkspace() {
  const user = useAuthStore(s => s.user)
  const cache = useQueryClient()
  const [grade, setGrade] = useState(6)
  const [subject, setSubject] = useState('all')
  const [edition, setEdition] = useState('ncert-2024')
  const [query, setQuery] = useState('')
  const [selected, setSelected] = useState<Chapter | null>(null)
  const [message, setMessage] = useState('')
  const [busy, setBusy] = useState(false)
  const catalogue = useQuery({queryKey: ['school-workspace', user?.id], queryFn: async () => (await api.get<Catalogue>('/curriculum-workspace')).data})
  const data = catalogue.data
  const chapters = data?.chapters || []
  const editable = data?.courses.filter(c => c.editable) || []
  const shown = chapters.filter(c => c.grade === grade && c.edition === edition && (subject === 'all' || c.subject === subject) && c.title.toLowerCase().includes(query.toLowerCase()))
  async function save(action: () => Promise<unknown>) {
    setBusy(true); setMessage('')
    try { await action(); await cache.invalidateQueries({queryKey: ['school-workspace']}); setSelected(null); setMessage('Saved. The catalogue is up to date.') }
    catch { setMessage('Could not save. Check your permissions and ensure the course and at least one lesson are published. Chapter references must use an official CBSE or NCERT URL.') }
    finally { setBusy(false) }
  }
  return <main className="school-workspace">
    <header className="school-hero"><Link to={roleHomePath(user?.role)}>SASHA INFINITY / LEARNING OS · Dashboard</Link><p>Connected learning · Classes 6–12</p><h1>Your class. Your learning journey.</h1><p>Find courses, explore concepts in a lab, and keep learning in one connected workspace.</p></header>
    <nav className="school-destinations" aria-label="Connected workspaces">
      <Link to="/labs"><strong>Meiporul</strong><span>Interactive labs & discovery →</span></Link>
      <Link to="/institutions"><strong>Seyappaduporul</strong><span>Institution workspace →</span></Link>
      <Link to="/courses"><strong>Utporul</strong><span>Courses & skills →</span></Link>
    </nav>
    <section className="school-panel"><h2>Choose your classroom</h2><div className="school-grades" role="group" aria-label="Class">{[6,7,8,9,10,11,12].map(n => <button key={n} aria-pressed={grade === n} onClick={() => {setGrade(n); setSubject('all')}}>Class {n}</button>)}</div>
      <div className="school-filters"><label>Curriculum map<select value={edition} onChange={e => {setEdition(e.target.value); setSubject('all')}}>{Array.from(new Set(['ncert-2024', ...chapters.map(c => c.edition)])).map(e => <option key={e} value={e}>{e === 'ncert-2024' ? 'Supplied NCERT 2024–25 map' : e}</option>)}</select></label>
      <label>Subject<select value={subject} onChange={e => setSubject(e.target.value)}><option value="all">All available subjects</option>{Array.from(new Set(chapters.filter(c => c.grade === grade && c.edition === edition).map(c => c.subject))).sort().map(s => <option key={s}>{s}</option>)}</select></label>
      <label>Find a chapter<input value={query} onChange={e => setQuery(e.target.value)} placeholder="Search chapter titles" /></label></div>
      <p className="school-notice">{data?.notice || 'Only real published resources are shown. Content coverage and syllabus alignment need educator review.'}</p>
      {catalogue.isLoading && <p role="status">Loading your curriculum…</p>}
      {catalogue.isError && <p role="alert">Cannot load the catalogue. <button onClick={() => catalogue.refetch()}>Retry</button></p>}
      {data && <p>{shown.length} chapter references · {shown.filter(c => c.coverage === 'linked_course').length} with reviewed course mappings · {shown.filter(c => c.labs.length).length} with activities</p>}
    </section>
    <p role="status">{message}</p>
    {selected && <section className="school-panel"><h2>Review course mapping: {selected.title}</h2><p>Confirm the published course teaches this chapter. Editing its lesson content will require re-review. This does not grant enrolment.</p><form onSubmit={e => {e.preventDefault(); const f = new FormData(e.currentTarget); void save(() => api.post('/curriculum-workspace/links', {chapter_key: selected.id, course_id: Number(f.get('course')), note: f.get('note')}))}}>
      <label>Course<select name="course" required>{editable.map(c => <option key={c.id} value={c.id}>{c.title}</option>)}</select></label><label>Review evidence<textarea name="note" required minLength={10} maxLength={2000} placeholder="Explain chapter coverage and limitations" /></label><button disabled={busy}>Save reviewed mapping</button> <button type="button" onClick={() => setSelected(null)}>Cancel</button>
    </form></section>}
    <section className="school-chapters" aria-label="Chapter resources">{shown.map(c => <article key={c.id}><p className="school-eyebrow">CLASS {c.grade} / {c.subject}</p><h2>{c.title}</h2><span className="school-badge">{c.coverage === 'linked_course' ? 'Reviewed course mapping' : c.coverage === 'activity_only' ? 'Activity available · course needed' : 'Content needed'}</span><p className="school-notice">{c.alignment}</p>
      {c.courses.map(course => <div key={course.link_id}>{course.ready ? <Link to={course.url}>{course.enrolled ? 'Continue' : 'View course'}: {course.title} →</Link> : <p>{course.title} — changed since review</p>}{course.editable && <button disabled={busy} onClick={() => void save(() => api.delete(`/curriculum-workspace/links/${course.link_id}`))}>Unlink mapping</button>}</div>)}
      {c.labs.map(l => <Link key={l.slug} to={`/labs/${l.slug}`}>Explore: {l.title} →</Link>)}
      {c.coverage === 'content_needed' && <p>No published resource mapped yet.</p>}
      {editable.length > 0 && <button onClick={() => setSelected(c)}>Link / re-review course</button>}
    </article>)}</section>
    {data && !shown.length && <section className="school-panel">No chapter references for these filters. Missing subjects are not yet a complete curriculum.</section>}
    {['admin','superadmin'].includes(user?.role || '') && <details className="school-panel"><summary>Add a reviewed subject / chapter reference</summary><form onSubmit={e => {e.preventDefault(); const f = new FormData(e.currentTarget); void save(() => api.post('/curriculum-workspace/chapters', {grade, subject: f.get('subject'), title: f.get('title'), edition: f.get('edition'), source_url: f.get('source_url'), review_note: f.get('review_note')}))}}>
      <p>Adds to Class {grade}. This creates a reference, not lesson content.</p>
      <label>Subject identifier<input name="subject" required pattern="[a-z][a-z0-9 -]+" maxLength={80} placeholder="economics" /></label><label>Chapter title<input name="title" required minLength={3} maxLength={200} /></label><label>Edition<input name="edition" required minLength={4} maxLength={40} placeholder="cbse-2026-27" /></label><label>Official reference URL<input name="source_url" type="url" required maxLength={500} /></label><label>Review note<textarea name="review_note" required minLength={10} maxLength={2000} /></label><button disabled={busy}>Add chapter reference</button>
    </form></details>}
  </main>
}
