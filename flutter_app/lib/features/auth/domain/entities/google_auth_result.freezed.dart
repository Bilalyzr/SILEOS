// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint
// ignore_for_file: unused_element, deprecated_member_use, deprecated_member_use_from_same_package, use_function_type_syntax_for_parameters, unnecessary_const, avoid_init_to_null, invalid_override_different_default_values_named, prefer_expression_function_bodies, annotate_overrides, invalid_annotation_target, unnecessary_question_mark

part of 'google_auth_result.dart';

// **************************************************************************
// FreezedGenerator
// **************************************************************************

T _$identity<T>(T value) => value;

final _privateConstructorUsedError = UnsupportedError(
    'It seems like you constructed your class using `MyClass._()`. This constructor is only meant to be used by freezed and you are not supposed to need it nor use it.\nPlease check the documentation here for more information: https://github.com/rrousselGit/freezed#adding-getters-and-methods-to-our-models');

/// @nodoc
mixin _$GoogleAuthResult {
  @optionalTypeArgs
  TResult when<TResult extends Object?>({
    required TResult Function(User user) signedIn,
    required TResult Function(
            String email, String name, String picture, String firebaseToken)
        needsRole,
  }) =>
      throw _privateConstructorUsedError;
  @optionalTypeArgs
  TResult? whenOrNull<TResult extends Object?>({
    TResult? Function(User user)? signedIn,
    TResult? Function(
            String email, String name, String picture, String firebaseToken)?
        needsRole,
  }) =>
      throw _privateConstructorUsedError;
  @optionalTypeArgs
  TResult maybeWhen<TResult extends Object?>({
    TResult Function(User user)? signedIn,
    TResult Function(
            String email, String name, String picture, String firebaseToken)?
        needsRole,
    required TResult orElse(),
  }) =>
      throw _privateConstructorUsedError;
  @optionalTypeArgs
  TResult map<TResult extends Object?>({
    required TResult Function(_SignedIn value) signedIn,
    required TResult Function(_NeedsRole value) needsRole,
  }) =>
      throw _privateConstructorUsedError;
  @optionalTypeArgs
  TResult? mapOrNull<TResult extends Object?>({
    TResult? Function(_SignedIn value)? signedIn,
    TResult? Function(_NeedsRole value)? needsRole,
  }) =>
      throw _privateConstructorUsedError;
  @optionalTypeArgs
  TResult maybeMap<TResult extends Object?>({
    TResult Function(_SignedIn value)? signedIn,
    TResult Function(_NeedsRole value)? needsRole,
    required TResult orElse(),
  }) =>
      throw _privateConstructorUsedError;
}

/// @nodoc
abstract class $GoogleAuthResultCopyWith<$Res> {
  factory $GoogleAuthResultCopyWith(
          GoogleAuthResult value, $Res Function(GoogleAuthResult) then) =
      _$GoogleAuthResultCopyWithImpl<$Res, GoogleAuthResult>;
}

/// @nodoc
class _$GoogleAuthResultCopyWithImpl<$Res, $Val extends GoogleAuthResult>
    implements $GoogleAuthResultCopyWith<$Res> {
  _$GoogleAuthResultCopyWithImpl(this._value, this._then);

  // ignore: unused_field
  final $Val _value;
  // ignore: unused_field
  final $Res Function($Val) _then;

  /// Create a copy of GoogleAuthResult
  /// with the given fields replaced by the non-null parameter values.
}

/// @nodoc
abstract class _$$SignedInImplCopyWith<$Res> {
  factory _$$SignedInImplCopyWith(
          _$SignedInImpl value, $Res Function(_$SignedInImpl) then) =
      __$$SignedInImplCopyWithImpl<$Res>;
  @useResult
  $Res call({User user});

  $UserCopyWith<$Res> get user;
}

/// @nodoc
class __$$SignedInImplCopyWithImpl<$Res>
    extends _$GoogleAuthResultCopyWithImpl<$Res, _$SignedInImpl>
    implements _$$SignedInImplCopyWith<$Res> {
  __$$SignedInImplCopyWithImpl(
      _$SignedInImpl _value, $Res Function(_$SignedInImpl) _then)
      : super(_value, _then);

  /// Create a copy of GoogleAuthResult
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? user = null,
  }) {
    return _then(_$SignedInImpl(
      null == user
          ? _value.user
          : user // ignore: cast_nullable_to_non_nullable
              as User,
    ));
  }

  /// Create a copy of GoogleAuthResult
  /// with the given fields replaced by the non-null parameter values.
  @override
  @pragma('vm:prefer-inline')
  $UserCopyWith<$Res> get user {
    return $UserCopyWith<$Res>(_value.user, (value) {
      return _then(_value.copyWith(user: value));
    });
  }
}

/// @nodoc

class _$SignedInImpl implements _SignedIn {
  const _$SignedInImpl(this.user);

  @override
  final User user;

  @override
  String toString() {
    return 'GoogleAuthResult.signedIn(user: $user)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$SignedInImpl &&
            (identical(other.user, user) || other.user == user));
  }

  @override
  int get hashCode => Object.hash(runtimeType, user);

  /// Create a copy of GoogleAuthResult
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  @pragma('vm:prefer-inline')
  _$$SignedInImplCopyWith<_$SignedInImpl> get copyWith =>
      __$$SignedInImplCopyWithImpl<_$SignedInImpl>(this, _$identity);

  @override
  @optionalTypeArgs
  TResult when<TResult extends Object?>({
    required TResult Function(User user) signedIn,
    required TResult Function(
            String email, String name, String picture, String firebaseToken)
        needsRole,
  }) {
    return signedIn(user);
  }

  @override
  @optionalTypeArgs
  TResult? whenOrNull<TResult extends Object?>({
    TResult? Function(User user)? signedIn,
    TResult? Function(
            String email, String name, String picture, String firebaseToken)?
        needsRole,
  }) {
    return signedIn?.call(user);
  }

  @override
  @optionalTypeArgs
  TResult maybeWhen<TResult extends Object?>({
    TResult Function(User user)? signedIn,
    TResult Function(
            String email, String name, String picture, String firebaseToken)?
        needsRole,
    required TResult orElse(),
  }) {
    if (signedIn != null) {
      return signedIn(user);
    }
    return orElse();
  }

  @override
  @optionalTypeArgs
  TResult map<TResult extends Object?>({
    required TResult Function(_SignedIn value) signedIn,
    required TResult Function(_NeedsRole value) needsRole,
  }) {
    return signedIn(this);
  }

  @override
  @optionalTypeArgs
  TResult? mapOrNull<TResult extends Object?>({
    TResult? Function(_SignedIn value)? signedIn,
    TResult? Function(_NeedsRole value)? needsRole,
  }) {
    return signedIn?.call(this);
  }

  @override
  @optionalTypeArgs
  TResult maybeMap<TResult extends Object?>({
    TResult Function(_SignedIn value)? signedIn,
    TResult Function(_NeedsRole value)? needsRole,
    required TResult orElse(),
  }) {
    if (signedIn != null) {
      return signedIn(this);
    }
    return orElse();
  }
}

abstract class _SignedIn implements GoogleAuthResult {
  const factory _SignedIn(final User user) = _$SignedInImpl;

  User get user;

  /// Create a copy of GoogleAuthResult
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  _$$SignedInImplCopyWith<_$SignedInImpl> get copyWith =>
      throw _privateConstructorUsedError;
}

/// @nodoc
abstract class _$$NeedsRoleImplCopyWith<$Res> {
  factory _$$NeedsRoleImplCopyWith(
          _$NeedsRoleImpl value, $Res Function(_$NeedsRoleImpl) then) =
      __$$NeedsRoleImplCopyWithImpl<$Res>;
  @useResult
  $Res call({String email, String name, String picture, String firebaseToken});
}

/// @nodoc
class __$$NeedsRoleImplCopyWithImpl<$Res>
    extends _$GoogleAuthResultCopyWithImpl<$Res, _$NeedsRoleImpl>
    implements _$$NeedsRoleImplCopyWith<$Res> {
  __$$NeedsRoleImplCopyWithImpl(
      _$NeedsRoleImpl _value, $Res Function(_$NeedsRoleImpl) _then)
      : super(_value, _then);

  /// Create a copy of GoogleAuthResult
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? email = null,
    Object? name = null,
    Object? picture = null,
    Object? firebaseToken = null,
  }) {
    return _then(_$NeedsRoleImpl(
      email: null == email
          ? _value.email
          : email // ignore: cast_nullable_to_non_nullable
              as String,
      name: null == name
          ? _value.name
          : name // ignore: cast_nullable_to_non_nullable
              as String,
      picture: null == picture
          ? _value.picture
          : picture // ignore: cast_nullable_to_non_nullable
              as String,
      firebaseToken: null == firebaseToken
          ? _value.firebaseToken
          : firebaseToken // ignore: cast_nullable_to_non_nullable
              as String,
    ));
  }
}

/// @nodoc

class _$NeedsRoleImpl implements _NeedsRole {
  const _$NeedsRoleImpl(
      {required this.email,
      required this.name,
      required this.picture,
      required this.firebaseToken});

  @override
  final String email;
  @override
  final String name;
  @override
  final String picture;
  @override
  final String firebaseToken;

  @override
  String toString() {
    return 'GoogleAuthResult.needsRole(email: $email, name: $name, picture: $picture, firebaseToken: $firebaseToken)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$NeedsRoleImpl &&
            (identical(other.email, email) || other.email == email) &&
            (identical(other.name, name) || other.name == name) &&
            (identical(other.picture, picture) || other.picture == picture) &&
            (identical(other.firebaseToken, firebaseToken) ||
                other.firebaseToken == firebaseToken));
  }

  @override
  int get hashCode =>
      Object.hash(runtimeType, email, name, picture, firebaseToken);

  /// Create a copy of GoogleAuthResult
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  @pragma('vm:prefer-inline')
  _$$NeedsRoleImplCopyWith<_$NeedsRoleImpl> get copyWith =>
      __$$NeedsRoleImplCopyWithImpl<_$NeedsRoleImpl>(this, _$identity);

  @override
  @optionalTypeArgs
  TResult when<TResult extends Object?>({
    required TResult Function(User user) signedIn,
    required TResult Function(
            String email, String name, String picture, String firebaseToken)
        needsRole,
  }) {
    return needsRole(email, name, picture, firebaseToken);
  }

  @override
  @optionalTypeArgs
  TResult? whenOrNull<TResult extends Object?>({
    TResult? Function(User user)? signedIn,
    TResult? Function(
            String email, String name, String picture, String firebaseToken)?
        needsRole,
  }) {
    return needsRole?.call(email, name, picture, firebaseToken);
  }

  @override
  @optionalTypeArgs
  TResult maybeWhen<TResult extends Object?>({
    TResult Function(User user)? signedIn,
    TResult Function(
            String email, String name, String picture, String firebaseToken)?
        needsRole,
    required TResult orElse(),
  }) {
    if (needsRole != null) {
      return needsRole(email, name, picture, firebaseToken);
    }
    return orElse();
  }

  @override
  @optionalTypeArgs
  TResult map<TResult extends Object?>({
    required TResult Function(_SignedIn value) signedIn,
    required TResult Function(_NeedsRole value) needsRole,
  }) {
    return needsRole(this);
  }

  @override
  @optionalTypeArgs
  TResult? mapOrNull<TResult extends Object?>({
    TResult? Function(_SignedIn value)? signedIn,
    TResult? Function(_NeedsRole value)? needsRole,
  }) {
    return needsRole?.call(this);
  }

  @override
  @optionalTypeArgs
  TResult maybeMap<TResult extends Object?>({
    TResult Function(_SignedIn value)? signedIn,
    TResult Function(_NeedsRole value)? needsRole,
    required TResult orElse(),
  }) {
    if (needsRole != null) {
      return needsRole(this);
    }
    return orElse();
  }
}

abstract class _NeedsRole implements GoogleAuthResult {
  const factory _NeedsRole(
      {required final String email,
      required final String name,
      required final String picture,
      required final String firebaseToken}) = _$NeedsRoleImpl;

  String get email;
  String get name;
  String get picture;
  String get firebaseToken;

  /// Create a copy of GoogleAuthResult
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  _$$NeedsRoleImplCopyWith<_$NeedsRoleImpl> get copyWith =>
      throw _privateConstructorUsedError;
}
