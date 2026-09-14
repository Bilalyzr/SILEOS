import 'package:freezed_annotation/freezed_annotation.dart';

part 'user.freezed.dart';

@freezed
class User with _$User {
  const factory User({
    required String id,
    required String email,
    required String firstName,
    required String lastName,
    required String role,
    String? avatarUrl,
    String? phone,
    bool? isActive,
    DateTime? createdAt,
  }) = _User;

  const User._();

  String get fullName => '$firstName $lastName';

  bool get isInstructor => role == 'instructor';
  bool get isAdmin => role == 'admin';
  bool get isStudent => role == 'student';
  bool get isCompanyManager => role == 'company_manager';
  bool get isCompany => role == 'company';
}
