import { useMemo,useState } from 'react'
import toast from 'react-hot-toast'
import { api } from '@/api/axios'
import { H5PPicker } from '@/components/h5p/H5PPicker'
import { GamePicker } from '@/components/games/GamePicker'
import { COURSE_TYPES,courseTypeLabel } from '@/config/courseTypes'
import {
validateQuestions,
friendlyServerError,
type ValidatableQuestion,
} from '@/pages/instructor/quizBuilderValidation'

/**
 * Popup quiz-creation flow (owner request 2026-09-04): the instructor picks
 * the course TYPE first, then sets up the quiz details and questions —
 * everything inside one modal, unlike the old inline wizard editor whose
 * data never reached the server. On save it creates a REAL quiz via
 * POST /courses/{id}/quizzes (the same endpoint the Quiz Builder page uses).
 */

interface QuizSetupModalProps {
  /** Draft course id; may be null — the modal auto-creates the course via ensureCourseExists on save. */
  courseId: number | null
  ensureCourseExists: () => Promise<number>
  /** The course's current type (preselects step 1). */
  defaultCourseType: string
  /** Called when the instructor picks a different type in step 1 so the wizard stays in sync. */
  onCourseTypeChange: (type: string) => void
  onClose: () => void
  /** Receives the id of the freshly created quiz. */
  onCreated: (quizId: number) => void
}

type QuestionType = 'multiple_choice' | 'multi_select' | 'true_false' | 'fill_in_blank' | 'short_answer' | 'essay'

const QUESTION_TYPE_OPTIONS: { value: QuestionType; label: string }[] = [
  { value: 'multiple_choice', label: 'Multiple choice (single answer)' },
  { value: 'multi_select', label: 'Multi select (many answers)' },
  { value: 'true_false', label: 'True / False' },
  { value: 'fill_in_blank', label: 'Fill in the blank' },
  { value: 'short_answer', label: 'Short answer (auto/manual)' },
  { value: 'essay', label: 'Essay (manual grading)' },
]

interface LocalQuestion extends ValidatableQuestion {
  id: string
}

let localQuestionSeq = 0
const newLocalId = () => `q-${Date.now()}-${localQuestionSeq++}`

function makeQuestion(type: QuestionType): LocalQuestion {
  return {
    id: newLocalId(),
    type,
    question: '',
    points: 1,
    options: type === 'multiple_choice' || type === 'multi_select' ? ['', '', '', ''] : undefined,
    correctAnswer: type === 'true_false' ? 'true' : type === 'fill_in_blank' ? '' : type === 'multiple_choice' ? 0 : undefined,
    correctAnswers: type === 'multi_select' ? [] : undefined,
    explanation: '',
  }
}

const FEEDBACK_MODES = [
  { value: 'reveal_immediate', label: 'Reveal answers immediately after submit' },
  { value: 'reveal_after_due', label: 'Reveal answers after the due date' },
  { value: 'reveal_never', label: 'Never reveal answers' },
]

export function QuizSetupModal({
  ensureCourseExists,
  defaultCourseType,
  onCourseTypeChange,
  onClose,
  onCreated,
}: QuizSetupModalProps) {
  const [step, setStep] = useState<1 | 2>(1)
  const [selectedType, setSelectedType] = useState<string>(defaultCourseType || '')
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [timeLimit, setTimeLimit] = useState('30')
  const [passingScore, setPassingScore] = useState('70')
  const [maxAttempts, setMaxAttempts] = useState('0')
  const [feedbackMode, setFeedbackMode] = useState('reveal_immediate')
  const [questions, setQuestions] = useState<LocalQuestion[]>([])
  const [modules, setModules] = useState<{ kind: 'h5p' | 'game'; id: number; title: string }[]>([])
  const [questionErrors, setQuestionErrors] = useState<Record<string, string>>({})
  const [saving, setSaving] = useState(false)

  const setQuestion = (id: string, patch: Partial<LocalQuestion>) => {
    setQuestions(prev => prev.map(q => (q.id === id ? { ...q, ...patch } : q)))
  }

  const changeQuestionType = (id: string, newType: QuestionType) => {
    setQuestions(prev =>
      prev.map(q => {
        if (q.id !== id) return q
        const base: LocalQuestion = { ...q, type: newType }
        if (newType === 'multiple_choice' || newType === 'multi_select') {
          base.options = q.options && q.options.length >= 2 ? q.options : ['', '', '', '']
        } else {
          base.options = undefined
        }
        if (newType === 'true_false') base.correctAnswer = 'true'
        else if (newType === 'multiple_choice') base.correctAnswer = 0
        else if (newType === 'fill_in_blank') base.correctAnswer = ''
        else if (newType === 'multi_select') base.correctAnswers = []
        else { base.correctAnswer = undefined; base.correctAnswers = undefined }
        return base
      })
    )
  }

  const totalPoints = useMemo(
    () => questions.reduce((sum, q) => sum + (parseInt(String(q.points), 10) || 0), 0),
    [questions]
  )

  const proceedToQuestions = () => {
    if (!selectedType) {
      toast.error('Choose a course type first')
      return
    }
    // Keep the wizard/course in sync with the type chosen here.
    if (selectedType !== defaultCourseType) onCourseTypeChange(selectedType)
    setStep(2)
  }

  const saveQuiz = async () => {
    const errors = validateQuestions(questions as ValidatableQuestion[])
    const byQuestion: Record<string, string> = {}
    for (const err of errors) {
      const q = questions[err.index]
      if (q) byQuestion[q.id] = err.message
    }
    setQuestionErrors(byQuestion)
    if (errors.length > 0) {
      toast.error('Fix the highlighted questions before saving')
      return
    }
    if (questions.length === 0 && modules.length === 0) {
      toast.error('Add at least one question OR one scored interactive module')
      return
    }

    setSaving(true)
    try {
      const targetCourseId = await ensureCourseExists()
      const payload = {
        title: title.trim() || 'Untitled Quiz',
        description: description.trim(),
        timeLimit: parseInt(timeLimit, 10) || 0,
        passingScore: parseInt(passingScore, 10) || 70,
        maxAttempts: parseInt(maxAttempts, 10) || 0,
        feedbackMode,
        courseType: selectedType,
        interactive_modules: modules,
        questions: questions.map(q => ({
          type: q.type,
          question: q.question,
          points: q.points,
          options: q.options,
          correctAnswer: q.correctAnswer,
          correctAnswers: q.correctAnswers,
          explanation: q.explanation || '',
        })),
      }
      const response = await api.post(`/courses/${targetCourseId}/quizzes`, payload)
      const quizId = response?.data?.id
      toast.success(`Quiz created (${courseTypeLabel(selectedType)})`)
      onCreated(quizId)
      onClose()
    } catch (error: any) {
      const detail = error?.response?.data?.detail
      const friendly =
        typeof detail === 'object' ? friendlyServerError(detail)?.message : detail
      toast.error(friendly || 'Failed to create quiz')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 z-modal flex items-center justify-center bg-black/50 p-4" onMouseDown={e => { if (e.target === e.currentTarget) onClose() }}>
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-3xl max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">
              {step === 1 ? 'Create Quiz — Choose Course Type' : 'Create Quiz — Questions & Settings'}
            </h2>
            <p className="text-xs text-gray-500 mt-0.5">Step {step} of 2</p>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-2xl leading-none" aria-label="Close">×</button>
        </div>

        {/* Step progress */}
        <div className="px-6 pt-4">
          <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden">
            <div className={`h-full bg-blue-500 transition-all ${step === 1 ? 'w-1/2' : 'w-full'}`} />
          </div>
        </div>

        <div className="overflow-y-auto px-6 py-5 flex-1">
          {step === 1 && (
            <div>
              <p className="text-sm text-gray-600 mb-4">
                Every course (and its quizzes) belongs to exactly one type. Pick the type this quiz falls under:
              </p>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                {COURSE_TYPES.map(t => (
                  <button
                    key={t.value}
                    type="button"
                    onClick={() => setSelectedType(t.value)}
                    className={`p-4 rounded-xl border-2 text-left transition-all ${t.cardClass} ${selectedType === t.value ? t.selectedClass : 'border-gray-200 bg-white'}`}
                  >
                    <div className="text-2xl mb-1">{t.emoji}</div>
                    <div className="font-semibold text-gray-900">{t.label}</div>
                    <div className="text-xs text-gray-500">{t.tamil}</div>
                    <div className="text-xs text-gray-400 mt-1">{t.tagline}</div>
                  </button>
                ))}
              </div>
              {defaultCourseType && selectedType !== defaultCourseType && (
                <p className="text-xs text-amber-600 mt-3">
                  ⚠️ This changes the course type from <b>{courseTypeLabel(defaultCourseType)}</b> to <b>{courseTypeLabel(selectedType)}</b>.
                </p>
              )}
            </div>
          )}

          {step === 2 && (
            <div className="space-y-5">
              {/* Quiz settings */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="md:col-span-2">
                  <label className="block text-sm font-medium text-gray-700 mb-1">Quiz Title *</label>
                  <input
                    type="text"
                    value={title}
                    onChange={e => setTitle(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    placeholder="e.g., Unit 1 — Basics Check"
                  />
                </div>
                <div className="md:col-span-2">
                  <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
                  <textarea
                    value={description}
                    onChange={e => setDescription(e.target.value)}
                    rows={2}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    placeholder="What will students learn from this quiz?"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Time Limit (minutes, 0 = none)</label>
                  <input type="number" min="0" value={timeLimit} onChange={e => setTimeLimit(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Passing Score (%)</label>
                  <input type="number" min="0" max="100" value={passingScore} onChange={e => setPassingScore(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Max Attempts (0 = unlimited)</label>
                  <input type="number" min="0" value={maxAttempts} onChange={e => setMaxAttempts(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Answer Reveal</label>
                  <select value={feedbackMode} onChange={e => setFeedbackMode(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent">
                    {FEEDBACK_MODES.map(m => <option key={m.value} value={m.value}>{m.label}</option>)}
                  </select>
                </div>
              </div>

              {/* Scored interactive modules */}
              <div className="border border-violet-200 bg-violet-50 rounded-xl p-4">
                <h4 className="text-sm font-semibold text-gray-800">Scored interactive modules (optional)</h4>
                <p className="text-xs text-gray-500 mt-0.5 mb-3">
                  Embed one of your H5P packages or games — their scores count
                  toward this quiz in the cumulative grade (20% weight).
                </p>
                {modules.length > 0 && (
                  <ul className="mb-3 space-y-1">
                    {modules.map((m, i) => (
                      <li key={`${m.kind}-${m.id}`} className="flex items-center justify-between text-sm bg-white rounded-lg px-3 py-2 border border-gray-200">
                        <span>
                          {m.kind === 'h5p' ? '🧩 H5P' : '🎮 Game'}: {m.title || `#${m.id}`}
                          <span className="text-xs text-gray-400 ml-2">scored</span>
                        </span>
                        <button type="button" className="text-xs text-red-500 hover:text-red-700"
                          onClick={() => setModules((prev) => prev.filter((_, idx) => idx !== i))}>
                          Remove
                        </button>
                      </li>
                    ))}
                  </ul>
                )}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <p className="text-xs font-medium text-gray-600 mb-1">Add H5P package</p>
                    <H5PPicker
                      value={null}
                      onChange={(id) => {
                        if (id && !modules.some((m) => m.kind === 'h5p' && m.id === id)) {
                          setModules((prev) => [...prev, { kind: 'h5p', id, title: `H5P #${id}` }])
                        }
                      }}
                    />
                  </div>
                  <div>
                    <p className="text-xs font-medium text-gray-600 mb-1">Add learning game</p>
                    <GamePicker
                      value={null}
                      onChange={(id) => {
                        if (id && !modules.some((m) => m.kind === 'game' && m.id === id)) {
                          setModules((prev) => [...prev, { kind: 'game', id, title: `Game #${id}` }])
                        }
                      }}
                    />
                  </div>
                </div>
              </div>

              {/* Questions */}
              <div className="border-t border-gray-200 pt-4">
                <div className="flex items-center justify-between mb-3">
                  <label className="text-sm font-semibold text-gray-800">
                    Questions ({questions.length}) · Total points: {totalPoints}
                  </label>
                </div>

                <div className="flex flex-wrap gap-2 mb-4">
                  {QUESTION_TYPE_OPTIONS.map(opt => (
                    <button
                      key={opt.value}
                      type="button"
                      onClick={() => setQuestions(prev => [...prev, makeQuestion(opt.value)])}
                      className="px-3 py-1.5 text-xs font-medium rounded-full border border-blue-200 text-blue-700 bg-blue-50 hover:bg-blue-100"
                    >
                      + {opt.label.split(' (')[0]}
                    </button>
                  ))}
                </div>

                {questions.length === 0 && (
                  <p className="text-sm text-gray-500 border border-dashed border-gray-300 rounded-lg p-4 text-center">
                    No questions yet — add one with the buttons above.
                  </p>
                )}

                <div className="space-y-4">
                  {questions.map((q, idx) => (
                    <div key={q.id} className="border border-gray-200 rounded-xl p-4 bg-gray-50">
                      <div className="flex items-center justify-between mb-3">
                        <span className="text-xs font-bold text-gray-500 uppercase">Question {idx + 1}</span>
                        <button
                          type="button"
                          onClick={() => setQuestions(prev => prev.filter(x => x.id !== q.id))}
                          className="text-xs text-red-500 hover:text-red-700"
                        >
                          Remove
                        </button>
                      </div>

                      <div className="grid grid-cols-1 md:grid-cols-4 gap-3 mb-3">
                        <div className="md:col-span-3">
                          <input
                            type="text"
                            value={q.question || ''}
                            onChange={e => setQuestion(q.id, { question: e.target.value })}
                            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                            placeholder="Question text *"
                          />
                        </div>
                        <select
                          value={q.type}
                          onChange={e => changeQuestionType(q.id, e.target.value as QuestionType)}
                          className="px-2 py-2 border border-gray-300 rounded-lg text-sm bg-white"
                        >
                          {QUESTION_TYPE_OPTIONS.map(opt => (
                            <option key={opt.value} value={opt.value}>{opt.label.split(' (')[0]}</option>
                          ))}
                        </select>
                      </div>

                      {(q.type === 'multiple_choice' || q.type === 'multi_select') && (
                        <div className="space-y-2 mb-3">
                          {(q.options || []).map((opt, oIdx) => (
                            <div key={oIdx} className="flex items-center gap-2">
                              <input
                                type={q.type === 'multi_select' ? 'checkbox' : 'radio'}
                                name={`correct-${q.id}`}
                                checked={
                                  q.type === 'multi_select'
                                    ? (q.correctAnswers || []).includes(oIdx)
                                    : q.correctAnswer === oIdx
                                }
                                onChange={() => {
                                  if (q.type === 'multi_select') {
                                    const cur = q.correctAnswers || []
                                    setQuestion(q.id, {
                                      correctAnswers: cur.includes(oIdx) ? cur.filter(i => i !== oIdx) : [...cur, oIdx],
                                    })
                                  } else {
                                    setQuestion(q.id, { correctAnswer: oIdx })
                                  }
                                }}
                                className="shrink-0"
                                title="Mark as correct answer"
                              />
                              <input
                                type="text"
                                value={opt}
                                onChange={e => {
                                  const next = [...(q.options || [])]
                                  next[oIdx] = e.target.value
                                  setQuestion(q.id, { options: next })
                                }}
                                className="flex-1 px-3 py-1.5 border border-gray-300 rounded-lg text-sm"
                                placeholder={`Option ${oIdx + 1}`}
                              />
                              {(q.options || []).length > 2 && (
                                <button
                                  type="button"
                                  onClick={() => setQuestion(q.id, { options: (q.options || []).filter((_, i) => i !== oIdx) })}
                                  className="text-xs text-gray-400 hover:text-red-500"
                                >
                                  ✕
                                </button>
                              )}
                            </div>
                          ))}
                          <button
                            type="button"
                            onClick={() => setQuestion(q.id, { options: [...(q.options || []), ''] })}
                            className="text-xs text-blue-600 hover:underline"
                          >
                            + Add option
                          </button>
                          <p className="text-xs text-gray-400">Tick the circle/box next to the correct answer{q.type === 'multi_select' ? 's' : ''}.</p>
                        </div>
                      )}

                      {q.type === 'true_false' && (
                        <div className="flex gap-4 mb-3">
                          {['true', 'false'].map(v => (
                            <label key={v} className="flex items-center gap-1.5 text-sm">
                              <input
                                type="radio"
                                name={`tf-${q.id}`}
                                checked={q.correctAnswer === v}
                                onChange={() => setQuestion(q.id, { correctAnswer: v })}
                              />
                              {v === 'true' ? 'True' : 'False'}
                            </label>
                          ))}
                        </div>
                      )}

                      {q.type === 'fill_in_blank' && (
                        <input
                          type="text"
                          value={String(q.correctAnswer ?? '')}
                          onChange={e => setQuestion(q.id, { correctAnswer: e.target.value })}
                          className="w-full px-3 py-1.5 border border-gray-300 rounded-lg text-sm mb-3"
                          placeholder="Correct answer (exact match) *"
                        />
                      )}

                      {(q.type === 'short_answer' || q.type === 'essay') && (
                        <p className="text-xs text-gray-500 mb-3">
                          {q.type === 'short_answer'
                            ? 'Optional reference answer — leave blank for manual grading.'
                            : 'Manually graded — no answer key needed.'}
                        </p>
                      )}

                      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                        <div>
                          <label className="text-xs text-gray-500">Points</label>
                          <input
                            type="number"
                            min="1"
                            max="1000"
                            value={q.points ?? 1}
                            onChange={e => setQuestion(q.id, { points: parseInt(e.target.value, 10) || 1 })}
                            className="w-full px-3 py-1.5 border border-gray-300 rounded-lg text-sm"
                          />
                        </div>
                        <div className="md:col-span-2">
                          <label className="text-xs text-gray-500">Explanation (shown after submit, if allowed)</label>
                          <input
                            type="text"
                            value={q.explanation || ''}
                            onChange={e => setQuestion(q.id, { explanation: e.target.value })}
                            className="w-full px-3 py-1.5 border border-gray-300 rounded-lg text-sm"
                            placeholder="Why is this the correct answer?"
                          />
                        </div>
                      </div>

                      {questionErrors[q.id] && (
                        <p className="text-xs text-red-600 mt-2">⚠ {questionErrors[q.id]}</p>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-6 py-4 border-t border-gray-200 bg-gray-50 rounded-b-2xl">
          <div>
            {step === 2 && (
              <button
                type="button"
                onClick={() => setStep(1)}
                className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800"
              >
                ← Back
              </button>
            )}
          </div>
          <div className="flex items-center gap-3">
            {step === 1 && (
              <span className="text-sm text-gray-500">
                {selectedType ? `Type: ${courseTypeLabel(selectedType)}` : 'No type selected'}
              </span>
            )}
            {step === 1 ? (
              <button
                type="button"
                onClick={proceedToQuestions}
                disabled={!selectedType}
                className="px-5 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-40 disabled:cursor-not-allowed"
              >
                Next: Set Up Questions →
              </button>
            ) : (
              <button
                type="button"
                onClick={saveQuiz}
                disabled={saving}
                className="px-5 py-2 bg-emerald-600 text-white rounded-lg text-sm font-medium hover:bg-emerald-700 disabled:opacity-40"
              >
                {saving ? 'Saving…' : '✓ Create Quiz'}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

export default QuizSetupModal
