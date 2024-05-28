import serial
import struct
import requests
import time
from decimal import Decimal, ROUND_DOWN

# Configuration for the serial port
SERIAL_PORT = '/dev/ttyUSB0'  # Replace with your serial port
BAUD_RATE = 9600
TIMEOUT = 1

# Commands to query the MPPT chargers
QUERY_COMMAND_A = bytes.fromhex('01b10100000000b3')
QUERY_COMMAND_B = bytes.fromhex('02b10100000000b4')

# Home Assistant configuration
HA_URL = 'http://192.168.1.245:8123'
HA_TOKEN = 'your_long_lived_ha_token'
HEADERS = {
    'Authorization': f'Bearer {HA_TOKEN}',
    'Content-Type': 'application/json',
}

# Previous values to store the last known good values
previous_total_kwh_a = None
previous_total_kwh_b = None

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
    parsed_data['ext_temp'] = struct.unpack('>H', response[40:42])[0] / 10
    parsed_data['power_generated_today'] = struct.unpack('>H', response[44:47])[0] / 1000
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
def update_combined_power_sensor(charging_current_a, charging_current_b, battery_voltage_a):
    charging_current_a_dec = Decimal(str(charging_current_a))
    charging_current_b_dec = Decimal(str(charging_current_b))
    battery_voltage_a_dec = Decimal(str(battery_voltage_a))
    combined_power = (charging_current_a_dec + charging_current_b_dec) * battery_voltage_a_dec
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

# Function to update the combined total_kwh_generated sensor
def update_combined_total_kwh_sensor(total_kwh_a, total_kwh_b):
    global previous_total_kwh_a, previous_total_kwh_b

    # Check if either value is zero or None
    if total_kwh_a is None or total_kwh_a == 0:
        total_kwh_a = previous_total_kwh_a
    else:
        previous_total_kwh_a = total_kwh_a

    if total_kwh_b is None or total_kwh_b == 0:
        total_kwh_b = previous_total_kwh_b
    else:
        previous_total_kwh_b = total_kwh_b

    total_kwh_a_dec = Decimal(str(total_kwh_a))
    total_kwh_b_dec = Decimal(str(total_kwh_b))
    combined_total_kwh = total_kwh_a_dec + total_kwh_b_dec
    combined_total_kwh = combined_total_kwh.quantize(Decimal('0.001'), rounding=ROUND_DOWN)  # Truncate to three decimal places
    sensor_name = "sensor.mppt_charger_combined_total_kwh_generated"
    state = {
        'state': float(combined_total_kwh),
        'attributes': {
            'unit_of_measurement': 'kWh',  # Kilowatt-hours
            'friendly_name': 'MPPT Charger Combined Total kWh Generated',
            'state_class': 'total_increasing',
            'device_class': 'energy'
        }
    }
    response = requests.post(f"{HA_URL}/api/states/{sensor_name}", headers=HEADERS, json=state)
    if response.status_code not in (200, 201):
        print(f"Failed to update sensor {sensor_name}: {response.status_code} - {response.text}")

if __name__ == "__main__":
    while True:
        try:
            data_a = query_mppt_charger(QUERY_COMMAND_A)
            update_ha_sensors(data_a, "mppt_charger_a")

            data_b = query_mppt_charger(QUERY_COMMAND_B)
            update_ha_sensors(data_b, "mppt_charger_b")

            # Update combined power output sensor
            update_combined_power_sensor(data_a['charging_current'], data_b['charging_current'], data_a['battery_voltage'])

            # Update combined total kWh generated sensor
            update_combined_total_kwh_sensor(data_a['total_kwh_generated'], data_b['total_kwh_generated'])

            print("MPPT Charger Data A:")
            for key, value in data_a.items():
                print(f"A - {key}: {value}")

            print("MPPT Charger Data B:")
            for key, value in data_b.items():
                print(f"B - {key}: {value}")

            combined_power = (Decimal(str(data_a['charging_current'])) + Decimal(str(data_b['charging_current']))) * Decimal(str(data_a['battery_voltage']))
            combined_power = combined_power.quantize(Decimal('0.1'), rounding=ROUND_DOWN)
            print(f"Combined Power Output: {combined_power} W")

            combined_total_kwh = Decimal(str(data_a['total_kwh_generated'])) + Decimal(str(data_b['total_kwh_generated']))
            combined_total_kwh = combined_total_kwh.quantize(Decimal('0.001'), rounding=ROUND_DOWN)
            print(f"Combined Total kWh Generated: {combined_total_kwh} kWh")

        except Exception as e:
            print(f"Error: {e}")

        time.sleep(1)  # Wait for 1 second before querying again
