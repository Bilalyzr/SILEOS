import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../providers/assignment_provider.dart';
import '../../../../shared/widgets/common/app_loader.dart';
import '../../../../shared/widgets/common/error_display.dart';

class AssignmentPage extends ConsumerStatefulWidget {
  final int assignmentId;

  const AssignmentPage({super.key, required this.assignmentId});

  @override
  ConsumerState<AssignmentPage> createState() => _AssignmentPageState();
}

class _AssignmentPageState extends ConsumerState<AssignmentPage> {
  final _contentController = TextEditingController();

  @override
  void dispose() {
    _contentController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final assignmentAsync = ref.watch(assignmentProvider(widget.assignmentId));
    final submissionState = ref.watch(assignmentSubmissionProvider);

    return Scaffold(
      appBar: AppBar(title: const Text('Assignment')),
      body: assignmentAsync.when(
        data: (assignment) => SingleChildScrollView(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Text(
                assignment.title,
                style: Theme.of(context).textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.w800),
              ),
              const SizedBox(height: 10),
              Align(
                alignment: Alignment.centerLeft,
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                  decoration: BoxDecoration(
                    color: Theme.of(context).colorScheme.primary.withOpacity(0.12),
                    borderRadius: BorderRadius.circular(999),
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(Icons.military_tech_rounded,
                          size: 16, color: Theme.of(context).colorScheme.primary),
                      const SizedBox(width: 6),
                      Text(
                        '${assignment.totalPoints} Points',
                        style: Theme.of(context).textTheme.labelLarge?.copyWith(
                              color: Theme.of(context).colorScheme.primary,
                              fontWeight: FontWeight.w800,
                            ),
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 16),
              if (assignment.description != null) ...[
                Text('Description', style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold)),
                const SizedBox(height: 8),
                Text(assignment.description!),
                const SizedBox(height: 24),
              ],
              if (assignment.isSubmitted) ...[
                Card(
                  color: Colors.green.withOpacity(0.1),
                  child: const Padding(
                    padding: EdgeInsets.all(16.0),
                    child: Row(
                      children: [
                        Icon(Icons.check_circle, color: Colors.green),
                        SizedBox(width: 12),
                        Text('Assignment Submitted Successfully'),
                      ],
                    ),
                  ),
                ),
                const SizedBox(height: 16),
                if (assignment.submission?.grade != null) ...[
                  Text('Grade: ${assignment.submission!.grade} / ${assignment.totalPoints}', 
                    style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 18)),
                  if (assignment.submission?.feedback != null)
                    Padding(
                      padding: const EdgeInsets.only(top: 8.0),
                      child: Text('Feedback: ${assignment.submission!.feedback}'),
                    ),
                ],
              ] else ...[
                Text('Your Submission', style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold)),
                const SizedBox(height: 8),
                TextField(
                  controller: _contentController,
                  maxLines: 5,
                  decoration: const InputDecoration(
                    hintText: 'Enter your assignment content here...',
                    border: OutlineInputBorder(),
                  ),
                ),
                const SizedBox(height: 16),
                ElevatedButton(
                  onPressed: submissionState is AsyncLoading
                      ? null
                      : () {
                          ref.read(assignmentSubmissionProvider.notifier).submit(
                                assignmentId: widget.assignmentId,
                                content: _contentController.text,
                              );
                        },
                  child: submissionState is AsyncLoading
                      ? const AppLoader()
                      : const Text('Submit Assignment'),
                ),
              ],
            ],
          ),
        ),
        loading: () => const BrandedLoader(),
        error: (error, stack) => ErrorDisplay(
          message: error.toString(),
          onRetry: () => ref.refresh(assignmentProvider(widget.assignmentId)),
        ),
      ),
    );
  }
}
