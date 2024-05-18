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

so the structure is as follows, where i give our data in bytes from left to right, and then the definition of each byte/bit according to the spec. i will chop off each bit of data so you can follow along.

01 byte 0: the address of the mppt charger which is returning data - we will need to query multiple chargers later so this will be required

remaining data in packet: b101000d000001030404040104000012c016a8164510680fa00fa00fa0046d14b0024201390000006a0000000002a0000f16d701011388190016a8000a001200010002010800000001000000050000000803000000000000000000ad

b1 byte 1: the command type which we issued and therefore the data subset that the inverter is returning

remaining data in packet:
01000d000001030404040104000012c016a8164510680fa00fa00fa0046d14b0024201390000006a0000000002a0000f16d701011388190016a8000a001200010002010800000001000000050000000803000000000000000000ad

01 byte 2: control code of some kind 0x01

remaining data in packet:

000d000001030404040104000012c016a8164510680fa00fa00fa0046d14b0024201390000006a0000000002a0000f16d701011388190016a8000a001200010002010800000001000000050000000803000000000000000000ad

00 byte 3: operating status. 
hex data: 00 binary data= 00000000 therefore no faults as per the below 
0 bit 0: 0, battery auto identification passed, 1 = failed 
0 bit 1: battery over discharge protection, 0=good 1=battery over discharge enabled (fault) 
0 bit 2: fan status 0= normal 1= fan failure. 
0 bit 3: temp status. 0 = normal 1= fault. 
0 bit 4: dc output status 0 normal 1 short circuit (fault)
0 bit 5: int temp probe 1 status 0 good 1 fault
0 bit 6: int temp probe 2 status 0 good 1 fault
0 bit 7: ext temp probe status 0 good 1 fault

remaining data in packet: 
0d000001030404040104000012c016a8164510680fa00fa00fa0046d14b0024201390000006a0000000002a0000f16d701011388190016a8000a001200010002010800000001000000050000000803000000000000000000ad

0d byte 4: 

Bit	Description	Value Explanation	Value in Sample Data (0d = 00001101)
1 bit 0: Charging status	0 = stop charging; 1 = charging	1 (charging)
0 bit 1: Equalizing charge	1 = valid	0 (not valid)
1 bit 2: Tracking	1 = valid	1 (valid)
1 bit 3: Floating charge	1 = valid	1 (valid)
0 bit 4: Charging current limit	1 = valid	0 (not valid)
0 bit 5: Charging derating	1 = valid	0 (not valid)
0 bit 6: Remote control prohibits charging	1 = valid	0 (not valid)
0 bit 7: PV overvoltage	1 = valid	0 (not valid)

remaining data in packet: 
000001030404040104000012c016a8164510680fa00fa00fa0046d14b0024201390000006a0000000002a0000f16d701011388190016a8000a001200010002010800000001000000050000000803000000000000000000ad

00 byte 5:
