# ScienceMode4 Python

## Introduction

Pure Python implementation of HasomedScience ScienceMode 4 protocol for P24 (https://github.com/ScienceMode/ScienceMode4_P24) and I24 (https://github.com/ScienceMode/ScienceMode4_I24) devices. To use this library see section [Installation](#installation). Library and examples are tested under Windows, Linux and MacOS.

## Requirements

Python 3.11 or higher

# Library

## Installation
- Install science_mode_4 library inclusive dependencies via pip
  - `pip install science_mode_4`
  - https://pypi.org/project/science-mode-4/

## Dependencies
- PySerial
  - https://pypi.org/project/pyserial/
  - `pip install pyserial`
- PyUSB
  - https://pypi.org/project/pyusb/
  - `pip install pyusb` 
  - On Windows
    - Install libusb-package to get _libusb-XX.dll_
      - https://pypi.org/project/libusb-package/
      - `pip install libusb-package`
    - Under Windows there may be driver issues
      - See https://github.com/libusb/libusb/wiki/Windows#How_to_use_libusb_on_Windows
      - Use Zadig to change driver for _STM32 Virtual ComPort_ to _libusb-XX.dll_ and reinstall driver

## Build library
- Only necessary, if you made changes to the library or install a version from a branch
- Install build dependencies
  - `python -m pip install --upgrade build`
- Install other library dependencies
  - `pip install -r src/science_mode_4/requirements.txt`
- Optional run linter
  - `pip install pylint`
  - `pylint .\src\science_mode_4\`
- Build project
  - `python -m build`
- Install local library
  - `pip install .\dist\science_mode_4-0.0.7-py3-none-any.whl` (adjust filename accordingly)

# Examples

## Description
- Located in folder `examples`
- Run examples with `python -m examples.<layer>.<example>`
  - From root directory of this repository
  - Example: `python -m examples.dyscom.example_dyscom_fastplotlib`
  - All examples try to find the serial port that a science mode device is connected to automatically
  - If that fails, provide serial port name as parameter, e.g. `python -m examples.<layer>.<example> COM3`
- Good starting point for an simple stimulation is example `example_mid_level`
- Examples have own dependencies, see [Dependencies for examples](#dependencies-for-examples)
- General layer
  - `python -m examples.general.example_general`
    - Demonstrates how to use general layer to initialize device, get serial number and firmware version
    - Does not call any stimulation functions
- Mid level layer
  - `python -m examples.mid_level.example_mid_level_simple`
    - Demonstrates how to use mid level layer, where a stimulation pattern is send to the stimulator and the device automatically executes the pattern by itself for 15s
  - `python -m examples.mid_level.example_mid_level`
    - Demonstrates how to use mid level layer, where a stimulation pattern is send to the stimulator and the device automatically executes the pattern by itself until user ends stimulation by keyboard
- Low level layer
  - `python -m examples.low_level.example_low_level`
    - Demonstrates how to use low level layer, where host has to trigger stimulation manually, in this case by pressing a key 
  - `python -m examples.low_level.example_low_level_plot`
    - Demonstrates how to use low level layer to stimulate, measure current and plot it in a graph using PyPlot
- Dyscom layer
  - `python -m examples.dyscom.example_dyscom_get`
    - Demonstrate how to use different get commands from dyscom layer
  - `python -m examples.dyscom.example_dyscom_fastplotlib`
    - Demonstrate how to use dyscom layer to measure data and plotting values using fastplotlib
  - `python -m examples.dyscom.example_dyscom_pyplot`
    - Demonstrate how to use dyscom layer to measure data and plotting values using PyPlot
  - `python -m examples.dyscom.example_dyscom_write_csv`
    - Demonstrate how to use dyscom layer to measure data and writing measurement data to a .csv-file
  - `python -m examples.dyscom.example_dyscom_send_file`
    - Demonstrate how to use dyscom layer to save measurement data on memory card and reading it afterwards

## Dependencies for examples
- Install all dependencies
  - `pip install -r examples/requirements.txt`
- Py-Getch
  - https://pypi.org/project/py-getch/
  - `pip install py-getch`
- NumPy
  - https://pypi.org/project/numpy/
  - `pip install numpy`
- Matplotlib / PyPlot
  - https://pypi.org/project/matplotlib/
  - `pip install matplotlib`
- Fastplotlib with glfw backend
  - https://pypi.org/project/fastplotlib/
  - `pip install -U fastplotlib`
  - `pip install -U glfw`

# Changes

## 0.0.11
- Implemented UsbConnection class
  - Alternative for SerialPortConnection, both share the same base class Connection
  - Added _PyUSB_ and _libusb-package_ as dependencies

## 0.0.12
- Dyscom init
  - Added channel settings register
- Some bugfixes

## 0.0.13
- Fixed error with example keyboard utils under Linux
- Enhanced example low level plot to show all channels

## 0.0.14
- Improved examples under Linux/MacOS

## 0.0.15
- Enhanced readme
- Changed current for ChannelPoint from int to float

## 0.0.16
- Fixed error with PacketLowLevelChannelConfigAck result

## 0.0.17
- Added sample that demonstrates how to read measurement data files from I24 devices

## 0.0.18
- More documentation
