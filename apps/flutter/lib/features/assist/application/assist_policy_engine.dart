import '../../../core/errors/app_error.dart';
import '../domain/models/assist_intent.dart';
import '../domain/models/assist_trigger.dart';

/// Owns source-agnostic rules before a turn starts (dedupe, preemption).
class AssistPolicyEngine {
  /// Checks preflight rules like SOS preemption.
  /// Throws AppError if the turn should be rejected.
  void validatePreflight({
    required AssistTrigger trigger,
    required AssistIntent intent,
    required bool isSafetyActive,
  }) {
    if (isSafetyActive) {
      throw AppError.assist(
        'Assist preempted by active SOS event.',
        code: 'assist.preempted_by_sos',
      );
    }
  }
}
