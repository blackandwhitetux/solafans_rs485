import serial
import struct

# Configuration for the serial port
SERIAL_PORT = '/dev/ttyUSB0'  # Replace with your serial port
BAUD_RATE = 9600
TIMEOUT = 1

# Command to query the MPPT charger
QUERY_COMMAND = bytes.fromhex('01b10100000000b3')

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

    # Correct parsing for days_of_power_generation
    parsed_data['days_of_power_generation'] = struct.unpack('>I', b'\x00' + response[44:47])[0]  # Use only the last 3 bytes

    parsed_data['total_kwh_generated'] = struct.unpack('>I', response[48:52])[0] / 1000

    return parsed_data

# Function to query the MPPT charger
def query_mppt_charger():
    with serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=TIMEOUT) as ser:
        ser.write(QUERY_COMMAND)
        response = ser.read(93)
        if response:
            return parse_response(response)
        else:
            raise ValueError("No response received from MPPT charger.")

if __name__ == "__main__":
    try:
        data = query_mppt_charger()
        print("MPPT Charger Data:")
        for key, value in data.items():
            print(f"{key}: {value}")
    except Exception as e:
        print(f"Error: {e}")
