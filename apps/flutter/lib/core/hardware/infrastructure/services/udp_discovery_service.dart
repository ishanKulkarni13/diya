import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'package:flutter/foundation.dart';

/// UDP-based discovery service for Wi-Fi devices (Smart Goggles).
/// 
/// Listens for broadcast packets on port 8888 and emits discovered devices.
/// Implements the Diya Discovery Protocol v1.0.0.
/// 
/// Packet format:
/// ```json
/// {
///   "protocol": "diya-discovery",
///   "version": "1.0.0",
///   "device_id": "goggle-abc123",
///   "device_type": "goggle",
///   "ip": "192.168.1.120",
///   "port": 9000,
///   "battery": 75,
///   "uptime": 12345,
///   "timestamp": 1718812345678
/// }
/// ```
class UdpDiscoveryService {
  final int port;
  RawDatagramSocket? _socket;
  StreamController<Map<String, dynamic>>? _controller;
  
  static const String _expectedProtocol = 'diya-discovery';
  static const String _expectedVersion = '1.0.0';
  static const int _maxPacketAge = 60000; // 60 seconds in milliseconds
  static const int _clockSkewTolerance = 5000; // 5 seconds in milliseconds

  UdpDiscoveryService({this.port = 8888});

  /// Start listening for UDP broadcasts and return a stream of discovered devices.
  /// 
  /// The stream emits events in the format:
  /// ```dart
  /// {
  ///   'device_id': 'goggle-abc123',
  ///   'device_type': 'goggle',
  ///   'device_name': 'Diya Smart Goggles',
  ///   'source_ip': '192.168.1.120',
  ///   'port': 9000,
  /// }
  /// ```
  Stream<Map<String, dynamic>> scan() {
    if (_controller != null && !_controller!.isClosed) {
      debugPrint('[UDP] Discovery service already running');
      return _controller!.stream;
    }

    _controller = StreamController<Map<String, dynamic>>.broadcast();

    _startListening();

    _controller!.onCancel = () {
      stop();
    };

    return _controller!.stream;
  }

  Future<void> _startListening() async {
    try {
      // Bind to all interfaces on the discovery port
      _socket = await RawDatagramSocket.bind(InternetAddress.anyIPv4, port);
      
      debugPrint('[UDP] Discovery service started on port $port');
      
      _socket!.listen((RawSocketEvent event) {
        if (event == RawSocketEvent.read) {
          final datagram = _socket!.receive();
          if (datagram != null) {
            _handlePacket(datagram);
          }
        }
      });
    } catch (e) {
      debugPrint('[UDP] Failed to bind socket on port $port: $e');
      _controller?.addError(e);
    }
  }

  void _handlePacket(Datagram datagram) {
    try {
      final sourceIp = datagram.address.address;
      final bytes = datagram.data;
      
      debugPrint('[UDP] Received packet from $sourceIp (${bytes.length} bytes)');
      
      // Decode UTF-8
      final jsonString = utf8.decode(bytes);
      
      // Parse JSON
      final packet = jsonDecode(jsonString) as Map<String, dynamic>;
      
      // Validate packet
      if (!_validatePacket(packet)) {
        debugPrint('[UDP] Invalid packet from $sourceIp: validation failed');
        return;
      }
      
      // Validate timestamp
      if (!_validateTimestamp(packet['timestamp'] as int)) {
        debugPrint('[UDP] Invalid packet from $sourceIp: timestamp out of range');
        return;
      }
      
      // Extract fields
      final deviceId = packet['device_id'] as String;
      final deviceType = packet['device_type'] as String;
      final deviceName = packet['device_name'] as String?;
      final ip = packet['ip'] as String;
      final port = packet['port'] as int;
      
      debugPrint('[UDP] Parsed device: $deviceId at $ip:$port');
      
      // Emit discovery event (matches BLE/HTTP format)
      _controller?.add({
        'device_id': deviceId,
        'device_type': deviceType,
        'device_name': deviceName ?? 'Diya Device',
        'source_ip': ip,
        'port': port,
      });
    } on FormatException catch (e) {
      debugPrint('[UDP] Invalid packet: malformed JSON - $e');
    } catch (e) {
      debugPrint('[UDP] Error processing packet: $e');
    }
  }

  bool _validatePacket(Map<String, dynamic> packet) {
    // Check protocol
    if (packet['protocol'] != _expectedProtocol) {
      debugPrint('[UDP] Invalid packet: protocol mismatch (expected $_expectedProtocol, got ${packet['protocol']})');
      return false;
    }
    
    // Check version (currently only 1.0.0 supported)
    if (packet['version'] != _expectedVersion) {
      debugPrint('[UDP] Invalid packet: unsupported version (${packet['version']})');
      return false;
    }
    
    // Check required fields
    if (packet['device_id'] == null || (packet['device_id'] as String).isEmpty) {
      debugPrint('[UDP] Invalid packet: missing or empty device_id');
      return false;
    }
    
    if (packet['device_type'] == null) {
      debugPrint('[UDP] Invalid packet: missing device_type');
      return false;
    }
    
    if (packet['ip'] == null) {
      debugPrint('[UDP] Invalid packet: missing ip');
      return false;
    }
    
    if (packet['port'] == null || (packet['port'] as int) < 1) {
      debugPrint('[UDP] Invalid packet: missing or invalid port');
      return false;
    }
    
    if (packet['timestamp'] == null) {
      debugPrint('[UDP] Invalid packet: missing timestamp');
      return false;
    }
    
    return true;
  }

  bool _validateTimestamp(int timestamp) {
    final now = DateTime.now().millisecondsSinceEpoch;
    final age = now - timestamp;
    
    // Reject future packets (with clock skew tolerance)
    if (age < -_clockSkewTolerance) {
      debugPrint('[UDP] Invalid timestamp: packet from future (age: ${age}ms)');
      return false;
    }
    
    // Reject very old packets
    if (age > _maxPacketAge) {
      debugPrint('[UDP] Invalid timestamp: packet too old (age: ${age}ms)');
      return false;
    }
    
    return true;
  }

  /// Stop listening for UDP broadcasts.
  Future<void> stop() async {
    _socket?.close();
    _socket = null;
    
    if (_controller != null && !_controller!.isClosed) {
      await _controller!.close();
    }
    _controller = null;
    
    debugPrint('[UDP] Discovery service stopped');
  }
}
