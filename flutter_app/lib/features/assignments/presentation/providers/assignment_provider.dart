import 'dart:io';
import 'package:riverpod_annotation/riverpod_annotation.dart';
import '../../../../core/network/network_provider.dart';
import '../../data/datasources/assignment_remote_datasource.dart';
import '../../data/repositories/assignment_repository_impl.dart';
import '../../domain/entities/assignment.dart';
import '../../domain/repositories/assignment_repository.dart';

part 'assignment_provider.g.dart';

@riverpod
AssignmentRemoteDataSource assignmentRemoteDataSource(AssignmentRemoteDataSourceRef ref) {
  return AssignmentRemoteDataSourceImpl(
    apiClient: ref.watch(apiClientProvider),
  );
}

@riverpod
AssignmentRepository assignmentRepository(AssignmentRepositoryRef ref) {
  return AssignmentRepositoryImpl(
    remoteDataSource: ref.watch(assignmentRemoteDataSourceProvider),
  );
}

@riverpod
Future<Assignment> assignment(AssignmentRef ref, int id) async {
  final result = await ref.watch(assignmentRepositoryProvider).getAssignment(id);
  return result.fold(
    (failure) => throw failure,
    (assignment) => assignment,
  );
}

class AssignmentSubmissionNotifier extends AutoDisposeAsyncNotifier<AssignmentSubmission?> {
  @override
  Future<AssignmentSubmission?> build() async => null;

  Future<void> submit({
    required int assignmentId,
    required String content,
    File? file,
  }) async {
    state = const AsyncLoading();
    final result = await ref.read(assignmentRepositoryProvider).submitAssignment(
      assignmentId: assignmentId,
      content: content,
      file: file,
    );
    
    result.fold(
      (failure) => state = AsyncError(failure, StackTrace.current),
      (submission) => state = AsyncData(submission),
    );
  }
}

final assignmentSubmissionProvider = AsyncNotifierProvider.autoDispose<AssignmentSubmissionNotifier, AssignmentSubmission?>(
  () => AssignmentSubmissionNotifier(),
);
