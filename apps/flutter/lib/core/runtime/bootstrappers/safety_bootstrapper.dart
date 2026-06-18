import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'runtime_bootstrapper.dart';
import '../../../features/safety/providers/safety_controller.dart';
import '../../session/session_controller.dart';

/// Bootstraps safety systems and ensures any offline queues are processed.
class SafetyBootstrapper extends RuntimeBootstrapper {
  const SafetyBootstrapper();

  @override
  Future<void> boot(ProviderContainer container) async {
    // Ensure safety controller is created
    final safetyController = container.read(safetyControllerProvider);
    
    // Process offline queue if we have a valid session
    final sessionState = container.read(sessionControllerProvider).state;
    if (sessionState.session?.accessToken != null) {
      await safetyController.processQueue(sessionState.session!.accessToken);
    }
  }
}
