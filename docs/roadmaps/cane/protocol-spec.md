# Smart Cane Protocol Spec

This document defines the first Smart Cane application protocol between firmware and Flutter.

The first version intentionally uses UTF-8 JSON payloads over BLE characteristics. This is easier to implement, easier to inspect in logs, easier to test, and less likely to create parser bugs than a custom binary protocol. A binary protocol can be introduced later only if real profiling shows JSON is too large or too slow.

## Design Goals

- Keep firmware and Flutter easy to debug.
- Keep button actions configurable in Flutter.
- Avoid high-rate raw ultrasonic streaming for safety decisions.
- Let the cane detect obstacle danger locally and notify the app immediately.
- Keep payloads small and versioned.
- Support foreground-service ownership later without changing packet meaning.

## BLE Shape

Use one Smart Cane BLE service with separate characteristics:

| Characteristic | Direction | Purpose |
| --- | --- | --- |
| Notify characteristic | Cane to app | Button, obstacle, telemetry, heartbeat, error events |
| Command characteristic | App to cane | Haptic and status feedback commands |
| Device info characteristic | App reads cane | Optional firmware/protocol/capability info |

UUID values are still `TBD` and must be shared by firmware and Flutter in one constants file.

## Common Payload Fields

Every payload should be one JSON object.

```json
{"v":1,"t":"heartbeat","seq":12,"status":"ok"}
```

Common fields:

| Field | Required | Description |
| --- | --- | --- |
| `v` | Yes | Protocol version. First version is `1`. |
| `t` | Yes | Payload type. |
| `seq` | Preferred | Rolling sequence number for duplicate detection. |
| `ts` | Optional | Firmware timestamp or uptime milliseconds. |

Flutter must reject unsupported protocol versions safely and log a structured error.

## Cane To App Events

### Button Gesture

```json
{"v":1,"t":"button","button":1,"press":"single","seq":42}
```

Rules:

- `button` must be `1`, `2`, or `3`.
- `press` must be `single` or `double`.
- Flutter emits a physical button event and then maps it to an app action through configuration.
- BLE parsing must not hardcode assist, repeat, navigation, or SOS.

Gesture keys:

| Button | Press | Gesture Key |
| --- | --- | --- |
| 1 | single | `button_1_single` |
| 1 | double | `button_1_double` |
| 2 | single | `button_2_single` |
| 2 | double | `button_2_double` |
| 3 | single | `button_3_single` |
| 3 | double | `button_3_double` |

### Obstacle Detection

```json
{"v":1,"t":"obstacle","distance_cm":72.5,"level":"danger","seq":43}
```

Rules:

- Cane firmware decides obstacle detection locally.
- The app must treat `obstacle` as an already-decided event.
- `level` should be `warning` or `danger`.
- `distance_cm` is useful context, but the app should not wait for separate raw distance telemetry before acting.

### Low-Rate Distance Telemetry

```json
{"v":1,"t":"distance","distance_cm":118.0,"seq":44}
```

Rules:

- This is for debug/status UI.
- It should be low-rate.
- Missing distance telemetry must not break obstacle detection.

### Battery Telemetry

```json
{"v":1,"t":"battery","battery_percent":81,"seq":45}
```

Rules:

- `battery_percent` must be clamped to `0..100`.
- Low battery should publish a warning event.

### Heartbeat

```json
{"v":1,"t":"heartbeat","status":"ok","seq":46}
```

Rules:

- Used to detect stale connections.
- Missing heartbeat should move the connection to degraded/reconnecting according to the state machine.

### Error

```json
{"v":1,"t":"error","code":"sensor_fault","message":"ultrasonic timeout","seq":47}
```

Rules:

- Firmware errors should become `HardwareErrorEvent`s.
- The app should not disconnect automatically unless the error indicates the connection is invalid.

## App To Cane Commands

### Haptic

```json
{"v":1,"t":"haptic","duration_ms":500}
```

Rules:

- `duration_ms` should be bounded in Flutter before sending.
- Failed writes should publish structured command errors.
- No unbounded retries for haptic commands.

### Status Feedback

```json
{"v":1,"t":"status_feedback","mode":"ok","duration_ms":500}
```

Rules:

- `mode` can be `ok`, `warning`, or `error`.
- This command is optional for the first implementation.

## Configurable Action Mapping

Flutter should define a mapping separate from BLE parsing.

Example:

```dart
const defaultCaneGestureActions = {
  'button_1_single': CaneAction.assist,
  'button_1_double': CaneAction.repeatLast,
  'button_2_single': CaneAction.navigationHint,
  'button_2_double': CaneAction.shareStatus,
  'button_3_single': CaneAction.statusCheck,
  'button_3_double': CaneAction.sos,
};
```

The exact product actions can change later. The protocol should not change when the mapping changes.

## Parser Requirements

The parser must:

- accept UTF-8 JSON bytes
- validate the root value is an object
- validate `v` and `t`
- validate required fields per type
- return typed parse results instead of throwing from stream listeners
- preserve unknown payloads for debug logs when practical
- reject malformed payloads without closing the BLE connection
- dedupe repeated `seq` values when available

## Platform Notes

Android provides BLE APIs for discovering devices, connecting to a GATT server, discovering services/characteristics, and transferring data. Android 12 and higher require runtime Nearby Devices permissions such as `BLUETOOTH_SCAN` and `BLUETOOTH_CONNECT`. Future foreground-service work should use the Android `connectedDevice` foreground service type for long-running interaction with the cane.

