import 'dart:convert';
import 'dart:io';

import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';

import '../../../core/errors/app_error.dart';
import '../../../core/errors/app_error_mapper.dart';
import '../domain/models/assist_intent.dart';
import '../domain/models/assist_response.dart';
import '../domain/models/assist_trigger.dart';
import 'gemini_direct.dart';

/// Client for communicating with the FastAPI Assist endpoints.
class AssistApi {
  AssistApi(this._dio);

  final Dio _dio;

  /// Creates a new Assist turn by uploading the image and context to the backend.
  /// HOTFIX: Temporarily using direct Gemini call for demo
  Future<AssistResponse> createTurn({
    required AssistTrigger trigger,
    required AssistIntent intent,
    required File imageFile,
    required String sessionId,
  }) async {
    try {
      debugPrint('[AssistApi] HOTFIX: Using direct Gemini call');
      
      // HOTFIX: Call Gemini directly from Flutter
      return await GeminiDirect.analyzeImage(
        imageFile: imageFile,
        sessionId: sessionId,
      );
      
      /* ORIGINAL BACKEND CALL - Commented out for demo
      debugPrint('[AssistApi] Creating turn for session: $sessionId');
      final fileName = imageFile.path.split('/').last;

      final formData = FormData.fromMap({
        'intent_json': jsonEncode(intent.toJson()),
        'trigger_json': jsonEncode(trigger.toJson()),
        'client_context_json': jsonEncode({
          'locale': 'en-US',
          'timezone': DateTime.now().timeZoneName,
          'device_state': {
            'smart_cane_connected': false,
            'smart_goggles_connected': false,
          }
        }),
        'image_file': await MultipartFile.fromFile(
          imageFile.path,
          filename: fileName,
        ),
      });

      debugPrint('[AssistApi] Sending POST request to /assist/sessions/$sessionId/turns');
      final response = await _dio.post(
        '/assist/sessions/$sessionId/turns',
        data: formData,
        options: Options(
          headers: {
            'Idempotency-Key': trigger.idempotencyKey,
          },
        ),
      );

      debugPrint('[AssistApi] Received response: ${response.statusCode}');
      return AssistResponse.fromJson(response.data);
      */
    } catch (e) {
      debugPrint('[AssistApi] Error: $e');
      if (e is DioException) {
        throw AppErrorMapper.fromException(e, fallbackType: AppErrorType.network);
      }
      throw AppError.network('Failed to create assist turn: $e');
    }
  }
}
