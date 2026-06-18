import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_dotenv/flutter_dotenv.dart';

import 'app/second_eye_app.dart';
import 'core/config/app_config.dart';
import 'core/runtime/diya_runtime.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  try {
    await dotenv.load(fileName: '.env', isOptional: true);
  } on FileNotFoundError {
    // Allow local runs without a .env file.
  }

  AppConfig.validate();

  // Boot the underlying headless runtime
  final runtime = DiyaRuntime();
  await runtime.boot();
  
  runApp(
    UncontrolledProviderScope(
      container: runtime.container,
      child: const SecondEyeApp(),
    ),
  );
}
