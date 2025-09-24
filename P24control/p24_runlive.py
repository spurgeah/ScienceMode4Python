# This script controls a Hasomed P24 stimulator using mid-level commands,
# allows keyboard control over amplitude, frequency, and pulse width,
# deleted plot of stim paraeters for cleaner controls
# controls 2 channels always

import asyncio  # For asynchronous programming (non-blocking loops)
import threading  # To run keyboard listeners in parallel
import keyboard  # To capture real-time key presses
import matplotlib 
import matplotlib.pyplot as plt  # For plotting data
import matplotlib.animation as animation  # For updating plots in real time

# Import classes to communicate with the Hasomed P24 device
from science_mode_4 import DeviceP24, MidLevelChannelConfiguration, ChannelPoint, SerialPortConnection
from examples.utils.example_utils import ExampleUtils  # Utility for fetching COM port from command line
# Get the COM port for the connected device (e.g., COM3 on Windows)
com_port = ExampleUtils.get_comport_from_commandline_argument()
#matplotlib.get_backend()
#matplotlib.use('Qt5Agg')  # Use Qt5 backend for interactive plotting

# ===== USER CONFIGURATION =====
num_channels = 2   # <-- SET NUMBER OF CHANNELS HERE (1–4)

# Default settings per channel
# Define amplitude (mA), frequency (Hz), and pulse width (µs) for each channel
channel_defaults = {
    1: {"amp": 5, "freq": 35, "pw": 275},
    2: {"amp": 5, "freq": 35, "pw": 300},
    3: {"amp": 8, "freq": 40, "pw": 150},
    4: {"amp": 6, "freq": 30, "pw": 200},
    #    Amps = mA, Freq = Hz, PW = µs
}

# keep only active channels
channel_defaults = {ch: channel_defaults[ch] for ch in range(1, num_channels+1)}

# Step sizes for key changes
delta_amp = 1 # mA
delta_freq = 5
delta_pw = 10
# ==============================


# Maximum allowed values for safety
amp_max = 120 # maximum amplitude in mA
    #0-130 in manual
freq_max = 2000 # maximum frequency in Hz
    #in manual, impulse repetition period is .5-16383 ms
    # .0610 - 2000 Hz
pw_max = 10000 # maximum pulse width in microseconds
    #10-65520 in manual

# Parameters that will be updated live during runtime
# params = channel_defaults.copy()
params = {ch: channel_defaults[ch].copy() for ch in channel_defaults}

stop_loop = False  # Flag to indicate if the stimulation loop should stop
# Listens for Enter key to stop stimulation
def listen_for_input():
    global stop_loop
    input("Press Enter to stop...\n")  # Waits for Enter key
    stop_loop = True

# Listens for amplitude changes via keyboard
# 1+w/q = CH1 up/down, 2+w/q = CH2 up/down, etc. 
def listen_for_amp():
    while not stop_loop:
        for ch in range(1, num_channels+1):
            if keyboard.is_pressed(str(ch)):
                if keyboard.is_pressed('w'):
                    params[ch]["amp"] = min(amp_max, params[ch]["amp"] + delta_amp)
                    print(f"[CH{ch}] Amplitude increased to {params[ch]['amp']} mA")
                    keyboard.wait('r')
                elif keyboard.is_pressed('q'):
                    params[ch]["amp"] = max(0.1, params[ch]["amp"] - delta_amp)
                    print(f"[CH{ch}] Amplitude decreased to {params[ch]['amp']} mA")
                    keyboard.wait('r')

# Listens for frequency changes
# 1+s/a = CH1 up/down, 2+s/a = CH2 up/down
def listen_for_freq():
    while not stop_loop:
        for ch in range(1, num_channels+1):
            if keyboard.is_pressed(str(ch)):
                if keyboard.is_pressed('s'):
                    params[ch]["freq"] = min(freq_max, params[ch]["freq"] + delta_freq)
                    print(f"[CH{ch}] Frequency increased to {params[ch]['freq']} Hz")
                    keyboard.wait('r')
                elif keyboard.is_pressed('a'):
                    params[ch]["freq"] = max(0.1, params[ch]["freq"] - delta_freq)
                    print(f"[CH{ch}] Frequency decreased to {params[ch]['freq']} Hz")
                    keyboard.wait('r')

# Listens for pulse width changes
# 1+x/z = CH1 up/down, 2+x/z = CH2 up/down
def listen_for_pw():
    while not stop_loop:
        for ch in range(1, num_channels+1):
            if keyboard.is_pressed(str(ch)):
                if keyboard.is_pressed('x'):
                    params[ch]["pw"] = min(pw_max, params[ch]["pw"] + delta_pw)
                    print(f"[CH{ch}] Pulse Width increased to {params[ch]['pw']} mA")
                    keyboard.wait('r')
                elif keyboard.is_pressed('z'):
                    params[ch]["pw"] = max(0.1, params[ch]["pw"] - delta_pw)
                    print(f"[CH{ch}] Pulse Width decreased to {params[ch]['pw']} mA")
                    keyboard.wait('r')


# Builds stimulation configuration for all channels based on current params
# This is called before every stimulation update
def build_stim_config():
    configs = []
    for ch in range(1, num_channels+1):
        amp = int(params[ch]["amp"])
        pw = int(params[ch]["pw"] / 2)
        freq = params[ch]["freq"]

        points = [
            ChannelPoint(pw, amp),
            ChannelPoint(pw, 0),
            ChannelPoint(pw, -amp)
        ]
        configs.append(MidLevelChannelConfiguration(True, 3, freq, points))
    return configs


# ========== MAIN EXECUTION ==========
async def main():
    global stop_loop

    # Connect to stimulator device
    connection = SerialPortConnection(com_port)
    connection.open()
    device = DeviceP24(connection)
    await device.initialize()  # Get device info and stop any ongoing stimulation

    # Initialize mid-level interface
    mid_level = device.get_layer_mid_level()
    #await mid_level.init(stop_on_error=True)
    await mid_level.init(do_stop_on_all_errors=True)  # Initialize with error handling

    # Start threads for real-time keyboard control
    threading.Thread(target=listen_for_input, daemon=True).start()
    threading.Thread(target=listen_for_amp, daemon=True).start()
    threading.Thread(target=listen_for_freq, daemon=True).start()
    threading.Thread(target=listen_for_pw, daemon=True).start()

    # user input to begin stimulation  
    #input("Press Enter to begin stimulation...\n")
    # once user begins stimulation
    print(f"Stimulation started with {num_channels} channel(s). Press Enter to stop.")

    # Main stimulation loop
    while not stop_loop:
        configs = build_stim_config()  # Get updated config
        await mid_level.update(configs)  # Apply to device
        await asyncio.sleep(1.0)  # Wait a bit
        #await mid_level.get_current_data()  # Keep connection alive

    print("Stopping stimulation...")
    # Print final parameters
    for ch in range(1, num_channels+1):
        print(f"Current amplitude for channel {ch}: {params[ch]['amp']} mA ")
        print(f"Current pulse width for channel {ch}: {params[ch]['pw']} µs ")
        print(f"Current frequency for channel {ch}: {params[ch]['freq']} Hz ")


    # After stopping, cleanly shut down
    # closing stim connection
    await mid_level.stop()
    connection.close()


# Run the async main function
if __name__ == "__main__":
    asyncio.run(main())
