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

## Packet Format

Use small binary packets with a common header.

```text
[type, payload..., sequence]
```

`sequence` is a rolling `uint8` counter used for duplicate protection. If the firmware cannot include sequence in the first version, Flutter should still support it as optional but log that dedupe is degraded.

### Packet Types From Cane To App

| Type | Name | Payload |
| --- | --- | --- |
| `0x10` | Button event | `[button_id, press_type, sequence]` |
| `0x20` | Ultrasonic telemetry | `[distance_low, distance_high, detected, sequence]` |
| `0x21` | Battery telemetry | `[battery_percent, sequence]` |
| `0x22` | Heartbeat | `[status, sequence]` |
| `0x40` | Error | `[error_code, sequence]` |

### Commands From App To Cane

| Type | Name | Payload |
| --- | --- | --- |
| `0x30` | Haptic | `[duration_low, duration_high]` |
| `0x31` | Status feedback | `[mode, duration_low, duration_high]` |

Use little-endian `uint16` for duration and distance values.

## Button Mapping

BLE values:

```text
button_id:
  0x01 = button 1
  0x02 = button 2
  0x03 = button 3

press_type:
  0x01 = single
  0x02 = double
```

Flutter mapping:

| BLE Button | BLE Press | Flutter Event |
| --- | --- | --- |
| `0x01` | `0x01` | `ButtonPressEvent(button1, single)` |
| `0x01` | `0x02` | `ButtonPressEvent(button1, double)` |
| `0x02` | `0x01` | `ButtonPressEvent(button2, single)` |
| `0x02` | `0x02` | `ButtonPressEvent(button2, double)` |
| `0x03` | `0x01` | `ButtonPressEvent(button3, single)` |
| `0x03` | `0x02` | `ButtonPressEvent(button3, double)` |

`button3 + double` is the default SOS trigger and should bypass event buffering.

This requires expanding `ButtonId` from two values to three values.

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
- Parse ultrasonic, battery, heartbeat, and error packets.
- Send haptic command with two-byte duration.
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
- parser handles ultrasonic little-endian distance
- parser handles battery bounds
- adapter publishes expected `HardwareEvent`s
- haptic command encodes duration as little-endian `uint16`
- duplicate sequence packets are ignored

Integration/manual tests:

- first pairing stores known cane
- app restart auto-connects cane
- foreground to background does not crash transport
- reconnect backoff is bounded and visible
- haptic command reaches firmware
- Button 3 double press reaches resolved event stream as critical/SOS

Failure-mode coverage is tracked in [failure-modes.md](failure-modes.md).

## Open Decisions

- Final BLE UUID values.
- Whether Button 3 double press is final SOS gesture.
- Whether firmware can include packet sequence from the first version.
- Which Flutter BLE package to standardize on.
- Whether the first branch includes native Android foreground service or only the service-ready boundary.
