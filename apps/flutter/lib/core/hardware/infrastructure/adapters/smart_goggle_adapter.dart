import 'dart:async';
import 'dart:io';
import 'dart:typed_data';

import '../../domain/capabilities/device_capability.dart';
import '../../domain/messaging/event_bus.dart';
import '../../domain/models/base_device.dart';
import '../../domain/models/connection_state.dart';
import '../../domain/models/hardware_event.dart';
import '../../domain/transports/device_transport.dart';

class _SmartGoggleCameraCapability implements CameraCapability {
  final DeviceTransport _transport;
  final String _deviceId;
  final HardwareEventBus _eventBus;

  _SmartGoggleCameraCapability(this._transport, this._deviceId, this._eventBus);

  @override
  Type get type => CameraCapability;

  bool _isSupportedImageBytes(Uint8List bytes) {
    return bytes.length >= 2 && bytes[0] == 0xFF && bytes[1] == 0xD8;
  }

  @override
  Future<Uint8List?> capture() async {
    try {
      final bytes = await _transport.requestBytes('GET', '/capture');
      if (_isSupportedImageBytes(bytes)) {
        return bytes;
      }

      final diagPath = await _writeDiagnostic(bytes, 'capture');
      if (diagPath != null) {
        _eventBus.publish(HardwareErrorEvent(
          deviceId: _deviceId,
          errorCode: 'capture_bad_image',
          message: 'Capture returned invalid image; wrote diagnostics to $diagPath',
          priority: 1,
          trusted: true,
        ));
        return null;
      }

      _eventBus.publish(HardwareErrorEvent(
        deviceId: _deviceId,
        errorCode: 'capture_bad_image',
        message: 'Capture returned invalid image and diagnostics write failed',
        priority: 1,
        trusted: true,
      ));
      return null;
    } catch (e) {
      _eventBus.publish(HardwareErrorEvent(
        deviceId: _deviceId,
        errorCode: 'capture_failed',
        message: '$e',
        priority: 1,
        trusted: true,
      ));
      return null;
    }
  }

  Future<String?> _writeDiagnostic(Uint8List bytes, String prefix) async {
    final candidates = <String>[];
    try {
      candidates.add(Directory.systemTemp.path);
    } catch (_) {}
    candidates.addAll([
      '/sdcard/Download',
      '/storage/emulated/0/Download',
    ]);

    for (final base in candidates) {
      try {
        final dir = Directory(base);
        if (!await dir.exists()) {
          try {
            await dir.create(recursive: true);
          } catch (_) {
            continue;
          }
        }
        final file = File('${dir.path}/${prefix}_${_deviceId}_${DateTime.now().microsecondsSinceEpoch}.bin');
        await file.writeAsBytes(bytes, flush: true);
        return file.path;
      } catch (_) {
        continue;
      }
    }
    return null;
  }
}

class _SmartGoggleBatteryCapability implements BatteryCapability {
  final DeviceTransport _transport;
  final String _deviceId;
  final HardwareEventBus _eventBus;

  _SmartGoggleBatteryCapability(this._transport, this._deviceId, this._eventBus);

  @override
  Type get type => BatteryCapability;

  @override
  Future<int?> pullBatteryLevel() async {
    try {
      final response = await _transport.requestJson('GET', '/state');
      final battery = response['battery_level'];
      if (battery is! num) return null;
      final normalized = battery.toInt().clamp(0, 100);
      _eventBus.publish(TelemetryEvent(
        deviceId: _deviceId,
        batteryLevel: normalized,
        status: 'battery_pull',
        priority: 3,
        trusted: true,
      ));
      return normalized;
    } catch (e) {
      _eventBus.publish(HardwareErrorEvent(
        deviceId: _deviceId,
        errorCode: 'battery_pull_failed',
        message: '$e',
        priority: 2,
        trusted: true,
      ));
      return null;
    }
  }
}

class SmartGoggleAdapter implements BaseDevice {
  final String _id;
  final DeviceTransport _transport;
  final HardwareEventBus _eventBus;

  HardwareConnectionState _state = HardwareConnectionState.idle;
  final StreamController<HardwareConnectionState> _stateController = StreamController.broadcast();
  late final List<DeviceCapability> _capabilities;

  StreamSubscription? _stateSubscription;

  SmartGoggleAdapter(this._id, this._transport, this._eventBus) {
    _capabilities = [
      _SmartGoggleCameraCapability(_transport, _id, _eventBus),
      _SmartGoggleBatteryCapability(_transport, _id, _eventBus),
    ];

    _stateSubscription = _transport.state.listen((transportState) {
      if (transportState == TransportState.connected) {
        _state = HardwareConnectionState.ready;
      } else if (transportState == TransportState.disconnected) {
        _state = HardwareConnectionState.disconnected;
      } else if (transportState == TransportState.error) {
        _state = HardwareConnectionState.failed;
      }
      _stateController.add(_state);
    });
  }

  @override
  Future<void> connect(String address) async {
    await _transport.connect(address);
  }

  @override
  Future<void> disconnect() async {
    await _transport.disconnect();
  }

  @override
  String get id => _id;

  @override
  String get name => 'Smart Goggle';

  @override
  HardwareConnectionState get state => _state;

  @override
  Stream<HardwareConnectionState> get stateStream => _stateController.stream;

  @override
  List<DeviceCapability> get capabilities => _capabilities;

  @override
  T? getCapability<T extends DeviceCapability>() {
    for (final cap in capabilities) {
      if (cap.type == T || cap is T) return cap as T;
    }
    return null;
  }

  void dispose() {
    _stateSubscription?.cancel();
    _stateController.close();
  }
}
