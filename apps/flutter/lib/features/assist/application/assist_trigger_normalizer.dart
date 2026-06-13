import '../domain/models/assist_intent.dart';
import '../domain/models/assist_trigger.dart';

/// Converts a raw AssistTrigger into a normalized AssistIntent.
class AssistTriggerNormalizer {
  AssistIntent normalize(AssistTrigger trigger) {
    if (trigger.sourceType == AssistTriggerSourceType.uiButton) {
      if (trigger.pressType == AssistPressType.tap) {
        return const AssistIntent(type: AssistIntentType.describeScene);
      } else if (trigger.pressType == AssistPressType.longPress) {
        return const AssistIntent(type: AssistIntentType.answerQuestionAboutScene);
      }
    }
    
    // Default to describe scene for unknown or simple taps
    return const AssistIntent(type: AssistIntentType.describeScene);
  }
}
