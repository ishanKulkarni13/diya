#ifndef CONFIG_H
#define CONFIG_H

// ============================================================================
// DEVICE CONFIGURATION
// ============================================================================

#define DEVICE_TYPE "goggle"
#define FIRMWARE_VERSION "1.0.0"
#define DEVICE_NAME "Smart-Goggle"

// ============================================================================
// WiFi CONFIGURATION
// ============================================================================

// Default WiFi credentials (can be changed via serial or web interface)
#define DEFAULT_WIFI_SSID "Cat"
#define DEFAULT_WIFI_PASSWORD "9136360202"

// WiFi connection timeout
#define WIFI_CONNECT_TIMEOUT_MS 20000
#define WIFI_RECONNECT_INTERVAL_MS 5000

// ============================================================================
// HTTP SERVER CONFIGURATION
// ============================================================================

#define HTTP_PORT 9000
#define MAX_HTTP_CLIENTS 4

// ============================================================================
// CAMERA CONFIGURATION (OV5640)
// ============================================================================

// Image resolution (prioritize quality and text readability for OCR)
#define CAMERA_FRAME_SIZE    FRAMESIZE_XGA  // 1024x768
#define CAMERA_JPEG_QUALITY  12             // 0-63, lower = better quality

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
// OV5640 operates correctly at 16 MHz. 20 MHz also works electrically,
// but the psram_mode gate in cam_hal.c is the deciding constraint.
#define CAMERA_XCLK_HZ       16000000      // 16 MHz — required for PSRAM DMA mode

// Camera pins for ESP32-S3-WROOM-1-N16R8 with OV5640
// These match the standard ESP32-S3-CAM style layout verified against
// the Freenove ESP32-S3-WROOM reference schematic.
#define CAM_PIN_PWDN    -1   // Power down: not connected (module has no PWDN)
#define CAM_PIN_RESET   -1   // Reset: not connected (module has no hard reset)
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

// Camera initialization retry configuration
#define CAMERA_INIT_RETRIES        3
#define CAMERA_INIT_RETRY_DELAY_MS 1000

// Capture configuration
#define CAMERA_CAPTURE_TIMEOUT_MS  5000
#define CAMERA_CAPTURE_RETRIES     2

// ============================================================================
// BUTTON CONFIGURATION
// ============================================================================

#define BUTTON_ASSIST_PIN 21
#define BUTTON_SOS_PIN 47

// Button debounce and timing (milliseconds)
#define BUTTON_DEBOUNCE_MS 50
#define BUTTON_LONG_PRESS_MS 1000
#define BUTTON_DOUBLE_PRESS_WINDOW_MS 400

// ============================================================================
// TELEMETRY CONFIGURATION
// ============================================================================

// Hardcoded battery level (hardware integration postponed)
#define BATTERY_LEVEL_HARDCODED 75

// ============================================================================
// MEMORY MONITORING THRESHOLDS
// ============================================================================

// Internal heap low-water marks
#define HEAP_LOW_THRESHOLD      50000   // Warn when free heap drops below 50 KB
#define HEAP_CRITICAL_THRESHOLD 20000   // Critical when free heap drops below 20 KB

// PSRAM low-water threshold for periodic monitoring
#define PSRAM_LOW_THRESHOLD 500000      // 500 KB — warn if PSRAM free falls below this

// ============================================================================
// LOGGING CONFIGURATION
// ============================================================================

#define LOG_TAG "GOGGLE"
#define ENABLE_VERBOSE_LOGGING 1

// ============================================================================
// PHONE REGISTRATION
// ============================================================================

#define PHONE_REGISTRATION_TIMEOUT_MS 5000

#endif // CONFIG_H