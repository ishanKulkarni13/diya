import 'dart:convert';
import 'dart:typed_data';
import 'package:flutter_test/flutter_test.dart';
import 'package:diya_flutter/core/hardware/domain/models/connection_state.dart';
import 'package:diya_flutter/core/hardware/infrastructure/manager/backoff_strategy.dart';
import 'package:diya_flutter/core/hardware/infrastructure/manager/connection_coordinator.dart';
import '../../mocks/fake_ble_transport.dart';

void main() {
  late FakeBleTransport transport;
  late BackoffStrategy backoff;
  late ConnectionCoordinator coordinator;

  setUp(() {
    transport = FakeBleTransport();
    backoff = BackoffStrategy();
    coordinator = ConnectionCoordinator(
      deviceId: 'test_mac',
      transport: transport,
      backoffStrategy: backoff,
      heartbeatTimeout: const Duration(milliseconds: 100),
    );
  });

  tearDown(() {
    coordinator.dispose();
    transport.dispose();
  });

  test('Successful connection establishes ready state', () async {
    expect(coordinator.state, HardwareConnectionState.idle);
    coordinator.connect('test_mac');
    expect(coordinator.state, HardwareConnectionState.connecting);
    
    await Future.delayed(const Duration(milliseconds: 50));
    expect(coordinator.state, HardwareConnectionState.ready);
  });

  test('Heartbeat timeout triggers reconnect', () async {
    coordinator.connect('test_mac');
    await Future.delayed(const Duration(milliseconds: 50));
    expect(coordinator.state, HardwareConnectionState.ready);

    // Wait for heartbeat timeout
    await Future.delayed(const Duration(milliseconds: 150));
    
    // Should have transitioned to degraded or reconnecting
    expect(coordinator.state, isNot(HardwareConnectionState.ready));
    expect(coordinator.state, isNot(HardwareConnectionState.idle));
  });

  test('Valid JSON resets heartbeat', () async {
    coordinator.connect('test_mac');
    await Future.delayed(const Duration(milliseconds: 50));
    expect(coordinator.state, HardwareConnectionState.ready);

    // Send valid json before timeout
    await Future.delayed(const Duration(milliseconds: 80));
    final validJson = utf8.encode('{"t":"heartbeat","v":1}');
    transport.simulateIncoming(Uint8List.fromList(validJson));

    // Wait past the original 100ms timeout
    await Future.delayed(const Duration(milliseconds: 50));
    
    // State should still be ready because heartbeat was reset
    expect(coordinator.state, HardwareConnectionState.ready);
  });

  test('Malformed payload does not reset heartbeat', () async {
    coordinator.connect('test_mac');
    await Future.delayed(const Duration(milliseconds: 50));
    expect(coordinator.state, HardwareConnectionState.ready);
    
    // Send malformed json
    await Future.delayed(const Duration(milliseconds: 80));
    final malformedJson = utf8.encode('{"t":');
    transport.simulateIncoming(Uint8List.fromList(malformedJson));
    
    // Should timeout because payload was malformed
    await Future.delayed(const Duration(milliseconds: 50));
    expect(coordinator.state, isNot(HardwareConnectionState.ready));
  });

  test('Unexpected disconnect triggers reconnect', () async {
    coordinator.connect('test_mac');
    await Future.delayed(const Duration(milliseconds: 50));
    
    transport.simulateDisconnect();
    await Future.delayed(const Duration(milliseconds: 10));
    expect(coordinator.state, HardwareConnectionState.reconnecting);
  });
}
