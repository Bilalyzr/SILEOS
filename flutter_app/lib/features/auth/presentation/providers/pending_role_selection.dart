// lib/features/auth/presentation/providers/pending_role_selection.dart
import 'package:riverpod_annotation/riverpod_annotation.dart';

part 'pending_role_selection.g.dart';

@riverpod
class PendingRoleSelection extends _$PendingRoleSelection {
  @override
  Map<String, String>? build() => null;

  void set({
    required String email,
    required String name,
    required String picture,
    required String token,
  }) {
    state = {
      'email': email,
      'name': name,
      'picture': picture,
      'token': token,
    };
  }

  void clear() {
    state = null;
  }
}
