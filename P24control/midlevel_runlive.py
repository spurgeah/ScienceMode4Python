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
# Default settings for amplitude, frequency, and pulse width for both channels
channel_defaults = {
    "amp1": 10,    # in milliamps
    "amp2": 5,
    "freq1": 35,  # in Hz
    "freq2": 35,
    "pw1": 75,   # in microseconds
    "pw2": 300
}

# Change steps when keys are pressed
delta_amp = 0.25
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
params = channel_defaults.copy()

stop_loop = False  # Flag to indicate if the stimulation loop should stop
# Listens for Enter key to stop stimulation
def listen_for_input():
    global stop_loop
    input("Press Enter to stop...\n")  # Waits for Enter key
    stop_loop = True

# Listens for amplitude changes via keyboard
# 1+w/q = CH1 up/down, 2+w/q = CH2 up/down
def listen_for_amp():
    while not stop_loop:
        if keyboard.is_pressed('1'):
            if keyboard.is_pressed('w'):
                params["amp1"] = min(amp_max, params["amp1"] + delta_amp)
                print(f"[CH1] Amplitude increased to {params['amp1']} mA")
                keyboard.wait('r')
            elif keyboard.is_pressed('q'):
                params["amp1"] = max(0.1, params["amp1"] - delta_amp)
                print(f"[CH1] Amplitude decreased to {params['amp1']} mA")
                keyboard.wait('r')
        elif keyboard.is_pressed('2'):
            if keyboard.is_pressed('w'):
                params["amp2"] = min(amp_max, params["amp2"] + delta_amp)
                print(f"[CH2] Amplitude increased to {params['amp2']} mA")
                keyboard.wait('r')
            elif keyboard.is_pressed('q'):
                params["amp2"] = max(0.1, params["amp2"] - delta_amp)
                print(f"[CH2] Amplitude decreased to {params['amp2']} mA")
                keyboard.wait('r')

# Listens for frequency changes
# 1+s/a = CH1 up/down, 2+s/a = CH2 up/down
def listen_for_freq():
    while not stop_loop:
        if keyboard.is_pressed('1'):
            if keyboard.is_pressed('s'):
                params["freq1"] = min(freq_max, params["freq1"] + delta_freq)
                print(f"[CH1] Frequency increased to {params['freq1']} Hz")
                keyboard.wait('r')
            elif keyboard.is_pressed('a'):
                params["freq1"] = max(1, params["freq1"] - delta_freq)
                print(f"[CH1] Frequency decreased to {params['freq1']} Hz")
                keyboard.wait('r')
        elif keyboard.is_pressed('2'):
            if keyboard.is_pressed('s'):
                params["freq2"] = min(freq_max, params["freq2"] + delta_freq)
                print(f"[CH2] Frequency increased to {params['freq2']} Hz")
                keyboard.wait('r')
            elif keyboard.is_pressed('a'):
                params["freq2"] = max(1, params["freq2"] - delta_freq)
                print(f"[CH2] Frequency decreased to {params['freq2']} Hz")
                keyboard.wait('r')

# Listens for pulse width changes
# 1+x/z = CH1 up/down, 2+x/z = CH2 up/down
def listen_for_pw():
    while not stop_loop:
        if keyboard.is_pressed('1'):
            if keyboard.is_pressed('x'):
                params["pw1"] = min(pw_max, params["pw1"] + delta_pw)
                print(f"[CH1] Pulse width increased to {params['pw1']} μs")
                keyboard.wait('r')
            elif keyboard.is_pressed('z'):
                params["pw1"] = max(1, params["pw1"] - delta_pw)
                print(f"[CH1] Pulse width decreased to {params['pw1']} μs")
                keyboard.wait('r')
        elif keyboard.is_pressed('2'):
            if keyboard.is_pressed('x'):
                params["pw2"] = min(pw_max, params["pw2"] + delta_pw)
                print(f"[CH2] Pulse width increased to {params['pw2']} μs")
                keyboard.wait('r')
            elif keyboard.is_pressed('z'):
                params["pw2"] = max(1, params["pw2"] - delta_pw)
                print(f"[CH2] Pulse width decreased to {params['pw2']} μs")
                keyboard.wait('r')

# Builds stimulation configuration for both channels based on current params
# This is called before every stimulation update
def build_stim_config():
    c1_points = [
        ChannelPoint(int(params["pw1"] / 2), int(params["amp1"])),
        ChannelPoint(int(params["pw1"] / 2), 0),
        ChannelPoint(int(params["pw1"] / 2), -int(params["amp1"]))
    ]
    c2_points = [
        ChannelPoint(int(params["pw2"] / 2), int(params["amp2"])),
        ChannelPoint(int(params["pw2"] / 2), 0),
        ChannelPoint(int(params["pw2"] / 2), -int(params["amp2"]))  
    ]
    cc1 = MidLevelChannelConfiguration(True, 3, params["freq1"], c1_points)
    cc2 = MidLevelChannelConfiguration(True, 3, params["freq2"], c2_points)
    return [cc1, cc2]

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

    print("Stimulation started. Press Enter to stop.")

    # Main stimulation loop
    while not stop_loop:
        configs = build_stim_config()  # Get updated config
        await mid_level.update(configs)  # Apply to device
        await asyncio.sleep(1.0)  # Wait a bit
        #await mid_level.get_current_data()  # Keep connection alive

    print("Stopping stimulation...")
    # Print final parameters
    print(f"Current amplitude for channel 1: {params['amp1']} mA ")
    print(f"Current amplitude for channel 2: {params['amp2']} mA ")
    print(f"Current pulse width for channel 1: {params['pw1']} µs ")
    print(f"Current pulse width for channel 2: {params['pw2']} µs ")
    print(f"Current frequency for channel 1: {params['freq1']} Hz ")
    print(f"Current frequency for channel 2: {params['freq2']} Hz ")


    # After stopping, cleanly shut down
    # closing stim connection
    await mid_level.stop()
    connection.close()


# Run the async main function
if __name__ == "__main__":
    asyncio.run(main())
