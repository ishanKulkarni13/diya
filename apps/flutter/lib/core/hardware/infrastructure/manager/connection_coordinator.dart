import 'dart:async';
import 'dart:convert';
import 'dart:typed_data';
import '../../domain/models/connection_state.dart';
import '../../domain/transports/device_transport.dart';
import 'backoff_strategy.dart';

class ConnectionCoordinator {
  final String deviceId;
  final DeviceTransport transport;
  final BackoffStrategy backoffStrategy;
  final Duration heartbeatTimeout;

  HardwareConnectionState _state = HardwareConnectionState.idle;
  final _stateController = StreamController<HardwareConnectionState>.broadcast();

  Timer? _heartbeatTimer;
  Timer? _reconnectTimer;
  int _reconnectAttempts = 0;
  StreamSubscription? _incomingSub;
  StreamSubscription? _transportStateSub;

  ConnectionCoordinator({
    required this.deviceId,
    required this.transport,
    required this.backoffStrategy,
    this.heartbeatTimeout = const Duration(seconds: 15),
  }) {
    _incomingSub = transport.incoming.listen(_onIncomingData);
    _transportStateSub = transport.state.listen(_onTransportState);
  }

  Stream<HardwareConnectionState> get stateStream => _stateController.stream;
  HardwareConnectionState get state => _state;

  void connect(String address) {
    if (_state == HardwareConnectionState.connecting || _state == HardwareConnectionState.ready) return;
    _updateState(HardwareConnectionState.connecting);
    _reconnectAttempts = 0;
    _attemptConnect(address);
  }

  void _attemptConnect(String address) {
    _reconnectTimer?.cancel();
    _reconnectTimer = null;
    transport.connect(address).catchError((_) {
      // Handled via transport state stream emitting error/disconnected
    });
  }

  void disconnect() {
    _reconnectTimer?.cancel();
    _heartbeatTimer?.cancel();
    transport.disconnect();
    _updateState(HardwareConnectionState.disconnected);
  }

  void _onTransportState(TransportState tState) {
    switch (tState) {
      case TransportState.connected:
        _reconnectAttempts = 0;
        _updateState(HardwareConnectionState.ready);
        _resetHeartbeat();
        break;
      case TransportState.disconnected:
      case TransportState.error:
        _handleDisconnectOrError();
        break;
      case TransportState.connecting:
        break;
      case TransportState.degraded:
        _updateState(HardwareConnectionState.degraded);
        break;
    }
  }

  void _onIncomingData(Uint8List data) {
    // Reset heartbeat only on valid JSON payloads from the cane
    try {
      final str = utf8.decode(data);
      final json = jsonDecode(str);
      if (json is Map && json.containsKey('t')) {
        if (_state == HardwareConnectionState.degraded || _state == HardwareConnectionState.reconnecting) {
          _updateState(HardwareConnectionState.ready);
        }
        _resetHeartbeat();
      }
    } catch (_) {
      // Ignore malformed payloads for heartbeat reset
    }
  }

  void _resetHeartbeat() {
    _heartbeatTimer?.cancel();
    _heartbeatTimer = Timer(heartbeatTimeout, _onHeartbeatTimeout);
  }

  void _onHeartbeatTimeout() {
    _updateState(HardwareConnectionState.degraded);
    _heartbeatTimer?.cancel();
    _handleDisconnectOrError();
  }

  void _handleDisconnectOrError() {
    if (_state == HardwareConnectionState.disconnected) return; // Intentional disconnect

    _updateState(HardwareConnectionState.reconnecting);
    _reconnectAttempts++;
    final delayMs = backoffStrategy.calculateDelay(_reconnectAttempts);

    _reconnectTimer?.cancel();
    _reconnectTimer = Timer(Duration(milliseconds: delayMs), () {
      _attemptConnect(deviceId); // Uses deviceId as the BLE MAC address
    });
  }

  void _updateState(HardwareConnectionState newState) {
    if (_state != newState) {
      _state = newState;
      _stateController.add(newState);
    }
  }

  void dispose() {
    _incomingSub?.cancel();
    _transportStateSub?.cancel();
    _heartbeatTimer?.cancel();
    _reconnectTimer?.cancel();
    _stateController.close();
  }
}
