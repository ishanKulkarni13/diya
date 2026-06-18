import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'bootstrappers/assist_bootstrapper.dart';
import 'bootstrappers/hardware_bootstrapper.dart';
import 'bootstrappers/safety_bootstrapper.dart';
import '../hardware/providers/hardware_providers.dart';

/// The core headless runtime for the Diya Assistant.
/// It owns the dependency injection container and manages the lifecycle 
/// of long-lived background services (hardware, safety, assist) independently of the UI.
class DiyaRuntime {
  ProviderContainer? _container;
  bool _isBooted = false;

  /// Returns the underlying provider container. 
  /// Throws if the runtime has not been booted.
  ProviderContainer get container {
    if (!_isBooted || _container == null) {
      throw StateError('DiyaRuntime has not been booted yet.');
    }
    return _container!;
  }

  bool get isBooted => _isBooted;

  /// Initializes the runtime environment and all headless subsystems.
  Future<void> boot() async {
    if (_isBooted) return;

    // 1. Initialize core system dependencies
    final sharedPrefs = await SharedPreferences.getInstance();

    // 2. Create the standalone provider container
    _container = ProviderContainer(
      overrides: [
        sharedPreferencesProvider.overrideWithValue(sharedPrefs),
      ],
    );

    // 3. Execute domain bootstrappers
    await const HardwareBootstrapper().boot(_container!);
    await const SafetyBootstrapper().boot(_container!);
    await const AssistBootstrapper().boot(_container!);

    _isBooted = true;
  }

  /// Gracefully shuts down the runtime and disposes all services.
  Future<void> shutdown() async {
    if (!_isBooted) return;
    
    _container?.dispose();
    _container = null;
    _isBooted = false;
  }
}
