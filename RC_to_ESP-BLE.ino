/***********************************************************************
 * Official ESP32 BLE Arduino + MCP4728 Example 
 * (Roll, Pitch, Yaw, Throttle = R-P-Y-T order)
 * 
 * 1. This code creates a BLE server with a single service and characteristic.
 * 2. A BLE client can connect, discover the service & characteristic, and write 6 bytes:
 *    [roll, pitch, yaw, throttle, extra1, extra2] (each 0..255).
 * 3. We map the first 4 bytes (R, P, Y, T) into 12-bit values (0..4095)
 *    and update the MCP4728 channels in the same R-P-Y-T order.
 * 4. If we haven’t received new data for 2 seconds, we read analog pins (A0..A3)
 *    in R-P-Y-T order and update the MCP4728 from those values.
 * 
 * Make sure you have:
 *   - ESP32 BLE Arduino library (usually bundled with Arduino-ESP32).
 *   - Adafruit MCP4728 library.
 *   - A board that truly supports BLE with the official library. 


 need to add condition that if analogRead is not 0 -> then listen only to the analogRead, 
 otherwise - listen to the bluetooth device (as long as values remain 0)
 after this - add analogWrite to the RC - consistently sending the sticks command (just prioritize
 who we want to listen to)
 ***********************************************************************/

#include <Arduino.h>
#include <Wire.h>
#include <Adafruit_MCP4728.h>

// Official ESP32 BLE includes
#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEUtils.h>
#include <BLE2902.h>

// MCP4728 object
Adafruit_MCP4728 mcp;

// Define your analog pins for R, P, Y, T (verify these exist on your board)
#define ROLL_PIN   A0
#define PITCH_PIN  A1
#define YAW_PIN    A2
#define THROTTLE_PIN A3

// BLE UUIDs (random example)
#define SERVICE_UUID        "12345678-1234-1234-1234-123456789abc"
#define CHARACTERISTIC_UUID "87654321-4321-4321-4321-cba987654321"

static bool gotRecentWrite = false;
static unsigned long lastWriteMillis = 0;
static const unsigned long TIMEOUT_MS = 2000; // fallback if no BLE write for 2 sec

// Store previous BLE values to detect changes
static uint8_t prevRol = 255;
static uint8_t prevPit = 255;
static uint8_t prevYaw = 255;
static uint8_t prevThr = 255;

/***********************************************************************
 * readAnalogAndSetDAC()
 * Reads from analog pins in R-P-Y-T order, sets the MCP4728 in same order.
 ***********************************************************************/
void readAnalogAndSetDAC() {
  uint16_t rollVal  = analogRead(ROLL_PIN);
  uint16_t pitchVal = analogRead(PITCH_PIN);
  uint16_t yawVal   = analogRead(YAW_PIN);
  uint16_t thrVal   = analogRead(THROTTLE_PIN);

  // MCP4728 channels: A=Roll, B=Pitch, C=Yaw, D=Throttle
  mcp.setChannelValue(MCP4728_CHANNEL_A, rollVal);
  mcp.setChannelValue(MCP4728_CHANNEL_B, pitchVal);
  mcp.setChannelValue(MCP4728_CHANNEL_C, yawVal);
  mcp.setChannelValue(MCP4728_CHANNEL_D, thrVal);

  // Debug
  Serial.print("Analog => ROL:");
  Serial.print(rollVal);
  Serial.print(", PIT:");
  Serial.print(pitchVal);
  Serial.print(", YAW:");
  Serial.print(yawVal);
  Serial.print(", THR:");
  Serial.println(thrVal);
}

/***********************************************************************
 * handleNewBLEData()
 * Extract the first 4 bytes as R, P, Y, T, map them to 0-4095, and set DAC.
 ***********************************************************************/
void handleNewBLEData(const uint8_t* data, size_t length) {
  if (length < 4) return; // not enough data

  gotRecentWrite = true;
  lastWriteMillis = millis();

  // Extract 8-bit R, P, Y, T
  uint8_t rol_raw = data[0];
  uint8_t pit_raw = data[1];
  uint8_t yaw_raw = data[2];
  uint8_t thr_raw = data[3];

  // If data is same as last time, skip
  if (rol_raw == prevRol &&
      pit_raw == prevPit &&
      yaw_raw == prevYaw &&
      thr_raw == prevThr) {
    return;
  }

  // Map 8-bit -> 12-bit
  uint16_t rol_mapped = map(rol_raw, 0, 255, 0, 4095);
  uint16_t pit_mapped = map(pit_raw, 0, 255, 0, 4095);
  uint16_t yaw_mapped = map(yaw_raw, 0, 255, 0, 4095);
  uint16_t thr_mapped = map(thr_raw, 0, 255, 0, 4095);

  // Set MCP4728 channels (R, P, Y, T)
  mcp.setChannelValue(MCP4728_CHANNEL_A, rol_mapped);
  mcp.setChannelValue(MCP4728_CHANNEL_B, pit_mapped);
  mcp.setChannelValue(MCP4728_CHANNEL_C, yaw_mapped);
  mcp.setChannelValue(MCP4728_CHANNEL_D, thr_mapped);

  // Remember new data
  prevRol = rol_raw;
  prevPit = pit_raw;
  prevYaw = yaw_raw;
  prevThr = thr_raw;

  // Debug
  Serial.print("BLE => ROL:");
  Serial.print(rol_raw);
  Serial.print(", PIT:");
  Serial.print(pit_raw);
  Serial.print(", YAW:");
  Serial.print(yaw_raw);
  Serial.print(", THR:");
  Serial.println(thr_raw);
}

/***********************************************************************
 * A custom callback class derived from the official library
 ***********************************************************************/
class MyCallbacks : public BLECharacteristicCallbacks {
  void onWrite(BLECharacteristic* pCharacteristic) {
    String rxData = pCharacteristic->getValue();
    if (rxData.length() >= 6) {
      const uint8_t* data = (const uint8_t*) rxData.c_str();
      size_t length = rxData.length();
      handleNewBLEData(data, length);
    }
  }
};

/***********************************************************************
 * setup()
 ***********************************************************************/
void setup() {
  Serial.begin(115200);
  while (!Serial) {
    delay(10);
  }
  Serial.println("ESP32 Official BLE + MCP4728 (RPYT) Example");

  // Initialize MCP4728
  if (!mcp.begin()) {
    Serial.println("Failed to find MCP4728 chip!");
    while (true) {
      delay(100);
    }
  }
  Serial.println("MCP4728 initialized.");

  // Configure analog inputs
  pinMode(ROLL_PIN, INPUT);
  pinMode(PITCH_PIN, INPUT);
  pinMode(YAW_PIN, INPUT);
  pinMode(THROTTLE_PIN, INPUT);

  // Default to analog
  readAnalogAndSetDAC();

  // Initialize BLE
  BLEDevice::init("XIAO_S3_MCP4728_RPYT"); // or your board name

  BLEServer* pServer = BLEDevice::createServer();
  // If you want to handle connection events, you can set server callbacks
  // pServer->setCallbacks(...);

  // Create the BLE Service
  BLEService* pService = pServer->createService(SERVICE_UUID);

  // Create the BLE Characteristic: READ/WRITE
  BLECharacteristic* pCharacteristic = pService->createCharacteristic(
      CHARACTERISTIC_UUID,
      BLECharacteristic::PROPERTY_READ | BLECharacteristic::PROPERTY_WRITE
  );

  // Set our custom callback
  pCharacteristic->setCallbacks(new MyCallbacks());

  // You can add a 2902 descriptor if needed for notifications
  // pCharacteristic->addDescriptor(new BLE2902());

  // Start the Service
  pService->start();

  // Start advertising
  BLEAdvertising* pAdvertising = pServer->getAdvertising();
  pAdvertising->addServiceUUID(SERVICE_UUID);
  pAdvertising->start();

  Serial.println("BLE advertising started...");
}

/***********************************************************************
 * loop()
 ***********************************************************************/
void loop() {
  // If we haven't seen a BLE write for 2 seconds, or never got one:
  if (!gotRecentWrite || (millis() - lastWriteMillis) > TIMEOUT_MS) {
    // Fallback to reading analog pins
    readAnalogAndSetDAC();
  }

  delay(50);
}
