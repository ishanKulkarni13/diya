import 'dart:io';

import 'package:flutter/foundation.dart';
import 'package:flutter_dotenv/flutter_dotenv.dart';
import 'package:google_generative_ai/google_generative_ai.dart';

import '../domain/models/assist_response.dart';

/// HOTFIX: Direct Gemini API call from Flutter
/// This bypasses the backend due to Docker networking issues
class GeminiDirect {
  // Read API key from .env file (never commit the actual key!)
  static String get _apiKey {
    final key = dotenv.env['GEMINI_API_KEY'];
    if (key == null || key.trim().isEmpty || key == 'your-api-key-here') {
      throw StateError(
        'GEMINI_API_KEY not found in .env file. '
        'Please add your API key to apps/flutter/.env'
      );
    }
    return key.trim();
  }
  
  static const String _model = 'gemini-2.0-flash-exp';

  /// Call Gemini directly with an image
  static Future<AssistResponse> analyzeImage({
    required File imageFile,
    required String sessionId,
  }) async {
    try {
      debugPrint('[GeminiDirect] Starting analysis...');
      
      // Read image bytes
      final imageBytes = await imageFile.readAsBytes();
      debugPrint('[GeminiDirect] Image size: ${imageBytes.length} bytes');

      // Create Gemini client
      final model = GenerativeModel(
        model: _model,
        apiKey: _apiKey,
      );

      // Create prompt
      const prompt = '''
You are an assistive AI for a visually impaired user.
Analyze this image and provide a response that prioritizes:
1. Immediate hazards (obstacles, stairs, vehicles, wet floors)
2. Navigation information (doorways, paths, intersections)
3. Important objects the user should know about
4. Any visible text (signs, labels, screens)
5. Brief general scene description

Keep the response to 1-3 concise sentences.
Focus on what matters for safe mobility and awareness.
Do not describe colors or aesthetics unless safety-relevant.

Respond in JSON format:
{
  "spoken_text": "concise description for TTS",
  "display_text": "short summary",
  "hazards": ["list", "of", "hazards"],
  "detected_objects": ["list", "of", "objects"],
  "confidence": 0.85
}
''';

      // Call Gemini
      final content = [
        Content.multi([
          TextPart(prompt),
          DataPart('image/jpeg', imageBytes),
        ])
      ];

      debugPrint('[GeminiDirect] Calling Gemini API...');
      final response = await model.generateContent(content);
      
      final text = response.text ?? '';
      debugPrint('[GeminiDirect] Response: ${text.substring(0, text.length > 100 ? 100 : text.length)}...');

      // Parse JSON response
      // For demo, just return a simple response
      return AssistResponse(
        turnId: DateTime.now().millisecondsSinceEpoch.toString(),
        sessionId: sessionId,
        status: 'completed',
        spokenText: text,
        displayText: text.length > 100 ? text.substring(0, 100) : text,
        confidence: 0.85,
        followUpMode: 'available',
        hazards: const [],
        detectedObjects: const [],
        providerName: 'gemini-direct',
        modelName: _model,
        latencyMs: 1000,
      );
    } catch (e) {
      debugPrint('[GeminiDirect] Error: $e');
      rethrow;
    }
  }
}
