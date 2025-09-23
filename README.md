# Alisa's working development notes
## Do not touch

## P24 control
- i24_runlive.py - I24 code, needs work
- midlevel_runlive.py - P24 code, 2 channels only, includes graph that doesnt work
- p24_runlive.py - optional 4 channels, much cleaner

## Setup 9/23
- git clone https://github.com/spurgeah/ScienceMode4Python
- conda create --name p24setupenv
- conda activate p24setupenv
- conda install pip
- cd ScienceMode4Python
- pip install -r src/science_mode_4/requirements.txt
- cd P24 control
- python p24_runlive.py
- $env:PYTHONPATH="Y:\Hasomed Code\HasomedSetup14\ScienceMode4Python"

upon opening VSCode
- conda activate p24setupenv
- cd ScienceMode4Python
- cd P24control
- $env:PYTHONPATH="Y:\Hasomed Code\HasomedSetup14\ScienceMode4Python"
- python p24_runlive.py
