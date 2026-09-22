import { useEffect, useMemo, useRef, useState } from 'react'
import { motion } from 'framer-motion'
import {
  BookOpen, BrainCircuit, CheckCircle2, ChevronRight, History, Lightbulb,
  Mic, Plus, Send, Sparkles, Speaker, Square, Trash2, Volume2,
} from 'lucide-react'
import { api } from '@/api/axios'
import { SashaAvatarStage } from '@/components/ai/SashaAvatarStage'
import '@/styles/ai-experience.css'

type Message = { id: string; role: 'user' | 'assistant'; content: string; createdAt: string }
type LearningSignal = { concept: string; score: number; severity: 'high' | 'watch' | 'developing'; likely_gap: string }
type Session = { id: string; title: string; messages: Message[]; updatedAt: string; courseId?: number | null; lastSignal?: LearningSignal | null }
type CourseOption = { id: number; title?: string; post_title?: string }
type SashaMood = 'idle' | 'thinking' | 'talking' | 'celebrate'

const STORAGE_KEY = 'sasha-ai-studio-sessions-v1'
const welcome = (): Message => ({
  id: crypto.randomUUID(), role: 'assistant', createdAt: new Date().toISOString(),
  content: "Vanakkam! I’m Sasha, your learning companion. Bring me a difficult concept, a practice question, or something from your course—we’ll work it out together.",
})
const newSession = (): Session => ({
  id: crypto.randomUUID(), title: 'New learning space', messages: [welcome()], updatedAt: new Date().toISOString(),
})

const QUICK_PROMPTS = [
  { icon: Lightbulb, label: 'Explain simply', prompt: 'Explain a difficult concept to me using a simple real-world analogy.' },
  { icon: BrainCircuit, label: 'Test my understanding', prompt: 'Give me a short diagnostic question, then guide me based on my answer.' },
  { icon: BookOpen, label: 'Build a study plan', prompt: 'Help me create a focused study plan for the topic I am learning.' },
]

export default function LearnWithSashaPage() {
  const [sessions, setSessions] = useState<Session[]>(() => {
    try {
      const parsed = JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]') as Session[]
      return parsed.length ? parsed : [newSession()]
    } catch { return [newSession()] }
  })
  const [activeId, setActiveId] = useState(() => sessions[0].id)
  const [input, setInput] = useState('')
  const [busy, setBusy] = useState(false)
  const [mood, setMood] = useState<SashaMood>('idle')
  const [listening, setListening] = useState(false)
  const [voiceOn, setVoiceOn] = useState(true)
  const [providerReady, setProviderReady] = useState<boolean | null>(null)
  const [courses, setCourses] = useState<CourseOption[]>([])
  const endRef = useRef<HTMLDivElement>(null)
  const active = sessions.find((session) => session.id === activeId) || sessions[0]

  useEffect(() => { localStorage.setItem(STORAGE_KEY, JSON.stringify(sessions.slice(0, 20))) }, [sessions])
  useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [active?.messages, busy])
  useEffect(() => {
    api.get<{ configured: boolean }>('/ai/providers/status')
      .then((response) => setProviderReady(response.data.configured))
      .catch(() => setProviderReady(false))
    api.get<CourseOption[]>('/users/my-courses')
      .then((response) => setCourses(response.data || []))
      .catch(() => setCourses([]))
  }, [])

  const history = useMemo(() => active?.messages.slice(-8).map(({ role, content }) => ({ role, content })) || [], [active])
  const updateActive = (updater: (session: Session) => Session) => {
    setSessions((current) => current.map((session) => session.id === activeId ? updater(session) : session))
  }

  const speak = (text: string) => {
    if (!voiceOn || !('speechSynthesis' in window)) return
    window.speechSynthesis.cancel()
    const utterance = new SpeechSynthesisUtterance(text.replace(/[*#`]/g, ''))
    utterance.rate = 0.98
    utterance.pitch = 1.04
    utterance.onstart = () => setMood('talking')
    utterance.onend = () => setMood('idle')
    window.speechSynthesis.speak(utterance)
  }

  const send = async (raw?: string) => {
    const text = (raw ?? input).trim()
    if (!text || busy || !active) return
    const userMessage: Message = { id: crypto.randomUUID(), role: 'user', content: text, createdAt: new Date().toISOString() }
    setInput('')
    setBusy(true)
    setMood('thinking')
    updateActive((session) => ({
      ...session,
      title: session.messages.length <= 1 ? text.slice(0, 42) : session.title,
      updatedAt: new Date().toISOString(),
      messages: [...session.messages, userMessage],
    }))
    try {
      const response = await api.post<{ reply?: string; learning_signal?: LearningSignal | null }>('/ai/tutor/chat', { message: text, history, course_id: active.courseId || null, session_id: active.id })
      const reply = String(response.data.reply || 'Let’s try that another way.')
      updateActive((session) => ({
        ...session, updatedAt: new Date().toISOString(), lastSignal: response.data.learning_signal || null,
        messages: [...session.messages, { id: crypto.randomUUID(), role: 'assistant', content: reply, createdAt: new Date().toISOString() }],
      }))
      setMood('celebrate')
      speak(reply)
      if (!voiceOn) window.setTimeout(() => setMood('idle'), 900)
    } catch (error: unknown) {
      const detail = (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      updateActive((session) => ({
        ...session,
        messages: [...session.messages, {
          id: crypto.randomUUID(), role: 'assistant', createdAt: new Date().toISOString(),
          content: detail || 'I could not reach the AI provider. Ask your administrator to check the provider vault.',
        }],
      }))
      setMood('idle')
    } finally { setBusy(false) }
  }

  const createSession = () => {
    const session = newSession()
    setSessions((current) => [session, ...current])
    setActiveId(session.id)
  }

  const removeSession = (id: string) => {
    const next = sessions.filter((session) => session.id !== id)
    const ensured = next.length ? next : [newSession()]
    setSessions(ensured)
    if (id === activeId) setActiveId(ensured[0].id)
  }

  const startListening = () => {
    const Recognition = (window as unknown as { webkitSpeechRecognition?: new () => {
      lang: string; interimResults: boolean
      onresult: (event: { results: ArrayLike<{ 0: { transcript: string } }> }) => void
      onend: () => void; start: () => void
    } }).webkitSpeechRecognition
    if (!Recognition || listening) { setListening(false); return }
    const recognition = new Recognition()
    recognition.lang = 'en-IN'
    recognition.interimResults = false
    recognition.onresult = (event) => setInput(event.results[0][0].transcript)
    recognition.onend = () => setListening(false)
    recognition.start()
    setListening(true)
  }

  return (
    <div className="sasha-ai-studio relative isolate min-h-[calc(100vh-5rem)] overflow-hidden rounded-[2rem] bg-[#160e0a] text-white shadow-2xl shadow-orange-950/20">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_18%_18%,rgba(249,115,22,0.21),transparent_34%),radial-gradient(circle_at_86%_8%,rgba(251,191,36,0.16),transparent_29%),linear-gradient(135deg,#160e0a_0%,#27140b_52%,#1b1210_100%)]" />
      <div className="pointer-events-none absolute inset-0 opacity-[0.13] [background-image:linear-gradient(rgba(255,255,255,.18)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,.18)_1px,transparent_1px)] [background-size:42px_42px]" />

      <div className="relative grid min-h-[calc(100vh-5rem)] grid-cols-1 xl:grid-cols-[300px_minmax(0,1fr)_340px]">
        <aside className="hidden border-r border-white/10 bg-white/[0.035] p-5 backdrop-blur-xl xl:flex xl:flex-col">
          <div className="mb-7 flex items-center gap-3">
            <div className="grid h-11 w-11 place-items-center rounded-2xl bg-gradient-to-br from-orange-500 to-amber-300 shadow-lg shadow-orange-500/25"><Sparkles className="h-5 w-5 text-slate-950" /></div>
            <div><p className="font-semibold tracking-tight">Learn with Sasha</p><p className="text-xs text-slate-400">Personal learning spaces</p></div>
          </div>
          <button onClick={createSession} className="mb-6 flex w-full items-center justify-center gap-2 rounded-2xl border border-orange-300/25 bg-orange-400/10 px-4 py-3 text-sm font-semibold text-orange-100 transition hover:bg-orange-400/15"><Plus className="h-4 w-4" /> New conversation</button>
          <p className="mb-2 flex items-center gap-2 px-2 text-xs font-semibold uppercase tracking-[0.18em] text-slate-500"><History className="h-3.5 w-3.5" /> Recent</p>
          <div className="space-y-1 overflow-y-auto">
            {sessions.map((session) => (
              <div key={session.id} className={`group flex items-center rounded-xl transition ${session.id === activeId ? 'bg-white/10 text-white' : 'text-slate-400 hover:bg-white/5 hover:text-slate-200'}`}>
                <button onClick={() => setActiveId(session.id)} className="min-w-0 flex-1 px-3 py-3 text-left text-sm"><span className="block truncate">{session.title}</span></button>
                <button onClick={() => removeSession(session.id)} className="mr-2 rounded-lg p-1.5 opacity-0 transition hover:bg-rose-400/10 hover:text-rose-300 group-hover:opacity-100" aria-label="Delete conversation"><Trash2 className="h-3.5 w-3.5" /></button>
              </div>
            ))}
          </div>
          <div className="mt-auto rounded-2xl border border-emerald-300/15 bg-emerald-300/[0.06] p-4">
            <p className="flex items-center gap-2 text-xs font-semibold text-emerald-200"><span className="h-2 w-2 rounded-full bg-emerald-300 shadow-[0_0_12px_#6ee7b7]" /> Guarded learning mode</p>
            <p className="mt-2 text-xs leading-relaxed text-slate-400">Only course-linked questions become instructor learning signals. General spaces stay private.</p>
          </div>
        </aside>

        <main className="flex min-w-0 flex-col border-r border-white/10">
          <header className="flex items-center justify-between gap-4 border-b border-white/10 px-5 py-4 md:px-7">
            <div className="min-w-0"><p className="truncate text-sm font-semibold">{active?.title}</p><p className={`mt-0.5 text-xs ${active?.courseId ? 'text-orange-200/75' : 'text-slate-500'}`}>{active?.courseId ? 'Course-linked · learning signals visible to your instructor' : 'Private general workspace · excluded from instructor insights'}</p></div>
            <div className="ml-auto hidden min-w-0 md:block">
              <label className="sr-only" htmlFor="sasha-course-context">Course context</label>
              <select id="sasha-course-context" value={active?.courseId || ''} onChange={(event) => updateActive((session) => ({ ...session, courseId: event.target.value ? Number(event.target.value) : null, lastSignal: null }))} className="sasha-ai-context max-w-56 truncate rounded-xl border border-white/10 bg-white/[0.06] px-3 py-2.5 text-xs text-slate-300 outline-none focus:border-orange-300/50">
                <option value="" className="bg-slate-900">General learning</option>
                {courses.map((course) => <option key={course.id} value={course.id} className="bg-slate-900">{course.title || course.post_title || `Course ${course.id}`}</option>)}
              </select>
            </div>
            <div className="flex shrink-0 items-center gap-2">
              <button onClick={() => setVoiceOn((value) => !value)} className={`rounded-xl border p-2.5 transition ${voiceOn ? 'border-orange-300/25 bg-orange-400/10 text-orange-200' : 'border-white/10 text-slate-500'}`} aria-label={voiceOn ? 'Disable spoken replies' : 'Enable spoken replies'}>{voiceOn ? <Volume2 className="h-4 w-4" /> : <Speaker className="h-4 w-4" />}</button>
              <button onClick={createSession} className="rounded-xl border border-white/10 p-2.5 text-slate-300 transition hover:bg-white/10 xl:hidden" aria-label="New conversation"><Plus className="h-4 w-4" /></button>
            </div>
          </header>

          <div className="flex-1 space-y-5 overflow-y-auto px-4 py-6 md:px-8">
            {active?.messages.map((message, index) => (
              <motion.div key={message.id} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: Math.min(index * 0.025, 0.15) }} className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div className={`max-w-[88%] rounded-3xl px-5 py-4 text-sm leading-7 md:max-w-[76%] ${message.role === 'user' ? 'rounded-br-lg bg-gradient-to-br from-orange-500 to-amber-300 text-slate-950 shadow-lg shadow-orange-500/15' : 'rounded-bl-lg border border-white/10 bg-white/[0.065] text-slate-200 backdrop-blur-xl'}`}>
                  <p className="whitespace-pre-wrap">{message.content}</p>
                  {message.role === 'assistant' && <button onClick={() => speak(message.content)} className="mt-3 flex items-center gap-1.5 text-xs font-semibold text-orange-300/90 transition hover:text-orange-200"><Volume2 className="h-3.5 w-3.5" /> Listen</button>}
                </div>
              </motion.div>
            ))}
            {busy && <div className="flex items-center gap-3 text-sm text-slate-400"><div className="flex gap-1 rounded-2xl border border-white/10 bg-white/[0.055] px-4 py-3"><i className="h-1.5 w-1.5 animate-bounce rounded-full bg-orange-300" /><i className="h-1.5 w-1.5 animate-bounce rounded-full bg-orange-300 [animation-delay:120ms]" /><i className="h-1.5 w-1.5 animate-bounce rounded-full bg-orange-300 [animation-delay:240ms]" /></div>Sasha is mapping the concept…</div>}
            <div ref={endRef} />
          </div>

          <div className="border-t border-white/10 bg-[#160e0a]/80 p-4 backdrop-blur-xl md:p-6">
            <div className="mb-3 flex gap-2 overflow-x-auto pb-1">
              {QUICK_PROMPTS.map(({ icon: Icon, label, prompt }) => <button key={label} onClick={() => void send(prompt)} disabled={busy} className="flex shrink-0 items-center gap-2 rounded-full border border-white/10 bg-white/[0.04] px-3 py-2 text-xs text-slate-300 transition hover:border-orange-300/35 hover:bg-orange-400/10 hover:text-orange-100 disabled:opacity-40"><Icon className="h-3.5 w-3.5" />{label}</button>)}
            </div>
            <div className="flex items-end gap-2 rounded-[1.5rem] border border-white/10 bg-white/[0.07] p-2 shadow-[0_16px_50px_rgba(0,0,0,.2)] focus-within:border-orange-300/40 focus-within:ring-4 focus-within:ring-orange-300/5">
              <textarea id="sasha-ai-composer" value={input} onChange={(event) => setInput(event.target.value)} onKeyDown={(event) => { if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); void send() } }} placeholder="Ask Sasha anything about what you are learning…" rows={1} className="sasha-ai-composer max-h-36 min-h-11 flex-1 resize-none bg-transparent px-3 py-3 text-sm text-white outline-none placeholder:text-slate-500" />
              <button onClick={startListening} className={`mb-0.5 grid h-10 w-10 place-items-center rounded-xl transition ${listening ? 'bg-rose-400 text-slate-950' : 'text-slate-400 hover:bg-white/10 hover:text-white'}`} aria-label={listening ? 'Stop listening' : 'Speak your question'}>{listening ? <Square className="h-4 w-4" /> : <Mic className="h-4 w-4" />}</button>
              <button onClick={() => void send()} disabled={busy || !input.trim()} className="mb-0.5 grid h-10 w-10 place-items-center rounded-xl bg-gradient-to-br from-orange-500 to-amber-300 text-slate-950 shadow-lg shadow-orange-500/25 transition hover:scale-[1.03] disabled:scale-100 disabled:opacity-30" aria-label="Send message"><Send className="h-4 w-4" /></button>
            </div>
            <p className={`mt-2 text-center text-xs ${active?.courseId ? 'text-orange-200/60' : 'text-slate-500'}`}>{active?.courseId ? 'Course insight is on: your question—not Sasha’s reply—can help your instructor support you.' : 'General learning is private and excluded from instructor insights. Verify important answers.'}</p>
          </div>
        </main>

        <aside className="relative hidden overflow-hidden p-6 xl:flex xl:flex-col">
          <div className="flex items-center justify-between"><span className={`flex items-center gap-2 text-xs font-semibold ${providerReady === false ? 'text-amber-200' : 'text-orange-100'}`}><Sparkles className={`h-4 w-4 ${providerReady === false ? 'text-amber-300' : 'text-orange-300'}`} /> {providerReady === null ? 'Checking Sasha…' : providerReady ? 'Sasha live' : 'Provider setup needed'}</span><span className="rounded-full border border-white/10 bg-white/5 px-2.5 py-1 text-xs text-slate-400">3D · voice ready</span></div>
          <div className="relative my-4 min-h-[310px] flex-1 rounded-[2rem] border border-orange-300/15 bg-gradient-to-b from-orange-400/[0.08] to-amber-300/[0.025] shadow-[inset_0_0_70px_rgba(249,115,22,.08)]">
            <div className="absolute inset-x-10 bottom-8 h-16 rounded-full bg-orange-300/10 blur-2xl" />
            <SashaAvatarStage mood={mood} className="absolute inset-0" />
          </div>
          <div className="space-y-3">
            <div className="rounded-2xl border border-white/10 bg-white/[0.05] p-4"><p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">Learning signal</p>{active?.lastSignal ? <div className="mt-2"><p className="flex items-center gap-2 text-sm font-semibold text-orange-100"><CheckCircle2 className="h-4 w-4 text-orange-300" /> {active.lastSignal.concept}</p><p className="mt-1 text-xs text-slate-400">{active.lastSignal.score}% concern · {active.lastSignal.likely_gap}</p></div> : <p className="mt-2 flex items-center gap-2 text-sm text-slate-200"><CheckCircle2 className="h-4 w-4 text-emerald-300" /> Socratic guidance active</p>}</div>
            <button onClick={() => void send('Give me one quick question to check what I understand, without revealing the answer first.')} className="group flex w-full items-center justify-between rounded-2xl border border-orange-300/15 bg-orange-400/[0.08] p-4 text-left transition hover:bg-orange-400/15"><span><span className="block text-sm font-semibold text-orange-100">Quick knowledge check</span><span className="mt-1 block text-xs text-slate-500">One question · guided feedback</span></span><ChevronRight className="h-4 w-4 text-orange-300 transition group-hover:translate-x-1" /></button>
          </div>
        </aside>
      </div>
    </div>
  )
}
