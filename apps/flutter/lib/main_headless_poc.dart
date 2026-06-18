import 'package:flutter/widgets.dart';
import 'package:flutter_dotenv/flutter_dotenv.dart';

import 'core/config/app_config.dart';
import 'core/runtime/diya_runtime.dart';

/// A headless entrypoint for Diya to prove it can run purely as a background
/// runtime without `MaterialApp`, `runApp`, or any UI layer routing.
void main() async {
  // Ensure basic platform channel bindings are available for plugins 
  // (e.g. shared preferences, BLE, location).
  WidgetsFlutterBinding.ensureInitialized();

  debugPrint('=== [Headless PoC] Starting Boot Sequence ===');

  try {
    await dotenv.load(fileName: '.env', isOptional: true);
  } on FileNotFoundError {
    debugPrint('No .env file found. Proceeding with defaults.');
  }

  AppConfig.validate();

  final runtime = DiyaRuntime();
  
  // This will initialize the dependency injection container, the hardware
  // adapters, the safety queue processor, and the assist pipelines.
  await runtime.boot();

  debugPrint('=== [Headless PoC] DiyaRuntime Booted Successfully ===');
  debugPrint('Running headless... Press stop to exit.');

  // Normally we would start an isolate or wait here. 
  // For the PoC, we will just keep the process alive briefly.
  await Future.delayed(const Duration(seconds: 10));

  await runtime.shutdown();
  debugPrint('=== [Headless PoC] Shutdown Complete ===');
}
