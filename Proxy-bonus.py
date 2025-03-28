# Proxy-bonus.py - Enhanced Web Proxy Implementation
#
# BONUS FEATURES IMPLEMENTED:
# 1. Expires Header Checking: The proxy checks the Expires header of cached objects
#    to determine if a new copy is needed from the origin server.
#
# 2. Pre-fetching Associated Files: When an HTML page is fetched, the proxy 
#    analyzes it for href and src attributes to identify associated resources,
#    then pre-fetches and caches these resources.
#
# 3. Support for Custom Ports: The proxy handles URLs with explicit port numbers
#    (hostname:portnumber/file) by extracting the port and connecting to it.

# Include the libraries for socket and system calls
import socket
import sys
import os
import re
import time
import threading
from datetime import datetime
from urllib.parse import urlparse, urljoin

# 1MB buffer size
BUFFER_SIZE = 1000000

def main():
    if len(sys.argv) <= 2:
        print('Usage : "python Proxy-bonus.py server_ip server_port"\n[server_ip : IP Address Of Proxy Server]\n[server_port : Port Of Proxy Server]')
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
    
            # BONUS FEATURE 3: Support for Custom Ports
            # Extract hostname, port, and resource from URI
            port = 80  # Default HTTP port
            
            # Check if there's a port specified in the hostname part
            port_match = re.match(r'^([^/:]+):(\d+)(/.*)?$', URI)
            if port_match:
                hostname = port_match.group(1)
                port = int(port_match.group(2))
                resource = port_match.group(3) if port_match.group(3) else '/'
                print(f"Found custom port: {port}")
            else:
                # Standard format without custom port
                resourceParts = URI.split('/', 1)
                hostname = resourceParts[0]
                resource = '/'
                
                if len(resourceParts) == 2:
                    # Resource is absolute URI with hostname and resource
                    resource = resource + resourceParts[1]
    
            print('Requested Resource:\t' + resource)
            print(f'Hostname: {hostname}, Port: {port}')
    
            # Check if resource is in cache
            try:
                # Create cache location key including port if not default
                cache_key = hostname
                if port != 80:
                    cache_key += f"_{port}"
                    
                cacheLocation = './' + cache_key + resource
                if cacheLocation.endswith('/'):
                    cacheLocation = cacheLocation + 'default'
    
                print('Cache location:\t\t' + cacheLocation)
    
                # BONUS FEATURE 1: Expires Header Checking
                use_cache = False
                if os.path.isfile(cacheLocation):
                    with open(cacheLocation, 'rb') as f:
                        headers_data = f.read(1024)  # Read enough to get headers
                        headers_text = headers_data.decode('utf-8', errors='replace')
                        
                        # Check for redirect - don't use cache for redirects
                        status_line = headers_text.split('\r\n')[0]
                        if '301 ' in status_line or '302 ' in status_line:
                            print("Cache contains redirect response - not using")
                            use_cache = False
                        else:
                            # Check for Cache-Control: max-age
                            max_age_match = re.search(r'Cache-Control:.*?max-age=(\d+)', headers_text, re.IGNORECASE)
                            if max_age_match:
                                max_age = int(max_age_match.group(1))
                                if max_age == 0:
                                    print("Cache-Control: max-age=0 found, not using cache")
                                    use_cache = False
                                else:
                                    # Check if file is still fresh based on modification time
                                    file_mtime = os.path.getmtime(cacheLocation)
                                    current_time = time.time()
                                    if (current_time - file_mtime) > max_age:
                                        print(f"Cache expired according to max-age: {max_age}s")
                                        use_cache = False
                                    else:
                                        use_cache = True
                            else:
                                # BONUS FEATURE 1: Check for Expires header
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
                                                    use_cache = False
                                                else:
                                                    print(f"Cache valid according to Expires header: {expires_date}")
                                                    use_cache = True
                                                break
                                            except ValueError:
                                                continue
                                    except Exception as e:
                                        print(f"Error parsing Expires date: {e}")
                                        use_cache = False
                                else:
                                    # No cache control directives found, use cache
                                    use_cache = True
                
                if use_cache:
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
                originServerSocket.settimeout(10)  # 10 second timeout
                # ~~~~ END CODE INSERT ~~~~
    
                print(f'Connecting to: {hostname} on port {port}\n')
                try:
                    # Get the IP address for a hostname
                    address = socket.gethostbyname(hostname)
                    # Connect to the origin server
                    # ~~~~ INSERT CODE ~~~~
                    # BONUS FEATURE 3: Connect using the custom port
                    originServerSocket.connect((address, port))
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
                    try:
                        while True:
                            chunk = originServerSocket.recv(BUFFER_SIZE)
                            if not chunk:
                                break
                            response_bytes += chunk
                    except socket.timeout:
                        print("Socket timeout while receiving - response might be incomplete")
                    # ~~~~ END CODE INSERT ~~~~
    
                    # Send the response to the client
                    # ~~~~ INSERT CODE ~~~~
                    clientSocket.sendall(response_bytes)
                    # ~~~~ END CODE INSERT ~~~~
    
                    # Check if we should cache this response
                    should_cache = True
                    
                    # Check if it's a redirect response
                    is_redirect = False
                    is_html = False
                    try:
                        # Split headers and body
                        header_end = response_bytes.find(b'\r\n\r\n')
                        if header_end > 0:
                            headers = response_bytes[:header_end].decode('utf-8', errors='replace')
                            body = response_bytes[header_end+4:]
                            
                            # Check response status code
                            status_line = headers.split('\r\n')[0]
                            if '301 ' in status_line or '302 ' in status_line:
                                print(f"Redirect response detected: {status_line}")
                                should_cache = False
                                is_redirect = True
                            
                            # Check for no-store directive
                            if 'Cache-Control: no-store' in headers or 'Cache-Control: no-cache' in headers:
                                should_cache = False
                            
                            # Check if this is HTML content
                            if 'Content-Type: text/html' in headers:
                                is_html = True
                    except Exception as e:
                        print(f"Error checking response headers: {e}")
                    
                    # If we should cache, save the response
                    if should_cache:
                        # Create directory structure for cache
                        cache_key = hostname
                        if port != 80:
                            cache_key += f"_{port}"
                            
                        cacheLocation = './' + cache_key + resource
                        if cacheLocation.endswith('/'):
                            cacheLocation = cacheLocation + 'default'
                            
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
                        
                        # BONUS FEATURE 2: Pre-fetching Associated Files
                        if is_html and not is_redirect:
                            # Start a thread to prefetch resources
                            def prefetch_resources():
                                try:
                                    # Extract URLs from HTML (href and src attributes)
                                    html_content = body.decode('utf-8', errors='replace')
                                    
                                    # Find all href attributes
                                    href_urls = re.findall(r'href=[\'"]?([^\'" >]+)', html_content)
                                    
                                    # Find all src attributes
                                    src_urls = re.findall(r'src=[\'"]?([^\'" >]+)', html_content)
                                    
                                    # Combine URLs
                                    all_urls = href_urls + src_urls
                                    print(f"Found {len(all_urls)} resources to potentially prefetch")
                                    
                                    # Base URL for resolving relative URLs
                                    base_url = f"http://{hostname}:{port}"
                                    
                                    # Process each URL
                                    for url in all_urls:
                                        # Skip non-HTTP URLs and fragment identifiers
                                        if url.startswith(('javascript:', 'mailto:', '#')):
                                            continue
                                            
                                        # Convert relative URL to absolute
                                        if not url.startswith(('http://', 'https://')):
                                            if url.startswith('/'):
                                                full_url = f"{base_url}{url}"
                                            else:
                                                # Handle relative path
                                                path_parts = resource.split('/')
                                                path_dir = '/'.join(path_parts[:-1]) + '/'
                                                full_url = f"{base_url}{path_dir}{url}"
                                        else:
                                            full_url = url
                                            
                                        # Skip URLs that aren't HTTP
                                        if not full_url.startswith('http://'):
                                            continue
                                            
                                        # Extract hostname and resource path
                                        parsed_url = urlparse(full_url)
                                        prefetch_hostname = parsed_url.netloc
                                        prefetch_resource = parsed_url.path
                                        if not prefetch_resource:
                                            prefetch_resource = '/'
                                            
                                        # Extract port if specified
                                        prefetch_port = 80
                                        if ':' in prefetch_hostname:
                                            hostname_parts = prefetch_hostname.split(':')
                                            prefetch_hostname = hostname_parts[0]
                                            prefetch_port = int(hostname_parts[1])
                                            
                                        # Generate cache location
                                        prefetch_cache_key = prefetch_hostname
                                        if prefetch_port != 80:
                                            prefetch_cache_key += f"_{prefetch_port}"
                                            
                                        prefetch_cache_location = './' + prefetch_cache_key + prefetch_resource
                                        if prefetch_cache_location.endswith('/'):
                                            prefetch_cache_location += 'default'
                                            
                                        # Skip if already cached
                                        if os.path.exists(prefetch_cache_location):
                                            continue
                                            
                                        print(f"Prefetching: {full_url}")
                                        
                                        # Create socket for prefetch request
                                        try:
                                            prefetch_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                                            prefetch_socket.settimeout(5)  # Short timeout
                                            
                                            # Get IP address
                                            prefetch_address = socket.gethostbyname(prefetch_hostname)
                                            
                                            # Connect
                                            prefetch_socket.connect((prefetch_address, prefetch_port))
                                            
                                            # Create request
                                            prefetch_request = f"GET {prefetch_resource} HTTP/1.1\r\nHost: {prefetch_hostname}\r\nConnection: close\r\n\r\n"
                                            
                                            # Send request
                                            prefetch_socket.sendall(prefetch_request.encode())
                                            
                                            # Get response
                                            prefetch_response = b''
                                            while True:
                                                try:
                                                    chunk = prefetch_socket.recv(BUFFER_SIZE)
                                                    if not chunk:
                                                        break
                                                    prefetch_response += chunk
                                                except socket.timeout:
                                                    break
                                                except Exception as e:
                                                    print(f"Error receiving prefetch data: {e}")
                                                    break
                                            
                                            # Close socket
                                            prefetch_socket.close()
                                            
                                            # Check if we should cache this prefetched response
                                            should_cache_prefetch = True
                                            
                                            # Check for redirect and other non-cacheable responses
                                            try:
                                                prefetch_headers = prefetch_response[:100].decode('utf-8', errors='replace')
                                                prefetch_status = prefetch_headers.split('\r\n')[0]
                                                
                                                if '301 ' in prefetch_status or '302 ' in prefetch_status:
                                                    should_cache_prefetch = False
                                                
                                                if 'Cache-Control: no-store' in prefetch_headers or 'Cache-Control: no-cache' in prefetch_headers:
                                                    should_cache_prefetch = False
                                            except:
                                                pass
                                            
                                            # Cache the prefetched resource if appropriate
                                            if should_cache_prefetch and prefetch_response:
                                                try:
                                                    # Create directories if needed
                                                    prefetch_dir = os.path.dirname(prefetch_cache_location)
                                                    if not os.path.exists(prefetch_dir):
                                                        os.makedirs(prefetch_dir)
                                                        
                                                    # Write to cache file
                                                    with open(prefetch_cache_location, 'wb') as f:
                                                        f.write(prefetch_response)
                                                    
                                                    print(f"Successfully cached prefetched resource: {full_url}")
                                                except Exception as e:
                                                    print(f"Error caching prefetched resource: {e}")
                                                    
                                        except Exception as e:
                                            print(f"Error prefetching {full_url}: {e}")
                                except Exception as e:
                                    print(f"Error in prefetch thread: {e}")
                            
                            # Start prefetch thread
                            prefetch_thread = threading.Thread(target=prefetch_resources)
                            prefetch_thread.daemon = True
                            prefetch_thread.start()
                            print("Started prefetching thread for associated resources")
    
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