import 'dart:io';
import 'package:image_picker/image_picker.dart';
import '../domain/ports/image_capture_port.dart';

/// Implements ImageCapturePort using the image_picker package.
/// DEMO PATCH: Auto-captures without user interaction
class ImagePickerAdapter implements ImageCapturePort {
  ImagePickerAdapter({ImagePicker? picker}) : _picker = picker ?? ImagePicker();

  final ImagePicker _picker;

  @override
  Future<File?> captureImage() async {
    try {
      // DEMO: Use pickImage with camera source - it opens camera
      // User presses shutter button, then image is captured
      final XFile? image = await _picker.pickImage(
        source: ImageSource.camera,
        preferredCameraDevice: CameraDevice.rear,
        imageQuality: 80, // Compress slightly for faster upload
      );

      if (image == null) return null;
      return File(image.path);
    } catch (e) {
      // Return null on any error (permission denied, user cancelled, etc)
      return null;
    }
  }
}
