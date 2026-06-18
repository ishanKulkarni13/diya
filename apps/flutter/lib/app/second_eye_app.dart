import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'app_router.dart';

import 'package:diya_flutter/features/debug/widgets/secret_debug_trigger.dart';

class SecondEyeApp extends ConsumerWidget {
  const SecondEyeApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final router = ref.watch(appRouterProvider);

    return MaterialApp.router(
      title: '2ndEye',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: const Color(0xFF1466FF)),
        useMaterial3: true,
      ),
      builder: (context, child) => SecretDebugTrigger(child: child!),
      routerConfig: router,
    );
  }
}
