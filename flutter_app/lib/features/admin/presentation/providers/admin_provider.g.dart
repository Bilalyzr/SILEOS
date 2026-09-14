// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'admin_provider.dart';

// **************************************************************************
// RiverpodGenerator
// **************************************************************************

String _$adminRemoteDataSourceHash() =>
    r'49fcf0f667606ea800ca808571890d29989111a1';

/// See also [adminRemoteDataSource].
@ProviderFor(adminRemoteDataSource)
final adminRemoteDataSourceProvider =
    AutoDisposeProvider<AdminRemoteDataSource>.internal(
  adminRemoteDataSource,
  name: r'adminRemoteDataSourceProvider',
  debugGetCreateSourceHash: const bool.fromEnvironment('dart.vm.product')
      ? null
      : _$adminRemoteDataSourceHash,
  dependencies: null,
  allTransitiveDependencies: null,
);

@Deprecated('Will be removed in 3.0. Use Ref instead')
// ignore: unused_element
typedef AdminRemoteDataSourceRef
    = AutoDisposeProviderRef<AdminRemoteDataSource>;
String _$adminRepositoryHash() => r'73f1cc811cdbe78cf193c964040948c3df524570';

/// See also [adminRepository].
@ProviderFor(adminRepository)
final adminRepositoryProvider = AutoDisposeProvider<AdminRepository>.internal(
  adminRepository,
  name: r'adminRepositoryProvider',
  debugGetCreateSourceHash: const bool.fromEnvironment('dart.vm.product')
      ? null
      : _$adminRepositoryHash,
  dependencies: null,
  allTransitiveDependencies: null,
);

@Deprecated('Will be removed in 3.0. Use Ref instead')
// ignore: unused_element
typedef AdminRepositoryRef = AutoDisposeProviderRef<AdminRepository>;
String _$adminStatsHash() => r'4080da479a324f0f1bd7cd21ad1e120bfa918452';

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

/// See also [adminStats].
@ProviderFor(adminStats)
const adminStatsProvider = AdminStatsFamily();

/// See also [adminStats].
class AdminStatsFamily extends Family<AsyncValue<Map<String, dynamic>>> {
  /// See also [adminStats].
  const AdminStatsFamily();

  /// See also [adminStats].
  AdminStatsProvider call({
    String period = '30d',
  }) {
    return AdminStatsProvider(
      period: period,
    );
  }

  @override
  AdminStatsProvider getProviderOverride(
    covariant AdminStatsProvider provider,
  ) {
    return call(
      period: provider.period,
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
  String? get name => r'adminStatsProvider';
}

/// See also [adminStats].
class AdminStatsProvider
    extends AutoDisposeFutureProvider<Map<String, dynamic>> {
  /// See also [adminStats].
  AdminStatsProvider({
    String period = '30d',
  }) : this._internal(
          (ref) => adminStats(
            ref as AdminStatsRef,
            period: period,
          ),
          from: adminStatsProvider,
          name: r'adminStatsProvider',
          debugGetCreateSourceHash:
              const bool.fromEnvironment('dart.vm.product')
                  ? null
                  : _$adminStatsHash,
          dependencies: AdminStatsFamily._dependencies,
          allTransitiveDependencies:
              AdminStatsFamily._allTransitiveDependencies,
          period: period,
        );

  AdminStatsProvider._internal(
    super._createNotifier, {
    required super.name,
    required super.dependencies,
    required super.allTransitiveDependencies,
    required super.debugGetCreateSourceHash,
    required super.from,
    required this.period,
  }) : super.internal();

  final String period;

  @override
  Override overrideWith(
    FutureOr<Map<String, dynamic>> Function(AdminStatsRef provider) create,
  ) {
    return ProviderOverride(
      origin: this,
      override: AdminStatsProvider._internal(
        (ref) => create(ref as AdminStatsRef),
        from: from,
        name: null,
        dependencies: null,
        allTransitiveDependencies: null,
        debugGetCreateSourceHash: null,
        period: period,
      ),
    );
  }

  @override
  AutoDisposeFutureProviderElement<Map<String, dynamic>> createElement() {
    return _AdminStatsProviderElement(this);
  }

  @override
  bool operator ==(Object other) {
    return other is AdminStatsProvider && other.period == period;
  }

  @override
  int get hashCode {
    var hash = _SystemHash.combine(0, runtimeType.hashCode);
    hash = _SystemHash.combine(hash, period.hashCode);

    return _SystemHash.finish(hash);
  }
}

@Deprecated('Will be removed in 3.0. Use Ref instead')
// ignore: unused_element
mixin AdminStatsRef on AutoDisposeFutureProviderRef<Map<String, dynamic>> {
  /// The parameter `period` of this provider.
  String get period;
}

class _AdminStatsProviderElement
    extends AutoDisposeFutureProviderElement<Map<String, dynamic>>
    with AdminStatsRef {
  _AdminStatsProviderElement(super.provider);

  @override
  String get period => (origin as AdminStatsProvider).period;
}

String _$adminStudentsHash() => r'29a13ab5777388c4e21512aabd8aaca2b41cb85e';

/// See also [adminStudents].
@ProviderFor(adminStudents)
const adminStudentsProvider = AdminStudentsFamily();

/// See also [adminStudents].
class AdminStudentsFamily extends Family<AsyncValue<AdminUserListResult>> {
  /// See also [adminStudents].
  const AdminStudentsFamily();

  /// See also [adminStudents].
  AdminStudentsProvider call({
    String? status,
    String? search,
    int skip = 0,
  }) {
    return AdminStudentsProvider(
      status: status,
      search: search,
      skip: skip,
    );
  }

  @override
  AdminStudentsProvider getProviderOverride(
    covariant AdminStudentsProvider provider,
  ) {
    return call(
      status: provider.status,
      search: provider.search,
      skip: provider.skip,
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
  String? get name => r'adminStudentsProvider';
}

/// See also [adminStudents].
class AdminStudentsProvider
    extends AutoDisposeFutureProvider<AdminUserListResult> {
  /// See also [adminStudents].
  AdminStudentsProvider({
    String? status,
    String? search,
    int skip = 0,
  }) : this._internal(
          (ref) => adminStudents(
            ref as AdminStudentsRef,
            status: status,
            search: search,
            skip: skip,
          ),
          from: adminStudentsProvider,
          name: r'adminStudentsProvider',
          debugGetCreateSourceHash:
              const bool.fromEnvironment('dart.vm.product')
                  ? null
                  : _$adminStudentsHash,
          dependencies: AdminStudentsFamily._dependencies,
          allTransitiveDependencies:
              AdminStudentsFamily._allTransitiveDependencies,
          status: status,
          search: search,
          skip: skip,
        );

  AdminStudentsProvider._internal(
    super._createNotifier, {
    required super.name,
    required super.dependencies,
    required super.allTransitiveDependencies,
    required super.debugGetCreateSourceHash,
    required super.from,
    required this.status,
    required this.search,
    required this.skip,
  }) : super.internal();

  final String? status;
  final String? search;
  final int skip;

  @override
  Override overrideWith(
    FutureOr<AdminUserListResult> Function(AdminStudentsRef provider) create,
  ) {
    return ProviderOverride(
      origin: this,
      override: AdminStudentsProvider._internal(
        (ref) => create(ref as AdminStudentsRef),
        from: from,
        name: null,
        dependencies: null,
        allTransitiveDependencies: null,
        debugGetCreateSourceHash: null,
        status: status,
        search: search,
        skip: skip,
      ),
    );
  }

  @override
  AutoDisposeFutureProviderElement<AdminUserListResult> createElement() {
    return _AdminStudentsProviderElement(this);
  }

  @override
  bool operator ==(Object other) {
    return other is AdminStudentsProvider &&
        other.status == status &&
        other.search == search &&
        other.skip == skip;
  }

  @override
  int get hashCode {
    var hash = _SystemHash.combine(0, runtimeType.hashCode);
    hash = _SystemHash.combine(hash, status.hashCode);
    hash = _SystemHash.combine(hash, search.hashCode);
    hash = _SystemHash.combine(hash, skip.hashCode);

    return _SystemHash.finish(hash);
  }
}

@Deprecated('Will be removed in 3.0. Use Ref instead')
// ignore: unused_element
mixin AdminStudentsRef on AutoDisposeFutureProviderRef<AdminUserListResult> {
  /// The parameter `status` of this provider.
  String? get status;

  /// The parameter `search` of this provider.
  String? get search;

  /// The parameter `skip` of this provider.
  int get skip;
}

class _AdminStudentsProviderElement
    extends AutoDisposeFutureProviderElement<AdminUserListResult>
    with AdminStudentsRef {
  _AdminStudentsProviderElement(super.provider);

  @override
  String? get status => (origin as AdminStudentsProvider).status;
  @override
  String? get search => (origin as AdminStudentsProvider).search;
  @override
  int get skip => (origin as AdminStudentsProvider).skip;
}

String _$adminInstructorsHash() => r'b6d0537815df542628573b0d8a40bf3b50b20854';

/// See also [adminInstructors].
@ProviderFor(adminInstructors)
const adminInstructorsProvider = AdminInstructorsFamily();

/// See also [adminInstructors].
class AdminInstructorsFamily extends Family<AsyncValue<AdminUserListResult>> {
  /// See also [adminInstructors].
  const AdminInstructorsFamily();

  /// See also [adminInstructors].
  AdminInstructorsProvider call({
    String? status,
    String? search,
    int skip = 0,
  }) {
    return AdminInstructorsProvider(
      status: status,
      search: search,
      skip: skip,
    );
  }

  @override
  AdminInstructorsProvider getProviderOverride(
    covariant AdminInstructorsProvider provider,
  ) {
    return call(
      status: provider.status,
      search: provider.search,
      skip: provider.skip,
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
  String? get name => r'adminInstructorsProvider';
}

/// See also [adminInstructors].
class AdminInstructorsProvider
    extends AutoDisposeFutureProvider<AdminUserListResult> {
  /// See also [adminInstructors].
  AdminInstructorsProvider({
    String? status,
    String? search,
    int skip = 0,
  }) : this._internal(
          (ref) => adminInstructors(
            ref as AdminInstructorsRef,
            status: status,
            search: search,
            skip: skip,
          ),
          from: adminInstructorsProvider,
          name: r'adminInstructorsProvider',
          debugGetCreateSourceHash:
              const bool.fromEnvironment('dart.vm.product')
                  ? null
                  : _$adminInstructorsHash,
          dependencies: AdminInstructorsFamily._dependencies,
          allTransitiveDependencies:
              AdminInstructorsFamily._allTransitiveDependencies,
          status: status,
          search: search,
          skip: skip,
        );

  AdminInstructorsProvider._internal(
    super._createNotifier, {
    required super.name,
    required super.dependencies,
    required super.allTransitiveDependencies,
    required super.debugGetCreateSourceHash,
    required super.from,
    required this.status,
    required this.search,
    required this.skip,
  }) : super.internal();

  final String? status;
  final String? search;
  final int skip;

  @override
  Override overrideWith(
    FutureOr<AdminUserListResult> Function(AdminInstructorsRef provider) create,
  ) {
    return ProviderOverride(
      origin: this,
      override: AdminInstructorsProvider._internal(
        (ref) => create(ref as AdminInstructorsRef),
        from: from,
        name: null,
        dependencies: null,
        allTransitiveDependencies: null,
        debugGetCreateSourceHash: null,
        status: status,
        search: search,
        skip: skip,
      ),
    );
  }

  @override
  AutoDisposeFutureProviderElement<AdminUserListResult> createElement() {
    return _AdminInstructorsProviderElement(this);
  }

  @override
  bool operator ==(Object other) {
    return other is AdminInstructorsProvider &&
        other.status == status &&
        other.search == search &&
        other.skip == skip;
  }

  @override
  int get hashCode {
    var hash = _SystemHash.combine(0, runtimeType.hashCode);
    hash = _SystemHash.combine(hash, status.hashCode);
    hash = _SystemHash.combine(hash, search.hashCode);
    hash = _SystemHash.combine(hash, skip.hashCode);

    return _SystemHash.finish(hash);
  }
}

@Deprecated('Will be removed in 3.0. Use Ref instead')
// ignore: unused_element
mixin AdminInstructorsRef on AutoDisposeFutureProviderRef<AdminUserListResult> {
  /// The parameter `status` of this provider.
  String? get status;

  /// The parameter `search` of this provider.
  String? get search;

  /// The parameter `skip` of this provider.
  int get skip;
}

class _AdminInstructorsProviderElement
    extends AutoDisposeFutureProviderElement<AdminUserListResult>
    with AdminInstructorsRef {
  _AdminInstructorsProviderElement(super.provider);

  @override
  String? get status => (origin as AdminInstructorsProvider).status;
  @override
  String? get search => (origin as AdminInstructorsProvider).search;
  @override
  int get skip => (origin as AdminInstructorsProvider).skip;
}

String _$adminCoursesHash() => r'2cefc5c16c1a86342a233fc3f5e3c7f93ee03b52';

/// See also [adminCourses].
@ProviderFor(adminCourses)
const adminCoursesProvider = AdminCoursesFamily();

/// See also [adminCourses].
class AdminCoursesFamily
    extends Family<AsyncValue<List<Map<String, dynamic>>>> {
  /// See also [adminCourses].
  const AdminCoursesFamily();

  /// See also [adminCourses].
  AdminCoursesProvider call({
    String? status,
    int skip = 0,
  }) {
    return AdminCoursesProvider(
      status: status,
      skip: skip,
    );
  }

  @override
  AdminCoursesProvider getProviderOverride(
    covariant AdminCoursesProvider provider,
  ) {
    return call(
      status: provider.status,
      skip: provider.skip,
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
  String? get name => r'adminCoursesProvider';
}

/// See also [adminCourses].
class AdminCoursesProvider
    extends AutoDisposeFutureProvider<List<Map<String, dynamic>>> {
  /// See also [adminCourses].
  AdminCoursesProvider({
    String? status,
    int skip = 0,
  }) : this._internal(
          (ref) => adminCourses(
            ref as AdminCoursesRef,
            status: status,
            skip: skip,
          ),
          from: adminCoursesProvider,
          name: r'adminCoursesProvider',
          debugGetCreateSourceHash:
              const bool.fromEnvironment('dart.vm.product')
                  ? null
                  : _$adminCoursesHash,
          dependencies: AdminCoursesFamily._dependencies,
          allTransitiveDependencies:
              AdminCoursesFamily._allTransitiveDependencies,
          status: status,
          skip: skip,
        );

  AdminCoursesProvider._internal(
    super._createNotifier, {
    required super.name,
    required super.dependencies,
    required super.allTransitiveDependencies,
    required super.debugGetCreateSourceHash,
    required super.from,
    required this.status,
    required this.skip,
  }) : super.internal();

  final String? status;
  final int skip;

  @override
  Override overrideWith(
    FutureOr<List<Map<String, dynamic>>> Function(AdminCoursesRef provider)
        create,
  ) {
    return ProviderOverride(
      origin: this,
      override: AdminCoursesProvider._internal(
        (ref) => create(ref as AdminCoursesRef),
        from: from,
        name: null,
        dependencies: null,
        allTransitiveDependencies: null,
        debugGetCreateSourceHash: null,
        status: status,
        skip: skip,
      ),
    );
  }

  @override
  AutoDisposeFutureProviderElement<List<Map<String, dynamic>>> createElement() {
    return _AdminCoursesProviderElement(this);
  }

  @override
  bool operator ==(Object other) {
    return other is AdminCoursesProvider &&
        other.status == status &&
        other.skip == skip;
  }

  @override
  int get hashCode {
    var hash = _SystemHash.combine(0, runtimeType.hashCode);
    hash = _SystemHash.combine(hash, status.hashCode);
    hash = _SystemHash.combine(hash, skip.hashCode);

    return _SystemHash.finish(hash);
  }
}

@Deprecated('Will be removed in 3.0. Use Ref instead')
// ignore: unused_element
mixin AdminCoursesRef
    on AutoDisposeFutureProviderRef<List<Map<String, dynamic>>> {
  /// The parameter `status` of this provider.
  String? get status;

  /// The parameter `skip` of this provider.
  int get skip;
}

class _AdminCoursesProviderElement
    extends AutoDisposeFutureProviderElement<List<Map<String, dynamic>>>
    with AdminCoursesRef {
  _AdminCoursesProviderElement(super.provider);

  @override
  String? get status => (origin as AdminCoursesProvider).status;
  @override
  int get skip => (origin as AdminCoursesProvider).skip;
}

String _$adminOrdersHash() => r'7979ade6d84e983f66a8daf8b9fb5aee45eccf80';

/// See also [adminOrders].
@ProviderFor(adminOrders)
const adminOrdersProvider = AdminOrdersFamily();

/// See also [adminOrders].
class AdminOrdersFamily extends Family<AsyncValue<List<Map<String, dynamic>>>> {
  /// See also [adminOrders].
  const AdminOrdersFamily();

  /// See also [adminOrders].
  AdminOrdersProvider call({
    String? status,
    int skip = 0,
  }) {
    return AdminOrdersProvider(
      status: status,
      skip: skip,
    );
  }

  @override
  AdminOrdersProvider getProviderOverride(
    covariant AdminOrdersProvider provider,
  ) {
    return call(
      status: provider.status,
      skip: provider.skip,
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
  String? get name => r'adminOrdersProvider';
}

/// See also [adminOrders].
class AdminOrdersProvider
    extends AutoDisposeFutureProvider<List<Map<String, dynamic>>> {
  /// See also [adminOrders].
  AdminOrdersProvider({
    String? status,
    int skip = 0,
  }) : this._internal(
          (ref) => adminOrders(
            ref as AdminOrdersRef,
            status: status,
            skip: skip,
          ),
          from: adminOrdersProvider,
          name: r'adminOrdersProvider',
          debugGetCreateSourceHash:
              const bool.fromEnvironment('dart.vm.product')
                  ? null
                  : _$adminOrdersHash,
          dependencies: AdminOrdersFamily._dependencies,
          allTransitiveDependencies:
              AdminOrdersFamily._allTransitiveDependencies,
          status: status,
          skip: skip,
        );

  AdminOrdersProvider._internal(
    super._createNotifier, {
    required super.name,
    required super.dependencies,
    required super.allTransitiveDependencies,
    required super.debugGetCreateSourceHash,
    required super.from,
    required this.status,
    required this.skip,
  }) : super.internal();

  final String? status;
  final int skip;

  @override
  Override overrideWith(
    FutureOr<List<Map<String, dynamic>>> Function(AdminOrdersRef provider)
        create,
  ) {
    return ProviderOverride(
      origin: this,
      override: AdminOrdersProvider._internal(
        (ref) => create(ref as AdminOrdersRef),
        from: from,
        name: null,
        dependencies: null,
        allTransitiveDependencies: null,
        debugGetCreateSourceHash: null,
        status: status,
        skip: skip,
      ),
    );
  }

  @override
  AutoDisposeFutureProviderElement<List<Map<String, dynamic>>> createElement() {
    return _AdminOrdersProviderElement(this);
  }

  @override
  bool operator ==(Object other) {
    return other is AdminOrdersProvider &&
        other.status == status &&
        other.skip == skip;
  }

  @override
  int get hashCode {
    var hash = _SystemHash.combine(0, runtimeType.hashCode);
    hash = _SystemHash.combine(hash, status.hashCode);
    hash = _SystemHash.combine(hash, skip.hashCode);

    return _SystemHash.finish(hash);
  }
}

@Deprecated('Will be removed in 3.0. Use Ref instead')
// ignore: unused_element
mixin AdminOrdersRef
    on AutoDisposeFutureProviderRef<List<Map<String, dynamic>>> {
  /// The parameter `status` of this provider.
  String? get status;

  /// The parameter `skip` of this provider.
  int get skip;
}

class _AdminOrdersProviderElement
    extends AutoDisposeFutureProviderElement<List<Map<String, dynamic>>>
    with AdminOrdersRef {
  _AdminOrdersProviderElement(super.provider);

  @override
  String? get status => (origin as AdminOrdersProvider).status;
  @override
  int get skip => (origin as AdminOrdersProvider).skip;
}

String _$adminApplicationsHash() => r'b919f070fabe0d0b36f0d29777df16c825cb883a';

/// See also [adminApplications].
@ProviderFor(adminApplications)
const adminApplicationsProvider = AdminApplicationsFamily();

/// See also [adminApplications].
class AdminApplicationsFamily
    extends Family<AsyncValue<List<Map<String, dynamic>>>> {
  /// See also [adminApplications].
  const AdminApplicationsFamily();

  /// See also [adminApplications].
  AdminApplicationsProvider call({
    String status = 'pending',
  }) {
    return AdminApplicationsProvider(
      status: status,
    );
  }

  @override
  AdminApplicationsProvider getProviderOverride(
    covariant AdminApplicationsProvider provider,
  ) {
    return call(
      status: provider.status,
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
  String? get name => r'adminApplicationsProvider';
}

/// See also [adminApplications].
class AdminApplicationsProvider
    extends AutoDisposeFutureProvider<List<Map<String, dynamic>>> {
  /// See also [adminApplications].
  AdminApplicationsProvider({
    String status = 'pending',
  }) : this._internal(
          (ref) => adminApplications(
            ref as AdminApplicationsRef,
            status: status,
          ),
          from: adminApplicationsProvider,
          name: r'adminApplicationsProvider',
          debugGetCreateSourceHash:
              const bool.fromEnvironment('dart.vm.product')
                  ? null
                  : _$adminApplicationsHash,
          dependencies: AdminApplicationsFamily._dependencies,
          allTransitiveDependencies:
              AdminApplicationsFamily._allTransitiveDependencies,
          status: status,
        );

  AdminApplicationsProvider._internal(
    super._createNotifier, {
    required super.name,
    required super.dependencies,
    required super.allTransitiveDependencies,
    required super.debugGetCreateSourceHash,
    required super.from,
    required this.status,
  }) : super.internal();

  final String status;

  @override
  Override overrideWith(
    FutureOr<List<Map<String, dynamic>>> Function(AdminApplicationsRef provider)
        create,
  ) {
    return ProviderOverride(
      origin: this,
      override: AdminApplicationsProvider._internal(
        (ref) => create(ref as AdminApplicationsRef),
        from: from,
        name: null,
        dependencies: null,
        allTransitiveDependencies: null,
        debugGetCreateSourceHash: null,
        status: status,
      ),
    );
  }

  @override
  AutoDisposeFutureProviderElement<List<Map<String, dynamic>>> createElement() {
    return _AdminApplicationsProviderElement(this);
  }

  @override
  bool operator ==(Object other) {
    return other is AdminApplicationsProvider && other.status == status;
  }

  @override
  int get hashCode {
    var hash = _SystemHash.combine(0, runtimeType.hashCode);
    hash = _SystemHash.combine(hash, status.hashCode);

    return _SystemHash.finish(hash);
  }
}

@Deprecated('Will be removed in 3.0. Use Ref instead')
// ignore: unused_element
mixin AdminApplicationsRef
    on AutoDisposeFutureProviderRef<List<Map<String, dynamic>>> {
  /// The parameter `status` of this provider.
  String get status;
}

class _AdminApplicationsProviderElement
    extends AutoDisposeFutureProviderElement<List<Map<String, dynamic>>>
    with AdminApplicationsRef {
  _AdminApplicationsProviderElement(super.provider);

  @override
  String get status => (origin as AdminApplicationsProvider).status;
}
// ignore_for_file: type=lint
// ignore_for_file: subtype_of_sealed_class, invalid_use_of_internal_member, invalid_use_of_visible_for_testing_member, deprecated_member_use_from_same_package
