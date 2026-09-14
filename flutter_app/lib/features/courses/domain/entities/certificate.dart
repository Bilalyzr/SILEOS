import 'package:freezed_annotation/freezed_annotation.dart';

part 'certificate.freezed.dart';

@freezed
class Certificate with _$Certificate {
  const factory Certificate({
    required String id,
    required String courseId,
    required String userId,
    required String certificateUrl,
    required String verificationCode,
    required DateTime issuedAt,
  }) = _Certificate;
}
