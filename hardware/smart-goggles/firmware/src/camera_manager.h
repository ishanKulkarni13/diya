#ifndef CAMERA_MANAGER_H
#define CAMERA_MANAGER_H

#include <Arduino.h>
#include <esp_camera.h>
#include "config.h"

class CameraManager {
private:
    bool initialized;
    uint32_t captureCount;
    uint32_t captureFailures;
    unsigned long lastCaptureTime;

    camera_config_t getCameraConfig() {
        camera_config_t config;
        config.ledc_channel = LEDC_CHANNEL_0;
        config.ledc_timer = LEDC_TIMER_0;
        config.pin_d0 = CAM_PIN_D0;
        config.pin_d1 = CAM_PIN_D1;
        config.pin_d2 = CAM_PIN_D2;
        config.pin_d3 = CAM_PIN_D3;
        config.pin_d4 = CAM_PIN_D4;
        config.pin_d5 = CAM_PIN_D5;
        config.pin_d6 = CAM_PIN_D6;
        config.pin_d7 = CAM_PIN_D7;
        config.pin_xclk = CAM_PIN_XCLK;
        config.pin_pclk = CAM_PIN_PCLK;
        config.pin_vsync = CAM_PIN_VSYNC;
        config.pin_href = CAM_PIN_HREF;
        config.pin_sscb_sda = CAM_PIN_SIOD;
        config.pin_sscb_scl = CAM_PIN_SIOC;
        config.pin_pwdn = CAM_PIN_PWDN;
        config.pin_reset = CAM_PIN_RESET;
        config.xclk_freq_hz = 20000000;
        config.pixel_format = PIXFORMAT_JPEG;
        config.frame_size = CAMERA_FRAME_SIZE;
        config.jpeg_quality = CAMERA_JPEG_QUALITY;
        config.fb_count = 2;  // Double buffering for stability
        config.grab_mode = CAMERA_GRAB_LATEST;

        return config;
    }

public:
    CameraManager() : initialized(false), captureCount(0), 
                      captureFailures(0), lastCaptureTime(0) {}

    bool init() {
        Serial.println("[CAMERA] Initializing...");
        
        camera_config_t config = getCameraConfig();

        // Attempt initialization with retries
        for (int attempt = 0; attempt < CAMERA_INIT_RETRIES; attempt++) {
            if (attempt > 0) {
                Serial.printf("[CAMERA] Retry %d/%d...\n", 
                             attempt + 1, CAMERA_INIT_RETRIES);
                delay(CAMERA_INIT_RETRY_DELAY_MS);
            }

            esp_err_t err = esp_camera_init(&config);
            
            if (err == ESP_OK) {
                initialized = true;
                Serial.println("[CAMERA] Initialized successfully");
                Serial.printf("[CAMERA] Resolution: %dx%d\n", 
                             config.frame_size == FRAMESIZE_XGA ? 1024 : 800,
                             config.frame_size == FRAMESIZE_XGA ? 768 : 600);
                Serial.printf("[CAMERA] JPEG Quality: %d\n", config.jpeg_quality);
                
                // Configure sensor settings for better text readability
                sensor_t * s = esp_camera_sensor_get();
                if (s != NULL) {
                    s->set_brightness(s, 0);     // -2 to 2
                    s->set_contrast(s, 0);       // -2 to 2
                    s->set_saturation(s, 0);     // -2 to 2
                    s->set_sharpness(s, 0);      // -2 to 2
                    s->set_denoise(s, 0);        // 0 to 8
                    s->set_special_effect(s, 0); // 0 to 6 (0 = No Effect)
                    s->set_wb_mode(s, 0);        // 0 to 4 (0 = Auto)
                    s->set_awb_gain(s, 1);       // 0 = disable , 1 = enable
                    s->set_exposure_ctrl(s, 1);  // 0 = disable , 1 = enable
                    s->set_aec2(s, 0);           // 0 = disable , 1 = enable
                    s->set_gain_ctrl(s, 1);      // 0 = disable , 1 = enable
                    s->set_agc_gain(s, 0);       // 0 to 30
                    s->set_gainceiling(s, (gainceiling_t)0);  // 0 to 6
                    s->set_bpc(s, 0);            // 0 = disable , 1 = enable
                    s->set_wpc(s, 1);            // 0 = disable , 1 = enable
                    s->set_raw_gma(s, 1);        // 0 = disable , 1 = enable
                    s->set_lenc(s, 1);           // 0 = disable , 1 = enable
                    s->set_hmirror(s, 0);        // 0 = disable , 1 = enable
                    s->set_vflip(s, 0);          // 0 = disable , 1 = enable
                    s->set_dcw(s, 1);            // 0 = disable , 1 = enable
                    s->set_colorbar(s, 0);       // 0 = disable , 1 = enable
                    
                    Serial.println("[CAMERA] Sensor settings configured for text readability");
                }
                
                return true;
            }

            Serial.printf("[CAMERA] Init failed: %s (0x%x)\n", 
                         esp_err_to_name(err), err);
        }

        Serial.println("[CAMERA] Initialization failed after all retries");
        initialized = false;
        return false;
    }

    bool reinit() {
        Serial.println("[CAMERA] Reinitializing camera...");
        esp_camera_deinit();
        delay(100);
        return init();
    }

    camera_fb_t* capture() {
        if (!initialized) {
            Serial.println("[CAMERA] Not initialized - attempting init...");
            if (!init()) {
                captureFailures++;
                return nullptr;
            }
        }

        unsigned long startTime = millis();
        Serial.println("[CAMERA] Capturing frame...");

        // Capture with retry logic
        camera_fb_t* fb = nullptr;
        for (int attempt = 0; attempt < CAMERA_CAPTURE_RETRIES; attempt++) {
            if (attempt > 0) {
                Serial.printf("[CAMERA] Capture retry %d/%d\n", 
                             attempt + 1, CAMERA_CAPTURE_RETRIES);
                delay(100);
            }

            fb = esp_camera_fb_get();
            
            if (fb != nullptr) {
                unsigned long duration = millis() - startTime;
                lastCaptureTime = millis();
                captureCount++;
                
                Serial.printf("[CAMERA] Capture successful - %d bytes in %lu ms\n", 
                             fb->len, duration);
                Serial.printf("[CAMERA] Format: %s, Size: %dx%d\n",
                             fb->format == PIXFORMAT_JPEG ? "JPEG" : "RAW",
                             fb->width, fb->height);
                
                // Validate JPEG magic bytes
                if (fb->len >= 2 && fb->buf[0] == 0xFF && fb->buf[1] == 0xD8) {
                    Serial.println("[CAMERA] JPEG magic bytes validated");
                    return fb;
                } else {
                    Serial.printf("[CAMERA] Invalid JPEG magic: 0x%02X%02X\n", 
                                 fb->buf[0], fb->buf[1]);
                    esp_camera_fb_return(fb);
                    fb = nullptr;
                    captureFailures++;
                }
            } else {
                Serial.println("[CAMERA] Capture failed - fb is null");
            }
        }

        captureFailures++;
        Serial.println("[CAMERA] All capture attempts failed");
        
        // If multiple failures, try reinitializing camera
        if (captureFailures % 5 == 0) {
            Serial.println("[CAMERA] Multiple failures detected - reinitializing...");
            reinit();
        }
        
        return nullptr;
    }

    void returnFrameBuffer(camera_fb_t* fb) {
        if (fb != nullptr) {
            esp_camera_fb_return(fb);
        }
    }

    // Status information
    bool isInitialized() const { return initialized; }
    uint32_t getCaptureCount() const { return captureCount; }
    uint32_t getCaptureFailures() const { return captureFailures; }
    unsigned long getLastCaptureTime() const { return lastCaptureTime; }

    String getStatus() const {
        if (initialized) {
            return "ok";
        } else {
            return "error";
        }
    }
};

#endif // CAMERA_MANAGER_H