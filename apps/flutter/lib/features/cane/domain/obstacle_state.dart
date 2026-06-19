/// Minimal snapshot of the latest obstacle telemetry from the Smart Cane.
///
/// Intentionally thin — no history, no persistence.
/// UI reads this; ObstacleIngressService writes it.
class ObstacleState {
  final double distanceCm;
  final bool detected;
  final DateTime updatedAt;

  const ObstacleState({
    required this.distanceCm,
    required this.detected,
    required this.updatedAt,
  });
}
