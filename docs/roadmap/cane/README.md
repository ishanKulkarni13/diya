# Smart Cane Roadmap

This folder documents the Smart Cane feature before implementation so Flutter, firmware, and assist-flow work can happen in parallel without hidden assumptions.

The Smart Cane should be treated as a foreground-service-ready hardware subsystem. It is not just a BLE adapter. It owns reliable cane discovery, pairing, reconnect, button events, sensor telemetry, haptic feedback, and lifecycle behavior that can later run from an Android foreground service.

## Current Code Status

The Flutter codebase already has a partial cane scaffold:

- `apps/flutter/lib/core/hardware/infrastructure/adapters/smart_cane_adapter.dart`
  - maps a few raw bytes into hardware events
  - exposes a haptic capability
- `apps/flutter/lib/core/hardware/infrastructure/transports/ble_transport.dart`
  - exists, but is currently a stub
- `apps/flutter/lib/core/hardware/infrastructure/manager/adapter_factory.dart`
  - already maps `deviceType == 'cane'` to `BleTransportImpl` and `SmartCaneAdapter`
- `apps/flutter/lib/core/hardware/domain/messaging/event_router.dart`
  - already has priority handling for safety-style button events

The next work should turn this scaffold into a stable, testable, foreground-ready implementation.

## Product Requirements

The Smart Cane must support:

- three physical buttons
- single press and double press for each button
- automatic reconnect after first setup
- foreground-service-ready BLE ownership
- reliable button event delivery
- obstacle telemetry from cane sensors
- battery telemetry
- haptic feedback commands from the app to the cane
- visible debug tooling for development and field testing

## Button Actions

The cane has three buttons. Each button supports single press and double press.

| Button | Press | Intended Meaning | Event Priority |
| --- | --- | --- | --- |
| Button 1 | Single | Assist / describe surroundings | High |
| Button 1 | Double | Repeat last response or quick assist mode | Medium |
| Button 2 | Single | Navigation or obstacle hint | Medium |
| Button 2 | Double | Share location or status check | Medium |
| Button 3 | Single | Cane status / haptic confirmation | Low |
| Button 3 | Double | SOS emergency trigger | Critical |

SOS should be double press on Button 3 by default to reduce accidental emergency triggers. If product feedback says otherwise, this mapping can change without changing the BLE packet format.

## Connection Behavior

After first successful pairing:

1. The app stores the cane as a known device.
2. On app startup, the hardware bootstrap layer loads known devices.
3. The cane coordinator starts a reconnect attempt without user action.
4. If connected, the app subscribes to BLE notifications.
5. If disconnected, the app retries with bounded backoff.
6. If retries are exhausted, the cane becomes `failed` or `lost` instead of retrying forever.
7. The user can manually retry or forget the device from debug/device UI.

The UI should observe device state. It should not own reconnect loops directly.

## Foreground-Service Readiness

The first implementation does not need to complete the native Android foreground service, but it must be designed so the service can own the BLE connection later.

Required boundary:

- Flutter UI asks for scan, connect, disconnect, haptic, and diagnostics.
- A cane connection coordinator owns reconnect policy and lifecycle decisions.
- `BleTransportImpl` owns BLE scan/connect/notify/write details.
- `SmartCaneAdapter` owns cane protocol parsing and event mapping.
- Future Android foreground service can replace or host the coordinator without changing assist logic.

Foreground service responsibilities later:

- keep the cane BLE connection alive while the user enables cane monitoring
- maintain reconnect loop while foreground-service notification is active
- publish connection and event state back to Flutter
- stop cleanly when the user disables cane monitoring
- expose visible notification state required by Android

## Smart Goggle Inspiration

The Smart Goggle implementation is the closest working reference in the Flutter codebase. The Smart Cane should reuse its architectural ideas, but not its Wi-Fi transport assumptions.

Reuse these patterns:

- capability-based adapters, where UI asks for a capability instead of talking to transport directly
- transport state streams mapped into `HardwareConnectionState`
- `HardwareEventBus` publishing for telemetry, button, and error events
- structured `HardwareErrorEvent` reporting instead of silent failures
- debug service/session helpers for device-specific test actions
- device detail UI sections for capabilities, diagnostics, logs, and manual actions

Do not copy these goggle-specific patterns:

- HTTP hotspot registration through `POST /register`
- request-response commands like `/state`, `/health`, and `/capture`
- polling-heavy telemetry loops for routine cane data
- Wi-Fi address handling as the device connection identity

The cane equivalent should be BLE service scanning, notify subscriptions, command characteristic writes, heartbeat monitoring, and foreground-service-ready connection ownership.

## Stability Requirements

The cane implementation should include:

- service UUID filtering during BLE scan
- explicit BLE permission checks
- connection timeout
- notification subscription timeout
- bounded reconnect with backoff
- heartbeat timeout detection
- packet sequence deduplication
- structured error events
- debug logs for scan, connect, disconnect, packet parse, retry, and haptic write
- parser tests for all packet types
- adapter tests for all six button actions

For detailed failure handling, see [failure-modes.md](failure-modes.md).

## Non-Goals For First Pass

These are important, but should not block the first solid Flutter implementation:

- full native Android foreground service implementation
- iOS background BLE restoration
- backend persistence for cane events
- production pairing UX polish
- firmware OTA update flow

## Parallel Work Boundaries

The other assist-flow/backend work should depend only on resolved hardware events, not BLE internals.

Smart Cane branch should avoid changing:

- backend auth and safety APIs
- assist-flow screens
- app-wide routing unless needed for debug entry points
- shared session/network code

Smart Cane branch may safely change:

- `core/hardware/domain`
- `core/hardware/infrastructure/adapters`
- `core/hardware/infrastructure/transports`
- `core/hardware/infrastructure/manager`
- `core/hardware/providers`
- `features/debug`
- tests around hardware parsing, adapter behavior, and reconnect policy

## Success Criteria

The first complete Smart Cane Flutter slice is done when:

- a known cane auto-connects after app startup
- all three buttons emit single and double press events
- Button 3 double press emits the critical SOS event
- ultrasonic and battery packets parse into typed events
- the app can send haptic feedback to the cane
- disconnect and reconnect behavior is visible in debug UI
- parser and adapter tests cover the cane protocol
- implementation is ready to move behind an Android foreground service boundary
