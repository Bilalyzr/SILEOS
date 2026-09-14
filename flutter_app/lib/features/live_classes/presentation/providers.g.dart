// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'providers.dart';

// **************************************************************************
// RiverpodGenerator
// **************************************************************************

String _$liveClassApiHash() => r'd0d73e2385fa4e92a81212da559356675e4fbbec';

/// See also [liveClassApi].
@ProviderFor(liveClassApi)
final liveClassApiProvider = AutoDisposeProvider<LiveClassApi>.internal(
  liveClassApi,
  name: r'liveClassApiProvider',
  debugGetCreateSourceHash:
      const bool.fromEnvironment('dart.vm.product') ? null : _$liveClassApiHash,
  dependencies: null,
  allTransitiveDependencies: null,
);

@Deprecated('Will be removed in 3.0. Use Ref instead')
// ignore: unused_element
typedef LiveClassApiRef = AutoDisposeProviderRef<LiveClassApi>;
String _$liveClassRepositoryHash() =>
    r'ef5bbafb34d9ef38e1425efa26a0ccb866215c47';

/// See also [liveClassRepository].
@ProviderFor(liveClassRepository)
final liveClassRepositoryProvider =
    AutoDisposeProvider<LiveClassRepository>.internal(
  liveClassRepository,
  name: r'liveClassRepositoryProvider',
  debugGetCreateSourceHash: const bool.fromEnvironment('dart.vm.product')
      ? null
      : _$liveClassRepositoryHash,
  dependencies: null,
  allTransitiveDependencies: null,
);

@Deprecated('Will be removed in 3.0. Use Ref instead')
// ignore: unused_element
typedef LiveClassRepositoryRef = AutoDisposeProviderRef<LiveClassRepository>;
String _$liveClassesHash() => r'40e4be5c1148412864dbdb7adf1fa89741a80893';

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

/// scope: upcoming | past | live — matches the backend query param exactly.
///
/// Copied from [liveClasses].
@ProviderFor(liveClasses)
const liveClassesProvider = LiveClassesFamily();

/// scope: upcoming | past | live — matches the backend query param exactly.
///
/// Copied from [liveClasses].
class LiveClassesFamily extends Family<AsyncValue<List<LiveClass>>> {
  /// scope: upcoming | past | live — matches the backend query param exactly.
  ///
  /// Copied from [liveClasses].
  const LiveClassesFamily();

  /// scope: upcoming | past | live — matches the backend query param exactly.
  ///
  /// Copied from [liveClasses].
  LiveClassesProvider call({
    String scope = 'upcoming',
  }) {
    return LiveClassesProvider(
      scope: scope,
    );
  }

  @override
  LiveClassesProvider getProviderOverride(
    covariant LiveClassesProvider provider,
  ) {
    return call(
      scope: provider.scope,
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
  String? get name => r'liveClassesProvider';
}

/// scope: upcoming | past | live — matches the backend query param exactly.
///
/// Copied from [liveClasses].
class LiveClassesProvider extends AutoDisposeFutureProvider<List<LiveClass>> {
  /// scope: upcoming | past | live — matches the backend query param exactly.
  ///
  /// Copied from [liveClasses].
  LiveClassesProvider({
    String scope = 'upcoming',
  }) : this._internal(
          (ref) => liveClasses(
            ref as LiveClassesRef,
            scope: scope,
          ),
          from: liveClassesProvider,
          name: r'liveClassesProvider',
          debugGetCreateSourceHash:
              const bool.fromEnvironment('dart.vm.product')
                  ? null
                  : _$liveClassesHash,
          dependencies: LiveClassesFamily._dependencies,
          allTransitiveDependencies:
              LiveClassesFamily._allTransitiveDependencies,
          scope: scope,
        );

  LiveClassesProvider._internal(
    super._createNotifier, {
    required super.name,
    required super.dependencies,
    required super.allTransitiveDependencies,
    required super.debugGetCreateSourceHash,
    required super.from,
    required this.scope,
  }) : super.internal();

  final String scope;

  @override
  Override overrideWith(
    FutureOr<List<LiveClass>> Function(LiveClassesRef provider) create,
  ) {
    return ProviderOverride(
      origin: this,
      override: LiveClassesProvider._internal(
        (ref) => create(ref as LiveClassesRef),
        from: from,
        name: null,
        dependencies: null,
        allTransitiveDependencies: null,
        debugGetCreateSourceHash: null,
        scope: scope,
      ),
    );
  }

  @override
  AutoDisposeFutureProviderElement<List<LiveClass>> createElement() {
    return _LiveClassesProviderElement(this);
  }

  @override
  bool operator ==(Object other) {
    return other is LiveClassesProvider && other.scope == scope;
  }

  @override
  int get hashCode {
    var hash = _SystemHash.combine(0, runtimeType.hashCode);
    hash = _SystemHash.combine(hash, scope.hashCode);

    return _SystemHash.finish(hash);
  }
}

@Deprecated('Will be removed in 3.0. Use Ref instead')
// ignore: unused_element
mixin LiveClassesRef on AutoDisposeFutureProviderRef<List<LiveClass>> {
  /// The parameter `scope` of this provider.
  String get scope;
}

class _LiveClassesProviderElement
    extends AutoDisposeFutureProviderElement<List<LiveClass>>
    with LiveClassesRef {
  _LiveClassesProviderElement(super.provider);

  @override
  String get scope => (origin as LiveClassesProvider).scope;
}

String _$liveClassByIdHash() => r'd0885952f267cc33a4da3527deb49aefbe26a697';

/// See also [liveClassById].
@ProviderFor(liveClassById)
const liveClassByIdProvider = LiveClassByIdFamily();

/// See also [liveClassById].
class LiveClassByIdFamily extends Family<AsyncValue<LiveClass>> {
  /// See also [liveClassById].
  const LiveClassByIdFamily();

  /// See also [liveClassById].
  LiveClassByIdProvider call(
    int id,
  ) {
    return LiveClassByIdProvider(
      id,
    );
  }

  @override
  LiveClassByIdProvider getProviderOverride(
    covariant LiveClassByIdProvider provider,
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
  String? get name => r'liveClassByIdProvider';
}

/// See also [liveClassById].
class LiveClassByIdProvider extends AutoDisposeFutureProvider<LiveClass> {
  /// See also [liveClassById].
  LiveClassByIdProvider(
    int id,
  ) : this._internal(
          (ref) => liveClassById(
            ref as LiveClassByIdRef,
            id,
          ),
          from: liveClassByIdProvider,
          name: r'liveClassByIdProvider',
          debugGetCreateSourceHash:
              const bool.fromEnvironment('dart.vm.product')
                  ? null
                  : _$liveClassByIdHash,
          dependencies: LiveClassByIdFamily._dependencies,
          allTransitiveDependencies:
              LiveClassByIdFamily._allTransitiveDependencies,
          id: id,
        );

  LiveClassByIdProvider._internal(
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
    FutureOr<LiveClass> Function(LiveClassByIdRef provider) create,
  ) {
    return ProviderOverride(
      origin: this,
      override: LiveClassByIdProvider._internal(
        (ref) => create(ref as LiveClassByIdRef),
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
  AutoDisposeFutureProviderElement<LiveClass> createElement() {
    return _LiveClassByIdProviderElement(this);
  }

  @override
  bool operator ==(Object other) {
    return other is LiveClassByIdProvider && other.id == id;
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
mixin LiveClassByIdRef on AutoDisposeFutureProviderRef<LiveClass> {
  /// The parameter `id` of this provider.
  int get id;
}

class _LiveClassByIdProviderElement
    extends AutoDisposeFutureProviderElement<LiveClass> with LiveClassByIdRef {
  _LiveClassByIdProviderElement(super.provider);

  @override
  int get id => (origin as LiveClassByIdProvider).id;
}

String _$liveNowClassesHash() => r'8f9e947254af11af5f43f162d3fd89a65c6c4144';

/// See also [liveNowClasses].
@ProviderFor(liveNowClasses)
final liveNowClassesProvider =
    AutoDisposeFutureProvider<List<LiveClass>>.internal(
  liveNowClasses,
  name: r'liveNowClassesProvider',
  debugGetCreateSourceHash: const bool.fromEnvironment('dart.vm.product')
      ? null
      : _$liveNowClassesHash,
  dependencies: null,
  allTransitiveDependencies: null,
);

@Deprecated('Will be removed in 3.0. Use Ref instead')
// ignore: unused_element
typedef LiveNowClassesRef = AutoDisposeFutureProviderRef<List<LiveClass>>;
String _$liveClassJoinTokenHash() =>
    r'ec37d3c17cd9fdf0d3c8cb8be781ca5c467c0a69';

/// Fetches a fresh join token; used by JoinLiveClassScreen right before
/// handing control to the Jitsi SDK. autoDispose: a stale token must never
/// be reused across screen visits.
///
/// Copied from [liveClassJoinToken].
@ProviderFor(liveClassJoinToken)
const liveClassJoinTokenProvider = LiveClassJoinTokenFamily();

/// Fetches a fresh join token; used by JoinLiveClassScreen right before
/// handing control to the Jitsi SDK. autoDispose: a stale token must never
/// be reused across screen visits.
///
/// Copied from [liveClassJoinToken].
class LiveClassJoinTokenFamily extends Family<AsyncValue<LiveClassJoinToken>> {
  /// Fetches a fresh join token; used by JoinLiveClassScreen right before
  /// handing control to the Jitsi SDK. autoDispose: a stale token must never
  /// be reused across screen visits.
  ///
  /// Copied from [liveClassJoinToken].
  const LiveClassJoinTokenFamily();

  /// Fetches a fresh join token; used by JoinLiveClassScreen right before
  /// handing control to the Jitsi SDK. autoDispose: a stale token must never
  /// be reused across screen visits.
  ///
  /// Copied from [liveClassJoinToken].
  LiveClassJoinTokenProvider call(
    int classId,
  ) {
    return LiveClassJoinTokenProvider(
      classId,
    );
  }

  @override
  LiveClassJoinTokenProvider getProviderOverride(
    covariant LiveClassJoinTokenProvider provider,
  ) {
    return call(
      provider.classId,
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
  String? get name => r'liveClassJoinTokenProvider';
}

/// Fetches a fresh join token; used by JoinLiveClassScreen right before
/// handing control to the Jitsi SDK. autoDispose: a stale token must never
/// be reused across screen visits.
///
/// Copied from [liveClassJoinToken].
class LiveClassJoinTokenProvider
    extends AutoDisposeFutureProvider<LiveClassJoinToken> {
  /// Fetches a fresh join token; used by JoinLiveClassScreen right before
  /// handing control to the Jitsi SDK. autoDispose: a stale token must never
  /// be reused across screen visits.
  ///
  /// Copied from [liveClassJoinToken].
  LiveClassJoinTokenProvider(
    int classId,
  ) : this._internal(
          (ref) => liveClassJoinToken(
            ref as LiveClassJoinTokenRef,
            classId,
          ),
          from: liveClassJoinTokenProvider,
          name: r'liveClassJoinTokenProvider',
          debugGetCreateSourceHash:
              const bool.fromEnvironment('dart.vm.product')
                  ? null
                  : _$liveClassJoinTokenHash,
          dependencies: LiveClassJoinTokenFamily._dependencies,
          allTransitiveDependencies:
              LiveClassJoinTokenFamily._allTransitiveDependencies,
          classId: classId,
        );

  LiveClassJoinTokenProvider._internal(
    super._createNotifier, {
    required super.name,
    required super.dependencies,
    required super.allTransitiveDependencies,
    required super.debugGetCreateSourceHash,
    required super.from,
    required this.classId,
  }) : super.internal();

  final int classId;

  @override
  Override overrideWith(
    FutureOr<LiveClassJoinToken> Function(LiveClassJoinTokenRef provider)
        create,
  ) {
    return ProviderOverride(
      origin: this,
      override: LiveClassJoinTokenProvider._internal(
        (ref) => create(ref as LiveClassJoinTokenRef),
        from: from,
        name: null,
        dependencies: null,
        allTransitiveDependencies: null,
        debugGetCreateSourceHash: null,
        classId: classId,
      ),
    );
  }

  @override
  AutoDisposeFutureProviderElement<LiveClassJoinToken> createElement() {
    return _LiveClassJoinTokenProviderElement(this);
  }

  @override
  bool operator ==(Object other) {
    return other is LiveClassJoinTokenProvider && other.classId == classId;
  }

  @override
  int get hashCode {
    var hash = _SystemHash.combine(0, runtimeType.hashCode);
    hash = _SystemHash.combine(hash, classId.hashCode);

    return _SystemHash.finish(hash);
  }
}

@Deprecated('Will be removed in 3.0. Use Ref instead')
// ignore: unused_element
mixin LiveClassJoinTokenRef
    on AutoDisposeFutureProviderRef<LiveClassJoinToken> {
  /// The parameter `classId` of this provider.
  int get classId;
}

class _LiveClassJoinTokenProviderElement
    extends AutoDisposeFutureProviderElement<LiveClassJoinToken>
    with LiveClassJoinTokenRef {
  _LiveClassJoinTokenProviderElement(super.provider);

  @override
  int get classId => (origin as LiveClassJoinTokenProvider).classId;
}

String _$liveClassRecordingPlaybackHash() =>
    r'353c9752f3ad506b22b86328a54bcfd74272fcd7';

/// See also [liveClassRecordingPlayback].
@ProviderFor(liveClassRecordingPlayback)
const liveClassRecordingPlaybackProvider = LiveClassRecordingPlaybackFamily();

/// See also [liveClassRecordingPlayback].
class LiveClassRecordingPlaybackFamily
    extends Family<AsyncValue<LiveClassRecordingPlayback?>> {
  /// See also [liveClassRecordingPlayback].
  const LiveClassRecordingPlaybackFamily();

  /// See also [liveClassRecordingPlayback].
  LiveClassRecordingPlaybackProvider call(
    int classId,
  ) {
    return LiveClassRecordingPlaybackProvider(
      classId,
    );
  }

  @override
  LiveClassRecordingPlaybackProvider getProviderOverride(
    covariant LiveClassRecordingPlaybackProvider provider,
  ) {
    return call(
      provider.classId,
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
  String? get name => r'liveClassRecordingPlaybackProvider';
}

/// See also [liveClassRecordingPlayback].
class LiveClassRecordingPlaybackProvider
    extends AutoDisposeFutureProvider<LiveClassRecordingPlayback?> {
  /// See also [liveClassRecordingPlayback].
  LiveClassRecordingPlaybackProvider(
    int classId,
  ) : this._internal(
          (ref) => liveClassRecordingPlayback(
            ref as LiveClassRecordingPlaybackRef,
            classId,
          ),
          from: liveClassRecordingPlaybackProvider,
          name: r'liveClassRecordingPlaybackProvider',
          debugGetCreateSourceHash:
              const bool.fromEnvironment('dart.vm.product')
                  ? null
                  : _$liveClassRecordingPlaybackHash,
          dependencies: LiveClassRecordingPlaybackFamily._dependencies,
          allTransitiveDependencies:
              LiveClassRecordingPlaybackFamily._allTransitiveDependencies,
          classId: classId,
        );

  LiveClassRecordingPlaybackProvider._internal(
    super._createNotifier, {
    required super.name,
    required super.dependencies,
    required super.allTransitiveDependencies,
    required super.debugGetCreateSourceHash,
    required super.from,
    required this.classId,
  }) : super.internal();

  final int classId;

  @override
  Override overrideWith(
    FutureOr<LiveClassRecordingPlayback?> Function(
            LiveClassRecordingPlaybackRef provider)
        create,
  ) {
    return ProviderOverride(
      origin: this,
      override: LiveClassRecordingPlaybackProvider._internal(
        (ref) => create(ref as LiveClassRecordingPlaybackRef),
        from: from,
        name: null,
        dependencies: null,
        allTransitiveDependencies: null,
        debugGetCreateSourceHash: null,
        classId: classId,
      ),
    );
  }

  @override
  AutoDisposeFutureProviderElement<LiveClassRecordingPlayback?>
      createElement() {
    return _LiveClassRecordingPlaybackProviderElement(this);
  }

  @override
  bool operator ==(Object other) {
    return other is LiveClassRecordingPlaybackProvider &&
        other.classId == classId;
  }

  @override
  int get hashCode {
    var hash = _SystemHash.combine(0, runtimeType.hashCode);
    hash = _SystemHash.combine(hash, classId.hashCode);

    return _SystemHash.finish(hash);
  }
}

@Deprecated('Will be removed in 3.0. Use Ref instead')
// ignore: unused_element
mixin LiveClassRecordingPlaybackRef
    on AutoDisposeFutureProviderRef<LiveClassRecordingPlayback?> {
  /// The parameter `classId` of this provider.
  int get classId;
}

class _LiveClassRecordingPlaybackProviderElement
    extends AutoDisposeFutureProviderElement<LiveClassRecordingPlayback?>
    with LiveClassRecordingPlaybackRef {
  _LiveClassRecordingPlaybackProviderElement(super.provider);

  @override
  int get classId => (origin as LiveClassRecordingPlaybackProvider).classId;
}
// ignore_for_file: type=lint
// ignore_for_file: subtype_of_sealed_class, invalid_use_of_internal_member, invalid_use_of_visible_for_testing_member, deprecated_member_use_from_same_package
