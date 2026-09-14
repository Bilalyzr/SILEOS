import 'package:riverpod_annotation/riverpod_annotation.dart';
import '../../../../core/network/network_provider.dart';
import '../../data/datasources/quiz_remote_datasource.dart';
import '../../data/repositories/quiz_repository_impl.dart';
import '../../domain/entities/quiz.dart';
import '../../domain/repositories/quiz_repository.dart';
import '../../domain/usecases/quiz_usecases.dart';

part 'quiz_provider.g.dart';

@riverpod
QuizRemoteDataSource quizRemoteDataSource(QuizRemoteDataSourceRef ref) {
  return QuizRemoteDataSourceImpl(
    apiClient: ref.watch(apiClientProvider),
  );
}

@riverpod
QuizRepository quizRepository(QuizRepositoryRef ref) {
  return QuizRepositoryImpl(
    remoteDataSource: ref.watch(quizRemoteDataSourceProvider),
  );
}

@riverpod
GetQuizUseCase getQuizUseCase(GetQuizUseCaseRef ref) {
  return GetQuizUseCase(ref.watch(quizRepositoryProvider));
}

@riverpod
StartQuizAttemptUseCase startQuizAttemptUseCase(StartQuizAttemptUseCaseRef ref) {
  return StartQuizAttemptUseCase(ref.watch(quizRepositoryProvider));
}

@riverpod
SubmitQuizAttemptUseCase submitQuizAttemptUseCase(SubmitQuizAttemptUseCaseRef ref) {
  return SubmitQuizAttemptUseCase(ref.watch(quizRepositoryProvider));
}

@riverpod
Future<Quiz> quiz(QuizRef ref, {required int courseId, required int quizId}) async {
  final result = await ref.watch(getQuizUseCaseProvider).call(
        courseId: courseId,
        quizId: quizId,
      );

  return result.fold(
    (failure) => throw failure,
    (quiz) => quiz,
  );
}
