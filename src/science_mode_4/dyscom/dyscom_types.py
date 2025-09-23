"""Provides dyscom types"""

from dataclasses import dataclass, field
from enum import IntEnum
import datetime

from science_mode_4.utils.byte_builder import ByteBuilder
from .ads129x.ads129x import Ads129x
from .dyscom_helper import DyscomHelper

class DyscomFrequencyOut(IntEnum):
    """Represent dyscom type for frequency out"""
    UNUSED = 0
    SAMPLES_PER_SECOND_32K = 1
    SAMPLES_PER_SECOND_16K = 2
    SAMPLES_PER_SECOND_8K = 3
    SAMPLES_PER_SECOND_4K = 4
    SAMPLES_PER_SECOND_2K = 5
    SAMPLES_PER_SECOND_1K = 6
    SAMPLES_PER_SECOND_500 = 7
    SAMPLES_PER_SECOND_250  = 8


class DyscomInitState(IntEnum):
    """Represent dyscom type for init state"""
    UNUSED = 0
    SUCCESS = 1
    ERROR_STORAGE_INIT = 2
    ERROR_STORAGE_WRITE = 3
    ERROR_STORAGE_FULL = 4
    UNUSED2 = 5
    ERROR_ADS129X_REGISTER  = 6


class DyscomSignalType(IntEnum):
    """Represent dyscom type for signal type"""
    UNUSED = 0
    UNKNOWN = 1
    BI = 2 # bipolar signal
    EMG_1 = 3 # electromyography signal 1
    OP_VOLTAGE = 4 # operational amplifier voltage
    TEST_SIGNAL = 5 # test signal
    GROUND = 6 # ground
    TEMPERATURE = 7 # temperature
    INTERNAL_SC = 8 # internal temperature sensor
    EMG_2 = 9 # electromyography signal 2
    TIME = 10 # time
    PUSHBUTTON = 11 # pushbutton
    BREATHING = 12 # breathing 


class DyscomFilterType(IntEnum):
    """Represent dyscom type for filter type"""
    FILTER_OFF = 0 # 4k sample rate
    PREDEFINED_FILTER_1 = 1 # 1k sample rate
    PREDEFINED_FILTER_2 = 2 # 4k sample rate
    PREDEFINED_FILTER_3 = 3 # 1k sample rate


class DyscomInitFlag(IntEnum):
    """Represent dyscom type for init flag"""
    ENABLE_LIVE_DATA_MODE = 0
    ENABLE_SD_STORAGE_MODE = 1
    ENABLE_TIMED_START = 2
    SET_SYSTEM_TIME_WITH_SENDED_SYSTEM_TIME_STAMP = 3
    MUTE = 4


class DyscomGetType(IntEnum):
    """Represent dyscom type for get"""
    BATTERY = 0
    FILESYSTEM_STATUS = 1
    LIST_OF_MEASUREMENT_META_INFO = 2
    OPERATION_MODE = 3
    FILE_BY_NAME = 4
    DEVICE_ID = 5
    FIRMWARE_VERSION = 6
    FILE_INFO = 7


class DyscomGetOperationModeType(IntEnum):
    """Represents dyscom get operation mode type"""
    UNDEFINED = 0
    IDLE = 1
    LIVE_MEASURING_PRE = 2
    LIVE_MEASURING = 3
    RECORD_PRE = 4
    RECORD = 5
    DATATRANSFER_PRE = 6
    DATATRANSFER = 7


class DyscomPowerModuleType(IntEnum):
    """Represents dyscom power module type"""
    UNDEFINED = 0
    BLUETOOTH = 1
    MEMORY_CARD = 2
    MEASUREMENT = 3
    RESEARCH = 4


class DyscomPowerModulePowerType(IntEnum):
    """Represents dyscom power module power type"""
    SWITCH_OFF = 0
    SWITCH_ON = 1


class DyscomPowerLiveDataStatusFlag(IntEnum):
    """Represents dyscom live data status type"""
    POSITIVE_ELECTRODE_ADHESIVE = 1
    NEGATIVE_ELECTRODE_ADHESIVE = 2
    BOTH_ELECTRODES_ADHESIVE = 3


class DyscomFileByNameMode(IntEnum):
    """Represents dyscom file by name mode type"""
    UNDEFINED = 0
    MULTI_BLOCK = 1
    SINGLE_BLOCK = 2


class DyscomEnergyFlag(IntEnum):
    """Represents dyscom energy flag type"""
    UNDEFINED = 0
    CABLE_CONNECTED = 1
    DEVICE_IS_LOADING = 2


class DyscomSysType(IntEnum):
    """Represents dyscom sys type"""
    UNDEFINED = 0
    DELETE_FILE = 1
    DEVICE_SLEEP = 2
    DEVICE_STORAGE = 3


class DyscomSysState(IntEnum):
    """Represents dyscom sys state"""
    UNDEFINED = 0
    SUCCESSFUL = 1


@dataclass
class DyscomElectrodeSample:
    """Represent an electrode sample send by live data packet"""
    value: float = 0.0
    signal_type: DyscomSignalType = DyscomSignalType.UNUSED
    status: set[DyscomPowerLiveDataStatusFlag] = field(default_factory=lambda: set()) # pylint:disable=unnecessary-lambda


@dataclass
class DyscomInitParams():
    """Dyscom init packet parameters"""

    register_map_ads129x = Ads129x()
    start_time = datetime.datetime.now()
    system_time = datetime.datetime.now()
    proband_name = ""
    investigator_name = ""
    proband_number = ""
    duration = datetime.timedelta()
    signal_type: list[DyscomSignalType] = field(default_factory=lambda: [DyscomSignalType.BI,  DyscomSignalType.EMG_1])
    sync_signal: bool = False
    filter = DyscomFilterType.FILTER_OFF
    flags: set[DyscomInitFlag] = field(default_factory=lambda: {DyscomInitFlag.ENABLE_LIVE_DATA_MODE})


    def get_data(self) -> bytes:
        """Convert information to bytes"""

        if len(self.proband_name) > 128:
            raise ValueError(f"Proband name must be shorter than 129 {self.proband_name}")
        if len(self.investigator_name) > 128:
            raise ValueError(f"Investigator name must be shorter than 129 {self.investigator_name}")
        if len(self.proband_number) > 36:
            raise ValueError(f"Proband number must be shorter than 37 {self.proband_number}")


        bb = ByteBuilder()
        bb.append_bytes(self.register_map_ads129x.get_data())
        bb.append_bytes(DyscomHelper.datetime_to_bytes(self.start_time))
        bb.append_bytes(DyscomHelper.datetime_to_bytes(self.system_time))
        bb.append_bytes(DyscomHelper.str_to_bytes(self.proband_name, 129))
        bb.append_bytes(DyscomHelper.str_to_bytes(self.investigator_name, 129))
        bb.append_bytes(DyscomHelper.str_to_bytes(self.proband_number, 37))
        bb.append_value(len(self.signal_type), 2, True)
        bb.append_value(self.duration.seconds, 4, True)
        for x in range(8):
            bb.append_byte(self.signal_type[x] if x < len(self.signal_type) else DyscomSignalType.UNUSED)
        bb.append_byte(0)
        bb.append_byte(1 if self.sync_signal else 0)
        bb.append_byte(self.filter)
        flags = 0
        for x in self.flags:
            flags |= 1 << x
        bb.append_byte(flags)

        return bb.get_bytes()


    def set_data(self, data: bytes):
        """Convert bytes to information"""
