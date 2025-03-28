# Include the libraries for socket and system calls
import socket
import sys
import os
import re
import time
from datetime import datetime

# 1MB buffer size
BUFFER_SIZE = 1000000

def main():
    if len(sys.argv) <= 2:
        print('Usage : "python Proxy.py server_ip server_port"\n[server_ip : IP Address Of Proxy Server]\n[server_port : Port Of Proxy Server]')
        sys.exit(2)
    
    # Get the command line arguments
    proxyHost = sys.argv[1]
    proxyPort = int(sys.argv[2])
    
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
            try:
                cacheLocation = './' + hostname + resource
                if cacheLocation.endswith('/'):
                    cacheLocation = cacheLocation + 'default'
    
                print('Cache location:\t\t' + cacheLocation)
    
                # Check if we should use cached version
                use_cache = False
                if os.path.isfile(cacheLocation):
                    # Check cache-control headers
                    with open(cacheLocation, 'rb') as f:
                        head_data = f.read(1024)  # Read enough for headers
                        head_text = head_data.decode('utf-8', errors='replace')
                        
                        # Check for redirect - don't use cache for redirects
                        status_line = head_text.split('\r\n')[0]
                        if '301 ' in status_line or '302 ' in status_line:
                            use_cache = False
                        else:
                            # Check for max-age=0
                            max_age_match = re.search(r'Cache-Control:.*?max-age=(\d+)', head_text, re.IGNORECASE)
                            if max_age_match:
                                max_age = int(max_age_match.group(1))
                                if max_age == 0:
                                    # Don't use cache for max-age=0
                                    use_cache = False
                                else:
                                    # Check if file is still fresh
                                    file_time = os.path.getmtime(cacheLocation)
                                    current_time = time.time()
                                    if (current_time - file_time) <= max_age:
                                        use_cache = True
                            else:
                                use_cache = True  # No max-age directive, use cache
                
                if use_cache:
                    fileExists = os.path.isfile(cacheLocation)
                    
                    # Check wether the file is currently in the cache
                    cacheFile = open(cacheLocation, "rb")
                    cacheData = cacheFile.read()
        
                    print('Cache hit! Loading from cache file: ' + cacheLocation)
                    # ProxyServer finds a cache hit
                    # Send back response to client 
                    # ~~~~ INSERT CODE ~~~~
                    clientSocket.sendall(cacheData)
                    # ~~~~ END CODE INSERT ~~~~
                    cacheFile.close()
                    print('Sent to the client:')
                    print('> ' + str(cacheData[:100]))
                else:
                    raise Exception("Cache validation failed or cache not usable")
            except:
                # cache miss.  Get resource from origin server
                originServerSocket = None
                # Create a socket to connect to origin server
                # and store in originServerSocket
                # ~~~~ INSERT CODE ~~~~
                originServerSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                # ~~~~ END CODE INSERT ~~~~
    
                print('Connecting to:\t\t' + hostname + '\n')
                try:
                    # Get the IP address for a hostname
                    address = socket.gethostbyname(hostname)
                    # Connect to the origin server
                    # ~~~~ INSERT CODE ~~~~
                    originServerSocket.connect((address, 80))
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
                    originServerRequestHeader = 'Host: ' + hostname + '\r\nConnection: close'
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
                        sys.exit()
    
                    print('Request sent to origin server\n')
    
                    # Get the response from the origin server
                    # ~~~~ INSERT CODE ~~~~
                    response_bytes = b''
                    while True:
                        chunk = originServerSocket.recv(BUFFER_SIZE)
                        if not chunk:
                            break
                        response_bytes += chunk
                    # ~~~~ END CODE INSERT ~~~~
    
                    # Send the response to the client
                    # ~~~~ INSERT CODE ~~~~
                    clientSocket.sendall(response_bytes)
                    # ~~~~ END CODE INSERT ~~~~
    
                    # Check if we should cache this response
                    should_cache = True
                    
                    # Don't cache redirects
                    try:
                        response_start = response_bytes[:100].decode('utf-8', errors='replace')
                        status_line = response_start.split('\r\n')[0]
                        if '301 ' in status_line or '302 ' in status_line:
                            print("Not caching redirect response")
                            should_cache = False
                        
                        # Don't cache if Cache-Control says not to
                        if 'Cache-Control: no-store' in response_start or 'Cache-Control: no-cache' in response_start:
                            print("Not caching due to Cache-Control directive")
                            should_cache = False
                    except:
                        pass
                    
                    if should_cache:
                        # Create a new file in the cache for the requested file.
                        cacheDir, file = os.path.split(cacheLocation)
                        print('cached directory ' + cacheDir)
                        if not os.path.exists(cacheDir):
                            os.makedirs(cacheDir)
                        cacheFile = open(cacheLocation, 'wb')
        
                        # Save origin server response in the cache file
                        # ~~~~ INSERT CODE ~~~~
                        cacheFile.write(response_bytes)
                        # ~~~~ END CODE INSERT ~~~~
                        cacheFile.close()
                        print('cache file closed')
    
                    # finished communicating with origin server - shutdown socket writes
                    print('origin response received. Closing sockets')
                    originServerSocket.close()
                     
                    clientSocket.shutdown(socket.SHUT_WR)
                    print('client socket shutdown for writing')
                except OSError as err:
                    print('origin server request failed. ' + str(err))
                    # Send error response to client
                    error_response = f"HTTP/1.1 502 Bad Gateway\r\n\r\n<html><body><h1>502 Bad Gateway</h1><p>{str(err)}</p></body></html>"
                    clientSocket.sendall(error_response.encode())
        except Exception as e:
            print(f"Error processing request: {e}")
            # Send error response to client
            error_response = f"HTTP/1.1 400 Bad Request\r\n\r\n<html><body><h1>400 Bad Request</h1><p>{str(e)}</p></body></html>"
            clientSocket.sendall(error_response.encode())
    
        try:
            clientSocket.close()
        except:
            print('Failed to close client socket')

if __name__ == "__main__":
    main()