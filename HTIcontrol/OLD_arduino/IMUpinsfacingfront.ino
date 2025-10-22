// Viha's code for Arduino control Only
// CH and TENS plugged into relay


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

bool fesState = false; //Is FES ON or OFF?
bool chState = false;  //Is CH ON or OFF?

bool waitingForRightRelease = false;  // Prevents retrigger until head returns to center
bool waitingForLeftRelease = false;// After FES/CH is turned ON or OFF, this becomes true, it only 
                                   // turns to false when head returns to neautral, so one tilt=one action

unsigned long rightTiltStart = 0;  // Records when right tilt starts and if it has been held long enough
unsigned long leftTiltStart = 0; // = 0 means no tilt has started yet, later in the code we check if it has lasted long enoug


void setup() {
  Serial.begin(9600);
  Wire.begin();
  mpu.initialize();

  pinMode(fesRelayPin, OUTPUT);
  pinMode(chRelayPin, OUTPUT);
  pinMode(fesLedPin, OUTPUT);
  pinMode(chLedPin, OUTPUT);
  pinMode(resetButtonPin, INPUT_PULLUP);  // uses internal pull-up resistor

  digitalWrite(fesRelayPin, LOW);
  digitalWrite(fesLedPin, LOW);
  digitalWrite(chRelayPin, HIGH);  // 
  digitalWrite(chLedPin, LOW);

  if (!mpu.testConnection()) {
    Serial.println("MPU6050 connection failed!");
    while (1);
  } else {
    Serial.println("MPU6050 connected.");
  }
}

void loop() {
  // ----------- RESET BUTTON LOGIC -----------
  if (digitalRead(resetButtonPin) == LOW) { // Turn everything off and reset all variables
    // Turn off FES 
    fesState = false;
    digitalWrite(fesRelayPin, LOW);
    digitalWrite(fesLedPin, LOW);

    // If CH is currently locked, send a pulse to unlock it
    if (chState == true) {
      digitalWrite(chRelayPin, LOW);   // Pulse to unlock
      delay(500);
      digitalWrite(chRelayPin, HIGH);
      Serial.println("CH manually unlocked via reset button");
    }

    chState = false;
    digitalWrite(chLedPin, LOW);       // Turn off LED

    // Reset flags
    waitingForRightRelease = false;
    waitingForLeftRelease = false;
    rightTiltStart = 0;
    leftTiltStart = 0;

    Serial.println("System RESET via button");
    delay(500);  // debounce
  }

  // ----------- READ IMU -----------
  int16_t ax, ay, az;       //Reads 3-axis acceleration values MPU6050, ay/y-axis is used to detect left/right head tilts
  mpu.getAcceleration(&ax, &ay, &az);

  if (ax == 0 && ay == 0 && az == 0) {  // if all values = 0, sensor has disconnected or failed, therefore reinitialize 
    Serial.println("IMU unresponsive. Reinitializing...");
    mpu.initialize();
    delay(100);
    return;
  }

  Serial.print("AY: "); // prints out real time y-axis values in Serial Monitor 
  Serial.println(ay);

  // ----------- FES CONTROL (Tilt Right) -----------
  if (ay < rightTiltThreshold && !waitingForRightRelease) { //if both statements = true, the timing for how long the tilt is held starts
    if (rightTiltStart == 0) rightTiltStart = millis(); // millis - acts like a stopwatch

    if (millis() - rightTiltStart >= holdTime) {
      fesState = !fesState;   // toggle FES state
      digitalWrite(fesRelayPin, fesState ? HIGH : LOW);
      digitalWrite(fesLedPin, fesState ? HIGH : LOW);
      Serial.println(fesState ? "FES ON" : "FES OFF");

      waitingForRightRelease = true; // to prevent retriggering
      rightTiltStart = 0;
      delay(500);
    }
  } else if (ay > rightTiltThreshold + 2000) { // when head returns to neautral - reset flag to allow future toggles 
    rightTiltStart = 0;
    waitingForRightRelease = false;
  }

  // ----------- CARBONHAND PULSE CONTROL (Tilt Left) -----------
  if (ay > leftTiltThreshold && !waitingForLeftRelease) {
    if (leftTiltStart == 0) leftTiltStart = millis();

    if (millis() - leftTiltStart >= holdTime) {
      chState = !chState;
      digitalWrite(chLedPin, chState ? HIGH : LOW);
      Serial.println(chState ? "CH LOCK ON" : "CH LOCK OFF");

// Relay pulse to simulate button press
      digitalWrite(chRelayPin, LOW);  // ON (active-low)
      delay(500);                     // Hold 0.5 sec
      digitalWrite(chRelayPin, HIGH); // OFF

      waitingForLeftRelease = true;
      leftTiltStart = 0;
      delay(500);
    }
  } else if (ay < leftTiltThreshold - 2000) {
    leftTiltStart = 0;
    waitingForLeftRelease = false;
  }

  delay(100); // loop delay
}

