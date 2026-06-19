import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../domain/manager/device_manager.dart';
import '../domain/manager/device_registry.dart';
import '../domain/messaging/event_bus.dart';
import '../domain/messaging/event_arbitrator.dart';
import '../domain/messaging/event_router.dart';
import '../infrastructure/manager/adapter_factory.dart';
import '../infrastructure/manager/backoff_strategy.dart';
import '../infrastructure/manager/device_manager_impl.dart';
import '../infrastructure/manager/shared_prefs_device_registry.dart';
import '../domain/services/ble_permission_service.dart';
import '../infrastructure/observability/hardware_logger.dart';
import '../infrastructure/services/ble_permission_service_impl.dart';
import '../infrastructure/services/debug_goggle_service.dart';
import '../infrastructure/transports/device_discovery_server.dart';
import '../infrastructure/services/ble_discovery_service.dart';
import '../infrastructure/services/udp_discovery_service.dart';

// ──────────────────────────────────────────────────────────────
// External Dependencies (must be overridden in ProviderScope)
// ──────────────────────────────────────────────────────────────

final sharedPreferencesProvider = Provider<SharedPreferences>((ref) {
  throw UnimplementedError('sharedPreferencesProvider must be overridden');
});

final dioProvider = Provider<Dio>((ref) {
  return Dio();
});

// ──────────────────────────────────────────────────────────────
// Infrastructure
// ──────────────────────────────────────────────────────────────

final deviceRegistryProvider = Provider<DeviceRegistry>((ref) {
  final prefs = ref.watch(sharedPreferencesProvider);
  return SharedPreferencesDeviceRegistry(prefs);
});

final backoffStrategyProvider = Provider<BackoffStrategy>((ref) {
  return BackoffStrategy();
});

final hardwareLoggerProvider = Provider<HardwareLogger>((ref) {
  final logger = HardwareLogger();
  ref.onDispose(() => logger.dispose());
  return logger;
});

final deviceDiscoveryServerProvider = Provider<DeviceDiscoveryServer>((ref) {
  final server = DeviceDiscoveryServer();
  // Server is started internally by DeviceManager when it initializes
  ref.onDispose(() => server.stop());
  return server;
});

final blePermissionServiceProvider = Provider<BlePermissionService>((ref) {
  return BlePermissionServiceImpl();
});

final bleDiscoveryServiceProvider = Provider<BleDiscoveryService>((ref) {
  return BleDiscoveryService('1b050001-c852-4752-b883-fa4c0342ab01');
});

final udpDiscoveryServiceProvider = Provider<UdpDiscoveryService>((ref) {
  final service = UdpDiscoveryService(port: 8888);
  ref.onDispose(() => service.stop());
  return service;
});

// ──────────────────────────────────────────────────────────────
// Event Pipeline: EventBus → EventRouter (with Arbitration)
// ──────────────────────────────────────────────────────────────

final hardwareEventBusProvider = Provider<HardwareEventBus>((ref) {
  final bus = HardwareEventBusImpl();
  ref.onDispose(() => bus.dispose());
  return bus;
});

final eventArbitratorProvider = Provider<EventArbitrator>((ref) {
  return const EventArbitrator();
});

final eventRouterProvider = Provider<EventRouter>((ref) {
  final bus = ref.watch(hardwareEventBusProvider);
  final arbitrator = ref.watch(eventArbitratorProvider);
  final router = EventRouter(bus, arbitrator);
  ref.onDispose(() => router.dispose());
  return router;
});

final adapterFactoryProvider = Provider<AdapterFactory>((ref) {
  final dio = ref.watch(dioProvider);
  final eventBus = ref.watch(hardwareEventBusProvider);
  final backoff = ref.watch(backoffStrategyProvider);
  return AdapterFactory(dio, eventBus, backoff);
});

final debugGoggleServiceProvider = Provider<DebugGoggleService>((ref) {
  final dio = ref.watch(dioProvider);
  final eventBus = ref.watch(hardwareEventBusProvider);
  final service = DebugGoggleService(dio, eventBus);
  ref.onDispose(service.dispose);
  return service;
});

// ──────────────────────────────────────────────────────────────
// Device Manager (lifecycle only — does NOT route events)
// ──────────────────────────────────────────────────────────────

final deviceManagerProvider = Provider<DeviceManager>((ref) {
  final registry = ref.watch(deviceRegistryProvider);
  final logger = ref.watch(hardwareLoggerProvider);
  final eventBus = ref.watch(hardwareEventBusProvider);
  final adapterFactory = ref.watch(adapterFactoryProvider);
  final discoveryServer = ref.watch(deviceDiscoveryServerProvider);
  final bleDiscoveryService = ref.watch(bleDiscoveryServiceProvider);
  final udpDiscoveryService = ref.watch(udpDiscoveryServiceProvider);
  
  final manager = DeviceManagerImpl(
    registry, 
    logger, 
    eventBus,
    adapterFactory,
    discoveryServer,
    bleDiscoveryService,
    udpDiscoveryService,
  );
  ref.onDispose(() => manager.dispose());
  return manager;
});
