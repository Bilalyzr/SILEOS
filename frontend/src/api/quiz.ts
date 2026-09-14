import { api, apiRequest } from './axios'
import { Quiz, QuizQuestion, QuizAttempt } from '@/types'

export const quizAPI = {
  // Get quiz by ID
  getQuiz: async (id: number): Promise<Quiz> => {
    return apiRequest(
      api.get(`/quizzes/${id}`)
    )
  },

  // Start a new quiz attempt
  startQuiz: async (quizId: number): Promise<{
    quiz: Quiz
    attempt: QuizAttempt
    questions: QuizQuestion[]
  }> => {
    return apiRequest(
      api.post(`/quizzes/${quizId}/start`)
    )
  },

  // Get existing quiz attempt
  getQuizAttempt: async (attemptId: number): Promise<QuizAttempt> => {
    return apiRequest(
      api.get(`/quiz-attempts/${attemptId}`)
    )
  },

  // Save answer for a question
  saveAnswer: async (
    attemptId: number,
    questionId: number,
    answer: string
  ): Promise<void> => {
    return apiRequest(
      api.post(`/quiz-attempts/${attemptId}/answers`, {
        question_id: questionId,
        given_answer: answer,
      })
    )
  },

  // Submit quiz attempt
  submitQuiz: async (
    attemptId: number,
    answers: Record<number, string>
  ): Promise<QuizAttempt> => {
    return apiRequest(
      api.post(`/quiz-attempts/${attemptId}/submit`, { answers })
    )
  },

  // Pause quiz attempt
  pauseQuiz: async (attemptId: number): Promise<void> => {
    return apiRequest(
      api.post(`/quiz-attempts/${attemptId}/pause`)
    )
  },

  // Resume quiz attempt
  resumeQuiz: async (attemptId: number): Promise<void> => {
    return apiRequest(
      api.post(`/quiz-attempts/${attemptId}/resume`)
    )
  },

  // Get quiz results
  getQuizResults: async (attemptId: number): Promise<QuizAttempt> => {
    return apiRequest(
      api.get(`/quiz-attempts/${attemptId}/results`)
    )
  },

  // Get user's quiz attempts for a quiz
  getUserQuizAttempts: async (quizId: number): Promise<QuizAttempt[]> => {
    return apiRequest(
      api.get(`/quizzes/${quizId}/attempts`)
    )
  },

  // Get quiz statistics
  getQuizStatistics: async (quizId: number): Promise<{
    total_attempts: number
    average_score: number
    pass_rate: number
    completion_rate: number
    average_time: string
  }> => {
    return apiRequest(
      api.get(`/quizzes/${quizId}/statistics`)
    )
  },

  // Get course quizzes
  getCourseQuizzes: async (courseId: number): Promise<Quiz[]> => {
    return apiRequest(
      api.get(`/courses/${courseId}/quizzes`)
    )
  },

  // Instructor-specific endpoints
  instructor: {
    // Create quiz
    createQuiz: async (courseId: number, quizData: Partial<Quiz>): Promise<Quiz> => {
      return apiRequest(
        api.post(`/courses/${courseId}/quizzes`, quizData)
      )
    },

    // Update quiz
    updateQuiz: async (quizId: number, quizData: Partial<Quiz>): Promise<Quiz> => {
      return apiRequest(
        api.put(`/instructor/quizzes/${quizId}`, quizData)
      )
    },

    // Delete quiz
    deleteQuiz: async (quizId: number): Promise<void> => {
      return apiRequest(
        api.delete(`/instructor/quizzes/${quizId}`)
      )
    },

    // Add question to quiz
    addQuestion: async (
      quizId: number,
      questionData: Partial<QuizQuestion>
    ): Promise<QuizQuestion> => {
      return apiRequest(
        api.post(`/quizzes/${quizId}/questions`, questionData)
      )
    },

    // Update question
    updateQuestion: async (
      questionId: number,
      questionData: Partial<QuizQuestion>
    ): Promise<QuizQuestion> => {
      return apiRequest(
        api.put(`/instructor/quiz-questions/${questionId}`, questionData)
      )
    },

    // Delete question
    deleteQuestion: async (questionId: number): Promise<void> => {
      return apiRequest(
        api.delete(`/instructor/quiz-questions/${questionId}`)
      )
    },

    // Reorder questions
    reorderQuestions: async (
      quizId: number,
      questionIds: number[]
    ): Promise<void> => {
      return apiRequest(
        api.put(`/instructor/quizzes/${quizId}/reorder-questions`, {
          question_ids: questionIds,
        })
      )
    },

    // Get quiz attempts (for instructor review)
    getQuizAttempts: async (quizId: number): Promise<QuizAttempt[]> => {
      return apiRequest(
        api.get(`/instructor/quizzes/${quizId}/attempts`)
      )
    },

    // Grade quiz attempt manually
    gradeAttempt: async (
      attemptId: number,
      grades: Array<{
        question_id: number
        achieved_mark: number
        feedback?: string
      }>
    ): Promise<QuizAttempt> => {
      return apiRequest(
        api.post(`/instructor/quiz-attempts/${attemptId}/grade`, { grades })
      )
    },

    // Get quiz analytics
    getQuizAnalytics: async (quizId: number): Promise<{
      total_attempts: number
      completion_rate: number
      average_score: number
      score_distribution: Record<string, number>
      difficult_questions: Array<{
        question_id: number
        question_title: string
        success_rate: number
      }>
      student_performance: Array<{
        user_id: number
        user_name: string
        attempts: number
        best_score: number
        latest_attempt: string
      }>
    }> => {
      return apiRequest(
        api.get(`/instructor/quizzes/${quizId}/analytics`)
      )
    },

    // Export quiz results
    exportQuizResults: async (quizId: number, format: 'csv' | 'excel'): Promise<Blob> => {
      const response = await api.get(`/instructor/quizzes/${quizId}/export`, {
        params: { format },
        responseType: 'blob',
      })
      return response.data
    },

    // Duplicate quiz
    duplicateQuiz: async (quizId: number): Promise<Quiz> => {
      return apiRequest(
        api.post(`/instructor/quizzes/${quizId}/duplicate`)
      )
    },

    // Import questions from file
    importQuestions: async (
      quizId: number,
      file: File,
      format: 'csv' | 'json'
    ): Promise<{
      imported: number
      failed: number
      errors: string[]
    }> => {
      const formData = new FormData()
      formData.append('file', file)
      formData.append('format', format)

      return apiRequest(
        api.post(`/instructor/quizzes/${quizId}/import-questions`, formData, {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
        })
      )
    },

    // Get question bank (reusable questions)
    getQuestionBank: async (): Promise<QuizQuestion[]> => {
      return apiRequest(
        api.get('/instructor/question-bank')
      )
    },

    // Add question to question bank
    addToQuestionBank: async (
      questionData: Partial<QuizQuestion>
    ): Promise<QuizQuestion> => {
      return apiRequest(
        api.post('/instructor/question-bank', questionData)
      )
    },

    // Add existing question from bank to quiz
    addQuestionFromBank: async (
      quizId: number,
      questionId: number
    ): Promise<void> => {
      return apiRequest(
        api.post(`/instructor/quizzes/${quizId}/add-from-bank`, {
          question_id: questionId,
        })
      )
    },
  },
}