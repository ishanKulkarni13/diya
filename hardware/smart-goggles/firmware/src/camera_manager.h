#ifndef CAMERA_MANAGER_H
#define CAMERA_MANAGER_H

#include <Arduino.h>
#include <esp_camera.h>
#include <esp_heap_caps.h>
#include "config.h"

// ============================================================================
// CameraManager
//
// Responsibilities:
//   - Build the camera_config_t with PSRAM-only framebuffers
//   - Initialize the sensor with retries and full diagnostics
//   - Capture frames with per-capture timing and memory stats
//   - Log sensor identity (model, PID, resolution) after init
//   - Reject init if PSRAM is absent (fatal bringup error)
//
// Design decisions:
//   fb_location  = CAMERA_FB_IN_PSRAM   — framebuffers live in PSRAM only
//   fb_count     = 2                    — double buffering, GRAB_LATEST discards stale frames
//   grab_mode    = CAMERA_GRAB_LATEST   — always returns the newest frame
//   frame_size   = FRAMESIZE_XGA        — 1024x768, suitable for OCR and text reading
//   jpeg_quality = 12                   — high quality (0=best, 63=worst)
//   xclk_freq_hz = 20000000             — 20 MHz XCLK, standard for OV2640/OV5640
//
// DRAM fallback is intentionally NOT implemented. Missing PSRAM is a fatal
// bringup error for this hardware family. See main.cpp printBootDiagnostics().
// ============================================================================

class CameraManager {
private:
    bool _initialized;
    uint32_t _captureCount;
    uint32_t _captureFailures;
    unsigned long _lastCaptureTime;

    // ── Camera configuration ─────────────────────────────────────────────
    camera_config_t buildConfig() {
        camera_config_t config = {};

        // Pin assignments from config.h
        config.pin_d0       = CAM_PIN_D0;
        config.pin_d1       = CAM_PIN_D1;
        config.pin_d2       = CAM_PIN_D2;
        config.pin_d3       = CAM_PIN_D3;
        config.pin_d4       = CAM_PIN_D4;
        config.pin_d5       = CAM_PIN_D5;
        config.pin_d6       = CAM_PIN_D6;
        config.pin_d7       = CAM_PIN_D7;
        config.pin_xclk     = CAM_PIN_XCLK;
        config.pin_pclk     = CAM_PIN_PCLK;
        config.pin_vsync    = CAM_PIN_VSYNC;
        config.pin_href     = CAM_PIN_HREF;
        config.pin_sscb_sda = CAM_PIN_SIOD;
        config.pin_sscb_scl = CAM_PIN_SIOC;
        config.pin_pwdn     = CAM_PIN_PWDN;
        config.pin_reset    = CAM_PIN_RESET;

        // Clock
        config.ledc_channel  = LEDC_CHANNEL_0;
        config.ledc_timer    = LEDC_TIMER_0;
        config.xclk_freq_hz  = 20000000;    // 20 MHz

        // Image format and quality
        config.pixel_format  = PIXFORMAT_JPEG;
        config.frame_size    = CAMERA_FRAME_SIZE;   // FRAMESIZE_XGA = 1024x768
        config.jpeg_quality  = CAMERA_JPEG_QUALITY; // 12 (lower = better)

        // PSRAM framebuffers — no DRAM fallback
        config.fb_count      = 2;                       // Double buffer
        config.grab_mode     = CAMERA_GRAB_LATEST;      // Discard stale frames
        config.fb_location   = CAMERA_FB_IN_PSRAM;      // Must be in PSRAM

        return config;
    }

    // ── Sensor identity diagnostics ──────────────────────────────────────
    void printSensorDiagnostics() {
        sensor_t* s = esp_camera_sensor_get();
        if (s == nullptr) {
            Serial.println("[CAM]  Sensor: NULL — could not get sensor handle");
            return;
        }

        // Sensor model from PID
        const char* sensorName = "Unknown";
        switch (s->id.PID) {
            case OV2640_PID: sensorName = "OV2640"; break;
            case OV5640_PID: sensorName = "OV5640"; break;
            case OV3660_PID: sensorName = "OV3660"; break;
            case OV7725_PID: sensorName = "OV7725"; break;
            case OV7670_PID: sensorName = "OV7670"; break;
            default:         sensorName = "Unknown"; break;
        }

        // Resolution string
        const char* resStr = "Unknown";
        switch (CAMERA_FRAME_SIZE) {
            case FRAMESIZE_QQVGA:  resStr = "160x120";  break;
            case FRAMESIZE_QVGA:   resStr = "320x240";  break;
            case FRAMESIZE_VGA:    resStr = "640x480";  break;
            case FRAMESIZE_SVGA:   resStr = "800x600";  break;
            case FRAMESIZE_XGA:    resStr = "1024x768"; break;
            case FRAMESIZE_SXGA:   resStr = "1280x1024";break;
            case FRAMESIZE_UXGA:   resStr = "1600x1200";break;
            default:               resStr = "Custom";   break;
        }

        Serial.println("[CAM]  ── Sensor Identity ──────────────────────");
        Serial.printf( "[CAM]  Sensor       : %s\n",   sensorName);
        Serial.printf( "[CAM]  PID          : 0x%04X\n", s->id.PID);
        Serial.printf( "[CAM]  MID          : 0x%04X\n", s->id.MIDH << 8 | s->id.MIDL);
        Serial.printf( "[CAM]  Resolution   : %s\n",   resStr);
        Serial.printf( "[CAM]  JPEG Quality : %d (0=best, 63=worst)\n", CAMERA_JPEG_QUALITY);
        Serial.printf( "[CAM]  FB Count     : 2\n");
        Serial.printf( "[CAM]  FB Location  : PSRAM\n");
        Serial.printf( "[CAM]  Grab Mode    : LATEST\n");
        Serial.println("[CAM]  ─────────────────────────────────────────");
    }

    // ── Sensor settings for text / OCR readability ───────────────────────
    void applySensorSettings() {
        sensor_t* s = esp_camera_sensor_get();
        if (s == nullptr) return;

        s->set_brightness(s, 0);      // -2 to 2
        s->set_contrast(s, 0);        // -2 to 2
        s->set_saturation(s, 0);      // -2 to 2
        s->set_sharpness(s, 0);       // -2 to 2
        s->set_denoise(s, 0);         // 0 to 8
        s->set_special_effect(s, 0);  // 0=No effect
        s->set_wb_mode(s, 0);         // 0=Auto white balance
        s->set_awb_gain(s, 1);        // AWB gain enable
        s->set_exposure_ctrl(s, 1);   // AEC enable
        s->set_aec2(s, 0);            // AEC DSP
        s->set_gain_ctrl(s, 1);       // AGC enable
        s->set_agc_gain(s, 0);        // AGC gain 0
        s->set_gainceiling(s, (gainceiling_t)0);
        s->set_bpc(s, 0);             // Black pixel correction
        s->set_wpc(s, 1);             // White pixel correction
        s->set_raw_gma(s, 1);         // Raw GMA
        s->set_lenc(s, 1);            // Lens correction
        s->set_hmirror(s, 0);
        s->set_vflip(s, 0);
        s->set_dcw(s, 1);             // Downsize crop window
        s->set_colorbar(s, 0);

        Serial.println("[CAM]  Sensor settings applied (optimized for text/OCR)");
    }

public:
    CameraManager()
        : _initialized(false), _captureCount(0),
          _captureFailures(0), _lastCaptureTime(0) {}

    // ── Initialize ───────────────────────────────────────────────────────
    bool init() {
        Serial.println("[CAM]  ── Camera Init ────────────────────────────");

        // Refuse to init without PSRAM
        if (!psramFound()) {
            Serial.println("[CAM]  FATAL: PSRAM not found. Camera init refused.");
            Serial.println("[CAM]  CAMERA_FB_IN_PSRAM requires PSRAM to be present.");
            Serial.println("[CAM]  Fix platformio.ini: board_build.arduino.memory_type = qio_opi");
            _initialized = false;
            return false;
        }

        size_t psramFreeBefore = ESP.getFreePsram();
        Serial.printf("[CAM]  PSRAM free before init : %u bytes\n", psramFreeBefore);

        camera_config_t config = buildConfig();

        for (int attempt = 1; attempt <= CAMERA_INIT_RETRIES; attempt++) {
            if (attempt > 1) {
                Serial.printf("[CAM]  Init retry %d/%d ...\n", attempt, CAMERA_INIT_RETRIES);
                // Deinit before retry to reset sensor state
                esp_camera_deinit();
                delay(CAMERA_INIT_RETRY_DELAY_MS);
            }

            esp_err_t err = esp_camera_init(&config);

            if (err == ESP_OK) {
                _initialized = true;

                size_t psramFreeAfter = ESP.getFreePsram();
                Serial.printf("[CAM]  PSRAM free after init  : %u bytes\n", psramFreeAfter);
                Serial.printf("[CAM]  PSRAM used by camera   : %u bytes\n",
                              psramFreeBefore - psramFreeAfter);

                applySensorSettings();
                printSensorDiagnostics();

                Serial.println("[CAM]  Camera initialized successfully");
                Serial.println("[CAM]  ─────────────────────────────────────────");
                return true;
            }

            Serial.printf("[CAM]  Init attempt %d failed: %s (err=0x%x)\n",
                          attempt, esp_err_to_name(err), err);

            if (err == ESP_ERR_NO_MEM) {
                Serial.println("[CAM]  ESP_ERR_NO_MEM — framebuffer allocation failed.");
                Serial.printf("[CAM]  PSRAM free: %u bytes\n", ESP.getFreePsram());
                Serial.printf("[CAM]  Heap free : %u bytes\n", ESP.getFreeHeap());
            }
        }

        _initialized = false;
        Serial.println("[CAM]  Camera initialization failed after all retries.");
        Serial.println("[CAM]  ─────────────────────────────────────────");
        return false;
    }

    // ── Reinitialize ─────────────────────────────────────────────────────
    bool reinit() {
        Serial.println("[CAM]  Reinitializing camera...");
        if (_initialized) {
            esp_camera_deinit();
            _initialized = false;
            delay(100);
        }
        return init();
    }

    // ── Capture ──────────────────────────────────────────────────────────
    camera_fb_t* capture() {
        if (!_initialized) {
            Serial.println("[CAM]  Not initialized — attempting init before capture...");
            if (!init()) {
                _captureFailures++;
                Serial.println("[CAPTURE] FAILED — camera not initialized");
                return nullptr;
            }
        }

        size_t heapBefore  = ESP.getFreeHeap();
        size_t psramBefore = ESP.getFreePsram();
        unsigned long t0   = millis();

        Serial.printf("[CAPTURE] Starting capture #%lu\n", _captureCount + 1);
        Serial.printf("[CAPTURE] Pre-capture  heap=%u  psram=%u\n", heapBefore, psramBefore);

        camera_fb_t* fb = nullptr;

        for (int attempt = 1; attempt <= CAMERA_CAPTURE_RETRIES; attempt++) {
            if (attempt > 1) {
                Serial.printf("[CAPTURE] Retry %d/%d\n", attempt, CAMERA_CAPTURE_RETRIES);
                delay(100);
            }

            fb = esp_camera_fb_get();

            if (fb == nullptr) {
                Serial.printf("[CAPTURE] fb_get returned NULL (attempt %d)\n", attempt);
                continue;
            }

            // Validate JPEG magic bytes (FFD8)
            if (fb->len < 2 || fb->buf[0] != 0xFF || fb->buf[1] != 0xD8) {
                Serial.printf("[CAPTURE] Invalid JPEG header: 0x%02X%02X (attempt %d)\n",
                              fb->buf[0], fb->buf[1], attempt);
                esp_camera_fb_return(fb);
                fb = nullptr;
                continue;
            }

            // ── Success ──────────────────────────────────────────────────
            unsigned long duration = millis() - t0;
            _captureCount++;
            _lastCaptureTime = millis();

            size_t heapAfter  = ESP.getFreeHeap();
            size_t psramAfter = ESP.getFreePsram();

            Serial.printf("[CAPTURE] %ux%u\n",       fb->width, fb->height);
            Serial.printf("[CAPTURE] %u bytes\n",    fb->len);
            Serial.printf("[CAPTURE] %lu ms\n",      duration);
            Serial.printf("[CAPTURE] Post-capture heap=%u  psram=%u\n", heapAfter, psramAfter);
            Serial.println("[CAPTURE] SUCCESS");

            return fb;
        }

        // ── All attempts failed ───────────────────────────────────────────
        _captureFailures++;
        Serial.println("[CAPTURE] FAILED — all attempts exhausted");

        // Auto-reinit after repeated failures
        if (_captureFailures > 0 && (_captureFailures % 5) == 0) {
            Serial.printf("[CAM]  %lu consecutive failures — triggering reinit\n",
                          (unsigned long)_captureFailures);
            reinit();
        }

        return nullptr;
    }

    // ── Return framebuffer ───────────────────────────────────────────────
    void returnFrameBuffer(camera_fb_t* fb) {
        if (fb != nullptr) {
            esp_camera_fb_return(fb);
        }
    }

    // ── Accessors ────────────────────────────────────────────────────────
    bool     isInitialized()     const { return _initialized; }
    uint32_t getCaptureCount()   const { return _captureCount; }
    uint32_t getCaptureFailures()const { return _captureFailures; }
    unsigned long getLastCaptureTime() const { return _lastCaptureTime; }

    String getStatus() const {
        return _initialized ? "ok" : "error";
    }
};

#endif // CAMERA_MANAGER_H
