#ifndef DEVICE_STATE_H
#define DEVICE_STATE_H

#include <Arduino.h>
#include <ArduinoJson.h>

class DeviceState {
private:
    String deviceId;
    bool connected;
    unsigned long bootTime;
    
    // Phone registration
    String phoneIp;
    uint16_t phonePort;
    bool phoneRegistered;

public:
    DeviceState() : connected(false), bootTime(0), 
                    phonePort(0), phoneRegistered(false) {}

    void init() {
        bootTime = millis();
        
        // Generate device ID from MAC address
        uint8_t mac[6];
        WiFi.macAddress(mac);
        deviceId = String(DEVICE_TYPE) + "-" + 
                   String(mac[3], HEX) + String(mac[4], HEX) + String(mac[5], HEX);
        
        Serial.printf("[STATE] Device ID: %s\n", deviceId.c_str());
    }

    // Getters
    String getDeviceId() const { return deviceId; }
    bool isConnected() const { return connected; }
    unsigned long getUptime() const { return (millis() - bootTime) / 1000; }
    
    String getPhoneIp() const { return phoneIp; }
    uint16_t getPhonePort() const { return phonePort; }
    bool isPhoneRegistered() const { return phoneRegistered; }

    // Setters
    void setConnected(bool state) { 
        if (connected != state) {
            connected = state;
            Serial.printf("[STATE] Connection state: %s\n", state ? "CONNECTED" : "DISCONNECTED");
        }
    }

    void setPhoneRegistration(const String& ip, uint16_t port) {
        phoneIp = ip;
        phonePort = port;
        phoneRegistered = true;
        Serial.printf("[STATE] Phone registered: %s:%d\n", ip.c_str(), port);
    }

    void clearPhoneRegistration() {
        phoneIp = "";
        phonePort = 0;
        phoneRegistered = false;
        Serial.println("[STATE] Phone registration cleared");
    }
};

#endif // DEVICE_STATE_H