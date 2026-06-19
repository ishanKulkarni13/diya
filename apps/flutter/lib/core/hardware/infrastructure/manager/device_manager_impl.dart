import 'dart:async';
import '../../domain/manager/device_manager.dart';
import '../../domain/manager/device_registry.dart';
import '../../domain/models/base_device.dart';
import '../../domain/models/hardware_event.dart';
import '../../domain/models/known_device.dart';
import '../../domain/observability/hardware_log_event.dart';
import '../observability/hardware_logger.dart';
import '../../domain/messaging/event_bus.dart';
import '../transports/device_discovery_server.dart';
import '../services/ble_discovery_service.dart';
import '../services/udp_discovery_service.dart';
import 'adapter_factory.dart';

class DeviceManagerImpl implements DeviceManager {
  final DeviceRegistry _registry;
  final HardwareLogger _logger;
  final HardwareEventBus _eventBus;
  final AdapterFactory _adapterFactory;
  final DeviceDiscoveryServer _discoveryServer;
  final BleDiscoveryService _bleDiscoveryService;
  final UdpDiscoveryService _udpDiscoveryService;
  
  StreamSubscription? _discoverySubscription;
  StreamSubscription? _bleDiscoverySubscription;
  StreamSubscription? _udpDiscoverySubscription;
  StreamSubscription? _sensorEventSubscription;

  final Map<String, BaseDevice> _activeDevices = {};
  final Map<String, StreamSubscription> _stateSubscriptions = {};
  final StreamController<List<BaseDevice>> _devicesController = StreamController.broadcast();

  DeviceManagerImpl(
    this._registry, 
    this._logger, 
    this._eventBus,
    this._adapterFactory,
    this._discoveryServer,
    this._bleDiscoveryService,
    this._udpDiscoveryService,
  ) {
    _discoveryServer.start();
    _discoverySubscription = _discoveryServer.onDeviceRegistered.listen(_handleDiscoveryEvent);
    _sensorEventSubscription = _discoveryServer.onSensorEvent.listen(_handleSensorEvent);
  }

  Future<void> _handleDiscoveryEvent(Map<String, dynamic> data) async {
    final deviceId = data['device_id'] as String?;
    final deviceTypeStr = data['device_type'] as String?;
    final sourceIp = data['source_ip'] as String?;
    final advertisedPort = data['port'] as int?;
    final deviceName = data['device_name'] as String?;

    if (deviceId == null || deviceTypeStr == null) return;

    final type = deviceTypeStr == 'goggle' ? DeviceType.goggle : DeviceType.cane;
    
    final knownDevice = KnownDevice(
      deviceId: deviceId,
      deviceName: deviceName,
      deviceType: type,
      lastKnownIp: sourceIp,
      lastKnownPort: advertisedPort,
      lastSeenTimestamp: DateTime.now(),
    );

    await _registry.saveKnownDevice(knownDevice);
    _logger.log(HardwareLogEvent(type: LogType.connect, deviceId: deviceId, message: "Discovered device, attempting connection..."));
    
    _triggerConnection(deviceId);
  }

  void _handleSensorEvent(Map<String, dynamic> data) {
    final eventType = data['event_type'] as String?;
    if (eventType != 'ultrasonic') return;

    final deviceId = data['device_id'] as String?;
    if (deviceId == null || deviceId.isEmpty) return;

    final rawDistance = data['distance_cm'] ?? data['ultrasonic_cm'];
    final distanceCm = rawDistance is num ? rawDistance.toDouble() : null;
    if (distanceCm == null) return;

    final detected = (data['detected'] as bool?) ?? true;

    _eventBus.publish(UltrasonicDetectionEvent(
      deviceId: deviceId,
      distanceCm: distanceCm,
      detected: detected,
      priority: 1,
      trusted: true,
    ));
  }

  @override
  Stream<List<BaseDevice>> get devices => _devicesController.stream;

  @override
  Future<void> startScan() async {
    final knownDevices = await _registry.getKnownDevices();
    for (final device in knownDevices) {
      _logger.log(HardwareLogEvent(type: LogType.connect, deviceId: device.deviceId, message: "Restoring known device"));
      _triggerConnection(device.deviceId);
    }
    
    _bleDiscoverySubscription?.cancel();
    _bleDiscoverySubscription = _bleDiscoveryService.scan().listen(_handleDiscoveryEvent);
    
    _udpDiscoverySubscription?.cancel();
    _udpDiscoverySubscription = _udpDiscoveryService.scan().listen(_handleDiscoveryEvent);
  }

  @override
  Future<void> stopScan() async {
    _bleDiscoverySubscription?.cancel();
    _udpDiscoverySubscription?.cancel();
  }

  @override
  Future<void> disconnectDevice(String deviceId) async {
    await _registry.removeDevice(deviceId);
    final adapter = _activeDevices.remove(deviceId);
    _stateSubscriptions.remove(deviceId)?.cancel();
    adapter?.disconnect();
    _logger.log(HardwareLogEvent(type: LogType.disconnect, deviceId: deviceId, message: "Manual disconnect"));
    _emitDevices();
  }

  @override
  Future<void> retryConnection(String deviceId) async {
    _triggerConnection(deviceId);
  }

  Future<void> _triggerConnection(String deviceId) async {
    if (_activeDevices.containsKey(deviceId)) {
       final allKnown = await _registry.getKnownDevices();
       final knownDevice = allKnown.firstWhere((d) => d.deviceId == deviceId);
       final address = knownDevice.deviceType == DeviceType.goggle ? _buildGoggleAddress(knownDevice) : knownDevice.deviceId;
       _activeDevices[deviceId]?.connect(address);
       return;
    }

    try {
      final allKnown = await _registry.getKnownDevices();
      final knownDevice = allKnown.where((d) => d.deviceId == deviceId).firstOrNull;
      
      if (knownDevice == null) {
        throw Exception("Device $deviceId not found in registry");
      }

      final adapter = _adapterFactory.createAdapter(
        deviceId: knownDevice.deviceId,
        deviceType: knownDevice.deviceType.name,
      );

      _activeDevices[deviceId] = adapter;
      _stateSubscriptions[deviceId] = adapter.stateStream.listen((state) {
         _emitDevices();
      });

      final address = knownDevice.deviceType == DeviceType.goggle
        ? _buildGoggleAddress(knownDevice)
        : knownDevice.deviceId;

      await adapter.connect(address);
      _emitDevices();
    } catch (e) {
      _logger.log(HardwareLogEvent(type: LogType.error, deviceId: deviceId, message: "Connect failed: $e"));
      _emitDevices();
    }
  }

  void _emitDevices() {
    _devicesController.add(_activeDevices.values.toList());
  }

  String _buildGoggleAddress(KnownDevice device) {
    final host = device.lastKnownIp ?? '192.168.43.1';
    final port = device.lastKnownPort ?? 80;
    return '$host:$port';
  }
  
  void dispose() {
    _discoverySubscription?.cancel();
    _sensorEventSubscription?.cancel();
    _bleDiscoverySubscription?.cancel();
    _udpDiscoverySubscription?.cancel();
    for (final sub in _stateSubscriptions.values) {
      sub.cancel();
    }
    _stateSubscriptions.clear();
    _devicesController.close();
  }
}
