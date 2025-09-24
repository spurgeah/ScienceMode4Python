"""
Alisa Spurgeon - Last edit; 7/22/25

This script demonstrates live data acquisition from a Dyscom device using the ScienceMode4Python library.
It connects to the device via a serial port, initializes the device for measurement, and records live data
from multiple channels. The data is plotted in real-time using fastplotlib and saved to a CSV file.

Run the script, follow the prompts to start and stop recording, and specify the filename for saving the data.
"""
# Import required Python libraries and modules for functionality
import asyncio  # Allows handling tasks that run asynchronously, like live data collection
import threading  # Used for running multiple operations at once (e.g., listening for keyboard input while collecting data)
import shutil  # Used to move files around (e.g., renaming the CSV after saving)
import os  # Interacts with the operating system (not directly used in this script)

# Import the tools provided by the ScienceMode4Python library
# These manage communication with the Dyscom device and interpret its data
from science_mode_4 import DeviceI24, Commands, SerialPortConnection
from science_mode_4.dyscom.ads129x.ads129x_config_register_1 import Ads129xOutputDataRate, Ads129xPowerMode
from science_mode_4.dyscom.ads129x.ads129x_config_register_3 import Ads129xReferenceVoltage
from science_mode_4.dyscom.ads129x.ads129x_channel_settings_register import Ads129xChannelGain, Ads129xChannelSettingsRegister 
from science_mode_4.dyscom.dyscom_get_operation_mode import PacketDyscomGetAckOperationMode
from science_mode_4.dyscom.dyscom_send_live_data import PacketDyscomSendLiveData
from science_mode_4.dyscom.dyscom_types import DyscomGetType, DyscomInitParams, DyscomPowerModulePowerType, DyscomPowerModuleType, DyscomSignalType
from science_mode_4.protocol.types import ResultAndError
from science_mode_4.utils.logger import logger

# import utility modules for keyboard input, CSV saving, and plotting
from examples.utils.example_utils import ExampleUtils, KeyboardInputThread
# from examples.utils.csv_utils import CsvHelper
# from examples.utils.fastplotlib_utils import FastPlotLibHelper
from ccfes_functions import FastPlotLibHelper
#from examples.utils.fastplotlib_utils import FastPlotLibHelper
#from .ccfes_functions import CsvHelper
from examples.utils.csv_utils import CsvHelper
import time  # Used to track how long the program has been running



# prints basic information about the connected Dyscom device
def get_device_info(device):
    general = device.get_layer_general()
    print(f"Device id: {general.device_id}")
    print(f"Firmware version: {general.firmware_version}")
    print(f"Science mode version: {general.science_mode_version}")

# asks the user what filename to save the data under
def prompt_filename(default="values.csv"):
    name = input(f"Enter filename to save (default: {default}): ").strip()
    name = name + ".csv" if not name.endswith(".csv") else name # Ensure it ends with .csv
    return name if name else default  # Use default if user enters nothing

# The main function where everything is set up and run
start_time = time.time() # Record start time before main loop 
def main():
    logger().disabled = True  # Turns off internal logging output to keep the screen clean

    # Automatically finds or accepts a COM port to talk to the Dyscom device
    com_port = ExampleUtils.get_comport_from_commandline_argument()
    connection = SerialPortConnection(com_port)
    connection.open()  # Opens the serial connection

    # Connects to the device and shows its info
    device = DeviceI24(connection)
    asyncio.run(device.initialize())  # Sets up the device for communication
    get_device_info(device)  # Prints out ID and firmware info

    input("Press Enter to start recording...")  # waits for user to start data collection

    # Set up real-time plotting for the first 4 data channels
    # plot_helper = FastPlotLibHelper({
    #     0: ["Channel 1", "r"],  # 'r' = red line
    #     1: ["Channel 2", "g"],  # 'g' = green line
    #     2: ["Channel 3", "y"],  # 'y' = yellow line
    #     3: ["Channel 4", "b"]   # 'b' = blue line
    # }, 1000)  # 1000 samples shown in the plot at a time
    plot_helper = FastPlotLibHelper({
        0: ["Channel 1 (µV)", "r"],
        1: ["Channel 2 (µV)", "g"],
        2: ["Channel 3 (µV)", "y"],
        3: ["Channel 4 (µV)", "b"]
    }, 1000)

    # Set up a temporary file to save incoming data from all 5 channels
    temp_csv = "temp_values.csv"
    csv_helper = CsvHelper(temp_csv, ["package_nr", "Channel 1", "Channel 2", "Channel 3", "Channel 4", "Channel 5", "total_runtime", "time_delta"])
    csv_helper.start()

    # used to stop recording later
    stop_event = threading.Event()

    # waits for the user to press Enter to stop recording
    def keyboard_listener():
        input("Press Enter to stop recording...")
        stop_event.set()  # Signals to stop the recording

    # function that handles receiving and processing live data from the device
    def data_acquisition():
        async def run():
            # Get access to the part of the device that handles physiological signals
            dyscom = device.get_layer_dyscom() # Gets access to Dyscom-specific functions

            # Turn ON the measurement power on the device
            await dyscom.power_module(
                DyscomPowerModuleType.MEASUREMENT,
                DyscomPowerModulePowerType.SWITCH_ON
            )

            # Set up how we want to collect data
            init_params = DyscomInitParams()

            # Choose which signal types we want to collect:
            init_params.signal_type = [
                DyscomSignalType.BI, 
                DyscomSignalType.EMG_1,
                DyscomSignalType.EMG_2,
                DyscomSignalType.BREATHING
                    # there isn't an EMG_3 signal type in the DyscomSignalType enum, default was BREATHING
                    # not sure what I can choose instead for the 4th channel
            ]

            # Choose the speed (samples per second) and quality of data
            # HR_MODE_4_KSPS means high resolution at 4000 samples per second
            # LP_MODE_2_KSPS means lower power mode at 2000 samples per second
            # edit these science_mode_4/dyscom/ads129x/ads129x_config_register_1.py  
            init_params.register_map_ads129x.config_register_1.output_data_rate = (
                #Ads129xOutputDataRate.HR_MODE_4_KSPS__LP_MODE_2_KSPS
                Ads129xOutputDataRate.HR_MODE_1_KSPS__LP_MODE_500_SPS # 1k sample rate
            )
            init_params.register_map_ads129x.config_register_1.power_mode = (
                Ads129xPowerMode.HIGH_RESOLUTION
            )

            ADC_GAIN = 12  # Set this to your configured gain if you change it later
            ADC_VREF = 2.4  # Use 2.4 or 4.0 depending on your CONFIG3 setting
            uV_CONVERSION = ADC_VREF * ADC_GAIN * 1000000 / (2 ** 23)  # for 2.4V
            ohm_CONVERSION = 1 

            
            # This is used to convert raw ADC values to microvolts (µV) for easier interpretation

            init_params.register_map_ads129x.config_register_1.output_data_rate = (
                Ads129xReferenceVoltage.VREF_2_4
            )  # Set the reference voltage to 2.4V
                #VREF_4_0 = 1  Set the reference voltage to 4.0V

            # init_params.register_map_ads129x.channel_settings_register.gain = (
            #     Ads129xChannelGain.GAIN_12
            # )
            init_params.register_map_ads129x.channel_1_setting_register.gain = (
                Ads129xChannelGain.GAIN_12
            )
            init_params.register_map_ads129x.channel_2_setting_register.gain = (
                Ads129xChannelGain.GAIN_12
            )
            init_params.register_map_ads129x.channel_3_setting_register.gain = (
                Ads129xChannelGain.GAIN_12
            )
            init_params.register_map_ads129x.channel_4_setting_register.gain = (
                Ads129xChannelGain.GAIN_12
            )

            # Apply those settings to the device
            await dyscom.init(init_params)

            # Start sending live data from the device
            await dyscom.start()

            try:
                # Keep looping until the stop button is pressed
                while not stop_event.is_set():
                    # Try to get the latest data packet from the device
                    ack = dyscom.packet_buffer.get_packet_from_buffer()

                    # If the packet is valid and contains live data
                    if ack and ack.command == Commands.DL_SEND_LIVE_DATA:
                        sld: PacketDyscomSendLiveData = ack

                        # Plot the first 4 channels on the graph
                        value_uV = [0] * 5
                        for ch in range(4):
                            if ch ==0:
                                value_uV[ch] = sld.samples[ch].value * ohm_CONVERSION
                                #channel 1 is a resistance channel, not an EMG channel
                            else:
                                value_uV[ch] = sld.samples[ch].value * uV_CONVERSION
                            # plot_helper.append_value(ch, sld.samples[ch].value)
                            plot_helper.append_value(ch, value_uV[ch])
                        plot_helper.update()

                        # Save all 5 channel values + time info into the CSV file
                        # csv_helper.append_values(
                        #     ack.number,
                        #     [sld.samples[0].value,
                        #     sld.samples[1].value,
                        #     sld.samples[2].value,
                        #     sld.samples[3].value,
                        #     sld.samples[4].value],
                        #     sld.time_offset
                        # )
                        duration = time.time() - start_time  # Total duration of program in seconds
                        csv_helper.append_values(
                            ack.number,
                            [value_uV[0],
                            value_uV[1],
                            value_uV[2],
                            value_uV[3],
                            value_uV[4],
                            duration ],
                            sld.time_offset
                            
                        )

                    else:
                        # If no valid packet, just pause very briefly to reduce CPU use
                        await asyncio.sleep(0.001)

            finally:
                # Clean shutdown: stop data stream and turn off power
                await dyscom.stop()
                await dyscom.power_module(
                    DyscomPowerModuleType.MEASUREMENT,
                    DyscomPowerModulePowerType.SWITCH_OFF
                )

        asyncio.run(run())  # Actually start the process


    # Start the keyboard listener and data collection in separate threads
    t1 = threading.Thread(target=keyboard_listener, daemon=True)
    t2 = threading.Thread(target=data_acquisition, daemon=True)
    t1.start()
    t2.start()

    # Run the live plotting window (this will block the main thread)
    import fastplotlib as fpl
    fpl.loop.run()

    stop_event.set()  # Stop acquisition when window is closed

    t1.join()  # Wait for user input thread to finish
    t2.join()  # Wait for data thread to finish
    #plot_helper.close()  # Close the plotting figure

    csv_helper.stop()  # Finalize and close the CSV file
    connection.close()  # Close the connection to the device

    folder = os.path.join(".", "csv_files")  # Folder: ./csv_files
    os.makedirs(folder, exist_ok=True) 

    #folder = ".//csv_files"  # Default folder to save CSV file
    # folder = input("Enter folder to save the CSV file (default: ./csv_files):").strip()
    # if not folder:
    #     folder = ".//csv_files"  # Use current directory if nothing entered
    # os.makedirs(folder, exist_ok=True)  # Create folder if it doesn't exist

    # Ask the user where to save the data and rename the file
    final_csv = prompt_filename("values.csv")
    final_path = os.path.join(folder, final_csv) # Use current directory if nothing entered
    shutil.move(temp_csv, final_path)
    print(f"Data saved to {final_path}")  # Confirm file save to user

# Run everything if this file is executed directly
if __name__ == "__main__":
    main()
