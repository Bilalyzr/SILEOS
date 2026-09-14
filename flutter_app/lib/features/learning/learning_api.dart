import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../core/network/api_client.dart';
import '../../core/network/network_provider.dart';

typedef LearningData = Map<String, dynamic>;
List<LearningData> learningRows(dynamic value) => (value as List? ?? [])
    .map((e) => Map<String, dynamic>.from(e as Map))
    .toList();

class LearningApi {
  LearningApi(this.client);
  final ApiClient client;
  Future<LearningData> get(String path) async => Map<String, dynamic>.from(
      (await client.get('/api/v1/$path')).data as Map);
  Future<LearningData> post(String path, [LearningData? data]) async =>
      Map<String, dynamic>.from(
          (await client.post('/api/v1/$path', data: data)).data as Map);
  Future<LearningData> planner() => get('planner/me');
  Future<LearningData> saveGoal(LearningData goal) =>
      post('planner/goals', goal);
  Future<LearningData> refreshGoal(int id) => post('planner/goals/$id/refresh');
  Future<LearningData> taskAction(int id, String action) =>
      post('planner/tasks/$id/action', {'action': action});
  Future<LearningData> startCheck(int id) => post('planner/tasks/$id/start');
  Future<LearningData> submitCheck(int id, LearningData answers) =>
      post('planner/tasks/$id/submit', {'answers': answers});
  Future<LearningData> reviewQueue() => get('planner/instructor/interventions');
  Future<LearningData> review(int id, String action, String note) => post(
      'planner/instructor/interventions/$id/review',
      {'action': action, 'note': note});
  Future<LearningData> recording(int id) => get('recording-lessons/$id/reader');
}

final learningApiProvider =
    Provider((ref) => LearningApi(ref.watch(apiClientProvider)));
final learningPlanProvider = FutureProvider.autoDispose(
    (ref) => ref.watch(learningApiProvider).planner());
final learningReviewsProvider = FutureProvider.autoDispose(
    (ref) => ref.watch(learningApiProvider).reviewQueue());
final recordingReaderProvider = FutureProvider.autoDispose
    .family<LearningData, int>(
        (ref, id) => ref.watch(learningApiProvider).recording(id));

/// Web planner URLs carry a course context. The mobile lesson route takes only its id.
String? mobileLessonPath(String? url) {
  final match =
      RegExp(r'^/courses/\d+/lessons/lesson-(\d+)$').firstMatch(url ?? '');
  return match == null ? null : '/lessons/${match.group(1)}';
}
