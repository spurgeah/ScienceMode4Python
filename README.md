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

## 10/16
start with runing as-is




ghost code python
connect to p24
connect to arudino
read IMU



ghost code ardino - loop

print IMU readings

declare FES on
flip light (on/off)
flip state/pin (boolean - high/low)
send state message to python

Declare CH on
flip light
flip state
    pulse relay
send state message to python

recieve message from python
    decode

if 


[SERIAL IN]  <- b'IMU,8640,316,13128\r\n'       .PY 117 arduino write to py, raw line, SUPRESSED
[SERIAL IN]  <- decoded: IMU,8640,316,13128     .py 122 arduino write to py, decoded line
[LOG] Arduino - RX IMU,8640,316,13128           .py 124 log arduino read/RX
[Arduino] IMU,8640,316,13128                    .py 337
[LOG] IMU - Position AX=8640 AY=316 AZ=13128    .py 345

RX - logs for recieving data from a device
TX - logs for sending commands