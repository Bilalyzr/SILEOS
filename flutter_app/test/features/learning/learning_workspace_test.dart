import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sashalms/core/network/api_client.dart';
import 'package:sashalms/features/learning/learning_api.dart';
import 'package:sashalms/features/learning/learning_workspace.dart';
import 'package:sashalms/features/learning/recording_reader.dart';
import 'package:sashalms/features/dashboard/presentation/providers/monthly_revenue_provider.dart';

class MockClient extends ApiClient {
  MockClient() : super(baseUrl: 'http://example.invalid');
  final replies = <String, dynamic>{};
  final sent = <String, dynamic>{};
  Future<Response> respond(String path) async {
    if (!replies.containsKey(path)) throw StateError('Unexpected request: $path');
    final value = replies[path];
    if (value is Exception) throw value;
    return Response(requestOptions: RequestOptions(path: path), data: value, statusCode: 200);
  }
  @override
  Future<Response> get(String path, {Map<String, dynamic>? queryParameters, Options? options}) => respond(path);
  @override
  Future<Response> post(String path, {dynamic data, Map<String, dynamic>? queryParameters, Options? options}) { sent[path] = data; return respond(path); }
}

void main() {
  test('planner lesson URLs only map recognized internal lesson paths', () {
    expect(mobileLessonPath('/courses/9/lessons/lesson-26'), '/lessons/26');
    expect(mobileLessonPath('https://example.com/courses/9/lessons/lesson-26'),
        isNull);
    expect(mobileLessonPath('/courses/9/lessons/quiz-26'), isNull);
  });

  test(
      'monthly revenue groups the API daily evidence and leaves undefined growth unknown',
      () {
    final report = monthlyRevenueFromDaily({
      'points': [
        {'date': '2026-08-31', 'courses': 0, 'internships': 0},
        {'date': '2026-09-01', 'courses': 200, 'internships': 100},
        {'date': '2026-09-02', 'courses': 50, 'internships': 0},
      ]
    }, 12);
    expect(report.points.length, 2);
    expect(report.currentMonth!.revenue, 350);
    expect(report.currentMonth!.courses, 250);
    expect(report.changePct, isNull);
  });

  testWidgets(
      'mobile check submits multiple selections to the planner and distinguishes insufficient evidence',
      (tester) async {
    final client = MockClient();
    client.replies['/api/v1/planner/tasks/7/start'] = {'session_id':1,'questions':[{'question_id':-5,'title':'Choose the prime numbers','type':'multiple_select','options':['2','3','4']}]};
    client.replies['/api/v1/planner/tasks/7/submit'] = {'outcome':{'note':'Check saved.','score':100,'enough_evidence':false,'results':[]},'goal':{}};
    await tester.pumpWidget(ProviderScope(
        overrides: [learningApiProvider.overrideWithValue(LearningApi(client))],
        child: const MaterialApp(
            home: PracticeCheckPage(taskId: 7, title: 'Practice'))));
    await tester.pumpAndSettle();
    await tester.tap(find.text('2'));
    await tester.tap(find.text('3'));
    await tester.pump();
    await tester.tap(find.text('Submit check'));
    await tester.pumpAndSettle();
    expect(client.sent['/api/v1/planner/tasks/7/submit'], {
      'answers': {
        '-5': ['2', '3']
      }
    });
    expect(find.text('There is not enough evidence to conclude mastery.'),
        findsOneWidget);
    expect(find.text('Check saved.'), findsOneWidget);
  });

  testWidgets(
      'failed practice startup has a retry and does not show fabricated questions',
      (tester) async {
    final client = MockClient();
    client.replies['/api/v1/planner/tasks/7/start'] = Exception('Enrollment required');
    await tester.pumpWidget(ProviderScope(
        overrides: [learningApiProvider.overrideWithValue(LearningApi(client))],
        child: const MaterialApp(
            home: PracticeCheckPage(taskId: 7, title: 'Practice'))));
    await tester.pumpAndSettle();
    expect(find.textContaining('Enrollment required'), findsOneWidget);
    expect(find.text('Try again'), findsOneWidget);
    expect(find.text('Submit check'), findsNothing);
  });

  testWidgets(
      'recording transcript searches Tamil text without requiring video playback',
      (tester) async {
    final client = MockClient();
    client.replies['/api/v1/recording-lessons/16/reader'] = {'title':'Fractions','language':'ta','notes':'Class notes','recording_available':false,'chapters':[],'segments':[{'start':0,'text':'A fraction is part of a whole.'},{'start':61,'text':'தமிழ் பாடம்'}]};
    await tester.pumpWidget(ProviderScope(
        overrides: [learningApiProvider.overrideWithValue(LearningApi(client))],
        child: const MaterialApp(home: RecordingReaderPage(classId: 16))));
    await tester.pumpAndSettle();
    await tester.enterText(find.byType(TextField), 'தமிழ்');
    await tester.pump();
    expect(find.text('தமிழ் பாடம்'), findsOneWidget);
    expect(find.text('A fraction is part of a whole.'), findsNothing);
    expect(find.text('1:01'), findsOneWidget);
  });
}
