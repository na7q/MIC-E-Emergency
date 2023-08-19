import socket
import aprslib
import datetime
import subprocess
import threading
import time

APRS_IS_HOST = 'rotate.aprs2.net'
APRS_IS_PORT = 14580
APRS_FILTER = 'b/CALL-*'
APRS_CALLSIGN = 'CALL-E'
APRS_PASSCODE = 'PASS'
MESSAGE_COUNTER = 1  # Initialize the message counter

FROM_CALLSIGN = 'CALL' #This can be different from the login call. And is used for the SMS gateway from callsign

# Declare the global aprs_socket
aprs_socket = None

# Declare socket_ready as a global variable
socket_ready = False

def send_curl_request(destination_callsign, current_time):
    curl_message = "Emergency Beacon Detected from {} at {}".format(destination_callsign, current_time)
    curl_command = "curl -d '{}' URL HERE".format(curl_message)
    print(curl_command)
    
    try:
        subprocess.run(curl_command, shell=True, check=True)
        print("Executed curl command successfully.")
    except subprocess.CalledProcessError as e:
        print("Error executing curl command:", e)

def send_aprs_packet(aprs_socket, destination_callsign):
    global MESSAGE_COUNTER
    current_time = datetime.datetime.now().strftime("%H:%M:%S")  # Get current time in HH:MM:SS format
    #APRS format requires 9 characters between :: and : Use spaces after the callsign if characters are less than 9 total. It MUST equal 9!
    aprs_message = "{}>APRS::CALL     :Emergency Beacon Detected from {} at {}{{{:d}\r\n".format(FROM_CALLSIGN, destination_callsign, current_time, MESSAGE_COUNTER)
    aprs_socket.sendall(aprs_message.encode())
    print("Sent APRS packet to {}: {} Message {}".format(destination_callsign, current_time, MESSAGE_COUNTER))
    MESSAGE_COUNTER += 1
    print("CURL SEND")
    send_curl_request(destination_callsign, current_time)

def receive_aprs_messages():
    global socket_ready, aprs_socket  # Declare that you're using the global variables

    aprs_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    aprs_socket.connect((APRS_IS_HOST, APRS_IS_PORT))
    print("Connected to APRS server with callsign: {}".format(APRS_CALLSIGN))

    login_str = 'user {} pass {} vers MicE-Gateway 0.1b\r\n'.format(APRS_CALLSIGN, APRS_PASSCODE)
    filter_command = '#filter {}\r\n'.format(APRS_FILTER)
    aprs_socket.sendall(login_str.encode())
    aprs_socket.sendall(filter_command.encode())
    print("Sent login information and filter command.")
    
    # Set the socket_ready flag to indicate that the socket is ready for keepalives
    socket_ready = True

    buffer = b""  # Use bytes buffer
    try:
        while True:
            data = aprs_socket.recv(1024)
            if not data:
                break
            
            buffer += data  # Append received bytes to the buffer
            lines = buffer.split(b'\n')

            for line in lines[:-1]:
                if line.startswith(b'#'):
                    continue

                print("Received raw APRS packet:", line)

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
        
def send_keepalive():
    global socket_ready, aprs_socket  # Declare that you're using the global variables
    
    while True:
        try:
            if socket_ready:        
                # Send a keepalive packet to the APRS server
                keepalive_packet = '#\r\n'
                aprs_socket.sendall(keepalive_packet.encode())
                print("Sent keepalive packet.")
        except Exception as e:
            print("Error sending keepalive:", str(e))
        time.sleep(30)  # Send keepalive every 30 seconds
        

if __name__ == "__main__":
    # Start a separate thread for sending keepalive packets
    keepalive_thread = threading.Thread(target=send_keepalive)
    keepalive_thread.start()
    
    receive_aprs_messages()

