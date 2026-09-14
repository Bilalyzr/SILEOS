import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../shared/widgets/video/video_player_widget.dart';
import '../live_classes/presentation/providers.dart';
import 'learning_api.dart';
import 'learning_workspace.dart';

class RecordingReaderPage extends ConsumerStatefulWidget {
  const RecordingReaderPage({super.key, required this.classId});
  final int classId;
  @override
  ConsumerState<RecordingReaderPage> createState() =>
      _RecordingReaderPageState();
}

class _RecordingReaderPageState extends ConsumerState<RecordingReaderPage> {
  String search = '';
  @override
  Widget build(BuildContext context) => Scaffold(
      appBar: AppBar(title: const Text('Recording notes & transcript')),
      body: ref.watch(recordingReaderProvider(widget.classId)).when(
            loading: () => const Center(child: CircularProgressIndicator()),
            error: (e, _) => LearningError(
                message:
                    'The transcript may not be published yet, or your enrollment may have changed.\n$e',
                retry: () =>
                    ref.invalidate(recordingReaderProvider(widget.classId))),
            data: (data) =>
                ListView(padding: const EdgeInsets.all(16), children: [
              Text(data['title'] as String,
                  style: Theme.of(context).textTheme.headlineSmall),
              Text('Transcript language: ${data['language']}'),
              const SizedBox(height: 12),
              if (data['recording_available'] == true)
                _RecordingPlayback(classId: widget.classId),
              const SizedBox(height: 16),
              Text('Lesson notes',
                  style: Theme.of(context).textTheme.titleLarge),
              SelectableText(data['notes'] as String? ?? ''),
              const SizedBox(height: 16),
              if (learningRows(data['chapters']).isNotEmpty)
                ExpansionTile(title: const Text('Chapters'), children: [
                  for (final chapter in learningRows(data['chapters']))
                    ListTile(
                        leading:
                            Text(recordingTimestamp(chapter['start'] as num)),
                        title: Text(chapter['title'] as String))
                ]),
              TextField(
                  decoration: const InputDecoration(
                      labelText: 'Search transcript',
                      prefixIcon: Icon(Icons.search)),
                  onChanged: (v) =>
                      setState(() => search = v.trim().toLowerCase())),
              const SizedBox(height: 12),
              for (final segment in learningRows(data['segments']).where(
                  (s) => (s['text'] as String).toLowerCase().contains(search)))
                Padding(
                    padding: const EdgeInsets.symmetric(vertical: 8),
                    child: Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          SizedBox(
                              width: 64,
                              child: Text(
                                  recordingTimestamp(segment['start'] as num))),
                          Expanded(
                              child: SelectableText(segment['text'] as String)),
                        ])),
              if (!learningRows(data['segments']).any(
                  (s) => (s['text'] as String).toLowerCase().contains(search)))
                const Text('No transcript lines match your search.'),
            ]),
          ));
}

String recordingTimestamp(num seconds) {
  final n = seconds.floor().clamp(0, 864000);
  return '${n ~/ 60}:${(n % 60).toString().padLeft(2, '0')}';
}

class _RecordingPlayback extends ConsumerWidget {
  const _RecordingPlayback({required this.classId});
  final int classId;
  @override
  Widget build(BuildContext context, WidgetRef ref) =>
      ref.watch(liveClassRecordingPlaybackProvider(classId)).when(
            data: (playback) => playback == null
                ? const Text(
                    'The recording is not available. You can still read the transcript.')
                : VideoPlayerWidget(videoUrl: playback.hlsUrl),
            loading: () => const LinearProgressIndicator(),
            error: (_, __) => Column(children: [
              const Text(
                  'Playback could not load. Notes and transcript remain available.'),
              TextButton(
                  onPressed: () => ref
                      .invalidate(liveClassRecordingPlaybackProvider(classId)),
                  child: const Text('Retry playback'))
            ]),
          );
}
