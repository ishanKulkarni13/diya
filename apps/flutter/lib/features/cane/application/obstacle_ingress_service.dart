import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/hardware/domain/messaging/event_router.dart';
import '../../../core/hardware/domain/models/hardware_event.dart';
import '../domain/obstacle_state.dart';

/// Subscribes to [EventRouter.resolvedEvents], filters [UltrasonicDetectionEvent],
/// and exposes the latest [ObstacleState] via a [StateNotifier].
///
/// Responsibilities:
///   - Subscribe to the resolved event stream.
///   - Store the latest obstacle reading.
///   - Expose state for UI consumption.
///   - Debug logging.
///
/// Does NOT: speak, trigger Assist, trigger Gemini, maintain history,
/// or persist telemetry.
class ObstacleIngressService extends StateNotifier<ObstacleState?> {
  final EventRouter _eventRouter;
  StreamSubscription<HardwareEvent>? _subscription;

  ObstacleIngressService({required EventRouter eventRouter})
      : _eventRouter = eventRouter,
        super(null) {
    _subscription = _eventRouter.resolvedEvents.listen(_onEvent);
    debugPrint('ObstacleIngressService started');
  }

  void _onEvent(HardwareEvent event) {
    if (event is UltrasonicDetectionEvent) {
      debugPrint(
        'ObstacleIngressService: ${event.distanceCm.toStringAsFixed(1)} cm '
        'detected=${event.detected} device=${event.deviceId}',
      );
      state = ObstacleState(
        distanceCm: event.distanceCm,
        detected: event.detected,
        updatedAt: DateTime.now(),
      );
    }
  }

  @override
  void dispose() {
    _subscription?.cancel();
    debugPrint('ObstacleIngressService disposed');
    super.dispose();
  }
}
