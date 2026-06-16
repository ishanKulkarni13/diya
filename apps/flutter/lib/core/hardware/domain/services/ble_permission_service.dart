abstract class BlePermissionService {
  /// Checks if all required BLE and location permissions are granted.
  Future<bool> hasPermissions();

  /// Requests the necessary permissions from the user.
  Future<bool> requestPermissions();

  /// Checks if Bluetooth adapter is enabled on the device.
  Future<bool> isBluetoothEnabled();
}
