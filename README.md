# MPPT Charger Data Query and Home Assistant Integration

This repository contains two Python scripts for querying data from MPPT chargers over RS485 and integrating the data into Home Assistant. The scripts support querying two MPPT chargers and updating their respective sensors in Home Assistant.

Files

   * query_mppt.py: Script for querying MPPT charger data over RS485.
   * homeassistant_dual.py: Script for querying two MPPT chargers and updating Home Assistant sensors every second.

Features

   * Queries MPPT chargers over RS485.
   * Parses the received data according to the provided protocol.
   * Updates Home Assistant with the parsed data.
   * Supports querying two MPPT chargers and updating their respective sensors.

# Getting Started

Prerequisites

   * Python 3.x
   * pyserial library
   * requests library
   * Home Assistant with REST API enabled
   * Long-lived access token for Home Assistant

Installation

Clone the repository:

sh git clone https://github.com/blackandwhitetux/solafans_rs485.git

cd mppt-homeassistant

Install the required Python libraries:

sh pip install pyserial requests

# Configuration

Home Assistant Configuration:

* Replace YOUR_HA_URL and YOUR_LONG_LIVED_ACCESS_TOKEN in homeassistant_dual.py with your Home Assistant URL and token.

Serial Port Configuration:
* Replace '/dev/ttyUSB0' in both scripts with the appropriate serial port for your system.

# Running the Scripts

Query MPPT Charger:

sh sudo python3 query_mppt.py

Home Assistant Integration for Dual MPPT Chargers:

sh sudo python3 homeassistant_dual.py

# Protocol Description

The MPPT charger responds with 93 bytes of data. The following describes the structure and meaning of each byte in the response:

Byte	Description	Example Value

0	MPPT address	01

1	Command type	b1

2	Control code	01

3	Operating status (bitwise flags)	00

4	Charging status (bitwise flags)	0d

5	Control status	00

6-7	Reserved	0000

8	Battery type	03

9	Battery ID method	04

10	Number of batteries	04

11	Load control mode	04

12	MPPT address confirmation	01

13	Baud rate	04

14-15	Reserved	0000

16-17	Rated voltage level (2 decimal places)	12c0 (48.00V)

18-19	Upper charge voltage (2 decimal places)	16a8 (58.00V)

20-21	Float voltage limit (2 decimal places)	1645 (57.01V)

22-23	Low voltage discharge limit (2 decimal places)	1068 (42.00V)

24-25	Hardware max charging current limit (2 decimal places)	0fa0 (40.00A)

26-27	Defined charge limit (2 decimal places)	0fa0 (40.00A)

28-29	Running charging current limit (2 decimal places)	0fa0 (40.00A)

30-31	PV voltage input (1 decimal place)	046d (111.3V)

32-33	Battery voltage (2 decimal places)	14b0 (52.96V)

34-35	Charging current (2 decimal places)	0242 (5.78A)

36-37	Internal temperature sensor (1 decimal place)	0139 (31.3°C)

38-39	Internal temperature sensor 2 (if available)	0000

40-41	External temperature sensor (1 decimal place)	006a (10.6°C)

42-43	Reserved	0000

44-47	Power generated today	000002a0 (00000672 wh generated today)

48-51	Total kWh generated (3 decimal places)	000f16d7 (988.887kWh)

52-92	Extra settings and control data	N/A

# Credits

Developed by James Preston. Protocol description and script implementation provided with assistance from ChatGPT.
License

This project is licensed under the MIT License - see the LICENSE file for details.
