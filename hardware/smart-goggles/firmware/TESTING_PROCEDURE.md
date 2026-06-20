# Smart Goggle Camera Testing Procedure

**Date**: June 20, 2026  
**Branch**: `feat/goggle-camera-debug`  
**Hardware**: ESP32-S3-N16R8 + OV5640 Camera Module  
**Issue**: Camera captures show corruption (green tint, horizontal blocks, darkness)

---

## Prerequisites

### Software Requirements
- ✅ PlatformIO installed (VS Code extension or CLI)
- ✅ ESP32-S3 toolchain installed (via PlatformIO)
- ✅ esptool.py available
- ✅ Serial monitor software (PlatformIO built-in or Putty/screen)
- ✅ curl or similar HTTP client

### Hardware Requirements
- ✅ ESP32-S3-N16R8 development board
- ✅ OV5640 camera module (or compatible)
- ✅ USB-C cable (data cable, not charge-only)
- ✅ WiFi network (2.4 GHz)
- ⚠️ Multimeter (for pin verification if needed)

### Before Starting
1. Ensure ESP32-S3 is connected via USB
2. Verify COM port (Windows) or /dev/tty* (Linux/Mac)
3. Update `upload_port` in `platformio.ini` if needed
4. Update WiFi credentials in `src/config.h`:
   ```cpp
   #define DEFAULT_WIFI_SSID "YourNetworkName"
   #define DEFAULT_WIFI_PASSWORD "YourPassword"
   ```

---

## Step 1: Clean Build Environment

Remove any cached build artifacts from previous configurations:

```bash
cd hardware/smart-goggles/firmware

# Clean build artifacts
pio run --target clean

# Remove entire build directory (more thorough)
rm -rf .pio/build   # Linux/Mac
# OR
rmdir /s .pio\build # Windows CMD
# OR
Remove-Item -Recurse -Force .pio\build  # Windows PowerShell
```

**Expected result**: `.pio/build` directory removed

---

## Step 2: Verify Configuration

Check that `platformio.ini` has the correct environment:

```bash
cat platformio.ini | grep -A 20 "\[env:esp32-s3-n16r8\]"
# OR on Windows:
type platformio.ini | findstr /N "env:esp32-s3-n16r8"
```

**Expected configuration**:
```ini
[env:esp32-s3-n16r8]
platform = espressif32
board = 4d_systems_esp32s3_gen4_r8n16
framework = arduino
board_build.arduino.memory_type = qio_opi
board_build.partitions = default_16MB.csv
```

**Critical settings**:
- ✅ `board = 4d_systems_esp32s3_gen4_r8n16` (NOT esp32-s3-devkitc-1)
- ✅ `board_build.arduino.memory_type = qio_opi` (enables OPI PSRAM)
- ✅ `lib_deps` includes `espressif/esp32-camera@^2.0.13`

---

## Step 3: Build Firmware

Build the firmware and verify the build output:

```bash
pio run -e esp32-s3-n16r8
```

**Watch for these in build output**:
```
PLATFORM: Espressif 32 (7.0.1) > 4D Systems ESP32-S3 gen4-R8N16
HARDWARE: ESP32S3 240MHz, 320KB RAM, 16MB Flash
```

**❌ WRONG** (indicates wrong board):
```
PLATFORM: Espressif 32 (7.0.1) > Espressif ESP32-S3-DevKitC-1-N8 (8 MB QD, No PSRAM)
```

**Expected result**: Build succeeds without errors, correct board definition shown

---

## Step 4: Full Flash Erase

Erase the entire flash to ensure clean state:

```bash
# Find your COM port first
pio device list

# Erase flash (adjust COM3 to your port)
esptool.py --chip esp32s3 --port COM3 erase_flash

# OR on Linux/Mac:
esptool.py --chip esp32s3 --port /dev/ttyUSB0 erase_flash
```

**Expected output**:
```
Chip erase completed successfully in X.Xs
```

**⚠️ Warning**: This erases everything including NVS partitions

---

## Step 5: Upload Firmware

Upload the freshly built firmware:

```bash
pio run -e esp32-s3-n16r8 --target upload
```

**Expected output**:
```
Writing at 0x... (100%)
Wrote XXXXX bytes at 0x00010000 in X.X seconds
Hash of data verified.
Leaving...
Hard resetting via RTS pin...
```

**If upload fails**:
- Check USB cable (use a data cable, not charge-only)
- Verify COM port in `platformio.ini`
- Try holding BOOT button while connecting USB
- Check device manager (Windows) for driver issues

---

## Step 6: Monitor Serial Output

Start the serial monitor to watch boot sequence:

```bash
pio device monitor -e esp32-s3-n16r8
```

**Press RESET button on ESP32-S3 to see boot sequence**

### Expected Boot Output

```
==================================================
  Diya Smart Goggle Firmware
==================================================
[BOOT] Firmware Version : 1.0.0
[BOOT] Device Type      : goggle
[BOOT] Build target     : ESP32-S3-WROOM-1-N16R8
[BOOT] Board definition : 4d_systems_esp32s3_gen4_r8n16
[BOOT] memory_type      : qio_opi
[BOOT] Camera XCLK      : 16000000 Hz
[BOOT] PSRAM mode gate  : xclk==16MHz → ACTIVE
[BOOT] Chip model       : ESP32-S3 rev 0
[BOOT] CPU cores        : 2
[BOOT] Flash size       : 16777216 bytes (16 MB)
[MEM]  Total Heap       : 390140 bytes
[MEM]  Free Heap        : 352000 bytes
[MEM]  PSRAM Found      : YES
[MEM]  PSRAM Size        : 8388608 bytes (8 MB)
[MEM]  Free PSRAM        : 8355840 bytes
[MEM]  Largest PSRAM blk : 4194304 bytes
==================================================
[INIT] Device state initialized
[INIT] Telemetry initialized
[INIT] Buttons initialized
[INIT] Initializing camera...
[CAM]  ── Camera Init ────────────────────────────
[CAM]  PSRAM free before init : 8355840 bytes
[CAM]  XCLK: 16000000 Hz — psram_mode WILL be active
[CAM]  PSRAM free after init  : 5120000 bytes (approx)
[CAM]  PSRAM used by camera   : 3235840 bytes (approx)
[CAM]  Sensor settings applied (optimized for text/OCR)
[CAM]  ── Sensor Identity ──────────────────────
[CAM]  Sensor       : OV5640 (or OV2640)
[CAM]  PID          : 0x5640 (or 0x2642)
[CAM]  MIDH         : 0x56
[CAM]  MIDL         : 0x40
[CAM]  MID (joined) : 0x5640
[CAM]  Resolution   : 1024x768
[CAM]  JPEG Quality : 12 (0=best, 63=worst)
[CAM]  XCLK         : 16000000 Hz
[CAM]  PSRAM mode   : ENABLED (xclk==16MHz: YES)
[CAM]  FB Count     : 2
[CAM]  FB Location  : PSRAM
[CAM]  Grab Mode    : LATEST
[CAM]  Free Heap    : 350000 bytes
[CAM]  Free PSRAM   : 5120000 bytes
[CAM]  Largest PSRAM blk : 2097152 bytes
[CAM]  ─────────────────────────────────────────
[CAM]  Camera initialized successfully
[INIT] Camera initialized successfully
[WIFI] Connecting...
.....
[WIFI] Connected!
[WIFI] IP Address : 192.168.x.x
[WIFI] RSSI       : -45 dBm
[HTTP] Server started on port 9000
[READY] Smart Goggle is ready!
[READY] Access at: http://192.168.x.x:9000
```

### Record These Values

Create a test log file and record:

```
Date/Time: _______________
Branch: feat/goggle-camera-debug
Commit: _______________

PSRAM Found: YES / NO
PSRAM Size: _________ bytes
Sensor Model: _________
Sensor PID: 0x_______
XCLK: _________ Hz
PSRAM Mode: ENABLED / DISABLED
Free PSRAM after init: _________ bytes
Camera Init: SUCCESS / FAILED
WiFi Connected: YES / NO
IP Address: _________
```

---

## Step 7: Capture Test Image

From another machine on the same network:

```bash
# Replace IP with your device's IP
curl http://192.168.x.x:9000/capture -o test_capture_1.jpg

# Capture multiple images for comparison
curl http://192.168.x.x:9000/capture -o test_capture_2.jpg
curl http://192.168.x.x:9000/capture -o test_capture_3.jpg
```

### Expected Serial Logs During Capture

```
[CAPTURE] Starting capture #1
[CAPTURE] Pre-capture  heap=348000  psram=5110000
[CAPTURE] Resolution  : 1024x768
[CAPTURE] Format      : JPEG
[CAPTURE] Size        : 143872 bytes
[CAPTURE] Duration    : 125 ms
[CAPTURE] Heap after  : 348000 bytes
[CAPTURE] PSRAM after : 5110000 bytes
[CAPTURE] SUCCESS
```

### Record Capture Metrics

```
Capture #1:
  Size: _________ bytes
  Duration: _________ ms
  Format: JPEG / OTHER
  Status: SUCCESS / FAILED

Capture #2:
  Size: _________ bytes
  Duration: _________ ms
  Format: JPEG / OTHER
  Status: SUCCESS / FAILED

Capture #3:
  Size: _________ bytes
  Duration: _________ ms
  Format: JPEG / OTHER
  Status: SUCCESS / FAILED
```

---

## Step 8: Analyze Captured Images

Open each test image in an image viewer:

```bash
# Windows
start test_capture_1.jpg

# macOS
open test_capture_1.jpg

# Linux
xdg-open test_capture_1.jpg
```

### Image Quality Checklist

For each captured image, check:

| Criterion | Expected | Actual | Pass/Fail |
|-----------|----------|--------|-----------|
| File opens successfully | YES | _____ | _____ |
| Image shows scene | YES | _____ | _____ |
| Resolution | 1024x768 | _____ | _____ |
| Color accuracy | Natural colors | _____ | _____ |
| Green tint present | NO | _____ | _____ |
| Horizontal blocks | NO | _____ | _____ |
| Vertical artifacts | NO | _____ | _____ |
| Overall brightness | Normal | _____ | _____ |
| Text readability (if any) | Readable at 0.5m | _____ | _____ |
| Focus | Sharp | _____ | _____ |
| Exposure | Balanced | _____ | _____ |

### Corruption Pattern Analysis

If corruption is present, describe the pattern:

```
Corruption Description:
- Location: [ ] Entire image [ ] Top half [ ] Bottom half [ ] Random blocks
- Color shift: [ ] Green tint [ ] Red tint [ ] Blue tint [ ] Grayscale [ ] Other: _____
- Pattern: [ ] Horizontal lines [ ] Vertical lines [ ] Blocks [ ] Noise [ ] Other: _____
- Consistency: [ ] Same in all captures [ ] Different each time
- Severity: [ ] Minor [ ] Moderate [ ] Severe [ ] Unusable
```

---

## Step 9: Test Other Endpoints

Verify that other functionality works:

```bash
# Health check
curl http://192.168.x.x:9000/health

# Device state
curl http://192.168.x.x:9000/state

# Register phone (test endpoint)
curl -X POST http://192.168.x.x:9000/register-phone \
  -H "Content-Type: application/json" \
  -d '{"phone_ip": "192.168.1.100", "port": 8080}'
```

### Expected Responses

**Health endpoint**:
```json
{
  "status": "ok",
  "device_id": "goggle-abc123",
  "firmware_version": "1.0.0"
}
```

**State endpoint**:
```json
{
  "device_id": "goggle-abc123",
  "connected": true,
  "battery_level": 75,
  "telemetry": {
    "battery": 75,
    "wifi_rssi": -45,
    "uptime": 12345,
    "heap_free": 340000,
    "heap_min": 320000,
    "camera": "ok",
    "buttons": "ok",
    "ip": "192.168.x.x",
    "captures": 3,
    "capture_failures": 0
  }
}
```

---

## Step 10: Physical Pin Verification (If Needed)

If image corruption persists, verify physical connections:

### Tools Needed
- Multimeter (continuity mode)
- Camera module pinout diagram
- ESP32-S3 pinout diagram

### Verification Procedure

1. **Power off the device**
2. Set multimeter to continuity mode (beep)
3. For each signal, verify continuity:
   - Place one probe on ESP32-S3 GPIO pin
   - Place other probe on camera module pin
   - Should beep if connected

### Pin Verification Table

| Signal | ESP32-S3 GPIO | Camera Pin | Continuity | Notes |
|--------|---------------|------------|------------|-------|
| XCLK   | GPIO 15       | XCLK       | ☐ PASS ☐ FAIL | |
| SIOD   | GPIO 4        | SDA        | ☐ PASS ☐ FAIL | |
| SIOC   | GPIO 5        | SCL        | ☐ PASS ☐ FAIL | |
| D0     | GPIO 11       | D0/Y2      | ☐ PASS ☐ FAIL | |
| D1     | GPIO 9        | D1/Y3      | ☐ PASS ☐ FAIL | |
| D2     | GPIO 8        | D2/Y4      | ☐ PASS ☐ FAIL | |
| D3     | GPIO 10       | D3/Y5      | ☐ PASS ☐ FAIL | |
| D4     | GPIO 12       | D4/Y6      | ☐ PASS ☐ FAIL | |
| D5     | GPIO 18       | D5/Y7      | ☐ PASS ☐ FAIL | |
| D6     | GPIO 17       | D6/Y8      | ☐ PASS ☐ FAIL | |
| D7     | GPIO 16       | D7/Y9      | ☐ PASS ☐ FAIL | |
| VSYNC  | GPIO 6        | VSYNC      | ☐ PASS ☐ FAIL | |
| HREF   | GPIO 7        | HREF       | ☐ PASS ☐ FAIL | |
| PCLK   | GPIO 13       | PCLK       | ☐ PASS ☐ FAIL | |
| 3.3V   | 3.3V          | VCC        | ☐ PASS ☐ FAIL | Measure voltage: _____ V |
| GND    | GND           | GND        | ☐ PASS ☐ FAIL | |

**⚠️ Important**: Some camera modules label data pins as Y2-Y9 instead of D0-D7

---

## Troubleshooting

### Issue: PSRAM Not Detected

**Symptoms**:
```
[MEM]  PSRAM Found      : NO
[FATAL] PSRAM NOT DETECTED
```

**Solutions**:
1. Verify `platformio.ini` uses `board = 4d_systems_esp32s3_gen4_r8n16`
2. Verify `board_build.arduino.memory_type = qio_opi`
3. Run full erase: `esptool.py --chip esp32s3 erase_flash`
4. Re-flash firmware
5. Check hardware: Ensure you have ESP32-S3-N16R8 (not N8 or N4)

### Issue: Camera Init Failed

**Symptoms**:
```
[CAM]  Init attempt 1 failed: ESP_ERR_NOT_FOUND (err=0x105)
```

**Solutions**:
1. Check camera module power (3.3V, not 5V!)
2. Verify SIOD (GPIO 4) and SIOC (GPIO 5) connections
3. Try different camera module (may be defective)
4. Check for loose connections
5. Verify camera module is OV5640 or OV2640

### Issue: WiFi Won't Connect

**Symptoms**:
```
[WIFI] Connection failed
```

**Solutions**:
1. Verify SSID and password in `src/config.h`
2. Ensure WiFi is 2.4 GHz (ESP32 doesn't support 5 GHz)
3. Move closer to router
4. Check router firewall settings
5. Try different WiFi network

### Issue: Capture Returns HTTP 503

**Symptoms**:
```
HTTP/1.1 503 Service Unavailable
{"error": "Camera not available"}
```

**Solutions**:
1. Camera init failed - check serial logs
2. Camera may be reinitializing - wait 5 seconds and retry
3. Memory exhausted - check heap logs
4. Power supply insufficient - try powered USB hub

---

## Success Criteria

### ✅ Test Passes If:
- [x] PSRAM detected (8 MB)
- [x] Camera initializes successfully
- [x] Sensor PID is valid (OV5640: 0x5640, OV2640: 0x2642)
- [x] WiFi connects
- [x] Capture returns 200 OK
- [x] JPEG size is 50-250 KB
- [x] Image opens in viewer
- [x] Image shows correct scene
- [x] No green tint
- [x] No horizontal/vertical artifacts
- [x] Text is readable (if present)
- [x] Colors are natural
- [x] Exposure is balanced

### ❌ Test Fails If:
- [ ] PSRAM not detected
- [ ] Camera init fails after retries
- [ ] Sensor PID shows "Unknown" or 0x0000
- [ ] WiFi fails to connect
- [ ] Capture returns error
- [ ] JPEG size < 10 KB or > 500 KB
- [ ] Image won't open
- [ ] Image is black or white
- [ ] Severe corruption present
- [ ] Text is unreadable
- [ ] Colors are wildly inaccurate

---

## Reporting Results

After completing all tests, update `docs/roadmaps/goggles/CAMERA_DEBUG_REPORT.md`:

1. Copy serial logs to report
2. Attach sample captured images (good and bad)
3. Document any pin verification findings
4. Note any configuration changes made
5. Describe next steps based on findings

**Report template**:
```markdown
## Test Results - [Date]

### Hardware
- Board: ESP32-S3-N16R8
- Camera: OV5640 / OV2640 / Unknown
- Sensor PID: 0x____

### Configuration
- PSRAM: Detected / Not Detected
- PSRAM Size: _____ MB
- XCLK: _____ Hz
- PSRAM Mode: Enabled / Disabled

### Image Quality
- Resolution: _____x_____
- File Size: _____ KB
- Corruption: None / Minor / Severe
- Pattern: _____

### Conclusion
- Status: PASS / FAIL
- Root Cause: _____
- Next Steps: _____
```

---

## Files to Preserve

Save these for analysis:
- Serial log output (`serial_output.txt`)
- Captured test images (`test_capture_*.jpg`)
- Pin verification results (photo or checklist)
- Configuration files used (`platformio.ini`, `config.h`)

---

## Next Steps After Testing

Based on test results:

1. **If images are clean**: ✅ Issue resolved, document solution
2. **If corruption persists**: Continue to pin verification
3. **If sensor not detected**: Check I2C connections (SIOD/SIOC)
4. **If PSRAM not detected**: Review platformio.ini configuration

See `CAMERA_DEBUG_REPORT.md` for detailed troubleshooting guides.
