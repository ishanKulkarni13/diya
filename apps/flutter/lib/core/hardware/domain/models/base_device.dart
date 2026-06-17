import 'connection_state.dart';
import '../capabilities/device_capability.dart';

abstract class BaseDevice {
  String get id;
  String get name;
  HardwareConnectionState get state;
  Stream<HardwareConnectionState> get stateStream;

  List<DeviceCapability> get capabilities;

  T? getCapability<T extends DeviceCapability>() {
    for (final cap in capabilities) {
      if (cap.type == T || cap is T) {
        return cap as T;
      }
    }
    return null;
  }

  Future<void> connect(String address);
  Future<void> disconnect();
}
