/*
Arduino Sketch for IMU tilt detection and Carbonhand control.
Outputs trigger messages via Serial to Python instead of relays.
Author: Alisa Spurgeon
Date: 9/25/25
*/

#include <Wire.h> 
#include <MPU6050.h>
MPU6050 mpu;

// Pin definitions
const int fesLedPin = 9;   // Green LED for FES state
const int chLedPin = 10;   // Blue LED for Carbonhand state
const int chRelayPin = 6; // plugged into IN2 on relay
const int resetButtonPin = 2;

const int rightTiltThreshold = -13000; // Right tilt triggers FES
  // -7000 to -6500 for S01
const int leftTiltThreshold  = 3000;   // Left tilt triggers Carbonhand
  // 700  for S01, can be increased to reduce false triggers (S01 naturally tilts left)
const unsigned long holdTime = 2000; // Hold time in milliseconds

bool fesState = false; // FES state is OFF
bool chState = false; // Carbonhand state is OFF
bool waitingForRightRelease = false; // To prevent multiple toggles
bool waitingForLeftRelease = false;
unsigned long rightTiltStart = 0; // Time when right tilt started
unsigned long leftTiltStart = 0;

void setup() {
  Serial.begin(9600); // Start serial communication at 9600 baud
  Wire.begin();
  mpu.initialize();

  pinMode(fesLedPin, OUTPUT);
  pinMode(chLedPin, OUTPUT);
  // Ensure relay pin is configured as an output and set inactive state
  pinMode(chRelayPin, OUTPUT);
  // Relay is active-low in this setup, so set HIGH to keep it off initially
  digitalWrite(chRelayPin, HIGH);
  pinMode(resetButtonPin, INPUT_PULLUP);

  digitalWrite(fesLedPin, LOW);
  digitalWrite(chLedPin, LOW);

  if (!mpu.testConnection()) {
    Serial.println("MPU6050 connection failed!");
    while (1);
  } else {
    Serial.println("MPU6050 connected.");
  }
}



void loop() {
  // Reset button
  if (digitalRead(resetButtonPin) == LOW) {
    fesState = false;
    chState = false;
    waitingForRightRelease = false;
    waitingForLeftRelease = false;
    rightTiltStart = 0;
    leftTiltStart = 0;
    digitalWrite(fesLedPin, LOW);
    digitalWrite(chLedPin, LOW);
    Serial.println("RESET");
    delay(500);
  }

  // Read IMU
  int16_t ax, ay, az;
  mpu.getAcceleration(&ax, &ay, &az);

  // Send raw IMU values every loop
  Serial.print("IMU,");
  Serial.print(ax);
  Serial.print(",");
  Serial.print(ay);
  Serial.print(",");
  Serial.println(az);

  if (ax == 0 && ay == 0 && az == 0) {
    mpu.initialize();
    delay(100);
    return;
  }

  // --- FES Control (Tilt Right) ---
  if (ay < rightTiltThreshold && !waitingForRightRelease) {
    if (rightTiltStart == 0) rightTiltStart = millis();
    if (millis() - rightTiltStart >= holdTime) {
      fesState = !fesState;       // toggle FES state
      // digitalWrite(fesLedPin, fesState ? HIGH : LOW);
        // turned off relay switch
      Serial.println(fesState ? "FES ON" : "FES OFF");
      waitingForRightRelease = true;
      rightTiltStart = 0;
      delay(500);
    }
  } else if (ay > rightTiltThreshold + 2000) {
    rightTiltStart = 0;
    waitingForRightRelease = false;
  }

  // --- Carbonhand Control (Tilt Left) ---
  if (ay > leftTiltThreshold && !waitingForLeftRelease) {  //if both statements = true, the timing for how long the tilt is held starts
    if (leftTiltStart == 0) leftTiltStart = millis(); // millis - acts like a stopwatch
    if (millis() - leftTiltStart >= holdTime) {
      chState = !chState;
      digitalWrite(chLedPin, chState ? HIGH : LOW);
      Serial.println(chState ? "CH ON" : "CH OFF");



      // ✅ Pulse the Carbonhand relay, not just LED
      digitalWrite(chRelayPin, LOW); // active-low ON
      delay(500);
      digitalWrite(chRelayPin, HIGH);


      waitingForLeftRelease = true;
      leftTiltStart = 0;
      delay(500);
    }
  } else if (ay < leftTiltThreshold - 2000) {
    leftTiltStart = 0;
    waitingForLeftRelease = false;
  }

  delay(100);
}
// End of Arduino code