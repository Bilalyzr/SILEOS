import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';
import '../auth/presentation/providers/auth_provider.dart';
import 'learning_api.dart';

class LearningWorkspace extends ConsumerWidget {
  const LearningWorkspace({super.key});
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final teacher = ref.watch(authProvider).maybeWhen(
        authenticated: (u) => u.isInstructor || u.isAdmin, orElse: () => false);
    return DefaultTabController(
        length: teacher ? 2 : 1,
        child: Scaffold(
          appBar: AppBar(
              title: const Text('Learning workspace'),
              bottom: TabBar(tabs: [
                const Tab(text: 'My plan'),
                if (teacher) const Tab(text: 'Instructor reviews')
              ])),
          body: TabBarView(
              children: [const _PlanView(), if (teacher) const _ReviewView()]),
        ));
  }
}

class _PlanView extends ConsumerStatefulWidget {
  const _PlanView();
  @override
  ConsumerState<_PlanView> createState() => _PlanViewState();
}

class _PlanViewState extends ConsumerState<_PlanView> {
  bool busy = false;
  Future<void> run(Future<dynamic> Function() action) async {
    if (busy) return;
    setState(() => busy = true);
    try {
      await action();
      ref.invalidate(learningPlanProvider);
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text(e.toString())));
      }
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  @override
  Widget build(BuildContext context) => ref.watch(learningPlanProvider).when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => LearningError(
            message: e.toString(),
            retry: () => ref.invalidate(learningPlanProvider)),
        data: (data) {
          final courses = learningRows(data['courses']);
          final goals = learningRows(data['goals']);
          return RefreshIndicator(
              onRefresh: () async {
                ref.invalidate(learningPlanProvider);
                  await ref.read(learningPlanProvider.future);
              },
              child: ListView(
                  padding: const EdgeInsets.all(16),
                  physics: const AlwaysScrollableScrollPhysics(),
                  children: [
                    const Text(
                        'Build a daily plan around your course goal. Practice and delayed checks use your course question bank.'),
                    const SizedBox(height: 12),
                    FilledButton.icon(
                        onPressed: busy || courses.isEmpty
                            ? null
                            : () => _editGoal(courses),
                        icon: const Icon(Icons.add),
                        label: const Text('Create or update a goal')),
                    if (courses.isEmpty)
                      const Padding(
                          padding: EdgeInsets.all(16),
                          child: Text(
                              'Enroll in a course to create your first learning plan.')),
                    if (goals.isEmpty && courses.isNotEmpty)
                      const Padding(
                          padding: EdgeInsets.all(16),
                          child: Text(
                              'No goals yet. Choose a course and a target date.')),
                    for (final goal in goals)
                      Card(
                          child: Padding(
                              padding: const EdgeInsets.all(16),
                              child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Text(goal['title'] as String,
                                        style: Theme.of(context)
                                            .textTheme
                                            .titleLarge),
                                    Text(
                                        '${goal['daily_minutes']} min/day · Target ${goal['target_date']} · ${goal['status']}'),
                                    Text(
                                        'Estimated finish: ${goal['estimated_finish']} · ${goal['timezone']}'),
                                    for (final warning
                                        in (goal['warnings'] as List? ?? []))
                                      Text(warning.toString(),
                                          style: TextStyle(
                                              color: Theme.of(context)
                                                  .colorScheme
                                                  .error)),
                                    Wrap(spacing: 8, children: [
                                      TextButton(
                                          onPressed: busy
                                              ? null
                                              : () => _editGoal(courses, goal),
                                          child: const Text('Edit goal')),
                                      TextButton(
                                          onPressed:
                                              busy || goal['status'] != 'active'
                                                  ? null
                                                  : () => run(() => ref
                                                      .read(learningApiProvider)
                                                      .refreshGoal(
                                                          goal['id'] as int)),
                                          child: const Text('Rebuild plan')),
                                    ]),
                                    for (final task
                                        in learningRows(goal['tasks']))
                                      _task(goal, task),
                                    for (final intervention
                                        in learningRows(goal['interventions']))
                                      ListTile(
                                          contentPadding: EdgeInsets.zero,
                                          leading: const Icon(Icons.insights),
                                          title: Text(
                                              '${intervention['concept']} · ${intervention['status']}'),
                                          subtitle: Text([
                                            intervention['reason'],
                                            intervention['instructor_note']
                                          ].whereType<String>().join('\n'))),
                                  ]))),
                  ]));
        },
      );
  Widget _task(LearningData goal, LearningData task) {
    final available = !busy &&
        goal['status'] == 'active' &&
        task['status'] == 'pending' &&
        (task['not_before'] as String).compareTo(goal['today'] as String) <= 0;
    final check = task['kind'] == 'practice' || task['kind'] == 'followup';
    final lesson = mobileLessonPath(task['lesson_url'] as String?);
    final outcome = task['outcome'] as Map?;
    return Padding(
        padding: const EdgeInsets.symmetric(vertical: 8),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text('${task['title']} · ${task['minutes']} min',
              style: const TextStyle(fontWeight: FontWeight.w600)),
          Text(
              '${task['reason']}\nDue ${task['due_date']} · ${task['status']}'),
          if (outcome != null)
            Text(outcome['note']?.toString() ?? 'Check submitted.'),
          Wrap(spacing: 8, children: [
            if (lesson != null)
              TextButton(
                  onPressed: () => context.push(lesson),
                  child: const Text('Open lesson')),
            if (check)
              FilledButton.tonal(
                  onPressed: available
                      ? () async {
                          await Navigator.of(context).push(
                              MaterialPageRoute<void>(
                                  builder: (_) => PracticeCheckPage(
                                      taskId: task['id'] as int,
                                      title: task['title'] as String)));
                          ref.invalidate(learningPlanProvider);
                        }
                      : null,
                  child: const Text('Start understanding check'))
            else
              TextButton(
                  onPressed: available
                      ? () => run(() => ref
                          .read(learningApiProvider)
                          .taskAction(task['id'] as int, 'done'))
                      : null,
                  child: const Text('Mark studied')),
            if (task['status'] == 'pending')
              TextButton(
                  onPressed: available
                      ? () => run(() => ref
                          .read(learningApiProvider)
                          .taskAction(task['id'] as int, 'snooze'))
                      : null,
                  child: const Text('Snooze one day')),
          ]),
          if (!check)
            const Text(
                'Marking studied does not award course progress or mastery.',
                style: TextStyle(fontSize: 12)),
        ]));
  }

  Future<void> _editGoal(List<LearningData> courses,
      [LearningData? goal]) async {
    final saved = await Navigator.of(context).push<bool>(MaterialPageRoute(
        builder: (_) => _GoalEditor(courses: courses, goal: goal)));
    if (saved == true && mounted) ref.invalidate(learningPlanProvider);
  }
}

class _GoalEditor extends ConsumerStatefulWidget {
  const _GoalEditor({required this.courses, this.goal});
  final List<LearningData> courses;
  final LearningData? goal;
  @override
  ConsumerState<_GoalEditor> createState() => _GoalEditorState();
}

class _GoalEditorState extends ConsumerState<_GoalEditor> {
  final form = GlobalKey<FormState>();
  late final TextEditingController title, timezone;
  late int courseId, minutes;
  late DateTime date;
  bool active = true, busy = false;
  String? error;
  @override
  void initState() {
    super.initState();
    title = TextEditingController(
        text: widget.goal?['title'] as String? ?? 'Finish my course');
    timezone = TextEditingController(
        text: widget.goal?['timezone'] as String? ?? 'Asia/Kolkata');
    courseId = (widget.goal?['course_id'] ?? widget.courses.first['id']) as int;
    minutes = widget.goal?['daily_minutes'] as int? ?? 30;
    date = DateTime.tryParse(widget.goal?['target_date'] as String? ?? '') ??
        DateTime.now().add(const Duration(days: 30));
    active = widget.goal?['status'] != 'paused';
  }

  @override
  void dispose() {
    title.dispose();
    timezone.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => Scaffold(
      appBar: AppBar(title: const Text('Course goal')),
      body: Form(
          key: form,
          child: ListView(padding: const EdgeInsets.all(20), children: [
            DropdownButtonFormField<int>(
                value: courseId,
                decoration: const InputDecoration(labelText: 'Course'),
                items: widget.courses
                    .map((c) => DropdownMenuItem(
                        value: c['id'] as int,
                        child: Text(c['title'] as String,
                            overflow: TextOverflow.ellipsis)))
                    .toList(),
                isExpanded: true,
                onChanged: busy || widget.goal != null
                    ? null
                    : (v) => setState(() => courseId = v!)),
            TextFormField(
                controller: title,
                maxLength: 200,
                decoration: const InputDecoration(labelText: 'Your goal'),
                validator: (v) => (v?.trim().length ?? 0) < 3
                    ? 'Describe your goal in at least 3 characters.'
                    : null),
            TextFormField(
                controller: timezone,
                decoration: const InputDecoration(
                    labelText: 'Time zone',
                    helperText:
                        'IANA name, for example Asia/Kolkata or Europe/London'),
                validator: (v) =>
                    (v?.trim().isEmpty ?? true) ? 'Enter a time zone.' : null),
            Text('Daily study time: $minutes minutes'),
            Slider(
                value: minutes.toDouble(),
                min: 5,
                max: 180,
                divisions: 35,
                label: '$minutes minutes',
                onChanged:
                    busy ? null : (v) => setState(() => minutes = v.round())),
            ListTile(
                title: Text('Target: ${DateFormat('yyyy-MM-dd').format(date)}'),
                trailing: const Icon(Icons.calendar_month),
                onTap: busy
                    ? null
                    : () async {
                        final now = DateTime.now();
                        final today = DateTime(now.year, now.month, now.day);
                        final picked = await showDatePicker(
                            context: context,
                            initialDate: date.isBefore(today) ? today : date,
                            firstDate: today,
                            lastDate: today.add(const Duration(days: 730)));
                        if (picked != null && mounted) {
                          setState(() => date = picked);
                        }
                      }),
            SwitchListTile(
                title: const Text('Active goal'),
                subtitle: const Text('Pause to stop scheduled practice.'),
                value: active,
                onChanged: busy ? null : (v) => setState(() => active = v)),
            if (error != null)
              Text(error!,
                  style: TextStyle(color: Theme.of(context).colorScheme.error)),
            FilledButton(
                onPressed: busy
                    ? null
                    : () async {
                        if (!form.currentState!.validate()) return;
                        setState(() {
                          busy = true;
                          error = null;
                        });
                        try {
                          await ref.read(learningApiProvider).saveGoal({
                            'course_id': courseId,
                            'title': title.text.trim(),
                            'timezone': timezone.text.trim(),
                            'daily_minutes': minutes,
                            'target_date':
                                DateFormat('yyyy-MM-dd').format(date),
                            'status': active ? 'active' : 'paused'
                          });
                          if (context.mounted) Navigator.of(context).pop(true);
                        } catch (e) {
                          if (mounted) setState(() => error = e.toString());
                        } finally {
                          if (mounted) setState(() => busy = false);
                        }
                      },
                child: Text(busy ? 'Saving…' : 'Save goal')),
          ])));
}

class PracticeCheckPage extends ConsumerStatefulWidget {
  const PracticeCheckPage(
      {super.key, required this.taskId, required this.title});
  final int taskId;
  final String title;
  @override
  ConsumerState<PracticeCheckPage> createState() => _PracticeCheckPageState();
}

class _PracticeCheckPageState extends ConsumerState<PracticeCheckPage> {
  late Future<LearningData> session;
  final LearningData answers = {};
  LearningData? outcome;
  bool busy = false;
  String? error;
  @override
  void initState() {
    super.initState();
    session = ref.read(learningApiProvider).startCheck(widget.taskId);
  }

  @override
  Widget build(BuildContext context) => Scaffold(
      appBar: AppBar(title: Text(widget.title)),
      body: FutureBuilder<LearningData>(
          future: session,
          builder: (context, snapshot) {
            if (snapshot.hasError) {
              return LearningError(
                  message: snapshot.error.toString(),
                  retry: () => setState(() => session =
                      ref.read(learningApiProvider).startCheck(widget.taskId)));
            }
            if (!snapshot.hasData) {
              return const Center(child: CircularProgressIndicator());
            }
            if (outcome != null) {
              return ListView(padding: const EdgeInsets.all(20), children: [
                Text(outcome!['note']?.toString() ?? 'Check submitted.',
                    style: Theme.of(context).textTheme.titleLarge),
                if (outcome!['score'] != null)
                  Text('Score: ${outcome!['score']}%'),
                if (outcome!['enough_evidence'] != true)
                  const Text(
                      'There is not enough evidence to conclude mastery.'),
                if (outcome!['freshness_note'] != null)
                  Text(outcome!['freshness_note'].toString()),
                for (final result in learningRows(outcome!['results']))
                  ListTile(
                      leading: Icon(result['correct'] == true
                          ? Icons.check_circle
                          : Icons.info_outline),
                      title: Text(
                          'Expected: ${(result['expected'] as List? ?? []).join(', ')}'),
                      subtitle: Text(result['explanation']?.toString() ?? '')),
                FilledButton(
                    onPressed: () => Navigator.of(context).pop(),
                    child: const Text('Back to plan')),
              ]);
            }
            final questions = learningRows(snapshot.data!['questions']);
            return ListView(padding: const EdgeInsets.all(20), children: [
              for (final q in questions)
                Card(
                    child: Padding(
                        padding: const EdgeInsets.all(12),
                        child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(q['title'] as String,
                                  style:
                                      Theme.of(context).textTheme.titleMedium),
                              if ((q['options'] as List? ?? []).isEmpty)
                                TextFormField(
                                    key: ValueKey(q['question_id']),
                                    decoration: const InputDecoration(
                                        labelText: 'Your answer'),
                                    enabled: !busy,
                                    onChanged: (v) =>
                                        answers['${q['question_id']}'] = v)
                              else
                                for (final option in q['options'] as List)
                                  q['type'] == 'multiple_select'
                                      ? CheckboxListTile(
                                          title: Text(option.toString()),
                                          value:
                                              (answers[
                                                              '${q['question_id']}']
                                                          as List? ??
                                                      [])
                                                  .contains(option),
                                          onChanged: busy
                                              ? null
                                              : (v) => setState(() {
                                                    final selected = List<
                                                            String>.from(
                                                        answers['${q['question_id']}']
                                                                as List? ??
                                                            []);
                                                    if (v == true) {
                                                      selected.add(
                                                          option.toString());
                                                    } else {
                                                      selected.remove(option);
                                                    }
                                                    answers['${q['question_id']}'] =
                                                        selected;
                                                  }))
                                      : RadioListTile<String>(
                                          title: Text(option.toString()),
                                          value: option.toString(),
                                          groupValue:
                                              answers['${q['question_id']}']
                                                  as String?,
                                          onChanged: busy
                                              ? null
                                              : (v) => setState(() => answers[
                                                  '${q['question_id']}'] = v)),
                            ]))),
              if (error != null)
                Text(error!,
                    style:
                        TextStyle(color: Theme.of(context).colorScheme.error)),
              FilledButton(
                  onPressed: busy
                      ? null
                      : () async {
                          setState(() {
                            busy = true;
                            error = null;
                          });
                          try {
                            final result = await ref
                                .read(learningApiProvider)
                                .submitCheck(widget.taskId, answers);
                            if (mounted) {
                              setState(() => outcome =
                                  Map<String, dynamic>.from(
                                      result['outcome'] as Map));
                            }
                          } catch (e) {
                            if (mounted) setState(() => error = e.toString());
                          } finally {
                            if (mounted) setState(() => busy = false);
                          }
                        },
                  child: Text(busy ? 'Submitting…' : 'Submit check')),
            ]);
          }));
}

class _ReviewView extends ConsumerStatefulWidget {
  const _ReviewView();
  @override
  ConsumerState<_ReviewView> createState() => _ReviewViewState();
}

class _ReviewViewState extends ConsumerState<_ReviewView> {
  bool busy = false;
  @override
  Widget build(BuildContext context) => ref.watch(learningReviewsProvider).when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => LearningError(
            message: e.toString(),
            retry: () => ref.invalidate(learningReviewsProvider)),
        data: (data) {
          final rows = learningRows(data['interventions']);
          return RefreshIndicator(
              onRefresh: () async {
                ref.invalidate(learningReviewsProvider);
                  await ref.read(learningReviewsProvider.future);
              },
              child: ListView(
                  padding: const EdgeInsets.all(16),
                  physics: const AlwaysScrollableScrollPhysics(),
                  children: [
                    if (rows.isEmpty)
                      const Text('No learner interventions need review.'),
                    for (final row in rows)
                      Card(
                          child: Padding(
                              padding: const EdgeInsets.all(16),
                              child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Text(
                                        '${row['learner_name']} · ${row['course_title']}',
                                        style: Theme.of(context)
                                            .textTheme
                                            .titleMedium),
                                    Text(
                                        '${row['concept']} · ${row['status']}\n${row['reason']}'),
                                    Text(
                                        'Latest score: ${row['latest_score'] ?? 'Unknown'} · Delayed check: ${row['followup_score'] ?? 'Unknown'}'),
                                    if (row['instructor_note'] != null)
                                      Text(row['instructor_note'] as String),
                                    Wrap(spacing: 8, children: [
                                      for (final action in [
                                        'request_check',
                                        'dismiss'
                                      ])
                                        TextButton(
                                            onPressed: busy ||
                                                    row['goal_status'] !=
                                                        'active'
                                                ? null
                                                : () => review(
                                                    row['id'] as int, action),
                                            child: Text(action == 'dismiss'
                                                ? 'Close with note'
                                                : 'Request another check'))
                                    ]),
                                  ]))),
                  ]));
        },
      );
  Future<void> review(int id, String action) async {
    final text = await showDialog<String>(
        context: context, builder: (_) => const _ReviewNoteDialog());
    if (text == null || !mounted) return;
    setState(() => busy = true);
    try {
      await ref.read(learningApiProvider).review(id, action, text);
      ref.invalidate(learningReviewsProvider);
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text(e.toString())));
      }
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }
}

class LearningError extends StatelessWidget {
  const LearningError({super.key, required this.message, required this.retry});
  final String message;
  final VoidCallback retry;
  @override
  Widget build(BuildContext context) => Center(
      child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(mainAxisSize: MainAxisSize.min, children: [
            Text(message),
            const SizedBox(height: 12),
            OutlinedButton(onPressed: retry, child: const Text('Try again'))
          ])));
}

class _ReviewNoteDialog extends StatefulWidget {
  const _ReviewNoteDialog();
  @override
  State<_ReviewNoteDialog> createState() => _ReviewNoteDialogState();
}

class _ReviewNoteDialogState extends State<_ReviewNoteDialog> {
  final note = TextEditingController();
  String? error;
  @override
  void dispose() {
    note.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => AlertDialog(
          title: const Text('Instructor review'),
          content: TextField(
              controller: note,
              maxLength: 2000,
              maxLines: 4,
              decoration: InputDecoration(
                  labelText: 'Explain your decision', errorText: error)),
          actions: [
            TextButton(
                onPressed: () => Navigator.pop(context),
                child: const Text('Cancel')),
            TextButton(
                onPressed: () {
                  if (note.text.trim().length < 3) {
                    setState(() => error = 'Enter at least 3 characters.');
                    return;
                  }
                  Navigator.pop(context, note.text.trim());
                },
                child: const Text('Save review')),
          ]);
}
