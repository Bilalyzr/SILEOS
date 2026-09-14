// lib/features/auth/data/models/user_model.dart
import 'package:freezed_annotation/freezed_annotation.dart';
import '../../domain/entities/user.dart';

part 'user_model.freezed.dart';
part 'user_model.g.dart';

@freezed
class UserModel with _$UserModel {
  const factory UserModel({
    @JsonKey(name: 'id') required String id,
    @JsonKey(name: 'email') required String email,
    @JsonKey(name: 'first_name') required String firstName,
    @JsonKey(name: 'last_name') required String lastName,
    @JsonKey(name: 'role') required String role,
    @JsonKey(name: 'avatar_url') String? avatarUrl,
    @JsonKey(name: 'phone') String? phone,
    @JsonKey(name: 'is_active') bool? isActive,
    @JsonKey(name: 'created_at') String? createdAt,
  }) = _UserModel;

  const UserModel._();

  factory UserModel.fromJson(Map<String, dynamic> json) =>
      _$UserModelFromJson(json);

  factory UserModel.fromAuthResponse(Map<String, dynamic> json) {
    final userData = json['user'] as Map<String, dynamic>;
    final profileData = json['profile'] as Map<String, dynamic>?;

    return UserModel(
      id: userData['id'].toString(),
      email: userData['email'],
      firstName: profileData?['first_name'] ?? '',
      lastName: profileData?['last_name'] ?? '',
      role: userData['role'],
      avatarUrl: profileData?['profile_photo'],
      phone: profileData?['phone'],
      isActive: true, // Assuming active if they can log in
      createdAt: null,
    );
  }

  User toEntity() {
    return User(
      id: id,
      email: email,
      firstName: firstName,
      lastName: lastName,
      role: role,
      avatarUrl: avatarUrl,
      phone: phone,
      isActive: isActive,
      createdAt: createdAt != null ? DateTime.tryParse(createdAt!) : null,
    );
  }

  factory UserModel.fromEntity(User entity) {
    return UserModel(
      id: entity.id,
      email: entity.email,
      firstName: entity.firstName,
      lastName: entity.lastName,
      role: entity.role,
      avatarUrl: entity.avatarUrl,
      phone: entity.phone,
      isActive: entity.isActive,
      createdAt: entity.createdAt?.toIso8601String(),
    );
  }
}
