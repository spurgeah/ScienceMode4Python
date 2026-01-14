# import important stuff
# user configurations
# press enter to exit code
# no keyboard listeners for amplitude, frequency, or pulse width
# build stim configuration
# main loop
# initialize / device setup
# listen for stim toggle on/off with space bar
# if stim toggle is ON:
#     turn on stimulation with current parameters
# else:
#     turn off stimulation
# print code exited once enter is pressed
# stop stim and close device connection

# This script controls a Hasomed P24 stimulator using mid-level commands
# Simple spacebar toggle on/off - no amplitude/frequency/pulse width adjustments
# Press SPACE to toggle stimulation, Enter to exit

## Runs continuously - stim turned on and off with SPACE
# TOGGLE WORKS
# NO EDITING PARAMETERS WITH KEYBOARD LISTENERS

# ===== IMPORT IMPORTANT STUFF =====
import asyncio
import threading
import keyboard

# Import classes to communicate with the Hasomed P24 device
from science_mode_4 import DeviceP24, MidLevelChannelConfiguration, ChannelPoint, SerialPortConnection
from examples.utils.example_utils import ExampleUtils
# Get the COM port for the connected device (e.g., COM3 on Windows)
com_port = ExampleUtils.get_comport_from_commandline_argument()

# ===== USER CONFIGURATION =====
num_channels = 1   # <-- SET NUMBER OF CHANNELS HERE (1–4)

# Default settings per channel
channel_defaults = {
    1: {"amp": 30, "freq": 35, "pw": 100},
    2: {"amp": 25, "freq": 35, "pw": 100},
    3: {"amp": 8, "freq": 40, "pw": 150},
    4: {"amp": 6, "freq": 30, "pw": 200},
}

# Keep only active channels
channel_defaults = {ch: channel_defaults[ch] for ch in range(1, num_channels+1)}

# Maximum allowed values for safety
amp_max = 120 # maximum amplitude in mA
    #0-130 in manual
freq_max = 2000 # maximum frequency in Hz
    #in manual, impulse repetition period is .5-16383 ms
    # .0610 - 2000 Hz
pw_max = 10000 # maximum pulse width in microseconds
    #10-65520 in manual

# Parameters updated during runtime
params = {ch: channel_defaults[ch].copy() for ch in channel_defaults}

stop_loop = False  # Flag to exit
stim_active = False  # Track stimulation state
stim_was_active = False  # Track previous state

# ===== LISTEN FOR ENTER KEY TO EXIT =====
def listen_for_input():
    global stop_loop
    input("Press Enter to stop...\n")
    stop_loop = True

# ===== BUILD STIMULATION CONFIGURATION =====
def build_stim_config():
    """Build configuration for all 8 channels on P24"""
    configs = []
    for ch in range(1, 9):  # 8 channels on P24
        if ch <= num_channels:
            # Active channels use our parameters
            amp = int(params[ch]["amp"])
            pw = int(params[ch]["pw"] / 2)
            freq = params[ch]["freq"]
            points = [
                ChannelPoint(pw, amp),
                ChannelPoint(pw, 0),
                ChannelPoint(pw, -amp)
            ]
            configs.append(MidLevelChannelConfiguration(True, 3, freq, points))
        else:
            # Inactive channels - disabled
            points = [
                ChannelPoint(1, 1),
                ChannelPoint(1, 0),
                ChannelPoint(1, -1)
            ]
            configs.append(MidLevelChannelConfiguration(False, 3, 1, points))
    return configs

# ===== LISTEN FOR SPACEBAR TOGGLE =====
async def listen_for_spacebar(mid_level):
    """Listen for spacebar presses to toggle stimulation on/off"""
    global stim_active
    space_pressed = False
    
    while not stop_loop:
        if keyboard.is_pressed('space'):
            if not space_pressed:  # Transition from not-pressed to pressed
                print("\nToggling stimulation ON/OFF")
                stim_active = not stim_active  # Toggle state
                
                if stim_active:
                    print("FES ON")
                else:
                    print("FES OFF")
                    try:
                        await mid_level.stop()
                    except Exception as e:
                        print(f"Error stopping: {e}")
                
                space_pressed = True
                await asyncio.sleep(0.2)  # Debounce delay
        else:
            space_pressed = False
        
        await asyncio.sleep(0.05)

# ===== MAIN EXECUTION =====
async def main():
    global stop_loop, stim_was_active

    # Initialize device and connection
    connection = SerialPortConnection(com_port)
    connection.open()
    device = DeviceP24(connection)
    await device.initialize()

    # Get mid-level interface
    mid_level = device.get_layer_mid_level()
    await mid_level.init(do_stop_on_all_errors=True)

    # Start listener for Enter key to exit
    threading.Thread(target=listen_for_input, daemon=True).start()
    
    # Start spacebar listener as concurrent task
    spacebar_task = asyncio.create_task(listen_for_spacebar(mid_level))

    print(f"Stimulation controller ready with {num_channels} channel(s).")
    print("Press SPACE to toggle ON/OFF, Enter to exit.")

    # Main loop
    while not stop_loop:
        try:
            # Detect transition from OFF to ON
            if stim_active and not stim_was_active:
                # Reinitialize when turning back on
                await mid_level.init(do_stop_on_all_errors=True)
                await asyncio.sleep(0.1)
                stim_was_active = True
            
            # Send continuous updates while stimulation is active
            if stim_active:
                configs = build_stim_config()
                await mid_level.update(configs)
            else:
                stim_was_active = False
            
            await asyncio.sleep(1.0)
        except Exception as e:
            print(f"Error in main loop: {e}")
            await asyncio.sleep(1.0)

    # Clean up
    spacebar_task.cancel()
    
    print("\nStopping stimulation...")
    await mid_level.stop()
    connection.close()
    print("Code exited. Device connection closed.")

# ===== RUN =====
if __name__ == "__main__":
    asyncio.run(main())
