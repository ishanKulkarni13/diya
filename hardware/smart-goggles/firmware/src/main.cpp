#include <Arduino.h>
#include <WiFi.h>
#include <ESPAsyncWebServer.h>
#include <ArduinoJson.h>
#include <esp_camera.h>
#include <esp_heap_caps.h>
#include <esp_chip_info.h>
#include <esp_flash.h>

#include "config.h"
#include "camera_manager.h"
#include "button_manager.h"
#include "telemetry.h"
#include "http_server.h"
#include "device_state.h"

// ============================================================================
// GLOBAL OBJECTS
// ============================================================================

AsyncWebServer server(HTTP_PORT);
CameraManager cameraManager;
ButtonManager buttonManager;
Telemetry telemetry;
DeviceState deviceState;

// ============================================================================
// BOOT DIAGNOSTICS
// ============================================================================

/**
 * printBootDiagnostics()
 *
 * Prints full hardware identity and memory map at startup.
 * Call before camera init — if PSRAM is absent the camera init will fail
 * and these logs are essential for root-cause analysis.
 *
 * Sections:
 *   [BOOT]  — firmware identity and chip model
 *   [MEM]   — heap and PSRAM sizes / free / largest block
 *
 * PSRAM failure handling:
 *   If psramFound() == false we log the likely root cause and halt.
 *   Missing PSRAM is a fatal bringup error for this hardware family.
 *   We do NOT silently downgrade to DRAM framebuffers.
 */
static void printBootDiagnostics() {
    Serial.println();
    Serial.println("==================================================");
    Serial.println("  Diya Smart Goggle Firmware");
    Serial.println("==================================================");

    // ── Firmware identity ────────────────────────────────────────────────
    Serial.printf("[BOOT] Firmware Version : %s\n", FIRMWARE_VERSION);
    Serial.printf("[BOOT] Device Type      : %s\n", DEVICE_TYPE);
    Serial.printf("[BOOT] Build target     : ESP32-S3-WROOM-1-N16R8\n");
    Serial.printf("[BOOT] Board definition : 4d_systems_esp32s3_gen4_r8n16\n");
    Serial.printf("[BOOT] memory_type      : qio_opi\n");
    Serial.printf("[BOOT] Camera XCLK      : %d Hz\n", CAMERA_XCLK_HZ);
    Serial.printf("[BOOT] PSRAM mode gate  : xclk==16MHz → %s\n",
                  CAMERA_XCLK_HZ == 16000000 ? "ACTIVE" : "INACTIVE — camera will produce corrupt images");

    // ── Chip identity ────────────────────────────────────────────────────
    esp_chip_info_t chip;
    esp_chip_info(&chip);
    Serial.printf("[BOOT] Chip model       : ESP32-S3 rev %d\n", chip.revision);
    Serial.printf("[BOOT] CPU cores        : %d\n", chip.cores);

    // ── Flash ────────────────────────────────────────────────────────────
    uint32_t flashSize = 0;
    esp_flash_get_size(NULL, &flashSize);
    Serial.printf("[BOOT] Flash size       : %u bytes (%u MB)\n",
                  flashSize, flashSize / (1024 * 1024));

    // ── Heap ─────────────────────────────────────────────────────────────
    Serial.printf("[MEM]  Total Heap       : %u bytes\n", ESP.getHeapSize());
    Serial.printf("[MEM]  Free Heap        : %u bytes\n", ESP.getFreeHeap());
    Serial.printf("[MEM]  Min Free Heap    : %u bytes\n", ESP.getMinFreeHeap());
    Serial.printf("[MEM]  Max Alloc Heap   : %u bytes\n", ESP.getMaxAllocHeap());

    // ── PSRAM ─────────────────────────────────────────────────────────────
    bool psramDetected = psramFound();
    Serial.printf("[MEM]  PSRAM Found      : %s\n", psramDetected ? "YES" : "NO");

    if (psramDetected) {
        size_t psramSize    = ESP.getPsramSize();
        size_t psramFree    = ESP.getFreePsram();
        size_t psramMinFree = ESP.getMinFreePsram();
        size_t psramMaxAlloc = heap_caps_get_largest_free_block(MALLOC_CAP_SPIRAM);

        Serial.printf("[MEM]  PSRAM Size        : %u bytes (%u MB)\n",
                      psramSize, psramSize / (1024 * 1024));
        Serial.printf("[MEM]  Free PSRAM        : %u bytes\n", psramFree);
        Serial.printf("[MEM]  Min Free PSRAM    : %u bytes\n", psramMinFree);
        Serial.printf("[MEM]  Largest PSRAM blk : %u bytes\n", psramMaxAlloc);

        if (psramSize < 4 * 1024 * 1024) {
            Serial.println("[MEM]  WARNING: PSRAM detected but size < 4MB — unexpected for N16R8");
        }
    } else {
        // ── Fatal PSRAM absence — log cause and halt ──────────────────────
        Serial.println("[MEM]  PSRAM Size        : 0");
        Serial.println("[MEM]  Free PSRAM        : 0");
        Serial.println("[MEM]  Largest PSRAM blk : 0");
        Serial.println();
        Serial.println("[FATAL] ============================================================");
        Serial.println("[FATAL] PSRAM NOT DETECTED — camera framebuffer malloc will fail.");
        Serial.println("[FATAL] This firmware targets ESP32-S3-N16R8 (16MB Flash, 8MB PSRAM).");
        Serial.println("[FATAL] ");
        Serial.println("[FATAL] Likely root causes:");
        Serial.println("[FATAL]   1. Wrong board definition in platformio.ini");
        Serial.println("[FATAL]      Required: board = 4d_systems_esp32s3_gen4_r8n16");
        Serial.println("[FATAL]      Required: board_build.arduino.memory_type = qio_opi");
        Serial.println("[FATAL]      The N16R8 uses OPI PSRAM — 'qio' memory_type will not");
        Serial.println("[FATAL]      initialize the PSRAM controller.");
        Serial.println("[FATAL]   2. Flash not fully erased before reflash");
        Serial.println("[FATAL]      Fix: esptool.py --chip esp32s3 erase_flash");
        Serial.println("[FATAL]      Then re-flash with correct board definition.");
        Serial.println("[FATAL]   3. Hardware fault on PSRAM lines");
        Serial.println("[FATAL]      Unlikely if the board worked previously in Arduino IDE.");
        Serial.println("[FATAL] ");
        Serial.println("[FATAL] Camera initialization will NOT proceed without PSRAM.");
        Serial.println("[FATAL] Halting. Fix PSRAM configuration and reflash.");
        Serial.println("[FATAL] ============================================================");
    }

    Serial.println("==================================================");
    Serial.println();
}

// ============================================================================
// SETUP
// ============================================================================

void setup() {
    Serial.begin(115200);
    delay(1000);  // Allow serial monitor to attach

    // ── Boot diagnostics first ───────────────────────────────────────────
    printBootDiagnostics();

    // ── Fatal check: no PSRAM = no camera = no point continuing ─────────
    if (!psramFound()) {
        // Loop here so the FATAL messages remain visible on serial monitor.
        // All other features (WiFi, HTTP, buttons) cannot serve camera
        // requests anyway — the only path forward is a correct reflash.
        Serial.println("[FATAL] System halted. Reflash with correct board definition.");
        while (true) {
            delay(5000);
            Serial.println("[FATAL] Still halted — PSRAM not found. Reflash required.");
        }
    }

    // ── Initialize device state ──────────────────────────────────────────
    deviceState.init();
    Serial.println("[INIT] Device state initialized");

    // ── Initialize telemetry ─────────────────────────────────────────────
    telemetry.init();
    Serial.println("[INIT] Telemetry initialized");

    // ── Initialize buttons ───────────────────────────────────────────────
    buttonManager.init();
    Serial.println("[INIT] Buttons initialized");

    // ── Initialize camera ────────────────────────────────────────────────
    Serial.println("[INIT] Initializing camera...");
    if (cameraManager.init()) {
        Serial.println("[INIT] Camera initialized successfully");
    } else {
        Serial.println("[ERROR] Camera initialization failed after retries.");
        Serial.println("[ERROR] HTTP server will start. Capture endpoint returns 503.");
        Serial.println("[ERROR] Camera will be retried on first capture request.");
    }

    // ── Connect to WiFi ──────────────────────────────────────────────────
    Serial.println("[WIFI] Connecting...");
    WiFi.mode(WIFI_STA);
    WiFi.begin(DEFAULT_WIFI_SSID, DEFAULT_WIFI_PASSWORD);

    unsigned long wifiStart = millis();
    while (WiFi.status() != WL_CONNECTED &&
           (millis() - wifiStart) < WIFI_CONNECT_TIMEOUT_MS) {
        delay(500);
        Serial.print(".");
    }
    Serial.println();

    if (WiFi.status() == WL_CONNECTED) {
        Serial.println("[WIFI] Connected!");
        Serial.printf("[WIFI] IP Address : %s\n", WiFi.localIP().toString().c_str());
        Serial.printf("[WIFI] RSSI       : %d dBm\n", WiFi.RSSI());
        deviceState.setConnected(true);
    } else {
        Serial.println("[WIFI] Connection failed — will retry in background");
        deviceState.setConnected(false);
    }

    // ── Start HTTP server ────────────────────────────────────────────────
    setupHttpServer(server, cameraManager, buttonManager, telemetry, deviceState);
    server.begin();
    Serial.printf("[HTTP] Server started on port %d\n", HTTP_PORT);

    // ── Ready ────────────────────────────────────────────────────────────
    Serial.println();
    Serial.println("[READY] Smart Goggle is ready!");
    if (WiFi.status() == WL_CONNECTED) {
        Serial.printf("[READY] Access at: http://%s:%d\n",
                      WiFi.localIP().toString().c_str(), HTTP_PORT);
    }
    Serial.println();
}

// ============================================================================
// MAIN LOOP
// ============================================================================

void loop() {
    // Update telemetry
    telemetry.update();

    // Process button events
    buttonManager.update();

    // ── WiFi watchdog ────────────────────────────────────────────────────
    if (WiFi.status() != WL_CONNECTED) {
        if (deviceState.isConnected()) {
            Serial.println("[WIFI] Connection lost — attempting reconnect...");
            deviceState.setConnected(false);
        }

        static unsigned long lastReconnectAttempt = 0;
        if (millis() - lastReconnectAttempt > WIFI_RECONNECT_INTERVAL_MS) {
            lastReconnectAttempt = millis();
            Serial.println("[WIFI] Reconnecting...");
            WiFi.reconnect();
        }
    } else {
        if (!deviceState.isConnected()) {
            Serial.println("[WIFI] Reconnected!");
            Serial.printf("[WIFI] IP: %s\n", WiFi.localIP().toString().c_str());
            deviceState.setConnected(true);
        }
    }

    // ── Heap / PSRAM monitoring ──────────────────────────────────────────
    static unsigned long lastHeapCheck = 0;
    if (millis() - lastHeapCheck > 10000) {  // Every 10 seconds
        lastHeapCheck = millis();
        size_t freeHeap = ESP.getFreeHeap();
        size_t freePsram = ESP.getFreePsram();

        if (freeHeap < HEAP_CRITICAL_THRESHOLD) {
            Serial.printf("[HEAP] CRITICAL: %u bytes free\n", freeHeap);
        } else if (freeHeap < HEAP_LOW_THRESHOLD) {
            Serial.printf("[HEAP] LOW: %u bytes free\n", freeHeap);
        }

        if (freePsram < PSRAM_LOW_THRESHOLD) {
            Serial.printf("[PSRAM] LOW: %u bytes free\n", freePsram);
        }
    }

    delay(10);  // Small delay to prevent watchdog trigger
}
