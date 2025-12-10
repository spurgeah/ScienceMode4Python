/*
Fixed Arduino sketch that respects runMode and reduces debounce delays.
Created by assistant to replace HTIcontrol/hti_arduino.ino for testing.
*/

#include <Wire.h>
#include <MPU6050.h>
MPU6050 mpu;

// Pin definitions
const int fesLedPin = 9;   // Green LED for FES state
const int chLedPin = 10;   // Blue LED for Carbonhand state
const int chRelayPin = 6;  // relay pin (if present)
const int resetButtonPin = 2;

const int rightTiltThreshold = -13000; // Right tilt triggers FES
const int leftTiltThreshold  = 3000;   // Left tilt triggers Carbonhand
const unsigned long holdTime = 2000; // Hold time in milliseconds

bool fesState = false; // FES state is OFF
bool chState = false; // Carbonhand state is OFF
bool waitingForRightRelease = false; // To prevent multiple toggles
bool waitingForLeftRelease = false;
unsigned long rightTiltStart = 0; // Time when right tilt started
unsigned long leftTiltStart = 0;
bool runMode = false; // When true: process IMU and toggles. When false: stay idle but accept serial commands.

void setup() {
  Serial.begin(9600); // Start serial communication at 9600 baud
  Wire.begin();
  mpu.initialize();

  pinMode(fesLedPin, OUTPUT);
  pinMode(chLedPin, OUTPUT);
  pinMode(chRelayPin, OUTPUT);
  pinMode(resetButtonPin, INPUT_PULLUP);

  digitalWrite(fesLedPin, LOW);
  digitalWrite(chLedPin, LOW);
  digitalWrite(chRelayPin, LOW);

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
    digitalWrite(chRelayPin, LOW);
    Serial.println("RESET");
    delay(500);
  }

  // Always process serial commands first so Python can control runMode even when paused
  if (Serial.available()) {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim();
    if (cmd == "RUN") {
      runMode = true;
      Serial.println("ACK RUN");
    } else if (cmd == "PAUSE") {
      runMode = false;
      // ensure hardware off when pausing
      fesState = false;
      chState = false;
      digitalWrite(fesLedPin, LOW);
      digitalWrite(chLedPin, LOW);
      digitalWrite(chRelayPin, LOW);
      Serial.println("ACK PAUSE");
    } else if (cmd == "FES OFF") {
      fesState = false;
      digitalWrite(fesLedPin, LOW);
      Serial.println("ACK FES OFF");
    } else if (cmd == "CH OFF" || cmd == "CH LOCK OFF") {
      chState = false;
      digitalWrite(chLedPin, LOW);
      digitalWrite(chRelayPin, LOW);
      Serial.println("ACK CH OFF");
    }
  }

  // If not in run mode, don't read/process IMU or trigger hardware; return early
  if (!runMode) {
    delay(100);
    return;
  }

  // Read IMU
  int16_t ax, ay, az;
  mpu.getAcceleration(&ax, &ay, &az);

  // Send raw IMU values every loop
  //Serial.print("IMU,");
  //Serial.print(ax);
  //Serial.print(",");
  //Serial.print(ay);
  //Serial.print(",");
  //Serial.println(az);

  if (ax == 0 && ay == 0 && az == 0) {
    mpu.initialize();
    delay(100);
    return;
  }

  // --- FES Control (Tilt Right) ---
  if (ay < rightTiltThreshold && !waitingForRightRelease) {
    if (rightTiltStart == 0) rightTiltStart = millis();
    if (millis() - rightTiltStart >= holdTime) {
      fesState = !fesState;
      digitalWrite(fesLedPin, fesState ? HIGH : LOW);
      Serial.println(fesState ? "FES ON" : "FES OFF");
      waitingForRightRelease = true;
      rightTiltStart = 0;
      delay(200); // shorter debounce to reduce perceived latency
    }
  } else if (ay > rightTiltThreshold + 2000) {
    rightTiltStart = 0;
    waitingForRightRelease = false;
  }

  // --- Carbonhand Control (Tilt Left) ---
  if (ay > leftTiltThreshold && !waitingForLeftRelease) {
    if (leftTiltStart == 0) leftTiltStart = millis();
    if (millis() - leftTiltStart >= holdTime) {
      chState = !chState;
      digitalWrite(chLedPin, chState ? HIGH : LOW);
      Serial.println(chState ? "CH ON" : "CH OFF");
      waitingForLeftRelease = true;
      leftTiltStart = 0;
      // Pulse the relay if present
      digitalWrite(chRelayPin, HIGH);
      delay(200); // shorter pulse
      digitalWrite(chRelayPin, LOW);
    }
  } else if (ay < leftTiltThreshold - 2000) {
    leftTiltStart = 0;
    waitingForLeftRelease = false;
  }

  delay(50);
}
