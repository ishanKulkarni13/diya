# Smart Cane BLE Transport Architecture

This document describes the BLE foundation layer for the Smart Cane.

## GATT Contract
*   **Service UUID**: `0000ffe0-0000-1000-8000-00805f9b34fb`
*   **RX/TX Characteristic UUID**: `0000ffe1-0000-1000-8000-00805f9b34fb`
*   **MTU Expectations**: The client requests an MTU of 512 upon connection to handle larger JSON payloads efficiently.
*   **Notification Requirements**: The client MUST subscribe to the RX characteristic to receive JSON events and heartbeats from the cane.

## Boundaries
The BLE Transport layer (`BleTransportImpl`) is strictly responsible for:
- Device Scanning
- Connection Establishment
- Characteristic Discovery & Subscription
- Raw Read/Writes

It does NOT handle business logic, SOS workflows, Gemini interactions, or UI updates.

## Connection State Ownership
The `ConnectionCoordinator` is the definitive source of truth for connection health. 
It oversees:
- **Heartbeat Monitoring**: The heartbeat timer resets upon receiving any valid JSON payload. If it times out, the connection enters a `degraded` state.
- **Reconnection**: It integrates with the `BackoffStrategy` to retry connections silently and infinitely with exponential backoff on unexpected disconnects.
- **State Machine**: Transitions through `idle`, `connecting`, `ready`, `degraded`, `reconnecting`, `failed`, and `disconnected`.

## Protocol & Validation
All payloads must conform to the documented JSON structure. The protocol uses the `CaneMessageDto` to ensure strict validation of fields (`v` and `t`). Malformed JSON payloads are intercepted and safely discarded at the parsing boundary without crashing the transport or severing the connection.

## Persistence
Discovered and paired devices are stored in the `DeviceRegistry` as `KnownDevice` entities. This persists the `Device Identifier` (MAC address), `Device Name`, and `Last Seen Timestamp`, allowing automatic reconnection flows on app startup.
