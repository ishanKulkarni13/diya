import 'dart:convert';
import 'dart:io';

import 'package:flutter/foundation.dart';
import 'package:google_generative_ai/google_generative_ai.dart';

import '../domain/models/assist_response.dart';
import 'api_keys.dart';

/// HOTFIX: Direct Gemini API call from Flutter
/// This bypasses the backend due to Docker networking issues
class GeminiDirect {
  // Read API key from api_keys.dart (gitignored)
  static String get _apiKey => ApiKeys.geminiApiKey;
  
  static const String _model = 'gemini-3.5-flash'; // dont change this

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

      // Parse JSON response to extract structured data
      String spokenText = 'Unable to analyze the image.';
      String displayText = 'Analysis failed';
      List<String> hazards = [];
      List<String> detectedObjects = [];
      double confidence = 0.0;

      try {
        // Clean up the response (remove markdown code blocks if present)
        String cleanedText = text.trim();
        if (cleanedText.startsWith('```json')) {
          cleanedText = cleanedText.substring(7);
        }
        if (cleanedText.startsWith('```')) {
          cleanedText = cleanedText.substring(3);
        }
        if (cleanedText.endsWith('```')) {
          cleanedText = cleanedText.substring(0, cleanedText.length - 3);
        }
        cleanedText = cleanedText.trim();

        // Parse the JSON
        final jsonResponse = jsonDecode(cleanedText) as Map<String, dynamic>;
        
        spokenText = jsonResponse['spoken_text'] as String? ?? spokenText;
        displayText = jsonResponse['display_text'] as String? ?? displayText;
        confidence = (jsonResponse['confidence'] as num?)?.toDouble() ?? 0.85;
        
        if (jsonResponse['hazards'] is List) {
          hazards = (jsonResponse['hazards'] as List).map((e) => e.toString()).toList();
        }
        if (jsonResponse['detected_objects'] is List) {
          detectedObjects = (jsonResponse['detected_objects'] as List).map((e) => e.toString()).toList();
        }

        debugPrint('[GeminiDirect] Parsed - Spoken: ${spokenText.substring(0, spokenText.length > 50 ? 50 : spokenText.length)}...');
      } catch (parseError) {
        debugPrint('[GeminiDirect] JSON parse failed: $parseError');
        // Fallback: use raw text if JSON parsing fails
        spokenText = text.length > 200 ? text.substring(0, 200) : text;
        displayText = text.length > 100 ? text.substring(0, 100) : text;
      }

      // Return structured response
      return AssistResponse(
        turnId: DateTime.now().millisecondsSinceEpoch.toString(),
        sessionId: sessionId,
        status: 'completed',
        spokenText: spokenText,
        displayText: displayText,
        confidence: confidence,
        followUpMode: 'available',
        hazards: hazards,
        detectedObjects: detectedObjects,
        providerName: 'gemini-direct',
        modelName: _model,
        latencyMs: 1000,
      );
    } on GenerativeAIException catch (e) {
      // Handle 503 high demand error with user-friendly message
      if (e.message.contains('503') || e.message.contains('high demand')) {
        debugPrint('[GeminiDirect] High demand error: $e');
        return AssistResponse(
          turnId: DateTime.now().millisecondsSinceEpoch.toString(),
          sessionId: sessionId,
          status: 'completed',
          spokenText: 'Our AI service is currently experiencing high demand. Please try again in a moment.',
          displayText: 'High demand - please retry',
          confidence: 0.0,
          followUpMode: 'available',
          hazards: const [],
          detectedObjects: const [],
          providerName: 'gemini-direct',
          modelName: _model,
          latencyMs: 0,
        );
      }
      debugPrint('[GeminiDirect] Error: $e');
      rethrow;
    } catch (e) {
      debugPrint('[GeminiDirect] Error: $e');
      rethrow;
    }
  }
}
