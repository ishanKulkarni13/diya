/// Calculates delays for BLE reconnect attempts.
///
/// Sequence: 1s → 3s → 5s → 10s → 30s (then holds at 30s).
/// These steps were chosen to feel responsive in the first few seconds
/// while not hammering the BLE stack during a prolonged outage.
class BackoffStrategy {
  static const List<int> _stepsMs = [1000, 3000, 5000, 10000, 30000];

  int calculateDelay(int attemptCount) {
    if (attemptCount <= 0) return 0;
    final index = (attemptCount - 1).clamp(0, _stepsMs.length - 1);
    return _stepsMs[index];
  }
}
