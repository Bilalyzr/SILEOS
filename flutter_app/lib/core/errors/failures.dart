import 'package:freezed_annotation/freezed_annotation.dart';

part 'failures.freezed.dart';

@freezed
class Failure with _$Failure {
  const factory Failure.server({
    required String message,
    int? statusCode,
  }) = ServerFailure;

  const factory Failure.network({
    required String message,
  }) = NetworkFailure;

  const factory Failure.cache({
    required String message,
  }) = CacheFailure;

  const factory Failure.unauthorized({
    String? message,
  }) = UnauthorizedFailure;

  const factory Failure.forbidden({
    String? message,
  }) = ForbiddenFailure;

  const factory Failure.notFound({
    String? message,
  }) = NotFoundFailure;

  const factory Failure.validation({
    required String message,
    Map<String, dynamic>? fieldErrors,
  }) = ValidationFailure;

  const factory Failure.unknown({
    String? message,
  }) = UnknownFailure;
}
