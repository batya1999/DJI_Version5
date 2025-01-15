#include <BLEDevice.h>
#include <BLEUtils.h>
#include <BLEServer.h>

#define SERVICE_UUID "4fafc201-1fb5-459e-8fcc-c5c9c331914b"
#define CHARACTERISTIC_UUID "beb5483e-36e1-4688-b7f5-ea07361b26a8"

BLEServer* pServer = NULL;
BLECharacteristic* pCharacteristic = NULL;
bool deviceConnected = false;

// Callback to handle connection and disconnection
class MyServerCallbacks : public BLEServerCallbacks {
  void onConnect(BLEServer* pServer) {
    deviceConnected = true;
    Serial.println("Device connected");
  }

  void onDisconnect(BLEServer* pServer) {
    deviceConnected = false;
    Serial.println("Device disconnected");
    // Restart advertising to allow reconnection
    pServer->getAdvertising()->start();
    Serial.println("Advertising restarted");
  }
};

// Callback for the characteristic to detect write events
class MyCharacteristicCallbacks : public BLECharacteristicCallbacks {
void onWrite(BLECharacteristic* pCharacteristic) {
    String value = pCharacteristic->getValue();  // Use String here
    Serial.print("Received value: ");
    Serial.println(value);
}
};

void setup() {
  Serial.begin(115200);

  // Initialize BLE
  BLEDevice::init("ESP32_AlwaysConnected");
  pServer = BLEDevice::createServer();
  pServer->setCallbacks(new MyServerCallbacks());

  // Create BLE service and characteristic
  BLEService* pService = pServer->createService(SERVICE_UUID);
  pCharacteristic = pService->createCharacteristic(
                      CHARACTERISTIC_UUID,
                      BLECharacteristic::PROPERTY_READ |
                      BLECharacteristic::PROPERTY_WRITE
                    );
  pCharacteristic->setValue("Hello from ESP32!");

  // Set the callback for writes to the characteristic
  pCharacteristic->setCallbacks(new MyCharacteristicCallbacks());

  // Start the BLE service
  pService->start();
  Serial.println("BLE Service started");

  // Set connection parameters to optimize connection stability
  pServer->getAdvertising()->setMinPreferred(0x06); // Minimum interval (7.5ms)
  pServer->getAdvertising()->setMaxPreferred(0x12); // Maximum interval (15ms)

  // Set MTU size (increase for stability and faster data transfer)
  BLEDevice::setMTU(500);  // Set Maximum Transmission Unit (MTU) size

  // Start advertising
  pServer->getAdvertising()->start();
  Serial.println("Advertising started. Waiting for a connection...");
}

void loop() {
  if (deviceConnected) {
    // Periodically update the characteristic value to keep the connection active
    String value = "Updated value: " + String(millis()); // Use String instead of std::string
    pCharacteristic->setValue(value); // Set value using String
    Serial.print("Sending value: ");
    Serial.println(value);

    delay(1000);  // Update every second
  } else {
    Serial.println("Waiting for a device to connect...");
    delay(1000);
  }
}