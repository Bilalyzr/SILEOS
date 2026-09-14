// lib/features/live_classes/presentation/providers.dart
import 'package:riverpod_annotation/riverpod_annotation.dart';
import '../../../core/network/network_provider.dart';
import '../data/live_class_api.dart';
import '../data/live_class_repository.dart';
import '../domain/entities/live_class.dart';
import '../domain/repositories/live_class_repository.dart';

part 'providers.g.dart';

@riverpod
LiveClassApi liveClassApi(LiveClassApiRef ref) {
  return LiveClassApiImpl(apiClient: ref.watch(apiClientProvider));
}

@riverpod
LiveClassRepository liveClassRepository(LiveClassRepositoryRef ref) {
  return LiveClassRepositoryImpl(api: ref.watch(liveClassApiProvider));
}

/// scope: upcoming | past | live — matches the backend query param exactly.
@riverpod
Future<List<LiveClass>> liveClasses(LiveClassesRef ref, {String scope = 'upcoming'}) async {
  final result = await ref.watch(liveClassRepositoryProvider).getClasses(scope: scope);
  return result.fold(
    (failure) => throw failure,
    (classes) => classes,
  );
}

@riverpod
Future<LiveClass> liveClassById(LiveClassByIdRef ref, int id) async {
  final result = await ref.watch(liveClassRepositoryProvider).getClassById(id);
  return result.fold(
    (failure) => throw failure,
    (liveClass) => liveClass,
  );
}

@riverpod
Future<List<LiveClass>> liveNowClasses(LiveNowClassesRef ref) async {
  final result = await ref.watch(liveClassRepositoryProvider).getLiveNow();
  return result.fold(
    (failure) => throw failure,
    (classes) => classes,
  );
}

/// Fetches a fresh join token; used by JoinLiveClassScreen right before
/// handing control to the Jitsi SDK. autoDispose: a stale token must never
/// be reused across screen visits.
@riverpod
Future<LiveClassJoinToken> liveClassJoinToken(LiveClassJoinTokenRef ref, int classId) async {
  final result = await ref.watch(liveClassRepositoryProvider).joinToken(classId);
  return result.fold(
    (failure) => throw failure,
    (token) => token,
  );
}

@riverpod
Future<LiveClassRecordingPlayback?> liveClassRecordingPlayback(
  LiveClassRecordingPlaybackRef ref,
  int classId,
) async {
  final result = await ref.watch(liveClassRepositoryProvider).getRecordingPlayback(classId);
  return result.fold(
    (failure) => throw failure,
    (playback) => playback,
  );
}
