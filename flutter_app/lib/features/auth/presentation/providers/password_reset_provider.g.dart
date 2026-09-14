// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'password_reset_provider.dart';

// **************************************************************************
// RiverpodGenerator
// **************************************************************************

String _$passwordResetHash() => r'e5d6e427877a4531482233fe8747606d3c2b2f6a';

/// Drives the forgot/reset password screens.
/// State: `AsyncData(null)` = idle, `AsyncData(message)` = success message
/// from the backend, `AsyncError` = failure to show inline.
///
/// Copied from [PasswordReset].
@ProviderFor(PasswordReset)
final passwordResetProvider =
    AutoDisposeNotifierProvider<PasswordReset, AsyncValue<String?>>.internal(
  PasswordReset.new,
  name: r'passwordResetProvider',
  debugGetCreateSourceHash: const bool.fromEnvironment('dart.vm.product')
      ? null
      : _$passwordResetHash,
  dependencies: null,
  allTransitiveDependencies: null,
);

typedef _$PasswordReset = AutoDisposeNotifier<AsyncValue<String?>>;
// ignore_for_file: type=lint
// ignore_for_file: subtype_of_sealed_class, invalid_use_of_internal_member, invalid_use_of_visible_for_testing_member, deprecated_member_use_from_same_package
