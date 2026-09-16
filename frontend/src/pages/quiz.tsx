import * as React from "react"
import { sanitizeHtml } from "@/utils/sanitize"
import { useParams, useNavigate } from "react-router-dom"
import {
  Clock,
  HelpCircle,
  ChevronLeft,
  ChevronRight,
  Flag,
  CheckCircle,
  XCircle,
  AlertTriangle,
  RotateCcw,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Progress } from "@/components/ui/progress"
import * as Dialog from "@radix-ui/react-dialog"
import { useQuizStore, useQuizSelectors } from "@/store/quiz"
import { api } from "@/api/axios"
import { cn } from "@/utils/cn"

export const QuizPage = () => {
  const { courseId, quizId } = useParams<{ courseId: string; quizId: string }>()
  const navigate = useNavigate()
  const [showSubmitDialog, setShowSubmitDialog] = React.useState(false)
  const [showExitDialog, setShowExitDialog] = React.useState(false)
  // Attempt usage from GET /courses/{courseId}/quizzes/{quizId}/attempts-count
  // — drives the retake gate (the old gate compared user_id, not attempts used).
  const [attemptsCount, setAttemptsCount] = React.useState<{
    attempts_used: number
    max_attempts: number
    unlimited: boolean
  } | null>(null)

  const {
    currentQuiz,
    questions,
    currentQuestionIndex,
    answers,
    timeRemaining,
    isSubmitting,
    isLoading,
    error,
    quizResults,
    isReviewMode,
    showExplanations,
    startQuiz,
    submitAnswer,
    navigateToQuestion,
    nextQuestion,
    previousQuestion,
    submitQuiz,
    retakeQuiz,
    resetQuiz,
  } = useQuizStore()

  const {
    currentQuestion,
    progress,
    answeredQuestions,
    formattedTimeRemaining,
    canGoNext,
    canGoPrevious,
    isLastQuestion,
    currentAnswer,
    isQuizComplete,
    resultsSummary,
  } = useQuizSelectors()

  // Start quiz on mount
  React.useEffect(() => {
    if (quizId && !currentQuiz) {
      startQuiz(parseInt(quizId))
    }
  }, [quizId, currentQuiz, startQuiz])

  // Fetch attempt usage once results are shown, so the retake gate reflects
  // attempts actually used (including the just-submitted attempt). Best-effort
  // — on failure the gate falls back to the quiz's unlimited-attempts flag.
  React.useEffect(() => {
    if (!quizResults || !courseId || !quizId) return
    api
      .get(`/courses/${courseId}/quizzes/${quizId}/attempts-count`)
      .then((response) => setAttemptsCount(response.data))
      .catch((error) => {
        console.error("Failed to fetch attempts count:", error)
      })
  }, [quizResults, courseId, quizId])

  // Cleanup on unmount
  React.useEffect(() => {
    return () => {
      if (!isReviewMode) {
        resetQuiz()
      }
    }
  }, [isReviewMode, resetQuiz])

  const handleAnswerSelect = (answerId: string) => {
    if (currentQuestion && !isReviewMode) {
      submitAnswer(currentQuestion.question_id, answerId)
    }
  }

  const handleSubmitQuiz = async () => {
    try {
      await submitQuiz()
      setShowSubmitDialog(false)
    } catch (error) {
      console.error("Failed to submit quiz:", error)
    }
  }

  const handleExitQuiz = () => {
    resetQuiz()
    navigate(`/courses/${courseId}`)
  }

  const handleRetakeQuiz = () => {
    retakeQuiz()
  }

  if (isLoading) {
    return (
      <div className="min-h-screen bg-neutral-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-500 mx-auto mb-4"></div>
          <p className="text-neutral-600">Loading quiz...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="min-h-screen bg-neutral-50 flex items-center justify-center">
        <Card className="max-w-md mx-auto">
          <CardContent className="p-6 text-center">
            <XCircle className="w-12 h-12 text-danger-500 mx-auto mb-4" />
            <h3 className="text-lg font-semibold mb-2">Error Loading Quiz</h3>
            <p className="text-neutral-600 mb-4">{error}</p>
            <Button onClick={() => navigate(`/courses/${courseId}`)}>
              Back to Course
            </Button>
          </CardContent>
        </Card>
      </div>
    )
  }

  if (!currentQuiz || !currentQuestion) {
    return null
  }

  // Results View
  if (quizResults && resultsSummary) {
    return (
      <div className="min-h-screen bg-neutral-50">
        <div className="container-custom py-8">
          <Card className="max-w-2xl mx-auto">
            <CardHeader className="text-center">
              <div className={cn(
                "w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-4",
                resultsSummary.passed ? "bg-success-100" : "bg-danger-100"
              )}>
                {resultsSummary.passed ? (
                  <CheckCircle className="w-8 h-8 text-success-600" />
                ) : (
                  <XCircle className="w-8 h-8 text-danger-600" />
                )}
              </div>
              <CardTitle className="text-2xl">
                {resultsSummary.passed ? "Congratulations!" : "Quiz Complete"}
              </CardTitle>
              <p className="text-neutral-600">
                {resultsSummary.passed
                  ? "You've successfully passed the quiz!"
                  : "You can review your answers and try again."
                }
              </p>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Score Summary */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-center">
                <div>
                  <div className="text-2xl font-bold text-primary-600">
                    {resultsSummary.score}%
                  </div>
                  <div className="text-sm text-neutral-600">Score</div>
                </div>
                <div>
                  <div className="text-2xl font-bold">
                    {resultsSummary.correctAnswers}/{resultsSummary.totalQuestions}
                  </div>
                  <div className="text-sm text-neutral-600">Correct</div>
                </div>
                <div>
                  <div className="text-2xl font-bold">
                    {resultsSummary.timeSpent}
                  </div>
                  <div className="text-sm text-neutral-600">Time</div>
                </div>
                <div>
                  <div className={cn(
                    "text-2xl font-bold",
                    resultsSummary.passed ? "text-success-600" : "text-danger-600"
                  )}>
                    {resultsSummary.passed ? "PASS" : "FAIL"}
                  </div>
                  <div className="text-sm text-neutral-600">Status</div>
                </div>
              </div>

              {/* Actions */}
              <div className="flex flex-col sm:flex-row gap-3">
                <Button
                  variant="outline"
                  className="flex-1"
                  onClick={() => navigate(`/courses/${courseId}`)}
                >
                  Back to Course
                </Button>
                {(attemptsCount
                  ? attemptsCount.unlimited ||
                    attemptsCount.attempts_used < attemptsCount.max_attempts
                  : currentQuiz.quiz_max_attempts_allowed === 0) && (
                  <Button className="flex-1" onClick={handleRetakeQuiz}>
                    <RotateCcw className="w-4 h-4 mr-2" />
                    Retake Quiz
                  </Button>
                )}
                <Button
                  variant="secondary"
                  className="flex-1"
                  onClick={() => window.location.reload()}
                >
                  Review Answers
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-neutral-50">
      {/* Header */}
      <div className="bg-white border-b border-neutral-200 sticky top-0 z-10">
        <div className="container-custom py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Button
                variant="ghost"
                size="icon"
                onClick={() => setShowExitDialog(true)}
              >
                <ChevronLeft className="w-5 h-5" />
              </Button>
              <div>
                <h1 className="font-semibold">{currentQuiz.post_title}</h1>
                <p className="text-sm text-neutral-600">
                  Question {progress.currentIndex + 1} of {progress.total}
                </p>
              </div>
            </div>

            <div className="flex items-center gap-4">
              {/* Timer */}
              {timeRemaining > 0 && !isReviewMode && (
                <div className="flex items-center gap-2 text-warning-600">
                  <Clock className="w-4 h-4" />
                  <span className="font-mono font-medium">
                    {formattedTimeRemaining}
                  </span>
                </div>
              )}

              {/* Progress */}
              <div className="hidden sm:flex items-center gap-2">
                <span className="text-sm text-neutral-600">{answeredQuestions} answered</span>
                <Progress value={progress.percentage} className="w-32" />
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="container-custom py-8">
        <div className="max-w-4xl mx-auto">
          <div className="grid lg:grid-cols-4 gap-8">
            {/* Question Content */}
            <div className="lg:col-span-3">
              <Card>
                <CardHeader>
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-2">
                        <Badge variant="outline">
                          Question {progress.currentIndex + 1}
                        </Badge>
                        <Badge variant="secondary">
                          {currentQuestion.question_mark} point{currentQuestion.question_mark !== 1 ? 's' : ''}
                        </Badge>
                      </div>
                      <h2 className="text-xl font-semibold">
                        {currentQuestion.question_title}
                      </h2>
                    </div>
                    {!isReviewMode && (
                      <Button variant="ghost" size="icon">
                        <Flag className="w-4 h-4" />
                      </Button>
                    )}
                  </div>
                </CardHeader>
                <CardContent>
                  {/* Question Description */}
                  {currentQuestion.question_description && (
                    <div
                      className="prose max-w-none mb-6"
                      dangerouslySetInnerHTML={{
                        __html: sanitizeHtml(currentQuestion.question_description)
                      }}
                    />
                  )}

                  {/* Answer Options */}
                  <div className="space-y-3">
                    {currentQuestion.answers?.map((answer) => {
                      const isSelected = currentAnswer === answer.answer_id.toString()
                      const isCorrect = answer.is_correct
                      const showCorrectAnswer = isReviewMode && showExplanations

                      return (
                        <label
                          key={answer.answer_id}
                          className={cn(
                            "block p-4 border rounded-lg cursor-pointer transition-all",
                            isSelected && !showCorrectAnswer && "border-primary-300 bg-primary-50",
                            showCorrectAnswer && isCorrect && "border-success-300 bg-success-50",
                            showCorrectAnswer && isSelected && !isCorrect && "border-danger-300 bg-danger-50",
                            !isSelected && !showCorrectAnswer && "border-neutral-200 hover:border-neutral-300",
                            isReviewMode && "cursor-default"
                          )}
                        >
                          <div className="flex items-start gap-3">
                            <input
                              type="radio"
                              name={`question-${currentQuestion.question_id}`}
                              value={answer.answer_id}
                              checked={isSelected}
                              onChange={() => handleAnswerSelect(answer.answer_id.toString())}
                              disabled={isReviewMode}
                              className="mt-1"
                            />
                            <div className="flex-1">
                              <div className="font-medium">{answer.answer_title}</div>
                              {showCorrectAnswer && (
                                <div className="mt-2 flex items-center gap-2">
                                  {isCorrect ? (
                                    <div className="flex items-center gap-1 text-success-600">
                                      <CheckCircle className="w-4 h-4" />
                                      <span className="text-sm">Correct Answer</span>
                                    </div>
                                  ) : isSelected ? (
                                    <div className="flex items-center gap-1 text-danger-600">
                                      <XCircle className="w-4 h-4" />
                                      <span className="text-sm">Your Answer</span>
                                    </div>
                                  ) : null}
                                </div>
                              )}
                            </div>
                          </div>
                        </label>
                      )
                    })}
                  </div>

                  {/* Explanation */}
                  {isReviewMode && showExplanations && currentQuestion.answer_explanation && (
                    <div className="mt-6 p-4 bg-neutral-50 rounded-lg">
                      <div className="flex items-start gap-2">
                        <HelpCircle className="w-5 h-5 text-primary-600 mt-0.5 flex-shrink-0" />
                        <div>
                          <h4 className="font-medium mb-2">Explanation</h4>
                          <div
                            className="text-sm text-neutral-700"
                            dangerouslySetInnerHTML={{
                              __html: sanitizeHtml(currentQuestion.answer_explanation)
                            }}
                          />
                        </div>
                      </div>
                    </div>
                  )}
                </CardContent>
              </Card>
            </div>

            {/* Sidebar */}
            <div className="lg:col-span-1">
              {/* Question Navigation */}
              <Card className="mb-6">
                <CardHeader>
                  <CardTitle className="text-lg">Questions</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-5 gap-2">
                    {questions.map((_, index) => {
                      const questionId = questions[index]?.question_id
                      const isAnswered = questionId && answers[questionId]
                      const isCurrent = index === currentQuestionIndex

                      return (
                        <button
                          key={index}
                          onClick={() => navigateToQuestion(index)}
                          className={cn(
                            "w-10 h-10 rounded-lg border-2 font-medium text-sm transition-all",
                            isCurrent && "border-primary-500 bg-primary-500 text-white",
                            !isCurrent && isAnswered && "border-success-500 bg-success-50 text-success-700",
                            !isCurrent && !isAnswered && "border-neutral-300 hover:border-neutral-400"
                          )}
                        >
                          {index + 1}
                        </button>
                      )
                    })}
                  </div>
                </CardContent>
              </Card>

              {/* Quiz Info */}
              <Card>
                <CardHeader>
                  <CardTitle className="text-lg">Quiz Info</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  <div className="flex justify-between">
                    <span>Questions</span>
                    <span>{questions.length}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Answered</span>
                    <span>{answeredQuestions}</span>
                  </div>
                  {currentQuiz.quiz_time_limit > 0 && (
                    <div className="flex justify-between">
                      <span>Time Limit</span>
                      <span>{currentQuiz.quiz_time_limit} min</span>
                    </div>
                  )}
                  <div className="flex justify-between">
                    <span>Passing Grade</span>
                    <span>{currentQuiz.quiz_passing_grade}%</span>
                  </div>
                </CardContent>
              </Card>
            </div>
          </div>

          {/* Navigation */}
          <div className="flex items-center justify-between mt-8">
            <Button
              variant="outline"
              onClick={previousQuestion}
              disabled={!canGoPrevious}
            >
              <ChevronLeft className="w-4 h-4 mr-2" />
              Previous
            </Button>

            <div className="flex gap-3">
              {!isReviewMode && (
                <Button
                  variant={isQuizComplete ? "default" : "outline"}
                  onClick={() => setShowSubmitDialog(true)}
                  disabled={isSubmitting}
                >
                  Submit Quiz
                </Button>
              )}

              <Button
                onClick={nextQuestion}
                disabled={!canGoNext}
              >
                {isLastQuestion ? "Finish" : "Next"}
                <ChevronRight className="w-4 h-4 ml-2" />
              </Button>
            </div>
          </div>
        </div>
      </div>

      {/* Submit Dialog */}
      <Dialog.Root open={showSubmitDialog} onOpenChange={setShowSubmitDialog}>
        <Dialog.Portal>
          <Dialog.Overlay className="fixed inset-0 bg-black/50 z-50" />
          <Dialog.Content className="fixed top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 bg-white rounded-lg shadow-xl z-50 w-full max-w-md p-6">
            <Dialog.Title className="text-lg font-semibold mb-4">
              Submit Quiz
            </Dialog.Title>
            <div className="space-y-4">
              <div className="flex items-start gap-3 p-4 bg-warning-50 rounded-lg">
                <AlertTriangle className="w-5 h-5 text-warning-600 mt-0.5" />
                <div>
                  <p className="font-medium text-warning-800">Are you sure?</p>
                  <p className="text-sm text-warning-700">
                    You have answered {answeredQuestions} out of {questions.length} questions.
                    Once submitted, you cannot change your answers.
                  </p>
                </div>
              </div>
              <div className="flex gap-3">
                <Dialog.Close asChild>
                  <Button variant="outline" className="flex-1">
                    Cancel
                  </Button>
                </Dialog.Close>
                <Button
                  className="flex-1"
                  onClick={handleSubmitQuiz}
                  loading={isSubmitting}
                >
                  Submit Quiz
                </Button>
              </div>
            </div>
          </Dialog.Content>
        </Dialog.Portal>
      </Dialog.Root>

      {/* Exit Dialog */}
      <Dialog.Root open={showExitDialog} onOpenChange={setShowExitDialog}>
        <Dialog.Portal>
          <Dialog.Overlay className="fixed inset-0 bg-black/50 z-50" />
          <Dialog.Content className="fixed top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 bg-white rounded-lg shadow-xl z-50 w-full max-w-md p-6">
            <Dialog.Title className="text-lg font-semibold mb-4">
              Exit Quiz
            </Dialog.Title>
            <div className="space-y-4">
              <p className="text-neutral-600">
                Are you sure you want to exit the quiz? Your progress will be lost.
              </p>
              <div className="flex gap-3">
                <Dialog.Close asChild>
                  <Button variant="outline" className="flex-1">
                    Stay
                  </Button>
                </Dialog.Close>
                <Button
                  variant="destructive"
                  className="flex-1"
                  onClick={handleExitQuiz}
                >
                  Exit Quiz
                </Button>
              </div>
            </div>
          </Dialog.Content>
        </Dialog.Portal>
      </Dialog.Root>
    </div>
  )
}