import '../models/hardware_event.dart';

enum BleLifecycleType {
  scanStarted,
  scanStopped,
  deviceDiscovered,
  connectionStarted,
  connectionEstablished,
  connectionLost,
  reconnectAttempt,
  reconnectSuccess,
  heartbeatTimeout,
  heartbeatRestored,
}

class BleLifecycleEvent extends HardwareEvent {
  final BleLifecycleType type;
  final String? details;

  BleLifecycleEvent({
    required super.deviceId,
    required this.type,
    this.details,
    super.eventId,
    super.timestamp,
  }) : super(priority: 5, trusted: true); // Priority 5 = informative, trusted = internal transport
}
