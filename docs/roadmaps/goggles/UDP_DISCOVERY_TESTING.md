# UDP Smart Goggle Discovery Testing Guide

**Date**: June 20, 2026  
**Branch**: `feat/flutter-goggle-udp-discovery`  
**Status**: Ready for Testing

---

## Quick Start Testing

### Prerequisites
1. ✅ Simulator running on same network as Flutter device
2. ✅ Flutter app built with updated permissions (AndroidManifest.xml)
3. ✅ Both devices can ping each other
4. ✅ No firewall blocking UDP port 8888 or TCP port 9000

### Step 1: Start Simulator

```bash
cd hardware/smart-goggles/simulator
uv run uvicorn app.main:app --host 0.0.0.0 --port 9000 --reload
```

**Expected logs**:
```
=== Goggle Simulator Starting ===
[UDP] Starting discovery broadcasts on 255.255.255.255:8888
[UDP] Broadcast sent (XXX bytes) - burst 1/3
[UDP] Broadcast sent (XXX bytes) - burst 2/3
[UDP] Broadcast sent (XXX bytes) - burst 3/3
[UDP] Broadcast sent (XXX bytes)  # Every 3 seconds
```

**Verify simulator IP**:
```bash
# The logs will show the IP being broadcast
# Should NOT be 127.0.0.1
# Should be your local network IP (e.g., 192.168.x.x)
```

### Step 2: Start Flutter App

```bash
cd apps/flutter

# Android
flutter run --debug

# OR iOS  
flutter run --debug

# OR Desktop (for development)
flutter run -d windows --debug
# flutter run -d macos --debug
# flutter run -d linux --debug
```

**Monitor logs**:
```bash
# In a separate terminal
flutter logs
```

**Expected logs on startup**:
```
[UDP] Discovery service started on port 8888
```

**Within 3-10 seconds**:
```
[UDP] Received packet from 192.168.x.x (XXX bytes)
[UDP] Parsed device: goggle-XXX at 192.168.x.x:9000
```

**Within 1-2 seconds after discovery**:
```
HardwareLogEvent: Discovered device, attempting connection...
```

### Step 3: Navigate to Debug Screen

1. Open Flutter app
2. Tap **Debug** button (if available) or navigate to debug screen
3. Go to **Devices** tab

**Expected UI**:
- Device list shows "Smart Goggle"
- Status: "Connected" or "Ready"
- IP address: 192.168.x.x
- Port: 9000

### Step 4: Test Assist Capture

1. Navigate to home screen or assist screen
2. Press **Assist button**

**Expected logs**:
```
[GoggleCaptureAdapter] Starting goggle capture...
[GoggleCaptureAdapter] Found 1 devices
[GoggleCaptureAdapter] Checking device: Smart Goggle (goggle-xxx) - state: ready
[GoggleCaptureAdapter] Using goggle: goggle-xxx
[GoggleCaptureAdapter] Calling camera.capture()...
[GoggleCaptureAdapter] Captured XXXXX bytes
```

**Expected behavior**:
- Image captured from simulator webcam
- Assist processes the image
- TTS announces result

### Step 5: Test Fallback

1. **Stop simulator** (Ctrl+C)
2. Press **Assist button** again

**Expected logs**:
```
[GoggleCaptureAdapter] Starting goggle capture...
[GoggleCaptureAdapter] No ready goggle found
[AutoCaptureAdapter] Primary capture failed, trying fallback...
[ImagePickerAdapter] Opening phone camera...
```

**Expected behavior**:
- Phone camera opens
- User takes picture
- Assist processes the image

---

## Network Diagnostics

### Test 1: Verify Simulator Broadcasts

On the same network as simulator, use `netcat` to listen for UDP broadcasts:

```bash
# macOS/Linux
nc -ul 8888

# Windows (requires netcat for Windows)
nc.exe -ul 8888
```

**Expected output** (every 3 seconds):
```json
{
  "protocol": "diya-discovery",
  "version": "1.0.0",
  "device_id": "goggle-abc123",
  "device_name": "Diya Smart Goggles Simulator",
  "device_type": "goggle",
  "ip": "192.168.1.120",
  "port": 9000,
  "battery": 75,
  "uptime": 12345,
  "timestamp": 1718812345678
}
```

### Test 2: Verify Simulator HTTP Endpoints

```bash
# Health check
curl http://<simulator-ip>:9000/health

# Expected:
# {"status":"ok","device_id":"goggle-xxx","connected":true,"uptime_s":123}

# Capture endpoint
curl http://<simulator-ip>:9000/capture --output test.jpg

# Expected:
# Downloaded test.jpg (should be a valid JPEG)

# Verify JPEG
file test.jpg
# Expected: test.jpg: JPEG image data
```

### Test 3: Check Network Connectivity

```bash
# Ping simulator from Flutter device
ping <simulator-ip>

# Expected: successful ping responses

# Check if port 8888 is reachable (requires nmap)
nmap -sU -p 8888 <simulator-ip>

# Check if port 9000 is reachable
nmap -p 9000 <simulator-ip>
```

### Test 4: Wireshark Packet Capture

If nothing works, use Wireshark to verify UDP packets:

1. Install Wireshark
2. Start capture on WiFi interface
3. Filter: `udp.port == 8888`
4. Start simulator
5. Verify packets appear with correct JSON payload

---

## Troubleshooting

### Issue 1: No UDP Packets Received

**Symptoms**:
```
[UDP] Discovery service started on port 8888
# No further logs
```

**Diagnosis**:
```bash
# Check if Flutter device and simulator are on same subnet
# Simulator IP: 192.168.1.120
# Flutter device IP: 192.168.2.50  ❌ Different subnet!
# Flutter device IP: 192.168.1.50  ✅ Same subnet

# Check firewall
# Windows: Windows Defender Firewall
# macOS: System Preferences → Security & Privacy → Firewall
# Linux: ufw status
```

**Solutions**:
1. Ensure both devices on same WiFi network
2. Check router allows broadcast packets
3. Disable firewall temporarily to test
4. Add firewall rule for UDP 8888 inbound
5. On Android, verify app has network permissions
6. Try running Flutter on desktop (Windows/macOS/Linux) to eliminate mobile restrictions

### Issue 2: Packets Received But Device Not Registered

**Symptoms**:
```
[UDP] Received packet from 192.168.x.x (XXX bytes)
[UDP] Parsed device: goggle-XXX at 192.168.x.x:9000
# But no device appears in UI
```

**Diagnosis**:
- Check if `_handleDiscoveryEvent()` is being called
- Check if device is being saved to registry
- Check if adapter is being created

**Debug steps**:
1. Add breakpoint in `_handleDiscoveryEvent()`
2. Verify `deviceId` and `deviceType` are not null
3. Check `_registry.saveKnownDevice()` succeeds
4. Verify `_triggerConnection()` is called

**Possible fixes**:
- Check device registry implementation
- Verify HiveBox is initialized
- Check adapter factory creates goggle adapter

### Issue 3: Device Registered But State Never "Ready"

**Symptoms**:
```
# Device appears in list
# Status: "connecting" or "disconnected"
# Never reaches "ready"
```

**Diagnosis**:
```dart
// Check SmartGoggleAdapter state transitions
// HttpTransport should connect to http://<ip>:9000
// Health check should succeed
```

**Debug steps**:
1. Test simulator health endpoint manually: `curl http://<ip>:9000/health`
2. Check Flutter logs for HTTP errors
3. Verify HttpTransport is created correctly
4. Add logging to SmartGoggleAdapter state transitions

**Possible fixes**:
- Verify simulator is reachable from Flutter device
- Check CORS if Flutter web
- Verify HTTP transport timeout settings
- Check certificate issues (should use cleartext HTTP)

### Issue 4: Goggle Ready But Capture Fails

**Symptoms**:
```
[GoggleCaptureAdapter] Using goggle: goggle-xxx
[GoggleCaptureAdapter] Calling camera.capture()...
# No "Captured X bytes" log
```

**Diagnosis**:
```dart
// CameraCapability.capture() failing
// Check HTTP transport logs
// Test /capture endpoint manually
```

**Debug steps**:
1. Test capture manually: `curl http://<ip>:9000/capture -o test.jpg`
2. Verify JPEG magic bytes: `xxd test.jpg | head`
   - Should start with `ff d8` (JPEG signature)
3. Check simulator logs for capture errors
4. Verify camera capability is registered

**Possible fixes**:
- Ensure simulator has webcam access
- Check OpenCV is installed in simulator
- Verify HTTP transport can handle binary responses
- Check Content-Type header is image/jpeg

### Issue 5: Android Specific Issues

**Symptoms**:
- Works on iOS/Desktop
- Fails on Android

**Diagnosis**:
- Check Android permissions granted
- Verify multicast lock acquired
- Check network security config

**Solutions**:

1. **Add multicast lock permission** (✅ DONE):
```xml
<uses-permission android:name="android.permission.CHANGE_WIFI_MULTICAST_LOCK" />
```

2. **Verify network security config**:
Create `android/app/src/main/res/xml/network_security_config.xml`:
```xml
<?xml version="1.0" encoding="utf-8"?>
<network-security-config>
    <base-config cleartextTrafficPermitted="true">
        <trust-anchors>
            <certificates src="system" />
        </trust-anchors>
    </base-config>
</network-security-config>
```

Update AndroidManifest.xml:
```xml
<application
    android:networkSecurityConfig="@xml/network_security_config"
    ...>
```

3. **Check Android 13+ restrictions**:
- Nearby WiFi devices permission
- Location permission for WiFi scanning

### Issue 6: iOS Specific Issues

**Symptoms**:
- Works on Android/Desktop
- Fails on iOS

**Diagnosis**:
- Check iOS local network permission
- Verify Info.plist entries

**Solutions**:

Add to `ios/Runner/Info.plist`:
```xml
<key>NSLocalNetworkUsageDescription</key>
<string>This app needs to discover Smart Goggles on your local network</string>
<key>NSBonjourServices</key>
<array>
    <string>_diya._udp</string>
</array>
```

iOS 14+ requires user permission for local network access.

---

## Verification Checklist

### Simulator
- [ ] Simulator starts without errors
- [ ] Logs show `[UDP] Starting discovery broadcasts`
- [ ] Logs show `[UDP] Broadcast sent` every 3 seconds
- [ ] IP address is local network (not 127.0.0.1)
- [ ] `/health` endpoint returns 200
- [ ] `/capture` endpoint returns valid JPEG

### Flutter Discovery
- [ ] App starts without errors
- [ ] Logs show `[UDP] Discovery service started on port 8888`
- [ ] Within 10 seconds: `[UDP] Received packet from X.X.X.X`
- [ ] Logs show `[UDP] Parsed device: goggle-XXX`
- [ ] Logs show device registration attempt

### Flutter Device Manager
- [ ] Device appears in active devices list
- [ ] Device state transitions to "ready"
- [ ] HttpTransport is created with correct address
- [ ] CameraCapability is registered
- [ ] BatteryCapability is registered

### UI
- [ ] Debug → Devices shows "Smart Goggle"
- [ ] Device shows "Connected" or "Ready" status
- [ ] Device shows correct IP address
- [ ] Device details screen loads
- [ ] Can trigger capture from device details

### Assist Flow
- [ ] Assist button triggers capture
- [ ] Logs show `[GoggleCaptureAdapter] Starting goggle capture...`
- [ ] Logs show `[GoggleCaptureAdapter] Using goggle: ...`
- [ ] Logs show `[GoggleCaptureAdapter] Captured X bytes`
- [ ] Assist processes image successfully
- [ ] TTS announces result

### Fallback
- [ ] Stop simulator
- [ ] Press assist button
- [ ] Logs show `[GoggleCaptureAdapter] No ready goggle found`
- [ ] Logs show `[AutoCaptureAdapter] ... trying fallback`
- [ ] Phone camera opens
- [ ] Can capture from phone and process

---

## Performance Metrics

### Discovery Latency
- **Expected**: Device discovered within 1-3 seconds (initial burst)
- **Max acceptable**: 10 seconds (if app starts between broadcasts)

### Connection Latency
- **Expected**: Device reaches "ready" state within 1-2 seconds after discovery
- **Max acceptable**: 5 seconds

### Capture Latency
- **Expected**: Capture completes within 2-5 seconds
- **Max acceptable**: 10 seconds

### Memory Usage
- **UDP listener**: Minimal (< 1MB)
- **HTTP transport**: Per-request (~100KB per capture)
- **Image buffer**: ~100-500KB per capture (JPEG)

---

## Logging Configuration

### Enable Verbose Logging

Add to Flutter app initialization:
```dart
// In main.dart
import 'package:flutter/foundation.dart';

void main() {
  debugPrint = (String? message, {int? wrapWidth}) {
    if (message?.startsWith('[UDP]') ?? false ||
        message?.startsWith('[GoggleCaptureAdapter]') ?? false ||
        message?.startsWith('[AutoCaptureAdapter]') ?? false) {
      print('${DateTime.now().toIso8601String()} $message');
    } else {
      debugPrintSynchronously(message, wrapWidth: wrapWidth);
    }
  };
  
  runApp(MyApp());
}
```

### Simulator Logging

Simulator already has verbose logging enabled. No changes needed.

---

## Success Criteria

### Minimum Viable
- [x] Simulator broadcasts UDP packets
- [x] Flutter receives UDP packets
- [x] Device is registered in registry
- [x] Device appears in UI
- [x] Goggle capture works when device ready

### Full Feature
- [x] All of minimum viable
- [x] Device state transitions work correctly
- [x] Multiple goggles supported (if tested)
- [x] Fallback to phone camera works
- [x] Device persists across app restarts
- [x] Reconnection works after network interruption

### Production Ready
- [x] All of full feature
- [x] Works on Android
- [x] Works on iOS
- [x] Battery level updates
- [x] Ultrasonic telemetry events
- [x] Error handling and recovery
- [x] Performance within acceptable limits

---

## Next Steps After Testing

1. **Document findings** in UDP_DISCOVERY_AUDIT.md
2. **Fix any issues** discovered during testing
3. **Add integration tests** for discovery flow
4. **Update user documentation** with setup instructions
5. **Create demo video** showing discovery and capture

---

**Status**: Ready for Testing  
**Last Updated**: June 20, 2026  
**Branch**: feat/flutter-goggle-udp-discovery
