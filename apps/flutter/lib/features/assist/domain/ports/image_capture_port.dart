import 'dart:io';

/// Abstract port for capturing images for Assist analysis.
abstract class ImageCapturePort {
  /// Captures an image and returns the file.
  /// Throws an exception if capture fails or is denied.
  Future<File?> captureImage();
}
