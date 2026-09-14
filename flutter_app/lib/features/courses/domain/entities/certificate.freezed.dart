// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint
// ignore_for_file: unused_element, deprecated_member_use, deprecated_member_use_from_same_package, use_function_type_syntax_for_parameters, unnecessary_const, avoid_init_to_null, invalid_override_different_default_values_named, prefer_expression_function_bodies, annotate_overrides, invalid_annotation_target, unnecessary_question_mark

part of 'certificate.dart';

// **************************************************************************
// FreezedGenerator
// **************************************************************************

T _$identity<T>(T value) => value;

final _privateConstructorUsedError = UnsupportedError(
    'It seems like you constructed your class using `MyClass._()`. This constructor is only meant to be used by freezed and you are not supposed to need it nor use it.\nPlease check the documentation here for more information: https://github.com/rrousselGit/freezed#adding-getters-and-methods-to-our-models');

/// @nodoc
mixin _$Certificate {
  String get id => throw _privateConstructorUsedError;
  String get courseId => throw _privateConstructorUsedError;
  String get userId => throw _privateConstructorUsedError;
  String get certificateUrl => throw _privateConstructorUsedError;
  String get verificationCode => throw _privateConstructorUsedError;
  DateTime get issuedAt => throw _privateConstructorUsedError;

  /// Create a copy of Certificate
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  $CertificateCopyWith<Certificate> get copyWith =>
      throw _privateConstructorUsedError;
}

/// @nodoc
abstract class $CertificateCopyWith<$Res> {
  factory $CertificateCopyWith(
          Certificate value, $Res Function(Certificate) then) =
      _$CertificateCopyWithImpl<$Res, Certificate>;
  @useResult
  $Res call(
      {String id,
      String courseId,
      String userId,
      String certificateUrl,
      String verificationCode,
      DateTime issuedAt});
}

/// @nodoc
class _$CertificateCopyWithImpl<$Res, $Val extends Certificate>
    implements $CertificateCopyWith<$Res> {
  _$CertificateCopyWithImpl(this._value, this._then);

  // ignore: unused_field
  final $Val _value;
  // ignore: unused_field
  final $Res Function($Val) _then;

  /// Create a copy of Certificate
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? id = null,
    Object? courseId = null,
    Object? userId = null,
    Object? certificateUrl = null,
    Object? verificationCode = null,
    Object? issuedAt = null,
  }) {
    return _then(_value.copyWith(
      id: null == id
          ? _value.id
          : id // ignore: cast_nullable_to_non_nullable
              as String,
      courseId: null == courseId
          ? _value.courseId
          : courseId // ignore: cast_nullable_to_non_nullable
              as String,
      userId: null == userId
          ? _value.userId
          : userId // ignore: cast_nullable_to_non_nullable
              as String,
      certificateUrl: null == certificateUrl
          ? _value.certificateUrl
          : certificateUrl // ignore: cast_nullable_to_non_nullable
              as String,
      verificationCode: null == verificationCode
          ? _value.verificationCode
          : verificationCode // ignore: cast_nullable_to_non_nullable
              as String,
      issuedAt: null == issuedAt
          ? _value.issuedAt
          : issuedAt // ignore: cast_nullable_to_non_nullable
              as DateTime,
    ) as $Val);
  }
}

/// @nodoc
abstract class _$$CertificateImplCopyWith<$Res>
    implements $CertificateCopyWith<$Res> {
  factory _$$CertificateImplCopyWith(
          _$CertificateImpl value, $Res Function(_$CertificateImpl) then) =
      __$$CertificateImplCopyWithImpl<$Res>;
  @override
  @useResult
  $Res call(
      {String id,
      String courseId,
      String userId,
      String certificateUrl,
      String verificationCode,
      DateTime issuedAt});
}

/// @nodoc
class __$$CertificateImplCopyWithImpl<$Res>
    extends _$CertificateCopyWithImpl<$Res, _$CertificateImpl>
    implements _$$CertificateImplCopyWith<$Res> {
  __$$CertificateImplCopyWithImpl(
      _$CertificateImpl _value, $Res Function(_$CertificateImpl) _then)
      : super(_value, _then);

  /// Create a copy of Certificate
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? id = null,
    Object? courseId = null,
    Object? userId = null,
    Object? certificateUrl = null,
    Object? verificationCode = null,
    Object? issuedAt = null,
  }) {
    return _then(_$CertificateImpl(
      id: null == id
          ? _value.id
          : id // ignore: cast_nullable_to_non_nullable
              as String,
      courseId: null == courseId
          ? _value.courseId
          : courseId // ignore: cast_nullable_to_non_nullable
              as String,
      userId: null == userId
          ? _value.userId
          : userId // ignore: cast_nullable_to_non_nullable
              as String,
      certificateUrl: null == certificateUrl
          ? _value.certificateUrl
          : certificateUrl // ignore: cast_nullable_to_non_nullable
              as String,
      verificationCode: null == verificationCode
          ? _value.verificationCode
          : verificationCode // ignore: cast_nullable_to_non_nullable
              as String,
      issuedAt: null == issuedAt
          ? _value.issuedAt
          : issuedAt // ignore: cast_nullable_to_non_nullable
              as DateTime,
    ));
  }
}

/// @nodoc

class _$CertificateImpl implements _Certificate {
  const _$CertificateImpl(
      {required this.id,
      required this.courseId,
      required this.userId,
      required this.certificateUrl,
      required this.verificationCode,
      required this.issuedAt});

  @override
  final String id;
  @override
  final String courseId;
  @override
  final String userId;
  @override
  final String certificateUrl;
  @override
  final String verificationCode;
  @override
  final DateTime issuedAt;

  @override
  String toString() {
    return 'Certificate(id: $id, courseId: $courseId, userId: $userId, certificateUrl: $certificateUrl, verificationCode: $verificationCode, issuedAt: $issuedAt)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$CertificateImpl &&
            (identical(other.id, id) || other.id == id) &&
            (identical(other.courseId, courseId) ||
                other.courseId == courseId) &&
            (identical(other.userId, userId) || other.userId == userId) &&
            (identical(other.certificateUrl, certificateUrl) ||
                other.certificateUrl == certificateUrl) &&
            (identical(other.verificationCode, verificationCode) ||
                other.verificationCode == verificationCode) &&
            (identical(other.issuedAt, issuedAt) ||
                other.issuedAt == issuedAt));
  }

  @override
  int get hashCode => Object.hash(runtimeType, id, courseId, userId,
      certificateUrl, verificationCode, issuedAt);

  /// Create a copy of Certificate
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  @pragma('vm:prefer-inline')
  _$$CertificateImplCopyWith<_$CertificateImpl> get copyWith =>
      __$$CertificateImplCopyWithImpl<_$CertificateImpl>(this, _$identity);
}

abstract class _Certificate implements Certificate {
  const factory _Certificate(
      {required final String id,
      required final String courseId,
      required final String userId,
      required final String certificateUrl,
      required final String verificationCode,
      required final DateTime issuedAt}) = _$CertificateImpl;

  @override
  String get id;
  @override
  String get courseId;
  @override
  String get userId;
  @override
  String get certificateUrl;
  @override
  String get verificationCode;
  @override
  DateTime get issuedAt;

  /// Create a copy of Certificate
  /// with the given fields replaced by the non-null parameter values.
  @override
  @JsonKey(includeFromJson: false, includeToJson: false)
  _$$CertificateImplCopyWith<_$CertificateImpl> get copyWith =>
      throw _privateConstructorUsedError;
}
