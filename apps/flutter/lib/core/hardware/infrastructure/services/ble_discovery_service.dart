import 'dart:async';
import 'package:flutter_blue_plus/flutter_blue_plus.dart';

class BleDiscoveryService {
  final String serviceUuid;
  BleDiscoveryService(this.serviceUuid);

  Stream<Map<String, dynamic>> scan() {
    final controller = StreamController<Map<String, dynamic>>.broadcast();
    
    FlutterBluePlus.startScan(
      withServices: [Guid(serviceUuid)],
      timeout: const Duration(seconds: 15),
    );

    final sub = FlutterBluePlus.scanResults.listen((results) {
      for (var result in results) {
        controller.add({
          'device_id': result.device.remoteId.str,
          'device_type': 'cane',
          'device_name': result.device.platformName.isEmpty ? 'Diya Cane' : result.device.platformName,
        });
      }
    });

    controller.onCancel = () {
      sub.cancel();
      FlutterBluePlus.stopScan();
    };

    return controller.stream;
  }
}
