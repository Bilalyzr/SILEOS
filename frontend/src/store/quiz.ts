import { create } from 'zustand'
import { Quiz, QuizAttempt, QuizQuestion } from '@/types'
import { quizAPI } from '@/api/quiz'

interface QuizState {
  // State
  currentQuiz: Quiz | null
  currentAttempt: QuizAttempt | null
  questions: QuizQuestion[]
  currentQuestionIndex: number
  answers: Record<number, string> // questionId -> answer
  timeRemaining: number
  isSubmitting: boolean
  isLoading: boolean
  error: string | null
  quizResults: QuizAttempt | null

  // Quiz settings
  isReviewMode: boolean
  showExplanations: boolean
  canNavigateFreely: boolean

  // Actions
  startQuiz: (quizId: number) => Promise<void>
  loadQuizAttempt: (attemptId: number) => Promise<void>
  submitAnswer: (questionId: number, answer: string) => void
  navigateToQuestion: (index: number) => void
  nextQuestion: () => void
  previousQuestion: () => void
  submitQuiz: () => Promise<QuizAttempt>
  pauseQuiz: () => Promise<void>
  resumeQuiz: () => Promise<void>
  resetQuiz: () => void
  setTimeRemaining: (seconds: number) => void
  getQuizResults: (attemptId: number) => Promise<QuizAttempt>
  retakeQuiz: () => Promise<void>
  clearError: () => void

  // Timer management
  startTimer: () => void
  stopTimer: () => void
  timer: NodeJS.Timeout | null
}

export const useQuizStore = create<QuizState>((set, get) => ({
  // Initial state
  currentQuiz: null,
  currentAttempt: null,
  questions: [],
  currentQuestionIndex: 0,
  answers: {},
  timeRemaining: 0,
  isSubmitting: false,
  isLoading: false,
  error: null,
  quizResults: null,
  isReviewMode: false,
  showExplanations: false,
  canNavigateFreely: false,

  // Actions
  startQuiz: async (quizId: number) => {
    try {
      // Clear stale quiz state up front so quiz B never renders quiz A's
      // content/results while (or after) loading.
      set({ isLoading: true, error: null, currentQuiz: null, quizResults: null })

      const { quiz, attempt, questions } = await quizAPI.startQuiz(quizId)

      // Set quiz settings based on quiz configuration
      const canNavigateFreely = quiz.quiz_question_layout_view === 'question_pagination'
      const timeLimit = quiz.quiz_time_limit * 60 // Convert minutes to seconds

      set({
        currentQuiz: quiz,
        currentAttempt: attempt,
        questions: questions,
        currentQuestionIndex: 0,
        answers: {},
        timeRemaining: timeLimit,
        isReviewMode: false,
        showExplanations: false,
        canNavigateFreely,
        isLoading: false,
      })

      // Start timer if quiz has time limit
      if (timeLimit > 0) {
        get().startTimer()
      }
    } catch (error: any) {
      set({
        error: error.message || 'Failed to start quiz',
        isLoading: false,
      })
      throw error
    }
  },

  loadQuizAttempt: async (attemptId: number) => {
    try {
      set({ isLoading: true, error: null })

      const attempt = await quizAPI.getQuizAttempt(attemptId)
      const quiz = attempt.quiz!
      const questions = quiz.questions!

      // Load existing answers
      const answers: Record<number, string> = {}
      attempt.answers?.forEach(answer => {
        answers[answer.question_id] = answer.given_answer
      })

      // Determine if this is review mode
      const isReviewMode = attempt.attempt_status === 'attempt_ended'

      set({
        currentQuiz: quiz,
        currentAttempt: attempt,
        questions,
        answers,
        isReviewMode,
        showExplanations: isReviewMode,
        canNavigateFreely: true, // Always allow navigation in review mode
        isLoading: false,
      })
    } catch (error: any) {
      set({
        error: error.message || 'Failed to load quiz attempt',
        isLoading: false,
      })
      throw error
    }
  },

  submitAnswer: (questionId: number, answer: string) => {
    const { answers } = get()
    set({
      answers: {
        ...answers,
        [questionId]: answer,
      },
    })

    // Auto-save answer if not in review mode
    const { isReviewMode, currentAttempt } = get()
    if (!isReviewMode && currentAttempt) {
      quizAPI.saveAnswer(currentAttempt.attempt_id, questionId, answer)
        .catch(error => {
          console.error('Failed to save answer:', error)
        })
    }
  },

  navigateToQuestion: (index: number) => {
    const { questions, canNavigateFreely } = get()

    if (!canNavigateFreely) return

    if (index >= 0 && index < questions.length) {
      set({ currentQuestionIndex: index })
    }
  },

  nextQuestion: () => {
    const { currentQuestionIndex, questions } = get()
    if (currentQuestionIndex < questions.length - 1) {
      set({ currentQuestionIndex: currentQuestionIndex + 1 })
    }
  },

  previousQuestion: () => {
    const { currentQuestionIndex, canNavigateFreely } = get()

    if (!canNavigateFreely) return

    if (currentQuestionIndex > 0) {
      set({ currentQuestionIndex: currentQuestionIndex - 1 })
    }
  },

  submitQuiz: async () => {
    try {
      set({ isSubmitting: true, error: null })

      const { currentAttempt, answers } = get()
      if (!currentAttempt) {
        throw new Error('No active quiz attempt')
      }

      const results = await quizAPI.submitQuiz(currentAttempt.attempt_id, answers)

      set({
        quizResults: results,
        isReviewMode: true,
        showExplanations: true,
        isSubmitting: false,
      })

      return results
    } catch (error: any) {
      set({
        error: error.message || 'Failed to submit quiz',
        isSubmitting: false,
      })
      throw error
    }
  },

  pauseQuiz: async () => {
    try {
      const { currentAttempt } = get()
      if (!currentAttempt) return

      await quizAPI.pauseQuiz(currentAttempt.attempt_id)

      // Stop timer
      get().stopTimer()
    } catch (error: any) {
      set({ error: error.message || 'Failed to pause quiz' })
      throw error
    }
  },

  resumeQuiz: async () => {
    try {
      const { currentAttempt } = get()
      if (!currentAttempt) return

      await quizAPI.resumeQuiz(currentAttempt.attempt_id)

      // Restart timer if quiz has time limit
      const { timeRemaining } = get()
      if (timeRemaining > 0) {
        get().startTimer()
      }
    } catch (error: any) {
      set({ error: error.message || 'Failed to resume quiz' })
      throw error
    }
  },

  resetQuiz: () => {
    set({
      currentQuiz: null,
      currentAttempt: null,
      questions: [],
      currentQuestionIndex: 0,
      answers: {},
      timeRemaining: 0,
      isSubmitting: false,
      error: null,
      quizResults: null,
      isReviewMode: false,
      showExplanations: false,
      canNavigateFreely: false,
    })

    // Stop timer
    get().stopTimer()
  },

  setTimeRemaining: (seconds: number) => {
    set({ timeRemaining: seconds })

    // Auto-submit when time runs out
    if (seconds <= 0) {
      const { isReviewMode, isSubmitting } = get()
      if (!isReviewMode && !isSubmitting) {
        get().submitQuiz()
      }
    }
  },

  getQuizResults: async (attemptId: number) => {
    try {
      set({ isLoading: true, error: null })

      const results = await quizAPI.getQuizResults(attemptId)

      set({
        quizResults: results,
        isLoading: false,
      })

      return results
    } catch (error: any) {
      set({
        error: error.message || 'Failed to get quiz results',
        isLoading: false,
      })
      throw error
    }
  },

  retakeQuiz: async () => {
    const { currentQuiz } = get()
    if (!currentQuiz) return

    // Reset state and start new attempt
    get().resetQuiz()
    await get().startQuiz(currentQuiz.id)
  },

  clearError: () => set({ error: null }),

  // Timer management (not exposed in interface)
  timer: null as NodeJS.Timeout | null,

  startTimer: () => {
    const state = get() as any

    // Clear existing timer
    if (state.timer) {
      clearInterval(state.timer)
    }

    // Start new timer
    const timer = setInterval(() => {
      const { timeRemaining } = get()
      if (timeRemaining > 0) {
        // Route through setTimeRemaining — it owns the expiry behavior
        // (auto-submit at 0). Setting the field directly bypassed that,
        // so a timed-out quiz was never submitted.
        get().setTimeRemaining(timeRemaining - 1)
      } else {
        get().stopTimer()
      }
    }, 1000)

    set({ timer })
  },

  stopTimer: () => {
    const state = get() as any
    if (state.timer) {
      clearInterval(state.timer)
      set({ timer: null })
    }
  },
}))

// Selectors for quiz statistics and utilities
export const useQuizSelectors = () => {
  const store = useQuizStore()

  return {
    // Current question
    currentQuestion: store.questions[store.currentQuestionIndex] || null,

    // Progress
    progress: {
      currentIndex: store.currentQuestionIndex,
      total: store.questions.length,
      percentage: store.questions.length > 0
        ? Math.round(((store.currentQuestionIndex + 1) / store.questions.length) * 100)
        : 0,
    },

    // Answered questions
    answeredQuestions: Object.keys(store.answers).length,

    // Remaining questions
    remainingQuestions: store.questions.length - Object.keys(store.answers).length,

    // Time formatting
    formattedTimeRemaining: formatTime(store.timeRemaining),

    // Navigation helpers
    canGoNext: store.currentQuestionIndex < store.questions.length - 1,
    canGoPrevious: store.currentQuestionIndex > 0 && store.canNavigateFreely,
    isLastQuestion: store.currentQuestionIndex === store.questions.length - 1,
    isFirstQuestion: store.currentQuestionIndex === 0,

    // Answer for current question
    currentAnswer: store.questions[store.currentQuestionIndex]
      ? store.answers[store.questions[store.currentQuestionIndex].question_id] || ''
      : '',

    // Quiz completion status
    isQuizComplete: Object.keys(store.answers).length === store.questions.length,

    // Results summary (if available)
    resultsSummary: store.quizResults ? {
      score: Math.round((store.quizResults.earned_marks / store.quizResults.total_marks) * 100),
      passed: store.quizResults.earned_marks >= (store.currentQuiz?.quiz_passing_grade || 80) / 100 * store.quizResults.total_marks,
      totalQuestions: store.quizResults.total_questions,
      correctAnswers: store.quizResults.answers?.filter(a => a.is_correct).length || 0,
      timeSpent: store.quizResults.attempt_ended_at && store.quizResults.attempt_started_at
        ? formatDuration(
            new Date(store.quizResults.attempt_ended_at).getTime() -
            new Date(store.quizResults.attempt_started_at).getTime()
          )
        : 'N/A',
    } : null,
  }
}

// Helper functions
function formatTime(seconds: number): string {
  const hours = Math.floor(seconds / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  const remainingSeconds = seconds % 60

  if (hours > 0) {
    return `${hours}:${minutes.toString().padStart(2, '0')}:${remainingSeconds.toString().padStart(2, '0')}`
  }
  return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`
}

function formatDuration(milliseconds: number): string {
  const totalSeconds = Math.floor(milliseconds / 1000)
  const hours = Math.floor(totalSeconds / 3600)
  const minutes = Math.floor((totalSeconds % 3600) / 60)
  const seconds = totalSeconds % 60

  if (hours > 0) {
    return `${hours}h ${minutes}m ${seconds}s`
  }
  if (minutes > 0) {
    return `${minutes}m ${seconds}s`
  }
  return `${seconds}s`
}