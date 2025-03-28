# Include the libraries for socket and system calls
import socket
import sys
import os
import re
import time
from datetime import datetime

# 1MB buffer size
BUFFER_SIZE = 1000000

def should_use_cache(cache_location):
    """
    Check if a cached file should be used based on its existence and cache-control headers
    """
    # Check if file exists
    if not os.path.exists(cache_location):
        return False
    
    try:
        # Read the first part of the file to check headers
        with open(cache_location, 'rb') as file:
            headers_data = file.read(1024)  # Read enough to get headers
            headers_text = headers_data.decode('utf-8', errors='replace')
            
            # Check for max-age in Cache-Control header
            max_age_match = re.search(r'Cache-Control:.*?max-age=(\d+)', headers_text, re.IGNORECASE)
            if max_age_match:
                max_age = int(max_age_match.group(1))
                if max_age == 0:  # If max-age=0, always revalidate
                    print(f"Cache-Control: max-age=0 found, not using cache")
                    return False
                
                # Check if file is still fresh based on modification time
                file_mtime = os.path.getmtime(cache_location)
                current_time = time.time()
                if (current_time - file_mtime) > max_age:
                    print(f"Cache expired according to max-age: {max_age}s")
                    return False
            
            # Check for Expires header
            expires_match = re.search(r'Expires: (.*?)(\r\n|\r|\n)', headers_text, re.IGNORECASE)
            if expires_match:
                expires_str = expires_match.group(1).strip()
                try:
                    # Handle multiple date formats
                    for fmt in ["%a, %d %b %Y %H:%M:%S GMT", "%A, %d-%b-%y %H:%M:%S GMT", "%A, %d-%b-%Y %H:%M:%S GMT"]:
                        try:
                            expires_date = datetime.strptime(expires_str, fmt)
                            current_date = datetime.utcnow()
                            if current_date > expires_date:
                                print(f"Cache expired according to Expires header: {expires_date}")
                                return False
                            break
                        except ValueError:
                            continue
                except Exception as e:
                    print(f"Error parsing Expires date: {e}")
            
            # Check if response is a redirect (301/302) - these should generally not be cached
            status_line = headers_text.split('\r\n')[0] if '\r\n' in headers_text else headers_text.split('\n')[0]
            if '301 ' in status_line or '302 ' in status_line:
                print("Cache is a redirect response, not using cache")
                return False
            
            # If no cache control directives found or all checks pass, use the cache
            return True
    except Exception as e:
        print(f"Error checking cache: {e}")
        return False

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
        serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        serverSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        print('Created socket')
    except:
        print('Failed to create socket')
        sys.exit()
    
    try:
        # Bind the the server socket to a host and port
        serverSocket.bind((proxyHost, proxyPort))
        print('Port is bound')
    except:
        print('Port is already in use')
        sys.exit()
    
    try:
        # Listen on the server socket
        serverSocket.listen(5)  # Allow up to 5 queued connections
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
            clientSocket, clientAddr = serverSocket.accept()
            print('Received a connection from:', clientAddr)
        except:
            print('Failed to accept connection')
            sys.exit()
    
        # Get HTTP request from client
        # and store it in the variable: message_bytes
        message_bytes = b''
        while True:
            try:
                data = clientSocket.recv(BUFFER_SIZE)
                message_bytes += data
                # If either no more data or we've received the end of the HTTP request (blank line)
                if not data or b'\r\n\r\n' in message_bytes:
                    break
            except Exception as e:
                print(f"Error receiving client request: {e}")
                break
    
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
    
            # Check if resource is in cache and should be used
            cacheLocation = './' + hostname + resource
            if cacheLocation.endswith('/'):
                cacheLocation = cacheLocation + 'default'
    
            print('Cache location:\t\t' + cacheLocation)
    
            # Check if we should use the cached file
            use_cache = should_use_cache(cacheLocation)
            
            if use_cache:
                try:
                    # Read from cache file
                    with open(cacheLocation, "rb") as cacheFile:
                        cacheData = cacheFile.read()
    
                    print('Cache hit! Loading from cache file: ' + cacheLocation)
                    # Send cached data to client
                    clientSocket.sendall(cacheData)
                    print('Sent to the client:')
                    print('> ' + str(cacheData[:100]))
                    
                    # Close connection
                    clientSocket.shutdown(socket.SHUT_WR)
                except Exception as e:
                    print(f"Error reading cache: {e}")
                    use_cache = False  # Fall back to origin server
            
            if not use_cache:
                # Cache miss or expired cache. Get resource from origin server
                originServerSocket = None
                try:
                    # Create a socket to connect to origin server
                    originServerSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    originServerSocket.settimeout(10)  # 10 second timeout
        
                    print('Connecting to:\t\t' + hostname + '\n')
                    try:
                        # Get the IP address for a hostname
                        address = socket.gethostbyname(hostname)
                        # Connect to the origin server
                        originServerSocket.connect((address, 80))
                        print('Connected to origin Server')
        
                        # Create origin server request line and headers
                        originServerRequest = method + ' ' + resource + ' HTTP/1.1'
                        originServerRequestHeader = 'Host: ' + hostname + '\r\nConnection: close'
        
                        # Construct the request to send to the origin server
                        request = originServerRequest + '\r\n' + originServerRequestHeader + '\r\n\r\n'
        
                        # Request the web resource from origin server
                        print('Forwarding request to origin server:')
                        for line in request.split('\r\n'):
                            print('> ' + line)
        
                        try:
                            originServerSocket.sendall(request.encode())
                        except socket.error as e:
                            print(f'Forward request to origin failed: {e}')
                            error_response = f"HTTP/1.1 502 Bad Gateway\r\n\r\n<html><body><h1>502 Bad Gateway</h1><p>Failed to send request to origin server: {e}</p></body></html>"
                            clientSocket.sendall(error_response.encode())
                            if originServerSocket:
                                originServerSocket.close()
                            continue
        
                        print('Request sent to origin server\n')
        
                        # Get the response from the origin server
                        response_bytes = b''
                        try:
                            while True:
                                chunk = originServerSocket.recv(BUFFER_SIZE)
                                if not chunk:
                                    break
                                response_bytes += chunk
                        except socket.timeout:
                            print("Socket timeout while receiving - response might be incomplete")
                        
                        # Check if we received a response
                        if not response_bytes:
                            raise Exception("No response received from origin server")
        
                        # Send the response to the client
                        clientSocket.sendall(response_bytes)
        
                        # Determine if we should cache this response
                        should_cache = True
                        
                        # Check if it's a redirect response
                        try:
                            # Get status code from response
                            response_start = response_bytes[:100].decode('utf-8', errors='replace')
                            status_line = response_start.split('\r\n')[0]
                            if '301 ' in status_line or '302 ' in status_line:
                                print(f"Redirect response detected: {status_line}")
                                should_cache = False  # Don't cache redirects
                            
                            # Check for no-store directive
                            if 'Cache-Control: no-store' in response_start or 'Cache-Control: no-cache' in response_start:
                                should_cache = False
                        except:
                            pass
                            
                        # If we should cache, save the response
                        if should_cache:
                            # Create directory structure for cache
                            cacheDir, file = os.path.split(cacheLocation)
                            if not os.path.exists(cacheDir):
                                os.makedirs(cacheDir)
                                
                            # Save to cache file
                            with open(cacheLocation, 'wb') as cacheFile:
                                cacheFile.write(response_bytes)
                            print(f'Cached response to {cacheLocation}')
        
                        # Close the origin server socket
                        originServerSocket.close()
                        
                        # Shut down client socket for writing
                        try:
                            clientSocket.shutdown(socket.SHUT_WR)
                        except:
                            pass
                            
                    except OSError as err:
                        print('Origin server request failed: ' + str(err))
                        # Send error response to client
                        error_response = f"HTTP/1.1 502 Bad Gateway\r\n\r\n<html><body><h1>502 Bad Gateway</h1><p>{str(err)}</p></body></html>"
                        clientSocket.sendall(error_response.encode())
                finally:
                    # Make sure origin server socket is closed
                    if originServerSocket:
                        try:
                            originServerSocket.close()
                        except:
                            pass
        except Exception as e:
            print(f"Error processing request: {e}")
            try:
                # Send error response to client
                error_response = f"HTTP/1.1 400 Bad Request\r\n\r\n<html><body><h1>400 Bad Request</h1><p>{str(e)}</p></body></html>"
                clientSocket.sendall(error_response.encode())
            except:
                pass
    
        # Close client socket
        try:
            clientSocket.close()
            print('Client socket closed')
        except:
            print('Failed to close client socket')

if __name__ == "__main__":
    main()