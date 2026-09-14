import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../../core/network/network_provider.dart';
import '../../data/datasources/profile_remote_datasource.dart';
import '../../data/repositories/profile_repository_impl.dart';
import '../../domain/repositories/profile_repository.dart';

final profileRemoteDataSourceProvider = Provider<ProfileRemoteDataSource>((ref) {
  return ProfileRemoteDataSourceImpl(
    apiClient: ref.watch(apiClientProvider),
  );
});

final profileRepositoryProvider = Provider<ProfileRepository>((ref) {
  return ProfileRepositoryImpl(
    remoteDataSource: ref.watch(profileRemoteDataSourceProvider),
  );
});

final profileFutureProvider = FutureProvider.autoDispose<Map<String, dynamic>>((ref) async {
  final repository = ref.watch(profileRepositoryProvider);
  final result = await repository.getProfile();
  return result.fold(
    (failure) => throw failure,
    (profileMap) => profileMap,
  );
});
