# solafans_rs485
Python script to read data from a solafans MPPT charger over RS485.

ALPHA CODE. STILL IN DEV AND STRICTLY WIP.

This script assumes you are using a USB > RS485 dongle which sits at /dev/ttyUSB0, I used a CH340.

chatgpt prompt:

good morning, today we are decoding a large data object returned from a solar mppt charger. we use the following code to compile a data object which is then sent to the inverter over rs485. i have a spec to decode this object. here's the code so far:

import serial
import struct
import time

# Define serial port parameters
SERIAL_PORT = '/dev/ttyUSB0'  # Adjust this to your specific serial port
BAUD_RATE = 9600
TIMEOUT = 2  # Increased timeout

# Define MPPT commands
MPPT_ADDRESS = 0x01
COMMAND_QUERY_ALL_DATA = 0xB1

def calculate_checksum(data):
    return sum(data) & 0xFF

def build_command(address, command_type):
    command = struct.pack('BBBBBBBB',
                          address, command_type, 0x01, 0x00, 0x00, 0x00, 0x00,
                          calculate_checksum([address, command_type, 0x01, 0x00, 0x00, 0x00, 0x00]))
    return command

and here's a sample of the returned data object. the spec says it is 93 bytes long.

Querying MPPT...
Sending: 01b10100000000b3
Received (93 bytes): 01b101000d000001030404040104000012c016a8164510680fa00fa00fa0046d14b0024201390000006a0000000002a0000f16d701011388190016a8000a001200010002010800000001000000050000000803000000000000000000ad

so the structure is as follows:

byte 0: the address of the mppt charger which is returning data - we will need to query multiple chargers later so this will be required
byte 1: the command type which we issued and therefore the data subset that the inverter is returning
byte 2: control code of some kind 0x01
byte 3: battery voltage good/ng 0=good 1=bad
byte 4:
