import 'dart:async';
import 'dart:ui';
import 'package:flutter/widgets.dart';
import 'package:flutter_background_service/flutter_background_service.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:flutter_dotenv/flutter_dotenv.dart';

import '../diya_runtime.dart';
import '../../config/app_config.dart';

@pragma('vm:entry-point')
void onForegroundStart(ServiceInstance service) async {
  // Ensure basic platform channel bindings are available for plugins 
  // (e.g. shared preferences, location) on the background isolate.
  DartPluginRegistrant.ensureInitialized();
  WidgetsFlutterBinding.ensureInitialized();

  debugPrint('Foreground service started');

  try {
    await dotenv.load(fileName: '.env', isOptional: true);
  } on FileNotFoundError {
    debugPrint('No .env file found. Proceeding with defaults.');
  }

  AppConfig.validate();

  final runtime = DiyaRuntime();
  await runtime.boot();

  debugPrint('DiyaRuntime booted');
  debugPrint('Session initialized');
  debugPrint('Queue initialized');
  debugPrint('Safety initialized');

  final FlutterLocalNotificationsPlugin flutterLocalNotificationsPlugin = FlutterLocalNotificationsPlugin();

  if (service is AndroidServiceInstance) {
    service.on('setAsForeground').listen((event) {
      service.setAsForegroundService();
    });

    service.on('setAsBackground').listen((event) {
      service.setAsBackgroundService();
    });
  }

  service.on('stopService').listen((event) {
    runtime.shutdown();
    service.stopSelf();
  });

  // Heartbeat every 30 seconds
  Timer.periodic(const Duration(seconds: 30), (timer) async {
    if (service is AndroidServiceInstance) {
      if (await service.isForegroundService()) {
        flutterLocalNotificationsPlugin.show(
          id: 888,
          title: 'Diya Runtime Active',
          body: 'Assistive Runtime Running (Heartbeat: ${DateTime.now().toIso8601String()})',
          notificationDetails: const NotificationDetails(
            android: AndroidNotificationDetails(
              'diya_foreground',
              'Diya Foreground Service',
              icon: 'ic_bg_service_small',
              ongoing: true,
              importance: Importance.low,
            ),
          ),
        );
      }
    }
    
    debugPrint('Foreground heartbeat');
  });
}
