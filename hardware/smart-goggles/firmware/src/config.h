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
#define DEFAULT_WIFI_SSID "Your-WiFi-SSID"
#define DEFAULT_WIFI_PASSWORD "Your-WiFi-Password"

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

// Image resolution (prioritize quality and text readability)
#define CAMERA_FRAME_SIZE FRAMESIZE_XGA  // 1024x768
#define CAMERA_JPEG_QUALITY 12  // 0-63, lower is better quality

// Camera pins for ESP32-S3 with OV5640
#define CAM_PIN_PWDN    -1
#define CAM_PIN_RESET   -1
#define CAM_PIN_XCLK    15
#define CAM_PIN_SIOD    4
#define CAM_PIN_SIOC    5

#define CAM_PIN_D7      16
#define CAM_PIN_D6      17
#define CAM_PIN_D5      18
#define CAM_PIN_D4      12
#define CAM_PIN_D3      10
#define CAM_PIN_D2      8
#define CAM_PIN_D1      9
#define CAM_PIN_D0      11

#define CAM_PIN_VSYNC   6
#define CAM_PIN_HREF    7
#define CAM_PIN_PCLK    13

// Camera initialization retry configuration
#define CAMERA_INIT_RETRIES 3
#define CAMERA_INIT_RETRY_DELAY_MS 1000

// Capture timeout
#define CAMERA_CAPTURE_TIMEOUT_MS 5000
#define CAMERA_CAPTURE_RETRIES 2

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

// Heap monitoring thresholds
#define HEAP_LOW_THRESHOLD 50000
#define HEAP_CRITICAL_THRESHOLD 20000

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