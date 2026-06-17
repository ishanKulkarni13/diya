import 'package:dio/dio.dart';

import '../../domain/models/base_device.dart';
import '../../domain/messaging/event_bus.dart';
import '../adapters/smart_cane_adapter.dart';
import '../adapters/smart_goggle_adapter.dart';
import '../transports/ble_transport.dart';
import '../transports/http_transport.dart';

import '../manager/connection_coordinator.dart';
import '../manager/backoff_strategy.dart';

/// Factory responsible for instantiating the correct transport and adapter
/// pair based on a given device type. This keeps DeviceManagerImpl clean.
class AdapterFactory {
  final Dio _dio;
  final HardwareEventBus _eventBus;
  final BackoffStrategy _backoffStrategy;

  AdapterFactory(this._dio, this._eventBus, this._backoffStrategy);

  /// Creates and returns a [BaseDevice] adapter.
  /// 
  /// Throws an [Exception] if the device type is unsupported.
  BaseDevice createAdapter({
    required String deviceId,
    required String deviceType,
  }) {
    if (deviceType == 'goggle') {
      final transport = HttpTransportImpl(_dio);
      return SmartGoggleAdapter(deviceId, transport, _eventBus);
    } else if (deviceType == 'cane') {
      final transport = BleTransportImpl();
      final coordinator = ConnectionCoordinator(
        deviceId: deviceId,
        transport: transport,
        backoffStrategy: _backoffStrategy,
      );
      return SmartCaneAdapter(deviceId, coordinator, _eventBus);
    }
    
    throw Exception('Unsupported device type: $deviceType');
  }
}
