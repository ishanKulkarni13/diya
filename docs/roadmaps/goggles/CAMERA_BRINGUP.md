# Smart Goggle Camera Bringup

**Date**: June 20, 2026  
**Hardware**: ESP32-S3-N16R8 (16 MB Flash, 8 MB OPI PSRAM)  
**Branch**: `feat/auth-ux-hardening`

---

## Root Cause Analysis

### Symptom
```
PSRAM ID read error
cam_dma_config(301): frame buffer malloc failed
camera config failed with error 0xffffffff
```

PlatformIO build header reported:
```
PLATFORM: Espressif 32 (7.0.1) > Espressif ESP32-S3-DevKitC-1-N8 (8 MB QD, No PSRAM)
```

### Root Cause

The `platformio.ini` specified `board = esp32-s3-devkitc-1`. That board definition maps to the **ESP32-S3-N8** variant — 8 MB flash, **no PSRAM**. PlatformIO's build system never initialized the PSRAM controller, so `psramFound()` returned `false` and `esp_camera_init()` could not allocate `CAMERA_FB_IN_PSRAM` framebuffers.

The actual hardware is the **ESP32-S3-N16R8**: 16 MB Flash, 8 MB PSRAM on an **OPI (Octal-SPI) interface**.

The critical missing configuration was `board_build.arduino.memory_type = qio_opi`. Without this, the Arduino-ESP32 HAL uses `qio` memory type (standard SPI PSRAM) and never touches the OPI PSRAM controller. The PSRAM was physically present but logically invisible.

### Why `-mfix-esp32-psram-cache-issue` Was Wrong

The original `platformio.ini` had `-mfix-esp32-psram-cache-issue`. This flag targets a specific silicon errata in **original ESP32** (Xtensa LX6, rev 0/1). The ESP32-S3 (Xtensa LX7) does not have this bug. The flag was at best a no-op and at worst introduced incorrect cache behavior. It has been removed.

### Why `esp32-camera@^2.0.0` Was Risky

The library spec `esp32-camera@^2.0.0` allows any version from 2.0.0 to 3.x. Version `2.0.13` introduced fixes for S3 DMA buffer allocation. Pinning to `espressif/esp32-camera@^2.0.13` ensures the correct S3 DMA path is used. The vendor namespace (`espressif/`) also ensures the official Espressif fork is resolved instead of a community fork.

---

## PlatformIO Configuration Decisions

### Board Selection

| Field | Old (wrong) | New (correct) |
|---|---|---|
| `board` | `esp32-s3-devkitc-1` | `4d_systems_esp32s3_gen4_r8n16` |
| Board name | N8, No PSRAM | ESP32S3-R8N16, 8MB PSRAM |
| `memory_type` | not set (defaults to qio) | `qio_opi` |
| `BOARD_HAS_PSRAM` | set via build_flags only | set in board definition + build_flags |
| Flash | 8 MB | 16 MB |
| Partitions | `huge_app.csv` | `default_16MB.csv` |

**Why `4d_systems_esp32s3_gen4_r8n16`?**

This is the best available stock board definition for the N16R8 variant in PlatformIO's Espressif32 platform (v7.0.1). It ships with:

```json
"memory_type": "qio_opi",
"-DBOARD_HAS_PSRAM",
"flash_size": "16MB"
```

The OPI memory type is the critical flag. It tells the Arduino-ESP32 bootloader to initialize PSRAM using the octal-SPI controller path, which is required for the N16R8's PSRAM chip.

### Memory Type: `qio_opi`

The ESP32-S3 supports several PSRAM configurations:

| Memory Type | Flash | PSRAM Interface | Applicable Variants |
|---|---|---|---|
| `qio` | QIO | — (no PSRAM) | N4, N8 |
| `qio_qspi` | QIO | QPI PSRAM | N4R2, N8R2 |
| `qio_opi` | QIO | OPI PSRAM | **N4R8, N8R8, N16R8** |
| `opi_opi` | OPI | OPI PSRAM | N16R8V |

The N16R8 uses OPI PSRAM (8MB, 80 MHz). Without `qio_opi`, the PSRAM controller is never started.

### Partition Scheme

Changed from `huge_app.csv` (designed for 8 MB flash) to `default_16MB.csv`. With 16 MB flash, the default 16 MB scheme gives ~3 MB app + full OTA + NVS partitions. `huge_app.csv` on 16 MB flash wastes space and produces incorrect partition offsets.

### Library Pinning

| Library | Old | New | Reason |
|---|---|---|---|
| `esp32-camera` | `^2.0.0` | `espressif/esp32-camera@^2.0.13` | Fixes S3 DMA allocation, pins vendor |
| `AsyncTCP` | `AsyncTCP@^1.1.1` | `mathieucarbou/AsyncTCP@^3.3.2` | Resolves ESPAsyncWebServer name conflict shown in build.log |
| `ESPAsyncWebServer` | `ESPAsyncWebServer@^1.2.3` | `mathieucarbou/ESPAsyncWebServer@^3.6.0` | Pins to mathieucarbou fork, eliminates "more than one package" warning from build.log |

---

## PSRAM Findings

### Physical PSRAM

- **Chip**: 8 MB OPI PSRAM, soldered on the N16R8 module
- **Interface**: OPI (Octal-SPI), not the common QPI used on smaller variants
- **Speed**: 80 MHz
- **Access**: Via `MALLOC_CAP_SPIRAM` heap capability

### Expected Values After Correct Init

```
[MEM]  PSRAM Found      : YES
[MEM]  PSRAM Size        : 8388608 bytes (8 MB)
[MEM]  Free PSRAM        : ~8200000 bytes (before camera init)
[MEM]  Free PSRAM        : ~7700000 bytes (after camera init with 2x XGA buffers)
[MEM]  Largest PSRAM blk : ~4000000+ bytes
```

### Framebuffer Memory Consumption

XGA (1024×768) JPEG framebuffer with `fb_count=2`:

- Each uncompressed frame: 1024 × 768 × 2 bytes (YUV) ≈ 1.57 MB
- Two framebuffers: ≈ 3.14 MB allocated from PSRAM at init
- PSRAM remaining: ≈ 4.86 MB free after camera init

This is well within the 8 MB PSRAM capacity.

---

## Camera Configuration Rationale

### `CAMERA_FB_IN_PSRAM`

Framebuffers allocated exclusively in PSRAM. No DRAM fallback is implemented. Rationale:

1. DRAM-backed framebuffers at XGA resolution would consume >1.5 MB of the ESP32-S3's 512 KB internal SRAM, leaving nothing for the application stack, WiFi buffers, and HTTP server. This causes heap fragmentation and random crashes.
2. The N16R8 has 8 MB PSRAM specifically for this purpose.
3. Missing PSRAM means the hardware is misconfigured or damaged. Silently degrading to smaller resolution in DRAM hides the real problem.

### `CAMERA_GRAB_LATEST` with `fb_count=2`

- **Why `GRAB_LATEST`**: The HTTP server serves on-demand captures. When `/capture` is called, the most recent frame is wanted, not a frame that has been sitting in the buffer for 500ms. `GRAB_LATEST` discards stale frames.
- **Why `fb_count=2`**: With one buffer, `esp_camera_fb_get()` blocks until the previous buffer is returned. With two, the camera can write to one while the application reads the other, eliminating deadlocks under load.

### Frame Size: `FRAMESIZE_XGA` (1024×768)

Selected for OCR and text reading use case:

- Sufficient resolution for road signs, labels, product names at normal distances
- Lower than SXGA (1280×1024) — faster JPEG encoding, lower memory pressure
- Higher than SVGA (800×600) — better character detail for small print

### JPEG Quality: `12`

Scale: 0 (best) to 63 (worst). Quality 12 produces:

- File size: typically 80–200 KB per XGA frame
- Quality: suitable for OCR, text recognition, indoor navigation
- Encoding time: ~80–150ms on ESP32-S3 at 240 MHz

---

## Memory Usage Summary

| Allocation | Location | Size |
|---|---|---|
| Application code + stack | Internal SRAM | ~280 KB |
| WiFi buffers | Internal SRAM | ~40 KB |
| Camera sensor registers | Internal SRAM | ~4 KB |
| JPEG encode buffer | Internal SRAM | ~16 KB |
| Frame buffer 1 (XGA) | **PSRAM** | ~1.57 MB |
| Frame buffer 2 (XGA) | **PSRAM** | ~1.57 MB |
| PSRAM remaining | **PSRAM** | ~4.86 MB free |

---

## Recommended Production Configuration

```ini
[env:esp32-s3-n16r8]
platform = espressif32
board = 4d_systems_esp32s3_gen4_r8n16
framework = arduino

board_build.arduino.memory_type = qio_opi
board_build.partitions = default_16MB.csv
board_build.f_flash = 80000000L
board_build.flash_mode = qio

build_flags =
    -DCORE_DEBUG_LEVEL=4
    -DBOARD_HAS_PSRAM
    -DARDUINO_USB_CDC_ON_BOOT=1

lib_deps =
    ArduinoJson@^7.0.0
    espressif/esp32-camera@^2.0.13
    mathieucarbou/AsyncTCP@^3.3.2
    mathieucarbou/ESPAsyncWebServer@^3.6.0
```

---

## Validation Checklist

### Boot Sequence

- [ ] Serial output at 115200 baud
- [ ] `[BOOT]` lines show firmware version and board target
- [ ] `[MEM]  PSRAM Found      : YES`
- [ ] `[MEM]  PSRAM Size        : 8388608 bytes`
- [ ] No `[FATAL]` lines in output

### Camera Init

- [ ] `[CAM]  Camera initialized successfully`
- [ ] `[CAM]  Sensor       : OV2640` (or OV5640, depending on module)
- [ ] `[CAM]  FB Location  : PSRAM`
- [ ] No `frame buffer malloc failed` error
- [ ] No `PSRAM ID read error`

### Capture Endpoint

- [ ] `GET http://<ip>:9000/capture` returns HTTP 200
- [ ] Response `Content-Type: image/jpeg`
- [ ] Response body starts with `FF D8` (JPEG magic bytes)
- [ ] `[CAPTURE] SUCCESS` in serial log
- [ ] `[CAPTURE] <size> bytes` shows reasonable size (>50 KB for XGA)

### Image Quality

- [ ] Image is sharp enough to read printed text at 0.5m
- [ ] No color distortion (auto white balance working)
- [ ] No extreme over/underexposure (AEC working)

### Existing Features (Regression Check)

- [ ] `GET /health` returns JSON with `status: ok`
- [ ] `GET /state` returns JSON with telemetry data
- [ ] `POST /register-phone` accepts phone registration
- [ ] Ultrasonic telemetry fields present in `/state`
- [ ] Button events logged when physical buttons pressed
- [ ] WiFi reconnects after router restart
- [ ] Heap monitor logs appear every 10 seconds (no CRITICAL/LOW)

---

## Serial Log Reference — Healthy Boot

```
==================================================
  Diya Smart Goggle Firmware
==================================================
[BOOT] Firmware Version : 1.0.0
[BOOT] Device Type      : goggle
[BOOT] Build target     : ESP32-S3-N16R8
[BOOT] Board definition : 4d_systems_esp32s3_gen4_r8n16
[BOOT] memory_type      : qio_opi
[BOOT] Chip model       : ESP32-S3 rev 0
[BOOT] CPU cores        : 2
[BOOT] Flash size       : 16777216 bytes (16 MB)
[MEM]  Total Heap       : 390140 bytes
[MEM]  Free Heap        : 352000 bytes
[MEM]  Min Free Heap    : 350000 bytes
[MEM]  Max Alloc Heap   : 327680 bytes
[MEM]  PSRAM Found      : YES
[MEM]  PSRAM Size        : 8388608 bytes (8 MB)
[MEM]  Free PSRAM        : 8355840 bytes
[MEM]  Min Free PSRAM    : 8355840 bytes
[MEM]  Largest PSRAM blk : 4194304 bytes
==================================================
[INIT] Device state initialized
[INIT] Telemetry initialized
[INIT] Buttons initialized
[INIT] Initializing camera...
[CAM]  ── Camera Init ────────────────────────────
[CAM]  PSRAM free before init : 8355840 bytes
[CAM]  PSRAM free after init  : 5120000 bytes
[CAM]  PSRAM used by camera   : 3235840 bytes
[CAM]  Sensor settings applied (optimized for text/OCR)
[CAM]  ── Sensor Identity ──────────────────────
[CAM]  Sensor       : OV2640
[CAM]  PID          : 0x2642
[CAM]  MID          : 0x7FA2
[CAM]  Resolution   : 1024x768
[CAM]  JPEG Quality : 12 (0=best, 63=worst)
[CAM]  FB Count     : 2
[CAM]  FB Location  : PSRAM
[CAM]  Grab Mode    : LATEST
[CAM]  ─────────────────────────────────────────
[CAM]  Camera initialized successfully
[INIT] Camera initialized successfully
[WIFI] Connected!
[WIFI] IP Address : 192.168.1.105
[HTTP] Server started on port 9000
[READY] Smart Goggle is ready!
[READY] Access at: http://192.168.1.105:9000
```

---

## Serial Log Reference — PSRAM Missing (Wrong Board)

```
[MEM]  PSRAM Found      : NO
[MEM]  PSRAM Size        : 0
[MEM]  Free PSRAM        : 0
[MEM]  Largest PSRAM blk : 0

[FATAL] ============================================================
[FATAL] PSRAM NOT DETECTED — camera framebuffer malloc will fail.
[FATAL] This firmware targets ESP32-S3-N16R8 (16MB Flash, 8MB PSRAM).
[FATAL]
[FATAL] Likely root causes:
[FATAL]   1. Wrong board definition in platformio.ini
[FATAL]      Required: board = 4d_systems_esp32s3_gen4_r8n16
[FATAL]      Required: board_build.arduino.memory_type = qio_opi
...
[FATAL] System halted. Reflash with correct board definition.
```
