import '../../../core/errors/app_error.dart';

enum AssistStatus {
  idle,
  capturing,
  analyzing,
  speaking,
  error,
}

/// Exposes current runtime progress to UI and speech output.
class AssistState {
  const AssistState({
    this.status = AssistStatus.idle,
    this.error,
    this.lastResponseText,
  });

  final AssistStatus status;
  final AppError? error;
  final String? lastResponseText;

  AssistState copyWith({
    AssistStatus? status,
    AppError? error,
    String? lastResponseText,
  }) {
    // If transitioning to a non-error state, we might want to clear the error.
    // We'll leave it up to the caller to pass null for error if they want to clear it,
    // but dart's copyWith doesn't easily clear nulls. 
    // Since this is a simple state object, we'll just implement a helper.
    return AssistState(
      status: status ?? this.status,
      error: status != null && status != AssistStatus.error ? null : (error ?? this.error),
      lastResponseText: lastResponseText ?? this.lastResponseText,
    );
  }

  bool get isIdle => status == AssistStatus.idle;
  bool get isCapturing => status == AssistStatus.capturing;
  bool get isAnalyzing => status == AssistStatus.analyzing;
  bool get isSpeaking => status == AssistStatus.speaking;
  bool get hasError => status == AssistStatus.error;
  bool get isBusy => isCapturing || isAnalyzing || isSpeaking;
}
