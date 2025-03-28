#!/usr/bin/env python3
"""
Test script for BONUS FEATURE 3: Support for Custom Ports
This script tests if your proxy correctly handles URLs with custom ports:
1. Starts a test server on multiple ports
2. Makes requests to those ports through the proxy
3. Verifies the proxy connects to the correct ports
"""

import os
import socket
import time
import sys
import threading
import http.server
import socketserver
import shutil

# Proxy settings
PROXY_HOST = 'localhost'
PROXY_PORT = 8081  # Update this if you're using a different port

# Test settings
TEST_HOST = 'localhost'
TEST_PORTS = [8000, 8082, 8083]  # We'll test with these ports
TEST_DIR = './testserver-ports'

class CustomPortHandler(http.server.SimpleHTTPRequestHandler):
    """Custom HTTP handler that includes the port in the response."""
    
    def do_GET(self):
        """Handle GET requests."""
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        
        # Include the server port in the response
        response = f"""
        <html>
        <head><title>Port {self.server.server_port} Test</title></head>
        <body>
            <h1>Server on Port {self.server.server_port}</h1>
            <p>This response comes from the server running on port {self.server.server_port}.</p>
        </body>
        </html>
        """
        
        self.wfile.write(response.encode())
    
    def log_message(self, format, *args):
        """Override to minimize output."""
        return

def start_test_server(port):
    """Start a test server on the specified port."""
    handler = CustomPortHandler
    httpd = socketserver.TCPServer((TEST_HOST, port), handler)
    
    print(f"Starting test server at http://{TEST_HOST}:{port}")
    server_thread = threading.Thread(target=httpd.serve_forever)
    server_thread.daemon = True
    server_thread.start()
    
    return httpd

def test_port(port):
    """Test if the proxy correctly handles a specific port."""
    print(f"\nTesting connection to port {port}")
    print("-" * 50)
    
    # Connect to proxy
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.settimeout(10)
    
    try:
        # Connect to the proxy
        client_socket.connect((PROXY_HOST, PROXY_PORT))
        print(f"Connected to proxy at {PROXY_HOST}:{PROXY_PORT}")
        
        # Request from the specified port
        request = f"GET http://{TEST_HOST}:{port}/ HTTP/1.1\r\nHost: {TEST_HOST}\r\n\r\n"
        print(f"Sending request: GET http://{TEST_HOST}:{port}/")
        client_socket.sendall(request.encode())
        
        # Receive response
        response = b""
        while True:
            try:
                data = client_socket.recv(4096)
                if not data:
                    break
                response += data
            except socket.timeout:
                print("Socket timeout - assuming response is complete")
                break
        
        # Close connection
        client_socket.close()
        
        # Check if the response contains the correct port
        response_str = response.decode('utf-8', errors='replace')
        
        print("\nResponse excerpt:")
        print("-" * 30)
        lines = response_str.split('\n')
        for line in lines[:20]:  # Print the first 20 lines
            if line.strip():
                print(line.strip())
        print("-" * 30)
        
        if f"Server on Port {port}" in response_str:
            print(f"✓ TEST PASSED: Proxy correctly connected to port {port}")
            return True
        else:
            print(f"✗ TEST FAILED: Response doesn't confirm connection to port {port}")
            return False
    
    except Exception as e:
        print(f"Error: {e}")
        return False
    finally:
        # Close the socket if it's still open
        try:
            client_socket.close()
        except:
            pass

def test_custom_ports():
    """Test if the proxy correctly handles URLs with custom ports."""
    print("\nTesting BONUS FEATURE 3: Support for Custom Ports")
    print("=" * 70)
    
    # Start test servers on different ports
    servers = []
    for port in TEST_PORTS:
        try:
            server = start_test_server(port)
            servers.append((port, server))
        except Exception as e:
            print(f"Failed to start server on port {port}: {e}")
    
    if not servers:
        print("Could not start any test servers. Aborting test.")
        return
    
    # Test each port
    results = []
    for port, _ in servers:
        result = test_port(port)
        results.append((port, result))
    
    # Summary
    print("\nTest Results Summary:")
    print("=" * 70)
    all_passed = True
    for port, result in results:
        status = "PASSED" if result else "FAILED"
        print(f"Port {port}: {status}")
        if not result:
            all_passed = False
    
    if all_passed:
        print("\nALL TESTS PASSED: The proxy correctly handles custom ports!")
    else:
        print("\nSOME TESTS FAILED: The proxy may not be handling custom ports correctly.")
    
    # Stop all servers
    for _, server in servers:
        server.shutdown()

if __name__ == "__main__":
    # Check if the proxy is running
    try:
        test_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        test_socket.settimeout(2)
        test_socket.connect((PROXY_HOST, PROXY_PORT))
        test_socket.close()
    except:
        print(f"ERROR: Could not connect to proxy at {PROXY_HOST}:{PROXY_PORT}")
        print("Make sure your proxy is running before running this test.")
        sys.exit(1)
    
    # Run test
    test_custom_ports()
    
    print("\nTest completed. Check the proxy server's console output for more information.")