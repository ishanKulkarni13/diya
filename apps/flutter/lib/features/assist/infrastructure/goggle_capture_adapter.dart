import 'dart:io';

import 'package:flutter/foundation.dart';

import '../../../core/hardware/domain/capabilities/device_capability.dart';
import '../../../core/hardware/domain/manager/device_manager.dart';
import '../../../core/hardware/domain/models/base_device.dart';
import '../../../core/hardware/domain/models/connection_state.dart';
import '../domain/ports/image_capture_port.dart';

/// Implements ImageCapturePort by capturing from a connected Smart Goggle.
///
/// This adapter queries the DeviceManager for an active goggle in "ready" state,
/// retrieves its CameraCapability, captures raw JPEG bytes, and converts them
/// to a temporary File for compatibility with the existing Assist pipeline.
class GoggleCaptureAdapter implements ImageCapturePort {
  final DeviceManager _deviceManager;

  GoggleCaptureAdapter({required DeviceManager deviceManager})
      : _deviceManager = deviceManager;

  @override
  Future<File?> captureImage() async {
    debugPrint('[GoggleCaptureAdapter] Starting goggle capture...');

    // Get current list of devices
    final devices = await _deviceManager.devices.first;
    debugPrint('[GoggleCaptureAdapter] Found ${devices.length} devices');

    // Find first goggle device in ready state
    BaseDevice? goggle;
    for (final device in devices) {
      debugPrint('[GoggleCaptureAdapter] Checking device: ${device.name} (${device.id}) - state: ${device.state}');
      if (device.name == 'Smart Goggle' && device.state == HardwareConnectionState.ready) {
        goggle = device;
        break;
      }
    }

    if (goggle == null) {
      debugPrint('[GoggleCaptureAdapter] No ready goggle found');
      return null;
    }

    debugPrint('[GoggleCaptureAdapter] Using goggle: ${goggle.id}');

    // Get camera capability
    final camera = goggle.getCapability<CameraCapability>();
    if (camera == null) {
      debugPrint('[GoggleCaptureAdapter] Goggle has no camera capability');
      return null;
    }

    // Capture image bytes
    debugPrint('[GoggleCaptureAdapter] Calling camera.capture()...');
    final Uint8List? bytes = await camera.capture();
    if (bytes == null) {
      debugPrint('[GoggleCaptureAdapter] Camera capture returned null');
      return null;
    }

    debugPrint('[GoggleCaptureAdapter] Captured ${bytes.length} bytes');

    // Write to temporary file
    try {
      final tempDir = Directory.systemTemp;
      final timestamp = DateTime.now().millisecondsSinceEpoch;
      final file = File('${tempDir.path}/goggle_capture_$timestamp.jpg');
      await file.writeAsBytes(bytes, flush: true);
      debugPrint('[GoggleCaptureAdapter] Wrote temp file: ${file.path}');
      return file;
    } catch (e) {
      debugPrint('[GoggleCaptureAdapter] Failed to write temp file: $e');
      return null;
    }
  }
}
