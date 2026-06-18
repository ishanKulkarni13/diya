import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'runtime_bootstrapper.dart';
import '../../hardware/providers/hardware_providers.dart';
import '../../../features/safety/providers/safety_controller.dart';

/// Bootstraps hardware systems and ingress services independently of the UI.
class HardwareBootstrapper extends RuntimeBootstrapper {
  const HardwareBootstrapper();

  @override
  Future<void> boot(ProviderContainer container) async {
    // Reading deviceManagerProvider initializes the hardware layer, event bus, 
    // and device discovery mechanisms.
    container.read(deviceManagerProvider);

    // Reading sosIngressServiceProvider binds the hardware event bus to the 
    // safety controller. This used to happen in the UI (SecondEyeApp).
    container.read(sosIngressServiceProvider);
  }
}
