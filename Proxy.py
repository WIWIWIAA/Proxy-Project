# Include the libraries for socket and system calls
import socket
import sys
import os
import argparse
import re
import time

# 1MB buffer size
BUFFER_SIZE = 1000000

# Get the IP address and Port number to use for this web proxy server
parser = argparse.ArgumentParser()
parser.add_argument('hostname', help='the IP Address Of Proxy Server')
parser.add_argument('port', help='the port number of the proxy server')
args = parser.parse_args()
proxyHost = args.hostname
proxyPort = int(args.port)

# Function to check if response is a redirect
def is_redirect(response_bytes):
    """
    Check if the HTTP response is a redirect (301 or 302).
    Returns (is_redirect, location) tuple.
    """
    try:
        # Check the status code in the first line
        first_line = response_bytes.split(b'\r\n')[0].decode('utf-8', errors='replace')
        is_redirect_response = '301 ' in first_line or '302 ' in first_line
        
        if is_redirect_response:
            # Try to extract the Location header
            headers_str = response_bytes.split(b'\r\n\r\n')[0].decode('utf-8', errors='replace')
            location_match = re.search(r'Location: (.*?)(\r\n|\r|\n)', headers_str)
            
            if location_match:
                location = location_match.group(1).strip()
                print(f"Detected redirect to: {location}")
                return True, location
            return True, None
    except:
        pass
    
    return False, None

# Function to check if we should cache a response
def should_cache_response(response_bytes):
    """
    Check HTTP headers to determine if we should cache this response.
    Returns True if cacheable, False if not.
    """
    # Don't cache empty responses
    if not response_bytes:
        return False
    
    # Convert first part of response to string to check headers
    try:
        headers_str = response_bytes.split(b'\r\n\r\n')[0].decode('utf-8', errors='replace')
    except:
        return False  # If we can't decode headers, don't cache
    
    # Check if it's a redirect
    redirect_found, _ = is_redirect(response_bytes)
    if redirect_found:
        print("Response is a redirect - not caching")
        return False
    
    # Don't cache if Cache-Control says not to
    if 'Cache-Control: no-store' in headers_str or 'Cache-Control: no-cache' in headers_str:
        print("Cache-Control indicates not to cache")
        return False
    
    # Check for max-age=0
    if 'Cache-Control: max-age=0' in headers_str:
        print("max-age=0 - not caching")
        return False
    
    return True

# Function to extract max-age from response
def extract_max_age(response_bytes):
    """
    Extract max-age value from Cache-Control header if present.
    Returns max-age in seconds, or None if not found.
    """
    try:
        headers_str = response_bytes.split(b'\r\n\r\n')[0].decode('utf-8', errors='replace')
        
        # Look for Cache-Control header with max-age
        max_age_match = re.search(r'Cache-Control:.*?max-age=(\d+)', headers_str)
        if max_age_match:
            return int(max_age_match.group(1))
    except:
        pass
    return None

# Function to check if cached file is still valid
def is_cache_valid(file_path):
    """
    Check if the cached file is still valid based on its content and modification time.
    Returns True if valid, False if expired or should not be cached.
    """
    # If file doesn't exist, it's not valid
    if not os.path.exists(file_path):
        return False
    
    try:
        # Read the file to check its headers
        with open(file_path, 'rb') as f:
            headers_data = f.read(1024)  # Read enough to get headers
            
            # Check if we should cache this type of response
            if not should_cache_response(headers_data):
                return False
            
            # Get max-age if specified
            max_age = extract_max_age(headers_data)
            if max_age is not None:
                # Check if file is still fresh based on modification time
                file_mtime = os.path.getmtime(file_path)
                current_time = time.time()
                return (current_time - file_mtime) <= max_age
    except:
        return False
    
    # If no max-age found or can't parse headers, default to valid
    return True

# Create a server socket, bind it to a port and start listening
try:
    # Create a server socket
    # ~~~~ INSERT CODE ~~~~
    serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    serverSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    # ~~~~ END CODE INSERT ~~~~
    print('Created socket')
except:
    print('Failed to create socket')
    sys.exit()

try:
    # Bind the the server socket to a host and port
    # ~~~~ INSERT CODE ~~~~
    serverSocket.bind((proxyHost, proxyPort))
    # ~~~~ END CODE INSERT ~~~~
    print('Port is bound')
except:
    print('Port is already in use')
    sys.exit()

try:
    # Listen on the server socket
    # ~~~~ INSERT CODE ~~~~
    serverSocket.listen(5)  # Allow up to 5 queued connections
    # ~~~~ END CODE INSERT ~~~~
    print('Listening to socket')
except:
    print('Failed to listen')
    sys.exit()

# continuously accept connections
while True:
    print('Waiting for connection...')
    clientSocket = None

    # Accept connection from client and store in the clientSocket
    try:
        # ~~~~ INSERT CODE ~~~~
        clientSocket, clientAddr = serverSocket.accept()
        # ~~~~ END CODE INSERT ~~~~
        print('Received a connection from:', clientAddr)
    except:
        print('Failed to accept connection')
        sys.exit()

    # Get HTTP request from client
    # and store it in the variable: message_bytes
    # ~~~~ INSERT CODE ~~~~
    message_bytes = b''
    while True:
        data = clientSocket.recv(BUFFER_SIZE)
        message_bytes += data
        # If either no more data or we've received the end of the HTTP request (blank line)
        if not data or b'\r\n\r\n' in message_bytes:
            break
    # ~~~~ END CODE INSERT ~~~~
    
    try:
        message = message_bytes.decode('utf-8')
        print('Received request:')
        print('< ' + message)

        # Extract the method, URI and version of the HTTP client request 
        requestParts = message.split()
        method = requestParts[0]
        URI = requestParts[1]
        version = requestParts[2]

        print('Method:\t\t' + method)
        print('URI:\t\t' + URI)
        print('Version:\t' + version)
        print('')

        # Get the requested resource from URI
        # Remove http protocol from the URI
        URI = re.sub('^(/?)http(s?)://', '', URI, count=1)

        # Remove parent directory changes - security
        URI = URI.replace('/..', '')

        # Split hostname from resource name
        resourceParts = URI.split('/', 1)
        hostname = resourceParts[0]
        resource = '/'

        if len(resourceParts) == 2:
            # Resource is absolute URI with hostname and resource
            resource = resource + resourceParts[1]

        print('Requested Resource:\t' + resource)

        # Check if resource is in cache
        cacheLocation = './' + hostname + resource
        if cacheLocation.endswith('/'):
            cacheLocation = cacheLocation + 'default'

        print('Cache location:\t\t' + cacheLocation)

        # Check if cache file exists and is valid
        use_cache = os.path.isfile(cacheLocation) and is_cache_valid(cacheLocation)
        
        if use_cache:
            try:
                # Read the cached file and send it to the client
                print('Cache hit! Loading from cache file: ' + cacheLocation)
                # ProxyServer finds a cache hit
                # Send back response to client 
                # ~~~~ INSERT CODE ~~~~
                # Open the file in binary mode instead of text mode
                with open(cacheLocation, "rb") as binary_cache_file:
                    cached_content = binary_cache_file.read()
                    
                # Send the cached data to the client
                clientSocket.sendall(cached_content)
                print(f"Sent {len(cached_content)} bytes from cache to client")
                # ~~~~ END CODE INSERT ~~~~
                
                print('Sent to the client from cache')
            except Exception as e:
                print(f"Error reading from cache: {e}")
                use_cache = False  # Fall back to origin server
        
        if not use_cache:
            # cache miss or invalid cache. Get resource from origin server
            originServerSocket = None
            # Create a socket to connect to origin server
            # and store in originServerSocket
            # ~~~~ INSERT CODE ~~~~
            # Create a socket with timeout
            originServerSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            originServerSocket.settimeout(5)  # 5 second timeout for operations
            # ~~~~ END CODE INSERT ~~~~

            print('Connecting to:\t\t' + hostname + '\n')
            try:
                # Get the IP address for a hostname
                address = socket.gethostbyname(hostname)
                # Connect to the origin server
                # ~~~~ INSERT CODE ~~~~
                try:
                    originServerSocket.connect((address, 80))
                except socket.error as e:
                    print(f"Failed to connect to origin server: {e}")
                    error_response = f"HTTP/1.1 502 Bad Gateway\r\n\r\n<html><body><h1>502 Bad Gateway</h1><p>Error connecting to origin server: {e}</p></body></html>"
                    clientSocket.sendall(error_response.encode())
                    clientSocket.close()
                    originServerSocket.close()
                    continue
                # ~~~~ END CODE INSERT ~~~~
                print('Connected to origin Server')

                originServerRequest = ''
                originServerRequestHeader = ''
                # Create origin server request line and headers to send
                # and store in originServerRequestHeader and originServerRequest
                # originServerRequest is the first line in the request and
                # originServerRequestHeader is the second line in the request
                # ~~~~ INSERT CODE ~~~~
                originServerRequest = method + ' ' + resource + ' HTTP/1.1'
                originServerRequestHeader = 'Host: ' + hostname
                # ~~~~ END CODE INSERT ~~~~

                # Construct the request to send to the origin server
                request = originServerRequest + '\r\n' + originServerRequestHeader + '\r\n\r\n'

                # Request the web resource from origin server
                print('Forwarding request to origin server:')
                for line in request.split('\r\n'):
                    print('> ' + line)

                try:
                    originServerSocket.sendall(request.encode())
                except socket.error:
                    print('Forward request to origin failed')
                    error_response = "HTTP/1.1 502 Bad Gateway\r\n\r\n<html><body><h1>502 Bad Gateway</h1><p>Failed to send request to origin server</p></body></html>"
                    clientSocket.sendall(error_response.encode())
                    clientSocket.close()
                    originServerSocket.close()
                    continue

                print('Request sent to origin server\n')

                # Get the response from the origin server
                # ~~~~ INSERT CODE ~~~~
                # Receive response with timeout
                response_bytes = b''
                try:
                    # Set a shorter timeout for receiving data
                    originServerSocket.settimeout(10)
                    
                    # Read response in chunks
                    while True:
                        try:
                            chunk = originServerSocket.recv(BUFFER_SIZE)
                            if not chunk:
                                break
                            response_bytes += chunk
                        except socket.timeout:
                            print("Socket timeout while receiving - assuming end of response")
                            break
                        except Exception as e:
                            print(f"Error receiving data: {e}")
                            break
                    
                    print(f"Received {len(response_bytes)} bytes from origin server")
                    if len(response_bytes) > 0:
                        print(f"First 100 bytes: {response_bytes[:100]}")
                    
                    # Check if it's a redirect or should be cached
                    redirect_found, redirect_location = is_redirect(response_bytes)
                    should_cache = should_cache_response(response_bytes)
                    
                    # Send response to client
                    if response_bytes:
                        clientSocket.sendall(response_bytes)
                        print(f"Sent {len(response_bytes)} bytes to client")
                    else:
                        # If no data received, send an error
                        error_msg = "HTTP/1.1 502 Bad Gateway\r\n\r\n<html><body><h1>502 Bad Gateway</h1><p>No response from origin server</p></body></html>"
                        clientSocket.sendall(error_msg.encode())
                    
                    # Cache the response if appropriate
                    if should_cache and response_bytes and len(response_bytes) > 0:
                        try:
                            # Create directory structure for cache
                            os.makedirs(os.path.dirname(cacheLocation), exist_ok=True)
                            with open(cacheLocation, 'wb') as cacheFile:
                                cacheFile.write(response_bytes)
                            print(f"Cached {len(response_bytes)} bytes to file: {cacheLocation}")
                        except Exception as e:
                            print(f"Error caching response: {e}")
                    elif redirect_found:
                        print(f"Not caching redirect response")
                    
                except Exception as e:
                    print(f"Error in communication with origin server: {e}")
                    try:
                        error_msg = f"HTTP/1.1 500 Internal Server Error\r\n\r\n<html><body><h1>500 Internal Server Error</h1><p>{str(e)}</p></body></html>"
                        clientSocket.sendall(error_msg.encode())
                    except:
                        pass
                finally:
                    # Clean up
                    originServerSocket.close()
                    print("Origin server socket closed")
                # ~~~~ END CODE INSERT ~~~~
                
                # finish up and close client connection
                try:
                    clientSocket.shutdown(socket.SHUT_WR)
                    print('Client socket shutdown for writing')
                except:
                    pass

            except OSError as err:
                print('Origin server request failed: ' + str(err))
                try:
                    error_response = f"HTTP/1.1 502 Bad Gateway\r\n\r\n<html><body><h1>502 Bad Gateway</h1><p>Error communicating with origin server: {str(err)}</p></body></html>"
                    clientSocket.sendall(error_response.encode())
                except:
                    pass
    except Exception as e:
        print(f"Error processing request: {e}")
        try:
            error_msg = f"HTTP/1.1 400 Bad Request\r\n\r\n<html><body><h1>400 Bad Request</h1><p>Error processing request: {str(e)}</p></body></html>"
            clientSocket.sendall(error_msg.encode())
        except:
            pass

    # Close client socket
    try:
        clientSocket.close()
    except:
        print('Failed to close client socket')