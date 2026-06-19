import 'dart:async';

import 'package:flutter/foundation.dart';

import '../../../core/hardware/domain/messaging/event_router.dart';
import '../../../core/hardware/domain/models/hardware_event.dart';
import '../domain/models/assist_trigger.dart';
import 'assist_controller.dart';

/// Service responsible for translating external events into AssistTriggers.
class AssistIngressService {
  final EventRouter _eventRouter;
  final AssistController _assistController;

  StreamSubscription<HardwareEvent>? _subscription;

  AssistIngressService({
    required EventRouter eventRouter,
    required AssistController assistController,
  })  : _eventRouter = eventRouter,
        _assistController = assistController;

  void start() {
    _subscription = _eventRouter.resolvedEvents.listen(_handleHardwareEvent);
    debugPrint('AssistIngressService started');
  }

  void dispose() {
    _subscription?.cancel();
    debugPrint('AssistIngressService disposed');
  }

  void _handleHardwareEvent(HardwareEvent event) {
    if (event is ButtonPressEvent) {
      _handleButtonEvent(event);
    }
  }

  void _handleButtonEvent(ButtonPressEvent event) {
    switch (event.pressType) {
      case ButtonPressType.short:
        final trigger = AssistTrigger.create(
          sourceType: AssistTriggerSourceType.hardwareButton,
          pressType: AssistPressType.tap,
          sourceDeviceId: event.deviceId,
        );
        debugPrint('Assist trigger created: ${trigger.triggerId}');
        _assistController.triggerAssist(trigger);
        break;
      case ButtonPressType.long:
        debugPrint('Long press reserved for future STT support');
        break;
      case ButtonPressType.double:
      case ButtonPressType.triple:
        // Ignored
        break;
    }
  }
}
