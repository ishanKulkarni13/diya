# Diya Cane Protocol v1

This document is the definitive source of truth for the Diya Smart Cane BLE protocol.

## Bluetooth GATT Profile

The Diya Cane implements a custom BLE GATT service to prevent accidental pairing with generic devices.

*   **Service UUID**: `1b050001-c852-4752-b883-fa4c0342ab01`
*   **TX Characteristic UUID**: `1b050002-c852-4752-b883-fa4c0342ab01` (App writes to Cane)
    *   Properties: `Write`, `Write Without Response`
*   **RX Characteristic UUID**: `1b050003-c852-4752-b883-fa4c0342ab01` (Cane notifies App)
    *   Properties: `Read`, `Notify`

## Protocol Format

All messages exchanged over the TX and RX characteristics must be serialized as JSON strings.

### Payload Rules
1.  **Versioning**: Every message MUST contain an integer version field `v`.
2.  **Type**: Every message MUST contain a string type field `t`.
3.  **Forward Compatibility**: Receivers MUST ignore any unknown fields.
4.  **Resilience**: Malformed payloads MUST be safely ignored by the receiver without severing the connection.

## Message Types

### 1. Hello Handshake (Cane -> App)
Transmitted immediately by the cane upon a successful BLE connection.
```json
{
  "v": 1,
  "t": "hello",
  "protocol": 1,
  "firmware": "1.0.0"
}
```

### 2. Heartbeat (Cane -> App)
Transmitted periodically by the cane (default: every 5 seconds). The app uses this to maintain the `ConnectionCoordinator` health state.
```json
{
  "v": 1,
  "t": "heartbeat"
}
```

### 3. Button Press (Cane -> App)
Transmitted when a physical button on the cane is pressed.
```json
{
  "v": 1,
  "t": "button",
  "button": 1,
  "press": "single" // Enums: "single", "double", "long"
}
```
