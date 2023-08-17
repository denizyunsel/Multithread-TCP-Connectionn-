import logging
from datetime import datetime
import socket
import time
import os

receiver_ip = '0.0.0.0' #'10.150.16.50'
receiver_port = 5000
max_connection_retries = 5
connection_retry_delay = 5  # Retry the connection after waiting for 5 seconds
connection_backlog = 1000  # Set a reasonably high value to accommodate many simultaneous connections

def main():

    # Get the absolute path of the directory where the script is located
    script_directory = os.path.dirname(os.path.abspath(__file__)) 

    # Construct the path to the parent directory (logs directory is here)
    parent_directory = os.path.dirname(script_directory)

    # Construct the path to the logs directory
    logs_directory = os.path.join(parent_directory, 'logs')

    # Create the logs directory if it doesn't exist
    os.makedirs(logs_directory, exist_ok=True)

    # Construct the path to the log file
    log_file = os.path.join(logs_directory, 'receiver.log')

    # Configure logging
    logging.basicConfig(
        filename=log_file,
        level=logging.INFO,
        format='%(asctime)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    connection_retries = 0
    last_received_package_id = 0

    while connection_retries < max_connection_retries:
        try:
            # Create a TCP socket with specified connection backlog
            receiver_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            receiver_socket.bind((receiver_ip, receiver_port))
            receiver_socket.listen(connection_backlog)  # Set the connection backlog

            print("Receiver is ready to receive data packages.")
            logging.info("Receiver is ready to receive data packages.")

            expected_package_id = last_received_package_id + 1

            while True:
                # Accept incoming connection
                connection, address = receiver_socket.accept()

                try:
                    while True:
                        # Receive data from the sender (128 bytes at a time)
                        data = connection.recv(132)

                        if not data:
                            break

                        # Check the package ID
                        package_id = int.from_bytes(data[:4], byteorder='big')

                        if package_id > last_received_package_id:
                            # Process the received data (you can add your logic here)
                            print(f"Received package with ID {package_id} and size {len(data) - 4} bytes")
                            logging.info(f"Received package with ID {package_id} and size {len(data) - 4} bytes")
                            last_received_package_id = package_id

                            # Send acknowledg(ment to the sender
                            ack_msg = 's' + str(package_id) + 'e'
                            connection.sendall(ack_msg.encode())
                            
                            expected_package_id += 1
                        elif package_id > expected_package_id:
                            # Request the sender to resend missing packages
                            print(f"Lost package {expected_package_id}. Requesting resend.")
                            logging.info(f"Lost package {expected_package_id}. Requesting resend.")
                            connection.sendall(b"Resend")
                        else:
                            # Ignore duplicate or out-of-order packages
                            print(f"Ignored duplicate or out-of-order package with ID {package_id}")
                            logging.info(f"Ignored duplicate or out-of-order package with ID {package_id}")

                except ConnectionResetError:
                    print("Connection closed by the sender.")
                    logging.info("Connection closed by the sender.")
                finally:
                    connection.close()
        except (socket.error, OSError) as e:
            print(f"Connection error: {e}")
            logging.error(f"Connection error: {e}")
            print(f"Retrying after {connection_retry_delay} seconds...")
            logging.info(f"Retrying after {connection_retry_delay} seconds...")
            time.sleep(connection_retry_delay)
            connection_retries += 1
        else:
            # If the connection is successful, reset the retry count
            connection_retries = 0

if __name__ == "__main__":
    main()
