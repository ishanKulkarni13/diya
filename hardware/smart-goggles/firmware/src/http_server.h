#ifndef HTTP_SERVER_H
#define HTTP_SERVER_H

#include <ESPAsyncWebServer.h>
#include <ArduinoJson.h>
#include <HTTPClient.h>
#include "camera_manager.h"
#include "button_manager.h"
#include "telemetry.h"
#include "device_state.h"
#include "config.h"

// Forward declarations
void setupHttpServer(AsyncWebServer& server, CameraManager& camera, 
                    ButtonManager& buttons, Telemetry& telemetry,
                    DeviceState& deviceState);

// ============================================================================
// HEALTH ENDPOINT: GET /health
// ============================================================================
void handleHealth(AsyncWebServerRequest *request, DeviceState& deviceState) {
    Serial.println("[HTTP] GET /health");
    
    StaticJsonDocument<256> doc;
    doc["status"] = "ok";
    doc["device_id"] = deviceState.getDeviceId();
    doc["connected"] = deviceState.isConnected();
    doc["uptime_s"] = deviceState.getUptime();

    String response;
    serializeJson(doc, response);
    
    request->send(200, "application/json", response);
    Serial.printf("[HTTP] Health check responded: uptime=%lu s\n", deviceState.getUptime());
}

// ============================================================================
// STATE ENDPOINT: GET /state
// ============================================================================
void handleGetState(AsyncWebServerRequest *request, CameraManager& camera,
                   ButtonManager& buttons, Telemetry& telemetry,
                   DeviceState& deviceState) {
    Serial.println("[HTTP] GET /state");
    
    DynamicJsonDocument doc(1024);
    doc["device_id"] = deviceState.getDeviceId();
    doc["connected"] = deviceState.isConnected();
    doc["battery_level"] = BATTERY_LEVEL_HARDCODED;
    doc["ultrasonic_cm"] = 0;  // Not implemented in V1
    doc["stream_fps"] = 0;     // Not implemented in V1
    doc["telemetry_hz"] = 0;   // Not implemented in V1
    
    // Add telemetry
    JsonObject telemetryObj = doc.createNestedObject("telemetry");
    telemetry.toJson(telemetryObj, deviceState.getUptime(), 
                    camera.getCaptureCount(), camera.getCaptureFailures(),
                    camera.getStatus(), buttons.getStatus(),
                    WiFi.localIP().toString());

    String response;
    serializeJson(doc, response);
    
    request->send(200, "application/json", response);
    Serial.println("[HTTP] State responded");
}

// ============================================================================
// CAPTURE ENDPOINT: GET /capture
// ============================================================================
void handleCapture(AsyncWebServerRequest *request, CameraManager& camera) {
    Serial.println("[HTTP] GET /capture - Starting capture...");
    unsigned long startTime = millis();
    
    camera_fb_t* fb = camera.capture();
    
    if (fb == nullptr) {
        Serial.println("[HTTP] Capture failed");
        request->send(503, "text/plain", "Camera capture failed");
        return;
    }

    unsigned long captureDuration = millis() - startTime;
    Serial.printf("[HTTP] Capture successful: %d bytes in %lu ms\n", 
                 fb->len, captureDuration);
    
    // Send JPEG response
    AsyncWebServerResponse *response = request->beginResponse_P(
        200,
        "image/jpeg",
        fb->buf,
        fb->len
    );
    
    response->addHeader("Cache-Control", "no-store");
    response->addHeader("X-Image-Format", "jpeg");
    response->addHeader("X-Image-Bytes", String(fb->len));
    response->addHeader("X-Capture-Duration-Ms", String(captureDuration));
    
    request->send(response);
    
    // Return frame buffer
    camera.returnFrameBuffer(fb);
    
    Serial.printf("[HTTP] Capture response sent: %d bytes\n", fb->len);
}

// ============================================================================
// REGISTER-PHONE ENDPOINT: POST /register-phone
// ============================================================================
void handleRegisterPhone(AsyncWebServerRequest *request, uint8_t *data, 
                        size_t len, DeviceState& deviceState) {
    Serial.println("[HTTP] POST /register-phone");
    
    DynamicJsonDocument doc(512);
    DeserializationError error = deserializeJson(doc, data, len);
    
    if (error) {
        Serial.printf("[HTTP] JSON parse error: %s\n", error.c_str());
        request->send(400, "application/json", "{\"error\":\"Invalid JSON\"}");
        return;
    }

    String phoneIp = doc["phone_ip"] | "";
    uint16_t phonePort = doc["port"] | 8080;
    uint16_t gogglePort = doc["goggle_port"] | HTTP_PORT;
    
    if (phoneIp.length() == 0) {
        Serial.println("[HTTP] Missing phone_ip");
        request->send(400, "application/json", "{\"error\":\"Missing phone_ip\"}");
        return;
    }

    // Clean up IP (remove http://, https://, trailing /)
    phoneIp.replace("http://", "");
    phoneIp.replace("https://", "");
    int slashPos = phoneIp.indexOf('/');
    if (slashPos > 0) {
        phoneIp = phoneIp.substring(0, slashPos);
    }

    Serial.printf("[HTTP] Registering with phone: %s:%d\n", phoneIp.c_str(), phonePort);

    // Store phone info
    deviceState.setPhoneRegistration(phoneIp, phonePort);

    // Send registration to phone
    HTTPClient http;
    String url = "http://" + phoneIp + ":" + String(phonePort) + "/register";
    
    Serial.printf("[HTTP] Posting to: %s\n", url.c_str());
    
    http.begin(url);
    http.addHeader("Content-Type", "application/json");
    http.setTimeout(PHONE_REGISTRATION_TIMEOUT_MS);

    DynamicJsonDocument regDoc(256);
    regDoc["device_id"] = deviceState.getDeviceId();
    regDoc["device_type"] = DEVICE_TYPE;
    regDoc["port"] = gogglePort;

    String regPayload;
    serializeJson(regDoc, regPayload);
    
    int httpCode = http.POST(regPayload);
    
    if (httpCode > 0) {
        Serial.printf("[HTTP] Phone registration response: %d\n", httpCode);
        if (httpCode == 200) {
            String payload = http.getString();
            Serial.printf("[HTTP] Response: %s\n", payload.c_str());
            
            request->send(200, "application/json", 
                         "{\"status\":\"ok\",\"registered\":true}");
        } else {
            request->send(502, "application/json", 
                         "{\"status\":\"error\",\"message\":\"Phone returned error\"}");
        }
    } else {
        Serial.printf("[HTTP] Phone registration failed: %s\n", 
                     http.errorToString(httpCode).c_str());
        request->send(502, "application/json", 
                     "{\"status\":\"error\",\"message\":\"Could not reach phone\"}");
    }
    
    http.end();
}

// ============================================================================
// COMMAND ENDPOINT: POST /command
// ============================================================================
void handleCommand(AsyncWebServerRequest *request, uint8_t *data, size_t len) {
    Serial.println("[HTTP] POST /command");
    
    DynamicJsonDocument doc(512);
    DeserializationError error = deserializeJson(doc, data, len);
    
    if (error) {
        Serial.printf("[HTTP] JSON parse error: %s\n", error.c_str());
        request->send(400, "application/json", "{\"error\":\"Invalid JSON\"}");
        return;
    }

    String command = doc["command"] | "";
    Serial.printf("[HTTP] Command: %s\n", command.c_str());

    if (command == "capture") {
        request->send(400, "application/json", 
                     "{\"error\":\"Use GET /capture for JPEG snapshot\"}");
    } else {
        // Acknowledge other commands
        StaticJsonDocument<128> response;
        response["status"] = "ok";
        response["command"] = command;
        
        String responseStr;
        serializeJson(response, responseStr);
        request->send(200, "application/json", responseStr);
    }
}

// ============================================================================
// ROOT ENDPOINT: GET /
// ============================================================================
void handleRoot(AsyncWebServerRequest *request) {
    Serial.println("[HTTP] GET /");
    
    String html = R"(
<!DOCTYPE html>
<html>
<head>
    <title>Diya Smart Goggle</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; background: #121212; color: #fff; }
        .container { max-width: 600px; margin: 0 auto; }
        h1 { color: #00d2ff; }
        .status { padding: 10px; background: #1e1e1e; border-radius: 5px; margin: 10px 0; }
        .ok { color: #1de9b6; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🥽 Diya Smart Goggle</h1>
        <div class="status">
            <p><strong>Device ID:</strong> )"; 
    
    html += deviceState.getDeviceId();
    html += R"(</p>
            <p><strong>Status:</strong> <span class="ok">● Online</span></p>
            <p><strong>Firmware:</strong> )";
    html += FIRMWARE_VERSION;
    html += R"(</p>
        </div>
        <p>Endpoints:</p>
        <ul>
            <li>GET /health</li>
            <li>GET /state</li>
            <li>GET /capture</li>
            <li>POST /register-phone</li>
            <li>POST /command</li>
        </ul>
    </div>
</body>
</html>
    )";
    
    request->send(200, "text/html", html);
}

// ============================================================================
// SETUP HTTP SERVER
// ============================================================================
void setupHttpServer(AsyncWebServer& server, CameraManager& camera,
                    ButtonManager& buttons, Telemetry& telemetry,
                    DeviceState& deviceState) {
    
    // Root
    server.on("/", HTTP_GET, [&deviceState](AsyncWebServerRequest *request) {
        handleRoot(request);
    });

    // Health
    server.on("/health", HTTP_GET, [&deviceState](AsyncWebServerRequest *request) {
        handleHealth(request, deviceState);
    });

    // State
    server.on("/state", HTTP_GET, [&camera, &buttons, &telemetry, &deviceState](
                                   AsyncWebServerRequest *request) {
        handleGetState(request, camera, buttons, telemetry, deviceState);
    });

    // Capture
    server.on("/capture", HTTP_GET, [&camera](AsyncWebServerRequest *request) {
        handleCapture(request, camera);
    });

    // Register Phone
    server.on("/register-phone", HTTP_POST, 
        [](AsyncWebServerRequest *request) {},
        nullptr,
        [&deviceState](AsyncWebServerRequest *request, uint8_t *data, 
                      size_t len, size_t index, size_t total) {
            if (index == 0) {  // First chunk
                handleRegisterPhone(request, data, len, deviceState);
            }
        }
    );

    // Command
    server.on("/command", HTTP_POST,
        [](AsyncWebServerRequest *request) {},
        nullptr,
        [](AsyncWebServerRequest *request, uint8_t *data, 
           size_t len, size_t index, size_t total) {
            if (index == 0) {  // First chunk
                handleCommand(request, data, len);
            }
        }
    );

    // 404 Handler
    server.onNotFound([](AsyncWebServerRequest *request) {
        Serial.printf("[HTTP] 404: %s\n", request->url().c_str());
        request->send(404, "text/plain", "Not Found");
    });

    Serial.println("[HTTP] All routes configured");
}

#endif // HTTP_SERVER_H