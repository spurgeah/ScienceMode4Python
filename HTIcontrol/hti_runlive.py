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
P24_BAUD = ARDUINO_BAUD  # Baud rate for P24 serial


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

# Logging utility
def log_event(source, event, details=""):
    with open(csv_filename, mode="a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([datetime.now().isoformat(), source, event, details])
    print(f"[LOG] {source} - {event} {details}")

def build_stim_config():
    amp = int(STIM_PARAMS["amp"])
    pw = int(STIM_PARAMS["pw"])
    freq = int(STIM_PARAMS["freq"])

    c1_points = [
        ChannelPoint(pw // 2, amp),
        ChannelPoint(pw // 2, 0),
        ChannelPoint(pw // 2, -amp)
    ]
    return [MidLevelChannelConfiguration(True, 3, freq, c1_points)]

async def stimulation_loop(mid_level, active_event):
    while active_event.is_set():
        configs = build_stim_config()
        await mid_level.update(configs)
        await asyncio.sleep(.02) # 50 Hz updates for smooth stim

# Keyboard listener functions
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

async def main():
    global stop_program

    # Init CSV header
    with open(csv_filename, mode="w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Timestamp", "Source", "Event", "Details"])

    # Connect Arduino
    print(f"Connecting to Arduino on {ARDUINO_PORT}...")
    arduino = serial.Serial(ARDUINO_PORT, ARDUINO_BAUD, timeout=1)

    # Connect P24
    print(f"Connecting to P24 stimulator on {P24_PORT}...")
    #device, mid_level, connection = await connect_p24()
    connection = SerialPortConnection(P24_PORT, baudrate=P24_BAUD)
    connection.open() 
    # Startup log: show the actual baud the Serial object is using
    try:
        actual_baud = getattr(connection, "_ser", None)
        if actual_baud is not None:
            actual_baud = actual_baud.baudrate
        else:
            actual_baud = P24_BAUD
    except Exception:
        actual_baud = P24_BAUD
    print(f"P24 connection opened on {P24_PORT} @ {actual_baud} baud")
    device = DeviceP24(connection)
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
            if arduino.in_waiting:
                line = arduino.readline().decode().strip()
                if line:
                    #print(f"[Arduino] {line}")
                    log_event("Arduino", "Message", line)
                    # if line.startswith("IMU"):
                    #     try:
                    #         _, ax, ay, az = line.split(",")
                    #         log_event("Arduino", "IMU", f"AX={ax}, AY={ay}, AZ={az}")
                    #         # output; 2025-09-25T11:05:32.123456,Arduino,IMU,AX=123 AY=-14567 AZ=876
                    #         # writer.writerow([timestamp, "IMU", ax, ay, az])
                    #         # output; Timestamp,Source,AX,AY,AZ
                    #     except ValueError:
                    #         log_event("Arduino", "IMU", f"Malformed: {line}")
                elif line == "FES ON":
                    if not fes_active.is_set():
                        fes_active.set()
                        asyncio.create_task(stimulation_loop(mid_level, fes_active))
                        log_event("P24", "Stimulation STARTED")
                elif line == "FES OFF":
                    if fes_active.is_set():
                        fes_active.clear()
                        await mid_level.stop()
                        log_event("P24", "Stimulation STOPPED")
                elif line.startswith("CH"):
                    log_event("Carbonhand", "State", line)

            await asyncio.sleep(0.05)

    except KeyboardInterrupt:
        print("Exiting program...")
        stop_program = True
        fes_active.clear()
        await mid_level.stop()
        connection.close()
        arduino.close()
        log_event("System", "Shutdown")

if __name__ == "__main__":
    asyncio.run(main())