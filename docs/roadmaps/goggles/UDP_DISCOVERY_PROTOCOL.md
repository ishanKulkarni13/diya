# UDP Discovery Protocol Specification

**Version**: 1.0.0  
**Date**: June 19, 2026  
**Status**: Phase 2 - Protocol Design

---

## Overview

This document defines the UDP-based discovery protocol for Diya Smart Goggles (and future WiFi devices).

### Goals
- **Simple**: Minimal packet structure
- **Reliable**: Tolerant of packet loss
- **Compatible**: Works with simulator AND ESP32
- **Future-proof**: Versioned and extensible
- **Observable**: Heavy logging everywhere

### Non-Goals
- ❌ Security (local network only)
- ❌ Encryption (plaintext JSON)
- ❌ Authentication (trust-on-first-use)
- ❌ Guaranteed delivery (UDP is lossy by design)

---

## Protocol Design

### Transport
- **Protocol**: UDP (User Datagram Protocol)
- **Direction**: Broadcast (device → all)
- **Port**: 8888 (configurable)
- **Broadcast Address**: 255.255.255.255 (local network)
- **Encoding**: UTF-8 JSON

### Packet Structure

**Format**: Single-line JSON

**Example**:
```json
{"protocol":"diya-discovery","version":"1.0.0","device_id":"goggle-abc123","device_name":"Diya Smart Goggles","device_type":"goggle","ip":"192.168.1.120","port":9000,"battery":75,"uptime":12345,"timestamp":1718812345678}
```

**Pretty-printed** (for documentation only):
```json
{
  "protocol": "diya-discovery",
  "version": "1.0.0",
  "device_id": "goggle-abc123",
  "device_name": "Diya Smart Goggles",
  "device_type": "goggle",
  "ip": "192.168.1.120",
  "port": 9000,
  "battery": 75,
  "uptime": 12345,
  "timestamp": 1718812345678
}
```

---

## Field Definitions

### Required Fields

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `protocol` | string | Protocol identifier | `"diya-discovery"` |
| `version` | string | Protocol version (semver) | `"1.0.0"` |
| `device_id` | string | Unique device identifier | `"goggle-abc123"` |
| `device_type` | string | Device category | `"goggle"` or `"cane"` |
| `ip` | string | Device IP address | `"192.168.1.120"` |
| `port` | integer | HTTP API port | `9000` |
| `timestamp` | integer | Unix timestamp (ms) | `1718812345678` |

### Optional Fields

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `device_name` | string | Human-readable name | `"Diya Smart Goggles"` |
| `battery` | integer | Battery level (0-100) | `75` |
| `uptime` | integer | Uptime in seconds | `12345` |
| `firmware_version` | string | Firmware version | `"1.0.0"` |
| `capabilities` | array | Device capabilities | `["camera","battery","audio"]` |

---

## Field Semantics

### `protocol`
- **Purpose**: Identify Diya discovery packets
- **Value**: Always `"diya-discovery"`
- **Validation**: Reject packets with different protocol

### `version`
- **Purpose**: Protocol version for backward compatibility
- **Format**: Semantic versioning (major.minor.patch)
- **Current**: `"1.0.0"`
- **Future**: May add fields in minor versions (e.g., 1.1.0)

### `device_id`
- **Purpose**: Unique device identifier for deduplication
- **Format**: Alphanumeric + hyphens
- **Examples**:
  - Simulator: `"sim-goggle-001"`
  - ESP32: `"goggle-<mac-address>"` (e.g., `"goggle-a4b1c2"`)
- **Uniqueness**: Must be stable across reboots

### `device_type`
- **Purpose**: Device category for UI/routing
- **Values**: `"goggle"`, `"cane"`, (future: `"bracelet"`, `"ring"`)
- **Validation**: Must match known types

### `ip`
- **Purpose**: Device's IP address for HTTP connection
- **Format**: IPv4 dotted-decimal
- **Example**: `"192.168.1.120"`
- **Note**: Should match packet source IP (validates packet integrity)

### `port`
- **Purpose**: HTTP API port
- **Type**: Integer (1-65535)
- **Default**: `9000` (simulator), `9000` (ESP32)
- **Example**: `9000`

### `battery`
- **Purpose**: Battery health metric
- **Type**: Integer (0-100)
- **Example**: `75`
- **Note**: Goggles may be hardcoded (USB-powered) or dynamic (battery model)

### `uptime`
- **Purpose**: Distinguish reboot vs. existing device
- **Type**: Integer (seconds since boot)
- **Example**: `12345` (3.4 hours)
- **Use Case**: Detect if device rebooted

### `timestamp`
- **Purpose**: Packet freshness validation
- **Type**: Integer (Unix milliseconds)
- **Example**: `1718812345678`
- **Validation**: Reject packets with future timestamps or very old timestamps

---

## Broadcast Behavior

### Timing

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| **Interval** | 3 seconds | Balance discovery speed vs. network load |
| **Initial Burst** | 3 packets @ 1s | Fast discovery on boot |
| **Ongoing** | 1 packet @ 3s | Maintenance heartbeat |
| **Jitter** | ±500ms | Avoid synchronized broadcasts |

### Algorithm

**Pseudocode**:
```python
async def broadcast_loop():
    # Initial burst (fast discovery)
    for i in range(3):
        send_broadcast()
        await sleep(1)
    
    # Ongoing (maintenance)
    while True:
        send_broadcast()
        await sleep(3 + random.uniform(-0.5, 0.5))  # Jitter
```

### Failure Handling

| Scenario | Behavior |
|----------|----------|
| **Network unavailable** | Log error, retry next interval |
| **Port unavailable** | Log error, continue (no broadcast) |
| **Packet send failure** | Log warning, continue |
| **Device offline** | Stop broadcasting |

---

## Receiver Behavior (Flutter)

### Discovery Service

**Responsibilities**:
1. Bind UDP socket to port 8888
2. Listen for incoming packets
3. Parse JSON
4. Validate schema
5. Emit discovery events
6. Log all activity

### Packet Processing

```
┌─────────────────┐
│ UDP Packet      │
│ (raw bytes)     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ UTF-8 Decode    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ JSON Parse      │
└────────┬────────┘
         │
         ├─Parse Error──►Log + Ignore
         │
         ▼
┌─────────────────┐
│ Schema          │
│ Validation      │
└────────┬────────┘
         │
         ├─Invalid──────►Log + Ignore
         │
         ▼
┌─────────────────┐
│ Emit Event      │
│ to DeviceManager│
└─────────────────┘
```

### Validation Rules

**Required Field Check**:
```dart
bool _validatePacket(Map<String, dynamic> packet) {
  if (packet['protocol'] != 'diya-discovery') return false;
  if (packet['version'] == null) return false;
  if (packet['device_id'] == null || packet['device_id'].isEmpty) return false;
  if (packet['device_type'] == null) return false;
  if (packet['ip'] == null) return false;
  if (packet['port'] == null || packet['port'] < 1) return false;
  if (packet['timestamp'] == null) return false;
  return true;
}
```

**Timestamp Validation**:
```dart
bool _validateTimestamp(int timestamp) {
  final now = DateTime.now().millisecondsSinceEpoch;
  final age = now - timestamp;
  
  // Reject future packets (clock skew tolerance: 5s)
  if (age < -5000) return false;
  
  // Reject very old packets (60s)
  if (age > 60000) return false;
  
  return true;
}
```

### Event Emission

**Format** (matches existing BLE/HTTP format):
```dart
{
  'device_id': 'goggle-abc123',
  'device_type': 'goggle',
  'device_name': 'Diya Smart Goggles',
  'source_ip': '192.168.1.120',
  'port': 9000,
}
```

**Note**: Same format as HTTP /register events → DeviceManager handles identically

---

## Network Configuration

### Port Selection

**UDP Discovery Port**: 8888

**Rationale**:
- Avoid 8080 (HTTP discovery server)
- Avoid 9000 (goggle API)
- Easy to remember (4 eights)
- Unlikely to conflict

### Broadcast Address

**IPv4**: `255.255.255.255`

**Rationale**:
- Local network broadcast
- No routing (stays on LAN)
- Simple (no multicast setup)

**Future Enhancement**: Multicast (239.255.0.1) for better efficiency

### Firewall Considerations

**Devices** (ESP32/Simulator):
- Outbound UDP to 255.255.255.255:8888 (should always work)

**Flutter** (Phone):
- Inbound UDP on 0.0.0.0:8888
- May require permissions (Android)
- May be blocked by firewall (rare on mobile)

---

## Device Lifecycle

### Discovery Flow

```
Device Boot
    │
    ▼
┌──────────────────┐
│ Initial Burst    │
│ 3 packets @ 1s   │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Flutter Receives │
│ Packet           │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ DeviceManager    │
│ Creates Device   │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Connection       │
│ Established      │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Ongoing Broadcasts│
│ 1 packet @ 3s    │
└──────────────────┘
```

### Reconnection Flow

```
Device Offline
    │
    ▼
┌──────────────────┐
│ No broadcasts    │
│ for 30s          │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ DeviceManager    │
│ Marks Offline    │
└────────┬─────────┘
         │
Device Back Online
         │
         ▼
┌──────────────────┐
│ Broadcasts Resume│
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ DeviceManager    │
│ Auto-Reconnects  │
└──────────────────┘
```

### Timeout Logic

**Device TTL**: 30 seconds

**Logic**:
```dart
// Mark device offline if no broadcast for 30s
final lastSeen = device.lastSeenTimestamp;
final age = DateTime.now().difference(lastSeen);

if (age > Duration(seconds: 30)) {
  device.state = ConnectionState.offline;
}
```

**Rationale**:
- 3s broadcast interval = ~10 broadcasts in 30s
- Tolerates 9 consecutive packet losses
- UDP loss rate << 90% on local network

---

## Logging Requirements

### Device Logs (Simulator/ESP32)

**Level**: INFO

**Events**:
```
[UDP] Broadcasting on 255.255.255.255:8888
[UDP] Broadcast sent: 234 bytes
[UDP] Broadcast failed: <error>
[UDP] Broadcast stopped
```

**Metrics**:
- Total broadcasts sent
- Broadcast failures
- Network availability

### Flutter Logs

**Level**: INFO

**Events**:
```
[UDP] Discovery service started on port 8888
[UDP] Received packet from 192.168.1.120 (234 bytes)
[UDP] Parsed device: goggle-abc123 at 192.168.1.120:9000
[UDP] Invalid packet: missing device_id
[UDP] Invalid packet: malformed JSON
[UDP] Invalid packet: protocol mismatch
[UDP] Discovery service stopped
```

**Metrics**:
- Packets received per minute
- Parse errors
- Validation failures
- Unique devices discovered

---

## Example Packets

### Simulator Packet

```json
{
  "protocol": "diya-discovery",
  "version": "1.0.0",
  "device_id": "sim-goggle-001",
  "device_name": "Diya Smart Goggles Simulator",
  "device_type": "goggle",
  "ip": "192.168.1.100",
  "port": 9000,
  "battery": 75,
  "uptime": 12345,
  "timestamp": 1718812345678
}
```

### ESP32 Packet (Future)

```json
{
  "protocol": "diya-discovery",
  "version": "1.0.0",
  "device_id": "goggle-a4b1c2",
  "device_name": "Diya Smart Goggles",
  "device_type": "goggle",
  "ip": "192.168.43.108",
  "port": 9000,
  "battery": 75,
  "uptime": 3456,
  "firmware_version": "1.0.0",
  "timestamp": 1718812345678
}
```

### Minimal Packet (Required Fields Only)

```json
{
  "protocol": "diya-discovery",
  "version": "1.0.0",
  "device_id": "goggle-123",
  "device_type": "goggle",
  "ip": "192.168.1.100",
  "port": 9000,
  "timestamp": 1718812345678
}
```

---

## Error Scenarios

### Invalid Packets

**Malformed JSON**:
```
{protocol:"diya-discovery",device_id:"goggle-123"}  ← Missing quotes
```
**Action**: Log + Ignore

**Missing Required Field**:
```json
{"protocol":"diya-discovery","version":"1.0.0"}  ← Missing device_id
```
**Action**: Log + Ignore

**Wrong Protocol**:
```json
{"protocol":"unknown","device_id":"dev-123"}
```
**Action**: Log + Ignore

**Future Timestamp**:
```json
{"timestamp":9999999999999}  ← Year 2286
```
**Action**: Log + Ignore

**Old Timestamp**:
```json
{"timestamp":1}  ← January 1970
```
**Action**: Log + Ignore

---

## Backward Compatibility

### HTTP /register (Existing)

**Status**: Remains fully functional

**Use Case**:
- Manual registration (debugging)
- Fallback if UDP fails
- Non-discoverable devices (behind NAT)

**Coexistence**:
- DeviceManager handles both UDP and HTTP events
- Deduplication by device_id (no duplicates)
- UDP preferred (automatic), HTTP fallback (manual)

### Migration Path

**V1.0**: Both UDP and HTTP supported  
**V1.1**: UDP primary, HTTP secondary  
**V2.0**: HTTP deprecated but functional  
**V3.0**: HTTP removed (if usage drops to 0%)

---

## Future Protocol Extensions

### V1.1 - Capabilities Field

**Addition**:
```json
{
  "capabilities": ["camera", "battery", "audio", "haptic"]
}
```

**Benefit**: Flutter knows capabilities before connection

### V1.2 - Device Status Field

**Addition**:
```json
{
  "status": "ready" | "busy" | "error" | "offline"
}
```

**Benefit**: Avoid connecting to busy devices

### V2.0 - Multicast Discovery

**Change**: Use multicast group `239.255.0.1` instead of broadcast

**Benefit**: More efficient, better scaling

### V3.0 - Encrypted Packets

**Change**: Add `signature` field for packet authenticity

**Benefit**: Prevent spoofing attacks

---

## Performance Characteristics

### Bandwidth Usage

**Per Device**:
- Packet size: ~250 bytes
- Interval: 3 seconds
- Bandwidth: ~83 bytes/second (~0.7 Kbps)

**10 Devices**:
- Total: ~830 bytes/second (~6.6 Kbps)

**Impact**: Negligible on WiFi networks

### Discovery Latency

**Best Case**: 1 second (immediate broadcast reception)  
**Average Case**: 1.5 seconds (half interval)  
**Worst Case**: 3 seconds (just missed broadcast)

**Initial Burst**: Guarantees discovery within 3 seconds

### Packet Loss Tolerance

**Broadcast Interval**: 3 seconds  
**TTL**: 30 seconds  
**Tolerance**: 90% packet loss (9/10 packets lost)

**Local WiFi**: Packet loss << 5% → Very reliable

---

## Security Considerations

### Threat Model

**In Scope**:
- Local network only
- Trusted WiFi network
- Physical proximity required

**Out of Scope**:
- Internet-exposed discovery
- Untrusted networks
- Remote attacks

### Risks

| Threat | Likelihood | Impact | Mitigation |
|--------|-----------|--------|------------|
| **Spoofing** | MEDIUM | MEDIUM | V3.0: Signed packets |
| **Eavesdropping** | HIGH | LOW | Public WiFi warning |
| **DoS (flood)** | LOW | MEDIUM | Rate limiting |
| **IP Injection** | MEDIUM | LOW | Validate source IP |

### Recommendations

1. **Trust-on-First-Use**: First discovery auto-connects, subsequent require user confirmation
2. **Public WiFi Warning**: Warn users not to use on untrusted networks
3. **Rate Limiting**: Ignore >10 broadcasts/second from same device
4. **Source Validation**: Compare packet `ip` field with source IP

---

## Testing Strategy

### Unit Tests

**Flutter**:
- [ ] Packet parsing (valid packets)
- [ ] Packet parsing (invalid packets)
- [ ] Schema validation
- [ ] Timestamp validation
- [ ] Event emission

**Simulator**:
- [ ] Packet construction
- [ ] JSON serialization
- [ ] Broadcast sending

### Integration Tests

**Flutter ↔ Simulator**:
- [ ] Discovery within 5 seconds
- [ ] Device appears in device list
- [ ] Connection succeeds
- [ ] Reconnection after disconnect

### Network Tests

- [ ] Packet loss simulation
- [ ] Network disconnection/reconnection
- [ ] Multiple devices simultaneously
- [ ] Device IP change (DHCP)

### Performance Tests

- [ ] 1 device: discovery latency
- [ ] 10 devices: discovery latency
- [ ] Bandwidth usage measurement
- [ ] CPU usage measurement

---

## Implementation Checklist

### Protocol Definition
- [x] Define packet schema
- [x] Define required fields
- [x] Define optional fields
- [x] Define validation rules
- [x] Define error handling
- [x] Define logging requirements

### Flutter Implementation
- [ ] Create UdpDiscoveryService
- [ ] Implement socket binding
- [ ] Implement packet parsing
- [ ] Implement validation
- [ ] Implement event emission
- [ ] Add logging
- [ ] Write tests

### Simulator Implementation
- [ ] Create broadcast loop
- [ ] Implement packet construction
- [ ] Add initial burst logic
- [ ] Add ongoing broadcast logic
- [ ] Add logging
- [ ] Test discovery

### Documentation
- [x] Protocol specification (this document)
- [ ] Flutter API documentation
- [ ] Simulator setup guide
- [ ] Firmware requirements (Phase 5)

---

## Conclusion

**Protocol Status**: ✅ **Complete & Ready for Implementation**

**Next Steps**:
1. Implement Flutter UdpDiscoveryService (Phase 3)
2. Implement Simulator UDP Broadcasting (Phase 4)
3. Test end-to-end discovery
4. Document ESP32 firmware requirements (Phase 5)

**Estimated Effort**: 8 hours implementation + 3 hours testing

**Blockers**: None

---

**Status**: ✅ **Phase 2 Complete - Ready for Phase 3 (Flutter Integration)**

**Next Phase**: Implement UdpDiscoveryService in Flutter
