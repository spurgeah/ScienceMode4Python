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

import asyncio
import serial
import csv
import os
import threading
import keyboard
import time
from datetime import datetime
from science_mode_4 import DeviceP24, MidLevelChannelConfiguration, ChannelPoint, SerialPortConnection

# ================== USER SETTINGS ==================
P24_PORT = "COM4"     # P24 COM port - gets plugged in first!!
ARDUINO_PORT = "COM6" # Arduino Uno port
ARDUINO_BAUD = 9600    # Baud rate for Arduino serial
    # Arduino code should be set to 9600 baud
    # baud rate is not critical as long as both sides match
#P24_BAUD = 3000000  # Baud rate for P24 serial
P24_BAUD = 9600  # Baud rate for P24 serial


# Default stimulation parameters
STIM_PARAMS = {
    "amp": 10,     # mA
    "freq": 35,    # Hz
    "pw": 300      # µs
}

# Safety limits
AMP_MAX = 120
FREQ_MAX = 2000
PW_MAX = 10000

# Step sizes for keyboard tuning
DELTA_AMP = 0.5
DELTA_FREQ = 5
DELTA_PW = 10

# CSV Logging setup
CSV_DIR = "csv_files"
os.makedirs(CSV_DIR, exist_ok=True)
csv_filename = os.path.join(CSV_DIR, f"log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
# ===================================================

# Global flags
stop_program = False # Flag to indicate if the stimulation loop should stop
# Listens for Enter key to stop stimulation
def listen_for_input():
    global stop_program
    input("Press Enter to stop...\n")  # Waits for Enter key
    stop_program = True

# log_event saves a row in the CSV file and prints a message --------------
def log_event(source, event, details="", stim_params=""):
    # Use provided stim_params or get current values
    if not stim_params:
        stim_params = f"{STIM_PARAMS['amp']},{STIM_PARAMS['freq']},{STIM_PARAMS['pw']}"
    
    with open(csv_filename, mode="a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([datetime.now().isoformat(), source, event, details, stim_params])
    print(f"[LOG] {source} - {event} {details}")
    

def build_stim_config():
    amp = int(STIM_PARAMS["amp"]) # converts to integer
    pw = int(STIM_PARAMS["pw"])
    freq = int(STIM_PARAMS["freq"])

    c1_points = [
        ChannelPoint(pw // 2, amp), # positive phase
        ChannelPoint(pw // 2, 0),
        ChannelPoint(pw // 2, -amp) # negative phase
    ]
    return [MidLevelChannelConfiguration(True, 3, freq, c1_points)]

async def stimulation_loop(mid_level, active_event):
    # stimulation_loop runs while the stim is active
    # keeps sending the config at ~50Hz
    # so the stim remains on and parameters can be adjusted live.
    last_get = time.monotonic()
    while active_event.is_set():
        configs = build_stim_config()
        # Log what we're sending so we can debug if the P24 doesn't stimulate
        try:
            log_event("P24", "Update", f"configs={configs}")
        except Exception:
            # In case configs aren't trivially printable
            log_event("P24", "Update", "configs prepared")
        try:
            await mid_level.update(configs)
        except Exception as e:
            # If the P24 rejects the command or raises, log it
            log_event("P24", "UpdateError", str(e))

        # Periodically call get_current_data() (example shows ~1.5s) to keep the
        # device's stimulation active and to fetch status. This prevents some
        # devices from stopping stimulation after only a short while.
        now = time.monotonic()
        if now - last_get >= 1.5:
            try:
                _ = await mid_level.get_current_data()
                log_event("P24", "get_current_data", "ok")
            except Exception as e:
                log_event("P24", "get_current_data_error", str(e))
            last_get = now

        await asyncio.sleep(.02) # 50 Hz updates for smooth stim

##Keyboard listener functions
    # change STIM_PARAMS in small steps when keys are pressed.
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

# ----------------- MAIN -------------------------------------------
async def main():
    global stop_program

    # Init CSV header
    with open(csv_filename, mode="w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Timestamp", "Source", "Event", "Details",  "Stim_Amp", "Stim_Freq", "Stim_PW"])

    # Connect Arduino
    print(f"Connecting to Arduino on {ARDUINO_PORT}...")
    arduino = serial.Serial(ARDUINO_PORT, ARDUINO_BAUD, timeout=1)
    # Tell the Arduino to enter "RUN" mode so its loop() will actively report IMU
    # and respond to commands. This requires small firmware support on the Arduino
    # (see the snippet at the bottom of this file). We send a newline-terminated
    # ASCII command so the Arduino can read it with Serial.readStringUntil('\n').
    # CUT ----------------------------------------------------------------------------------------
    try:
        arduino.write(b"RUN\n")
        # Small pause to ensure the command is transmitted before we proceed
        time.sleep(0.05)
        log_event("Arduino", "CMD", "RUN sent")
    except Exception as e:
        # If the serial write fails, record it but continue — the rest of the
        # program may still work if Arduino is already in RUN mode.
        print(f"Warning: failed to send RUN to Arduino: {e}")

    # FIXED: Send UNLOCK command to start in unlocked state
    try:
        arduino.write(b"UNLOCK\n")  # Start unlocked!
        time.sleep(0.05)
        arduino.write(b"RUN\n")
        time.sleep(0.05)
        log_event("Arduino", "CMD", "UNLOCK and RUN sent")
    except Exception as e:
        print(f"Warning: failed to send startup commands to Arduino: {e}")


    # Connect P24
    print(f"Connecting to P24 stimulator on {P24_PORT}...")
    #device, mid_level, connection = await connect_p24()
    # Try to pass baudrate (newer local code supports this). If the
    # installed/older package doesn't accept the keyword, fall back to
    # creating the connection without it and set the underlying serial
    # object's baudrate if possible.
    try:
        p24_serial = SerialPortConnection(P24_PORT, baudrate=P24_BAUD)
    except TypeError:
        p24_serial = SerialPortConnection(P24_PORT)
        try:
            ser_obj = getattr(p24_serial, "_ser", None) or getattr(p24_serial, "ser", None)
            if ser_obj is not None:
                # try setting baudrate on underlying pyserial object
                ser_obj.baudrate = P24_BAUD
                # Log the result to make it obvious what baud is in use
                try:
                    print(f"P24 baud fallback: set underlying serial baud to {ser_obj.baudrate}")
                except Exception:
                    print("P24 baud fallback: set underlying serial baud (value unavailable)")
            else:
                print("P24 baud fallback: underlying serial object not found; using default baud")
        except Exception as e:
            # best-effort; if this fails, we'll still try to open the
            # connection and hope the device uses default baud.
            print(f"P24 baud fallback: failed to set baud on underlying serial object: {e}")
    p24_serial.open() 
    
    # Startup log: show the actual baud the Serial object is using
    try:
        actual_baud = getattr(p24_serial, "_ser", None)
        if actual_baud is not None:
            actual_baud = actual_baud.baudrate
        else:
            actual_baud = P24_BAUD
    except Exception:
        actual_baud = P24_BAUD
    print(f"P24 connection opened on {P24_PORT} @ {actual_baud} baud")
    
    device = DeviceP24(p24_serial)
    await device.initialize()
    mid_level = device.get_layer_mid_level()
    await mid_level.init(do_stop_on_all_errors=True)
    #return device, mid_level, connection
    print("P24 ready.")

    # Start keyboard listeners
    threading.Thread(target=listen_for_input, daemon=True).start()
    threading.Thread(target=listen_for_amp, daemon=True).start()
    threading.Thread(target=listen_for_freq, daemon=True).start()
    threading.Thread(target=listen_for_pw, daemon=True).start()

    # FES active flag
    fes_active = asyncio.Event()

    try:
        while not stop_program:
            if arduino.in_waiting: # checks if data is available from the serial port
                raw = arduino.readline() # Read 1 line of bytes from Arduino

                # If the read timed out, raw will be empty bytes; skip in that case
                if not raw:
                    continue

                # Decode safely: prefer utf-8 but replace undecodable bytes rather than raising
                line = raw.decode('utf-8', errors='replace').strip()

                if not line:
                    continue

                print(f"[Arduino] {line}")
   
                # IMU message: "IMU,ax,ay,az"
                if line.startswith("IMU,"):
                    parts = line.split(",")
                    if len(parts) >= 4:
                        ax, ay, az = parts[1], parts[2], parts[3]
                        log_event("IMU", "Position", f"AX={ax} AY={ay} AZ={az}")
                    else:
                        log_event("Arduino", "Malformed IMU", line)

                # FES control messages from Arduino -> control P24 stimulation
                if line == "FES ON":
                    if not fes_active.is_set():
                        fes_active.set()
                        asyncio.create_task(stimulation_loop(mid_level, fes_active))
                        # Send one immediate update so stimulation starts right away
                        try:
                            configs = build_stim_config()
                            await mid_level.update(configs)
                            log_event("P24", "ImmediateStart", "update sent")
                        except Exception as e:
                            log_event("P24", "ImmediateStartError", str(e))
                        log_event("P24", "Stimulation STARTED", "trigger=arduino")
                elif line == "FES OFF":
                    if fes_active.is_set():
                        fes_active.clear()
                        await mid_level.stop()
                        log_event("P24", "Stimulation STOPPED", "trigger=arduino")

                # Carbonhand messages (Arduino pulses the relay directly) - just log state
                elif line.startswith("CH") or line in ("CH ON", "CH OFF"):
                    log_event("Carbonhand", "State", line)

                else:
                    # Generic messages
                    log_event("Arduino", "Message", line)
# -------------------------------------------------------------
                    
            await asyncio.sleep(0.05)

    except KeyboardInterrupt:
        print("Exiting program...")
        stop_program = True
        fes_active.clear()
        await mid_level.stop()

    # Tell Arduino to pause its active loop and turn off hardware so nothing -------------------
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


    p24_serial.close()
    arduino.close()
    log_event("System", "Shutdown", "COMPLETE")



    p24_serial.close()
    arduino.close()
    log_event("System", "Shutdown")

# if __name__ == "__main__":
#     asyncio.run(main())

try:
    asyncio.run(main())
except Exception:
    import traceback
    traceback.print_exc()
    raise