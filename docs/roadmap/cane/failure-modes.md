# Smart Cane Failure Modes

This document defines how the Smart Cane feature should behave when BLE, firmware, app lifecycle, or foreground-service readiness paths fail.

The goal is not to avoid every failure. The goal is to fail visibly, recover automatically where safe, and never lose critical cane events silently.

## Product Decisions

- The app automatically reconnects to a known cane after launch.
- Cane monitoring is always-on after pairing.
- The first implementation does not implement the native Android foreground service layer.
- All Flutter cane code must still be foreground-service-compatible so BLE ownership can move behind a foreground service later.
- Button actions are configurable in Flutter code and must not be hardcoded into BLE parsing.
- Ultrasonic danger detection happens on the cane first; the app receives obstacle events plus optional low-rate telemetry.

## Failure Handling Principles

- Prefer automatic recovery for connectivity failures.
- Never let reconnect loops run forever without bounded state and diagnostics.
- Do not surface raw BLE/plugin errors directly to user-facing UI.
- Convert known failures into structured hardware logs and `HardwareErrorEvent`s.
- Keep the UI passive: it observes connection state and offers manual retry/forget actions.
- Parser failures must not crash stream listeners.
- Safety events must not be delayed by low-priority telemetry.
- Foreground-service readiness must not depend on widget lifecycle.

## Failure Matrix

| Area | Failure | Expected Behavior | State | Observability |
| --- | --- | --- | --- | --- |
| Permissions | Bluetooth permission denied | Stop scan/connect, show actionable debug state | `failed` | `ble_permission_denied` |
| Permissions | Location permission required but missing on Android | Stop scan/connect until permission exists | `failed` | `ble_location_permission_missing` |
| Adapter | Bluetooth is off | Do not scan; retry when Bluetooth becomes available | `disconnected` or `failed` | `bluetooth_unavailable` |
| Scan | No cane found during scan window | Retry with backoff for known cane | `reconnecting` | `scan_timeout` |
| Scan | Multiple cane devices found | Prefer known device id; otherwise require user selection | `scanning` | `multiple_canes_found` |
| Connect | BLE connection timeout | Disconnect partial session and retry with backoff | `reconnecting` | `connect_timeout` |
| Connect | Device rejects connection | Retry until budget is exhausted | `reconnecting` then `failed` | `connect_rejected` |
| GATT | Service UUID not found | Mark firmware/protocol mismatch | `failed` | `service_not_found` |
| GATT | Notify characteristic missing | Mark incompatible cane | `failed` | `notify_characteristic_missing` |
| GATT | Command characteristic missing | Allow receive-only degraded mode if notifications work | `degraded` | `command_characteristic_missing` |
| Notify | Subscribe fails | Disconnect and retry with backoff | `reconnecting` | `notify_subscribe_failed` |
| Packet | Empty packet | Ignore and log at debug level | unchanged | `packet_empty` |
| Packet | Unknown packet type | Ignore and log structured warning | unchanged | `packet_unknown_type` |
| Packet | Malformed packet length | Publish parser error, keep connection alive | `degraded` if repeated | `packet_malformed` |
| Packet | Duplicate sequence | Drop duplicate without re-emitting event | unchanged | `packet_duplicate` |
| Packet | Unsupported protocol version | Mark incompatible or degraded based on capability response | `failed` or `degraded` | `protocol_unsupported` |
| Gesture mapping | Button gesture has no mapped action | Publish raw gesture for debug, do not crash | unchanged | `gesture_unmapped` |
| Obstacle detection | Cane sends danger event | Route immediately; do not wait for raw distance stream | `ready` | `obstacle_detected` |
| Obstacle detection | Raw distance telemetry missing | Keep safety events working; mark telemetry stale | `ready` or `degraded` | `distance_telemetry_stale` |
| Heartbeat | Heartbeat missing once | Keep connected, mark stale diagnostics | `ready` | `heartbeat_late` |
| Heartbeat | Heartbeat missing past timeout | Mark degraded and attempt recovery | `degraded` | `heartbeat_timeout` |
| Battery | Battery packet invalid | Ignore packet and log parser error | unchanged | `battery_packet_invalid` |
| Battery | Battery low | Publish telemetry/error warning | `ready` | `battery_low` |
| Command | Haptic write while disconnected | Reject command with structured error | unchanged | `haptic_disconnected` |
| Command | Haptic write timeout | Publish command error and keep connection alive | `degraded` if repeated | `haptic_write_timeout` |
| Lifecycle | App resumes after pause | Re-check known cane and reconnect automatically | `reconnecting` then `ready` | `lifecycle_resume_reconnect` |
| Lifecycle | Process restarts | Load known cane and auto-connect | `reconnecting` then `ready` | `startup_autoconnect` |
| Foreground service | Service boundary unavailable in first version | Run coordinator in Flutter process, keep API service-ready | unchanged | `foreground_service_not_enabled` |

## Auto-Reconnect Policy

Known cane reconnect starts automatically:

- on app startup
- after app resume
- after BLE disconnect
- after heartbeat timeout
- after transient scan/connect failure

Suggested retry profile:

| Attempt | Delay |
| --- | --- |
| 1 | immediate |
| 2 | 1 second |
| 3 | 2 seconds |
| 4 | 5 seconds |
| 5 | 10 seconds |
| 6+ | 30 seconds, bounded |

The implementation should avoid a tight infinite loop. Once the retry budget is exhausted, the app should keep the cane visible as failed/lost and continue with a slower recovery loop only if always-on monitoring is enabled.

Because cane monitoring is always-on after pairing, reconnect should continue in the background-compatible coordinator. The native foreground service can own this loop later without changing adapter behavior.

## Always-On Monitoring Rule

After pairing, the cane is considered part of the user's active safety setup.

That means:

- startup auto-connect is enabled by default
- reconnect is automatic
- foreground-service-compatible code must not depend on an open screen
- debug UI can stop/forget the cane, but normal app navigation should not stop monitoring
- foreground service implementation later should keep the connection alive with a visible Android notification

## Packet Safety Rules

The parser must be defensive:

- return typed parse results instead of throwing from stream handlers
- preserve raw packet bytes in debug logs when practical
- validate JSON shape and required fields before mapping
- validate button id and press type before creating `ButtonPressEvent`
- dedupe repeated sequence numbers per packet type
- convert button gestures through a configurable action map
- treat mapped SOS actions as critical regardless of physical button assignment
- treat obstacle events as already-decided cane-side detections
- do not let malformed telemetry block later button events

## Command Safety Rules

Commands from app to cane should include:

- connection pre-check
- timeout
- structured error code on failure
- optional ack support later
- no unbounded retries for haptic commands

Haptic command failure should not disconnect the cane by itself unless the BLE write failure indicates the connection is invalid.

## State Expectations

Minimum states:

- `idle`: no active connection attempt
- `scanning`: looking for cane BLE service
- `connecting`: connecting to selected/known cane
- `ready`: connected, notifications active, heartbeat healthy
- `degraded`: connected but missing heartbeat, command characteristic, or repeated parser issues
- `reconnecting`: reconnect in progress
- `failed`: retry budget exhausted or incompatible device
- `disconnected`: manually disconnected or forgotten

If the current enum cannot support all states at first, the implementation should keep public state compatible and expose detailed state through diagnostics until the state model is expanded.

## User-Facing Behavior

Normal users should see simple state:

- connecting
- connected
- reconnecting
- needs attention

Debug UI should show detailed state:

- last BLE error code
- last packet parse error
- last heartbeat time
- reconnect attempt count
- next retry delay
- protocol version
- firmware version when available
- raw recent packets

## Testing Requirements

Unit tests:

- empty packet does not crash
- malformed packet does not crash
- unknown packet type is ignored with error result
- duplicate sequence is dropped
- all six button combinations parse correctly
- mapped SOS action receives critical priority
- obstacle event does not wait for raw distance telemetry
- haptic command refuses disconnected writes
- heartbeat timeout moves coordinator to degraded/reconnect behavior

Manual/integration tests:

- Bluetooth off before launch
- permission denied then granted
- cane out of range then returns
- app launch auto-connects known cane
- app resume reconnects known cane
- haptic write works when connected
- foreground-service boundary can be introduced without changing adapter/parser contracts

## Open Questions

- Final retry budget before showing failed/lost.
- Exact heartbeat interval and timeout.
- Whether firmware can send sequence numbers in version one.
- Whether command ack is required in the first firmware version.
- Final user-facing text for always-on monitoring and foreground-service notification.

