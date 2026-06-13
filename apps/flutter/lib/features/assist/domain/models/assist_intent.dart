enum AssistIntentType {
  describeScene,
  answerQuestionAboutScene,
  continueConversation,
  repeatLastResponse,
  stopSpeaking,
  cancelAssist,
}

/// Normalized command consumed by the Assist pipeline.
class AssistIntent {
  const AssistIntent({
    required this.type,
    this.query,
  });

  final AssistIntentType type;
  final String? query;

  Map<String, dynamic> toJson() {
    return {
      'type': _typeToString(type),
      if (query != null) 'query': query,
    };
  }

  String _typeToString(AssistIntentType t) {
    switch (t) {
      case AssistIntentType.describeScene: return 'describe_scene';
      case AssistIntentType.answerQuestionAboutScene: return 'answer_question_about_scene';
      case AssistIntentType.continueConversation: return 'continue_conversation';
      case AssistIntentType.repeatLastResponse: return 'repeat_last_response';
      case AssistIntentType.stopSpeaking: return 'stop_speaking';
      case AssistIntentType.cancelAssist: return 'cancel_assist';
    }
  }
}
