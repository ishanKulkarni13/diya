/// Abstract port for speaking text aloud.
abstract class SpeechOutputPort {
  /// Speaks the provided text.
  Future<void> speak(String text);

  /// Stops any ongoing speech.
  Future<void> stop();
}
