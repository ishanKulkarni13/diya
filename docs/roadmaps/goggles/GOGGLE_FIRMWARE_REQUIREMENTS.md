# Smart Goggle Firmware Requirements - UDP Discovery Edition

**Version**: 2.0.0 (adds UDP Discovery to V1)  
**Date**: June 19, 2026  
**Status**: Requirements Definition

---

## Overview

This document extends the V1 firmware requirements with **UDP-based automatic discovery**.

### Changes from V1
- ✅ Add UDP broadcast functionality
- ✅ Periodic discovery announcements
- ✅ No changes to HTTP API
- ✅ Backward compatible with existing Flutter integration

---

## UDP Discovery Protocol

### Requirements

**MUST**:
- Broadcast UDP packets to `255.255.255.255:8888`
- Follow Diya Discovery Protocol v1.0.0
- Broadcast every 3 seconds (ongoing)
- Initial burst: 3 packets @ 1 second interval
- Include all required fields in packet
- UTF-8 encode JSON packet
- Log all broadcast attempts

**MUST NOT**:
- Break existing HTTP API
- Require phone IP configuration
- Block main loop during broadcasts
- Crash on broadcast failures

---

## Packet Format

### Required Packet Structure

```json
{
  "protocol": "diya-discovery",
  "version": "1.0.0",
  "device_id": "goggle-<mac-address>",
  "device_type": "goggle",
  "ip": "192.168.1.120",
  "port": 9000,
  "battery": 75,
  "uptime": 12345,
  "firmware_version": "2.0.0",
  "timestamp": 1718812345678
}
```

### Field Definitions

| Field | Type | Source | Example |
|-------|------|--------|---------|
| `protocol` | string | Constant | `"diya-discovery"` |
| `version` | string | Constant | `"1.0.0"` |
| `device_id` | string | MAC address | `"goggle-a4b1c2"` |
| `device_type` | string | Constant | `"goggle"` |
| `ip` | string | WiFi.localIP() | `"192.168.1.120"` |
| `port` | integer | Constant | `9000` |
| `battery` | integer | Hardcoded (75) or ADC | `75` |
| `uptime` | integer | millis() / 1000 | `12345` |
| `firmware_version` | string | Constant | `"2.0.0"` |
| `timestamp` | integer | Current time (ms) | `1718812345678` |

### Device ID Generation

**Format**: `goggle-<last-3-bytes-of-mac>`

**Example**:
```cpp
String deviceId = "goggle-" + WiFi.macAddress().substring(9).replace(":", "");
// MAC: A4:CF:12:B1:C2:D3 → device_id: "goggle-b1c2d3"
```

**Requirements**:
- MUST be stable across reboots
- MUST be unique per device
- MUST use lowercase hex

---

## Broadcast Behavior

### Timing

**Initial Burst** (on boot):
```
Boot → Wait 2s → Burst 1 → Wait 1s → Burst 2 → Wait 1s → Burst 3 → Ongoing
```

**Ongoing** (after burst):
```
Broadcast → Wait 3s → Broadcast → Wait 3s → ...
```

### Pseudocode

```cpp
// Global state
unsigned long lastBroadcast = 0;
int burstCount = 0;
bool burstComplete = false;

void loop() {
  unsigned long now = millis();
  
  // Initial burst (first 3 broadcasts)
  if (burstCount < 3) {
    unsigned long interval = burstCount == 0 ? 2000 : 1000;
    if (now - lastBroadcast >= interval) {
      sendUdpBroadcast();
      lastBroadcast = now;
      burstCount++;
      if (burstCount >= 3) {
        burstComplete = true;
        ESP_LOGI("UDP", "Initial burst complete");
      }
    }
  }
  // Ongoing broadcasts (every 3 seconds)
  else {
    if (now - lastBroadcast >= 3000) {
      sendUdpBroadcast();
      lastBroadcast = now;
    }
  }
  
  // Other loop tasks...
}
```

---

## Implementation Details

### UDP Socket Setup

```cpp
#include <WiFiUdp.h>

WiFiUDP udp;
const char* BROADCAST_ADDR = "255.255.255.255";
const int BROADCAST_PORT = 8888;

void setupUdp() {
  // No explicit setup needed for UDP broadcasts
  ESP_LOGI("UDP", "UDP broadcast configured: %s:%d", 
           BROADCAST_ADDR, BROADCAST_PORT);
}
```

### Packet Construction

```cpp
#include <ArduinoJson.h>

String createBroadcastPacket() {
  StaticJsonDocument<512> doc;
  
  doc["protocol"] = "diya-discovery";
  doc["version"] = "1.0.0";
  doc["device_id"] = getDeviceId();
  doc["device_type"] = "goggle";
  doc["ip"] = WiFi.localIP().toString();
  doc["port"] = 9000;
  doc["battery"] = getBatteryLevel();  // 75 or actual
  doc["uptime"] = millis() / 1000;
  doc["firmware_version"] = FIRMWARE_VERSION;
  doc["timestamp"] = getTimestamp();
  
  String output;
  serializeJson(doc, output);
  return output;
}

String getDeviceId() {
  String mac = WiFi.macAddress();
  mac.replace(":", "");
  mac.toLowerCase();
  return "goggle-" + mac.substring(6);  // Last 3 bytes
}

unsigned long long getTimestamp() {
  // V1: Simple implementation (milliseconds since boot)
  // V2: Use NTP for real timestamp
  return millis();
}
```

### Broadcast Sending

```cpp
void sendUdpBroadcast() {
  if (WiFi.status() != WL_CONNECTED) {
    ESP_LOGW("UDP", "Cannot broadcast: WiFi not connected");
    return;
  }
  
  String packet = createBroadcastPacket();
  
  udp.beginPacket(BROADCAST_ADDR, BROADCAST_PORT);
  udp.print(packet);
  int result = udp.endPacket();
  
  if (result == 1) {
    ESP_LOGI("UDP", "Broadcast sent: %d bytes", packet.length());
  } else {
    ESP_LOGE("UDP", "Broadcast failed");
  }
}
```

---

## Error Handling

### Network Errors

| Error | Behavior |
|-------|----------|
| **WiFi disconnected** | Skip broadcast, log warning |
| **UDP send failure** | Log error, continue |
| **JSON serialization failure** | Log error, continue |

### Recovery

**No automatic recovery needed**:
- Next broadcast will retry
- Broadcasts are stateless
- No accumulation of failures

---

## Logging Requirements

### Boot Sequence

```
[UDP] UDP broadcast configured: 255.255.255.255:8888
[UDP] Initial burst: packet 1/3 sent (234 bytes)
[UDP] Initial burst: packet 2/3 sent (234 bytes)
[UDP] Initial burst: packet 3/3 sent (234 bytes)
[UDP] Initial burst complete
```

### Ongoing

```
[UDP] Broadcast sent: 234 bytes
[UDP] Broadcast sent: 234 bytes
```

### Errors

```
[UDP] Cannot broadcast: WiFi not connected
[UDP] Broadcast failed
```

---

## Configuration Constants

```cpp
// config.h
#define FIRMWARE_VERSION "2.0.0"
#define UDP_BROADCAST_ADDR "255.255.255.255"
#define UDP_BROADCAST_PORT 8888
#define UDP_INITIAL_BURST_COUNT 3
#define UDP_INITIAL_BURST_INTERVAL 1000  // ms
#define UDP_ONGOING_INTERVAL 3000        // ms
```

---

## Memory Considerations

### Stack Usage
- JSON document: 512 bytes
- Packet string: ~250 bytes
- Total: ~800 bytes per broadcast

### Heap Usage
- ArduinoJson allocation: minimal (StaticJsonDocument)
- String allocation: ~250 bytes (freed after broadcast)
- No persistent allocations

### Performance Impact
- Broadcast duration: <10ms
- CPU usage: negligible
- Network bandwidth: ~83 bytes/s (ongoing)

---

## Testing Requirements

### Unit Tests
- [ ] Device ID generation (stable, unique)
- [ ] Packet construction (valid JSON)
- [ ] Timestamp generation
- [ ] Battery level reading

### Integration Tests
- [ ] Initial burst (3 packets @ 1s)
- [ ] Ongoing broadcasts (every 3s)
- [ ] WiFi disconnection handling
- [ ] Broadcast failure handling

### Field Tests
- [ ] Discovery from Flutter app
- [ ] Multi-device discovery
- [ ] Network change recovery
- [ ] Long-term stability (24h test)

---

## Dependencies

### Libraries

```cpp
#include <WiFi.h>
#include <WiFiUdp.h>
#include <ArduinoJson.h>  // v6.x or later
```

### PlatformIO

```ini
[env:esp32s3dev]
lib_deps =
    bblanchon/ArduinoJson@^6.21.0
```

---

## Backward Compatibility

### HTTP API (Unchanged)

All existing HTTP endpoints remain functional:
- `GET /health`
- `GET /state`
- `GET /capture`
- `POST /register-phone`
- `POST /command`

### Discovery Methods

**V1**: Manual registration via HTTP POST  
**V2**: Automatic UDP discovery + Manual HTTP (both work)

**Migration**: Seamless - no Flutter changes required

---

## Performance Benchmarks

### Expected Metrics

| Metric | Target | Acceptable | Critical |
|--------|--------|------------|----------|
| **Discovery latency** | <3s | <5s | <10s |
| **Broadcast success rate** | >99% | >95% | >90% |
| **Memory overhead** | <1KB | <2KB | <5KB |
| **CPU overhead** | <1% | <5% | <10% |

---

## Future Enhancements (V3)

### NTP Time Sync
- Real timestamps instead of uptime
- Synchronized across devices

### Capabilities Field
```json
{
  "capabilities": ["camera", "battery", "audio", "haptic"]
}
```

### Adaptive Broadcast Rate
- Fast discovery: 1s for first 30s
- Maintenance: 5s after connection

### Multicast Support
- Use `239.255.0.1` instead of broadcast
- More efficient for larger networks

---

## Button Events (V1 Requirements - Unchanged)

### Button Detection

**Firmware Responsibility**:
- Detect button press/release
- Measure press duration
- Classify event type (single/double/long)
- Publish event (store in state)

**Flutter Responsibility**:
- Poll `/state` for button events
- Decide action (trigger Assist, SOS, etc.)
- Acknowledge event

### Event Types

| Event | Trigger | Duration |
|-------|---------|----------|
| Single Press | One tap | <1000ms, no second press |
| Double Press | Two taps | Both <1000ms, within 400ms |
| Long Press | Hold | ≥1000ms |

### Event JSON

```json
{
  "button_events": [
    {
      "button": "assist",
      "event": "single_press",
      "timestamp": 123456
    }
  ]
}
```

**Note**: Events stored in device state, accessible via `GET /state`

---

## Camera Requirements (V1 Requirements - Unchanged)

### Resolution
- **Target**: 1024x768 (XGA)
- **Sensor**: OV5640
- **JPEG Quality**: 12 (0-63 scale, lower = better)

### Capture Behavior
- Always fresh capture (no caching)
- JPEG magic byte validation (0xFF 0xD8)
- Retry on failure (up to 2 times)
- Automatic recovery after 5 consecutive failures

### Endpoint
- `GET /capture` → Returns JPEG bytes

---

## Telemetry Requirements (V1 Requirements - Unchanged)

### Collected Metrics

| Metric | Source | Update |
|--------|--------|--------|
| `battery` | Hardcoded (75) | Static |
| `wifi_rssi` | WiFi.RSSI() | 1s |
| `uptime` | millis() | Real-time |
| `heap_free` | ESP.getFreeHeap() | 1s |
| `camera` | Camera status | Real-time |
| `ip` | WiFi.localIP() | Real-time |
| `captures` | Counter | Real-time |

### Endpoint
- `GET /state` → Returns telemetry JSON

---

## Connection Lifecycle

### Device States

```
Boot
  │
  ▼
WiFi Connecting
  │
  ▼
UDP Broadcasting ─────► Flutter Discovers
  │                           │
  │                           ▼
  │                     Connection Attempt
  │                           │
  │                           ▼
  └───────────────────► Connected & Ready
```

### Health Checks

**Broadcast-based** (V2):
- Flutter marks device offline if no broadcast for 30s
- No polling needed

**HTTP-based** (V1 - still supported):
- Flutter polls `GET /health` every 10s
- Timeout indicates offline

---

## Security Considerations

### Threat Model

**In Scope**:
- Local network only
- Trusted WiFi
- Physical proximity

**Out of Scope**:
- Internet exposure
- Untrusted networks
- Remote attacks

### Mitigations

**V2** (Current):
- No authentication
- No encryption
- Trust-on-first-use model

**V3** (Future):
- Signed packets (HMAC)
- TLS for HTTP API
- Device pairing

---

## Implementation Checklist

### Core UDP Discovery
- [ ] Add WiFiUdp library
- [ ] Add ArduinoJson library
- [ ] Implement device ID generation
- [ ] Implement packet construction
- [ ] Implement broadcast sending
- [ ] Add initial burst logic
- [ ] Add ongoing broadcast loop
- [ ] Add WiFi state checking
- [ ] Add error handling
- [ ] Add logging

### Integration
- [ ] Integrate with main loop
- [ ] Test with existing HTTP API
- [ ] Verify backward compatibility
- [ ] Test with Flutter app

### Testing
- [ ] Unit tests
- [ ] Integration tests
- [ ] Field tests
- [ ] Performance tests
- [ ] Long-term stability tests

### Documentation
- [x] Requirements document (this file)
- [ ] Implementation guide
- [ ] Testing guide
- [ ] Troubleshooting guide

---

## Success Criteria

### Functional
- ✅ Goggles broadcast UDP packets
- ✅ Flutter discovers goggles automatically
- ✅ Discovery within 5 seconds
- ✅ Backward compatible (HTTP still works)
- ✅ Stable over 24 hours

### Non-Functional
- ✅ Memory overhead <2KB
- ✅ CPU overhead <5%
- ✅ Broadcast success rate >95%
- ✅ No crashes or reboots

---

## References

### Related Documents
- [UDP Discovery Protocol](./UDP_DISCOVERY_PROTOCOL.md)
- [UDP Discovery Audit](./UDP_DISCOVERY_AUDIT.md)
- [Goggle Firmware V1](./GOGGLE_FIRMWARE_V1.md)

### External Standards
- [RFC 768 - User Datagram Protocol](https://tools.ietf.org/html/rfc768)
- [RFC 919 - Broadcasting Internet Datagrams](https://tools.ietf.org/html/rfc919)
- [ArduinoJson Documentation](https://arduinojson.org/)

---

**Status**: ✅ **Requirements Complete - Ready for Implementation**

**Version**: 2.0.0  
**Estimated Effort**: 4 hours implementation + 2 hours testing

**Next Steps**:
1. Update ESP32 firmware V1 codebase
2. Add UDP broadcast functionality
3. Test with Flutter app
4. Field test discovery
5. Performance benchmarking
