// test/features/live_classes/live_class_list_screen_test.dart
//
// Renders LiveClassListScreen against a fake LiveClassRepository (overriding
// liveClassRepositoryProvider, the screen's one real dependency chain) and
// asserts an upcoming card renders with its title and a countdown string.
// No mockito/build_runner mocks needed — see the repository test file's note
// on why this repo authors fakes by hand (no local Flutter toolchain).
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:dartz/dartz.dart';
import 'package:sashalms/core/errors/failures.dart';
import 'package:sashalms/features/live_classes/domain/entities/live_class.dart';
import 'package:sashalms/features/live_classes/domain/repositories/live_class_repository.dart';
import 'package:sashalms/features/live_classes/presentation/live_class_list_screen.dart';
import 'package:sashalms/features/live_classes/presentation/providers.dart';

class _FakeLiveClassRepository implements LiveClassRepository {
  final List<LiveClass> upcoming;
  _FakeLiveClassRepository(this.upcoming);

  @override
  Future<Either<Failure, List<LiveClass>>> getClasses({String scope = 'upcoming'}) async =>
      Right(upcoming);

  @override
  Future<Either<Failure, LiveClass>> getClassById(int id) async =>
      Right(upcoming.firstWhere((c) => c.id == id));

  @override
  Future<Either<Failure, List<LiveClass>>> getLiveNow() async =>
      Right(upcoming.where((c) => c.isLive).toList());

  @override
  Future<Either<Failure, LiveClassJoinToken>> joinToken(int classId) async =>
      Left(Failure.unknown(message: 'not used in this test'));

  @override
  Future<Either<Failure, void>> heartbeat(int classId) async => const Right(null);

  @override
  Future<Either<Failure, LiveClassRecordingPlayback?>> getRecordingPlayback(int classId) async =>
      const Right(null);
}

LiveClass _upcomingClass({required DateTime scheduledStart, required DateTime serverTs}) {
  return LiveClass(
    id: 1,
    courseId: 10,
    instructorId: 5,
    title: 'Live Algebra Session',
    description: 'A test class',
    scheduledStart: scheduledStart,
    scheduledEnd: scheduledStart.add(const Duration(hours: 1)),
    timezone: 'Asia/Kolkata',
    status: LiveClassStatus.scheduled,
    roomName: 'si-testroom',
    liveParticipants: 0,
    recordingStatus: RecordingStatus.none,
    settings: const LiveClassSettings(),
    serverTs: serverTs,
    canStart: false,
    joinOpensAt: scheduledStart.subtract(const Duration(minutes: 15)),
  );
}

void main() {
  testWidgets('renders an upcoming class card with title and countdown text', (tester) async {
    final now = DateTime.now().toUtc();
    final scheduledStart = now.add(const Duration(hours: 2));
    final fakeRepo = _FakeLiveClassRepository([
      _upcomingClass(scheduledStart: scheduledStart, serverTs: now),
    ]);

    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          liveClassRepositoryProvider.overrideWithValue(fakeRepo),
        ],
        child: const MaterialApp(home: LiveClassListScreen()),
      ),
    );

    // Let the FutureProvider resolve.
    await tester.pumpAndSettle();

    expect(find.text('Live Algebra Session'), findsOneWidget);
    // Countdown target is ~1h45m out (join opens 15m before the 2h-out
    // start) — assert the "Starts in" prefix rather than an exact minute to
    // avoid flakiness from wall-clock time elapsing during the test.
    expect(find.textContaining('Starts in'), findsOneWidget);
  });

  testWidgets('shows a LIVE badge and "LIVE now" text for a live class', (tester) async {
    final now = DateTime.now().toUtc();
    final liveClass = _upcomingClass(
      scheduledStart: now.subtract(const Duration(minutes: 5)),
      serverTs: now,
    ).copyWith(status: LiveClassStatus.live, canStart: true);
    final fakeRepo = _FakeLiveClassRepository([liveClass]);

    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          liveClassRepositoryProvider.overrideWithValue(fakeRepo),
        ],
        child: const MaterialApp(home: LiveClassListScreen()),
      ),
    );

    await tester.pumpAndSettle();

    expect(find.text('LIVE'), findsOneWidget);
    expect(find.text('LIVE now'), findsOneWidget);
    expect(find.text('Join now'), findsOneWidget);
  });

  testWidgets('shows an empty state when there are no upcoming classes', (tester) async {
    final fakeRepo = _FakeLiveClassRepository(const []);

    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          liveClassRepositoryProvider.overrideWithValue(fakeRepo),
        ],
        child: const MaterialApp(home: LiveClassListScreen()),
      ),
    );

    await tester.pumpAndSettle();

    expect(find.text('No upcoming live classes yet.'), findsOneWidget);
  });
}
