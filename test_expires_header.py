#!/usr/bin/env python3
"""
Test script for BONUS FEATURE 1: Expires Header Checking
This script tests if your proxy correctly handles the Expires header by:
1. Creating a cached file with an expired date
2. Requesting it through the proxy to see if it fetches a new copy
"""

import os
import socket
import time
import sys
from datetime import datetime, timedelta

# Proxy settings
PROXY_HOST = 'localhost'
PROXY_PORT = 8081  # Update this if you're using a different port

# Test settings
TEST_HOST = 'test-expires.com'
TEST_PATH = '/expires-test'
CACHE_DIR = './' + TEST_HOST
CACHE_FILE = CACHE_DIR + TEST_PATH

def create_test_cache_file():
    """Create a test cache file with an expired Expires header."""
    # Create the past date (1 day ago)
    past_date = datetime.utcnow() - timedelta(days=1)
    expires_date = past_date.strftime("%a, %d %b %Y %H:%M:%S GMT")
    
    # Create a future date (1 day ahead)
    future_date = datetime.utcnow() + timedelta(days=1)
    future_expires_date = future_date.strftime("%a, %d %b %Y %H:%M:%S GMT")
    
    # Create test directory
    os.makedirs(CACHE_DIR, exist_ok=True)
    
    # Create expired cache file
    expired_content = f"""HTTP/1.1 200 OK
Content-Type: text/html
Expires: {expires_date}
Content-Length: 56

<html><body><h1>This content has expired</h1></body></html>
"""
    
    # Create non-expired cache file
    fresh_content = f"""HTTP/1.1 200 OK
Content-Type: text/html
Expires: {future_expires_date}
Content-Length: 58

<html><body><h1>This content is still fresh</h1></body></html>
"""
    
    # Write the expired file
    with open(CACHE_FILE, 'w') as f:
        f.write(expired_content)
    
    # Write the fresh file
    with open(CACHE_DIR + '/fresh-test', 'w') as f:
        f.write(fresh_content)
    
    print(f"Created test files:")
    print(f"1. Expired cache file: {CACHE_FILE}")
    print(f"   with Expires: {expires_date} (in the past)")
    print(f"2. Fresh cache file: {CACHE_DIR}/fresh-test")
    print(f"   with Expires: {future_expires_date} (in the future)")

def test_expires_header():
    """Test if the proxy correctly handles expired content."""
    print("\nTesting BONUS FEATURE 1: Expires Header Checking")
    print("=" * 70)
    
    # Connect to proxy
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.settimeout(10)
    
    try:
        # Connect to the proxy
        client_socket.connect((PROXY_HOST, PROXY_PORT))
        print(f"Connected to proxy at {PROXY_HOST}:{PROXY_PORT}")
        
        # Request the expired content
        request = f"GET http://{TEST_HOST}{TEST_PATH} HTTP/1.1\r\nHost: {TEST_HOST}\r\n\r\n"
        print(f"Sending request for expired content: {request}")
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
        
        # Check if we received a response
        if response:
            response_str = response.decode('utf-8', errors='replace')
            print("\nReceived response header:")
            print("-" * 40)
            header_end = response_str.find('\r\n\r\n')
            if header_end > 0:
                print(response_str[:header_end])
            else:
                print(response_str)
            print("-" * 40)
            
            # Check if this is the cached content or a new response
            if "This content has expired" in response_str:
                print("\nTEST FAILED: Proxy returned the expired cached content!")
                print("The proxy should have detected the Expires header and fetched a fresh copy.")
            else:
                print("\nTEST PASSED: Proxy did not return the expired cached content!")
                print("The proxy correctly detected the expired Expires header.")
        else:
            print("\nNo response received from the proxy.")
    
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
    
    # Create test files
    create_test_cache_file()
    
    # Run test
    test_expires_header()
    
    print("\nTest completed. Check the proxy server's console output for more information.")