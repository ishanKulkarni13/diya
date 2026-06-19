#include <BLEDevice.h>
#include <BLEUtils.h>
#include <BLEServer.h>
#include <BLE2902.h>

// Logging macros
#define LOGI(...) Serial.printf(__VA_ARGS__)

// BLE UUIDs
#define SERVICE_UUID        "1b050001-c852-4752-b883-fa4c0342ab01"
#define TX_CHARACTERISTIC   "1b050002-c852-4752-b883-fa4c0342ab01" // App writes here
#define RX_CHARACTERISTIC   "1b050003-c852-4752-b883-fa4c0342ab01" // Cane notifies here

// Pin definitions
#define BUTTON_PIN 0   // ESP32 Dev Module BOOT button
#define TRIG_PIN   18  // HC-SR04 Trigger
#define ECHO_PIN   19  // HC-SR04 Echo
#define LED_PIN    23  // LED for haptic simulation

BLEServer* pServer = NULL;
BLECharacteristic* pRxCharacteristic = NULL;
BLECharacteristic* pTxCharacteristic = NULL;

bool deviceConnected = false;
bool oldDeviceConnected = false;

// Non-blocking timers
unsigned long lastHeartbeatTime = 0;
const unsigned long HEARTBEAT_INTERVAL = 5000;

unsigned long lastUltrasonicTime = 0;
const unsigned long ULTRASONIC_INTERVAL = 100; // 10Hz sampling

unsigned long lastObstaclePacketTime = 0;
const unsigned long OBSTACLE_PACKET_INTERVAL = 500; // Send every 500ms when connected

// Button debounce
bool lastButtonState = HIGH;
bool currentButtonState = HIGH;
unsigned long lastDebounceTime = 0;
const unsigned long DEBOUNCE_DELAY = 50;

// Ultrasonic state
float currentDistance = -1.0;
float filteredDistance = -1.0;
const float ALPHA = 0.3; // EMA filter coefficient

// Obstacle detection
const float OBSTACLE_THRESHOLD = 150.0; // cm
bool obstacleDetected = false;

// LED haptic state
unsigned long lastLedToggleTime = 0;
bool ledState = false;
int ledBlinkInterval = 0; // 0 = off, >0 = blink interval in ms

class MyServerCallbacks: public BLEServerCallbacks {
    void onConnect(BLEServer* pServer) {
      deviceConnected = true;
      LOGI("[BLE] Connected\n");
    }

    void onDisconnect(BLEServer* pServer) {
      deviceConnected = false;
      LOGI("[BLE] Disconnected\n");
    }
};

class MyTxCallbacks : public BLECharacteristicCallbacks {
    void onWrite(BLECharacteristic *pCharacteristic) {
        auto rxValue = pCharacteristic->getValue();
        LOGI("[BLE] Received Value: %s\n", rxValue.c_str());
    }
};

// ─────────────────────────────────────────────────────────────
// Helper Functions
// ─────────────────────────────────────────────────────────────

/**
 * Read distance from HC-SR04 ultrasonic sensor
 * Returns distance in cm, or -1.0 if reading failed
 */
float readDistanceCM() {
  // Send 10us pulse to trigger pin
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);
  
  // Read echo pulse duration (timeout after 30ms)
  long duration = pulseIn(ECHO_PIN, HIGH, 30000);
  
  if (duration == 0) {
    // Timeout or no echo
    return -1.0;
  }
  
  // Calculate distance: duration/2 * speed of sound (0.0343 cm/us)
  float distance = (duration / 2.0) * 0.0343;
  
  // Validate range (HC-SR04 spec: 2cm - 400cm)
  if (distance < 2.0 || distance > 400.0) {
    return -1.0;
  }
  
  return distance;
}

/**
 * Update LED pattern based on distance
 * DANGER (0-50cm): Solid ON
 * WARNING (50-100cm): Fast blink (200ms)
 * CAUTION (100-150cm): Slow blink (500ms)
 * CLEAR (>150cm): OFF
 */
void updateLedPattern(float distance) {
  if (distance < 0) {
    // Invalid reading - turn off LED
    ledBlinkInterval = 0;
    digitalWrite(LED_PIN, LOW);
    ledState = false;
    return;
  }
  
  if (distance <= 50.0) {
    // DANGER: Solid ON
    ledBlinkInterval = 0;
    digitalWrite(LED_PIN, HIGH);
    ledState = true;
  } else if (distance <= 100.0) {
    // WARNING: Fast blink
    ledBlinkInterval = 200;
  } else if (distance <= 150.0) {
    // CAUTION: Slow blink
    ledBlinkInterval = 500;
  } else {
    // CLEAR: OFF
    ledBlinkInterval = 0;
    digitalWrite(LED_PIN, LOW);
    ledState = false;
  }
}

/**
 * Send obstacle packet via BLE notification
 */
void sendObstaclePacket() {
  if (!deviceConnected || currentDistance < 0) {
    return;
  }
  
  // Determine if obstacle is detected (under threshold)
  obstacleDetected = (currentDistance <= OBSTACLE_THRESHOLD);
  
  // Build JSON packet
  String packet = "{\"v\":1,\"t\":\"obstacle\",\"distance_cm\":";
  packet += String(currentDistance, 1); // 1 decimal place
  packet += ",\"detected\":";
  packet += obstacleDetected ? "true" : "false";
  packet += "}";
  
  // Send notification
  pRxCharacteristic->setValue(packet.c_str());
  pRxCharacteristic->notify();
  
  if (obstacleDetected) {
    LOGI("[OBSTACLE] %.1f cm - DETECTED\n", currentDistance);
  }
}

void setup() {
  Serial.begin(115200);
  
  // Pin initialization
  pinMode(BUTTON_PIN, INPUT_PULLUP);
  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);
  pinMode(LED_PIN, OUTPUT);
  
  digitalWrite(TRIG_PIN, LOW);
  digitalWrite(LED_PIN, LOW);

  LOGI("[INIT] Starting Diya Cane BLE Server...\n");
  LOGI("[INIT] Pins - Button:%d Trig:%d Echo:%d LED:%d\n", BUTTON_PIN, TRIG_PIN, ECHO_PIN, LED_PIN);
  
  BLEDevice::init("DIYA_CANE_DEV");
  
  // Set MTU for larger JSON payloads
  BLEDevice::setMTU(512);

  pServer = BLEDevice::createServer();
  pServer->setCallbacks(new MyServerCallbacks());

  BLEService *pService = pServer->createService(SERVICE_UUID);

  pRxCharacteristic = pService->createCharacteristic(
                      RX_CHARACTERISTIC,
                      BLECharacteristic::PROPERTY_READ   |
                      BLECharacteristic::PROPERTY_NOTIFY
                    );
  pRxCharacteristic->addDescriptor(new BLE2902());

  pTxCharacteristic = pService->createCharacteristic(
                      TX_CHARACTERISTIC,
                      BLECharacteristic::PROPERTY_WRITE |
                      BLECharacteristic::PROPERTY_WRITE_NR
                    );
  pTxCharacteristic->setCallbacks(new MyTxCallbacks());

  pService->start();

  BLEAdvertising *pAdvertising = BLEDevice::getAdvertising();
  pAdvertising->addServiceUUID(SERVICE_UUID);
  pAdvertising->setScanResponse(true);
  pAdvertising->setMinPreferred(0x06);
  pAdvertising->setMinPreferred(0x12);
  BLEDevice::startAdvertising();
  
  LOGI("[BLE] Advertising started\n");
}

void loop() {
  unsigned long currentMillis = millis();

  // ─────────────────────────────────────────────────────────────
  // Ultrasonic Sensor Reading (10Hz)
  // ─────────────────────────────────────────────────────────────
  if (currentMillis - lastUltrasonicTime >= ULTRASONIC_INTERVAL) {
    lastUltrasonicTime = currentMillis;
    
    float rawDistance = readDistanceCM();
    
    if (rawDistance > 0) {
      currentDistance = rawDistance;
      
      // Apply EMA filter to smooth readings
      if (filteredDistance < 0) {
        // First valid reading - initialize filter
        filteredDistance = currentDistance;
      } else {
        filteredDistance = ALPHA * currentDistance + (1.0 - ALPHA) * filteredDistance;
      }
      
      // Update LED pattern based on filtered distance
      updateLedPattern(filteredDistance);
      
      LOGI("[US] %.1f cm (filtered: %.1f cm)\n", currentDistance, filteredDistance);
    } else {
      // Invalid reading - don't update distance but log it
      LOGI("[US] Invalid reading\n");
    }
  }

  // ─────────────────────────────────────────────────────────────
  // LED Blinking (for WARNING and CAUTION states)
  // ─────────────────────────────────────────────────────────────
  if (ledBlinkInterval > 0) {
    if (currentMillis - lastLedToggleTime >= ledBlinkInterval) {
      lastLedToggleTime = currentMillis;
      ledState = !ledState;
      digitalWrite(LED_PIN, ledState ? HIGH : LOW);
    }
  }

  // ─────────────────────────────────────────────────────────────
  // Connection Management
  // ─────────────────────────────────────────────────────────────
  if (deviceConnected) {
    if (!oldDeviceConnected) {
      // Just connected: Send Hello
      delay(500); // Give the client a moment to subscribe to notifications
      String helloMsg = "{\"v\":1,\"t\":\"hello\",\"protocol\":1,\"firmware\":\"1.0.0\"}";
      pRxCharacteristic->setValue(helloMsg.c_str());
      pRxCharacteristic->notify();
      LOGI("[HELLO] Sent handshake\n");
      
      oldDeviceConnected = deviceConnected;
      lastHeartbeatTime = currentMillis; // Reset heartbeat timer
      lastObstaclePacketTime = currentMillis; // Reset obstacle packet timer
    }

    // ─────────────────────────────────────────────────────────────
    // Heartbeat (every 5s)
    // ─────────────────────────────────────────────────────────────
    if (currentMillis - lastHeartbeatTime >= HEARTBEAT_INTERVAL) {
      lastHeartbeatTime = currentMillis;
      String hbMsg = "{\"v\":1,\"t\":\"heartbeat\"}";
      pRxCharacteristic->setValue(hbMsg.c_str());
      pRxCharacteristic->notify();
      LOGI("[HEARTBEAT] Sent\n");
    }

    // ─────────────────────────────────────────────────────────────
    // Obstacle Packet (every 500ms when connected)
    // ─────────────────────────────────────────────────────────────
    if (currentMillis - lastObstaclePacketTime >= OBSTACLE_PACKET_INTERVAL) {
      lastObstaclePacketTime = currentMillis;
      sendObstaclePacket();
    }

    // ─────────────────────────────────────────────────────────────
    // Button Handling (with debounce)
    // ─────────────────────────────────────────────────────────────
    int reading = digitalRead(BUTTON_PIN);
    if (reading != lastButtonState) {
      lastDebounceTime = currentMillis;
    }

    if ((currentMillis - lastDebounceTime) > DEBOUNCE_DELAY) {
      if (reading != currentButtonState) {
        currentButtonState = reading;
        
        // BOOT button is pulled up, so LOW means pressed
        if (currentButtonState == LOW) {
           String btnMsg = "{\"v\":1,\"t\":\"button\",\"button\":1,\"press\":\"single\"}";
           pRxCharacteristic->setValue(btnMsg.c_str());
           pRxCharacteristic->notify();
           LOGI("[BUTTON] Pressed\n");
        }
      }
    }
    lastButtonState = reading;
  }

  // ─────────────────────────────────────────────────────────────
  // Disconnecting
  // ─────────────────────────────────────────────────────────────
  if (!deviceConnected && oldDeviceConnected) {
      delay(500); // Give the bluetooth stack a chance to cleanup
      pServer->startAdvertising(); // restart advertising
      LOGI("[BLE] Restarting advertising\n");
      oldDeviceConnected = deviceConnected;
  }
}
