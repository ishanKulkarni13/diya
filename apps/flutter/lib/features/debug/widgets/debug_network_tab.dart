import 'dart:io';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:network_info_plus/network_info_plus.dart';
import 'package:dio/dio.dart';
import 'package:permission_handler/permission_handler.dart';

import '../../../core/config/app_config.dart';

class DebugNetworkTab extends ConsumerStatefulWidget {
  const DebugNetworkTab({super.key});

  @override
  ConsumerState<DebugNetworkTab> createState() => _DebugNetworkTabState();
}

class _DebugNetworkTabState extends ConsumerState<DebugNetworkTab> {
  final NetworkInfo _networkInfo = NetworkInfo();
  
  String _wifiIP = 'Loading...';
  bool _isLoadingIP = true;

  String _pingResult = '';
  Color _pingColor = Colors.grey;
  bool _isPinging = false;

  @override
  void initState() {
    super.initState();
    _fetchIP();
  }

  Future<void> _fetchIP() async {
    setState(() {
      _isLoadingIP = true;
      _wifiIP = 'Checking permissions...';
    });

    try {
      if (Platform.isAndroid || Platform.isIOS) {
        final locationStatus = await Permission.locationWhenInUse.request();
        final wifiStatus = Platform.isAndroid ? await Permission.nearbyWifiDevices.request() : PermissionStatus.granted;

        if (!locationStatus.isGranted || (Platform.isAndroid && !wifiStatus.isGranted)) {
          setState(() {
            _wifiIP = 'Permission denied (location/WiFi)';
            _isLoadingIP = false;
          });
          return;
        }
      }

      final ip = await _networkInfo.getWifiIP();
      final fallbackIp = ip ?? await _getLocalIPv4();
      
      setState(() {
        if (ip != null && ip.isNotEmpty) {
          _wifiIP = ip;
        } else if (fallbackIp != null) {
          _wifiIP = '$fallbackIp (non-WiFi)';
        } else {
          _wifiIP = 'Unknown (Check WiFi/Hotspot and Location Services)';
        }
      });
    } catch (e) {
      setState(() {
        _wifiIP = 'Error: $e';
      });
    } finally {
      setState(() {
        _isLoadingIP = false;
      });
    }
  }

  Future<String?> _getLocalIPv4() async {
    try {
      final interfaces = await NetworkInterface.list(type: InternetAddressType.IPv4, includeLoopback: false);
      for (final interface in interfaces) {
        for (final addr in interface.addresses) {
          if (!addr.isLoopback && addr.address.isNotEmpty) {
            return addr.address;
          }
        }
      }
    } catch (_) {
      // Best effort; ignore and return null.
    }
    return null;
  }

  Future<void> _pingBackend() async {
    setState(() {
      _isPinging = true;
      _pingResult = 'Pinging...';
      _pingColor = Colors.orange;
    });

    try {
      final dio = Dio(BaseOptions(connectTimeout: const Duration(seconds: 5)));
      final healthUrl = '${AppConfig.apiBaseUrl}/health';
      
      final startTime = DateTime.now();
      final response = await dio.get(healthUrl);
      final duration = DateTime.now().difference(startTime).inMilliseconds;

      if (response.statusCode == 200) {
        setState(() {
          _pingResult = 'SUCCESS (${duration}ms)\nResponse: ${response.data}';
          _pingColor = Colors.green;
        });
      } else {
        setState(() {
          _pingResult = 'FAILED: Status ${response.statusCode}';
          _pingColor = Colors.red;
        });
      }
    } on DioException catch (e) {
      setState(() {
        _pingResult = 'FAILED: ${e.message}';
        _pingColor = Colors.red;
      });
    } catch (e) {
      setState(() {
        _pingResult = 'FAILED to connect:\n$e';
        _pingColor = Colors.red;
      });
    } finally {
      setState(() {
        _isPinging = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          const Text(
            'Network Diagnostics',
            style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 16),
          _buildInfoCard(
            title: 'Phone Local IP (WiFi)',
            value: _wifiIP,
            icon: Icons.wifi,
            actionIcon: Icons.refresh,
            isLoading: _isLoadingIP,
            onAction: _fetchIP,
          ),
          const SizedBox(height: 16),
          _buildInfoCard(
            title: 'Configured API Domain',
            value: AppConfig.apiBaseUrl,
            icon: Icons.dns,
          ),
          const SizedBox(height: 32),
          ElevatedButton.icon(
            style: ElevatedButton.styleFrom(
              padding: const EdgeInsets.symmetric(vertical: 16),
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
            ),
            onPressed: _isPinging ? null : _pingBackend,
            icon: _isPinging 
                ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2))
                : const Icon(Icons.network_ping),
            label: const Text('PING BACKEND', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
          ),
          const SizedBox(height: 24),
          if (_pingResult.isNotEmpty)
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: Colors.black87,
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: _pingColor, width: 2),
              ),
              child: Text(
                _pingResult,
                style: TextStyle(color: _pingColor, fontFamily: 'monospace'),
              ),
            ),
        ],
      ),
    );
  }

  Widget _buildInfoCard({
    required String title,
    required String value,
    required IconData icon,
    IconData? actionIcon,
    bool isLoading = false,
    VoidCallback? onAction,
  }) {
    return Card(
      elevation: 2,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Row(
          children: [
            Icon(icon, size: 32, color: Theme.of(context).colorScheme.primary),
            const SizedBox(width: 16),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(title, style: const TextStyle(fontWeight: FontWeight.bold, color: Colors.grey)),
                  const SizedBox(height: 4),
                  Text(value, style: const TextStyle(fontSize: 16, fontFamily: 'monospace')),
                ],
              ),
            ),
            if (actionIcon != null && onAction != null)
              isLoading
                  ? const Padding(
                      padding: EdgeInsets.all(12.0),
                      child: SizedBox(width: 24, height: 24, child: CircularProgressIndicator(strokeWidth: 2)),
                    )
                  : IconButton(
                      icon: Icon(actionIcon),
                      onPressed: onAction,
                    ),
          ],
        ),
      ),
    );
  }
}
