import socket
import logging
import threading
import time
import random
import os
from datetime import datetime
from enum import Enum

package_id = 1   
class AckState(Enum):
    WAITING= 0
    RECEIVING = 1




receiver_ip = '10.150.16.191'
receiver_port = 5000
package_sizes = [64, 128]
connection_retry_delay = 5

global sending_time
sending_time = None
global data_package
data_package = None
global sender_socket
sender_socket = None

package_data = {}
lock = threading.Lock()

global current_state
current_state = AckState.WAITING
global receiving_chars
receiving_chars = []

def state_machine(char):
    global current_state
    global receiving_chars
    if current_state == AckState.WAITING:
         if char == 's':
            # Delete 's' from the string and transition to the next state
            current_state = AckState.RECEIVING
            
            
    elif current_state == AckState.RECEIVING:
            if char == 'e':
                package_id=''.join(receiving_chars)
                receiving_chars=[]
                print(f"Ack {package_id} received")
                logging.info(package_id)
                packageKey = "K-" + str(package_id)
                with lock:
                    if packageKey in package_data:
                            del package_data[packageKey]
                current_state = AckState.WAITING
            else:
                receiving_chars.append(char)


def generate_data_package(package_id, data):
    # Convert package ID to a 4-byte representation
    package_id_bytes = package_id.to_bytes(4, byteorder='big')

    # Combine package ID and data
    data_package = package_id_bytes + data.encode()

    return data_package



def connect_to_receiver():
    sender_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sender_socket.connect((receiver_ip, receiver_port))
    return sender_socket

data_ready_event = threading.Event()

def send_data_package(sender_socket, package_id):
    global sending_time
    global data_package
    
    package_size = package_sizes[package_id % len(package_sizes)]
    data = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz', k=package_size))

    data_package = generate_data_package(package_id, data)

    sender_socket.sendall(data_package)

    time.sleep(0.33)

    return data_package, sending_time

def ack_handling_thread(sender_socket):
    
    while True:
        sender_socket.settimeout(5)
        ack = sender_socket.recv(1024)
        receiving_time = datetime.now()
        ack_message = ack.decode()
        for char in ack_message:
            state_machine(char)

        
        # Clear the event and wait for the event to be set again in the main loop
        data_ready_event.clear()
        data_ready_event.set()

def check_timeout_thread():
    timeout_lst =[]
    while True:
       

        with lock:
            current_time = datetime.now()
            
            for package_id_1, sending_time in package_data.items():
                time_difference = (current_time - sending_time).total_seconds()
                
                if time_difference > 5:
                    timeout_lst.append(package_id_1)
                    print(f"Packet {package_id_1} timed out " + "Time:" + str (time_difference))
            for package_id_2 in timeout_lst:
                if package_id_2 in package_data:
                     del package_data[package_id_2]

       
        
def main():
    global package_id
    global sending_time
    global data_package
    
    script_directory = os.path.dirname(os.path.abspath(__file__))
    parent_directory = os.path.dirname(script_directory)
    logs_directory = os.path.join(parent_directory, 'logs')
    os.makedirs(logs_directory, exist_ok=True)
    log_file = os.path.join(logs_directory, 'sender.log')

    logging.basicConfig(
        filename=log_file,
        level=logging.INFO,
        format='%(asctime)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    sender_socket = connect_to_receiver()
    cleanup_thread_obj = threading.Thread(target=check_timeout_thread)
    cleanup_thread_obj.start()
    ack_thread = threading.Thread(target=ack_handling_thread, args=(sender_socket,))
    ack_thread.start()
    
    while True:
        try:
            if sender_socket is None or sender_socket.fileno() == -1:
                sender_socket = connect_to_receiver()
                
            sending_time = datetime.now()
            with lock:
                package_data["K-" + str(package_id)] = sending_time
            data_package, sending_time = send_data_package(sender_socket, package_id)
            log_message = f"Package ID: {package_id}, Sending Time: {sending_time}"
            logging.info(log_message)
            print(log_message) 
            package_id += 1
            

            # Event'i işaretle
            data_ready_event.set()

        except Exception as e:
            print(f"Error occurred: {e}")
            time.sleep(connection_retry_delay)

if __name__ == "__main__":
    main()
