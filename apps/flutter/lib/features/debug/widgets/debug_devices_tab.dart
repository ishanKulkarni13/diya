import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/hardware/domain/models/base_device.dart';
import '../../../core/hardware/domain/models/known_device.dart';
import '../../../core/hardware/providers/hardware_providers.dart';

class DebugDevicesTab extends ConsumerStatefulWidget {
  const DebugDevicesTab({super.key});

  @override
  ConsumerState<DebugDevicesTab> createState() => _DebugDevicesTabState();
}

class _DebugDevicesTabState extends ConsumerState<DebugDevicesTab> {
  List<KnownDevice> _knownDevices = const [];
  bool _isLoadingKnown = false;

  @override
  void initState() {
    super.initState();
    Future.microtask(() async {
      await _refreshAll();
    });
  }

  Future<void> _refreshAll() async {
    await ref.read(blePermissionServiceProvider).requestPermissions();
    await ref.read(deviceManagerProvider).startScan();
    await _loadKnownDevices();
  }

  Future<void> _loadKnownDevices() async {
    setState(() {
      _isLoadingKnown = true;
    });
    final registry = ref.read(deviceRegistryProvider);
    final devices = await registry.getKnownDevices();
    if (mounted) {
      setState(() {
        _knownDevices = devices;
        _isLoadingKnown = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final devicesStream = ref.watch(deviceManagerProvider).devices;

    return StreamBuilder<List<BaseDevice>>(
      stream: devicesStream,
      initialData: const [],
      builder: (context, snapshot) {
        final activeDevices = snapshot.data ?? [];
        final activeIds = activeDevices.map((d) => d.id).toSet();
        final inactiveKnown = _knownDevices.where((d) => !activeIds.contains(d.deviceId)).toList();

        return ListView(
          children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(12, 12, 12, 0),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  const Text('Devices', style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold)),
                  IconButton(
                    icon: const Icon(Icons.refresh),
                    tooltip: 'Refresh devices',
                    onPressed: _refreshAll,
                  ),
                ],
              ),
            ),
            if (activeDevices.isEmpty)
              const Padding(
                padding: EdgeInsets.symmetric(horizontal: 12, vertical: 16),
                child: Text(
                  "No active devices\n\nHint: Use the simulator to register on port 8080",
                  textAlign: TextAlign.center,
                  style: TextStyle(color: Colors.grey),
                ),
              )
            else
              ...activeDevices.map((device) => Card(
                    margin: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                    elevation: 2,
                    child: ListTile(
                      leading: const Icon(Icons.hardware),
                      title: Text(device.name, style: const TextStyle(fontWeight: FontWeight.bold)),
                      subtitle: Text("ID: ${device.id}\nState: ${device.state.name}"),
                      trailing: IconButton(
                        icon: const Icon(Icons.close, color: Colors.red),
                        tooltip: 'Disconnect',
                        onPressed: () {
                          ref.read(deviceManagerProvider).disconnectDevice(device.id);
                        },
                      ),
                      onTap: () {
                        context.push('/debug/device/${device.id}');
                      },
                    ),
                  )),
            Padding(
              padding: const EdgeInsets.fromLTRB(12, 20, 12, 4),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  const Text('Known Devices', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
                  if (_isLoadingKnown)
                    const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2)),
                ],
              ),
            ),
            if (_knownDevices.isEmpty)
              const Padding(
                padding: EdgeInsets.symmetric(horizontal: 12, vertical: 12),
                child: Text('No known devices saved.', style: TextStyle(color: Colors.grey)),
              )
            else
              ...inactiveKnown.map((device) => Card(
                    margin: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                    elevation: 1,
                    child: ListTile(
                      leading: const Icon(Icons.devices_other),
                      title: Text(device.deviceId, style: const TextStyle(fontWeight: FontWeight.bold)),
                      subtitle: Text('Type: ${device.deviceType.name}\nLast IP: ${device.lastKnownIp ?? 'unknown'}:${device.lastKnownPort ?? 80}'),
                      trailing: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          IconButton(
                            icon: const Icon(Icons.link, color: Colors.blueAccent),
                            tooltip: 'Connect',
                            onPressed: () {
                              ref.read(deviceManagerProvider).retryConnection(device.deviceId);
                            },
                          ),
                          IconButton(
                            icon: const Icon(Icons.delete_outline, color: Colors.redAccent),
                            tooltip: 'Forget device',
                            onPressed: () async {
                              await ref.read(deviceRegistryProvider).removeDevice(device.deviceId);
                              await _loadKnownDevices();
                            },
                          ),
                        ],
                      ),
                    ),
                  )),
          ],
        );
      },
    );
  }
}
