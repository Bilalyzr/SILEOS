/**
 * AI Tutor drawer (Engine C) — floating assistant on the lesson player.
 * Honest 503 handling: if the backend has no ANTHROPIC_API_KEY the drawer
 * says exactly that instead of pretending.
 */
import { useEffect, useRef, useState } from 'react'
import { Sparkles, X, Send } from 'lucide-react'
import { api } from '@/api/axios'
import { aiLayerAPI, errDetail, type ErrorKind } from '@/api/aiLayer'

interface Msg { role: 'user' | 'assistant'; content: string }

export function TutorDrawer({ courseId }: { courseId?: number }) {
  const [open, setOpen] = useState(false)
  const [messages, setMessages] = useState<Msg[]>([{
    role: 'assistant',
    content: "Hi! I'm your AI tutor — ask me anything about this course and I'll guide you to the answer.",
  }])
  const [input, setInput] = useState('')
  const [busy, setBusy] = useState(false)
  const [notConfigured, setNotConfigured] = useState(false)
  // v2.0 §9 (WP7): escalation, check question, error report
  const [reporting, setReporting] = useState(false)
  const [reportKind, setReportKind] = useState<ErrorKind>('lesson')
  const [reportText, setReportText] = useState('')
  const endRef = useRef<HTMLDivElement>(null)

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages])

  async function send() {
    const text = input.trim()
    if (!text || busy) return
    setInput('')
    setMessages((m) => [...m, { role: 'user', content: text }])
    setBusy(true)
    try {
      const r = await api.post('/ai/tutor/chat', {
        message: text,
        course_id: courseId,
        history: messages.slice(-6),
      })
      setMessages((m) => [...m, { role: 'assistant', content: r.data.reply }])
      setNotConfigured(false)
    } catch (e: unknown) {
      const status = (e as { response?: { status?: number } })?.response?.status
      const detail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      if (status === 503) {
        setNotConfigured(true)
        setMessages((m) => [...m, { role: 'assistant', content: '⚠ ' + (detail || 'AI tutor is not configured on the server yet.') }])
      } else {
        setMessages((m) => [...m, { role: 'assistant', content: '⚠ ' + (detail || 'Something went wrong — try again.') }])
      }
    } finally {
      setBusy(false)
    }
  }

  const say = (content: string) => setMessages((m) => [...m, { role: 'assistant', content }])
  const lastUser = [...messages].reverse().find((m) => m.role === 'user')?.content || input.trim()

  async function escalate() {
    if (!courseId || busy) return
    const question = lastUser
    if (!question) { say('Type your question first, then send it to your instructor.'); return }
    setBusy(true)
    try {
      await aiLayerAPI.escalate({ course_id: courseId, question, history: messages.slice(-8) })
      say('Sent to your instructor with this conversation. You will get a notification when they reply.')
    } catch (e) { say('⚠ ' + errDetail(e, 'Could not send to the instructor').detail) }
    finally { setBusy(false) }
  }

  async function checkMe() {
    if (!courseId || busy) return
    setBusy(true)
    try {
      const r = await aiLayerAPI.checkQuestion(courseId)
      const opts = r.check.kind === 'mcq' && r.check.options ? '\n' + r.check.options.map((o, i) => `${i + 1}. ${o}`).join('\n') : ''
      say(`Check yourself (${r.level}${r.concept ? ` · ${r.concept}` : ''}): ${r.check.question}${opts}`)
    } catch (e) {
      const { status, detail } = errDetail(e, 'Could not build a check question')
      if (status === 503) setNotConfigured(true)
      say('⚠ ' + detail)
    } finally { setBusy(false) }
  }

  async function sendReport() {
    if (!courseId || reportText.trim().length < 5) return
    setBusy(true)
    try {
      await aiLayerAPI.reportError({ course_id: courseId, kind: reportKind, message: reportText.trim() })
      setReporting(false); setReportText('')
      say('Thanks — your report went to the instructor. They will let you know what changed.')
    } catch (e) { say('⚠ ' + errDetail(e, 'Could not send the report').detail) }
    finally { setBusy(false) }
  }

  return (
    <>
      <button
        onClick={() => setOpen((v) => !v)}
        aria-label="AI Tutor"
        className="fixed bottom-5 right-5 z-40 h-12 w-12 rounded-full bg-violet-600 text-white shadow-lg hover:bg-violet-700 grid place-items-center"
      >
        {open ? <X className="h-5 w-5" /> : <Sparkles className="h-5 w-5" />}
      </button>

      {open && (
        <div className="fixed bottom-20 right-5 z-40 w-[22rem] max-w-[90vw] h-[26rem] rounded-2xl border border-gray-200 bg-white shadow-2xl flex flex-col overflow-hidden">
          <div className="px-4 py-3 bg-violet-600 text-white">
            <p className="text-sm font-semibold flex items-center gap-2">
              <Sparkles className="h-4 w-4" /> AI Tutor
              <span className="text-[10px] font-normal opacity-80 ml-auto">Socratic · course-scoped</span>
            </p>
          </div>
          <div className="flex-1 overflow-y-auto p-3 space-y-2">
            {messages.map((m, i) => (
              <div key={i} className={`text-sm rounded-xl px-3 py-2 max-w-[85%] ${
                m.role === 'user' ? 'ml-auto bg-blue-600 text-white' : 'bg-gray-100 text-gray-800'
              }`}>
                {m.content}
              </div>
            ))}
            {busy && <div className="text-xs text-gray-400 px-2">Tutor is thinking…</div>}
            <div ref={endRef} />
          </div>
          {notConfigured && (
            <p className="px-3 py-2 text-[11px] bg-amber-50 text-amber-700 border-t border-amber-100">
              The server needs a <code>GLM_API_KEY</code> (Zhipu GLM) to enable the tutor — ask the admin.
            </p>
          )}
          {courseId && (
            <div className="px-2 pt-2 border-t border-gray-100 flex flex-wrap gap-1">
              <button type="button" onClick={escalate} disabled={busy} className="px-2 py-1 text-[11px] rounded-full border border-gray-300 hover:bg-gray-50 disabled:opacity-40">Ask my instructor</button>
              <button type="button" onClick={checkMe} disabled={busy} className="px-2 py-1 text-[11px] rounded-full border border-gray-300 hover:bg-gray-50 disabled:opacity-40">Check my understanding</button>
              <button type="button" onClick={() => setReporting((v) => !v)} className="px-2 py-1 text-[11px] rounded-full border border-gray-300 hover:bg-gray-50">Report an error</button>
            </div>
          )}
          {reporting && courseId && (
            <div className="px-2 pt-2 flex flex-col gap-1" data-testid="error-report-form">
              <select value={reportKind} onChange={(e) => setReportKind(e.target.value as ErrorKind)} className="px-2 py-1 border border-gray-300 rounded text-xs" aria-label="What is wrong">
                <option value="lesson">A lesson has an error</option><option value="quiz_question">A quiz question is wrong</option><option value="other">Something else</option>
              </select>
              <div className="flex gap-1">
                <input value={reportText} onChange={(e) => setReportText(e.target.value)} placeholder="What is wrong, exactly?" className="flex-1 px-2 py-1 border border-gray-300 rounded text-xs" aria-label="Report details" />
                <button type="button" onClick={sendReport} disabled={busy || reportText.trim().length < 5} className="px-2 py-1 text-xs rounded bg-gray-900 text-white disabled:opacity-40">Send</button>
              </div>
            </div>
          )}
          <div className="p-2 border-t border-gray-100 flex gap-2">
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && send()}
              placeholder="Ask about this lesson…"
              className="flex-1 px-3 py-2 border border-gray-300 rounded-lg text-sm"
              disabled={busy}
            />
            <button
              onClick={send}
              disabled={busy || !input.trim()}
              className="px-3 py-2 bg-violet-600 text-white rounded-lg disabled:opacity-40"
              aria-label="Send"
            >
              <Send className="h-4 w-4" />
            </button>
          </div>
        </div>
      )}
    </>
  )
}

export default TutorDrawer
