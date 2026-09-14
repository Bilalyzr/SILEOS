// lib/features/live_classes/domain/repositories/live_class_repository.dart
import 'package:dartz/dartz.dart';
import '../../../../core/errors/failures.dart';
import '../entities/live_class.dart';

/// scope values accepted by GET /api/v1/live/classes (backend contract,
/// see Task 4 of the live-classes plan): upcoming | past | live.
abstract class LiveClassRepository {
  Future<Either<Failure, List<LiveClass>>> getClasses({String scope = 'upcoming'});

  Future<Either<Failure, LiveClass>> getClassById(int id);

  Future<Either<Failure, List<LiveClass>>> getLiveNow();

  Future<Either<Failure, LiveClassJoinToken>> joinToken(int classId);

  Future<Either<Failure, void>> heartbeat(int classId);

  /// GET /classes/{id}/recording-playback -> {video_id, hls_url, signed,
  /// expires_in}. Returns null hls_url when recording playback is not (yet)
  /// available; callers should show a "not available" state rather than an
  /// error for a 503/404.
  Future<Either<Failure, LiveClassRecordingPlayback?>> getRecordingPlayback(int classId);
}

class LiveClassRecordingPlayback {
  final String videoId;
  final String hlsUrl;
  final bool signed;
  final int expiresIn;

  const LiveClassRecordingPlayback({
    required this.videoId,
    required this.hlsUrl,
    required this.signed,
    required this.expiresIn,
  });
}
