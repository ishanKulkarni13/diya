import 'package:flutter_tts/flutter_tts.dart';
import 'package:flutter/foundation.dart';
import '../domain/ports/speech_output_port.dart';

/// Implements SpeechOutputPort using the flutter_tts package.
class FlutterTtsAdapter implements SpeechOutputPort {
  FlutterTtsAdapter({FlutterTts? tts}) : _tts = tts ?? FlutterTts() {
    _initTts();
  }

  final FlutterTts _tts;

  Future<void> _initTts() async {
    await _tts.setLanguage("en-US");
    await _tts.setSpeechRate(0.5);
    await _tts.setVolume(1.0);
    await _tts.setPitch(1.0);
  }

  @override
  Future<void> speak(String text) async {
    debugPrint('TTS speaking: $text');
    await _tts.speak(text);
  }

  @override
  Future<void> stop() async {
    await _tts.stop();
  }
}
