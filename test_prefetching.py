#!/usr/bin/env python3
"""
Test script for BONUS FEATURE 2: Pre-fetching Associated Files
This script tests if your proxy correctly pre-fetches resources in HTML:
1. Creates a simple HTML file with links to CSS and images
2. Serves it via a simple HTTP server
3. Requests it through the proxy
4. Checks if the linked resources were prefetched
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
TEST_PORT = 8000  # Port for our test server
TEST_DIR = './testserver'
CACHE_DIR = './' + TEST_HOST + '_' + str(TEST_PORT)  # Where the proxy will cache files

def setup_test_server():
    """Set up a test server with HTML files that have resources to prefetch."""
    # Create test directory and files
    if os.path.exists(TEST_DIR):
        shutil.rmtree(TEST_DIR)
    
    os.makedirs(TEST_DIR, exist_ok=True)
    
    # Create a CSS file
    with open(os.path.join(TEST_DIR, 'style.css'), 'w') as f:
        f.write("""
body {
    font-family: Arial, sans-serif;
    background-color: #f0f0f0;
    color: #333;
}
h1 {
    color: blue;
}
""")
    
    # Create a JavaScript file
    with open(os.path.join(TEST_DIR, 'script.js'), 'w') as f:
        f.write("""
function greet() {
    alert('Hello, world!');
}
""")
    
    # Create an HTML file with links to the CSS and JS
    with open(os.path.join(TEST_DIR, 'index.html'), 'w') as f:
        f.write("""<!DOCTYPE html>
<html>
<head>
    <title>Prefetch Test</title>
    <link rel="stylesheet" href="style.css">
    <script src="script.js"></script>
</head>
<body>
    <h1>Prefetch Test Page</h1>
    <p>This page has resources that should be prefetched.</p>
    <img src="image1.jpg" alt="Test Image 1">
    <img src="image2.jpg" alt="Test Image 2">
    <a href="page2.html">Link to another page</a>
</body>
</html>
""")
    
    # Create a second HTML page
    with open(os.path.join(TEST_DIR, 'page2.html'), 'w') as f:
        f.write("""<!DOCTYPE html>
<html>
<head>
    <title>Second Page</title>
    <link rel="stylesheet" href="style.css">
</head>
<body>
    <h1>Second Page</h1>
    <p>This is another page that could be prefetched.</p>
    <a href="index.html">Back to home</a>
</body>
</html>
""")
    
    # Create dummy image files
    for i in range(1, 3):
        with open(os.path.join(TEST_DIR, f'image{i}.jpg'), 'w') as f:
            f.write(f"This is a dummy image file {i}")
    
    print(f"Created test files in {TEST_DIR}")

def start_test_server():
    """Start a simple HTTP server to serve our test files."""
    os.chdir(TEST_DIR)
    
    handler = http.server.SimpleHTTPRequestHandler
    httpd = socketserver.TCPServer((TEST_HOST, TEST_PORT), handler)
    
    print(f"Starting test server at http://{TEST_HOST}:{TEST_PORT}")
    server_thread = threading.Thread(target=httpd.serve_forever)
    server_thread.daemon = True
    server_thread.start()
    
    return httpd

def check_prefetched_files():
    """Check if the proxy prefetched the resources."""
    resources = [
        '/style.css',
        '/script.js',
        '/image1.jpg',
        '/image2.jpg',
        '/page2.html'
    ]
    
    print("\nChecking for prefetched resources:")
    print("-" * 50)
    
    all_found = True
    for resource in resources:
        cache_path = CACHE_DIR + resource
        if os.path.exists(cache_path):
            print(f"✓ Found prefetched resource: {resource}")
        else:
            print(f"✗ Missing prefetched resource: {resource}")
            all_found = False
    
    print("-" * 50)
    if all_found:
        print("TEST PASSED: All resources were prefetched!")
    else:
        print("TEST FAILED: Some resources were not prefetched.")
    
    return all_found

def test_prefetching():
    """Test if the proxy correctly prefetches resources."""
    print("\nTesting BONUS FEATURE 2: Pre-fetching Associated Files")
    print("=" * 70)
    
    # Clean up any existing cache
    if os.path.exists(CACHE_DIR):
        shutil.rmtree(CACHE_DIR)
    
    # Connect to proxy
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.settimeout(10)
    
    try:
        # Connect to the proxy
        client_socket.connect((PROXY_HOST, PROXY_PORT))
        print(f"Connected to proxy at {PROXY_HOST}:{PROXY_PORT}")
        
        # Request the index page
        request = f"GET http://{TEST_HOST}:{TEST_PORT}/index.html HTTP/1.1\r\nHost: {TEST_HOST}\r\n\r\n"
        print(f"Sending request: GET http://{TEST_HOST}:{TEST_PORT}/index.html")
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
        
        # Give the proxy time to prefetch resources
        print("\nWaiting 5 seconds for proxy to prefetch resources...")
        time.sleep(5)
        
        # Check if resources were prefetched
        check_prefetched_files()
    
    except Exception as e:
        print(f"Error: {e}")
    finally:
        # Close the socket if it's still open
        try:
            client_socket.close()
        except:
            pass

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
    
    # Setup and start test server
    setup_test_server()
    httpd = start_test_server()
    
    try:
        # Run test
        test_prefetching()
    finally:
        # Stop the test server
        print("\nStopping test server...")
        httpd.shutdown()
        
        # Change back to the original directory
        os.chdir('..')
    
    print("\nTest completed. Check the proxy server's console output for more information.")