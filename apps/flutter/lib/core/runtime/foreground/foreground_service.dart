import 'dart:async';
import 'dart:io';

import 'package:flutter_background_service/flutter_background_service.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';

import 'foreground_entrypoint.dart';

class DiyaForegroundService {
  final FlutterBackgroundService _service = FlutterBackgroundService();

  Future<void> initialize() async {
    // Configure notification channel for Android
    const AndroidNotificationChannel channel = AndroidNotificationChannel(
      'diya_foreground',
      'Diya Foreground Service',
      description: 'This channel is used for important notifications.',
      importance: Importance.low, // low importance prevents sound/vibration
    );

    final FlutterLocalNotificationsPlugin flutterLocalNotificationsPlugin = FlutterLocalNotificationsPlugin();

    if (Platform.isAndroid) {
      await flutterLocalNotificationsPlugin
          .resolvePlatformSpecificImplementation<AndroidFlutterLocalNotificationsPlugin>()
          ?.createNotificationChannel(channel);
    }

    await _service.configure(
      androidConfiguration: AndroidConfiguration(
        // The entrypoint must be a top-level function
        onStart: onForegroundStart,
        autoStart: false,
        isForegroundMode: true,
        notificationChannelId: 'diya_foreground',
        initialNotificationTitle: 'Diya Runtime Active',
        initialNotificationContent: 'Runtime initialized',
        foregroundServiceNotificationId: 888,
      ),
      iosConfiguration: IosConfiguration(
        autoStart: false,
        onForeground: onForegroundStart,
      ),
    );
  }

  Future<void> start() async {
    await _service.startService();
  }

  Future<void> stop() async {
    _service.invoke("stopService");
  }
}
