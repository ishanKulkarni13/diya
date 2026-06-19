#ifndef BUTTON_MANAGER_H
#define BUTTON_MANAGER_H

#include <Arduino.h>
#include <ArduinoJson.h>
#include "config.h"

enum ButtonEvent {
    BTN_EVENT_NONE,
    BTN_EVENT_SINGLE_PRESS,
    BTN_EVENT_DOUBLE_PRESS,
    BTN_EVENT_LONG_PRESS
};

struct ButtonState {
    uint8_t pin;
    String name;
    bool lastState;
    unsigned long lastPressTime;
    unsigned long pressStartTime;
    bool longPressDetected;
    int pressCount;
    unsigned long firstPressTime;
    ButtonEvent pendingEvent;
};

class ButtonManager {
private:
    ButtonState buttons[2];
    StaticJsonDocument<256> lastEvent;
    bool hasNewEvent;

    void checkButton(ButtonState& btn) {
        bool currentState = digitalRead(btn.pin) == LOW;  // Active LOW (pulled high)
        unsigned long now = millis();

        // Debounce
        if (currentState != btn.lastState) {
            if (currentState) {
                // Button pressed
                if (btn.pressCount == 0) {
                    btn.firstPressTime = now;
                }
                btn.pressStartTime = now;
                btn.longPressDetected = false;
                btn.pressCount++;
                
                Serial.printf("[BUTTON] %s pressed (count: %d)\n", 
                             btn.name.c_str(), btn.pressCount);
            } else {
                // Button released
                unsigned long pressDuration = now - btn.pressStartTime;
                
                if (!btn.longPressDetected && pressDuration < BUTTON_LONG_PRESS_MS) {
                    // Short press - wait for potential double press
                    btn.lastPressTime = now;
                    Serial.printf("[BUTTON] %s released after %lu ms\n", 
                                 btn.name.c_str(), pressDuration);
                }
            }
            
            btn.lastState = currentState;
        }

        // Check for long press (while still pressed)
        if (currentState && !btn.longPressDetected) {
            unsigned long pressDuration = now - btn.pressStartTime;
            if (pressDuration >= BUTTON_LONG_PRESS_MS) {
                btn.longPressDetected = true;
                btn.pendingEvent = BTN_EVENT_LONG_PRESS;
                publishEvent(btn.name, "long_press");
                Serial.printf("[BUTTON] %s long press detected\n", btn.name.c_str());
                
                // Reset for next press
                btn.pressCount = 0;
            }
        }

        // Check for double press timeout
        if (btn.pressCount > 0 && !currentState && !btn.longPressDetected) {
            unsigned long timeSincePress = now - btn.lastPressTime;
            
            if (timeSincePress > BUTTON_DOUBLE_PRESS_WINDOW_MS) {
                // Timeout - determine event type
                if (btn.pressCount == 1) {
                    btn.pendingEvent = BTN_EVENT_SINGLE_PRESS;
                    publishEvent(btn.name, "single_press");
                    Serial.printf("[BUTTON] %s single press confirmed\n", btn.name.c_str());
                } else if (btn.pressCount >= 2) {
                    btn.pendingEvent = BTN_EVENT_DOUBLE_PRESS;
                    publishEvent(btn.name, "double_press");
                    Serial.printf("[BUTTON] %s double press confirmed\n", btn.name.c_str());
                }
                
                // Reset for next press
                btn.pressCount = 0;
            }
        }
    }

    void publishEvent(const String& button, const String& event) {
        lastEvent.clear();
        lastEvent["type"] = "button";
        lastEvent["button"] = button;
        lastEvent["event"] = event;
        lastEvent["timestamp"] = millis();
        hasNewEvent = true;
        
        Serial.println("[BUTTON] Event published:");
        serializeJsonPretty(lastEvent, Serial);
        Serial.println();
    }

public:
    ButtonManager() : hasNewEvent(false) {}

    void init() {
        // Initialize Assist button
        buttons[0].pin = BUTTON_ASSIST_PIN;
        buttons[0].name = "assist";
        buttons[0].lastState = HIGH;
        buttons[0].lastPressTime = 0;
        buttons[0].pressStartTime = 0;
        buttons[0].longPressDetected = false;
        buttons[0].pressCount = 0;
        buttons[0].firstPressTime = 0;
        buttons[0].pendingEvent = BTN_EVENT_NONE;
        
        pinMode(BUTTON_ASSIST_PIN, INPUT_PULLUP);
        Serial.printf("[BUTTON] Assist button initialized on pin %d\n", BUTTON_ASSIST_PIN);

        // Initialize SOS button
        buttons[1].pin = BUTTON_SOS_PIN;
        buttons[1].name = "sos";
        buttons[1].lastState = HIGH;
        buttons[1].lastPressTime = 0;
        buttons[1].pressStartTime = 0;
        buttons[1].longPressDetected = false;
        buttons[1].pressCount = 0;
        buttons[1].firstPressTime = 0;
        buttons[1].pendingEvent = BTN_EVENT_NONE;
        
        pinMode(BUTTON_SOS_PIN, INPUT_PULLUP);
        Serial.printf("[BUTTON] SOS button initialized on pin %d\n", BUTTON_SOS_PIN);

        Serial.println("[BUTTON] Button manager initialized");
        Serial.println("[BUTTON] Events: single_press, double_press, long_press");
    }

    void update() {
        checkButton(buttons[0]);  // Assist
        checkButton(buttons[1]);  // SOS
    }

    bool hasEvent() const {
        return hasNewEvent;
    }

    JsonDocument getLastEvent() {
        hasNewEvent = false;
        return lastEvent;
    }

    String getStatus() const {
        return "ok";
    }

    void getEventsJson(JsonArray& events) {
        // Return recent button events (for /state endpoint)
        // Currently just returns status - could be extended to maintain event history
    }
};

#endif // BUTTON_MANAGER_H