import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../providers/quiz_provider.dart';
import '../../domain/entities/quiz.dart';
import '../../../../shared/widgets/common/app_loader.dart';
import '../../../../shared/widgets/common/error_display.dart';

class QuizTakingPage extends ConsumerStatefulWidget {
  final int courseId;
  final int quizId;

  const QuizTakingPage({
    super.key,
    required this.courseId,
    required this.quizId,
  });

  @override
  ConsumerState<QuizTakingPage> createState() => _QuizTakingPageState();
}

class _QuizTakingPageState extends ConsumerState<QuizTakingPage> {
  int _currentQuestionIndex = 0;
  final Map<String, dynamic> _answers = {};
  int? _attemptId;
  bool _isSubmitting = false;
  String? _startError;
  bool _isStarting = false;

  @override
  void initState() {
    super.initState();
    _startAttempt();
  }

  Future<void> _startAttempt() async {
    if (_isStarting) return;
    setState(() { _isStarting = true; _startError = null; });
    final result = await ref.read(startQuizAttemptUseCaseProvider).call(widget.quizId);
    if (!mounted) return;
    setState(() => _isStarting = false);
    result.fold(
      (failure) {
        if (mounted) {
          setState(() => _startError = 'Failed to start quiz: ${failure.message}');
        }
      },
      (attemptId) {
        setState(() {
          _attemptId = attemptId;
        });
      },
    );
  }

  Future<void> _submitQuiz() async {
    if (_attemptId == null) return;

    setState(() {
      _isSubmitting = true;
    });

    final result = await ref.read(submitQuizAttemptUseCaseProvider).call(
          attemptId: _attemptId!,
          answers: _answers,
        );
    if (!mounted) return;

    setState(() {
      _isSubmitting = false;
    });

    result.fold(
      (failure) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Submission failed: ${failure.message}')),
        );
      },
      (results) {
        _showResults(results);
      },
    );
  }

  void _showResults(Map<String, dynamic> results) {
    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (context) => AlertDialog(
        title: Text(results['passed'] ? 'Quiz Passed! 🎉' : 'Quiz Failed'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Score: ${results['percentage']}%'),
            Text('Earned Marks: ${results['earned_marks']} / ${results['total_marks']}'),
            Text('Passing Grade: ${results['passing_grade']}%'),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () {
              context.pop(); // Pop dialog
              context.pop(); // Pop quiz page
            },
            child: const Text('OK'),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final quizAsync = ref.watch(quizProvider(courseId: widget.courseId, quizId: widget.quizId));

    return Scaffold(
      appBar: AppBar(
        title: quizAsync.maybeWhen(
          data: (quiz) => Text(quiz.title),
          orElse: () => const Text('Quiz'),
        ),
      ),
      body: _startError != null ? ErrorDisplay(message: _startError!, onRetry: () {
        ref.invalidate(quizProvider(courseId: widget.courseId, quizId: widget.quizId));
        _startAttempt();
      }) : quizAsync.when(
        data: (quiz) {
          if (_attemptId == null) return const BrandedLoader();
          if (quiz.questions.isEmpty) return const EmptyState(message: 'This quiz has no published questions yet.', icon: Icons.quiz_outlined);

          final question = quiz.questions[_currentQuestionIndex];

          return Padding(
            padding: const EdgeInsets.all(16.0),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                // Progress
                ClipRRect(
                  borderRadius: BorderRadius.circular(8),
                  child: LinearProgressIndicator(
                    value: (_currentQuestionIndex + 1) / quiz.questions.length,
                    minHeight: 10,
                    backgroundColor:
                        Theme.of(context).colorScheme.primary.withOpacity(0.12),
                  ),
                ),
                const SizedBox(height: 8),
                Text(
                  'Question ${_currentQuestionIndex + 1} of ${quiz.questions.length}',
                  style: Theme.of(context).textTheme.bodySmall,
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: 24),
                // Question Title
                Text(
                  question.title,
                  style: Theme.of(context)
                      .textTheme
                      .titleLarge
                      ?.copyWith(fontWeight: FontWeight.w800),
                ),
                const SizedBox(height: 16),
                // Options
                Expanded(
                  child: _buildQuestionOptions(question),
                ),
                // Navigation Buttons
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    if (_currentQuestionIndex > 0)
                      OutlinedButton(
                        onPressed: () {
                          setState(() {
                            _currentQuestionIndex--;
                          });
                        },
                        child: const Text('Previous'),
                      )
                    else
                      const SizedBox.shrink(),
                    ElevatedButton(
                      onPressed: _isSubmitting
                          ? null
                          : () {
                              if (_currentQuestionIndex < quiz.questions.length - 1) {
                                setState(() {
                                  _currentQuestionIndex++;
                                });
                              } else {
                                _submitQuiz();
                              }
                            },
                      child: _isSubmitting
                          ? const SizedBox(
                              width: 20,
                              height: 20,
                              child: CircularProgressIndicator(strokeWidth: 2),
                            )
                          : Text(_currentQuestionIndex < quiz.questions.length - 1 ? 'Next' : 'Submit Quiz'),
                    ),
                  ],
                ),
              ],
            ),
          );
        },
        loading: () => const BrandedLoader(),
        error: (error, stack) => ErrorDisplay(
          message: error.toString(),
          onRetry: () => ref.refresh(quizProvider(courseId: widget.courseId, quizId: widget.quizId)),
        ),
      ),
    );
  }

  Widget _buildQuestionOptions(QuizQuestion question) {
    if (question.type == 'multiple_choice') {
      return ListView.builder(
        itemCount: question.options.length,
        itemBuilder: (context, index) {
          final option = question.options[index];
          final isSelected = _answers[question.id] == index;

          final scheme = Theme.of(context).colorScheme;
          return Card(
            elevation: isSelected ? 3 : 0,
            color: isSelected ? scheme.primary.withOpacity(0.10) : null,
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(16),
              side: BorderSide(
                color: isSelected ? scheme.primary : scheme.outlineVariant,
                width: isSelected ? 2 : 1,
              ),
            ),
            child: RadioListTile<int>(
              title: Text(option.title),
              value: index,
              groupValue: _answers[question.id] as int?,
              onChanged: (value) {
                setState(() {
                  _answers[question.id] = value;
                });
              },
            ),
          );
        },
      );
    } else if (question.type == 'true_false') {
      return Column(
        children: [
          RadioListTile<String>(
            title: const Text('True'),
            value: 'true',
            groupValue: _answers[question.id] as String?,
            onChanged: (value) {
              setState(() {
                _answers[question.id] = value;
              });
            },
          ),
          RadioListTile<String>(
            title: const Text('False'),
            value: 'false',
            groupValue: _answers[question.id] as String?,
            onChanged: (value) {
              setState(() {
                _answers[question.id] = value;
              });
            },
          ),
        ],
      );
    } else {
      return TextField(
        decoration: const InputDecoration(
          hintText: 'Enter your answer here...',
          border: OutlineInputBorder(),
        ),
        onChanged: (value) {
          _answers[question.id] = value;
        },
      );
    }
  }
}
