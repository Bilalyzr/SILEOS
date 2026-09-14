import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sashalms/features/courses/domain/entities/course.dart';

class CartNotifier extends StateNotifier<List<Course>> {
  CartNotifier() : super([]);

  void addToCart(Course course) {
    if (!state.any((item) => item.id == course.id)) {
      state = [...state, course];
    }
  }

  void removeFromCart(String courseId) {
    state = state.where((item) => item.id != courseId).toList();
  }

  void clearCart() {
    state = [];
  }

  double get totalPrice => state.fold(0, (sum, item) => sum + item.price);
}

final cartProvider = StateNotifierProvider<CartNotifier, List<Course>>((ref) {
  return CartNotifier();
});
