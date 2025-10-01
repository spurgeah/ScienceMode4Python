"""Provides a class for a serial connection"""

import os
import serial
import serial.tools.list_ports
import serial.tools.list_ports_common

from .connection import Connection


class SerialPortConnection(Connection):
    """Serial connection class"""


    @staticmethod
    def list_ports() -> list[serial.tools.list_ports_common.ListPortInfo]:
        """Returns a list of all serial ports"""
        return serial.tools.list_ports.comports()


    @staticmethod
    def list_science_mode_device_ports() -> list[serial.tools.list_ports_common.ListPortInfo]:
        """Returns a list of all serial ports with a science mode device"""
        ports = SerialPortConnection.list_ports()
        # science mode devices (P24/I24) have an STM32 mcu and these are
        # default values for USB CDC devices
        filtered_ports = list(filter(lambda x: x.vid == 0x0483 and x.pid == 0x5740, ports))
        return filtered_ports


    def __init__(self, port: str, baudrate: int = 3000000, **kwargs):
        """Create a SerialPortConnection.

        Args:
            port: Serial port name (e.g., 'COM3' or '/dev/ttyUSB0').
            baudrate: Baud rate to use (defaults to 3000000).
            **kwargs: Additional keyword args forwarded to serial.Serial.
        """
        # Construct the underlying pyserial Serial object with provided
        # parameters. Use explicit port and timeout; allow callers to pass
        # other serial.Serial keyword args via **kwargs.
        self._ser = serial.Serial(port=port, baudrate=baudrate, timeout=0, **kwargs)


    def open(self):
        self._ser.open()

        if os.name == "nt":
            self._ser.set_buffer_size(4096*128)


    def close(self):
        self._ser.close()


    def is_open(self) -> bool:
        return self._ser.is_open


    def write(self, data: bytes):
        super().write(data)
        self._ser.write(data)


    def clear_buffer(self):
        self._ser.reset_input_buffer()


    def _read_intern(self) -> bytes:
        result = bytes()
        if self._ser.in_waiting > 0:
            result = self._ser.read_all()

        return result
