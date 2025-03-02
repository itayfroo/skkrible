import socket
import threading
import time
import pygame
import json
import random
import sys
import tkinter as tk

pygame.init()

# Set up the screen
screen_width = 600
screen_height = 500  # Increased height to make room for the chat box
screen = pygame.display.set_mode((screen_width, screen_height))
pygame.display.set_caption("Drawing App with Chat")

# Load words from "words.json"
with open('words.json', 'r') as file:
    data = json.load(file)
    words = data['drawable_words']

# Randomly select 3 words
random_words = random.sample(words, 3)

# Button settings
button_width = 200
button_height = 50
button_color = (100, 200, 255)
text_color = (0, 0, 0)
font = pygame.font.Font(None, 36)

# Set up the input box for chat
input_box = pygame.Rect(20, screen_height - 50, screen_width - 40, 40)
text = ''
messages = []

# Flag for whether we are in drawing mode
in_drawing_mode = False
current_word = random_words[0]  # Default to the first random word


class GameServer:
    def __init__(self):
        self.clients = []  # List of tuples (name, port)
        self.CHAT_IP = "127.0.0.1"
        self.CHAT_PORT = 5555
        self.server_thread = threading.Thread(target=self.run_server)
        self.server_thread.start()
        self.chat_thread = threading.Thread(target=self.open_window)
        self.chat_thread.start()
        self.word = ""
        self.new_message = ""
        self.players = {}

    def open_window(self):
        root = tk.Tk()
        root.title("Chat Window")
        root.geometry("400x300")

        # Create a Listbox widget to display the chat messages
        self.chat_display = tk.Listbox(root, height=15, width=40, selectmode=tk.SINGLE)
        self.chat_display.pack(pady=10)

        # Entry widget to type the message
        message_entry = tk.Entry(root, width=40)
        message_entry.pack(pady=5)

        # Function to send the message
        def send_message():
            message = message_entry.get()
            if message:
                self.new_message = message  # Update the self.new_message attribute
                self.chat_display.insert(tk.END, self.new_message)  # Insert message into Listbox
                message_entry.delete(0, tk.END)

                # Append the message to the messages list for pygame
                messages.append(self.new_message)

                # Automatically scroll to the bottom of the chat
                self.chat_display.yview(tk.END)

        # Button to send a message
        send_button = tk.Button(root, text="Send", command=send_message)
        send_button.pack(pady=5)

        # Function to check for new messages and update Listbox periodically
        def check_for_new_messages():
            if self.new_message != "":
                self.chat_display.insert(tk.END, self.new_message)
                self.chat_display.yview(tk.END)
            root.after(1000, check_for_new_messages)
            self.new_message = ""

        # Start checking for new messages
        root.after(3000, check_for_new_messages)

        # Start the Tkinter event loop
        root.mainloop()

    def run_server(self):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.bind((self.CHAT_IP, self.CHAT_PORT))
        server.listen(2)  # Allow up to 2 clients for simplicity
        print("Server listening on port 5555")
        while True:
            client_socket, addr = server.accept()
            print(f"New connection from {addr}")
            client_socket.sendall("What's your name? ".encode())  # Ask for the name
            client_name = client_socket.recv(1024).decode()  # Receive the client's name
            if client_name:
                self.clients.append((client_name, addr[1]))
                self.players[client_name] = [0, False]
                print(f"Added {client_name} from port {addr[1]} to the client list")
                self.new_message = f"{client_name} has joined the game!"
                self.broadcast(f"{client_name} has joined the game!",client_socket)
            # Start a new thread to handle this client
            thread = threading.Thread(target=self.handle_client, args=(client_socket, addr))
            thread.start()

    def handle_client(self, client_socket, address):
        # Send a welcome message
        client_socket.sendall(
            "Welcome to the Drawing App! Please wait for the other players to state their names.".encode())
        name = ""
        while True:
            try:
                data = client_socket.recv(1024)
                if not data:
                    break
                for client in self.clients:
                    if client[1] == address[1]:  # Compare port (address[1])
                        name = client[0]  # Extract the name from the tuple
                        client_found = True
                        break
                if data.decode() == self.word:
                    print(f"Correct word guessed by {name}!")
                    self.new_message = f"Correct word guessed by {name}!"
                    self.players[name][0] += 1
                    self.players[name][1] = True
                else:
                    print(f"{name}: {data.decode()} + actual word: {self.word}")
                    self.new_message = f"{name}: {data.decode()}"
                # Broadcast the received message to all other clients
                print(self.players)
                self.broadcast(data, client_socket, address)
            except Exception as e:
                print(f"Error: {e}")
                break
        print(f"Connection closed: {address}")
        client_socket.close()
        self.clients.remove(
            (self.get_client_name_by_socket(client_socket), address[1]))  # Remove client by name and port

    def broadcast(self, message, sender_socket=None, address=None):
        name = ""
        for client in self.clients:
            client_name, client_port = client
            try:
                # Send message to all clients except the sender
                if sender_socket:
                    if sender_socket.getpeername()[1] != client_port:
                        client_socket = self.get_client_socket_by_port(client_port)
                        if client_socket:
                            for client in self.clients:
                                if client[1] == address[1]:  # Compare port (address[1])
                                    name = client[0]  # Extract the name from the tuple
                                    client_found = True
                                    break
                            client_socket.sendall(f"{name}: {message.decode()}".encode())
                else:
                    client_socket = self.get_client_socket_by_port(client_port)
                    if client_socket:
                        client_socket.sendall(f"Server: {message}".encode())
            except:
                pass

    def get_client_socket_by_port(self, port):
        for client in self.clients:
            client_name, client_port = client
            if client_port == port:
                return client_name  # Return the socket associated with the port
        return None

    def get_client_name_by_socket(self, socket):
        for client in self.clients:
            if client[0] == socket:
                return client[0]  # Return the name associated with the socket
        return None


# Main Pygame Loop
def main_game_loop():
    global text, messages, in_drawing_mode, current_word

    clock = pygame.time.Clock()
    running = True

    # Start chat server in background
    chat_server = GameServer()

    while running:
        screen.fill((255, 255, 255))  # Fill screen with white

        if not in_drawing_mode:
            # Draw buttons for the 3 random words
            for i, word in enumerate(random_words):
                draw_button(word, 50, 50 + i * (button_height + 20))

        draw_messages()  # Draw chat messages
        draw_input_box()  # Draw the input box for chat

        # Event handling
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.MOUSEBUTTONDOWN:
                mouse_x, mouse_y = event.pos
                for i, word in enumerate(random_words):
                    if 50 < mouse_x < 50 + button_width and 50 + i * (button_height + 20) < mouse_y < 50 + i * (
                            button_height + 20) + button_height:
                        print(f"Button clicked: {word}")
                        chat_server.word = word
                        drawing_app(chat_server)
                        chat_server.word = ""
                        in_drawing_mode = True
                        screen.fill((255, 255, 255))
                        current_word = word  # Set the word the user will draw
                        in_drawing_mode = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:  # Send the message when Enter is pressed
                    if text:
                        messages.append(text)
                        text = ''  # Clear the input box after sending
                elif event.key == pygame.K_BACKSPACE:  # Handle backspace
                    text = text[:-1]
                else:
                    text += event.unicode  # Append typed character to the text

        pygame.display.flip()  # Update the display
        clock.tick(60)  # Limit the frame rate to 60 FPS

    pygame.quit()
    sys.exit()


def draw_button(text, x, y):
    pygame.draw.rect(screen, button_color, (x, y, button_width, button_height))
    text_surface = font.render(text, True, text_color)
    text_rect = text_surface.get_rect(center=(x + button_width // 2, y + button_height // 2))
    screen.blit(text_surface, text_rect)


# Function to draw chat input box
def draw_input_box():
    pygame.draw.rect(screen, (255, 255, 255), input_box)
    txt_surface = font.render(text, True, text_color)
    screen.blit(txt_surface, (input_box.x + 5, input_box.y + 5))


# Function to display chat messages
def draw_messages():
    y_offset = 10  # Start from the top of the screen
    for message in messages[-10:]:  # Limit to the last 10 messages
        message_surface = font.render(message, True, (0, 0, 0))
        screen.blit(message_surface, (20, y_offset))
        y_offset += 30  # Add space between messages


def drawing_app(chat_server):
    screen.fill((255, 255, 255))
    drawing = False
    last_pos = None
    drawn_lines = []  # List to store drawn lines
    running = True
    start_time = time.time()
    while (running and time.time() - start_time < 60) and (chat_server.players[chat_server.clients[0][0]][1] == False or chat_server.players[chat_server.clients[1][0]][1] == False) :
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                drawing = True
                last_pos = event.pos
            elif event.type == pygame.MOUSEBUTTONUP:
                drawing = False
            elif event.type == pygame.MOUSEMOTION:
                if drawing:
                    pygame.draw.line(screen, (0, 0, 0), last_pos, event.pos, 5)
                    drawn_lines.append((last_pos, event.pos))  # Store the line
                    last_pos = event.pos

        # Redraw all the lines stored in drawn_lines list
        for line in drawn_lines:
            pygame.draw.line(screen, (0, 0, 0), line[0], line[1], 5)
        chat_server.players[chat_server.clients[0][0]][1] = False
        chat_server.players[chat_server.clients[1][0]][1] = False
        pygame.display.flip()


# Run the main game loop
if __name__ == '__main__':
    main_game_loop()
