"""
Integrated Python control script for:
- Reading IMU triggers from Arduino Uno
- Controlling Hasomed P24 stimulator instead of relay-based TENS
- Logging all events (IMU, Carbonhand, P24) to CSV
- Allowing keyboard-based live tuning of stimulation parameters

Author: Alisa Spurgeon
Date: 9/25/25

Requirements:
- Python 3.8+
- pyserial
- ScienceMode4Python (https://github.com/spurgeah/ScienceMode4Python)
- keyboard
"""

# We import modules (libraries) that provide useful functions.
# asyncio: run asynchronous tasks (things that can run 'concurrently')
# serial: talk to devices over serial/COM ports (Arduino/P24)
# csv, os, threading, keyboard, time, datetime: helper libraries for logging and user input
import asyncio
import serial
import csv
import os
import threading
import keyboard
import time
from datetime import datetime
# Import classes from the science_mode_4 package which wrap the P24 device
from science_mode_4 import DeviceP24, MidLevelChannelConfiguration, ChannelPoint, SerialPortConnection

# ----------------- USER CONFIGURATION -----------------
# Here the user sets the names of COM ports and baud rates.
P24_PORT = "COM4"     # Which serial port the P24 device is on
ARDUINO_PORT = "COM6" # Which serial port the Arduino is on
ARDUINO_BAUD = 9600    # Communication speed for the Arduino
P24_BAUD = 9600        # Communication speed for the P24 device

# ----------------- STIMULATION PARAMETERS -----------------
# Default stimulation values; these control amplitude, frequency, and pulse width
STIM_PARAMS = {
    "amp": 10,     # amplitude in milliamps
    "freq": 35,    # frequency in Hertz
    "pw": 300      # pulse width in microseconds
}

# Safety limits for the stimulator to avoid dangerous settings
AMP_MAX = 120
FREQ_MAX = 2000
PW_MAX = 10000

# How much each keyboard press changes the value
DELTA_AMP = 0.5
DELTA_FREQ = 5
DELTA_PW = 10

# CSV logging setup: creates a csv file to record timestamps and events
CSV_DIR = "csv_files"
os.makedirs(CSV_DIR, exist_ok=True)
csv_filename = os.path.join(CSV_DIR, f"log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")

# ----------------- HELPERS -----------------
# Flag to stop the program when user presses Enter
stop_program = False

def listen_for_input():
    """This function waits for the user to press Enter and then sets a flag to stop the program."""
    global stop_program
    input("Press Enter to stop...\n")
    stop_program = True

# log_event saves a row in the CSV file and prints a simple message.
def log_event(source, event, details=""):
    with open(csv_filename, mode="a", newline="") as f:
        writer = csv.writer(f)
        # Save a line: timestamp, where the event came from, short event name, and details
        writer.writerow([datetime.now().isoformat(), source, event, details])
    # Print so the user sees live feedback
    print(f"[LOG] {source} - {event} {details}")

# build_stim_config prepares the waveform commands the P24 understands.
# It reads the global STIM_PARAMS and returns a configuration object.
def build_stim_config():
    amp = int(STIM_PARAMS["amp"])   # convert amplitude to integer
    pw = int(STIM_PARAMS["pw"])     # pulse width to integer
    freq = int(STIM_PARAMS["freq"]) # frequency to integer

    # Create three points that represent one stimulation cycle for a single channel.
    c1_points = [
        ChannelPoint(pw // 2, amp),  # positive pulse
        ChannelPoint(pw // 2, 0),    # zero in-between
        ChannelPoint(pw // 2, -amp)  # negative pulse
    ]
    # Return a list (for one channel); the P24 expects a list of channel configs
    return [MidLevelChannelConfiguration(True, 3, freq, c1_points)]

# stimulation_loop runs while the stim is active. It keeps sending the config at ~50Hz
# so the stim remains on and parameters can be adjusted live.
async def stimulation_loop(mid_level, active_event):
    while active_event.is_set():
        configs = build_stim_config()
        # send the commands to the P24 (this is the part that actually stimulates)
        await mid_level.update(configs)
        # pause a little to avoid flooding the device; 0.02s ~= 50 updates per second
        await asyncio.sleep(.02)

# Keyboard listeners change STIM_PARAMS in small steps when keys are pressed.
# Each listener runs in its own thread so they don't block the main loop.

def listen_for_amp():
    while not stop_program:
        if keyboard.is_pressed("w"):
            STIM_PARAMS["amp"] = min(AMP_MAX, STIM_PARAMS["amp"] + DELTA_AMP)
            log_event("Keyboard", "AMP UP", f"{STIM_PARAMS['amp']} mA")
            time.sleep(0.2)
        elif keyboard.is_pressed("q"):
            STIM_PARAMS["amp"] = max(0.1, STIM_PARAMS["amp"] - DELTA_AMP)
            log_event("Keyboard", "AMP DOWN", f"{STIM_PARAMS['amp']} mA")
            time.sleep(0.2)

# (similar for frequency and pulse width)

def listen_for_freq():
    while not stop_program:
        if keyboard.is_pressed("s"):
            STIM_PARAMS["freq"] = min(FREQ_MAX, STIM_PARAMS["freq"] + DELTA_FREQ)
            log_event("Keyboard", "FREQ UP", f"{STIM_PARAMS['freq']} Hz")
            time.sleep(0.2)
        elif keyboard.is_pressed("a"):
            STIM_PARAMS["freq"] = max(1, STIM_PARAMS["freq"] - DELTA_FREQ)
            log_event("Keyboard", "FREQ DOWN", f"{STIM_PARAMS['freq']} Hz")
            time.sleep(0.2)


def listen_for_pw():
    while not stop_program:
        if keyboard.is_pressed("x"):
            STIM_PARAMS["pw"] = min(PW_MAX, STIM_PARAMS["pw"] + DELTA_PW)
            log_event("Keyboard", "PW UP", f"{STIM_PARAMS['pw']} µs")
            time.sleep(0.2)
        elif keyboard.is_pressed("z"):
            STIM_PARAMS["pw"] = max(1, STIM_PARAMS["pw"] - DELTA_PW)
            log_event("Keyboard", "PW DOWN", f"{STIM_PARAMS['pw']} µs")
            time.sleep(0.2)

# ----------------- MAIN -----------------
async def main():
    global stop_program

    # Create/overwrite the CSV and add a header line
    with open(csv_filename, mode="w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Timestamp", "Source", "Event", "Details"])

    # Connect to the Arduino over the serial port using the specified baud rate
    print(f"Connecting to Arduino on {ARDUINO_PORT}...")
    arduino = serial.Serial(ARDUINO_PORT, ARDUINO_BAUD, timeout=1)
    # Tell the Arduino to enter "RUN" mode so its loop() will actively report IMU
    # and respond to commands. This requires small firmware support on the Arduino
    # (see the snippet at the bottom of this file). We send a newline-terminated
    # ASCII command so the Arduino can read it with Serial.readStringUntil('\n').
    try:
        arduino.write(b"RUN\n")
        # Small pause to ensure the command is transmitted before we proceed
        time.sleep(0.05)
        log_event("Arduino", "CMD", "RUN sent")
    except Exception as e:
        # If the serial write fails, record it but continue — the rest of the
        # program may still work if Arduino is already in RUN mode.
        print(f"Warning: failed to send RUN to Arduino: {e}")

    # Connect to the P24 device using the SerialPortConnection wrapper
    print(f"Connecting to P24 stimulator on {P24_PORT}...")
    try:
        connection = SerialPortConnection(P24_PORT, baudrate=P24_BAUD)
    except TypeError:
        # If the local version doesn't accept baudrate, create without it and try to set it
        connection = SerialPortConnection(P24_PORT)
        try:
            ser_obj = getattr(connection, "_ser", None) or getattr(connection, "ser", None)
            if ser_obj is not None:
                ser_obj.baudrate = P24_BAUD
                print(f"P24 baud fallback: set underlying serial baud to {ser_obj.baudrate}")
            else:
                print("P24 baud fallback: underlying serial object not found; using default baud")
        except Exception as e:
            print(f"P24 baud fallback: failed to set baud on underlying serial object: {e}")
    connection.open()

    # Print which baud is in use; helpful to confirm the connection is using the intended speed
    try:
        actual_baud = getattr(connection, "_ser", None)
        if actual_baud is not None:
            actual_baud = actual_baud.baudrate
        else:
            actual_baud = P24_BAUD
    except Exception:
        actual_baud = P24_BAUD
    print(f"P24 connection opened on {P24_PORT} @ {actual_baud} baud")

    # Initialize the P24 device so it's ready for commands
    device = DeviceP24(connection)
    await device.initialize()
    mid_level = device.get_layer_mid_level()
    await mid_level.init(do_stop_on_all_errors=True)
    print("P24 ready.")

    # Start background threads to listen for keyboard input
    threading.Thread(target=listen_for_input, daemon=True).start()
    threading.Thread(target=listen_for_amp, daemon=True).start()
    threading.Thread(target=listen_for_freq, daemon=True).start()
    threading.Thread(target=listen_for_pw, daemon=True).start()

    # This event is used to signal when FES should be active
    fes_active = asyncio.Event()

    try:
        while not stop_program:
            # If there is data from Arduino, read a line
            if arduino.in_waiting:
                raw = arduino.readline()
                try:
                    line = raw.decode().strip()
                except Exception:
                    line = raw.decode('latin1').strip()

                if not line:
                    continue

                # If the Arduino sent IMU data like: IMU,ax,ay,az, log the position
                if line.startswith("IMU,"):
                    parts = line.split(",")
                    if len(parts) >= 4:
                        ax, ay, az = parts[1], parts[2], parts[3]
                        log_event("IMU", "Position", f"AX={ax} AY={ay} AZ={az}")
                    else:
                        log_event("Arduino", "Malformed IMU", line)

                # If Arduino says FES ON or FES OFF, start/stop stimulation accordingly
                elif line == "FES ON":
                    if not fes_active.is_set():
                        fes_active.set()
                        asyncio.create_task(stimulation_loop(mid_level, fes_active))
                        log_event("P24", "Stimulation STARTED", "trigger=arduino")
                elif line == "FES OFF":
                    if fes_active.is_set():
                        fes_active.clear()
                        await mid_level.stop()
                        log_event("P24", "Stimulation STOPPED", "trigger=arduino")

                # If Arduino reports CH ON/OFF, we log that (the Arduino pulses the relay itself)
                elif line.startswith("CH") or line in ("CH ON", "CH OFF"):
                    log_event("Carbonhand", "State", line)

                else:
                    # Any other message is logged under Arduino
                    log_event("Arduino", "Message", line)

            # Small sleep so this loop doesn't run full-speed and use all CPU
            await asyncio.sleep(0.05)

    except KeyboardInterrupt:
        # If user presses Ctrl+C, shut down nicely
        print("Exiting program...")
        stop_program = True
        fes_active.clear()
        await mid_level.stop()
        # Tell Arduino to pause its active loop and turn off hardware so nothing
        # continues running after Python exits. We send PAUSE, FES OFF, CH OFF.
        try:
            arduino.write(b"PAUSE\n")
            time.sleep(0.02)
            arduino.write(b"FES OFF\n")
            time.sleep(0.02)
            arduino.write(b"CH OFF\n")
            time.sleep(0.02)
            log_event("Arduino", "CMD", "PAUSE,FES OFF,CH OFF sent")
        except Exception as e:
            print(f"Warning: failed to send shutdown commands to Arduino: {e}")
        connection.close()
        arduino.close()
        log_event("System", "Shutdown")

# Run the main function and show any exception if it happens
try:
    asyncio.run(main())
except Exception:
    import traceback
    traceback.print_exc()
    raise

# ----------------- Arduino firmware note -----------------
# The Arduino sketch must be updated to listen for these simple ASCII commands
# from the PC. Add code like this to the top of loop() or in a helper function:
#
#   if (Serial.available()) {
#     String cmd = Serial.readStringUntil('\n');
#     cmd.trim();
#     if (cmd == "RUN") {
#       // enter active reporting/trigger mode
#       runMode = true;  // a boolean you add to gate your IMU reporting
#     } else if (cmd == "PAUSE") {
#       runMode = false; // stop sending IMU data and responding to tilts
#     } else if (cmd == "FES OFF") {
#       fesState = false; // ensure FES indicator and any relay are OFF
#       digitalWrite(fesLedPin, LOW);
#     } else if (cmd == "CH OFF") {
#       chState = false; // ensure CH indicator is OFF
#       digitalWrite(chLedPin, LOW);
#       digitalWrite(chRelayPin, HIGH); // set relay inactive (active-low)
#     }
#
# Make sure these variables (runMode, fesState, chState) are declared globally
# and that your existing tilt logic only acts when runMode == true. This ensures
# that once the Python program stops and sends PAUSE, the Arduino will stop
# toggling stimulation and only resume when the PC sends RUN again.
