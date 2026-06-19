import 'dart:async';
import 'dart:convert';
import 'package:flutter/foundation.dart';
import '../../domain/models/base_device.dart';
import '../../domain/models/connection_state.dart';
import '../../domain/models/hardware_event.dart';
import '../../domain/capabilities/device_capability.dart';
import '../manager/connection_coordinator.dart';
import '../../domain/messaging/event_bus.dart';
import '../models/cane_message_dto.dart';

class _SmartCaneHapticCapability implements HapticCapability {
  final ConnectionCoordinator _coordinator;
  _SmartCaneHapticCapability(this._coordinator);

  @override
  Type get type => HapticCapability;

  @override
  Future<void> triggerHaptic(int durationMs) async {
    await _coordinator.transport.send(Uint8List.fromList([0x03, durationMs & 0xFF]));
  }
}

class SmartCaneAdapter implements BaseDevice {
  final String _id;
  final ConnectionCoordinator _coordinator;
  final HardwareEventBus _eventBus;
  
  StreamSubscription? _dataSubscription;
  
  final StreamController<HardwareEvent> _eventController = StreamController.broadcast();
  late final List<DeviceCapability> _capabilities;

  SmartCaneAdapter(this._id, this._coordinator, this._eventBus) {
    _capabilities = [_SmartCaneHapticCapability(_coordinator)];
    _dataSubscription = _coordinator.transport.incoming.listen(_handleRawData);
  }

  @override
  Future<void> connect(String address) async {
    _coordinator.connect(address);
  }

  @override
  Future<void> disconnect() async {
    _coordinator.disconnect();
  }

  Stream<HardwareEvent> get events => _eventController.stream;

  @override
  String get id => _id;

  @override
  String get name => 'Smart Cane';

  @override
  HardwareConnectionState get state => _coordinator.state;

  @override
  Stream<HardwareConnectionState> get stateStream => _coordinator.stateStream;

  @override
  List<DeviceCapability> get capabilities => _capabilities;

  @override
  T? getCapability<T extends DeviceCapability>() {
    for (final cap in capabilities) {
      if (cap.type == T || cap is T) return cap as T;
    }
    return null;
  }

  void _handleRawData(Uint8List data) {
    if (data.isEmpty) return;
    
    try {
      final str = utf8.decode(data);
      final json = jsonDecode(str);
      final dto = CaneMessageDto.fromJson(json);

      HardwareEvent? event;
      
      if (dto.type == 'button') {
        final buttonNum = dto.payload['button'];
        final pressTypeStr = dto.payload['press'];
        
        ButtonId btnId = buttonNum == 2 ? ButtonId.button2 : ButtonId.button1;
        ButtonPressType pressType = ButtonPressType.short;
        
        if (pressTypeStr == 'long') pressType = ButtonPressType.long;
        if (pressTypeStr == 'double') pressType = ButtonPressType.double;
        if (pressTypeStr == 'triple') pressType = ButtonPressType.triple;
        
        event = ButtonPressEvent(
          deviceId: id,
          buttonId: btnId,
          pressType: pressType,
          priority: pressType == ButtonPressType.long ? 0 : 1,
          trusted: true,
        );
        debugPrint('ButtonPressEvent emitted: ${btnId.name} ${pressType.name}');
      }
      
      if (event != null) {
        _eventController.add(event);
        _eventBus.publish(event);
      }
    } catch (e) {
      // Safely ignore malformed or unknown JSON payloads as per protocol v1
    }
  }

  void dispose() {
    _dataSubscription?.cancel();
    _eventController.close();
    _coordinator.dispose();
  }
}
