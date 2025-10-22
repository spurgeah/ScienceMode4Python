// Viha's code for Arduino control Only — VERBOSE DEBUG VERSION
// Every step, IMU reading, and state change is printed to Serial Monitor.

#include <Wire.h>
#include <MPU6050.h>

MPU6050 mpu;

// Pin definitions
const int fesRelayPin = 7;
const int chRelayPin = 6;
const int fesLedPin = 9;    // Green LED
const int chLedPin = 10;    // Blue LED
const int resetButtonPin = 2;  // Reset button input

// Thresholds & Timers 
const int rightTiltThreshold = -13000;   // Right tilt (negative AY) triggers FES
const int leftTiltThreshold = 3000;      // Left tilt (positive AY) triggers CH
const unsigned long holdTime = 2000;     // 2 seconds hold time, time (ms) the head must stay tilted

bool fesState = false; 
bool chState = false;  

bool waitingForRightRelease = false;  
bool waitingForLeftRelease = false;

unsigned long tiltStartTime = 0;

void setup() {
  Serial.begin(115200);
  Serial.println(F("\n=============================="));
  Serial.println(F("[INIT] Starting IMU + FES/CH Control System"));
  Serial.println(F("=============================="));

  Wire.begin();
  mpu.initialize();

  if (mpu.testConnection()) {
    Serial.println(F("[INIT] MPU6050 connected successfully."));
  } else {
    Serial.println(F("[ERROR] MPU6050 connection failed! Check wiring."));
  }

  pinMode(fesRelayPin, OUTPUT);
  pinMode(chRelayPin, OUTPUT);
  pinMode(fesLedPin, OUTPUT);
  pinMode(chLedPin, OUTPUT);
  pinMode(resetButtonPin, INPUT_PULLUP);

  digitalWrite(fesRelayPin, LOW);
  digitalWrite(chRelayPin, LOW);
  digitalWrite(fesLedPin, LOW);
  digitalWrite(chLedPin, LOW);

  Serial.println(F("[INIT] All pins set. System ready.\n"));
}

void loop() {
  int16_t ax, ay, az;
  mpu.getAcceleration(&ax, &ay, &az);

  // Print IMU readings
  Serial.print(F("[IMU] AX=")); Serial.print(ax);
  Serial.print(F("  AY=")); Serial.print(ay);
  Serial.print(F("  AZ=")); Serial.println(az);

  unsigned long currentTime = millis();

  // Reset button
  if (digitalRead(resetButtonPin) == LOW) {
    Serial.println(F("[INPUT] Reset button pressed — resetting states."));
    resetSystem();
    delay(500);
  }

  // Detect right tilt (FES)
  if (ay < rightTiltThreshold && !fesState && !waitingForRightRelease) {
    if (tiltStartTime == 0) {
      tiltStartTime = currentTime;
      Serial.println(F("[STATE] Right tilt detected — starting FES hold timer."));
    }
    if (currentTime - tiltStartTime >= holdTime) {
      Serial.println(F("[ACTION] FES Activated → Relay ON, LED ON"));
      digitalWrite(fesRelayPin, HIGH);
      digitalWrite(fesLedPin, HIGH);
      fesState = true;
      waitingForRightRelease = true;
      tiltStartTime = 0;
    } else {
      Serial.print(F("[TIMER] Holding right tilt: "));
      Serial.print(currentTime - tiltStartTime);
      Serial.print(F(" / "));
      Serial.print(holdTime);
      Serial.println(F(" ms"));
    }
  } 
  else if (ay > rightTiltThreshold && waitingForRightRelease) {
    Serial.println(F("[STATE] Right tilt released → ready for next detection."));
    waitingForRightRelease = false;
    if (fesState) {
      Serial.println(F("[ACTION] FES Deactivated → Relay OFF, LED OFF"));
      digitalWrite(fesRelayPin, LOW);
      digitalWrite(fesLedPin, LOW);
      fesState = false;
    }
  } 
  else if (ay > rightTiltThreshold && tiltStartTime != 0) {
    // User returned to center before hold time elapsed
    Serial.println(F("[INFO] Right tilt cancelled — head returned to center too soon."));
    tiltStartTime = 0;
  }

  // Detect left tilt (CH)
  if (ay > leftTiltThreshold && !chState && !waitingForLeftRelease) {
    if (tiltStartTime == 0) {
      tiltStartTime = currentTime;
      Serial.println(F("[STATE] Left tilt detected — starting CH hold timer."));
    }
    if (currentTime - tiltStartTime >= holdTime) {
      Serial.println(F("[ACTION] CH Activated → Relay ON, LED ON"));
      digitalWrite(chRelayPin, HIGH);
      digitalWrite(chLedPin, HIGH);
      chState = true;
      waitingForLeftRelease = true;
      tiltStartTime = 0;
    } else {
      Serial.print(F("[TIMER] Holding left tilt: "));
      Serial.print(currentTime - tiltStartTime);
      Serial.print(F(" / "));
      Serial.print(holdTime);
      Serial.println(F(" ms"));
    }
  } 
  else if (ay < leftTiltThreshold && waitingForLeftRelease) {
    Serial.println(F("[STATE] Left tilt released → ready for next detection."));
    waitingForLeftRelease = false;
    if (chState) {
      Serial.println(F("[ACTION] CH Deactivated → Relay OFF, LED OFF"));
      digitalWrite(chRelayPin, LOW);
      digitalWrite(chLedPin, LOW);
      chState = false;
    }
  } 
  else if (ay < leftTiltThreshold && tiltStartTime != 0) {
    Serial.println(F("[INFO] Left tilt cancelled — head returned to center too soon."));
    tiltStartTime = 0;
  }

  delay(100);  // Slow loop for readability (10Hz)
}

void resetSystem() {
  fesState = false;
  chState = false;
  waitingForRightRelease = false;
  waitingForLeftRelease = false;
  tiltStartTime = 0;

  digitalWrite(fesRelayPin, LOW);
  digitalWrite(chRelayPin, LOW);
  digitalWrite(fesLedPin, LOW);
  digitalWrite(chLedPin, LOW);

  Serial.println(F("[RESET] All outputs off, system returned to neutral.\n"));
}
