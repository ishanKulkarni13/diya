import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Base class for all components that initialize long-lived runtime services.
abstract class RuntimeBootstrapper {
  const RuntimeBootstrapper();

  /// Execute the bootstrap logic using the provided [ProviderContainer].
  Future<void> boot(ProviderContainer container);
}
