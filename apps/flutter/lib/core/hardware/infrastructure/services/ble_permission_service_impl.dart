import 'dart:io';
import 'package:flutter_blue_plus/flutter_blue_plus.dart';
import 'package:permission_handler/permission_handler.dart';

import '../../domain/services/ble_permission_service.dart';

class BlePermissionServiceImpl implements BlePermissionService {
  @override
  Future<bool> hasPermissions() async {
    if (Platform.isAndroid) {
      final scanStatus = await Permission.bluetoothScan.status;
      final connectStatus = await Permission.bluetoothConnect.status;
      final locationStatus = await Permission.locationWhenInUse.status;
      
      return scanStatus.isGranted && 
             connectStatus.isGranted && 
             locationStatus.isGranted;
    } else if (Platform.isIOS) {
      final bluetoothStatus = await Permission.bluetooth.status;
      return bluetoothStatus.isGranted;
    }
    return false;
  }

  @override
  Future<bool> requestPermissions() async {
    if (Platform.isAndroid) {
      final statuses = await [
        Permission.bluetoothScan,
        Permission.bluetoothConnect,
        Permission.locationWhenInUse,
      ].request();
      
      return statuses[Permission.bluetoothScan]!.isGranted &&
             statuses[Permission.bluetoothConnect]!.isGranted &&
             statuses[Permission.locationWhenInUse]!.isGranted;
    } else if (Platform.isIOS) {
      final status = await Permission.bluetooth.request();
      return status.isGranted;
    }
    return false;
  }

  @override
  Future<bool> isBluetoothEnabled() async {
    final state = await FlutterBluePlus.adapterState.first;
    return state == BluetoothAdapterState.on;
  }
}
