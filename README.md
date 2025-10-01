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
- `cd P24control`
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

## 10/2 
- get CH right small glove
- test baud rate setup as-is
- bring in hat for testing
order more magmets for decor
re-arrange project wires
re-arrange desk wires
re-align poster