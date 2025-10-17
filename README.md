# Alisa's working development notes
## Do not touch

## P24 control
- i24_runlive.py - I24 code, needs work
- midlevel_runlive.py - P24 code, 2 channels only, includes graph that doesnt work
- p24_runlive.py - optional 4 channels, much cleaner

## Setup 9/23
- Created project folder - HasomedSetup14
- open folder in VSCode
- `git clone https://github.com/spurgeah/ScienceMode4Python`
- `conda create --name p24setupenv`
- `conda activate p24setupenv`
- `conda install pip`
- `cd ScienceMode4Python`
- `pip install -r src/science_mode_4/requirements.txt`
- `cd P24 control`
- `python p24_runlive.py`
- If 'No module named examples' error: <br>
`$env:PYTHONPATH="Y:\Hasomed Code\HasomedSetup14\ScienceMode4Python"`

upon opening VSCode
- `conda activate p24setupenv`
- `cd HTIcontrol`
- `$env:PYTHONPATH="Y:\Hasomed Code\HasomedSetup14\ScienceMode4Python"`
- `python p24_runlive.py`
- `python hti_runlive.py`

device manager from powershell - devmgmt.msc 

## 10/16
- start with runing as-is - added delay in .ino to  avoid overwhelming the serial output 
- CH not turning on - emailed BioServo
- switched CHRelayPin, now Low = off? Ryan's suggestion
- removed deviceLocked from .ino
- wayback machine files - hti_runlive2.py and oct17_old.ino

- create ghost code








ghost code python
connect to p24
connect to arudino
read IMU



## Ghost Code Arduino
import libraries
establish variables
setup loop
    set up serial connection
    configure outputs
    connect to IMU
    permission to begin
run loop
    check for command from python
    if reset button is pressed, turn off/ unlock everything
    if not in runMode, skip the rest of the loop
    Arduino read IMU values 
    Arduino send serial IMU values to Py to print
    delay for serial
    if IMU values all = 0, re-initialize IMU
- FES tilt control - RIGHT
        checks tilt & time parameters (tiltStart, rightRelease)
        flip FES state & light
        Arduino send serial FES state to Py to print
        reset time parameters
        delay to prevent retriggering
- CH tilt control - LEFT
        checks tilt & time parameters (tiltStart, rightRelease)
        flip CH state & light
        Arduino send serial CH state to Py to print
        pulse relay to activate CH
        reset time parameters
        delay to prevent retriggering

## Ghost hti_runlive.py
user settings - COM ports, stim parameters, etc
functions
    listen_for_input - press enter to stop
    arduino_write - Send cmd (string) to Arduino and print raw+decoded representation
    arduino_read_line - Read one line from Arduino, print raw bytes (repr) and decoded text
    log_event - 
    build_stim_config
    stimulation_loop - async, updates stim parameters if manually changed
    listen_for_XX - keyboard listener functions
main
    open CSV
    connect to arduino
    Py cmd to Arduino, UNLOCK and RUN
    connect to P24
    start keyboard listeners
    RUN LOOP (while not stop_program)
        Py read and print incoming command from Arduino
        if line.startswith(XX), 
            do something
            log event
    EXCEPT stop_program = true

    Py cmd to Arduino - Pause, FES off, CH off, Lock
    log shutdown

    close P24 connection
    close arduino connection
    log shutdown complete



[SERIAL IN]  <- b'IMU,8640,316,13128\r\n'       .PY 117 arduino write to py, raw line, SUPRESSED
[SERIAL IN]  <- decoded: IMU,8640,316,13128     .py 122 arduino write to py, decoded line
[LOG] Arduino - RX IMU,8640,316,13128           .py 124 log arduino read/RX
[Arduino] IMU,8640,316,13128                    .py 337
[LOG] IMU - Position AX=8640 AY=316 AZ=13128    .py 345

RX - logs for recieving data from a device
TX - logs for sending commands



## Issues to solve 9/30
- csv doesnt log stim or CH events, need to log all events to CSV, including changing of stim parameters
- P24 and carbonhand are not actually triggering, just the LEDs turning on/off

## Fixed 10/1
- Set P24 serial communication baud rate to 9600, same as the arduino
- added baud rate input to utils > serial_port_connection.py 
- Added Arduino libraries (in IDE); MPU6050 by ElectronicCats
- COMS; 1=mouse 4=P24 6=Arduino
- 

## Fixed 10/3
serial communication
- fixed baud rate 
- fixed arduino output byte conversion
- added event logging
- 

CH activation by IMU works
    -device starts out in 'locked' state when the program begins. needs to be in the 'unlocked' state when the LED is off
FES activation does not turn on at all

## Fixed 10/15
- continued python > arduino serial communnication
- now see exact bytes transmitted and received. repr(raw) output shows newline/carriage-return characters and any stray control bytes that previously hid parsing problems.
- All serial traffic is also recorded to CSV via log_event("Arduino","TX"/"RX", ...)
- SERIAL_DEBUG flag lets you enable/disable console inputs without changing logic, puts arduino logic on pause when python isn't running
- Immediate mid_level.update() is sent when Python receives FES ON so stimulation starts immediately.
- CSV header was expanded; log_event now also records current stim params.
- added/fixed delays between serial communications and if statements