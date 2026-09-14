// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'course_provider.dart';

// **************************************************************************
// RiverpodGenerator
// **************************************************************************

String _$courseRemoteDataSourceHash() =>
    r'88b7a73df52ecdcf87ecf873ebe5b3114eebae38';

/// See also [courseRemoteDataSource].
@ProviderFor(courseRemoteDataSource)
final courseRemoteDataSourceProvider =
    AutoDisposeProvider<CourseRemoteDataSource>.internal(
  courseRemoteDataSource,
  name: r'courseRemoteDataSourceProvider',
  debugGetCreateSourceHash: const bool.fromEnvironment('dart.vm.product')
      ? null
      : _$courseRemoteDataSourceHash,
  dependencies: null,
  allTransitiveDependencies: null,
);

@Deprecated('Will be removed in 3.0. Use Ref instead')
// ignore: unused_element
typedef CourseRemoteDataSourceRef
    = AutoDisposeProviderRef<CourseRemoteDataSource>;
String _$courseRepositoryHash() => r'8d9d6072d46684d3467b5a0055aa02881cf9ad4d';

/// See also [courseRepository].
@ProviderFor(courseRepository)
final courseRepositoryProvider = AutoDisposeProvider<CourseRepository>.internal(
  courseRepository,
  name: r'courseRepositoryProvider',
  debugGetCreateSourceHash: const bool.fromEnvironment('dart.vm.product')
      ? null
      : _$courseRepositoryHash,
  dependencies: null,
  allTransitiveDependencies: null,
);

@Deprecated('Will be removed in 3.0. Use Ref instead')
// ignore: unused_element
typedef CourseRepositoryRef = AutoDisposeProviderRef<CourseRepository>;
String _$getCoursesUseCaseHash() => r'a5c9e565c41078e3b96d9a929f652652d3d0ccab';

/// See also [getCoursesUseCase].
@ProviderFor(getCoursesUseCase)
final getCoursesUseCaseProvider =
    AutoDisposeProvider<GetCoursesUseCase>.internal(
  getCoursesUseCase,
  name: r'getCoursesUseCaseProvider',
  debugGetCreateSourceHash: const bool.fromEnvironment('dart.vm.product')
      ? null
      : _$getCoursesUseCaseHash,
  dependencies: null,
  allTransitiveDependencies: null,
);

@Deprecated('Will be removed in 3.0. Use Ref instead')
// ignore: unused_element
typedef GetCoursesUseCaseRef = AutoDisposeProviderRef<GetCoursesUseCase>;
String _$getCourseByIdUseCaseHash() =>
    r'002bf34e02e2676646a6b70f3ac23343c67bd4b6';

/// See also [getCourseByIdUseCase].
@ProviderFor(getCourseByIdUseCase)
final getCourseByIdUseCaseProvider =
    AutoDisposeProvider<GetCourseByIdUseCase>.internal(
  getCourseByIdUseCase,
  name: r'getCourseByIdUseCaseProvider',
  debugGetCreateSourceHash: const bool.fromEnvironment('dart.vm.product')
      ? null
      : _$getCourseByIdUseCaseHash,
  dependencies: null,
  allTransitiveDependencies: null,
);

@Deprecated('Will be removed in 3.0. Use Ref instead')
// ignore: unused_element
typedef GetCourseByIdUseCaseRef = AutoDisposeProviderRef<GetCourseByIdUseCase>;
String _$getLessonByIdUseCaseHash() =>
    r'fc928a4777c5346591db45579439ffe6d71585b1';

/// See also [getLessonByIdUseCase].
@ProviderFor(getLessonByIdUseCase)
final getLessonByIdUseCaseProvider =
    AutoDisposeProvider<GetLessonByIdUseCase>.internal(
  getLessonByIdUseCase,
  name: r'getLessonByIdUseCaseProvider',
  debugGetCreateSourceHash: const bool.fromEnvironment('dart.vm.product')
      ? null
      : _$getLessonByIdUseCaseHash,
  dependencies: null,
  allTransitiveDependencies: null,
);

@Deprecated('Will be removed in 3.0. Use Ref instead')
// ignore: unused_element
typedef GetLessonByIdUseCaseRef = AutoDisposeProviderRef<GetLessonByIdUseCase>;
String _$completeLessonUseCaseHash() =>
    r'cc364c565f2b112b4ad6f878478a3c8f72da9501';

/// See also [completeLessonUseCase].
@ProviderFor(completeLessonUseCase)
final completeLessonUseCaseProvider =
    AutoDisposeProvider<CompleteLessonUseCase>.internal(
  completeLessonUseCase,
  name: r'completeLessonUseCaseProvider',
  debugGetCreateSourceHash: const bool.fromEnvironment('dart.vm.product')
      ? null
      : _$completeLessonUseCaseHash,
  dependencies: null,
  allTransitiveDependencies: null,
);

@Deprecated('Will be removed in 3.0. Use Ref instead')
// ignore: unused_element
typedef CompleteLessonUseCaseRef
    = AutoDisposeProviderRef<CompleteLessonUseCase>;
String _$getCertificateForCourseUseCaseHash() =>
    r'9e10c01f7a3d110cbff2c700518568a97af498f4';

/// See also [getCertificateForCourseUseCase].
@ProviderFor(getCertificateForCourseUseCase)
final getCertificateForCourseUseCaseProvider =
    AutoDisposeProvider<GetCertificateForCourseUseCase>.internal(
  getCertificateForCourseUseCase,
  name: r'getCertificateForCourseUseCaseProvider',
  debugGetCreateSourceHash: const bool.fromEnvironment('dart.vm.product')
      ? null
      : _$getCertificateForCourseUseCaseHash,
  dependencies: null,
  allTransitiveDependencies: null,
);

@Deprecated('Will be removed in 3.0. Use Ref instead')
// ignore: unused_element
typedef GetCertificateForCourseUseCaseRef
    = AutoDisposeProviderRef<GetCertificateForCourseUseCase>;
String _$coursesHash() => r'477d88057e63ba73a01edd30d41f9ce5fc8f456b';

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

/// See also [courses].
@ProviderFor(courses)
const coursesProvider = CoursesFamily();

/// See also [courses].
class CoursesFamily extends Family<AsyncValue<PaginatedCourses>> {
  /// See also [courses].
  const CoursesFamily();

  /// See also [courses].
  CoursesProvider call({
    int page = 1,
    int pageSize = 20,
    String? category,
    String? search,
  }) {
    return CoursesProvider(
      page: page,
      pageSize: pageSize,
      category: category,
      search: search,
    );
  }

  @override
  CoursesProvider getProviderOverride(
    covariant CoursesProvider provider,
  ) {
    return call(
      page: provider.page,
      pageSize: provider.pageSize,
      category: provider.category,
      search: provider.search,
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
  String? get name => r'coursesProvider';
}

/// See also [courses].
class CoursesProvider extends AutoDisposeFutureProvider<PaginatedCourses> {
  /// See also [courses].
  CoursesProvider({
    int page = 1,
    int pageSize = 20,
    String? category,
    String? search,
  }) : this._internal(
          (ref) => courses(
            ref as CoursesRef,
            page: page,
            pageSize: pageSize,
            category: category,
            search: search,
          ),
          from: coursesProvider,
          name: r'coursesProvider',
          debugGetCreateSourceHash:
              const bool.fromEnvironment('dart.vm.product')
                  ? null
                  : _$coursesHash,
          dependencies: CoursesFamily._dependencies,
          allTransitiveDependencies: CoursesFamily._allTransitiveDependencies,
          page: page,
          pageSize: pageSize,
          category: category,
          search: search,
        );

  CoursesProvider._internal(
    super._createNotifier, {
    required super.name,
    required super.dependencies,
    required super.allTransitiveDependencies,
    required super.debugGetCreateSourceHash,
    required super.from,
    required this.page,
    required this.pageSize,
    required this.category,
    required this.search,
  }) : super.internal();

  final int page;
  final int pageSize;
  final String? category;
  final String? search;

  @override
  Override overrideWith(
    FutureOr<PaginatedCourses> Function(CoursesRef provider) create,
  ) {
    return ProviderOverride(
      origin: this,
      override: CoursesProvider._internal(
        (ref) => create(ref as CoursesRef),
        from: from,
        name: null,
        dependencies: null,
        allTransitiveDependencies: null,
        debugGetCreateSourceHash: null,
        page: page,
        pageSize: pageSize,
        category: category,
        search: search,
      ),
    );
  }

  @override
  AutoDisposeFutureProviderElement<PaginatedCourses> createElement() {
    return _CoursesProviderElement(this);
  }

  @override
  bool operator ==(Object other) {
    return other is CoursesProvider &&
        other.page == page &&
        other.pageSize == pageSize &&
        other.category == category &&
        other.search == search;
  }

  @override
  int get hashCode {
    var hash = _SystemHash.combine(0, runtimeType.hashCode);
    hash = _SystemHash.combine(hash, page.hashCode);
    hash = _SystemHash.combine(hash, pageSize.hashCode);
    hash = _SystemHash.combine(hash, category.hashCode);
    hash = _SystemHash.combine(hash, search.hashCode);

    return _SystemHash.finish(hash);
  }
}

@Deprecated('Will be removed in 3.0. Use Ref instead')
// ignore: unused_element
mixin CoursesRef on AutoDisposeFutureProviderRef<PaginatedCourses> {
  /// The parameter `page` of this provider.
  int get page;

  /// The parameter `pageSize` of this provider.
  int get pageSize;

  /// The parameter `category` of this provider.
  String? get category;

  /// The parameter `search` of this provider.
  String? get search;
}

class _CoursesProviderElement
    extends AutoDisposeFutureProviderElement<PaginatedCourses> with CoursesRef {
  _CoursesProviderElement(super.provider);

  @override
  int get page => (origin as CoursesProvider).page;
  @override
  int get pageSize => (origin as CoursesProvider).pageSize;
  @override
  String? get category => (origin as CoursesProvider).category;
  @override
  String? get search => (origin as CoursesProvider).search;
}

String _$myCoursesHash() => r'5dacfe7f8bb500228c0631f1a8751b7fced849c5';

/// See also [myCourses].
@ProviderFor(myCourses)
final myCoursesProvider = AutoDisposeFutureProvider<List<Course>>.internal(
  myCourses,
  name: r'myCoursesProvider',
  debugGetCreateSourceHash:
      const bool.fromEnvironment('dart.vm.product') ? null : _$myCoursesHash,
  dependencies: null,
  allTransitiveDependencies: null,
);

@Deprecated('Will be removed in 3.0. Use Ref instead')
// ignore: unused_element
typedef MyCoursesRef = AutoDisposeFutureProviderRef<List<Course>>;
String _$courseByIdHash() => r'f528f07fb340af2baea2856cca7ab61db21bde7b';

/// See also [courseById].
@ProviderFor(courseById)
const courseByIdProvider = CourseByIdFamily();

/// See also [courseById].
class CourseByIdFamily extends Family<AsyncValue<Course>> {
  /// See also [courseById].
  const CourseByIdFamily();

  /// See also [courseById].
  CourseByIdProvider call(
    String id,
  ) {
    return CourseByIdProvider(
      id,
    );
  }

  @override
  CourseByIdProvider getProviderOverride(
    covariant CourseByIdProvider provider,
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
  String? get name => r'courseByIdProvider';
}

/// See also [courseById].
class CourseByIdProvider extends AutoDisposeFutureProvider<Course> {
  /// See also [courseById].
  CourseByIdProvider(
    String id,
  ) : this._internal(
          (ref) => courseById(
            ref as CourseByIdRef,
            id,
          ),
          from: courseByIdProvider,
          name: r'courseByIdProvider',
          debugGetCreateSourceHash:
              const bool.fromEnvironment('dart.vm.product')
                  ? null
                  : _$courseByIdHash,
          dependencies: CourseByIdFamily._dependencies,
          allTransitiveDependencies:
              CourseByIdFamily._allTransitiveDependencies,
          id: id,
        );

  CourseByIdProvider._internal(
    super._createNotifier, {
    required super.name,
    required super.dependencies,
    required super.allTransitiveDependencies,
    required super.debugGetCreateSourceHash,
    required super.from,
    required this.id,
  }) : super.internal();

  final String id;

  @override
  Override overrideWith(
    FutureOr<Course> Function(CourseByIdRef provider) create,
  ) {
    return ProviderOverride(
      origin: this,
      override: CourseByIdProvider._internal(
        (ref) => create(ref as CourseByIdRef),
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
  AutoDisposeFutureProviderElement<Course> createElement() {
    return _CourseByIdProviderElement(this);
  }

  @override
  bool operator ==(Object other) {
    return other is CourseByIdProvider && other.id == id;
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
mixin CourseByIdRef on AutoDisposeFutureProviderRef<Course> {
  /// The parameter `id` of this provider.
  String get id;
}

class _CourseByIdProviderElement
    extends AutoDisposeFutureProviderElement<Course> with CourseByIdRef {
  _CourseByIdProviderElement(super.provider);

  @override
  String get id => (origin as CourseByIdProvider).id;
}

String _$lessonByIdHash() => r'd9b71c31f4f36861cf7b0c83787bbda5f347afb7';

/// See also [lessonById].
@ProviderFor(lessonById)
const lessonByIdProvider = LessonByIdFamily();

/// See also [lessonById].
class LessonByIdFamily extends Family<AsyncValue<Lesson>> {
  /// See also [lessonById].
  const LessonByIdFamily();

  /// See also [lessonById].
  LessonByIdProvider call(
    String id,
  ) {
    return LessonByIdProvider(
      id,
    );
  }

  @override
  LessonByIdProvider getProviderOverride(
    covariant LessonByIdProvider provider,
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
  String? get name => r'lessonByIdProvider';
}

/// See also [lessonById].
class LessonByIdProvider extends AutoDisposeFutureProvider<Lesson> {
  /// See also [lessonById].
  LessonByIdProvider(
    String id,
  ) : this._internal(
          (ref) => lessonById(
            ref as LessonByIdRef,
            id,
          ),
          from: lessonByIdProvider,
          name: r'lessonByIdProvider',
          debugGetCreateSourceHash:
              const bool.fromEnvironment('dart.vm.product')
                  ? null
                  : _$lessonByIdHash,
          dependencies: LessonByIdFamily._dependencies,
          allTransitiveDependencies:
              LessonByIdFamily._allTransitiveDependencies,
          id: id,
        );

  LessonByIdProvider._internal(
    super._createNotifier, {
    required super.name,
    required super.dependencies,
    required super.allTransitiveDependencies,
    required super.debugGetCreateSourceHash,
    required super.from,
    required this.id,
  }) : super.internal();

  final String id;

  @override
  Override overrideWith(
    FutureOr<Lesson> Function(LessonByIdRef provider) create,
  ) {
    return ProviderOverride(
      origin: this,
      override: LessonByIdProvider._internal(
        (ref) => create(ref as LessonByIdRef),
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
  AutoDisposeFutureProviderElement<Lesson> createElement() {
    return _LessonByIdProviderElement(this);
  }

  @override
  bool operator ==(Object other) {
    return other is LessonByIdProvider && other.id == id;
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
mixin LessonByIdRef on AutoDisposeFutureProviderRef<Lesson> {
  /// The parameter `id` of this provider.
  String get id;
}

class _LessonByIdProviderElement
    extends AutoDisposeFutureProviderElement<Lesson> with LessonByIdRef {
  _LessonByIdProviderElement(super.provider);

  @override
  String get id => (origin as LessonByIdProvider).id;
}

String _$certificateForCourseHash() =>
    r'afe99f65c450dd14b0c3b2aa07d51a44709defd4';

/// See also [certificateForCourse].
@ProviderFor(certificateForCourse)
const certificateForCourseProvider = CertificateForCourseFamily();

/// See also [certificateForCourse].
class CertificateForCourseFamily extends Family<AsyncValue<Certificate?>> {
  /// See also [certificateForCourse].
  const CertificateForCourseFamily();

  /// See also [certificateForCourse].
  CertificateForCourseProvider call(
    int courseId,
  ) {
    return CertificateForCourseProvider(
      courseId,
    );
  }

  @override
  CertificateForCourseProvider getProviderOverride(
    covariant CertificateForCourseProvider provider,
  ) {
    return call(
      provider.courseId,
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
  String? get name => r'certificateForCourseProvider';
}

/// See also [certificateForCourse].
class CertificateForCourseProvider
    extends AutoDisposeFutureProvider<Certificate?> {
  /// See also [certificateForCourse].
  CertificateForCourseProvider(
    int courseId,
  ) : this._internal(
          (ref) => certificateForCourse(
            ref as CertificateForCourseRef,
            courseId,
          ),
          from: certificateForCourseProvider,
          name: r'certificateForCourseProvider',
          debugGetCreateSourceHash:
              const bool.fromEnvironment('dart.vm.product')
                  ? null
                  : _$certificateForCourseHash,
          dependencies: CertificateForCourseFamily._dependencies,
          allTransitiveDependencies:
              CertificateForCourseFamily._allTransitiveDependencies,
          courseId: courseId,
        );

  CertificateForCourseProvider._internal(
    super._createNotifier, {
    required super.name,
    required super.dependencies,
    required super.allTransitiveDependencies,
    required super.debugGetCreateSourceHash,
    required super.from,
    required this.courseId,
  }) : super.internal();

  final int courseId;

  @override
  Override overrideWith(
    FutureOr<Certificate?> Function(CertificateForCourseRef provider) create,
  ) {
    return ProviderOverride(
      origin: this,
      override: CertificateForCourseProvider._internal(
        (ref) => create(ref as CertificateForCourseRef),
        from: from,
        name: null,
        dependencies: null,
        allTransitiveDependencies: null,
        debugGetCreateSourceHash: null,
        courseId: courseId,
      ),
    );
  }

  @override
  AutoDisposeFutureProviderElement<Certificate?> createElement() {
    return _CertificateForCourseProviderElement(this);
  }

  @override
  bool operator ==(Object other) {
    return other is CertificateForCourseProvider && other.courseId == courseId;
  }

  @override
  int get hashCode {
    var hash = _SystemHash.combine(0, runtimeType.hashCode);
    hash = _SystemHash.combine(hash, courseId.hashCode);

    return _SystemHash.finish(hash);
  }
}

@Deprecated('Will be removed in 3.0. Use Ref instead')
// ignore: unused_element
mixin CertificateForCourseRef on AutoDisposeFutureProviderRef<Certificate?> {
  /// The parameter `courseId` of this provider.
  int get courseId;
}

class _CertificateForCourseProviderElement
    extends AutoDisposeFutureProviderElement<Certificate?>
    with CertificateForCourseRef {
  _CertificateForCourseProviderElement(super.provider);

  @override
  int get courseId => (origin as CertificateForCourseProvider).courseId;
}

String _$courseReviewsHash() => r'6158f77433daced4e77c24825a6e22c610064888';

/// See also [courseReviews].
@ProviderFor(courseReviews)
const courseReviewsProvider = CourseReviewsFamily();

/// See also [courseReviews].
class CourseReviewsFamily extends Family<AsyncValue<Map<String, dynamic>>> {
  /// See also [courseReviews].
  const CourseReviewsFamily();

  /// See also [courseReviews].
  CourseReviewsProvider call(
    String courseId,
  ) {
    return CourseReviewsProvider(
      courseId,
    );
  }

  @override
  CourseReviewsProvider getProviderOverride(
    covariant CourseReviewsProvider provider,
  ) {
    return call(
      provider.courseId,
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
  String? get name => r'courseReviewsProvider';
}

/// See also [courseReviews].
class CourseReviewsProvider
    extends AutoDisposeFutureProvider<Map<String, dynamic>> {
  /// See also [courseReviews].
  CourseReviewsProvider(
    String courseId,
  ) : this._internal(
          (ref) => courseReviews(
            ref as CourseReviewsRef,
            courseId,
          ),
          from: courseReviewsProvider,
          name: r'courseReviewsProvider',
          debugGetCreateSourceHash:
              const bool.fromEnvironment('dart.vm.product')
                  ? null
                  : _$courseReviewsHash,
          dependencies: CourseReviewsFamily._dependencies,
          allTransitiveDependencies:
              CourseReviewsFamily._allTransitiveDependencies,
          courseId: courseId,
        );

  CourseReviewsProvider._internal(
    super._createNotifier, {
    required super.name,
    required super.dependencies,
    required super.allTransitiveDependencies,
    required super.debugGetCreateSourceHash,
    required super.from,
    required this.courseId,
  }) : super.internal();

  final String courseId;

  @override
  Override overrideWith(
    FutureOr<Map<String, dynamic>> Function(CourseReviewsRef provider) create,
  ) {
    return ProviderOverride(
      origin: this,
      override: CourseReviewsProvider._internal(
        (ref) => create(ref as CourseReviewsRef),
        from: from,
        name: null,
        dependencies: null,
        allTransitiveDependencies: null,
        debugGetCreateSourceHash: null,
        courseId: courseId,
      ),
    );
  }

  @override
  AutoDisposeFutureProviderElement<Map<String, dynamic>> createElement() {
    return _CourseReviewsProviderElement(this);
  }

  @override
  bool operator ==(Object other) {
    return other is CourseReviewsProvider && other.courseId == courseId;
  }

  @override
  int get hashCode {
    var hash = _SystemHash.combine(0, runtimeType.hashCode);
    hash = _SystemHash.combine(hash, courseId.hashCode);

    return _SystemHash.finish(hash);
  }
}

@Deprecated('Will be removed in 3.0. Use Ref instead')
// ignore: unused_element
mixin CourseReviewsRef on AutoDisposeFutureProviderRef<Map<String, dynamic>> {
  /// The parameter `courseId` of this provider.
  String get courseId;
}

class _CourseReviewsProviderElement
    extends AutoDisposeFutureProviderElement<Map<String, dynamic>>
    with CourseReviewsRef {
  _CourseReviewsProviderElement(super.provider);

  @override
  String get courseId => (origin as CourseReviewsProvider).courseId;
}
// ignore_for_file: type=lint
// ignore_for_file: subtype_of_sealed_class, invalid_use_of_internal_member, invalid_use_of_visible_for_testing_member, deprecated_member_use_from_same_package
