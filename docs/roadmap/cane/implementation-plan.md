# Smart Cane Phase 1 — BLE Foundation Implementation Plan

This plan outlines the steps to build a production-quality BLE foundation for the Smart Cane subsystem.

## 1. Setup & Permissions
*   Add `flutter_blue_plus` to dependencies.
*   Update `AndroidManifest.xml` (BLUETOOTH_SCAN, BLUETOOTH_CONNECT, ACCESS_FINE_LOCATION).
*   Update `Info.plist` (NSBluetoothAlwaysUsageDescription).
*   Create a dedicated `BlePermissionService` to centralize permission checks, separate from the transport logic.

## 2. BLE Transport Implementation (`BleTransportImpl`)
*   **Discovery**: Implement BLE scanning with timeouts and device filtering.
*   **Connection**: Handle connection establishment, MTU requests, and service discovery.
*   **Communication**: Subscribe to GATT characteristics (RX for incoming JSON events, TX for writes).
*   **Reconnection**: Integrate with the existing `BackoffStrategy` to handle unexpected disconnects automatically.

## 3. Protocol & JSON Handling
*   Create Data Transfer Objects (DTOs) for the incoming JSON format (e.g., `{"type": "sos", "v": 1, ...}`).
*   Implement strict validation: safely catch and discard malformed payloads instead of crashing.
*   Map validated DTOs to the existing `HardwareEvent` domain models.

## 4. Heartbeat & State Machine
*   Implement a heartbeat timer inside the transport layer.
*   Reset the timer upon receiving any valid payload from the cane.
*   If the timer expires, transition to the `degraded` state and initiate the reconnection sequence.
*   Emit connectivity state changes to the `HardwareEventBus`.

## 5. Architecture & DI Integration
*   Ensure the BLE implementation strictly adheres to the transport interface. It must not contain business logic related to Assist, Gemini, or the UI.
*   Update `hardware_providers.dart` to inject the new BLE transport.
