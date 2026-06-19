#ifndef TELEMETRY_H
#define TELEMETRY_H

#include <Arduino.h>
#include <WiFi.h>
#include <ArduinoJson.h>
#include "config.h"

class Telemetry {
private:
    unsigned long lastUpdate;
    int rssi;
    size_t heapFree;
    size_t heapMin;

public:
    Telemetry() : lastUpdate(0), rssi(0), heapFree(0), heapMin(0) {}

    void init() {
        Serial.println("[TELEMETRY] Initializing...");
        update();
        Serial.println("[TELEMETRY] Initialized");
    }

    void update() {
        unsigned long now = millis();
        if (now - lastUpdate < 1000) {  // Update at most once per second
            return;
        }
        
        lastUpdate = now;

        // WiFi RSSI
        if (WiFi.status() == WL_CONNECTED) {
            rssi = WiFi.RSSI();
        } else {
            rssi = 0;
        }

        // Heap memory
        heapFree = ESP.getFreeHeap();
        heapMin = ESP.getMinFreeHeap();
    }

    int getRSSI() const { return rssi; }
    size_t getHeapFree() const { return heapFree; }
    size_t getHeapMin() const { return heapMin; }

    void toJson(JsonObject& obj, uint32_t uptime, uint32_t captureCount, 
                uint32_t captureFailures, const String& cameraStatus,
                const String& buttonStatus, const String& ipAddress) {
        obj["battery"] = BATTERY_LEVEL_HARDCODED;
        obj["wifi_rssi"] = rssi;
        obj["uptime"] = uptime;
        obj["heap_free"] = heapFree;
        obj["heap_min"] = heapMin;
        obj["camera"] = cameraStatus;
        obj["buttons"] = buttonStatus;
        obj["ip"] = ipAddress;
        obj["captures"] = captureCount;
        obj["capture_failures"] = captureFailures;
    }
};

#endif // TELEMETRY_H