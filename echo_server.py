import socket

# Create and set up server socket
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server_socket.bind(('localhost', 8888))
server_socket.listen(1)

print("Echo server running on port 8888...")

while True:
    print("Waiting for connection...")
    client_socket, addr = server_socket.accept()
    print(f"Connection from {addr}")
    
    # Echo back whatever is received
    data = client_socket.recv(1024)
    print(f"Received: {data.decode()}")
    client_socket.send(b"You sent: " + data)
    
    client_socket.close()