import socket
import threading


def receive_messages(client_socket):
    while True:
        try:
            message = client_socket.recv(2048)
            if not message:
                break
            print(message.decode())
        except:
            break


client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.connect(("127.0.0.1", 5555))

# Receive the prompt from the server asking for the client's name
print(client.recv(1024).decode())

# Send the client's name to the server
client.sendall(input().encode())

# Start a thread to listen for incoming messages
thread = threading.Thread(target=receive_messages, args=(client,))
thread.start()

while True:
    message = input()
    if message.lower() == "exit":
        break
    client.sendall(message.encode())

client.close()
