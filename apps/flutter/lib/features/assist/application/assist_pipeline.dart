import 'dart:io';

import 'package:flutter/foundation.dart';

import '../../../core/errors/app_error.dart';
import '../domain/models/assist_intent.dart';
import '../domain/models/assist_response.dart';
import '../domain/models/assist_state.dart';
import '../domain/models/assist_trigger.dart';
import '../domain/ports/image_capture_port.dart';
import '../domain/ports/speech_output_port.dart';
import '../infrastructure/assist_api.dart';
import 'assist_policy_engine.dart';

/// The single application service that runs the normalized intent through the pipeline.
class AssistPipeline {
  AssistPipeline({
    required ImageCapturePort imageCapturePort,
    required SpeechOutputPort speechOutputPort,
    required AssistApi assistApi,
    required AssistPolicyEngine policyEngine,
  })  : _imageCapturePort = imageCapturePort,
        _speechOutputPort = speechOutputPort,
        _assistApi = assistApi,
        _policyEngine = policyEngine;

  final ImageCapturePort _imageCapturePort;
  final SpeechOutputPort _speechOutputPort;
  final AssistApi _assistApi;
  final AssistPolicyEngine _policyEngine;

  /// Executes the full Assist turn pipeline.
  /// Returns the response or throws an AppError.
  Future<AssistResponse> executeTurn({
    required AssistTrigger trigger,
    required AssistIntent intent,
    required bool isSafetyActive,
    required Function(AssistStatus status) onProgress,
  }) async {
    // 1. Policy Preflight
    _policyEngine.validatePreflight(
      trigger: trigger,
      intent: intent,
      isSafetyActive: isSafetyActive,
    );

    // Stop any ongoing speech
    await _speechOutputPort.stop();

    // 2. Capture
    onProgress(AssistStatus.capturing);
    File? imageFile;
    try {
      imageFile = await _imageCapturePort.captureImage();
      if (imageFile == null) {
        throw AppError.assist('Image capture was cancelled.', code: 'assist.capture_cancelled');
      }
    } catch (e) {
      if (e is AppError) rethrow;
      throw AppError.assist('Failed to capture image: $e', code: 'assist.capture_failed');
    }

    // 3. Backend Analysis
    onProgress(AssistStatus.analyzing);
    AssistResponse response;
    try {
      response = await _assistApi.createTurn(
        trigger: trigger,
        intent: intent,
        imageFile: imageFile,
        // Mocking a session ID for Phase 1
        sessionId: 'session-${DateTime.now().millisecondsSinceEpoch}',
      );
    } catch (e) {
      if (e is AppError) rethrow;
      throw AppError.network('Failed to analyze image: $e', code: 'assist.network_failed');
    } finally {
      // Clean up ephemeral image file to prevent disk cache buildup
      try {
        if (await imageFile.exists()) {
          await imageFile.delete();
        }
      } catch (_) {
        // Best-effort cleanup — do not fail the pipeline
      }
    }

    debugPrint('Gemini response received');

    // 4. Speech Output
    onProgress(AssistStatus.speaking);
    try {
      await _speechOutputPort.speak(response.spokenText);
    } catch (e) {
      throw AppError.assist('Failed to speak response: $e', code: 'assist.tts_failed');
    }

    return response;
  }
}
