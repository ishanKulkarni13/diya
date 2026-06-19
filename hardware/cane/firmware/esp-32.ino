#include <BLEDevice.h>
#include <BLEUtils.h>
#include <BLEServer.h>
#include <BLE2902.h>

#define SERVICE_UUID        "1b050001-c852-4752-b883-fa4c0342ab01"
#define TX_CHARACTERISTIC   "1b050002-c852-4752-b883-fa4c0342ab01" // App writes here
#define RX_CHARACTERISTIC   "1b050003-c852-4752-b883-fa4c0342ab01" // Cane notifies here

// ESP32 Dev Module BOOT button is typically GPIO 0
#define BUTTON_PIN 0

BLEServer* pServer = NULL;
BLECharacteristic* pRxCharacteristic = NULL;
BLECharacteristic* pTxCharacteristic = NULL;

bool deviceConnected = false;
bool oldDeviceConnected = false;

// Non-blocking timers
unsigned long lastHeartbeatTime = 0;
const unsigned long HEARTBEAT_INTERVAL = 5000;

// Button debounce
bool lastButtonState = HIGH;
bool currentButtonState = HIGH;
unsigned long lastDebounceTime = 0;
const unsigned long DEBOUNCE_DELAY = 50;

class MyServerCallbacks: public BLEServerCallbacks {
    void onConnect(BLEServer* pServer) {
      deviceConnected = true;
    }

    void onDisconnect(BLEServer* pServer) {
      deviceConnected = false;
    }
};

class MyTxCallbacks : public BLECharacteristicCallbacks {

    void onWrite(BLECharacteristic *pCharacteristic) {

        auto rxValue = pCharacteristic->getValue();

        Serial.print("Received Value: ");
        Serial.println(rxValue);

    }

};

void setup() {
  Serial.begin(115200);
  pinMode(BUTTON_PIN, INPUT_PULLUP);

  Serial.println("Starting Diya Cane BLE Server...");
  
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
  Serial.println("Advertising started.");
}

void loop() {
  unsigned long currentMillis = millis();

  // Connection management
  if (deviceConnected) {
    if (!oldDeviceConnected) {
      // Just connected: Send Hello
      delay(500); // Give the client a moment to subscribe to notifications
      String helloMsg = "{\"v\":1,\"t\":\"hello\",\"protocol\":1,\"firmware\":\"1.0.0\"}";
      pRxCharacteristic->setValue(helloMsg.c_str());
      pRxCharacteristic->notify();
      Serial.println("Sent handshake: " + helloMsg);
      
      oldDeviceConnected = deviceConnected;
      lastHeartbeatTime = currentMillis; // Reset heartbeat timer
    }

    // Heartbeat
    if (currentMillis - lastHeartbeatTime >= HEARTBEAT_INTERVAL) {
      lastHeartbeatTime = currentMillis;
      String hbMsg = "{\"v\":1,\"t\":\"heartbeat\"}";
      pRxCharacteristic->setValue(hbMsg.c_str());
      pRxCharacteristic->notify();
    }

    // Button handling
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
           Serial.println("Button pressed: " + btnMsg);
        }
      }
    }
    lastButtonState = reading;
  }

  // Disconnecting
  if (!deviceConnected && oldDeviceConnected) {
      delay(500); // Give the bluetooth stack a chance to cleanup
      pServer->startAdvertising(); // restart advertising
      Serial.println("Device disconnected. Restarting advertising...");
      oldDeviceConnected = deviceConnected;
  }
}
