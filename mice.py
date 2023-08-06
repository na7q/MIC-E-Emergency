import socket
import aprslib
import datetime

APRS_IS_HOST = 'rotate.aprs2.net'
APRS_IS_PORT = 14580
APRS_FILTER = 'b/CALL-*'
APRS_CALLSIGN = 'CALL-E'
APRS_PASSCODE = 'PASS'
MESSAGE_COUNTER = 1  # Initialize the message counter

def send_aprs_packet(aprs_socket, destination_callsign):
    global MESSAGE_COUNTER
    current_time = datetime.datetime.now().strftime("%H:%M:%S")  # Get current time in HH:MM:SS format
    aprs_message = "{}>APRS::SMSGTE   :@1234567890 Emergency Beacon Detected from {} at {}{{{:d}\r\n".format(APRS_CALLSIGN, destination_callsign, current_time, MESSAGE_COUNTER)
    aprs_socket.sendall(aprs_message.encode())
    print("Sent APRS packet to {}: {} Message {}".format(destination_callsign, current_time, MESSAGE_COUNTER))
    MESSAGE_COUNTER += 1

def receive_aprs_messages():
    aprs_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    aprs_socket.connect((APRS_IS_HOST, APRS_IS_PORT))
    print("Connected to APRS server with callsign: {}".format(APRS_CALLSIGN))

    login_str = 'user {} pass {} vers MicE-Gateway 0.1b\r\n'.format(APRS_CALLSIGN, APRS_PASSCODE)
    filter_command = '#filter {}\r\n'.format(APRS_FILTER)
    aprs_socket.sendall(login_str.encode())
    aprs_socket.sendall(filter_command.encode())
    print("Sent login information and filter command.")

    buffer = ""
    try:
        while True:
            data = aprs_socket.recv(1024)
            if not data:
                break
            
            buffer += data.decode()
            lines = buffer.split('\n')

            for line in lines[:-1]:
                if line.startswith('#'):
                    continue

                print("Received raw APRS packet: {}".format(line.strip()))

                try:
                    # Initialize an APRS object and parse the received packet
                    aprs_packet = aprslib.parse(line.strip())
                    
                    # Check if mtype is "M1" (En Route)
                    if 'mtype' in aprs_packet and aprs_packet['mtype'] == 'Emergency':
                        print("En Route APRS packet:")
                        print("Source callsign:", aprs_packet['from'])
                        if 'message' in aprs_packet:
                            print("Message:", aprs_packet['message'])
                        if 'latitude' in aprs_packet and 'longitude' in aprs_packet:
                            print("Coordinates:", aprs_packet['latitude'], ",", aprs_packet['longitude'])
                        print("mtype:", aprs_packet['mtype'])
                        
                        # Send a response APRS packet using the same socket
                        send_aprs_packet(aprs_socket, aprs_packet['from'])

                except Exception as e:
                    print("Error parsing packet:", e)
                
            buffer = lines[-1]  # Save the last (potentially incomplete) line for the next iteration
                
                
    except KeyboardInterrupt:
        print("Stopping APRS reception.")
    finally:
        aprs_socket.close()

if __name__ == "__main__":
    receive_aprs_messages()
