/*
Arduino Sketch for IMU tilt detection and Carbonhand control.
This annotated version explains every line in plain English for a non-programmer.

Author: Annotated automatically
Based on: sept30_hti_p24.ino
*/

// Include the Wire library for I2C communication (used by the IMU)
#include <Wire.h>
// Include the MPU6050 library to talk to the IMU sensor
#include <MPU6050.h>
// Create an object that represents the IMU so we can call methods on it
MPU6050 mpu;

// Pin definitions - these numbers refer to the Arduino board pins
const int fesLedPin = 9;   // Pin for a green LED that shows FES (on/off)
const int chLedPin = 10;   // Pin for a blue LED that shows Carbonhand state
const int chRelayPin = 6;  // Pin that drives the relay controlling Carbonhand
const int resetButtonPin = 2; // Pin connected to a reset button

// Thresholds and timing (numbers tuned for your IMU readings)
const int rightTiltThreshold = -13000; // If the IMU's Y value goes below this, it counts as a right tilt
const int leftTiltThreshold  = 3000;   // If the IMU's Y value goes above this, it counts as a left tilt
const unsigned long holdTime = 2000;   // How long the tilt must be held (in milliseconds) to trigger

// State variables (remember whether FES / Carbonhand are ON or OFF)
bool fesState = false; // start with FES OFF
bool chState = false;  // start with Carbonhand OFF
bool runMode = true; // Whether the main loop should run (true = run, false = paused)
// Debounce / release flags to avoid toggling multiple times during one tilt
bool waitingForRightRelease = false;
bool waitingForLeftRelease = false;
// Variables to track when a tilt started (millis() gives time in ms since startup)
unsigned long rightTiltStart = 0;
unsigned long leftTiltStart = 0;

// setup() runs once when the Arduino powers up or is reset
void setup() {
  // Start serial communication over USB at 9600 bits per second so Python on the PC can read messages
  Serial.begin(9600);
  // Start the I2C bus used to talk to the IMU
  Wire.begin();
  // Initialize the IMU sensor
  mpu.initialize();

  // Configure the LED pins as outputs so we can turn LEDs on/off
  pinMode(fesLedPin, OUTPUT);
  pinMode(chLedPin, OUTPUT);
  // Configure the relay pin as an output so we can pulse the relay
  pinMode(chRelayPin, OUTPUT);
  // Many relay modules are "active-low" (LOW = on), so keep it HIGH to keep the relay off now
  digitalWrite(chRelayPin, HIGH); // Change to LOW to keep relay off?
  // Configure the reset button pin with an internal pull-up so it reads HIGH normally and LOW when pressed
  pinMode(resetButtonPin, INPUT_PULLUP);

  // Ensure LEDs are off at startup
  digitalWrite(fesLedPin, LOW);
  digitalWrite(chLedPin, LOW);

  // Check that the IMU is responding and inform the PC via Serial
  if (!mpu.testConnection()) {
    Serial.println("MPU6050 connection failed!"); // Tell PC there was a problem
    while (1); // Halt here forever — prevents the sketch from continuing without a sensor
  } else {
    Serial.println("MPU6050 connected."); // Tell PC everything is OK
  }
}

// loop() runs over and over; this is the main program
void loop() {

    // lets arduino read commands from python over serial
  if (Serial.available()) {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim();
    if (cmd == "RUN") {
      // enter active reporting/trigger mode
      runMode = true;  // a boolean you add to gate your IMU reporting
      Serial.println("ACK RUN");
    } else if (cmd == "PAUSE") {
      runMode = false; // stop sending IMU data and responding to tilts
      Serial.println("ACK PAUSE");
    } else if (cmd == "FES OFF") {
      fesState = false; // ensure FES indicator and any relay are OFF
      digitalWrite(fesLedPin, LOW);
      Serial.println("ACK FES OFF");
    } else if (cmd == "CH OFF") {
      chState = false; // ensure CH indicator is OFF
      digitalWrite(chLedPin, LOW);
      digitalWrite(chRelayPin, HIGH); // set relay inactive (active-low)
      Serial.println("ACK CH OFF");
    } 

    } // end of command processing


  // If the reset button is pressed (reads LOW because of INPUT_PULLUP)
  if (digitalRead(resetButtonPin) == LOW) {
    // Clear states and flags so both systems are considered OFF
    fesState = false;
    chState = false;
    waitingForRightRelease = false;
    waitingForLeftRelease = false;
    rightTiltStart = 0;
    leftTiltStart = 0;
    // Turn off the indicator LEDs
    digitalWrite(fesLedPin, LOW);
    digitalWrite(chLedPin, LOW);
    // Inform the PC we reset
    Serial.println("RESET");
    // Short delay so the button press doesn't cause repeated immediate actions
    delay(500);
  }

  if (!runMode) { /* skip */ } // If not in run mode, skip the rest of the loop
    // turns arduino 'off' when python not running
    

  // Read acceleration values from the IMU (ax, ay, az)
  int16_t ax, ay, az;
  mpu.getAcceleration(&ax, &ay, &az);

  // Send the raw IMU values over Serial in a simple CSV format: IMU,ax,ay,az
  Serial.print("IMU,");
  Serial.print(ax);
  Serial.print(",");
  Serial.print(ay);
  Serial.print(",");
  Serial.println(az);

  // If all readings are zero, the IMU might be uninitialized; try to reinitialize and skip this loop
  if (ax == 0 && ay == 0 && az == 0) {
    mpu.initialize();
    delay(100);
    return;
  }


  // --- FES Control (Tilt Right) ---
  // If the AY value is less than the right tilt threshold and we are not waiting for release
  if (ay < rightTiltThreshold && !waitingForRightRelease) {
    // Start timing how long the tilt has been held
    if (rightTiltStart == 0) rightTiltStart = millis();
    // If the tilt has been held for at least holdTime ms, toggle the FES state
    if (millis() - rightTiltStart >= holdTime) {
      fesState = !fesState; // flip ON <-> OFF
      digitalWrite(fesLedPin, fesState ? HIGH : LOW); // Turn the FES LED on or off to show state
      // Inform the PC whether FES is now ON or OFF (Python will act on these messages)
      Serial.println(fesState ? "FES ON" : "FES OFF");
      // Remember to wait for the tilt to be released before allowing another toggle
      waitingForRightRelease = true;
      rightTiltStart = 0;
      delay(500); // delay to prevent immediate retriggering
    }
  } else if (ay > rightTiltThreshold + 2000) {
    // If the IMU returns back toward center (release), clear the timers so we can detect next tilt
    rightTiltStart = 0;
    waitingForRightRelease = false;
  }

  // --- Carbonhand Control (Tilt Left) ---
  // Similar logic for left tilt
  if (ay > leftTiltThreshold && !waitingForLeftRelease) {
    if (leftTiltStart == 0) leftTiltStart = millis();
    if (millis() - leftTiltStart >= holdTime) {
      chState = !chState; // Toggle Carbonhand state
      digitalWrite(chLedPin, chState ? HIGH : LOW); // Turn the CH LED on/off to show state
      // Let the PC know the Carbonhand state changed
      Serial.println(chState ? "CH ON" : "CH OFF");

      // Pulse the relay to physically activate the Carbonhand (active-low relay)
      digitalWrite(chRelayPin, LOW); // Turn relay on
      delay(500);                    // Hold the relay on for 500 ms
      digitalWrite(chRelayPin, HIGH); // Turn relay off

      // Block further toggles until the tilt is released
      waitingForLeftRelease = true;
      leftTiltStart = 0;
      delay(500);
    }
  } else if (ay < leftTiltThreshold - 2000) {
    leftTiltStart = 0;
    waitingForLeftRelease = false;
  }

  // Short delay to limit loop speed and serial traffic
  delay(100);
}
// End of annotated Arduino sketch
