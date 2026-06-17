import 'dart:async';
import 'dart:typed_data';
import 'package:diya_flutter/core/hardware/domain/transports/device_transport.dart';

class FakeBleTransport implements DeviceTransport {
  final _stateController = StreamController<TransportState>.broadcast();
  final _incomingController = StreamController<Uint8List>.broadcast();

  TransportState _state = TransportState.disconnected;

  @override
  Stream<TransportState> get state => _stateController.stream;

  @override
  Stream<Uint8List> get incoming => _incomingController.stream;

  bool connectShouldFail = false;

  @override
  Future<void> connect(String address) async {
    _updateState(TransportState.connecting);
    await Future.delayed(const Duration(milliseconds: 10));
    if (connectShouldFail) {
      _updateState(TransportState.error);
      throw Exception('Fake connection failure');
    }
    _updateState(TransportState.connected);
  }

  @override
  Future<void> disconnect() async {
    _updateState(TransportState.disconnected);
  }

  @override
  Future<void> send(Uint8List data) async {
    if (_state != TransportState.connected) {
      throw Exception('Cannot send data while disconnected');
    }
  }

  void simulateIncoming(Uint8List data) {
    _incomingController.add(data);
  }

  void simulateDisconnect() {
    _updateState(TransportState.disconnected);
  }

  @override
  Future<Map<String, dynamic>> requestJson(String method, String path, {Map<String, dynamic>? body, Duration? timeout}) {
    throw UnimplementedError();
  }

  @override
  Future<Uint8List> requestBytes(String method, String path, {Map<String, dynamic>? body, Duration? timeout, int? maxResponseBytes}) {
    throw UnimplementedError();
  }

  void _updateState(TransportState newState) {
    _state = newState;
    _stateController.add(newState);
  }

  void dispose() {
    _stateController.close();
    _incomingController.close();
  }
}
