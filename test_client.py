import socket

def test_proxy(host='localhost', port=8081, url='http://example.com/'):
    """Test client for proxy server."""
    # Create a socket and connect to the proxy
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        client_socket.connect((host, port))
        print(f"Connected to proxy at {host}:{port}")
        
        # Send an HTTP request
        request = f"GET {url} HTTP/1.1\r\nHost: example.com\r\n\r\n"
        print(f"Sending request:\n{request}")
        client_socket.sendall(request.encode())
        
        # Receive the response
        response = b""
        while True:
            data = client_socket.recv(4096)
            if not data:
                break
            response += data
        
        # Print the response
        print("\nReceived response:")
        print("-" * 40)
        print(response.decode(errors='replace'))
        print("-" * 40)
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        # Close the socket
        client_socket.close()

if __name__ == "__main__":
    import sys
    
    # Default values
    proxy_host = 'localhost'
    proxy_port = 8081
    target_url = 'http://example.com/'
    
    # Allow command-line arguments to override defaults
    if len(sys.argv) > 1:
        proxy_port = int(sys.argv[1])
    if len(sys.argv) > 2:
        target_url = sys.argv[2]
    
    # Run the test
    test_proxy(proxy_host, proxy_port, target_url)