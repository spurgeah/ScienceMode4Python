"""
Integrated Python control script for:
- Reading IMU triggers from Arduino Uno
- Controlling Hasomed P24 stimulator instead of relay-based TENS
- Logging all events (IMU, Carbonhand, P24) to CSV
- Allowing keyboard-based live tuning of stimulation parameters

This is a small modified copy of hti_runlive4.py with faster P24 polling
and a forced immediate get_current_data after the first update to reduce
onset latency.
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
P24_BAUD = 9600  # Baud rate for P24 serial

# Default stimulation parameters
num_channels = 1   # <-- SET NUMBER OF CHANNELS HERE (1–4)
STIM_PARAMS = {
    1: {"amp": 8, "freq": 35, "pw": 360},
    2: {"amp": 5, "freq": 35, "pw": 300},
    3: {"amp": 8, "freq": 40, "pw": 150},
    4: {"amp": 6, "freq": 30, "pw": 200},
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

# Global flags
stop_program = False

def listen_for_input():
    global stop_program
    input("**** Press Enter to stop...**** \n")
    stop_program = True

# Serial helpers (same as original)
def arduino_write(arduino_ser, cmd: str):
    try:
        if not cmd.endswith("\n"):
            cmd_to_send = cmd + "\n"
        else:
            cmd_to_send = cmd
        raw = cmd_to_send.encode("utf-8")
        arduino_ser.write(raw)
        print(f"[PYTHON > ARDUINO] -> {repr(raw)}  (text: {cmd.strip()})")
        try:
            log_event("Arduino", "TX", cmd.strip())
        except Exception:
            pass
    except Exception as e:
        print(f"[PYTHON > ARDUINO SERIAL RECIEVE ERROR] failed to send {cmd!r}: {e}")
        try:
            log_event("Arduino", "TX_ERROR", f"{cmd} | {e}")
        except Exception:
            pass


def arduino_read_line(arduino_ser) -> str:
    try:
        raw = arduino_ser.readline()
    except Exception as e:
        print(f"[ARDUINO > PYTHON SERIAL CMD ERROR] readline failed: {e}")
        return ""
    if not raw:
        return ""
    text = raw.decode('utf-8', errors='replace').strip()
    try:
        log_event("Arduino", "RX", text)
    except Exception:
        pass
    return text


def log_event(source, event, details="", stim_params=""):
    if not stim_params:
        stim_params = {}
        for ch in range(1, num_channels + 1):
            stim_params[ch] = f"{STIM_PARAMS[ch]['amp']},{STIM_PARAMS[ch]['freq']},{STIM_PARAMS[ch]['pw']}"
    with open(csv_filename, mode="a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([datetime.now().isoformat(), source, event, details, stim_params])


def build_stim_config():
    configs = []
    for ch in range(1, num_channels + 1):
        amp = int(STIM_PARAMS[ch]["amp"])
        pw = int(STIM_PARAMS[ch]["pw"])
        freq = int(STIM_PARAMS[ch]["freq"])
        points = [
            ChannelPoint(pw // 2, amp),
            ChannelPoint(pw // 2, 0),
            ChannelPoint(pw // 2, -amp)
        ]
        configs.append(MidLevelChannelConfiguration(True, 3, freq, points))
    return configs

async def stimulation_loop(mid_level, active_event):
    last_get = time.monotonic()
    while active_event.is_set():
        configs = build_stim_config()
        try:
            log_event("P24", "Update", f"configs={configs}")
        except Exception:
            log_event("P24", "Update", "configs prepared")
        try:
            await mid_level.update(configs)
        except Exception as e:
            log_event("P24", "UpdateError", str(e))

        now = time.monotonic()
        # Reduced interval to poll device more frequently
        if now - last_get >= 0.75:
            try:
                _ = await mid_level.get_current_data()
                log_event("P24", "get_current_data", "ok")
            except Exception as e:
                log_event("P24", "get_current_data_error", str(e))
            last_get = now

        await asyncio.sleep(.02)

# keyboard listeners (unchanged) ...
def listen_for_amp():
    while not stop_program:
        if keyboard.is_pressed("w"):
            STIM_PARAMS[1] = min(AMP_MAX, STIM_PARAMS[1] + DELTA_AMP)
            log_event("Keyboard", "AMP UP", f"{STIM_PARAMS[1]} mA")
            time.sleep(0.2)
        elif keyboard.is_pressed("q"):
            STIM_PARAMS[1] = max(0.1, STIM_PARAMS[1] - DELTA_AMP)
            log_event("Keyboard", "AMP DOWN", f"{STIM_PARAMS[1]} mA")
            time.sleep(0.2)

def listen_for_freq():
    while not stop_program:
        if keyboard.is_pressed("s"):
            STIM_PARAMS[1] = min(FREQ_MAX, STIM_PARAMS[1] + DELTA_FREQ)
            log_event("Keyboard", "FREQ UP", f"{STIM_PARAMS[1]} Hz")
            time.sleep(0.2)
        elif keyboard.is_pressed("a"):
            STIM_PARAMS[1] = max(1, STIM_PARAMS[1] - DELTA_FREQ)
            log_event("Keyboard", "FREQ DOWN", f"{STIM_PARAMS[1]} Hz")
            time.sleep(0.2)

def listen_for_pw():
    while not stop_program:
        if keyboard.is_pressed("x"):
            STIM_PARAMS[1] = min(PW_MAX, STIM_PARAMS[1] + DELTA_PW)
            log_event("Keyboard", "PW UP", f"{STIM_PARAMS[1]} µs")
            time.sleep(0.2)
        elif keyboard.is_pressed("z"):
            STIM_PARAMS[1] = max(1, STIM_PARAMS[1] - DELTA_PW)
            log_event("Keyboard", "PW DOWN", f"{STIM_PARAMS[1]} µs")
            time.sleep(0.2)

async def main():
    global stop_program

    with open(csv_filename, mode="w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Timestamp", "Source", "Event", "Details",  "Stim_Amp", "Stim_Freq", "Stim_PW"])

    print(f"Connecting to Arduino on {ARDUINO_PORT}...")
    arduino = serial.Serial(ARDUINO_PORT, ARDUINO_BAUD, timeout=1)

    try:
        arduino_write(arduino, "RUN")
        time.sleep(0.05)
        log_event("Arduino", "CMD", "RUN sent")
    except Exception as e:
        print(f"Warning: failed to send RUN to Arduino: {e}")

    try:
        arduino_write(arduino, "UNLOCK")
        time.sleep(0.05)
        arduino_write(arduino, "RUN")
        time.sleep(0.05)
        log_event("Arduino", "CMD", "UNLOCK and RUN sent")
    except Exception as e:
        print(f"Warning: failed to send startup commands to Arduino: {e}")

    print(f"Connecting to P24 stimulator on {P24_PORT}...")
    try:
        p24_serial = SerialPortConnection(P24_PORT, baudrate=P24_BAUD)
    except TypeError:
        p24_serial = SerialPortConnection(P24_PORT)
        try:
            ser_obj = getattr(p24_serial, "_ser", None) or getattr(p24_serial, "ser", None)
            if ser_obj is not None:
                ser_obj.baudrate = P24_BAUD
                try:
                    print(f"P24 baud fallback: set underlying serial baud to {ser_obj.baudrate}")
                except Exception:
                    print("P24 baud fallback: set underlying serial baud (value unavailable)")
            else:
                print("P24 baud fallback: underlying serial object not found; using default baud")
        except Exception as e:
            print(f"P24 baud fallback: failed to set baud on underlying serial object: {e}")
    p24_serial.open()

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
    print("P24 ready.")

    threading.Thread(target=listen_for_input, daemon=True).start()
    threading.Thread(target=listen_for_amp, daemon=True).start()
    threading.Thread(target=listen_for_freq, daemon=True).start()
    threading.Thread(target=listen_for_pw, daemon=True).start()
    print("Keyboard listening threads started.")

    fes_active = asyncio.Event()
    print("FES event flag created.")

    try:
        while not stop_program:
            if arduino.in_waiting:
                line = arduino_read_line(arduino)
                if not line:
                    await asyncio.sleep(0.05)
                    continue
                print(f"[Arduino > Python] {line}")
                if line.startswith("IMU,"):
                    parts = line.split(",")
                    if len(parts) >= 4:
                        ax, ay, az = parts[1], parts[2], parts[3]
                        log_event("IMU", "Position", f"AX={ax} AY={ay} AZ={az}")
                    else:
                        log_event("Arduino", "Malformed IMU", line)
                elif line.startswith("FES ON"):
                    if not fes_active.is_set():
                        fes_active.set()
                        asyncio.create_task(stimulation_loop(mid_level, fes_active))
                        try:
                            configs = build_stim_config()
                            await mid_level.update(configs)
                            log_event("P24", "ImmediateStart", "update sent")
                            # Call get_current_data immediately to speed activation
                            try:
                                _ = await mid_level.get_current_data()
                                log_event("P24", "Immediate get_current_data", "ok")
                            except Exception as e:
                                log_event("P24", "Immediate get_current_data error", str(e))
                        except Exception as e:
                            log_event("P24", "ImmediateStartError", str(e))
                        log_event("P24", "Stimulation STARTED", "trigger=arduino")
                elif line.startswith("FES OFF"):
                    if fes_active.is_set():
                        fes_active.clear()
                        await mid_level.stop()
                        log_event("P24", "Stimulation STOPPED", "trigger=arduino")
                elif line.startswith("CH") or line in ("CH LOCK ON", "CH LOCK OFF"):
                    log_event("Carbonhand", "State", line)
                else:
                    log_event("Arduino", "Message", line)
            else:
                await asyncio.sleep(0.1)
                continue
            await asyncio.sleep(0.05)

    except KeyboardInterrupt:
        print("Exiting program...")
        stop_program = True
        fes_active.clear()
        await mid_level.stop()

    try:
        arduino_write(arduino, "PAUSE")
        time.sleep(0.02)
        arduino_write(arduino, "FES OFF")
        time.sleep(0.02)
        arduino_write(arduino, "CH OFF")
        time.sleep(0.02)
        arduino_write(arduino, "LOCK")
        time.sleep(0.02)
        log_event("Arduino", "CMD", "SHUTDOWN_COMMANDS_SENT")
    except Exception as e:
        print(f"Warning: failed to send shutdown commands to Arduino: {e}")

    p24_serial.close()
    arduino.close()
    log_event("System", "Shutdown", "COMPLETE")

try:
    asyncio.run(main())
except Exception:
    import traceback
    traceback.print_exc()
    raise
