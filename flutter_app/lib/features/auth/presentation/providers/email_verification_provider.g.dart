// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'email_verification_provider.dart';

// **************************************************************************
// RiverpodGenerator
// **************************************************************************

String _$emailVerificationHash() => r'24ce5199dde1111c665cd2d457ebdebc46d40e9f';

/// Drives the verify-email screen and the inline "resend verification"
/// action on the login form.
/// State: `AsyncData(null)` = idle, `AsyncData(message)` = success message,
/// `AsyncError` = failure to show inline.
///
/// Copied from [EmailVerification].
@ProviderFor(EmailVerification)
final emailVerificationProvider = AutoDisposeNotifierProvider<EmailVerification,
    AsyncValue<String?>>.internal(
  EmailVerification.new,
  name: r'emailVerificationProvider',
  debugGetCreateSourceHash: const bool.fromEnvironment('dart.vm.product')
      ? null
      : _$emailVerificationHash,
  dependencies: null,
  allTransitiveDependencies: null,
);

typedef _$EmailVerification = AutoDisposeNotifier<AsyncValue<String?>>;
// ignore_for_file: type=lint
// ignore_for_file: subtype_of_sealed_class, invalid_use_of_internal_member, invalid_use_of_visible_for_testing_member, deprecated_member_use_from_same_package
