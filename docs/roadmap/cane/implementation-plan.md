# Smart Cane Flutter Implementation Plan

This document describes how to implement the Smart Cane feature in Flutter while keeping it stable, testable, and ready for foreground-service ownership.

## Branch

Recommended branch:

```bash
codex/flutter-smart-cane-ble
```

Keep the branch focused on Smart Cane Flutter hardware work. Avoid backend or assist-flow changes unless integration requires a small event contract adjustment.

## Architecture

```text
Debug UI / Assist Flow
        |
        v
DeviceManager / CaneConnectionCoordinator
        |
        v
SmartCaneAdapter
        |
        v
BleTransportImpl
        |
        v
Smart Cane firmware
```

Responsibilities:

- `BleTransportImpl`
  - scans for the Smart Cane BLE service
  - connects to the selected device
  - discovers characteristics
  - subscribes to notify characteristic
  - writes command characteristic
  - emits transport state changes
- `SmartCaneAdapter`
  - parses cane packets
  - maps packets to `HardwareEvent`
  - exposes `HapticCapability`
  - publishes events to `HardwareEventBus`
- `CaneConnectionCoordinator`
  - auto-connects known cane
  - handles lifecycle resume/pause hooks
  - owns reconnect/backoff policy
  - exposes state that a foreground service can later own
- Debug UI
  - shows scan results
  - shows known cane state
  - shows last packets and parsed events
  - provides haptic test action

## Smart Goggle Reference Patterns

Use the Smart Goggle code as the local reference for shape and conventions:

- `SmartGoggleAdapter` shows how capabilities belong inside an adapter.
- `HttpTransportImpl` shows how a transport should own connection state and expose state streams.
- `DebugGoggleService` shows how debug-only device sessions can wrap adapter and transport safely.
- `DeviceDetailScreen` already separates cane and goggle capability UI, so cane controls should extend the existing cane section.
- `HardwareEventBus` usage in goggle capabilities is the model for cane telemetry and error publication.

Translate the pattern, not the transport. The cane should not use HTTP registration, URL paths, or polling as its primary data model. It should use BLE scan/connect/notify/write and expose the same logical hardware events to the rest of the app.

## BLE Contract

Use a single Smart Cane BLE service with separate notify and command characteristics.

Suggested UUID ownership:

```text
Smart Cane Service UUID:        TBD
Notify Characteristic UUID:     TBD
Command Characteristic UUID:    TBD
Device Info Characteristic UUID: optional
```

UUIDs should be defined once in Flutter, for example:

```text
apps/flutter/lib/core/hardware/infrastructure/protocols/smart_cane_protocol.dart
```

Firmware must use the same UUIDs.

The protocol should start with UTF-8 JSON payloads because it is easier to build, inspect, test, and debug than a custom binary format. The payloads are small enough for the cane's first event set. A compact binary protocol can be introduced later only if profiling proves JSON is too large or too slow.

## Packet Format

Use one JSON object per BLE notification or command write.

```json
{"v":1,"t":"button","button":1,"press":"single","seq":42}
```

Required common fields:

- `v`: protocol version
- `t`: event or command type
- `seq`: rolling sequence number for dedupe where available

`seq` is used for duplicate protection. If the firmware cannot include sequence in the first version, Flutter should still support it as optional but log that dedupe is degraded.

### Packet Types From Cane To App

| Type | Name | Payload |
| --- | --- | --- |
| `button` | Button gesture | `{ "button": 1..3, "press": "single" | "double" }` |
| `obstacle` | Cane-side obstacle detection | `{ "distance_cm": 84.5, "level": "warning" | "danger" }` |
| `distance` | Low-rate debug telemetry | `{ "distance_cm": 84.5 }` |
| `battery` | Battery telemetry | `{ "battery_percent": 0..100 }` |
| `heartbeat` | Health heartbeat | `{ "status": "ok" | "degraded" }` |
| `error` | Firmware/device error | `{ "code": "...", "message": "..." }` |

### Commands From App To Cane

| Type | Name | Payload |
| --- | --- | --- |
| `haptic` | Haptic feedback | `{ "duration_ms": 500 }` |
| `status_feedback` | LED/buzzer/status feedback | `{ "mode": "ok" | "warning" | "error", "duration_ms": 500 }` |

See [protocol-spec.md](protocol-spec.md) for the full contract.

## Button Mapping

BLE packets report physical gestures only:

```text
button: 1, 2, or 3
press: single or double
```

Flutter then maps gestures to app actions through a configurable table:

| Gesture | Default Action |
| --- | --- |
| `button_1_single` | Configurable |
| `button_1_double` | Configurable |
| `button_2_single` | Configurable |
| `button_2_double` | Configurable |
| `button_3_single` | Configurable |
| `button_3_double` | Configurable |

This requires expanding `ButtonId` from two values to three values. SOS should be one possible mapped action, not a hardcoded BLE packet.

## State Model

The cane should expose these states through the existing hardware state model or a compatible extension:

- `idle`
- `scanning`
- `connecting`
- `ready`
- `degraded`
- `reconnecting`
- `failed`
- `disconnected`

If the existing enum cannot represent all states yet, keep the external state model stable and add detailed state through diagnostics/logs until the enum can be changed safely.

## Auto-Connect Plan

1. User scans and connects to cane once.
2. App stores:
   - device id
   - BLE remote id/address when available
   - advertised name
   - service UUID
   - last seen timestamp
3. On startup, `DeviceManager` or `CaneConnectionCoordinator` loads known devices.
4. Known cane reconnect begins automatically.
5. Reconnect attempts use bounded backoff.
6. After retry budget is exhausted, state becomes failed/lost.
7. Manual retry resets the retry budget.

## Foreground-Service Ready Boundary

Add the coordinator so later foreground service work has a clear handoff point.

Suggested interface shape:

```dart
abstract class CaneConnectionCoordinator {
  Stream<CaneConnectionSnapshot> get snapshots;
  Future<void> start();
  Future<void> stop();
  Future<void> connectKnownCane();
  Future<void> disconnect();
  Future<void> sendHaptic(int durationMs);
}
```

The first implementation can run in normal Flutter process memory. Later, Android foreground service work can move ownership behind the same interface.

## Implementation Phases

### Phase 1: Protocol And Adapter

- Add protocol constants and parser.
- Expand `ButtonId` to include `button3`.
- Update `SmartCaneAdapter` to use parser instead of raw byte checks.
- Map all six button combinations.
- Add a configurable gesture-to-action mapping layer.
- Parse obstacle, low-rate distance telemetry, battery, heartbeat, and error packets.
- Send haptic command as a JSON command.
- Add parser and adapter tests.

### Phase 2: BLE Transport

- Add BLE dependency if not already selected.
- Implement service UUID scan.
- Implement connect/disconnect.
- Discover notify and command characteristics.
- Subscribe to notifications.
- Write haptic command.
- Emit transport state transitions and errors.
- Match the `HttpTransportImpl` state-stream pattern, but keep BLE characteristic details private to the transport.

### Phase 3: Auto-Connect And Debug UI

- Store known cane after successful connection.
- Auto-connect known cane at startup.
- Add bounded reconnect with backoff.
- Add debug UI for scan, connect, disconnect, haptic, packet log, and parsed event log.
- Show degraded/failed states clearly.
- Use the existing goggle debug layout as the visual and interaction baseline, with cane-specific controls.

### Phase 4: Foreground-Service Integration

- Add Android foreground service bridge.
- Move long-running BLE ownership behind service boundary.
- Add lifecycle recovery for foreground/background transitions.
- Validate behavior when app is backgrounded, resumed, or process-restarted.

## Test Plan

Unit tests:

- parser rejects empty and malformed packets
- parser handles all six button combinations
- parser handles cane-side obstacle events and low-rate distance telemetry
- parser handles battery bounds
- adapter publishes expected `HardwareEvent`s
- haptic command encodes duration as JSON
- duplicate sequence packets are ignored

Integration/manual tests:

- first pairing stores known cane
- app restart auto-connects cane
- foreground to background does not crash transport
- reconnect backoff is bounded and visible
- haptic command reaches firmware
- mapped SOS action reaches resolved event stream as critical/SOS

Failure-mode coverage is tracked in [failure-modes.md](failure-modes.md).

## Open Decisions

- Final BLE UUID values.
- Whether firmware can include packet sequence from the first version.
- Which Flutter BLE package to standardize on.
- Whether the first branch includes native Android foreground service or only the service-ready boundary.
