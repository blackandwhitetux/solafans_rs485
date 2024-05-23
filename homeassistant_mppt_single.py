import serial
import struct
import requests
import time
from decimal import Decimal, ROUND_DOWN

# Configuration for the serial port
SERIAL_PORT = '/dev/ttyUSB0'  # Replace with your serial port
BAUD_RATE = 9600
TIMEOUT = 1

# Command to query the MPPT charger
QUERY_COMMAND = bytes.fromhex('01b10100000000b3')

# Home Assistant configuration
HA_URL = 'http://192.168.1.x:8123'
HA_TOKEN = 'your_key_here'
HEADERS = {
    'Authorization': f'Bearer {HA_TOKEN}',
    'Content-Type': 'application/json',
}

# Previous value to store the last known good value
previous_total_kwh = None

# Function to parse the response from the MPPT charger
def parse_response(response):
    if len(response) < 93:
        raise ValueError("Response length is shorter than expected.")

    parsed_data = {}
    parsed_data['mppt_address'] = response[0]
    parsed_data['command_type'] = response[1]
    parsed_data['control_code'] = response[2]

    # Operating status
    operating_status = response[3]
    parsed_data['operating_status'] = {
        'battery_auto_identification': bool(operating_status & 0b00000001),
        'battery_over_discharge_protection': bool(operating_status & 0b00000010),
        'fan_status': bool(operating_status & 0b00000100),
        'temp_status': bool(operating_status & 0b00001000),
        'dc_output_status': bool(operating_status & 0b00010000),
        'int_temp_probe_1_status': bool(operating_status & 0b00100000),
        'int_temp_probe_2_status': bool(operating_status & 0b01000000),
        'ext_temp_probe_status': bool(operating_status & 0b10000000)
    }

    # Charging status
    charging_status = response[4]
    parsed_data['charging_status'] = {
        'charging': bool(charging_status & 0b00000001),
        'equalizing_charge': bool(charging_status & 0b00000010),
        'tracking': bool(charging_status & 0b00000100),
        'floating_charge': bool(charging_status & 0b00001000),
        'charging_current_limit': bool(charging_status & 0b00010000),
        'charging_derating': bool(charging_status & 0b00100000),
        'remote_control_prohibits_charging': bool(charging_status & 0b01000000),
        'pv_overvoltage': bool(charging_status & 0b10000000)
    }

    parsed_data['control_status'] = response[5]
    parsed_data['battery_type'] = response[8]
    parsed_data['battery_id_method'] = response[9]
    parsed_data['number_of_batteries'] = response[10]
    parsed_data['load_control_mode'] = response[11]
    parsed_data['mppt_address_confirm'] = response[12]
    parsed_data['baud_rate'] = response[13]

    # Battery and voltage readings
    parsed_data['rated_voltage_level'] = struct.unpack('>H', response[16:18])[0] / 100
    parsed_data['upper_charge_voltage'] = struct.unpack('>H', response[18:20])[0] / 100
    parsed_data['float_voltage_limit'] = struct.unpack('>H', response[20:22])[0] / 100
    parsed_data['low_voltage_discharge_limit'] = struct.unpack('>H', response[22:24])[0] / 100
    parsed_data['hardware_max_charging_current_limit'] = struct.unpack('>H', response[24:26])[0] / 100
    parsed_data['defined_charge_limit'] = struct.unpack('>H', response[26:28])[0] / 100
    parsed_data['running_charging_current_limit'] = struct.unpack('>H', response[28:30])[0] / 100
    parsed_data['pv_voltage_in'] = struct.unpack('>H', response[30:32])[0] / 10
    parsed_data['battery_voltage'] = struct.unpack('>H', response[32:34])[0] / 100
    parsed_data['charging_current'] = struct.unpack('>H', response[34:36])[0] / 100
    parsed_data['int_temp'] = struct.unpack('>H', response[36:38])[0] / 10

    # Correct parsing for ext_temp
    parsed_data['ext_temp'] = struct.unpack('>H', response[40:42])[0] / 10

    parsed_data['total_kwh_generated'] = struct.unpack('>I', response[48:52])[0] / 1000

    return parsed_data

# Function to query the MPPT charger
def query_mppt_charger(command):
    with serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=TIMEOUT) as ser:
        ser.write(command)
        response = ser.read(93)
        if response:
            return parse_response(response)
        else:
            raise ValueError("No response received from MPPT charger.")

# Function to update Home Assistant sensors
def update_ha_sensors(data, entity_prefix):
    units = {
        'rated_voltage_level': 'V',
        'upper_charge_voltage': 'V',
        'float_voltage_limit': 'V',
        'low_voltage_discharge_limit': 'V',
        'hardware_max_charging_current_limit': 'A',
        'defined_charge_limit': 'A',
        'running_charging_current_limit': 'A',
        'pv_voltage_in': 'V',
        'battery_voltage': 'V',
        'charging_current': 'A',
        'int_temp': '°C',
        'ext_temp': '°C',
        'total_kwh_generated': 'kWh'
    }

    for key, value in data.items():
        sensor_name = f"sensor.{entity_prefix}_{key}"
        unit = units.get(key, '')
        attributes = {
            'unit_of_measurement': unit,
            'friendly_name': key.replace('_', ' ').title()
        }

        if key == 'total_kwh_generated':
            attributes.update({
                'state_class': 'total_increasing',
                'device_class': 'energy'
            })

        state = {
            'state': value,
            'attributes': attributes
        }

        response = requests.post(f"{HA_URL}/api/states/{sensor_name}", headers=HEADERS, json=state)
        if response.status_code not in (200, 201):
            print(f"Failed to update sensor {sensor_name}: {response.status_code} - {response.text}")

# Function to update the combined power output sensor
def update_combined_power_sensor(charging_current, battery_voltage):
    charging_current_dec = Decimal(str(charging_current))
    battery_voltage_dec = Decimal(str(battery_voltage))
    combined_power = charging_current_dec * battery_voltage_dec
    combined_power = combined_power.quantize(Decimal('0.1'), rounding=ROUND_DOWN)  # Truncate to one decimal place
    sensor_name = "sensor.mppt_charger_combined_power"
    state = {
        'state': float(combined_power),
        'attributes': {
            'unit_of_measurement': 'W',  # Watts
            'friendly_name': 'MPPT Charger Combined Power',
            'state_class': 'measurement',
            'device_class': 'power'
        }
    }
    response = requests.post(f"{HA_URL}/api/states/{sensor_name}", headers=HEADERS, json=state)
    if response.status_code not in (200, 201):
        print(f"Failed to update sensor {sensor_name}: {response.status_code} - {response.text}")

if __name__ == "__main__":
    while True:
        try:
            data = query_mppt_charger(QUERY_COMMAND)
            update_ha_sensors(data, "mppt_charger")

            # Update combined power output sensor
            update_combined_power_sensor(data['charging_current'], data['battery_voltage'])

            print("MPPT Charger Data:")
            for key, value in data.items():
                print(f"{key}: {value}")

            combined_power = Decimal(str(data['charging_current'])) * Decimal(str(data['battery_voltage']))
            combined_power = combined_power.quantize(Decimal('0.1'), rounding=ROUND_DOWN)
            print(f"Combined Power Output: {combined_power} W")

        except Exception as e:
            print(f"Error: {e}")

        time.sleep(1)  # Wait for 1 second before querying again
