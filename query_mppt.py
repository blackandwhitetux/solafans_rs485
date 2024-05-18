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

def parse_response(response):
    if len(response) != 93:
        print(f"Unexpected response length: {len(response)}")
        return None
    return {
        'address': response[0],
        'command': response[1],
        'control_code': response[2],
        'data': response[3:91],
        'checksum': response[92]
    }

def decode_data(data):
    decoded = {}
    # Address
    decoded['address'] = data[0]
    
    # Command type
    decoded['command_type'] = data[1]
    
    # Control code
    decoded['control_code'] = data[2]
    
    # Operating status
    decoded['operating_status'] = {
        'battery_auto_id': bool(data[3] & 0x01),
        'battery_over_discharge': bool(data[3] & 0x02),
        'fan_status': bool(data[3] & 0x04),
        'temp_status': bool(data[3] & 0x08),
        'dc_output_status': bool(data[3] & 0x10),
        'int_temp_probe1': bool(data[3] & 0x20),
        'int_temp_probe2': bool(data[3] & 0x40),
        'ext_temp_probe': bool(data[3] & 0x80)
    }
    
    # Charging status
    decoded['charging_status'] = {
        'charging': bool(data[4] & 0x01),
        'equalizing_charge': bool(data[4] & 0x02),
        'tracking': bool(data[4] & 0x04),
        'floating_charge': bool(data[4] & 0x08),
        'charging_current_limit': bool(data[4] & 0x10),
        'charging_derating': bool(data[4] & 0x20),
        'remote_control_prohibits_charging': bool(data[4] & 0x40),
        'pv_overvoltage': bool(data[4] & 0x80)
    }
    
    # Control status
    decoded['control_status'] = {
        'charging_output_relay': bool(data[5] & 0x01),
        'load_output': bool(data[5] & 0x02),
        'fan': bool(data[5] & 0x04),
        'overcharge_protection': bool(data[5] & 0x10),
        'overvoltage': bool(data[5] & 0x20)
    }
    
    # Battery type
    battery_types = ["Lead acid maintenance free", "Lead acid colloid", "Lead acid liquid", "Lithium battery"]
    decoded['battery_type'] = battery_types[data[8]]
    
    # Battery ID method
    decoded['battery_id_method'] = "Auto" if data[9] == 0 else "Manual"
    
    # Number of batteries
    decoded['num_batteries'] = data[10]
    
    # Load control mode
    load_control_modes = ["Off", "Automatic", "Time control on/off", "Light control", "Remote control"]
    decoded['load_control_mode'] = load_control_modes[data[11]]
    
    # MPPT address
    decoded['mppt_address'] = data[12]
    
    # Baud rate
    baud_rates = ["1200", "2400", "4800", "9600"]
    decoded['baud_rate'] = baud_rates[data[13] - 1]
    
    # Rated voltage level (Bytes 16-17)
    rated_voltage_level = (data[16] << 8 | data[17]) / 100.0
    decoded['rated_voltage_level'] = rated_voltage_level
    
    # Upper charge voltage limit (Bytes 18-19)
    upper_charge_voltage_limit = (data[18] << 8 | data[19]) / 100.0
    decoded['upper_charge_voltage_limit'] = upper_charge_voltage_limit
    
    # Float voltage limit (Bytes 20-21)
    float_voltage_limit = (data[20] << 8 | data[21]) / 100.0
    decoded['float_voltage_limit'] = float_voltage_limit
    
    # Lower discharge voltage limit (Bytes 22-23)
    lower_discharge_voltage_limit = (data[22] << 8 | data[23]) / 100.0
    decoded['lower_discharge_voltage_limit'] = lower_discharge_voltage_limit
    
    # Hardware max charging current limit (Bytes 24-25)
    hw_max_charging_current_limit = (data[24] << 8 | data[25]) / 100.0
    decoded['hw_max_charging_current_limit'] = hw_max_charging_current_limit
    
    # Defined charge current limit (Bytes 26-27)
    defined_charge_current_limit = (data[26] << 8 | data[27]) / 100.0
    decoded['defined_charge_current_limit'] = defined_charge_current_limit
    
    # Running charge current limit (Bytes 28-29)
    running_charge_current_limit = (data[28] << 8 | data[29]) / 100.0
    decoded['running_charge_current_limit'] = running_charge_current_limit
    
    # PV Voltage (Bytes 30-31)
    pv_voltage = (data[30] << 8 | data[31]) / 10.0
    decoded['pv_voltage'] = pv_voltage
    
    # Battery Voltage (Bytes 32-33)
    battery_voltage = (data[32] << 8 | data[33]) / 100.0
    decoded['battery_voltage'] = battery_voltage
    
    # Charging Current (Bytes 34-35)
    charging_current = (data[34] << 8 | data[35]) / 100.0
    decoded['charging_current'] = charging_current
    
    # Internal Temperature 1 (Bytes 36-37)
    internal_temp1 = (data[36] << 8 | data[37]) / 10.0
    decoded['internal_temperature1'] = internal_temp1
    
    # Internal Temperature 2 (Bytes 38-39)
    internal_temp2 = (data[38] << 8 | data[39]) / 10.0
    decoded['internal_temperature2'] = internal_temp2
    
    # External Temperature 1 (Bytes 40-41)
    external_temp1 = (data[40] << 8 | data[41]) / 10.0
    decoded['external_temperature1'] = external_temp1
    
    # Days of Power Generation (Bytes 44-47)
    days_power_generation = data[44] << 24 | data[45] << 16 | data[46] << 8 | data[47]
    decoded['days_power_generation'] = days_power_generation
    
    # Total Power (Bytes 48-51)
    total_power = data[48] << 24 | data[49] << 16 | data[50] << 8 | data[51]
    decoded['total_power'] = total_power
    
    return decoded

def query_mppt(serial_connection, command):
    print(f"Sending: {command.hex()}")
    serial_connection.write(command)
    time.sleep(0.5)
    response = serial_connection.read(93)
    print(f"Received ({len(response)} bytes): {response.hex()}")
    parsed_response = parse_response(response)
    if parsed_response:
        print(f"Parsed Response: {parsed_response}")
    return parsed_response

def display_data(data):
    if data:
        decoded = decode_data(data['data'])
        for key, value in decoded.items():
            print(f"{key}: {value}")
    else:
        print(f"No valid response received")

def main():
    try:
        with serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=TIMEOUT) as ser:
            print("Querying MPPT...")

            # Query all data
            all_data_command = build_command(MPPT_ADDRESS, COMMAND_QUERY_ALL_DATA)
            all_data = query_mppt(ser, all_data_command)
            display_data(all_data)

    except serial.SerialException as e:
        print(f"Serial exception: {e}")
    except Exception as e:
        print(f"Exception: {e}")

if __name__ == "__main__":
    main()
