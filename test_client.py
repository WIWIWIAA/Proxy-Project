import socket
import time

def test_proxy(host='localhost', port=8081, url='http://example.com/'):
    """Test client for proxy server with timeout handling."""
    # Create a socket and connect to the proxy
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.settimeout(15)  # 15 second timeout
    
    try:
        client_socket.connect((host, port))
        print(f"Connected to proxy at {host}:{port}")
        
        # Send an HTTP request
        request = f"GET {url} HTTP/1.1\r\nHost: example.com\r\n\r\n"
        print(f"Sending request:\n{request}")
        client_socket.sendall(request.encode())
        
        # Receive the response with timeout handling
        response = b""
        start_time = time.time()
        
        while True:
            try:
                data = client_socket.recv(4096)
                if not data:
                    break
                response += data
                
                # Don't wait forever
                if time.time() - start_time > 15:
                    print("Response taking too long - breaking")
                    break
                    
            except socket.timeout:
                print("Socket timeout - assuming response is complete")
                break
            except Exception as e:
                print(f"Error receiving data: {e}")
                break
        
        # Print the response
        print(f"\nReceived {len(response)} bytes in response:")
        print("-" * 40)
        if response:
            # Try to decode as UTF-8, but fallback on latin-1 if there are encoding issues
            try:
                print(response.decode('utf-8', errors='replace'))
            except:
                print(response.decode('latin-1', errors='replace'))
        else:
            print("No response received")
        print("-" * 40)
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        # Close the socket
        client_socket.close()
        print("Connection closed")

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