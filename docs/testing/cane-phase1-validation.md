# Smart Cane Phase 1 Validation Guide

This document outlines the exact hardware verification procedure for the Diya Smart Cane ESP32 Reference Firmware and the Flutter Application.

## Prerequisites
1.  **ESP32 Dev Module**: Ensure it is connected via USB.
2.  **Arduino IDE**: Installed and configured for the `ESP32 Dev Module`.
3.  **Physical Device**: An Android or iOS phone running the Diya Flutter application (Simulators cannot scan BLE).

## Verification Steps

### Step 1: Flash Firmware
*   Open `hardware/cane/reference-firmware/reference-firmware.ino` in Arduino IDE.
*   Select your ESP32 board and COM port.
*   Compile and upload.
*   **Expected Result**: Arduino IDE reports "Hard resetting via RTS pin...". Serial monitor (115200 baud) prints "Starting Diya Cane BLE Server..." and "Advertising started."

### Step 2: Launch App
*   Run the Diya Flutter app on a physical mobile device.
*   **Expected Result**: The app launches and requests Bluetooth and Location permissions (if not previously granted).

### Step 3: Scan for Devices
*   Ensure the ESP32 is powered on.
*   Navigate to the hardware scanning/pairing screen in the app.
*   **Expected Result**: The app discovers `DIYA_CANE_DEV` based on the `1b050001` UUID and lists it as an available device.

### Step 4: Connect
*   Tap on `DIYA_CANE_DEV` in the app to initiate a connection.
*   **Expected Result**: The app transitions the device state to `Connecting`, then `Ready`. The ESP32 Serial Monitor prints "Sent handshake...".

### Step 5: Observe Heartbeat
*   Wait for 5-10 seconds while monitoring the app logs and the ESP32 Serial Monitor.
*   **Expected Result**: The ESP32 does not crash. The Flutter app's `ConnectionCoordinator` receives the `{"v":1,"t":"heartbeat"}` JSON, maintaining the `Ready` state without falling back to `Degraded`.

### Step 6: Press Button
*   Press the `BOOT` button (GPIO 0) on the ESP32 Dev Module.
*   **Expected Result**: The ESP32 Serial Monitor prints "Button pressed: {"v":1,"t":"button"...}". The Flutter application receives the event, strictly parses the `CaneMessageDto`, and publishes a `ButtonPressEvent` on the `HardwareEventBus`.

### Step 7: Power off ESP32 (Disconnect Test)
*   Unplug the USB cable powering the ESP32.
*   **Expected Result**: The Flutter app detects the disconnection within a few seconds. The device state transitions to `Reconnecting`.

### Step 8: Power on ESP32 (Reconnect Test)
*   Plug the USB cable back in. Wait for the ESP32 to boot and start advertising.
*   **Expected Result**: The Flutter app's `ConnectionCoordinator` background backoff strategy automatically finds the device, connects, and restores the state to `Ready` without any user interaction.

---

## Validation Status
*   **Architecture**: Complete
*   **Implementation**: Complete
*   **Hardware Verification**: Pending
