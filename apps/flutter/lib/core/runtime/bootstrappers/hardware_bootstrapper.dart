import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'runtime_bootstrapper.dart';
import '../../hardware/providers/hardware_providers.dart';
import '../../../features/safety/providers/safety_controller.dart';
import '../../../features/cane/providers/cane_providers.dart';

/// Bootstraps hardware systems and ingress services independently of the UI.
class HardwareBootstrapper extends RuntimeBootstrapper {
  const HardwareBootstrapper();

  @override
  Future<void> boot(ProviderContainer container) async {
    // Reading deviceManagerProvider initializes the hardware layer, event bus, 
    // and device discovery mechanisms.
    container.read(deviceManagerProvider);

    // Bind the hardware event bus to the safety controller.
    container.read(sosIngressServiceProvider);

    // Start obstacle ingress so telemetry is captured independently of the UI.
    container.read(obstacleIngressServiceProvider);
  }
}
