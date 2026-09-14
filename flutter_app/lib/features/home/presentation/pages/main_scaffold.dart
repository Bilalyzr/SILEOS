import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../../courses/presentation/providers/course_filter_providers.dart';
import '../../../courses/presentation/pages/all_courses_page.dart';
import 'package:sashalms/features/dashboard/presentation/pages/dashboard_page.dart';
import '../../../profile/presentation/pages/profile_page.dart';
import 'home_page.dart';

class MainScaffold extends ConsumerStatefulWidget {
  const MainScaffold({super.key});

  @override
  ConsumerState<MainScaffold> createState() => _MainScaffoldState();
}

class _MainScaffoldState extends ConsumerState<MainScaffold> {
  final List<Widget> _pages = const [
    HomePage(),
    AllCoursesPage(),
    DashboardPage(),
    ProfilePage(),
  ];

  @override
  Widget build(BuildContext context) {
    final currentIndex = ref.watch(scaffoldTabProvider);

    return Scaffold(
      floatingActionButton: currentIndex == 2 ? FloatingActionButton.extended(onPressed: () => context.push('/learning'), icon: const Icon(Icons.event_note), label: const Text('Learning workspace')) : null,
      body: IndexedStack(
        index: currentIndex,
        children: _pages,
      ),
      bottomNavigationBar: NavigationBar(
        selectedIndex: currentIndex,
        onDestinationSelected: (index) {
          ref.read(scaffoldTabProvider.notifier).state = index;
        },
        destinations: const [
          NavigationDestination(
            icon: Icon(Icons.home_outlined),
            selectedIcon: Icon(Icons.home),
            label: 'Home',
          ),
          NavigationDestination(
            icon: Icon(Icons.search_outlined),
            selectedIcon: Icon(Icons.search),
            label: 'Catalog',
          ),
          NavigationDestination(
            icon: Icon(Icons.dashboard_outlined),
            selectedIcon: Icon(Icons.dashboard),
            label: 'Dashboard',
          ),
          NavigationDestination(
            icon: Icon(Icons.person_outline),
            selectedIcon: Icon(Icons.person),
            label: 'Profile',
          ),
        ],
      ),
    );
  }
}
