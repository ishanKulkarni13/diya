# Smart Goggle Camera Debug Report

**Date**: June 20, 2026  
**Hardware**: ESP32-S3-N16R8 (16 MB Flash, 8 MB OPI PSRAM)  
**Branch**: `feat/goggle-camera-debug`  
**Issue**: Captured images show heavy corruption with horizontal blocks, green tint, and dark areas

---

## Current Status

### Working
- ✅ Firmware flashes successfully
- ✅ Device boots
- ✅ WiFi connects
- ✅ HTTP server works
- ✅ `/capture` endpoint returns an image
- ✅ Telemetry works
- ✅ Ultrasonic telemetry works
- ✅ Buttons work
- ✅ PSRAM is detected and initialized

### Problem
- ❌ Captured image is heavily corrupted
- ❌ Horizontal blocks visible
- ❌ Green tint present
- ❌ Partial frame corruption
- ❌ Dark image overall

**Key observation**: The image is NOT random noise. The scene is recognizable, which means the camera IS partially working.

---

## Investigation Plan

### Phase 1: Camera Pin Verification
**Goal**: Verify that the camera pin configuration matches the actual ESP32-S3-OV5640 hardware

**Current pin configuration** (from `config.h`):
```c
#define CAM_PIN_PWDN    -1   // Power down: not connected
#define CAM_PIN_RESET   -1   // Reset: not connected
#define CAM_PIN_XCLK    15   // Master clock output to OV5640
#define CAM_PIN_SIOD    4    // SCCB data (I2C SDA)
#define CAM_PIN_SIOC    5    // SCCB clock (I2C SCL)

// Parallel data bus D0-D7 (8-bit DVP)
#define CAM_PIN_D7      16
#define CAM_PIN_D6      17
#define CAM_PIN_D5      18
#define CAM_PIN_D4      12
#define CAM_PIN_D3      10
#define CAM_PIN_D2      8
#define CAM_PIN_D1      9
#define CAM_PIN_D0      11

// Synchronisation signals
#define CAM_PIN_VSYNC   6    // Vertical sync
#define CAM_PIN_HREF    7    // Horizontal reference (HREF/HSYNC)
#define CAM_PIN_PCLK    13   // Pixel clock
```

**Action items**:
1. Cross-reference with ESP32-S3-CAM reference designs
2. Verify against OV5640 datasheet DVP interface requirements
3. Check for common ESP32-S3 camera module pinouts

### Phase 2: Enhanced Camera Diagnostics
**Goal**: Add comprehensive logging to understand exactly what's happening during camera init and capture

**Diagnostics to add**:

#### After camera init:
- Sensor PID (Product ID)
- MIDH (Manufacturer ID High byte)
- MIDL (Manufacturer ID Low byte)
- Sensor name (OV5640 vs OV2640 vs other)
- Free heap before/after
- Free PSRAM before/after
- Largest free PSRAM block
- Framebuffer count
- Framebuffer location verification

#### Before/after each capture:
- Free heap
- Free PSRAM
- Image width
- Image height
- Image size in bytes
- Pixel format
- Capture duration
- JPEG magic bytes validation

#### XCLK frequency analysis:
- Test different XCLK frequencies:
  - 20 MHz (current setting)
  - 16 MHz (recommended for PSRAM mode)
  - 10 MHz (conservative fallback)
- Document stability and image quality at each frequency

### Phase 3: XCLK Investigation

**CRITICAL FINDING from code review**:

The `camera_manager.h` contains this comment:
```c
// XCLK frequency
//
// CRITICAL: The esp32-camera driver (cam_hal.c) only enables psram_mode when:
//   cam_obj->psram_mode = (config->xclk_freq_hz == 16000000);
//
// With xclk_freq_hz = 20000000 (20 MHz), psram_mode = FALSE.
// This causes the driver to attempt DMA from internal SRAM instead of PSRAM,
// resulting in malloc failure, partial frames, green tint, and block corruption.
//
// REQUIRED: XCLK must be exactly 16000000 (16 MHz) to activate psram_mode.
```

**Current `config.h` setting**:
```c
#define CAMERA_XCLK_HZ       16000000      // 16 MHz — required for PSRAM DMA mode
```

**Status**: ✅ Already set to 16 MHz

The XCLK is already configured correctly for PSRAM mode. This suggests the corruption issue is NOT related to XCLK/PSRAM mode mismatch.

### Phase 4: OV5640 Sensor Detection
**Goal**: Verify that the OV5640 sensor is actually detected and responding correctly

**Action items**:
1. Read and log sensor PID
2. Verify PID matches OV5640_PID (check esp_camera library for the correct constant)
3. If PID doesn't match, investigate:
   - I2C communication issues (SIOD/SIOC pins)
   - Sensor power issues
   - Wrong sensor module installed

### Phase 5: Frame Size Investigation
**Goal**: Determine if FRAMESIZE_XGA is causing allocation or processing issues

**Current settings**:
- Frame size: `FRAMESIZE_XGA` (1024×768)
- JPEG quality: 12
- PSRAM available: 8 MB
- Expected frame buffer size: ~1.5 MB × 2 = ~3 MB

**Memory calculation**:
- XGA uncompressed: 1024 × 768 × 2 bytes (YUV) = 1,572,864 bytes ≈ 1.5 MB
- Two framebuffers: ~3 MB
- PSRAM capacity: 8 MB
- **Available headroom: 5 MB** ✅ Sufficient

**Action items**:
1. Verify actual PSRAM consumption during init
2. Test with smaller frame size (SVGA: 800×600) to rule out resolution-related issues
3. Document memory usage before/after init

### Phase 6: DMA Buffer Investigation
**Goal**: Verify that DMA buffers are correctly allocated in PSRAM, not internal SRAM

**Action items**:
1. Check `fb_location` is set to `CAMERA_FB_IN_PSRAM`
2. Verify no DRAM fallback is occurring
3. Log actual framebuffer allocation addresses to confirm PSRAM region

**Expected behavior**:
- Framebuffers should be allocated from PSRAM address range
- No malloc failures
- No fallback to internal SRAM

---

## Root Cause Hypotheses

### Hypothesis 1: Wrong Camera Pins ⚠️ LIKELY
**Symptoms match**: Partial corruption, recognizable but distorted image
**Mechanism**: If data pins (D0-D7) are partially wrong, some bits would be correct while others are garbage, producing the observed block corruption pattern.

**Evidence for**:
- Green tint suggests specific bit patterns (color channel corruption)
- Horizontal blocks suggest line-by-line data corruption
- Scene is recognizable → some pins are correct

**Evidence against**:
- Camera initializes successfully (SIOD/SIOC must be correct)
- Some data is captured correctly

**Priority**: HIGH - Verify pin configuration first

### Hypothesis 2: Sensor Not OV5640 ⚠️ POSSIBLE
**Symptoms match**: Corruption could occur if driver expects OV5640 but sensor is OV2640 or other model

**Mechanism**: Different sensors have different register maps and timing requirements

**Evidence for**:
- Would explain persistent corruption despite correct PSRAM setup

**Evidence against**:
- Camera initializes without error
- esp_camera library typically detects sensor type automatically

**Priority**: MEDIUM - Check sensor PID during init

### Hypothesis 3: I2C Communication Issues ❓ UNLIKELY
**Symptoms don't match**: If SIOD/SIOC were wrong, camera init would fail completely

**Evidence against**:
- Camera initializes successfully
- Can capture frames

**Priority**: LOW - Only investigate if other hypotheses are ruled out

### Hypothesis 4: Power/Clock Instability ❓ POSSIBLE
**Symptoms might match**: Unstable XCLK or power could cause intermittent corruption

**Evidence for**:
- Corruption pattern could suggest timing issues

**Evidence against**:
- XCLK is already set to recommended 16 MHz
- No random crashes or initialization failures

**Priority**: LOW - Test XCLK frequencies if pin configuration is verified correct

---

## Firmware Code Changes (If Needed)

Based on testing results, code changes may be needed. Here are prepared modifications:

### Change 1: Test Different Resolution (If Memory Suspected)

If XGA shows corruption but smaller resolutions work, modify `config.h`:

```cpp
// Test with SVGA instead of XGA
#define CAMERA_FRAME_SIZE    FRAMESIZE_SVGA  // 800x600 instead of 1024x768
```

### Change 2: Test Different XCLK (If Timing Suspected)

If 16 MHz shows issues, try 10 MHz (more conservative):

```cpp
// More conservative clock speed
#define CAMERA_XCLK_HZ       10000000      // 10 MHz instead of 16 MHz
```

**Warning**: This disables PSRAM mode per cam_hal.c logic. Only use if 16 MHz fails completely.

### Change 3: Adjust Sensor Settings (If Exposure Issues)

If image is too dark, modify `applySensorSettings()` in `camera_manager.h`:

```cpp
s->set_brightness(s, 1);      // Increase brightness (+1)
s->set_contrast(s, 1);        // Increase contrast (+1)
s->set_exposure_ctrl(s, 1);   // Ensure AEC is enabled
s->set_aec2(s, 1);            // Enable AEC DSP
```

### Change 4: Fix Pin Configuration (If Pins Are Wrong)

If pin verification reveals incorrect wiring, update `config.h`:

**Example**: If D5 and D6 are swapped:
```cpp
// BEFORE:
#define CAM_PIN_D5      18
#define CAM_PIN_D6      17

// AFTER:
#define CAM_PIN_D5      17  // Swapped
#define CAM_PIN_D6      18  // Swapped
```

### Change 5: Add Additional Diagnostics (If Needed)

If standard diagnostics are insufficient, add to `camera_manager.h` `init()`:

```cpp
// After esp_camera_init() succeeds, add:
camera_fb_t* test_fb = esp_camera_fb_get();
if (test_fb) {
    Serial.printf("[CAM]  Test capture: %u bytes at %p\n", 
                  test_fb->len, test_fb->buf);
    Serial.printf("[CAM]  FB in PSRAM: %s\n",
                  heap_caps_check_integrity(MALLOC_CAP_SPIRAM, true) ? "YES" : "NO");
    esp_camera_fb_return(test_fb);
} else {
    Serial.println("[CAM]  Test capture: FAILED");
}
```

**Note**: No code changes should be made until testing confirms the need.

---

## Recommended Actions

### Immediate Actions (Testing With Current Firmware)

The current firmware **already has all necessary diagnostics implemented**. We should test it first before making any changes.

1. **Clean build environment**
   ```bash
   cd hardware/smart-goggles/firmware
   pio run --target clean
   ```

2. **Build with correct environment**
   ```bash
   pio run -e esp32-s3-n16r8
   ```
   - Verify board definition is `4d_systems_esp32s3_gen4_r8n16`
   - Verify `memory_type = qio_opi`
   - Verify `BOARD_HAS_PSRAM` is defined
   - Verify libraries are correct:
     - `espressif/esp32-camera@^2.0.13`
     - `mathieucarbou/AsyncTCP@^3.3.2`
     - `mathieucarbou/ESPAsyncWebServer@^3.6.0`

3. **Full flash erase before upload** (recommended for PSRAM changes)
   ```bash
   esptool.py --chip esp32s3 --port COM3 erase_flash
   pio run -e esp32-s3-n16r8 --target upload
   ```

4. **Monitor serial output during boot**
   ```bash
   pio device monitor -e esp32-s3-n16r8
   ```
   
   **Expected diagnostics** (from camera_manager.h printSensorDiagnostics()):
   - `[CAM] Sensor: <model name>` - Check if it's OV5640, OV2640, or Unknown
   - `[CAM] PID: 0x<hex>` - Product ID
   - `[CAM] MIDH: 0x<hex>` - Manufacturer ID High
   - `[CAM] MIDL: 0x<hex>` - Manufacturer ID Low
   - `[CAM] Resolution: 1024x768`
   - `[CAM] XCLK: 16000000 Hz`
   - `[CAM] PSRAM mode: ENABLED`
   - `[CAM] Free PSRAM: <size> bytes`
   - `[CAM] Largest PSRAM blk: <size> bytes`

5. **Capture test image**
   ```bash
   curl http://<ip>:9000/capture -o test_$(date +%s).jpg
   ```
   
   **Check serial logs for capture diagnostics**:
   - `[CAPTURE] Resolution: 1024x768`
   - `[CAPTURE] Format: JPEG`
   - `[CAPTURE] Size: <bytes>` - Should be ~80-200KB for XGA
   - `[CAPTURE] Duration: <ms>` - Should be ~80-150ms
   - `[CAPTURE] SUCCESS` or `[CAPTURE] FAILED`

### Analysis Based on Serial Logs

After running the firmware, analyze the serial output:

#### If Sensor PID is NOT OV5640:
- The camera module might be OV2640 instead
- OV2640 works with the same pins and supports XGA
- Continue testing - corruption may be unrelated to sensor type

#### If Sensor PID shows "Unknown" or NULL:
- **CRITICAL**: I2C communication failure
- Check SIOD (GPIO 4) and SIOC (GPIO 5) connections
- Verify camera module power (3.3V, not 5V!)
- Check for loose connections

#### If PSRAM mode shows "DISABLED":
- XCLK is not 16 MHz (should not happen - config.h has it correct)
- Check that config.h is being compiled correctly
- Verify build output shows XCLK=16000000

#### If capture size is very small (<10KB):
- Likely capturing black or corrupt frames
- Check PCLK (GPIO 13), VSYNC (GPIO 6), HREF (GPIO 7)
- These are synchronization signals - if wrong, timing is broken

#### If image is recognizable but corrupted:
- **LIKELY**: Data pins (D0-D7) are partially wrong
- Green tint suggests bit manipulation (specific bits stuck or swapped)
- Horizontal blocks suggest line-by-line corruption
- **ACTION**: Verify each D0-D7 pin connection against camera module datasheet

### Troubleshooting Based on Symptoms

#### Corruption Pattern Analysis

1. **Green tint throughout image**
   - Suggests specific color channel corruption
   - Likely cause: One or more data pins (D0-D7) are wrong
   - D5, D6, D7 affect different YUV components
   - **Action**: Double-check D5 (GPIO 18), D6 (GPIO 17), D7 (GPIO 16)

2. **Horizontal block artifacts**
   - Suggests line-by-line corruption
   - Could be HREF or PCLK timing issues
   - **Action**: Verify HREF (GPIO 7), PCLK (GPIO 13)

3. **Dark image overall**
   - Could be exposure control not working
   - Sensor settings may not be applied correctly
   - **Action**: Sensor must be detected properly for settings to apply
   - Check that `printSensorDiagnostics()` shows valid sensor model

4. **Partial frame only**
   - Suggests framebuffer too small or DMA cutoff
   - **Action**: Check PSRAM free space after init
   - Expected: ~5 MB free after camera init (8MB - 3MB framebuffers)

### Pin Verification Checklist

Use a multimeter in continuity mode to verify each connection:

| Signal | ESP32-S3 GPIO | Camera Module Pin | Verified |
|--------|---------------|-------------------|----------|
| XCLK   | GPIO 15       | XCLK              | [ ]      |
| SIOD   | GPIO 4        | SDA               | [ ]      |
| SIOC   | GPIO 5        | SCL               | [ ]      |
| D0     | GPIO 11       | D0 / Y2           | [ ]      |
| D1     | GPIO 9        | D1 / Y3           | [ ]      |
| D2     | GPIO 8        | D2 / Y4           | [ ]      |
| D3     | GPIO 10       | D3 / Y5           | [ ]      |
| D4     | GPIO 12       | D4 / Y6           | [ ]      |
| D5     | GPIO 18       | D5 / Y7           | [ ]      |
| D6     | GPIO 17       | D6 / Y8           | [ ]      |
| D7     | GPIO 16       | D7 / Y9           | [ ]      |
| VSYNC  | GPIO 6        | VSYNC             | [ ]      |
| HREF   | GPIO 7        | HREF/HSYNC        | [ ]      |
| PCLK   | GPIO 13       | PCLK              | [ ]      |
| 3.3V   | 3.3V          | VCC               | [ ]      |
| GND    | GND           | GND               | [ ]      |

**Note**: Some OV5640 modules label data pins as Y2-Y9 instead of D0-D7:
- Y2 = D0
- Y3 = D1
- Y4 = D2
- Y5 = D3
- Y6 = D4
- Y7 = D5
- Y8 = D6
- Y9 = D7

---

## Expected Diagnostic Output

### Healthy Camera Init
```
[CAM]  ── Camera Init ────────────────────────────
[CAM]  PSRAM free before init : 8355840 bytes
[CAM]  XCLK: 16000000 Hz — psram_mode WILL be active
[CAM]  PSRAM free after init  : 5120000 bytes
[CAM]  PSRAM used by camera   : 3235840 bytes
[CAM]  Sensor settings applied (optimized for text/OCR)
[CAM]  ── Sensor Identity ──────────────────────
[CAM]  Sensor       : OV5640
[CAM]  PID          : 0x5640
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
```

### Healthy Capture
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

---

## Known Issues and Limitations

### PSRAM Mode Gate in cam_hal.c
The esp-camera driver contains this hardcoded check:
```c
cam_obj->psram_mode = (config->xclk_freq_hz == 16000000);
```

This means:
- ✅ XCLK = 16 MHz → PSRAM DMA mode enabled
- ❌ XCLK ≠ 16 MHz → PSRAM DMA mode disabled, uses internal SRAM

**Our configuration**: ✅ Already set to 16 MHz

### No DRAM Fallback
The firmware intentionally does NOT fall back to internal DRAM if PSRAM fails:
- Rationale: Missing PSRAM indicates hardware misconfiguration
- XGA resolution requires ~3 MB which exceeds internal SRAM capacity
- Better to fail loudly than hide the problem

### OV5640 vs OV2640
Both sensors are supported by the esp-camera library, but:
- OV5640: 5MP, supports up to QSXGA (2592×1944)
- OV2640: 2MP, supports up to UXGA (1600×1200)

XGA (1024×768) is supported by both.

---

## Next Steps

1. ✅ Diagnostics are already implemented in firmware
2. ⏸️ Verify physical camera module pinout
3. ⏸️ Clean build and flash
4. ⏸️ Monitor serial output
5. ⏸️ Analyze sensor PID
6. ⏸️ Test capture and analyze corruption pattern
7. ⏸️ Adjust pins if needed
8. ⏸️ Test different resolutions if memory-related
9. ⏸️ Document findings and create final recommendations

---

## Summary

### Current Status
- ✅ **Firmware compiles** and flashes successfully
- ✅ **PSRAM is configured correctly** (qio_opi, 16MB flash, 8MB PSRAM)
- ✅ **XCLK is set correctly** (16 MHz for PSRAM DMA mode)
- ✅ **Diagnostics are implemented** (sensor detection, capture logging)
- ✅ **Libraries are pinned** (esp32-camera 2.0.13, AsyncTCP, ESPAsyncWebServer)
- ❌ **Camera captures corrupted images** (green tint, horizontal blocks, dark)

### Most Likely Root Cause
**Data pin misconfiguration** (D0-D7 pins partially incorrect)

**Evidence**:
- Image is recognizable → Camera works, some data is correct
- Green tint → Color channel corruption (specific bit patterns)
- Horizontal blocks → Line-by-line corruption (data bits wrong)
- Not random noise → Structured corruption pattern

### Next Steps
1. **Test current firmware** with full diagnostics logging
2. **Analyze serial output** to identify sensor type and PSRAM usage
3. **Verify physical connections** using pin verification checklist
4. **Adjust configuration** based on findings (pins, resolution, or XCLK)
5. **Document results** and update this report

### Testing Priority
1. ✅ **HIGH**: Flash and test current firmware (diagnostics already present)
2. ⚠️ **HIGH**: Verify physical pin connections (if corruption persists)
3. ⚠️ **MEDIUM**: Test SVGA resolution (if XGA fails)
4. ⚠️ **LOW**: Test different XCLK frequencies (only if 16 MHz fails)

### Success Criteria
- [ ] Sensor detected correctly (OV5640 or OV2640 PID logged)
- [ ] PSRAM mode active (confirmed in logs)
- [ ] Capture returns ~80-200KB JPEG
- [ ] Image is sharp, no corruption
- [ ] Colors are accurate (no green tint)
- [ ] Text is readable at 0.5m distance

---

## References

- [ESP32-Camera Library Documentation](https://github.com/espressif/esp32-camera)
- [OV5640 Datasheet](https://www.ovt.com/products/ov5640/)
- [ESP32-S3 Technical Reference Manual](https://www.espressif.com/sites/default/files/documentation/esp32-s3_technical_reference_manual_en.pdf)
- [PlatformIO ESP32-S3 Boards](https://docs.platformio.org/en/latest/boards/espressif32/index.html)
- Camera Bringup Report: `docs/roadmaps/goggles/CAMERA_BRINGUP.md`

---

## Revision History

| Date | Author | Changes |
|------|--------|---------|
| 2026-06-20 | Kiro | Initial camera debug report created |


