#include <Arduino.h>
#include <WiFi.h>
#include <ESPAsyncWebServer.h>
#include <ArduinoJson.h>
#include <esp_camera.h>
#include <esp_heap_caps.h>

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
// SETUP
// ============================================================================

void setup() {
    Serial.begin(115200);
    delay(1000);
    
    Serial.println("\n\n==================================");
    Serial.println("Diya Smart Goggle Firmware V1");
    Serial.println("==================================");
    Serial.printf("Firmware Version: %s\n", FIRMWARE_VERSION);
    Serial.printf("Device Type: %s\n", DEVICE_TYPE);
    Serial.printf("Free Heap: %d bytes\n", ESP.getFreeHeap());
    Serial.printf("PSRAM: %d bytes\n", ESP.getPsramSize());
    Serial.println("==================================\n");

    // Initialize device state
    deviceState.init();
    Serial.println("[INIT] Device state initialized");

    // Initialize telemetry
    telemetry.init();
    Serial.println("[INIT] Telemetry initialized");

    // Initialize buttons
    buttonManager.init();
    Serial.println("[INIT] Buttons initialized");

    // Initialize camera
    Serial.println("[INIT] Initializing camera...");
    if (cameraManager.init()) {
        Serial.println("[INIT] Camera initialized successfully");
    } else {
        Serial.println("[ERROR] Camera initialization failed!");
        // Continue anyway - will retry on capture
    }

    // Connect to WiFi
    Serial.println("[WIFI] Connecting to WiFi...");
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
        Serial.printf("[WIFI] IP Address: %s\n", WiFi.localIP().toString().c_str());
        Serial.printf("[WIFI] RSSI: %d dBm\n", WiFi.RSSI());
        deviceState.setConnected(true);
    } else {
        Serial.println("[WIFI] Connection failed - will retry in background");
        deviceState.setConnected(false);
    }

    // Initialize HTTP server
    setupHttpServer(server, cameraManager, buttonManager, telemetry, deviceState);
    server.begin();
    Serial.printf("[HTTP] Server started on port %d\n", HTTP_PORT);

    Serial.println("\n[READY] Smart Goggle is ready!");
    Serial.printf("[READY] Access at: http://%s:%d\n", 
                  WiFi.localIP().toString().c_str(), HTTP_PORT);
    Serial.println("==================================\n");
}

// ============================================================================
// MAIN LOOP
// ============================================================================

void loop() {
    // Update telemetry
    telemetry.update();

    // Process button events
    buttonManager.update();

    // Check WiFi connection
    if (WiFi.status() != WL_CONNECTED) {
        if (deviceState.isConnected()) {
            Serial.println("[WIFI] Connection lost - attempting reconnect...");
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

    // Heap monitoring
    static unsigned long lastHeapCheck = 0;
    if (millis() - lastHeapCheck > 10000) {  // Every 10 seconds
        lastHeapCheck = millis();
        size_t freeHeap = ESP.getFreeHeap();
        
        if (freeHeap < HEAP_CRITICAL_THRESHOLD) {
            Serial.printf("[HEAP] CRITICAL: %d bytes free\n", freeHeap);
        } else if (freeHeap < HEAP_LOW_THRESHOLD) {
            Serial.printf("[HEAP] LOW: %d bytes free\n", freeHeap);
        }
    }

    delay(10);  // Small delay to prevent watchdog trigger
}