import 'dart:io';

import 'package:flutter/foundation.dart';

import '../domain/ports/image_capture_port.dart';

/// Implements CaptureSource.AUTO logic.
///
/// This adapter tries the primary capture source (goggle) first,
/// and falls back to the secondary source (phone) if primary fails.
///
/// This enables transparent capture source selection based on hardware availability.
class AutoCaptureAdapter implements ImageCapturePort {
  AutoCaptureAdapter({
    required ImageCapturePort primarySource,
    required ImageCapturePort fallbackSource,
  })  : _primarySource = primarySource,
        _fallbackSource = fallbackSource;

  final ImageCapturePort _primarySource;
  final ImageCapturePort _fallbackSource;

  @override
  Future<File?> captureImage() async {
    debugPrint('[AutoCaptureAdapter] Attempting primary capture (goggle)...');

    // Try primary source first (goggle)
    File? image;
    try {
      image = await _primarySource.captureImage();
    } catch (e) {
      debugPrint('[AutoCaptureAdapter] Primary capture threw exception: $e');
      image = null;
    }

    // If primary succeeded, return it
    if (image != null) {
      debugPrint('[AutoCaptureAdapter] Primary capture succeeded: ${image.path}');
      return image;
    }

    // Fall back to secondary source (phone)
    debugPrint('[AutoCaptureAdapter] Primary capture failed, falling back to phone...');
    try {
      image = await _fallbackSource.captureImage();
      if (image != null) {
        debugPrint('[AutoCaptureAdapter] Fallback capture succeeded: ${image.path}');
      } else {
        debugPrint('[AutoCaptureAdapter] Fallback capture returned null');
      }
      return image;
    } catch (e) {
      debugPrint('[AutoCaptureAdapter] Fallback capture threw exception: $e');
      return null;
    }
  }
}
