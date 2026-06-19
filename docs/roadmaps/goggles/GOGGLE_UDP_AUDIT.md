# Smart Goggle — UDP & ESP32-S3 Readiness Audit

**Date**: 2026-06-19  
**Branch**: `feat/goggle-udp-audit`  
**Auditor**: Staff-engineer read-only audit  
**Source of truth**: Code. Documentation treated as supplementary.

---

## Quick-Reference Summary Table

| Area | Status | Score |
|---|---|---|
| Flutter goggle architecture | Complete, clean | 9/10 |
| Simulator HTTP API | Production-ready | 9/10 |
| Simulator UDP broadcasting | **Already implemented** | 9/10 |
| ESP32-S3 firmware (HTTP) | **Already implemented** | 8/10 |
| ESP32-S3 firmware (UDP) | **Missing — not yet added** | 0/10 |
| Flutter UDP listener | **Missing** | 0/10 |
| DeviceManager UDP wiring | **Missing** | 0/10 |
| Goggle → Assist (camera source) | Missing — phone camera hardcoded | 0/10 |
| Button events → Flutter | Not consumed (polling gap) | 2/10 |
| Documentation | Extensive, mostly accurate | 8/10 |

---

## Section 1 — Current Goggle Architecture

### 1.1 DeviceManager

**File**: `apps/flutter/lib/core/hardware/infrastructure/manager/device_manager_impl.dart`

`DeviceManagerImpl` is the single owner of device lifecycle. It holds:
- `DeviceRegistry` — SharedPreferences-backed store of `KnownDevice` records
- `AdapterFactory` — creates `SmartCaneAdapter` (BLE) or `SmartGoggleAdapter` (HTTP)
- `DeviceDiscoveryServer` — HTTP server on port 8080, receives `POST /register`
- `BleDiscoveryService` — BLE UUID scan for the Smart Cane

`startScan()` does two things: restores known devices from the registry and starts a BLE scan. There is **no UDP subscription here**. Goggles currently discover by making an outbound HTTP POST to the phone, not by being listened for.

`_handleDiscoveryEvent()` accepts a `Map<String, dynamic>` and saves a `KnownDevice`, then calls `_triggerConnection()`. This handler is transport-agnostic — it does not care whether the event originated from BLE, HTTP, or (future) UDP. This is the key extension point.

**Does Flutter support dynamic devices?** Yes. `_activeDevices` is a `Map<String, BaseDevice>` populated at runtime. New devices are created on-demand without restarting anything.

**Does Flutter support reconnect?** Yes, via `ConnectionCoordinator` (exponential backoff 1s→3s→5s→10s→30s, heartbeat timeout). For goggles specifically the HTTP transport has no heartbeat, but `retryConnection()` is manually callable and the debug UI exposes it.

### 1.2 DeviceRegistry and KnownDevice

**File**: `apps/flutter/lib/core/hardware/domain/manager/device_registry.dart`  
**Impl**: `apps/flutter/lib/core/hardware/infrastructure/manager/shared_prefs_device_registry.dart`

```dart
class KnownDevice {
  final String deviceId;
  final String? deviceName;
  final DeviceType deviceType;   // goggle | cane
  final String? lastKnownIp;
  final int? lastKnownPort;
  final DateTime lastSeenTimestamp;
}
```

The schema already stores `lastKnownIp` and `lastKnownPort`, which is exactly what UDP discovery will provide. No schema changes are needed. `saveKnownDevice()` upserts by `deviceId`, so repeated UDP packets from the same device simply update the IP/timestamp in place.

**Gap**: There is no TTL/expiry. A goggle that was seen six months ago still appears in the known-devices list.

### 1.3 AdapterFactory

**File**: `apps/flutter/lib/core/hardware/infrastructure/manager/adapter_factory.dart`

```dart
if (deviceType == 'goggle') {
  final transport = HttpTransportImpl(_dio);
  return SmartGoggleAdapter(deviceId, transport, _eventBus);
} else if (deviceType == 'cane') {
  final transport = BleTransportImpl();
  final coordinator = ConnectionCoordinator(...);
  return SmartCaneAdapter(deviceId, coordinator, _eventBus);
}
```

The factory is already bifurcated on device type. UDP discovery will emit `device_type: 'goggle'`, which routes correctly to `SmartGoggleAdapter` without any factory changes.

### 1.4 EventBus and EventArbitrator

**Files**: `domain/messaging/event_bus.dart`, `event_arbitrator.dart`, `event_router.dart`

`HardwareEventBusImpl` is a `StreamController.broadcast()`. Any adapter can publish to it. `EventRouter` buffers events in a 250ms window and runs `EventArbitrator.resolve()`, selecting the highest-priority winner. SOS bypasses the buffer entirely.

`UltrasonicDetectionEvent` already exists in `hardware_event.dart` and flows through this pipeline. When the goggle sends ultrasonic push events to `DeviceDiscoveryServer /events/ultrasonic`, `DeviceManagerImpl._handleSensorEvent()` publishes a `UltrasonicDetectionEvent` to the bus. This path is already functional.

### 1.5 SmartGoggleAdapter and Capabilities

**File**: `apps/flutter/lib/core/hardware/infrastructure/adapters/smart_goggle_adapter.dart`

Capabilities exposed:
- `CameraCapability.capture()` → `GET /capture` → validates JPEG magic bytes (0xFF 0xD8) → `Uint8List`
- `BatteryCapability.pullBatteryLevel()` → `GET /state` → `battery_level` integer

Connection: `connect(String address)` calls `HttpTransportImpl.connect()` which fires `GET /health`. If 200, state becomes `TransportState.connected`.

The adapter does **not** consume button events from the goggle. Buttons are stored in the firmware's internal state and would require polling `GET /state` for a `button_events` array, or a push mechanism. Neither is currently wired.

### 1.6 Capture Source — Critical Gap

**File**: `apps/flutter/lib/features/assist/providers/assist_providers.dart`

```dart
final imageCapturePortProvider = Provider<ImageCapturePort>((ref) {
  return ImagePickerAdapter();  // ← phone camera, always
});
```

The goggle's `CameraCapability` is never reached from Assist. The `AssistPipeline` only knows `ImageCapturePort`, which is always bound to the phone camera. There is no arbitration layer, no user preference, and no fallback. This is a **design gap**, not a bug — the architecture is intentional for Phase 1, but it means goggles cannot yet contribute to Assist.

---

## Section 2 — Simulator Audit

**Files**: `hardware/smart-goggles/simulator/app/main.py`, `state.py`, `logging.py`

### 2.1 Routes

| Route | Method | Status | Notes |
|---|---|---|---|
| `/` | GET | ✅ | HTML web UI |
| `/health` | GET | ✅ | `{status, device_id, connected, uptime_s}` |
| `/state` | GET | ✅ | Full state + telemetry |
| `/state` | POST | ✅ | Update battery, ultrasonic, fps, hz |
| `/capture` | GET/POST | ✅ | Real webcam JPEG or red fallback |
| `/register-phone` | POST | ✅ | Stores phone IP, POSTs to phone /register |
| `/command` | POST | ✅ | Acks command, updates `last_command` |
| `/sos` | POST | ✅ | Forwards SOS to phone `/sos` |
| `/logs` | GET | ✅ | Last 200 log entries |
| `/stream` | GET | ✅ (stub) | SSE PNG placeholder, not real webcam |
| `/telemetry` | GET | ✅ | SSE battery/ultrasonic/connected |

### 2.2 UDP Broadcasting — Already Implemented

**Critical finding**: The simulator already broadcasts UDP. This was not apparent from documentation alone.

```python
# hardware/smart-goggles/simulator/app/main.py
UDP_DISCOVERY_PORT = 8888
UDP_DISCOVERY_INTERVAL = 3.0  # seconds
UDP_BROADCAST_ADDRESS = "255.255.255.255"
UDP_INITIAL_BURST_COUNT = 3
UDP_INITIAL_BURST_INTERVAL = 1.0  # seconds
```

The `_udp_broadcast_loop()` coroutine starts at application lifespan startup via `asyncio.create_task()`. It sends an initial burst of 3 packets at 1-second intervals, then sends one packet every ~3 seconds with ±0.5s jitter.

**Broadcast packet produced by the simulator**:
```json
{
  "protocol": "diya-discovery",
  "version": "1.0.0",
  "device_id": "GOGGLE-SIM-001",
  "device_name": "Diya Smart Goggles Simulator",
  "device_type": "goggle",
  "ip": "192.168.x.x",
  "port": 9000,
  "battery": 92,
  "uptime": 12345,
  "timestamp": 1718812345678
}
```

`_get_local_ip()` uses a non-routed DNS socket trick to detect the real interface IP:
```python
with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
    s.connect(("8.8.8.8", 80))
    return s.getsockname()[0]
```

**The simulator is ready. Flutter is the missing half.**

### 2.3 Simulator Self-Announcement

The simulator does NOT automatically call `/register-phone`. It waits for the user to provide a phone IP either via the web UI or directly via `POST /register-phone`. UDP discovery was added precisely to eliminate this requirement. Once Flutter has a `UdpDiscoveryService` listening on port 8888, the simulator will be discovered with zero manual steps.

### 2.4 State

**File**: `hardware/smart-goggles/simulator/app/state.py`

```python
@dataclass
class SimulatorState:
    device_id: str = "GOGGLE-SIM-001"
    connected: bool = False
    phone_ip: str | None = None
    phone_port: int = 8080
    battery_level: int = 92
    ultrasonic_cm: float = 120.0
    stream_fps: int = 8
    telemetry_hz: float = 2.0
```

Default battery is 92 (not 75 — firmware uses 75). This is a minor inconsistency between simulator and firmware default but has no functional impact.

`LogBuffer` maintains a deque of the last 200 log entries, exposed via `GET /logs`.

---

## Section 3 — UDP Readiness Audit (Flutter)

### 3.1 Socket Support

Dart's `dart:io` provides `RawDatagramSocket`, which supports UDP. There is **no third-party library needed**. The pattern is:

```dart
final socket = await RawDatagramSocket.bind(InternetAddress.anyIPv4, 8888);
socket.broadcastEnabled = true;  // receive broadcasts
socket.listen((event) {
  if (event == RawSocketEvent.read) {
    final datagram = socket.receive();
    // parse datagram.data
  }
});
```

This is available on Android and iOS without additional plugins.

### 3.2 Existing Discovery Hooks

`DeviceManagerImpl.startScan()` already subscribes to `BleDiscoveryService.scan()` via:

```dart
_bleDiscoverySubscription = _bleDiscoveryService.scan().listen(_handleDiscoveryEvent);
```

`_handleDiscoveryEvent()` accepts `Map<String, dynamic>` in exactly the format a UDP packet would produce:
```dart
{
  'device_id': '...',
  'device_type': 'goggle',
  'device_name': '...',
  'source_ip': '192.168.x.x',
  'port': 9000,
}
```

Adding UDP discovery is two lines in `startScan()` and two lines in `stopScan()`. **No other DeviceManager changes are needed.**

### 3.3 Network Abstractions

`DeviceDiscoveryServer` already uses raw `dart:io` `HttpServer`. There are no wrappers or framework dependencies on the discovery layer. Adding a `UdpDiscoveryService` alongside it follows the same pattern.

The `BleDiscoveryService` class is the precise template to mirror:
```dart
class BleDiscoveryService {
  final String serviceUuid;
  BleDiscoveryService(this.serviceUuid);
  Stream<Map<String, dynamic>> scan() { ... }
}
```

`UdpDiscoveryService` should have the same shape:
```dart
class UdpDiscoveryService {
  final int port;
  UdpDiscoveryService(this.port);
  Stream<Map<String, dynamic>> scan() { ... }
}
```

### 3.4 Strengths

- `_handleDiscoveryEvent()` is already transport-agnostic
- `KnownDevice` already has `lastKnownIp` and `lastKnownPort`
- `AdapterFactory` already routes `device_type: 'goggle'` correctly
- Duplicate protection: `saveKnownDevice()` upserts by `deviceId`
- No schema changes needed anywhere

### 3.5 Weaknesses

- No `UdpDiscoveryService` exists yet — nothing is listening on port 8888
- No Android permission declared for `CHANGE_WIFI_MULTICAST_STATE` (needed for broadcast reception on some Android versions)
- No device TTL logic — stale entries accumulate in the registry
- `DeviceDiscoveryServer` SOS stream (`_sosEventController`) is never consumed by `DeviceManagerImpl` — this is a pre-existing bug unrelated to UDP

### 3.6 Risks

- **Android WiFi restrictions**: Some Android 10+ devices restrict UDP broadcast reception unless `WifiManager.MulticastLock` is acquired. The app must hold a multicast lock while scanning.
- **iOS local network permission**: iOS 14+ requires the `NSLocalNetworkUsageDescription` plist key and user consent before UDP sockets can receive LAN traffic.
- **Hotspot network topology**: When the phone hosts a hotspot, broadcast packets may not loop back to the phone depending on the kernel's hotspot bridge configuration. This must be tested on real hardware.

---

## Section 4 — ESP32-S3 Firmware Readiness

**Location**: `hardware/smart-goggles/firmware/`  
**Toolchain**: PlatformIO + Arduino framework  
**Build config**: `hardware/smart-goggles/firmware/platformio.ini`

### 4.1 Board Configuration

```ini
[env:esp32-s3-devkitc-1]
platform = espressif32
board = esp32-s3-devkitc-1
framework = arduino
build_flags =
    -DBOARD_HAS_PSRAM
    -mfix-esp32-psram-cache-issue
    -DARDUINO_USB_CDC_ON_BOOT=1
lib_deps =
    ArduinoJson@^7.0.0
    esp32-camera@^2.0.0
    AsyncTCP@^1.1.1
    ESPAsyncWebServer@^1.2.3
```

Board is correct for ESP32-S3. PSRAM is enabled. Camera library included. **WiFiUDP is not listed** — it is part of the ESP32 Arduino core (no explicit lib_dep needed), but `WiFiUdp.h` is not yet imported anywhere in the source.

### 4.2 HTTP Server — Implemented

`hardware/smart-goggles/firmware/src/http_server.h` implements all simulator-compatible endpoints:

| Endpoint | Implementation |
|---|---|
| `GET /` | HTML info page |
| `GET /health` | `{status, device_id, connected, uptime_s}` |
| `GET /state` | Full state + telemetry via `Telemetry::toJson()` |
| `GET /capture` | `CameraManager::capture()` → JPEG bytes with magic validation |
| `POST /register-phone` | Parses JSON, stores phone IP, POSTs to `http://phone:8080/register` |
| `POST /command` | Acks command |

### 4.3 Camera — Implemented

`hardware/smart-goggles/firmware/src/camera_manager.h`

- OV5640 pin assignments match documented wiring exactly
- Resolution: `FRAMESIZE_XGA` (1024×768)
- JPEG quality: 12 (lower = better)
- Double buffering (`fb_count = 2`, `CAMERA_GRAB_LATEST`)
- Auto-retry with re-init after 5 consecutive failures
- JPEG magic byte validation (0xFF 0xD8) before returning frame
- Sensor settings tuned for text readability (AWB, AEC, WPC, LEN)

### 4.4 Button Manager — Implemented

`hardware/smart-goggles/firmware/src/button_manager.h`

- GPIO 21 (Assist), GPIO 47 (SOS) — INPUT_PULLUP, active-LOW
- Debounce: 50ms
- Events: `single_press` (default), `double_press` (within 400ms window), `long_press` (≥1000ms)
- Event published via `publishEvent()` which fills a `StaticJsonDocument<256>`
- Event payload:
  ```json
  {"type":"button","button":"assist","event":"single_press","timestamp":12345}
  ```
- `hasNewEvent` flag — events are **stored**, not pushed

**Critical gap**: Firmware stores button events internally but never POSTs them to the phone. Flutter has no mechanism to consume them. The only path would be Flutter polling `GET /state` for a `button_events` array, but `handleGetState()` does not include button events in the response. The `getEventsJson()` method in `ButtonManager` exists but is empty:
```cpp
void getEventsJson(JsonArray& events) {
    // Return recent button events (for /state endpoint)
    // Currently just returns status - could be extended
}
```
**Buttons are fully detected by the firmware but never delivered to Flutter.**

### 4.5 Telemetry — Implemented

`hardware/smart-goggles/firmware/src/telemetry.h`

- WiFi RSSI: `WiFi.RSSI()` updated every 1s
- Heap free: `ESP.getFreeHeap()` updated every 1s
- Heap min: `ESP.getMinFreeHeap()`
- Battery: hardcoded `BATTERY_LEVEL_HARDCODED = 75`
- Uptime, capture count, capture failures all tracked

### 4.6 Device State and ID — Implemented

`hardware/smart-goggles/firmware/src/device_state.h`

Device ID generated from MAC address:
```cpp
deviceId = String(DEVICE_TYPE) + "-" + 
           String(mac[3], HEX) + String(mac[4], HEX) + String(mac[5], HEX);
// → "goggle-b1c2d3"
```
Stable across reboots. Unique per device. Matches the format documented in `UDP_DISCOVERY_PROTOCOL.md`.

### 4.7 WiFi Reconnect — Implemented

```cpp
// In loop():
if (WiFi.status() != WL_CONNECTED) {
    static unsigned long lastReconnectAttempt = 0;
    if (millis() - lastReconnectAttempt > WIFI_RECONNECT_INTERVAL_MS) {  // 5000ms
        WiFi.reconnect();
    }
}
```

Simple 5-second retry. No exponential backoff. Sufficient for V1.

### 4.8 UDP Broadcasting — NOT Implemented

The firmware has **zero UDP code**. No `WiFiUdp.h` include. No broadcast loop. No packet construction. The simulator has this fully implemented; the firmware does not.

This is the primary missing piece for the firmware.

---

## Section 5 — Target Architecture Evaluation

### 5.1 Proposed Flow

```
ESP broadcasts UDP → Simulator broadcasts UDP
        ↓
Flutter UdpDiscoveryService listens on port 8888
        ↓
Parses packet → emits Map<String, dynamic>
        ↓
DeviceManagerImpl._handleDiscoveryEvent()
        ↓
Upserts KnownDevice (IP, port, timestamp)
        ↓
AdapterFactory.createAdapter(deviceType: 'goggle')
        ↓
SmartGoggleAdapter + HttpTransportImpl
        ↓
CaptureSource (future) chooses Goggle vs Phone
        ↓
Assist remains unchanged
```

### 5.2 Fit Assessment

**Perfect fit for most of the chain.** The only entirely missing components are:

1. `UdpDiscoveryService` (Flutter) — ~80 lines of Dart
2. Provider registration for `UdpDiscoveryService`
3. Two lines in `DeviceManagerImpl.startScan()` / `stopScan()`
4. UDP broadcast loop in ESP32 firmware — ~60 lines of C++
5. `CaptureSource` arbitration layer — not part of this sprint per instructions

**No existing abstractions need to be broken.** The event format emitted by the UDP service is identical to what `DeviceDiscoveryServer` already emits. `_handleDiscoveryEvent()` already handles it.

### 5.3 Potential Conflicts

| Conflict | Risk | Resolution |
|---|---|---|
| Device discovered via both UDP and HTTP `/register` | Low — same `device_id` → upsert, no duplicate | Already handled by registry |
| Port 8888 conflicts with existing services | None — 8080 (HTTP server), 9000 (goggle), 8888 (UDP) | All distinct |
| UDP fails silently on Android | Medium | Log errors, fall back to HTTP register |
| Multiple phones receiving same broadcast | None — each phone discovers independently | Stateless broadcasts |
| IP changes on DHCP renewal | Low — next UDP packet updates registry | Already handled by upsert |
| Hotspot broadcast loopback | Unknown — requires physical test | Test with real Android device |

### 5.4 Existing Abstractions That Can Be Reused

- `_handleDiscoveryEvent()` — reuse without modification
- `KnownDevice` schema — reuse without modification
- `AdapterFactory` — reuse without modification
- `SmartGoggleAdapter` — reuse without modification
- `HttpTransportImpl` — reuse without modification
- `DeviceDiscoveryServer` — keep running alongside UDP (backward compatibility)
- `BleDiscoveryService` — use as template for `UdpDiscoveryService`

---

## Section 6 — Firmware Requirements Assessment

### 6.1 Existing Documentation

All five documents already exist in `docs/roadmaps/goggles/`:

| Document | Status | Accuracy vs Code |
|---|---|---|
| `GOGGLE_FIRMWARE_V1.md` | Complete | Accurate — firmware matches |
| `GOGGLE_FIRMWARE_REQUIREMENTS.md` | Complete | Accurate — covers UDP V2 requirements |
| `UDP_DISCOVERY_PROTOCOL.md` | Complete | Accurate — packet schema matches simulator |
| `UDP_DISCOVERY_AUDIT.md` | Complete | Accurate — architecture analysis correct |
| `GOGGLE_INTEGRATION_AUDIT.md` | Complete | Partially outdated — firmware now exists but audit says it doesn't |
| **`GOGGLE_UDP_AUDIT.md`** | **This document** | — |

### 6.2 Gaps in Existing Documentation

1. `GOGGLE_INTEGRATION_AUDIT.md` states "NO firmware directory" — this was accurate at time of writing but firmware now exists at `hardware/smart-goggles/firmware/`. The audit is stale on hardware status.

2. `GOGGLE_FIRMWARE_REQUIREMENTS.md` documents the UDP V2 requirements in full but the firmware codebase does not yet implement them.

3. No document describes the **button event delivery gap** — firmware detects button presses but never delivers them to Flutter.

4. No document describes the **Android multicast lock requirement** for UDP reception.

5. No testing guide for the UDP path exists yet.

---

## Section 7 — Recommendations

### 7.1 UDP Packet Schema (Confirmed — Match Simulator Exactly)

The simulator already emits a well-formed packet. The firmware and Flutter must use the identical schema. No changes to the schema are needed.

**Canonical packet**:
```json
{
  "protocol": "diya-discovery",
  "version": "1.0.0",
  "device_id": "goggle-b1c2d3",
  "device_name": "Diya Smart Goggles",
  "device_type": "goggle",
  "ip": "192.168.43.108",
  "port": 9000,
  "battery": 75,
  "uptime": 3456,
  "timestamp": 1718812345678
}
```

`firmware_version` is optional but recommended. Flutter must ignore unknown fields (forward-compatible). Flutter must reject any packet missing `protocol`, `device_id`, `device_type`, `ip`, or `port`.

### 7.2 Discovery Intervals

| Phase | Interval | Count | Rationale |
|---|---|---|---|
| Initial burst | 1s | 3 packets | Fast pickup on app open |
| Ongoing | 3s ± 0.5s jitter | ∞ | Maintenance heartbeat |

**Firmware implementation note**: Use `millis()` non-blocking timers in `loop()`. Do not use `delay()`. The existing `main.cpp` has a `delay(10)` at the end of `loop()` — the UDP timer logic must account for this.

### 7.3 Reconnect Strategy

**Current state**: `ConnectionCoordinator` handles cane reconnect with backoff (1→3→5→10→30s). Goggle reconnect works differently — `HttpTransportImpl` has no heartbeat; the coordinator's heartbeat timeout is cane-specific (BLE). For the goggle, UDP broadcasts serve as the liveness signal.

**Recommendation**:  
- Flutter: When a goggle's `lastSeenTimestamp` is >30 seconds old, mark the device as `HardwareConnectionState.degraded` and call `retryConnection()`.  
- This does not require a full foreground service — a `Timer.periodic` in `DeviceManagerImpl` checking UDP freshness is sufficient for now.
- Do not change `ConnectionCoordinator` — it is cane-specific.

### 7.4 Health Checks

**Current**: `DebugGoggleService.ping()` calls `GET /health`. This is manual, debug-only.

**Recommendation**:  
- Primary liveness: UDP broadcast presence (no broadcast for 30s = offline).
- Secondary: `GET /health` on reconnect attempt before declaring the device available.
- Do not add a periodic `GET /health` poll — it adds unnecessary HTTP traffic when UDP is working.

### 7.5 Button Semantics

**Firmware implements**: `single_press`, `double_press`, `long_press` on both `assist` (GPIO 21) and `sos` (GPIO 47) buttons.

**Flutter should interpret**:

| Button | Event | Flutter Action |
|---|---|---|
| `assist` | `single_press` | Trigger Assist (same as BLE button1 short) |
| `assist` | `double_press` | Reserved (future: switch camera source) |
| `assist` | `long_press` | Reserved (future: STT) |
| `sos` | `single_press` | SOS trigger via `sosIngressServiceProvider` |
| `sos` | `long_press` | Confirm SOS (bypass debounce) |

**Firmware responsibility**: Detect and classify. Flutter responsibility: decide action.

**Delivery gap to fix**: Firmware must either:
- (A) Push button events to phone via `POST http://phone:8080/events/button` — requires `DeviceDiscoveryServer` to add a `/events/button` endpoint, or
- (B) Include `button_events: [...]` array in `GET /state` response and have Flutter poll — simpler but adds latency.

Option A is preferred for responsiveness. Option B is acceptable for V1 given the phone polls state every 2 seconds in the debug UI.

### 7.6 Capture Strategy

**Current**: Flutter's `CameraCapability.capture()` calls `GET /capture` and validates JPEG magic bytes. This works correctly for both simulator and firmware.

**Recommendation for Assist integration** (future sprint, not this one):  
Create a `GoggleCaptureAdapter implements ImageCapturePort` that wraps `CameraCapability.capture()` and converts the `Uint8List` to a temp `File`. Wire `imageCapturePortProvider` to return this when a goggle is connected. The `AssistPipeline` requires zero changes.

### 7.7 Phone Fallback

When the goggle is disconnected or capture fails, Assist should fall back to the phone camera. The recommended logic:

```
If goggle is in HardwareConnectionState.ready → use GoggleCaptureAdapter
Else → use ImagePickerAdapter (phone camera)
```

This is a single conditional in `imageCapturePortProvider`. No pipeline changes.

### 7.8 Failure Recovery

| Failure | Current Behavior | Recommended |
|---|---|---|
| WiFi drop on goggle | Firmware retries every 5s, UDP stops | Flutter marks degraded after 30s, retries HTTP connect |
| Camera init failure | Firmware retries up to 3 times, continues | Flutter `CameraCapability.capture()` returns null, publishes `HardwareErrorEvent` ✅ |
| `/capture` returns invalid JPEG | Flutter validates magic bytes, writes diagnostic, returns null ✅ | Already handled |
| Goggle reboots | New UDP burst → Flutter re-discovers automatically | No action needed once UDP listener exists |
| Phone-side UDP port busy | UDP bind fails | Log error, fall back to HTTP /register only |

### 7.9 Logging

**Simulator** already logs at structured INFO level via Python `logging` + `pythonjsonlogger`. Every UDP broadcast logged.

**Firmware** already logs to Serial at 115200 baud with `[TAG]` prefixes. All camera, button, and WiFi events logged.

**Flutter** — add these logs in `UdpDiscoveryService`:
```
[UDP] Discovery service started on 0.0.0.0:8888
[UDP] Packet received from 192.168.x.x (234 bytes)
[UDP] Parsed device: goggle-b1c2d3 at 192.168.x.x:9000
[UDP] Invalid packet from 192.168.x.x: missing device_id
[UDP] Discovery service stopped
```

### 7.10 Simulator Parity

The simulator is ahead of the firmware on UDP. Once firmware adds UDP, the two will be in parity on all V1 features. The remaining gap is:

| Feature | Simulator | Firmware |
|---|---|---|
| UDP broadcasting | ✅ | ❌ (missing) |
| Battery (real) | ❌ (hardcoded 92) | ❌ (hardcoded 75) |
| Button push events | ❌ (web UI simulates) | ❌ (detected, not pushed) |
| SSE frame stream | ✅ (stub) | ❌ |
| SSE telemetry stream | ✅ | ❌ |
| Audio output | ❌ | ❌ |

Both are at the same level for V1. Neither has audio. Neither pushes button events. Both use hardcoded battery.

---

## Section 8 — Architecture Observations

### 8.1 The Discovery Server SOS Stream is Dead Code

`DeviceDiscoveryServer` emits `_sosEventController` events when `POST /sos` is received. `DeviceManagerImpl` subscribes to `_discoveryServer.onDeviceRegistered` and `_discoveryServer.onSensorEvent` but **never subscribes to `onSosEvent`**. Any SOS sent from a goggle via HTTP to the phone is silently dropped. This is a pre-existing bug independent of UDP.

### 8.2 The HTTP Transport Has No Heartbeat

`HttpTransportImpl` has no `ConnectionCoordinator`. Its `state` stream only emits during explicit `connect()` and `disconnect()` calls. A goggle that goes offline does not automatically transition to `disconnected` — the adapter's state stays `ready` indefinitely until the next operation fails. For a cane this is handled by BLE disconnect events and heartbeat timeouts. For goggles, UDP presence is the only liveness signal once UDP is implemented.

### 8.3 `DebugGoggleService` Creates a Parallel Adapter

`DebugGoggleService._ensureSession()` creates its own `SmartGoggleAdapter` instances separate from `DeviceManagerImpl._activeDevices`. This means the debug screen and the production path maintain independent HTTP connections to the same device. This is safe for HTTP but means battery and telemetry reads from the debug screen do not flow through the main event bus. The `UltrasonicDetectionEvent` published by `fetchUltrasonicCm()` does go to the bus, which is correct.

### 8.4 Button Events Are Fully Undelivered

The firmware detects buttons with correct debounce, double-press window, and long-press threshold. It stores events in `ButtonManager.lastEvent`. But `handleGetState()` in `http_server.h` does not include `button_events` in the `/state` response, and `getEventsJson()` is an empty stub. Flutter has no way to receive button events from the goggle today.

### 8.5 JPEG Validation Is Strong

Both the simulator (`_jpeg_magic_ok()`) and the firmware (`camera_manager.h` magic byte check) validate JPEG headers before sending. Flutter's `_SmartGoggleCameraCapability._isSupportedImageBytes()` validates on receipt. The full chain validates JPEG integrity — this is solid.

### 8.6 The Adapter Pattern Enables Zero-Change Integration

`SmartGoggleAdapter` takes a `DeviceTransport` constructor argument. If a future WebSocket or MJPEG transport is needed, it can be injected without touching the adapter. The `CameraCapability` and `BatteryCapability` implementations depend only on `DeviceTransport.requestBytes()` and `requestJson()` — both already implemented in `HttpTransportImpl`.

---

## Section 9 — Technical Debt

| Item | File | Severity |
|---|---|---|
| SOS stream never consumed in `DeviceManagerImpl` | `device_discovery_server.dart`, `device_manager_impl.dart` | Medium |
| Button events undelivered from firmware | `button_manager.h`, `http_server.h` | High |
| `getEventsJson()` is empty stub | `button_manager.h` | High |
| No device TTL — stale registry entries accumulate | `shared_prefs_device_registry.dart` | Low |
| `GOGGLE_INTEGRATION_AUDIT.md` states firmware doesn't exist | `docs/roadmaps/goggles/GOGGLE_INTEGRATION_AUDIT.md` | Low |
| Simulator default battery 92 vs firmware hardcoded 75 | `state.py`, `config.h` | Trivial |
| `DebugGoggleService` creates parallel adapters outside `DeviceManager` | `debug_goggle_service.dart` | Low |
| `HttpTransportImpl` has no liveness/heartbeat mechanism | `http_transport.dart` | Medium |
| No Android `MulticastLock` acquisition before UDP socket bind | (not yet implemented) | High — must fix before UDP works on Android |
| No `NSLocalNetworkUsageDescription` in iOS plist | (not yet implemented) | High — iOS will silently block UDP without this |

---

## Section 10 — Missing Features

**Not in scope for next sprint (per sprint constraints), but documented for completeness:**

| Feature | Status | Notes |
|---|---|---|
| `UdpDiscoveryService` (Flutter) | ❌ Missing | Core deliverable of next sprint |
| UDP broadcast in firmware | ❌ Missing | ~60 lines of C++ |
| Button event delivery (firmware → Flutter) | ❌ Missing | Either push or poll |
| Goggle camera as Assist source | ❌ Missing | Requires `GoggleCaptureAdapter` + arbitration |
| Android `MulticastLock` | ❌ Missing | Required for UDP on Android |
| iOS `NSLocalNetworkUsageDescription` | ❌ Missing | Required for UDP on iOS |
| Device TTL / stale entry cleanup | ❌ Missing | Quality-of-life |
| Goggle liveness via UDP timestamp | ❌ Missing | Replace HTTP health poll |
| Audio output routing | ❌ Missing | Hardware V2 |
| Battery ADC (real) | ❌ Missing | Hardware V2 |

---

## Section 11 — Foreground Readiness Assessment

The goggle subsystem has **no foreground service dependency**. Discovery, connection, and telemetry all run in the same process as the app. This is acceptable for V1.

However, when the app is backgrounded on Android:
- `DeviceDiscoveryServer` (HTTP on port 8080) will stop receiving connections
- `UdpDiscoveryService` (once implemented) will stop receiving packets
- Active HTTP connections from `HttpTransportImpl` will time out

When the app returns to foreground, `startScan()` is called from `DebugDevicesTab.initState()`. This restores known devices and restarts scans. For goggle-connected Assist use, the user must keep the app in foreground — acceptable for Phase 1.

The architecture is compatible with a future foreground service: `HardwareBootstrapper.boot()` already runs independently of the UI. Adding foreground service support requires only wiring `startScan()` into the service's `onStartCommand`.

---

## Section 12 — Recommended Next Sprint

In priority order, strictly scoped to what enables demo-ready UDP discovery:

**Step 1 — Flutter `UdpDiscoveryService`**  
Create `apps/flutter/lib/core/hardware/infrastructure/services/udp_discovery_service.dart`.  
Bind `RawDatagramSocket` on port 8888. Parse packets. Validate required fields. Emit `Map<String, dynamic>` matching the existing discovery event format. Acquire Android `MulticastLock`. Add `NSLocalNetworkUsageDescription` to iOS plist.  
Effort: ~4 hours.

**Step 2 — Wire into `DeviceManagerImpl`**  
Add `UdpDiscoveryService` to `hardware_providers.dart`. Subscribe in `startScan()`, unsubscribe in `stopScan()`. No other DeviceManager changes.  
Effort: ~1 hour.

**Step 3 — UDP broadcast in ESP32 firmware**  
Add `udp_broadcast.h` to `hardware/smart-goggles/firmware/src/`. Use `WiFiUdp` (already in ESP32 Arduino core). Initial burst of 3 packets on boot, then every 3 seconds. Use `millis()`-based non-blocking timer. Log every broadcast.  
Effort: ~2 hours.

**Step 4 — Fix button event delivery (firmware → Flutter)**  
Populate `getEventsJson()` in `ButtonManager`. Add `button_events` array to `GET /state` response. Add `/events/button` push endpoint on `DeviceDiscoveryServer`. Wire to event bus.  
Effort: ~3 hours.

**Step 5 — Device TTL**  
In `DeviceManagerImpl`, filter `getKnownDevices()` to exclude devices not seen in the last 5 minutes, or add a periodic cleanup. Non-blocking, low risk.  
Effort: ~1 hour.

**Total estimated effort**: ~11 hours implementation + testing.

---

## Verification Steps (Expected Demo)

```
1. Start simulator: uv run uvicorn app.main:app --host 0.0.0.0 --port 9000
   → Simulator begins broadcasting UDP on port 8888 immediately

2. Open Flutter app (debug tab)
   → UdpDiscoveryService binds port 8888
   → Within 3 seconds: packet received from simulator IP
   → Device appears in "Devices" list automatically (no manual registration)

3. Tap device → DeviceDetailScreen
   → Connection state: ready
   → Battery pull: 92%
   → Camera capture: returns JPEG from webcam

4. Unplug simulator (stop process)
   → After 30s: device marked offline/degraded in UI

5. Restart simulator
   → Initial UDP burst fires
   → Device reappears in UI within 3 seconds
   → Flutter reconnects automatically

6. Flash firmware to ESP32-S3
   → Boot sequence logs to serial
   → Device broadcasts UDP with real MAC-based device_id
   → Appears in Flutter alongside or instead of simulator
   → Capture returns real OV5640 JPEG
```

---

## Conclusion

The Smart Goggle architecture is **in a better state than its documentation suggests**. The ESP32-S3 firmware exists and is complete for HTTP (V1). The simulator has already implemented UDP broadcasting exactly as specified. Flutter's device management layer is designed to accept new discovery services with minimal changes.

**The single remaining implementation gap is a Flutter `UdpDiscoveryService`** — approximately 80 lines of Dart — and the corresponding UDP broadcast loop in the firmware (~60 lines of C++). Everything else either already exists or requires only minor wiring.

Implementation of UDP discovery and ESP32-S3 firmware integration can begin immediately with high confidence.

---

**Audit complete.**  
**Branch**: `feat/goggle-udp-audit`  
**Status**: Read-only. No files were modified except this document.
