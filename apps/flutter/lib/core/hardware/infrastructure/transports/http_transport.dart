import 'dart:async';
import 'dart:convert';
import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import '../../domain/transports/device_transport.dart';

class HttpTransportImpl implements DeviceTransport {
  final Dio _dio;
  final _stateController = StreamController<TransportState>.broadcast();
  final _incomingController = StreamController<Uint8List>.broadcast();

  TransportState _currentState = TransportState.disconnected;
  String? _connectedIp;

  HttpTransportImpl(this._dio);

  @override
  Stream<TransportState> get state => _stateController.stream;

  @override
  Stream<Uint8List> get incoming => _incomingController.stream;

  @override
  Future<void> connect(String address) async {
    _updateState(TransportState.connecting);
    try {
      _connectedIp = address;
      final response = await _dio.get(
        'http://$_connectedIp/health',
        options: Options(receiveTimeout: const Duration(seconds: 3)),
      );
      if (response.statusCode == 200) {
        _updateState(TransportState.connected);
      } else {
        _updateState(TransportState.error);
      }
    } catch (_) {
      _updateState(TransportState.error);
      rethrow;
    }
  }

  @override
  Future<void> disconnect() async {
    _connectedIp = null;
    _updateState(TransportState.disconnected);
  }

  @override
  Future<void> send(Uint8List data) async {
    if (_currentState != TransportState.connected || _connectedIp == null) {
      throw Exception('Cannot send data while disconnected');
    }
    
    final jsonStr = utf8.decode(data);
    final payload = jsonDecode(jsonStr);

    final response = await _dio.post(
      'http://$_connectedIp/command',
      data: payload,
      options: Options(sendTimeout: const Duration(seconds: 3)),
    );

    if (response.statusCode == 200 && response.data != null) {
      final responseBytes = utf8.encode(jsonEncode(response.data));
      _incomingController.add(Uint8List.fromList(responseBytes));
    }
  }

  @override
  Future<Map<String, dynamic>> requestJson(
    String method,
    String path, {
    Map<String, dynamic>? body,
    Duration? timeout,
  }) async {
    if (_currentState != TransportState.connected || _connectedIp == null) {
      throw Exception('Cannot request while disconnected');
    }

    final normalizedPath = path.startsWith('/') ? path : '/$path';
    final options = Options(
      sendTimeout: timeout ?? const Duration(seconds: 3),
      receiveTimeout: timeout ?? const Duration(seconds: 3),
    );

    final response = method.toUpperCase() == 'GET'
        ? await _dio.get('http://$_connectedIp$normalizedPath', options: options)
        : await _dio.post('http://$_connectedIp$normalizedPath', data: body, options: options);

    if (response.statusCode != 200 || response.data is! Map<String, dynamic>) {
      throw Exception('Unexpected response from $normalizedPath');
    }

    return response.data as Map<String, dynamic>;
  }

  /// Request raw bytes from the device. This is used for endpoints that return
  /// binary payloads such as images. A maximum response size is enforced to
  /// avoid OOMs. Returns the raw bytes on success.
  @override
  Future<Uint8List> requestBytes(
    String method,
    String path, {
    Map<String, dynamic>? body,
    Duration? timeout,
    int? maxResponseBytes = 4 * 1024 * 1024, // 4MB default
  }) async {
    if (_currentState != TransportState.connected || _connectedIp == null) {
      throw Exception('Cannot request while disconnected');
    }

    final normalizedPath = path.startsWith('/') ? path : '/$path';
    final options = Options(
      sendTimeout: timeout ?? const Duration(seconds: 5),
      receiveTimeout: timeout ?? const Duration(seconds: 5),
      responseType: ResponseType.bytes,
      validateStatus: (_) => true,
    );

    final response = method.toUpperCase() == 'GET'
        ? await _dio.get('http://$_connectedIp$normalizedPath', options: options)
        : await _dio.post('http://$_connectedIp$normalizedPath', data: body, options: options);

    final contentType = response.headers.value('content-type') ?? '';
    final status = response.statusCode ?? 0;
    final raw = response.data;
    final rawLength = raw is List<int>
        ? raw.length
        : (raw is Uint8List ? raw.length : raw?.toString().length ?? 0);
    debugPrint(
      'transport.bytes: $method $normalizedPath status=$status content-type=$contentType len=$rawLength',
    );

    if (response.statusCode != 200 || response.data == null) {
      throw Exception('Unexpected response from $normalizedPath: ${response.statusCode}');
    }

    // Ensure the server returned an image-like content-type. If not, try to
    // decode payload as UTF8 and include it in the exception to help debugging.
    if (!contentType.toLowerCase().startsWith('image/')) {
      // If the server returned JSON or text, return a helpful error with body
      try {
        final asUtf8 = raw is List<int> ? String.fromCharCodes(raw) : raw.toString();
        throw Exception('Unexpected content-type from $normalizedPath: $contentType, body: $asUtf8');
      } catch (e) {
        throw Exception('Unexpected non-image content from $normalizedPath: $contentType');
      }
    }

    final data = raw is List<int> ? raw : (raw is Uint8List ? raw.toList() : <int>[]);
    if (maxResponseBytes != null && data.length > maxResponseBytes) {
      throw Exception('Response too large: ${data.length} bytes (max $maxResponseBytes)');
    }

    return Uint8List.fromList(data);
  }

  void _updateState(TransportState newState) {
    _currentState = newState;
    _stateController.add(newState);
  }

  void dispose() {
    _stateController.close();
    _incomingController.close();
  }
}
