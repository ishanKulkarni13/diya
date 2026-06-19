import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/hardware/providers/hardware_providers.dart';
import '../application/obstacle_ingress_service.dart';
import '../domain/obstacle_state.dart';

/// Provides the single [ObstacleIngressService] instance for the app lifetime.
/// Reading this provider starts the subscription automatically.
final obstacleIngressServiceProvider =
    StateNotifierProvider<ObstacleIngressService, ObstacleState?>((ref) {
  final service = ObstacleIngressService(
    eventRouter: ref.watch(eventRouterProvider),
  );
  ref.onDispose(() => service.dispose());
  return service;
});
