// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'quiz_provider.dart';

// **************************************************************************
// RiverpodGenerator
// **************************************************************************

String _$quizRemoteDataSourceHash() =>
    r'f9fe43faaee0b3eaec98952c2de80d1361ac30c2';

/// See also [quizRemoteDataSource].
@ProviderFor(quizRemoteDataSource)
final quizRemoteDataSourceProvider =
    AutoDisposeProvider<QuizRemoteDataSource>.internal(
  quizRemoteDataSource,
  name: r'quizRemoteDataSourceProvider',
  debugGetCreateSourceHash: const bool.fromEnvironment('dart.vm.product')
      ? null
      : _$quizRemoteDataSourceHash,
  dependencies: null,
  allTransitiveDependencies: null,
);

@Deprecated('Will be removed in 3.0. Use Ref instead')
// ignore: unused_element
typedef QuizRemoteDataSourceRef = AutoDisposeProviderRef<QuizRemoteDataSource>;
String _$quizRepositoryHash() => r'6d3401f3e6fa30e28e9f7775cf98e5e1dda879c3';

/// See also [quizRepository].
@ProviderFor(quizRepository)
final quizRepositoryProvider = AutoDisposeProvider<QuizRepository>.internal(
  quizRepository,
  name: r'quizRepositoryProvider',
  debugGetCreateSourceHash: const bool.fromEnvironment('dart.vm.product')
      ? null
      : _$quizRepositoryHash,
  dependencies: null,
  allTransitiveDependencies: null,
);

@Deprecated('Will be removed in 3.0. Use Ref instead')
// ignore: unused_element
typedef QuizRepositoryRef = AutoDisposeProviderRef<QuizRepository>;
String _$getQuizUseCaseHash() => r'032490b4bb27fcb79c137143592ab3cf8ee6a5c5';

/// See also [getQuizUseCase].
@ProviderFor(getQuizUseCase)
final getQuizUseCaseProvider = AutoDisposeProvider<GetQuizUseCase>.internal(
  getQuizUseCase,
  name: r'getQuizUseCaseProvider',
  debugGetCreateSourceHash: const bool.fromEnvironment('dart.vm.product')
      ? null
      : _$getQuizUseCaseHash,
  dependencies: null,
  allTransitiveDependencies: null,
);

@Deprecated('Will be removed in 3.0. Use Ref instead')
// ignore: unused_element
typedef GetQuizUseCaseRef = AutoDisposeProviderRef<GetQuizUseCase>;
String _$startQuizAttemptUseCaseHash() =>
    r'b0b703a59c7e0f15604368a0dfb94867d9e3c38f';

/// See also [startQuizAttemptUseCase].
@ProviderFor(startQuizAttemptUseCase)
final startQuizAttemptUseCaseProvider =
    AutoDisposeProvider<StartQuizAttemptUseCase>.internal(
  startQuizAttemptUseCase,
  name: r'startQuizAttemptUseCaseProvider',
  debugGetCreateSourceHash: const bool.fromEnvironment('dart.vm.product')
      ? null
      : _$startQuizAttemptUseCaseHash,
  dependencies: null,
  allTransitiveDependencies: null,
);

@Deprecated('Will be removed in 3.0. Use Ref instead')
// ignore: unused_element
typedef StartQuizAttemptUseCaseRef
    = AutoDisposeProviderRef<StartQuizAttemptUseCase>;
String _$submitQuizAttemptUseCaseHash() =>
    r'5aefc4c0084dbc2eeda0935e835867bc121cd6d3';

/// See also [submitQuizAttemptUseCase].
@ProviderFor(submitQuizAttemptUseCase)
final submitQuizAttemptUseCaseProvider =
    AutoDisposeProvider<SubmitQuizAttemptUseCase>.internal(
  submitQuizAttemptUseCase,
  name: r'submitQuizAttemptUseCaseProvider',
  debugGetCreateSourceHash: const bool.fromEnvironment('dart.vm.product')
      ? null
      : _$submitQuizAttemptUseCaseHash,
  dependencies: null,
  allTransitiveDependencies: null,
);

@Deprecated('Will be removed in 3.0. Use Ref instead')
// ignore: unused_element
typedef SubmitQuizAttemptUseCaseRef
    = AutoDisposeProviderRef<SubmitQuizAttemptUseCase>;
String _$quizHash() => r'e111ef7281f37ffcb18c60577dd3f099c49aa7a8';

/// Copied from Dart SDK
class _SystemHash {
  _SystemHash._();

  static int combine(int hash, int value) {
    // ignore: parameter_assignments
    hash = 0x1fffffff & (hash + value);
    // ignore: parameter_assignments
    hash = 0x1fffffff & (hash + ((0x0007ffff & hash) << 10));
    return hash ^ (hash >> 6);
  }

  static int finish(int hash) {
    // ignore: parameter_assignments
    hash = 0x1fffffff & (hash + ((0x03ffffff & hash) << 3));
    // ignore: parameter_assignments
    hash = hash ^ (hash >> 11);
    return 0x1fffffff & (hash + ((0x00003fff & hash) << 15));
  }
}

/// See also [quiz].
@ProviderFor(quiz)
const quizProvider = QuizFamily();

/// See also [quiz].
class QuizFamily extends Family<AsyncValue<Quiz>> {
  /// See also [quiz].
  const QuizFamily();

  /// See also [quiz].
  QuizProvider call({
    required int courseId,
    required int quizId,
  }) {
    return QuizProvider(
      courseId: courseId,
      quizId: quizId,
    );
  }

  @override
  QuizProvider getProviderOverride(
    covariant QuizProvider provider,
  ) {
    return call(
      courseId: provider.courseId,
      quizId: provider.quizId,
    );
  }

  static const Iterable<ProviderOrFamily>? _dependencies = null;

  @override
  Iterable<ProviderOrFamily>? get dependencies => _dependencies;

  static const Iterable<ProviderOrFamily>? _allTransitiveDependencies = null;

  @override
  Iterable<ProviderOrFamily>? get allTransitiveDependencies =>
      _allTransitiveDependencies;

  @override
  String? get name => r'quizProvider';
}

/// See also [quiz].
class QuizProvider extends AutoDisposeFutureProvider<Quiz> {
  /// See also [quiz].
  QuizProvider({
    required int courseId,
    required int quizId,
  }) : this._internal(
          (ref) => quiz(
            ref as QuizRef,
            courseId: courseId,
            quizId: quizId,
          ),
          from: quizProvider,
          name: r'quizProvider',
          debugGetCreateSourceHash:
              const bool.fromEnvironment('dart.vm.product') ? null : _$quizHash,
          dependencies: QuizFamily._dependencies,
          allTransitiveDependencies: QuizFamily._allTransitiveDependencies,
          courseId: courseId,
          quizId: quizId,
        );

  QuizProvider._internal(
    super._createNotifier, {
    required super.name,
    required super.dependencies,
    required super.allTransitiveDependencies,
    required super.debugGetCreateSourceHash,
    required super.from,
    required this.courseId,
    required this.quizId,
  }) : super.internal();

  final int courseId;
  final int quizId;

  @override
  Override overrideWith(
    FutureOr<Quiz> Function(QuizRef provider) create,
  ) {
    return ProviderOverride(
      origin: this,
      override: QuizProvider._internal(
        (ref) => create(ref as QuizRef),
        from: from,
        name: null,
        dependencies: null,
        allTransitiveDependencies: null,
        debugGetCreateSourceHash: null,
        courseId: courseId,
        quizId: quizId,
      ),
    );
  }

  @override
  AutoDisposeFutureProviderElement<Quiz> createElement() {
    return _QuizProviderElement(this);
  }

  @override
  bool operator ==(Object other) {
    return other is QuizProvider &&
        other.courseId == courseId &&
        other.quizId == quizId;
  }

  @override
  int get hashCode {
    var hash = _SystemHash.combine(0, runtimeType.hashCode);
    hash = _SystemHash.combine(hash, courseId.hashCode);
    hash = _SystemHash.combine(hash, quizId.hashCode);

    return _SystemHash.finish(hash);
  }
}

@Deprecated('Will be removed in 3.0. Use Ref instead')
// ignore: unused_element
mixin QuizRef on AutoDisposeFutureProviderRef<Quiz> {
  /// The parameter `courseId` of this provider.
  int get courseId;

  /// The parameter `quizId` of this provider.
  int get quizId;
}

class _QuizProviderElement extends AutoDisposeFutureProviderElement<Quiz>
    with QuizRef {
  _QuizProviderElement(super.provider);

  @override
  int get courseId => (origin as QuizProvider).courseId;
  @override
  int get quizId => (origin as QuizProvider).quizId;
}
// ignore_for_file: type=lint
// ignore_for_file: subtype_of_sealed_class, invalid_use_of_internal_member, invalid_use_of_visible_for_testing_member, deprecated_member_use_from_same_package
