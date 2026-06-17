enum DeviceType { cane, goggle }

class KnownDevice {
  final String deviceId;
  final String? deviceName;
  final DeviceType deviceType;
  final String? lastKnownIp;
  final int? lastKnownPort;
  final DateTime lastSeenTimestamp;

  const KnownDevice({
    required this.deviceId,
    this.deviceName,
    required this.deviceType,
    this.lastKnownIp,
    this.lastKnownPort,
    required this.lastSeenTimestamp,
  });

  Map<String, dynamic> toJson() => {
        'device_id': deviceId,
        'device_name': deviceName,
        'device_type': deviceType.name,
        'last_known_ip': lastKnownIp,
        'last_known_port': lastKnownPort,
        'last_seen_timestamp': lastSeenTimestamp.toIso8601String(),
      };

  factory KnownDevice.fromJson(Map<String, dynamic> json) {
    return KnownDevice(
      deviceId: json['device_id'] as String,
      deviceName: json['device_name'] as String?,
      deviceType: DeviceType.values.firstWhere(
        (e) => e.name == json['device_type'],
        orElse: () => DeviceType.cane,
      ),
      lastKnownIp: json['last_known_ip'] as String?,
      lastKnownPort: json['last_known_port'] as int?,
      lastSeenTimestamp: DateTime.parse(json['last_seen_timestamp'] as String),
    );
  }
}
