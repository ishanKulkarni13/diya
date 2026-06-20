# Camera Debug Work Summary

**Date**: June 20, 2026  
**Branch**: `feat/goggle-camera-debug`  
**Status**: Ready for hardware testing  
**Issue**: Camera captures show corruption (green tint, horizontal blocks, darkness)

---

## Work Completed

### 1. Code Audit ✅

**Reviewed files**:
- `hardware/smart-goggles/firmware/platformio.ini` - Board configuration
- `hardware/smart-goggles/firmware/src/main.cpp` - Boot diagnostics
- `hardware/smart-goggles/firmware/src/camera_manager.h` - Camera initialization
- `hardware/smart-goggles/firmware/src/config.h` - Pin configuration

**Key findings**:
- ✅ PSRAM configuration is correct (`qio_opi` for ESP32-S3-N16R8)
- ✅ XCLK is set to 16 MHz (required for PSRAM DMA mode)
- ✅ All diagnostics are already implemented in firmware
- ✅ Libraries are pinned to correct versions (esp32-camera 2.0.13)
- ✅ Pin configuration matches documented ESP32-S3-CAM standard
- ⚠️ Image corruption suggests data pin (D0-D7) misconfiguration

### 2. Documentation Created ✅

Created comprehensive debugging documentation:

#### `CAMERA_DEBUG_REPORT.md`
- Root cause analysis of corruption symptoms
- Detailed investigation plan with 6 phases
- Hypothesis ranking (pin misconfiguration most likely)
- Expected diagnostic outputs
- Pin verification checklist
- Code change templates for fixes
- Success criteria

#### `TESTING_PROCEDURE.md`
- Step-by-step hardware testing guide
- Clean build and flash procedure
- Serial output analysis checklist
- Image quality evaluation rubric
- Physical pin verification procedure
- Troubleshooting for common issues
- Result reporting template

#### `CAMERA_BRINGUP.md` (already exists)
- Previous PSRAM configuration work
- Memory layout analysis
- Validation checklist

### 3. Code Analysis ✅

**Verified correct configuration**:

```cpp
// XCLK - CORRECT (enables PSRAM DMA mode)
#define CAMERA_XCLK_HZ 16000000

// Pin configuration - matches standard ESP32-S3-CAM pinout
#define CAM_PIN_XCLK    15
#define CAM_PIN_SIOD    4
#define CAM_PIN_SIOC    5
#define CAM_PIN_D0      11
#define CAM_PIN_D1      9
#define CAM_PIN_D2      8
#define CAM_PIN_D3      10
#define CAM_PIN_D4      12
#define CAM_PIN_D5      18
#define CAM_PIN_D6      17
#define CAM_PIN_D7      16
#define CAM_PIN_VSYNC   6
#define CAM_PIN_HREF    7
#define CAM_PIN_PCLK    13
```

**Verified PlatformIO configuration**:
```ini
[env:esp32-s3-n16r8]
board = 4d_systems_esp32s3_gen4_r8n16
board_build.arduino.memory_type = qio_opi
lib_deps = 
    espressif/esp32-camera@^2.0.13
    mathieucarbou/AsyncTCP@^3.3.2
    mathieucarbou/ESPAsyncWebServer@^3.6.0
```

### 4. Diagnostics Review ✅

**Already implemented in firmware**:
- ✅ Boot diagnostics (PSRAM detection, chip info, memory map)
- ✅ Camera init diagnostics (sensor PID, XCLK, PSRAM mode)
- ✅ Capture diagnostics (size, duration, format, memory usage)
- ✅ Sensor identity logging (model, PID, MIDH, MIDL)
- ✅ Memory monitoring (heap, PSRAM before/after)

**No code changes needed** - diagnostics are comprehensive.

---

## Key Findings

### Root Cause Hypothesis

**Most Likely: Data Pin Misconfiguration (D0-D7)**

Evidence:
1. ✅ Image is recognizable → Camera works, not total failure
2. ✅ Green tint → Color channel corruption (specific bit patterns)
3. ✅ Horizontal blocks → Line-by-line corruption (data bits wrong)
4. ✅ Not random noise → Structured corruption pattern
5. ✅ PSRAM works → Memory is not the issue
6. ✅ XCLK correct → Timing should be correct

**Other possibilities (lower priority)**:
- Sensor type mismatch (OV5640 vs OV2640)
- I2C communication issues (unlikely - init succeeds)
- Power/clock instability (unlikely - no crashes)
- Timing issues with HREF/PCLK (possible)

### What We Know

**Working**:
- ✅ ESP32-S3 boots successfully
- ✅ PSRAM detected (8 MB OPI PSRAM)
- ✅ WiFi connects
- ✅ HTTP server works
- ✅ Camera initializes (no init errors)
- ✅ Capture endpoint returns data
- ✅ JPEG files are created
- ✅ Images open in viewers
- ✅ Scene is recognizable

**Not Working**:
- ❌ Image has green tint
- ❌ Horizontal block artifacts
- ❌ Overall darkness
- ❌ Image quality unsuitable for OCR/text reading

---

## Next Steps

### Immediate: Hardware Testing

1. **Flash firmware** (current version has all diagnostics)
2. **Monitor serial output** during boot and capture
3. **Record diagnostic values**:
   - Sensor PID (OV5640: 0x5640, OV2640: 0x2642)
   - PSRAM size and free space
   - XCLK frequency
   - PSRAM mode status
   - Capture metrics (size, duration)

4. **Capture test images** and analyze corruption pattern
5. **Compare** with expected values in testing procedure

### If Corruption Persists: Pin Verification

1. **Power off device**
2. **Use multimeter** to verify each pin connection
3. **Check continuity** for all 15 camera signals
4. **Document** any mismatches
5. **Correct wiring** if needed
6. **Update config.h** to match actual hardware

### After Testing: Next Actions

Based on test results:

| Finding | Action |
|---------|--------|
| Clean images | ✅ Issue resolved - document solution |
| Sensor PID unknown | Check I2C pins (SIOD/SIOC) |
| PSRAM not detected | Review platformio.ini, re-flash |
| Corruption persists | Verify data pins (D0-D7) |
| Different corruption | Analyze new pattern, adjust hypothesis |

---

## Files Modified/Created

### Documentation
- ✅ `docs/roadmaps/goggles/CAMERA_DEBUG_REPORT.md` (created)
- ✅ `docs/roadmaps/goggles/CAMERA_DEBUG_SUMMARY.md` (this file)
- ✅ `hardware/smart-goggles/firmware/TESTING_PROCEDURE.md` (created)

### Configuration
- ✅ `hardware/smart-goggles/firmware/.gitignore` (updated)

### Code
- ⏸️ No code changes needed yet
- ⏸️ All diagnostics already present
- ⏸️ Configuration appears correct

---

## Commits

```bash
git log --oneline feat/goggle-camera-debug

0e06f67 docs(firmware): add comprehensive camera testing procedure
c26d350 chore(firmware): add build.log to gitignore  
1e48243 docs(goggles): add comprehensive camera debug report
a836f2b docs(camera): add camera debug report documenting XCLK psram_mode root cause
23224f2 chore(http): normalize whitespace and brace style in http_server.h
```

---

## Repository State

**Branch**: `feat/goggle-camera-debug`  
**Status**: Clean working directory  
**Ready for**: Hardware testing

```bash
# Check branch
git branch --show-current
# feat/goggle-camera-debug

# Check status
git status
# On branch feat/goggle-camera-debug
# nothing to commit, working tree clean
```

---

## Testing Instructions

Follow `hardware/smart-goggles/firmware/TESTING_PROCEDURE.md`:

```bash
# 1. Navigate to firmware directory
cd hardware/smart-goggles/firmware

# 2. Clean build
pio run --target clean

# 3. Build
pio run -e esp32-s3-n16r8

# 4. Erase flash
esptool.py --chip esp32s3 --port COM3 erase_flash

# 5. Upload
pio run -e esp32-s3-n16r8 --target upload

# 6. Monitor
pio device monitor -e esp32-s3-n16r8

# 7. Capture test image (from another machine)
curl http://<device-ip>:9000/capture -o test.jpg
```

---

## Expected Results

### Healthy System
- PSRAM: 8388608 bytes (8 MB)
- Sensor: OV5640 (PID 0x5640) or OV2640 (PID 0x2642)
- XCLK: 16000000 Hz
- PSRAM mode: ENABLED
- Capture size: 50-250 KB
- Image: Clear, no corruption, natural colors

### Current System (Corrupted)
- PSRAM: Likely OK (camera inits successfully)
- Sensor: Unknown until tested
- XCLK: Should be 16 MHz
- PSRAM mode: Should be ENABLED
- Capture size: Unknown
- Image: Green tint, horizontal blocks, dark

---

## Success Criteria

### ✅ Debugging Complete When:
- [ ] Root cause identified with evidence
- [ ] Fix implemented and tested
- [ ] Clean images captured
- [ ] Text is readable at 0.5m
- [ ] Colors are natural
- [ ] No artifacts or corruption
- [ ] Documentation updated with solution
- [ ] Changes committed and merged

### 📋 Documentation Complete When:
- [x] Debug report written
- [x] Testing procedure documented
- [x] Expected outputs documented
- [ ] Test results recorded
- [ ] Solution documented
- [ ] Lessons learned captured

---

## Resources

### Documentation
- [ESP32-Camera Library](https://github.com/espressif/esp32-camera)
- [OV5640 Datasheet](https://www.ovt.com/products/ov5640/)
- [ESP32-S3 TRM](https://www.espressif.com/sites/default/files/documentation/esp32-s3_technical_reference_manual_en.pdf)

### Internal Docs
- `docs/roadmaps/goggles/CAMERA_BRINGUP.md` - PSRAM configuration
- `docs/roadmaps/goggles/CAMERA_DEBUG_REPORT.md` - Detailed analysis
- `hardware/smart-goggles/firmware/TESTING_PROCEDURE.md` - Testing guide
- `hardware/smart-goggles/firmware/README.md` - General firmware docs
- `hardware/smart-goggles/firmware/QUICKSTART.md` - Quick setup

---

## Contact & Support

If hardware testing reveals issues not covered by this documentation:

1. Review serial logs for unexpected errors
2. Consult `CAMERA_DEBUG_REPORT.md` troubleshooting section
3. Check pin connections with multimeter
4. Compare against known ESP32-S3-CAM reference designs
5. Document new findings and update debug report

---

## Conclusion

The camera corruption issue has been thoroughly analyzed from a software perspective. All necessary diagnostics are already implemented in the firmware, and comprehensive testing procedures have been created.

**Current assessment**: The firmware configuration appears correct. The most likely cause is physical hardware wiring (data pins D0-D7). Hardware testing with the provided procedure will confirm or refute this hypothesis.

**Next milestone**: Execute hardware testing procedure and document results.

**Estimated time to resolution**: 1-2 hours for testing + 0-2 hours for pin correction (if needed)

---

**Engineer**: Kiro  
**Date**: June 20, 2026  
**Branch**: feat/goggle-camera-debug  
**Status**: Ready for hardware testing
