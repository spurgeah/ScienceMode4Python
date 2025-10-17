// Ryan's code with relay pin connections
// HTI FES Hand Opening and Closing with Debug Reset Button


// Pin assignments
const int toggleButtonPin = 2;  // Toggle button input pin
const int stopButtonPin = 3;    // Stop button input pin
const int FESOpeningPin = 8;    // FES Opening relay control pin (pin 8)
const int CHRelayPin = 9;       // CH relay control pin (pin 9)
const int FESClosingPin = 10;   // FES Closing relay control pin (pin 10)

// Variables to manage states
enum SystemState { STATE1, STATE2, STOPPED };
SystemState currentState = STATE1;  // Start in State 1

bool lastToggleButtonState = HIGH;
bool currentToggleButtonState = HIGH;
unsigned long lastDebounceTime = 0;
const unsigned long debounceDelay = 50;   // Debounce time (50ms)
const unsigned long FESClosingOnTime = 5000; // FES Closing stays on for 5 seconds
const unsigned long CHOnTime = 1000;         // CH stays on for 1 second
unsigned long stateChangeTime = 0;           // Timestamp for state changes

bool chLocked = false;  // Track if CH is locked
bool systemOff = false; // Track if the system is OFF after reset

void setup() {
  // Initialize pins
  pinMode(toggleButtonPin, INPUT_PULLUP);  // Use internal pull-up for toggle button
  pinMode(stopButtonPin, INPUT_PULLUP);    // Use internal pull-up for stop button
  pinMode(FESOpeningPin, OUTPUT);          // FES Opening relay control pin
  pinMode(CHRelayPin, OUTPUT);             // CH relay control pin
  pinMode(FESClosingPin, OUTPUT);          // FES Closing relay control pin

  Serial.begin(9600); // Initialize serial communication
  Serial.println("Setup complete. Starting in State 1: FES Opening ON.");

  // Start with FES Opening ON (State 1)
  digitalWrite(FESOpeningPin, HIGH); // Relay ON (assuming HIGH activates relay)
  digitalWrite(CHRelayPin, LOW);     // Ensure CH is off
  digitalWrite(FESClosingPin, LOW);  // Ensure FES Closing is off
}

void loop() {
  // Check the toggle button state
  int toggleReading = digitalRead(toggleButtonPin);
  if (toggleReading != lastToggleButtonState) {
    lastDebounceTime = millis();  // Reset debounce timer
  }

  if ((millis() - lastDebounceTime) > debounceDelay) {
    if (toggleReading != currentToggleButtonState) {
      currentToggleButtonState = toggleReading;

      if (currentToggleButtonState == LOW) {  // If button is pressed
        if (systemOff) {
          // If the system is OFF, toggle button returns to State 1
          systemOff = false;
          currentState = STATE1;
          digitalWrite(FESOpeningPin, HIGH); // Turn on FES Opening
          Serial.println("Toggle button pressed. Returning to State 1: FES Opening ON.");
        } else {
          toggleState();  // Switch between State 1 and State 2
        }
      }
    }
  }
  lastToggleButtonState = toggleReading;

  // Check if the stop button is pressed
  if (digitalRead(stopButtonPin) == LOW) {
    stopAllDevices();  // Turn off all devices
  }

  // Handle state-specific timing
  handleStateTiming();
}

// Function to switch between states
void toggleState() {
  if (currentState == STATE1) {
    // Switching from State 1 to State 2
    currentState = STATE2;
    digitalWrite(FESOpeningPin, LOW);      // Turn off FES Opening
    digitalWrite(FESClosingPin, HIGH);     // Turn on FES Closing
    Serial.println("Switched to State 2: FES Closing ON for 5 seconds.");
    stateChangeTime = millis();            // Record the time of state change
  } else if (currentState == STATE2) {
    // Switching from State 2 to State 1
    currentState = STATE1;
    digitalWrite(FESClosingPin, LOW);      // Turn off FES Closing
    digitalWrite(FESOpeningPin, HIGH);     // Turn on FES Opening
    Serial.println("Switched to State 1: FES Opening ON.");
  }
}

// Function to stop all devices
void stopAllDevices() {
  // Turn off FES Opening and FES Closing immediately
  digitalWrite(FESOpeningPin, LOW);
  digitalWrite(FESClosingPin, LOW);

  // Handle CH behavior
  if (chLocked) {
    digitalWrite(CHRelayPin, HIGH);  // Turn on CH for 1 second
    Serial.println("CH locked. Turning ON for 1 second.");
    delay(CHOnTime);                 // Wait for 1 second
    digitalWrite(CHRelayPin, LOW);   // Turn off CH
    Serial.println("CH turned OFF.");
  }

  // Reset system state
  currentState = STATE1;
  chLocked = false;
  systemOff = true;  // System remains OFF until toggle button is pressed
  Serial.println("All devices stopped. System OFF. Press toggle button to return to State 1.");
}

// Function to handle state-specific timing
void handleStateTiming() {
  if (currentState == STATE2) {
    if (millis() - stateChangeTime >= FESClosingOnTime) {
      digitalWrite(FESClosingPin, LOW);  // Turn off FES Closing after 5 seconds
      digitalWrite(CHRelayPin, HIGH);    // Turn on CH
      Serial.println("CH ON for 1 second.");
      stateChangeTime = millis();        // Reset the timer for CH
      chLocked = true;                   // Lock CH
    }

    if (chLocked && (millis() - stateChangeTime >= CHOnTime)) {
      digitalWrite(CHRelayPin, LOW);     // Turn off CH after 1 second
      Serial.println("CH turned OFF and locked.");
    }
  }
}