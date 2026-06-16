import 'dart:async';
import 'dart:typed_data';
import 'package:flutter_blue_plus/flutter_blue_plus.dart';
import '../../domain/transports/device_transport.dart';

/// GATT Contract:
/// - Service UUID: 0000ffe0-0000-1000-8000-00805f9b34fb
/// - RX/TX Characteristic UUID: 0000ffe1-0000-1000-8000-00805f9b34fb
/// - MTU Expectations: MTU request of 512 is attempted upon connection.
/// - Notification Requirements: Client must subscribe to characteristic notifications.
class BleTransportImpl implements DeviceTransport {
  final _stateController = StreamController<TransportState>.broadcast();
  final _incomingController = StreamController<Uint8List>.broadcast();

  TransportState _currentState = TransportState.disconnected;
  BluetoothDevice? _device;
  BluetoothCharacteristic? _rxTxCharacteristic;
  StreamSubscription? _connectionSub;
  StreamSubscription? _characteristicSub;

  static const String serviceUuid = "0000ffe0-0000-1000-8000-00805f9b34fb";
  static const String charUuid = "0000ffe1-0000-1000-8000-00805f9b34fb";

  @override
  Stream<TransportState> get state => _stateController.stream;

  @override
  Stream<Uint8List> get incoming => _incomingController.stream;

  /// Scans for BLE devices that match the Smart Cane's expected profile.
  Stream<ScanResult> scanForDevices({Duration timeout = const Duration(seconds: 10)}) {
    FlutterBluePlus.startScan(
      withServices: [Guid(serviceUuid)],
      timeout: timeout,
    );
    return FlutterBluePlus.scanResults.expand((results) => results);
  }

  @override
  Future<void> connect(String address) async {
    if (_currentState == TransportState.connecting || _currentState == TransportState.connected) {
      return;
    }
    _updateState(TransportState.connecting);

    try {
      _device = BluetoothDevice.fromId(address);

      _connectionSub?.cancel();
      _connectionSub = _device!.connectionState.listen((BluetoothConnectionState state) {
        if (state == BluetoothConnectionState.disconnected) {
          _cleanup();
          _updateState(TransportState.disconnected);
        }
      });

      await _device!.connect(timeout: const Duration(seconds: 10));

      try {
        await _device!.requestMtu(512);
      } catch (_) {
        // MTU request might not be supported on all devices, proceed anyway
      }

      final services = await _device!.discoverServices();
      BluetoothService? targetService;
      for (var s in services) {
        if (s.uuid.toString() == serviceUuid) {
          targetService = s;
          break;
        }
      }

      if (targetService == null) {
        throw Exception('Required GATT Service $serviceUuid not found.');
      }

      for (var c in targetService.characteristics) {
        if (c.uuid.toString() == charUuid) {
          _rxTxCharacteristic = c;
          break;
        }
      }

      if (_rxTxCharacteristic == null) {
        throw Exception('Required GATT Characteristic $charUuid not found.');
      }

      await _rxTxCharacteristic!.setNotifyValue(true);
      _characteristicSub?.cancel();
      _characteristicSub = _rxTxCharacteristic!.lastValueStream.listen((value) {
        if (value.isNotEmpty) {
          _incomingController.add(Uint8List.fromList(value));
        }
      });

      _updateState(TransportState.connected);
    } catch (e) {
      _cleanup();
      _updateState(TransportState.error);
      rethrow;
    }
  }

  @override
  Future<void> disconnect() async {
    await _device?.disconnect();
    _cleanup();
    _updateState(TransportState.disconnected);
  }

  @override
  Future<void> send(Uint8List data) async {
    if (_currentState != TransportState.connected || _rxTxCharacteristic == null) {
      throw Exception('Cannot send data while disconnected');
    }
    await _rxTxCharacteristic!.write(data, withoutResponse: true);
  }

  @override
  Future<Map<String, dynamic>> requestJson(
    String method,
    String path, {
    Map<String, dynamic>? body,
    Duration? timeout,
  }) {
    throw UnsupportedError('requestJson is not supported for BLE transport');
  }

  @override
  Future<Uint8List> requestBytes(
    String method,
    String path, {
    Map<String, dynamic>? body,
    Duration? timeout,
    int? maxResponseBytes,
  }) {
    throw UnsupportedError('requestBytes is not supported for BLE transport');
  }

  void _cleanup() {
    _characteristicSub?.cancel();
    _characteristicSub = null;
    _connectionSub?.cancel();
    _connectionSub = null;
    _rxTxCharacteristic = null;
  }

  void _updateState(TransportState newState) {
    if (_currentState != newState) {
      _currentState = newState;
      _stateController.add(newState);
    }
  }

  void dispose() {
    _cleanup();
    _stateController.close();
    _incomingController.close();
  }
}
