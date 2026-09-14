// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'assignment_provider.dart';

// **************************************************************************
// RiverpodGenerator
// **************************************************************************

String _$assignmentRemoteDataSourceHash() =>
    r'3d935c4c0f544773ed57e1012bd6471ee5a65cb1';

/// See also [assignmentRemoteDataSource].
@ProviderFor(assignmentRemoteDataSource)
final assignmentRemoteDataSourceProvider =
    AutoDisposeProvider<AssignmentRemoteDataSource>.internal(
  assignmentRemoteDataSource,
  name: r'assignmentRemoteDataSourceProvider',
  debugGetCreateSourceHash: const bool.fromEnvironment('dart.vm.product')
      ? null
      : _$assignmentRemoteDataSourceHash,
  dependencies: null,
  allTransitiveDependencies: null,
);

@Deprecated('Will be removed in 3.0. Use Ref instead')
// ignore: unused_element
typedef AssignmentRemoteDataSourceRef
    = AutoDisposeProviderRef<AssignmentRemoteDataSource>;
String _$assignmentRepositoryHash() =>
    r'4fdf0db580015cb3ec7520cd4f7a41969f073baa';

/// See also [assignmentRepository].
@ProviderFor(assignmentRepository)
final assignmentRepositoryProvider =
    AutoDisposeProvider<AssignmentRepository>.internal(
  assignmentRepository,
  name: r'assignmentRepositoryProvider',
  debugGetCreateSourceHash: const bool.fromEnvironment('dart.vm.product')
      ? null
      : _$assignmentRepositoryHash,
  dependencies: null,
  allTransitiveDependencies: null,
);

@Deprecated('Will be removed in 3.0. Use Ref instead')
// ignore: unused_element
typedef AssignmentRepositoryRef = AutoDisposeProviderRef<AssignmentRepository>;
String _$assignmentHash() => r'62d449028617420bd145104afa407924e3fbee19';

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

/// See also [assignment].
@ProviderFor(assignment)
const assignmentProvider = AssignmentFamily();

/// See also [assignment].
class AssignmentFamily extends Family<AsyncValue<Assignment>> {
  /// See also [assignment].
  const AssignmentFamily();

  /// See also [assignment].
  AssignmentProvider call(
    int id,
  ) {
    return AssignmentProvider(
      id,
    );
  }

  @override
  AssignmentProvider getProviderOverride(
    covariant AssignmentProvider provider,
  ) {
    return call(
      provider.id,
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
  String? get name => r'assignmentProvider';
}

/// See also [assignment].
class AssignmentProvider extends AutoDisposeFutureProvider<Assignment> {
  /// See also [assignment].
  AssignmentProvider(
    int id,
  ) : this._internal(
          (ref) => assignment(
            ref as AssignmentRef,
            id,
          ),
          from: assignmentProvider,
          name: r'assignmentProvider',
          debugGetCreateSourceHash:
              const bool.fromEnvironment('dart.vm.product')
                  ? null
                  : _$assignmentHash,
          dependencies: AssignmentFamily._dependencies,
          allTransitiveDependencies:
              AssignmentFamily._allTransitiveDependencies,
          id: id,
        );

  AssignmentProvider._internal(
    super._createNotifier, {
    required super.name,
    required super.dependencies,
    required super.allTransitiveDependencies,
    required super.debugGetCreateSourceHash,
    required super.from,
    required this.id,
  }) : super.internal();

  final int id;

  @override
  Override overrideWith(
    FutureOr<Assignment> Function(AssignmentRef provider) create,
  ) {
    return ProviderOverride(
      origin: this,
      override: AssignmentProvider._internal(
        (ref) => create(ref as AssignmentRef),
        from: from,
        name: null,
        dependencies: null,
        allTransitiveDependencies: null,
        debugGetCreateSourceHash: null,
        id: id,
      ),
    );
  }

  @override
  AutoDisposeFutureProviderElement<Assignment> createElement() {
    return _AssignmentProviderElement(this);
  }

  @override
  bool operator ==(Object other) {
    return other is AssignmentProvider && other.id == id;
  }

  @override
  int get hashCode {
    var hash = _SystemHash.combine(0, runtimeType.hashCode);
    hash = _SystemHash.combine(hash, id.hashCode);

    return _SystemHash.finish(hash);
  }
}

@Deprecated('Will be removed in 3.0. Use Ref instead')
// ignore: unused_element
mixin AssignmentRef on AutoDisposeFutureProviderRef<Assignment> {
  /// The parameter `id` of this provider.
  int get id;
}

class _AssignmentProviderElement
    extends AutoDisposeFutureProviderElement<Assignment> with AssignmentRef {
  _AssignmentProviderElement(super.provider);

  @override
  int get id => (origin as AssignmentProvider).id;
}
// ignore_for_file: type=lint
// ignore_for_file: subtype_of_sealed_class, invalid_use_of_internal_member, invalid_use_of_visible_for_testing_member, deprecated_member_use_from_same_package
