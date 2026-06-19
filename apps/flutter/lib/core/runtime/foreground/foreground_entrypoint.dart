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

  debugPrint('Service starting');

  try {
    await dotenv.load(fileName: '.env', isOptional: true);
  } on FileNotFoundError {
    debugPrint('No .env file found. Proceeding with defaults.');
  }

  AppConfig.validate();

  final FlutterLocalNotificationsPlugin flutterLocalNotificationsPlugin = FlutterLocalNotificationsPlugin();
  
  const AndroidInitializationSettings initializationSettingsAndroid = AndroidInitializationSettings('@mipmap/ic_launcher');
  const InitializationSettings initializationSettings = InitializationSettings(android: initializationSettingsAndroid);
  // Wait, let's fix it
  await flutterLocalNotificationsPlugin.initialize(settings: initializationSettings);

  Future<void> showNotification(String title, String body) async {
    await flutterLocalNotificationsPlugin.show(
      id: 888,
      title: title,
      body: body,
      notificationDetails: const NotificationDetails(
        android: AndroidNotificationDetails(
          'diya_foreground',
          'Diya Foreground Service',
          ongoing: true,
          importance: Importance.low,
        ),
      ),
    );
  }

  // Show notification immediately
  if (service is AndroidServiceInstance) {
    if (await service.isForegroundService()) {
      await showNotification('Diya Runtime Active', 'Starting runtime...');
      debugPrint('Notification visible');
    }
  }

  final runtime = DiyaRuntime();

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

  debugPrint('Heartbeat started');

  // Heartbeat every 30 seconds
  Timer.periodic(const Duration(seconds: 30), (timer) async {
    if (service is AndroidServiceInstance) {
      if (await service.isForegroundService()) {
        await showNotification('Diya Runtime Active', 'Assistive Runtime Running (Heartbeat: ${DateTime.now().toIso8601String()})');
      }
    }
    
    debugPrint('Heartbeat');
  });

  debugPrint('Runtime booting');
  try {
    await runtime.boot();
    debugPrint('Runtime booted');
    debugPrint('Session initialized');
    debugPrint('Queue initialized');
    debugPrint('Safety initialized');
  } catch (e, st) {
    debugPrint('Runtime boot failed');
    debugPrint(e.toString());
    debugPrint(st.toString());
    
    if (service is AndroidServiceInstance) {
      if (await service.isForegroundService()) {
        await showNotification('Diya Runtime Active', 'Runtime failed');
      }
    }
  }
}
