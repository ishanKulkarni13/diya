import 'dart:async';
import 'dart:io';
import 'dart:ui' as ui;

import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/hardware/domain/models/base_device.dart';
import '../../../core/hardware/domain/capabilities/device_capability.dart';
import '../../../core/hardware/domain/models/connection_state.dart';
import '../../../core/hardware/domain/models/known_device.dart';
import '../../../core/hardware/domain/observability/hardware_log_event.dart';
import '../../../core/hardware/providers/hardware_providers.dart';

class DeviceDetailScreen extends ConsumerStatefulWidget {
  final String deviceId;

  const DeviceDetailScreen({super.key, required this.deviceId});

  @override
  ConsumerState<DeviceDetailScreen> createState() => _DeviceDetailScreenState();
}

class _DeviceDetailScreenState extends ConsumerState<DeviceDetailScreen> {
  static const Duration _reachabilityFreshness = Duration(seconds: 8);
  KnownDevice? _knownDevice;
  String? _pingResult;
  Color _pingColor = Colors.grey;
  bool _isPinging = false;
  DateTime? _lastReachableAt;

  int? _batteryLevel;
  bool _isPullingBattery = false;
  DateTime? _lastBatteryPullAt;
  double? _ultrasonicCm;
  Timer? _telemetryTimer;
  bool _isCapturing = false;
  Uint8List? _captureImageBytes;
  String? _captureError;
  bool _hasRequestedRetry = false;

  final List<HardwareLogEvent> _logs = [];
  StreamSubscription? _logSubscription;

  @override
  void initState() {
    super.initState();
    _loadKnownDevice();
    _logSubscription = ref.read(hardwareLoggerProvider).logStream.listen((event) {
      if (event.deviceId == widget.deviceId && mounted) {
        setState(() {
          _logs.insert(0, event);
          if (_logs.length > 200) _logs.removeLast();
        });
      }
    });
    _telemetryTimer = Timer.periodic(const Duration(seconds: 2), (_) => _fetchTelemetry());
  }

  @override
  void dispose() {
    _telemetryTimer?.cancel();
    _logSubscription?.cancel();
    super.dispose();
  }

  Future<void> _loadKnownDevice() async {
    final registry = ref.read(deviceRegistryProvider);
    final devices = await registry.getKnownDevices();
    final known = devices.where((d) => d.deviceId == widget.deviceId).firstOrNull;
    if (mounted) {
      setState(() => _knownDevice = known);
      if (known != null && !_hasRequestedRetry) {
        _hasRequestedRetry = true;
        Future.microtask(() => ref.read(deviceManagerProvider).retryConnection(widget.deviceId));
      }
    }
  }

  Future<void> _fetchTelemetry() async {
    final known = _knownDevice;
    if (known == null || known.deviceType != DeviceType.goggle) {
      return;
    }
    final service = ref.read(debugGoggleServiceProvider);
    final ultrasonic = await service.fetchUltrasonicCm(known);
    if (!mounted) return;
    if (ultrasonic != null) {
      setState(() {
        _ultrasonicCm = ultrasonic;
        _lastReachableAt = DateTime.now();
      });
    }
  }

  Future<void> _pullBatteryStatus(BaseDevice? device) async {
    final capability = device?.getCapability<BatteryCapability>();
    if (capability == null && _knownDevice == null) return;

    setState(() {
      _isPullingBattery = true;
    });

    try {
      final int? level;
      if (capability != null) {
        level = await capability.pullBatteryLevel();
      } else {
        final known = _knownDevice;
        if (known == null) return;
        final service = ref.read(debugGoggleServiceProvider);
        level = await service.pullBatteryLevel(known);
      }
      if (!mounted) return;
      setState(() {
        if (level != null) {
          _batteryLevel = level;
          _lastBatteryPullAt = DateTime.now();
        }
      });
    } finally {
      if (mounted) {
        setState(() => _isPullingBattery = false);
      }
    }
  }

  Future<void> _captureSurroundings(BaseDevice? device) async {
    final capability = device?.getCapability<CameraCapability>();
    if (capability == null && _knownDevice == null) return;

    setState(() {
      _isCapturing = true;
      _captureError = null;
      _captureImageBytes = null;
    });

    try {
      Uint8List? bytes;
      if (capability != null) {
        bytes = await capability.capture();
      } else {
        final known = _knownDevice;
        if (known != null) {
          final service = ref.read(debugGoggleServiceProvider);
          bytes = await service.capture(known);
        }
      }

      if (!mounted) return;
      // Validate image bytes by attempting to instantiate an image codec.
      if (bytes == null || bytes.isEmpty) {
        if (mounted) setState(() => _captureError = 'No image returned by device');
        return;
      }

      try {
        // Decode a frame to ensure the bytes are actually renderable.
        final codec = await ui.instantiateImageCodec(bytes);
        try {
          await codec.getNextFrame();
        } finally {
          codec.dispose();
        }
        if (!mounted) return;
        setState(() {
          _captureImageBytes = bytes;
        });
      } catch (e) {
        final hexPrefix = _hexPrefix(bytes, 24);
        final asciiPrefix = _asciiPrefix(bytes, 64);
        // Persist diagnostic file to system temp for offline inspection.
        String diagPath = 'unknown';
        try {
          final tmp = Directory.systemTemp;
          final file = File('${tmp.path}/capture_diag_${widget.deviceId}_${DateTime.now().microsecondsSinceEpoch}.bin');
          await file.writeAsBytes(bytes, flush: true);
          diagPath = file.path;
        } catch (_) {
          // Ignore any write failures; keep diagPath as unknown.
        }

        final msg = 'Invalid image data: $e (diagnostic: $diagPath)';
        debugPrint('capture.decode.failed: $msg');
        debugPrint('capture.decode.failed: len=${bytes.length} hex=$hexPrefix ascii=$asciiPrefix');
        if (mounted) {
          setState(() {
            _captureError = msg;
            _captureImageBytes = null;
          });
        }
      }
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _captureError = '$e';
        _captureImageBytes = null;
      });
    } finally {
      if (mounted) {
        setState(() => _isCapturing = false);
      }
    }
  }

  String _hexPrefix(Uint8List bytes, int max) {
    final len = bytes.length < max ? bytes.length : max;
    final buffer = StringBuffer();
    for (var i = 0; i < len; i++) {
      buffer.write(bytes[i].toRadixString(16).padLeft(2, '0'));
    }
    return buffer.toString();
  }

  String _asciiPrefix(Uint8List bytes, int max) {
    final len = bytes.length < max ? bytes.length : max;
    final buffer = StringBuffer();
    for (var i = 0; i < len; i++) {
      final b = bytes[i];
      if (b >= 32 && b <= 126) {
        buffer.writeCharCode(b);
      } else {
        buffer.write('.');
      }
    }
    return buffer.toString();
  }

  bool get _hasRecentReachability {
    final lastReachableAt = _lastReachableAt;
    if (lastReachableAt == null) return false;
    return DateTime.now().difference(lastReachableAt) <= _reachabilityFreshness;
  }

  ({String label, Color color, IconData icon}) _buildLinkStatus(BaseDevice? activeDevice, KnownDevice? knownDevice) {
    if (activeDevice?.state == HardwareConnectionState.ready && _hasRecentReachability) {
      return (label: 'online', color: Colors.green, icon: Icons.link);
    }

    if (_hasRecentReachability) {
      return (label: 'reachable', color: Colors.blue, icon: Icons.wifi_tethering);
    }

    if (_isPinging) {
      return (label: 'checking', color: Colors.blueGrey, icon: Icons.hourglass_top);
    }

    if (knownDevice != null) {
      return (label: 'waiting for device', color: Colors.blueGrey, icon: Icons.cloud_off);
    }

    return (label: 'unknown', color: Colors.grey, icon: Icons.help_outline);
  }

  Future<void> _pingDevice() async {
    final known = _knownDevice;
    if (known == null) {
      return;
    }
    if (known.deviceType != DeviceType.goggle) {
      setState(() {
        _pingResult = 'UNSUPPORTED';
        _pingColor = Colors.grey;
      });
      return;
    }

    setState(() {
      _isPinging = true;
      _pingResult = 'Pinging...';
      _pingColor = Colors.orange;
    });

    try {
      final service = ref.read(debugGoggleServiceProvider);
      final ok = await service.ping(known);
      if (ok) {
        setState(() {
          _pingResult = 'OK';
          _pingColor = Colors.green;
          _lastReachableAt = DateTime.now();
        });
      } else {
        setState(() {
          _pingResult = 'FAILED';
          _pingColor = Colors.red;
        });
      }
    } catch (e) {
      setState(() {
        _pingResult = 'FAILED: $e';
        _pingColor = Colors.red;
      });
    } finally {
      setState(() => _isPinging = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final devicesStream = ref.watch(deviceManagerProvider).devices;

    return StreamBuilder<List<BaseDevice>>(
      stream: devicesStream,
      initialData: const [],
      builder: (context, snapshot) {
        final devices = snapshot.data ?? [];
        final activeDevice = devices.where((d) => d.id == widget.deviceId).firstOrNull;
        final knownDevice = _knownDevice;
        final isKnownGoggle = knownDevice?.deviceType == DeviceType.goggle;

        if (activeDevice == null && knownDevice == null) {
          return Scaffold(
            appBar: AppBar(title: const Text('Device Not Found')),
            body: const Center(child: Text('This device is no longer connected.')),
          );
        }

        final displayName = activeDevice?.name ?? (isKnownGoggle ? 'Smart Goggle' : 'Smart Cane');
        final isCane = activeDevice?.name.toLowerCase().contains('cane') ?? (knownDevice?.deviceType == DeviceType.cane);
        final isGoggle = activeDevice?.name.toLowerCase().contains('goggle') ?? isKnownGoggle;
        final isConnected = activeDevice != null;

        return Scaffold(
          appBar: AppBar(
            title: Text(displayName),
            actions: [
              IconButton(
                icon: const Icon(Icons.refresh),
                tooltip: 'Refresh device info',
                onPressed: () async {
                  await _loadKnownDevice();
                  await _fetchTelemetry();
                },
              ),
              IconButton(
                icon: const Icon(Icons.delete_outline, color: Colors.redAccent),
                tooltip: 'Disconnect & Forget',
                onPressed: () {
                  ref.read(deviceManagerProvider).disconnectDevice(widget.deviceId);
                  Navigator.of(context).pop();
                },
              )
            ],
          ),
          body: SingleChildScrollView(
            padding: const EdgeInsets.all(16.0),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                _buildInfoCard(activeDevice, knownDevice),
                const SizedBox(height: 16),
                _buildConnectionCard(),
                const SizedBox(height: 16),
                _buildLogsCard(),
                const SizedBox(height: 24),
                if (isCane) ...[
                  _buildCaneCapabilities(context, ref, activeDevice, isConnected),
                ] else if (isGoggle) ...[
                  _buildGoggleCapabilities(context, ref, activeDevice, isConnected),
                ] else ...[
                  const Center(child: Text('No specific capabilities for this device type.')),
                ]
              ],
            ),
          ),
        );
      },
    );
  }

    Widget _buildInfoCard(BaseDevice? activeDevice, KnownDevice? knownDevice) {
    final deviceId = activeDevice?.id ?? knownDevice?.deviceId ?? widget.deviceId;
    final managerLabel = activeDevice?.state.name ?? 'not attached';
    final managerColor = activeDevice == null
      ? Colors.blueGrey
      : (activeDevice.state == HardwareConnectionState.ready ? Colors.green : Colors.blueGrey);
    final linkStatus = _buildLinkStatus(activeDevice, knownDevice);
    final subtitle = knownDevice == null
        ? 'Unknown device'
      : 'Type: ${knownDevice.deviceType.name} • Last seen: ${knownDevice.lastSeenTimestamp.toLocal().toString().split('.').first}';

    return Card(
      elevation: 2,
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('ID: $deviceId', style: const TextStyle(color: Colors.grey)),
            const SizedBox(height: 8),
            Text(subtitle),
            const SizedBox(height: 8),
            Row(
              children: [
                const Text('Manager: '),
                Chip(
                  label: Text(managerLabel),
                  avatar: Icon(
                    activeDevice == null ? Icons.link_off : Icons.device_hub,
                    size: 16,
                    color: managerColor,
                  ),
                  backgroundColor: managerColor.withValues(alpha: 0.15),
                ),
              ],
            ),
            const SizedBox(height: 8),
            Row(
              children: [
                const Text('Link: '),
                Chip(
                  label: Text(linkStatus.label),
                  avatar: Icon(linkStatus.icon, size: 16, color: linkStatus.color),
                  backgroundColor: linkStatus.color.withValues(alpha: 0.15),
                ),
              ],
            ),
            if (activeDevice == null && knownDevice != null) ...[
              const SizedBox(height: 12),
              Align(
                alignment: Alignment.centerLeft,
                child: ElevatedButton.icon(
                  onPressed: () => ref.read(deviceManagerProvider).retryConnection(widget.deviceId),
                  icon: const Icon(Icons.refresh),
                  label: const Text('Retry Attach'),
                ),
              ),
            ],
            const SizedBox(height: 8),
            Text(
              _hasRecentReachability
                  ? 'Telemetry or ping confirmed the device is responding.'
                  : 'The app has a saved device profile and is waiting for a live response.',
              style: const TextStyle(color: Colors.grey),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildCaneCapabilities(BuildContext context, WidgetRef ref, BaseDevice? device, bool isConnected) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text('Cane Capabilities', style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold)),
        const SizedBox(height: 16),
        Card(
          child: ListTile(
            leading: const Icon(Icons.vibration),
            title: const Text('Trigger Haptic Feedback'),
            subtitle: const Text('Sends a vibration command'),
            trailing: ElevatedButton(
              onPressed: isConnected && device?.state == HardwareConnectionState.ready
                  ? () {
                      ScaffoldMessenger.of(context).showSnackBar(
                        const SnackBar(content: Text('Vibration command simulated.')),
                      );
                    }
                  : null,
              child: const Text('VIBRATE'),
            ),
          ),
        ),
        const SizedBox(height: 16),
        Card(
          child: Padding(
            padding: const EdgeInsets.all(16.0),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text('Ultrasonic Sensor Feed', style: TextStyle(fontWeight: FontWeight.bold)),
                const SizedBox(height: 24),
                Center(
                  child: Container(
                    height: 150,
                    width: double.infinity,
                    decoration: BoxDecoration(
                      color: Colors.black87,
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: const Center(
                      child: Text(
                        'WAITING FOR TELEMETRY STREAM...',
                        style: TextStyle(color: Colors.greenAccent, fontFamily: 'monospace'),
                      ),
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildGoggleCapabilities(BuildContext context, WidgetRef ref, BaseDevice? device, bool isConnected) {
    final canOperate = device != null || (_knownDevice?.lastKnownIp != null && _knownDevice?.deviceType == DeviceType.goggle);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text('Goggle Capabilities', style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold)),
        const SizedBox(height: 16),
        Card(
          child: ListTile(
            leading: const Icon(Icons.battery_full),
            title: const Text('Battery'),
            subtitle: Text(_batteryLevel != null
                ? '${_batteryLevel!}%${_lastBatteryPullAt != null ? ' • updated ${_lastBatteryPullAt!.toLocal().toString().split('.').first}' : ''}'
                : 'Pull to read current level'),
            trailing: ElevatedButton.icon(
              onPressed: _isPullingBattery || !canOperate ? null : () => _pullBatteryStatus(device),
              icon: _isPullingBattery
                  ? const SizedBox(width: 14, height: 14, child: CircularProgressIndicator(strokeWidth: 2))
                  : const Icon(Icons.download),
              label: const Text('Pull'),
            ),
          ),
        ),
        const SizedBox(height: 12),
        Card(
          child: ListTile(
            leading: const Icon(Icons.sensors),
            title: const Text('Ultrasonic'),
            subtitle: Text(_ultrasonicCm != null ? '${_ultrasonicCm!.toStringAsFixed(1)} cm' : 'Unknown'),
          ),
        ),
        const SizedBox(height: 12),
        Card(
          child: Padding(
            padding: const EdgeInsets.all(16.0),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    const Text('Camera', style: TextStyle(fontWeight: FontWeight.bold)),
                    const Spacer(),
                    ElevatedButton.icon(
                      onPressed: _isCapturing || !canOperate ? null : () => _captureSurroundings(device),
                      icon: _isCapturing
                          ? const SizedBox(width: 14, height: 14, child: CircularProgressIndicator(strokeWidth: 2))
                          : const Icon(Icons.camera_alt),
                      label: const Text('Capture'),
                    ),
                  ],
                ),
                const SizedBox(height: 16),
                Center(
                  child: Container(
                    height: 200,
                    width: double.infinity,
                    decoration: BoxDecoration(
                      color: Colors.black87,
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: Builder(builder: (context) {
                      final imageBytes = _captureImageBytes;
                      if (imageBytes != null) {
                        return ClipRRect(
                          borderRadius: BorderRadius.circular(8),
                          child: Image.memory(
                            imageBytes,
                            fit: BoxFit.cover,
                            errorBuilder: (context, error, stackTrace) {
                              return Center(
                                child: Text(
                                  'Image decode failed: $error',
                                  textAlign: TextAlign.center,
                                  style: const TextStyle(color: Colors.greenAccent, fontFamily: 'monospace'),
                                ),
                              );
                            },
                          ),
                        );
                      }

                      return Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          const Icon(Icons.videocam_off, color: Colors.white54, size: 48),
                          const SizedBox(height: 16),
                          Text(
                            _captureError ?? 'Press CAPTURE to fetch surrounding image',
                            textAlign: TextAlign.center,
                            style: const TextStyle(color: Colors.greenAccent, fontFamily: 'monospace'),
                          ),
                        ],
                      );
                    }),
                  ),
                ),
              ],
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildConnectionCard() {
    final host = _knownDevice?.lastKnownIp ?? 'unknown';
    final port = _knownDevice?.lastKnownPort ?? 80;

    return Card(
      elevation: 2,
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('Connection', style: TextStyle(fontWeight: FontWeight.bold)),
            const SizedBox(height: 8),
            Text('IP: $host', style: const TextStyle(fontFamily: 'monospace')),
            Text('Port: $port', style: const TextStyle(fontFamily: 'monospace')),
            const SizedBox(height: 12),
            Row(
              children: [
                ElevatedButton.icon(
                  onPressed: _isPinging ? null : _pingDevice,
                  icon: _isPinging
                      ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2))
                      : const Icon(Icons.network_ping),
                  label: const Text('Ping Device'),
                ),
                const SizedBox(width: 12),
                if (_pingResult != null)
                  Expanded(
                    child: Text(
                      _pingResult!,
                      style: TextStyle(color: _pingColor),
                    ),
                  ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildLogsCard() {
    return Card(
      elevation: 2,
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('Device Logs', style: TextStyle(fontWeight: FontWeight.bold)),
            const SizedBox(height: 8),
            if (_logs.isEmpty)
              const Text('No logs yet.', style: TextStyle(color: Colors.grey))
            else
              SizedBox(
                height: 160,
                child: ListView.builder(
                  itemCount: _logs.length,
                  itemBuilder: (context, index) {
                    final log = _logs[index];
                    return Text(
                      "[${log.timestamp.toLocal().toString().split('.').first}] ${log.toString()}",
                      style: const TextStyle(fontFamily: 'monospace', fontSize: 12),
                    );
                  },
                ),
              ),
          ],
        ),
      ),
    );
  }
}
