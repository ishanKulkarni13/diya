# Smart Cane State Machine

This document defines the Smart Cane connection states and transitions.

The goal is stable always-on behavior after pairing. The UI should observe state. Reconnect and lifecycle decisions should belong to the coordinator so the same logic can later be hosted by an Android foreground service.

## State Names

| State | Meaning |
| --- | --- |
| `idle` | No active scan or connection attempt has started. |
| `scanning` | Looking for the known cane BLE service/device. |
| `connecting` | BLE device found and connection/GATT setup is in progress. |
| `ready` | Connected, notifications active, heartbeat healthy. |
| `degraded` | Connected but not fully healthy, such as stale heartbeat or command characteristic unavailable. |
| `reconnecting` | Recovering from disconnect, timeout, or heartbeat failure. |
| `failed` | Retry budget exhausted or device/protocol is incompatible. |
| `disconnected` | User intentionally forgot/disconnected the cane. |

`lost` may be used as a diagnostic reason under `failed`, but the public state should stay `failed` unless the product needs a separate user-facing label later.

## Startup Flow

```text
app_start
  -> load_known_devices
  -> known_cane_found
  -> scanning
  -> connecting
  -> ready
```

If no cane is known, the state remains `idle` until the user pairs one.

Because cane monitoring is always-on after pairing, a known cane should auto-connect after startup without requiring the debug screen to be open.

## Normal Transition Rules

| From | Event | To |
| --- | --- | --- |
| `idle` | known cane loaded | `scanning` |
| `scanning` | cane found | `connecting` |
| `scanning` | scan timeout | `reconnecting` |
| `connecting` | GATT ready and notifications subscribed | `ready` |
| `connecting` | connect timeout | `reconnecting` |
| `ready` | heartbeat late | `degraded` |
| `ready` | BLE disconnect | `reconnecting` |
| `degraded` | heartbeat restored | `ready` |
| `degraded` | heartbeat timeout | `reconnecting` |
| `reconnecting` | retry delay elapsed | `scanning` |
| `reconnecting` | retry budget exhausted | `failed` |
| `failed` | manual retry or slow always-on retry | `scanning` |
| any state | user forgets cane | `disconnected` |

## Retry Policy

The coordinator should use bounded backoff:

| Attempt | Delay |
| --- | --- |
| 1 | immediate |
| 2 | 1 second |
| 3 | 2 seconds |
| 4 | 5 seconds |
| 5 | 10 seconds |
| 6+ | 30 seconds, bounded |

After the active retry budget is exhausted, move to `failed`. Since monitoring is always-on after pairing, the coordinator may continue a slower recovery loop, but it must stay observable and avoid tight retry loops.

## Heartbeat Policy

Suggested first values:

| Signal | Timing |
| --- | --- |
| expected heartbeat interval | 5 seconds |
| late heartbeat warning | 10 seconds |
| heartbeat timeout | 20 seconds |

These values should live in one config location and be easy to tune.

## Foreground-Service Compatibility

The coordinator must not depend on a screen widget staying mounted.

That means:

- auto-connect runs from app bootstrap/provider initialization
- reconnect timers are owned by a service/coordinator layer
- debug UI only observes state and sends commands
- BLE parser and adapter do not know whether the owner is Flutter UI or Android foreground service
- native foreground service can later own the same lifecycle contract

## Event Handling While Degraded

`degraded` does not mean all events stop.

Allowed behavior:

- button events still publish if notifications are active
- obstacle events still publish if notifications are active
- haptic commands may be disabled if command characteristic is missing
- low-rate distance telemetry may be stale
- UI should show needs-attention state

## Safety Rules

- Mapped SOS actions bypass buffering.
- Cane-side obstacle events are treated as immediate hardware events.
- Raw distance telemetry is never required before routing an obstacle event.
- Parser errors do not close the connection unless repeated errors indicate protocol incompatibility.

