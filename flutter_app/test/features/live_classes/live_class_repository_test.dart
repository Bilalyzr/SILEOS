// test/features/live_classes/live_class_repository_test.dart
//
// Mirrors test/auth_repository_test.dart's structure but uses a hand-written
// fake LiveClassApi instead of a mockito @GenerateNiceMocks build — this repo
// has no local Flutter/Dart toolchain to run build_runner (see the Task 9
// report), so a generated .mocks.dart file could not be produced/verified.
// The fake gives equivalent coverage for JSON mapping + status enums + the
// join-token payload shape without needing codegen.
import 'package:flutter_test/flutter_test.dart';
import 'package:dartz/dartz.dart';
import 'package:sashalms/core/errors/exceptions.dart';
import 'package:sashalms/core/errors/failures.dart';
import 'package:sashalms/features/live_classes/data/live_class_api.dart';
import 'package:sashalms/features/live_classes/data/live_class_repository.dart';
import 'package:sashalms/features/live_classes/data/models/live_class_model.dart';
import 'package:sashalms/features/live_classes/domain/entities/live_class.dart';

class _FakeLiveClassApi implements LiveClassApi {
  List<LiveClassModel> classesToReturn = const [];
  LiveClassModel? classByIdToReturn;
  Object? classByIdError;
  LiveClassJoinTokenModel? joinTokenToReturn;
  Object? joinTokenError;
  LiveClassRecordingPlaybackModel? playbackToReturn;

  @override
  Future<List<LiveClassModel>> getClasses({String scope = 'upcoming'}) async =>
      classesToReturn;

  @override
  Future<LiveClassModel> getClassById(int id) async {
    if (classByIdError != null) throw classByIdError!;
    return classByIdToReturn!;
  }

  @override
  Future<List<LiveClassModel>> getLiveNow() async => classesToReturn;

  @override
  Future<LiveClassJoinTokenModel> joinToken(int classId) async {
    if (joinTokenError != null) throw joinTokenError!;
    return joinTokenToReturn!;
  }

  @override
  Future<void> heartbeat(int classId) async {}

  @override
  Future<LiveClassRecordingPlaybackModel?> getRecordingPlayback(int classId) async =>
      playbackToReturn;
}

Map<String, dynamic> _rawLiveClassJson({
  String status = 'SCHEDULED',
  String recordingStatus = 'NONE',
}) {
  return {
    'id': 42,
    'course_id': 7,
    'lesson_id': null,
    'instructor_id': 3,
    'title': 'Intro to Algebra',
    'description': 'First live session',
    'scheduled_start': '2026-09-10T09:00:00Z',
    'scheduled_end': '2026-09-10T10:00:00Z',
    'timezone': 'Asia/Kolkata',
    'status': status,
    'room_name': 'si-abcd1234',
    'started_at': null,
    'ended_at': null,
    'live_participants': 0,
    'recording_video_id': null,
    'recording_status': recordingStatus,
    'settings': {
      'lobby_enabled': true,
      'start_muted': true,
      'allow_chat': true,
      'allow_share': true,
      'record': false,
      'attendance_threshold_pct': 60,
    },
    'server_ts': '2026-09-01T12:00:00Z',
    'can_start': false,
    'join_opens_at': '2026-09-10T08:45:00Z',
  };
}

void main() {
  group('LiveClassModel JSON mapping', () {
    test('maps every field exactly, including nested settings', () {
      final model = LiveClassModel.fromJson(_rawLiveClassJson());

      expect(model.id, 42);
      expect(model.courseId, 7);
      expect(model.lessonId, isNull);
      expect(model.instructorId, 3);
      expect(model.title, 'Intro to Algebra');
      expect(model.roomName, 'si-abcd1234');
      expect(model.timezone, 'Asia/Kolkata');
      expect(model.settings.attendanceThresholdPct, 60);
      expect(model.settings.lobbyEnabled, true);
      expect(model.canStart, false);
      expect(model.joinOpensAt, '2026-09-10T08:45:00Z');
    });

    test('maps status enum by NAME: SCHEDULED/LIVE/ENDED/CANCELLED', () {
      expect(LiveClassModel.fromJson(_rawLiveClassJson(status: 'SCHEDULED')).status,
          LiveClassStatus.scheduled);
      expect(LiveClassModel.fromJson(_rawLiveClassJson(status: 'LIVE')).status,
          LiveClassStatus.live);
      expect(LiveClassModel.fromJson(_rawLiveClassJson(status: 'ENDED')).status,
          LiveClassStatus.ended);
      expect(LiveClassModel.fromJson(_rawLiveClassJson(status: 'CANCELLED')).status,
          LiveClassStatus.cancelled);
    });

    test('unknown status string maps to LiveClassStatus.unknown, not a throw', () {
      final model = LiveClassModel.fromJson(_rawLiveClassJson(status: 'SOMETHING_NEW'));
      expect(model.status, LiveClassStatus.unknown);
    });

    test('maps recording status enum by NAME', () {
      expect(
        LiveClassModel.fromJson(_rawLiveClassJson(recordingStatus: 'AVAILABLE')).recordingStatus,
        RecordingStatus.available,
      );
      expect(
        LiveClassModel.fromJson(_rawLiveClassJson(recordingStatus: 'PROCESSING')).recordingStatus,
        RecordingStatus.processing,
      );
      expect(
        LiveClassModel.fromJson(_rawLiveClassJson(recordingStatus: 'FAILED')).recordingStatus,
        RecordingStatus.failed,
      );
    });

    test('toEntity() parses ISO timestamps and derives status booleans', () {
      final entity = LiveClassModel.fromJson(_rawLiveClassJson(status: 'LIVE')).toEntity();

      expect(entity.scheduledStart, DateTime.parse('2026-09-10T09:00:00Z'));
      expect(entity.serverTs, DateTime.parse('2026-09-01T12:00:00Z'));
      expect(entity.isLive, true);
      expect(entity.isEnded, false);
      expect(entity.hasRecording, false);
    });

    test('hasRecording is true only when AVAILABLE and a video id is set', () {
      final json = _rawLiveClassJson(status: 'ENDED', recordingStatus: 'AVAILABLE')
        ..['recording_video_id'] = 'bunny-guid-123';
      final entity = LiveClassModel.fromJson(json).toEntity();

      expect(entity.hasRecording, true);
      expect(entity.recordingVideoId, 'bunny-guid-123');
    });
  });

  group('LiveClassJoinTokenModel JSON mapping (join payload)', () {
    test('maps class_summary, room_name, jitsi_url, jwt, expires_in', () {
      final json = {
        'class_summary': _rawLiveClassJson(status: 'LIVE'),
        'room_name': 'si-abcd1234',
        'jitsi_url': 'https://live.sashainfinity.com',
        'jwt': 'header.payload.signature',
        'expires_in': 900,
      };

      final model = LiveClassJoinTokenModel.fromJson(json);
      final entity = model.toEntity();

      expect(entity.roomName, 'si-abcd1234');
      expect(entity.jitsiUrl, 'https://live.sashainfinity.com');
      expect(entity.jwt, 'header.payload.signature');
      expect(entity.expiresIn, 900);
      expect(entity.classSummary.isLive, true);
      expect(entity.classSummary.roomName, 'si-abcd1234');
    });
  });

  group('LiveClassRepositoryImpl', () {
    late _FakeLiveClassApi fakeApi;
    late LiveClassRepositoryImpl repository;

    setUp(() {
      fakeApi = _FakeLiveClassApi();
      repository = LiveClassRepositoryImpl(api: fakeApi);
    });

    test('getClassById returns Right(LiveClass) on success', () async {
      fakeApi.classByIdToReturn = LiveClassModel.fromJson(_rawLiveClassJson());

      final result = await repository.getClassById(42);

      expect(result.isRight(), true);
      result.fold(
        (_) => fail('expected Right'),
        (liveClass) => expect(liveClass.id, 42),
      );
    });

    test('getClassById maps ServerException to Failure.server', () async {
      fakeApi.classByIdError = const ServerException('boom', statusCode: 500);

      final result = await repository.getClassById(42);

      expect(result, equals(Left(Failure.server(message: 'boom', statusCode: 500))));
    });

    test('joinToken maps ForbiddenException to Failure.forbidden (non-enrolled student)', () async {
      fakeApi.joinTokenError = const ForbiddenException('Not enrolled');

      final result = await repository.joinToken(42);

      expect(result.isLeft(), true);
      result.fold(
        (failure) => expect(failure, isA<ForbiddenFailure>()),
        (_) => fail('expected Left'),
      );
    });

    test('joinToken returns Right(LiveClassJoinToken) on success', () async {
      fakeApi.joinTokenToReturn = LiveClassJoinTokenModel.fromJson({
        'class_summary': _rawLiveClassJson(status: 'LIVE'),
        'room_name': 'si-abcd1234',
        'jitsi_url': 'https://live.sashainfinity.com',
        'jwt': 'token123',
        'expires_in': 900,
      });

      final result = await repository.joinToken(42);

      expect(result.isRight(), true);
      result.fold(
        (_) => fail('expected Right'),
        (token) {
          expect(token.jwt, 'token123');
          expect(token.expiresIn, 900);
        },
      );
    });
  });
}
