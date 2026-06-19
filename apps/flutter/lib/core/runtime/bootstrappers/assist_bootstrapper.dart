import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'runtime_bootstrapper.dart';
import '../../../features/assist/providers/assist_providers.dart';

/// Bootstraps the Assist pipeline and triggers background readiness.
class AssistBootstrapper extends RuntimeBootstrapper {
  const AssistBootstrapper();

  @override
  Future<void> boot(ProviderContainer container) async {
    // Ensures Assist pipeline and controller are created and ready
    // to observe hardware triggers independently of the UI.
    container.read(assistControllerProvider);
    container.read(assistIngressServiceProvider);
  }
}
