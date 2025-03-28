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
import argparse
import re
import time
import threading
from datetime import datetime
from urllib.parse import urlparse, urljoin

# 1MB buffer size
BUFFER_SIZE = 1000000

# Get the IP address and Port number to use for this web proxy server
parser = argparse.ArgumentParser()
parser.add_argument('hostname', help='the IP Address Of Proxy Server')
parser.add_argument('port', help='the port number of the proxy server')
args = parser.parse_args()
proxyHost = args.hostname
proxyPort = int(args.port)

# BONUS FEATURE 3: Support for Custom Ports
# This function extracts hostname, port, and resource from a URI
# It handles URIs with explicit port numbers (hostname:portnumber/file)
def extract_host_port_resource(uri):
    """
    Extract the hostname, port, and resource path from a URI.
    Now handles URIs with explicit port numbers (hostname:portnumber/file).
    
    Args:
        uri (str): The URI to parse
        
    Returns:
        tuple: (hostname, port, resource_path)
    """
    # Remove http protocol from the URI
    uri = re.sub('^(/?)http(s?)://', '', uri, count=1)
    
    # Remove parent directory changes - security
    uri = uri.replace('/..', '')
    
    # Check if there's an explicit port number with regex
    # The pattern looks for: hostname:port/optional-path
    port_match = re.match(r'^([^/:]+):(\d+)(/.*)?$', uri)
    if port_match:
        hostname = port_match.group(1)
        port = int(port_match.group(2))
        resource = port_match.group(3) if port_match.group(3) else '/'
        return hostname, port, resource
    
    # If no explicit port, use the standard format
    resource_parts = uri.split('/', 1)
    hostname = resource_parts[0]
    resource = '/' + resource_parts[1] if len(resource_parts) > 1 else '/'
    
    return hostname, 80, resource  # Default HTTP port is 80

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

# BONUS FEATURE 1: Expires Header Checking
# This function extracts the Expires header value from the response
def extract_expires(response_bytes):
    """
    Extract the Expires header value from the response.
    Returns a datetime object representing the expiration time,
    or None if not found or invalid.
    """
    try:
        headers_str = response_bytes.split(b'\r\n\r\n')[0].decode('utf-8', errors='replace')
        
        # Look for Expires header with regex
        expires_match = re.search(r'Expires: (.*?)(\r\n|\r|\n)', headers_str)
        if expires_match:
            expires_str = expires_match.group(1).strip()
            
            # Try multiple date formats to handle various server formats
            try:
                # Standard HTTP date format (RFC 7231)
                return datetime.strptime(expires_str, "%a, %d %b %Y %H:%M:%S GMT")
            except ValueError:
                try:
                    # Alternative format sometimes used
                    return datetime.strptime(expires_str, "%A, %d-%b-%y %H:%M:%S GMT")
                except ValueError:
                    try:
                        # RFC 850 format
                        return datetime.strptime(expires_str, "%A, %d-%b-%Y %H:%M:%S GMT")
                    except ValueError:
                        # If all formats fail, return None
                        print(f"Could not parse Expires date: {expires_str}")
                        return None
    except:
        pass
    return None

# BONUS FEATURE 1: Expires Header Checking
# Function to check if cached file is still valid based on Expires header
def is_cache_valid(file_path):
    """
    Check if the cached file is still valid based on:
    1. Expires header - checks if the current time has passed the expiration time
    2. Cache-Control max-age - checks if the file is older than max-age seconds
    
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
            
            # BONUS FEATURE 1: Check for Expires header
            expires_date = extract_expires(headers_data)
            if expires_date is not None:
                # Compare with current time
                current_time = datetime.utcnow()
                if current_time > expires_date:
                    print(f"Cache expired according to Expires header: {expires_date}")
                    return False
            
            # Get max-age if specified (fallback if no Expires header)
            max_age = extract_max_age(headers_data)
            if max_age is not None:
                # Check if file is still fresh based on modification time
                file_mtime = os.path.getmtime(file_path)
                current_time = time.time()
                if (current_time - file_mtime) > max_age:
                    print(f"Cache expired according to max-age: {max_age}s")
                    return False
    except Exception as e:
        print(f"Error checking cache validity: {e}")
        return False
    
    # If no expiration found or all checks pass, consider it valid
    return True

# BONUS FEATURE 2: Pre-fetching Associated Files
# Function to extract URLs from HTML content
def extract_urls_from_html(html_content, base_url):
    """
    Extract URLs from href and src attributes in HTML content.
    
    Args:
        html_content (bytes): HTML content to analyze
        base_url (str): Base URL for resolving relative URLs
        
    Returns:
        list: List of absolute URLs found in the HTML
    """
    try:
        # Decode HTML content
        html_text = html_content.decode('utf-8', errors='replace')
        
        # Extract URLs from href attributes using regex
        href_urls = re.findall(r'href=[\'"]?([^\'" >]+)', html_text)
        
        # Extract URLs from src attributes using regex
        src_urls = re.findall(r'src=[\'"]?([^\'" >]+)', html_text)
        
        # Combine all URLs
        all_urls = href_urls + src_urls
        
        # Convert relative URLs to absolute
        absolute_urls = []
        for url in all_urls:
            # Skip URLs that aren't HTTP(S)
            if url.startswith('javascript:') or url.startswith('mailto:') or url.startswith('#'):
                continue
                
            # Convert to absolute URL if relative
            absolute_url = urljoin(base_url, url)
            absolute_urls.append(absolute_url)
        
        return absolute_urls
    except Exception as e:
        print(f"Error extracting URLs from HTML: {e}")
        return []

# BONUS FEATURE 2: Pre-fetching Associated Files
# Function to prefetch resources found in HTML
def prefetch_resources(html_content, base_url):
    """
    Pre-fetch resources referenced in an HTML page (href and src attributes).
    This runs in a separate thread to avoid blocking the main proxy.
    
    Args:
        html_content (bytes): HTML content to analyze
        base_url (str): Base URL for resolving relative URLs
    """
    # Extract URLs from the HTML
    urls = extract_urls_from_html(html_content, base_url)
    
    print(f"Found {len(urls)} resources to prefetch from {base_url}")
    
    # Prefetch each resource
    for url in urls:
        try:
            print(f"Pre-fetching: {url}")
            
            # Parse the URL to get hostname, port, and resource
            parsed_url = urlparse(url)
            
            # Skip non-HTTP URLs
            if parsed_url.scheme not in ['http', '']:
                continue
                
            # Extract hostname and port
            hostname = parsed_url.netloc
            if ':' in hostname:
                hostname, port_str = hostname.split(':', 1)
                port = int(port_str)
            else:
                port = 80  # Default HTTP port
                
            resource = parsed_url.path
            if not resource:
                resource = '/'
            if parsed_url.query:
                resource += '?' + parsed_url.query
                
            # Skip if we've already cached this resource
            cache_location = './' + hostname + resource
            if cache_location.endswith('/'):
                cache_location = cache_location + 'default'
                
            # Skip if already cached and valid
            if os.path.exists(cache_location) and is_cache_valid(cache_location):
                print(f"Resource already cached: {url}")
                continue
                
            # Create socket to connect to origin server
            origin_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            origin_socket.settimeout(5)  # 5 second timeout
            
            try:
                # Get the IP address for the hostname
                address = socket.gethostbyname(hostname)
                
                # Connect to the origin server
                origin_socket.connect((address, port))
                
                # Create HTTP request
                request = f"GET {resource} HTTP/1.1\r\nHost: {hostname}\r\nConnection: close\r\n\r\n"
                
                # Send request
                origin_socket.sendall(request.encode())
                
                # Receive response
                response_bytes = b''
                while True:
                    try:
                        chunk = origin_socket.recv(BUFFER_SIZE)
                        if not chunk:
                            break
                        response_bytes += chunk
                    except socket.timeout:
                        break
                    except Exception as e:
                        print(f"Error receiving prefetch data: {e}")
                        break
                
                # Only cache if appropriate
                if should_cache_response(response_bytes) and response_bytes:
                    # Create directory structure for cache
                    os.makedirs(os.path.dirname(cache_location), exist_ok=True)
                    
                    # Save to cache
                    with open(cache_location, 'wb') as cache_file:
                        cache_file.write(response_bytes)
                    print(f"Prefetched and cached: {url}")
                
            except Exception as e:
                print(f"Error prefetching {url}: {e}")
            finally:
                origin_socket.close()
                
        except Exception as e:
            print(f"Error in prefetch process for {url}: {e}")
    
    print("Prefetching completed")

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
    message_bytes = b''
    while True:
        data = clientSocket.recv(BUFFER_SIZE)
        message_bytes += data
        # If either no more data or we've received the end of the HTTP request (blank line)
        if not data or b'\r\n\r\n' in message_bytes:
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

        # BONUS FEATURE 3: Support for Custom Ports
        # Extract hostname, port, and resource from URI
        hostname, port, resource = extract_host_port_resource(URI)
        print(f'Hostname:\t{hostname}')
        print(f'Port:\t\t{port}')  # This will now show custom ports
        print(f'Resource:\t{resource}')

        # Check if resource is in cache
        cacheLocation = './' + hostname + resource
        if cacheLocation.endswith('/'):
            cacheLocation = cacheLocation + 'default'

        print('Cache location:\t\t' + cacheLocation)

        # BONUS FEATURE 1: Check if cache is still valid (including Expires header check)
        use_cache = os.path.isfile(cacheLocation) and is_cache_valid(cacheLocation)
        
        if use_cache:
            try:
                # Read the cached file and send it to the client
                print('Cache hit! Loading from cache file: ' + cacheLocation)
                
                # Open the file in binary mode
                with open(cacheLocation, "rb") as binary_cache_file:
                    cached_content = binary_cache_file.read()
                    
                # Send the cached data to the client
                clientSocket.sendall(cached_content)
                print(f"Sent {len(cached_content)} bytes from cache to client")
                
                print('Sent to the client from cache')
            except Exception as e:
                print(f"Error reading from cache: {e}")
                use_cache = False  # Fall back to origin server
        
        if not use_cache:
            # cache miss or invalid cache. Get resource from origin server
            originServerSocket = None
            
            # Create a socket with timeout
            originServerSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            originServerSocket.settimeout(5)  # 5 second timeout for operations

            # BONUS FEATURE 3: Using the custom port when connecting
            print(f'Connecting to:\t\t{hostname} on port {port}')
            try:
                # Get the IP address for a hostname
                address = socket.gethostbyname(hostname)
                
                # Connect to the origin server using the potentially custom port
                try:
                    originServerSocket.connect((address, port))
                except socket.error as e:
                    print(f"Failed to connect to origin server: {e}")
                    error_response = f"HTTP/1.1 502 Bad Gateway\r\n\r\n<html><body><h1>502 Bad Gateway</h1><p>Error connecting to origin server: {e}</p></body></html>"
                    clientSocket.sendall(error_response.encode())
                    clientSocket.close()
                    originServerSocket.close()
                    continue
                    
                print('Connected to origin Server')

                # Create origin server request line and headers
                originServerRequest = method + ' ' + resource + ' HTTP/1.1'
                originServerRequestHeader = 'Host: ' + hostname
                
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
                            
                            # BONUS FEATURE 2: Pre-fetching Associated Files
                            # Check if this is an HTML response and if so, prefetch resources
                            content_type = None
                            headers_str = response_bytes.split(b'\r\n\r\n')[0].decode('utf-8', errors='replace')
                            content_type_match = re.search(r'Content-Type: (.*?)(\r\n|\r|\n)', headers_str)
                            if content_type_match:
                                content_type = content_type_match.group(1).strip().lower()
                            
                            # If it's an HTML document, start prefetching resources
                            if content_type and ('text/html' in content_type or 'application/xhtml+xml' in content_type):
                                # Get the body content
                                body_parts = response_bytes.split(b'\r\n\r\n', 1)
                                if len(body_parts) > 1:
                                    # Start a thread to prefetch resources without blocking
                                    base_url = f"http://{hostname}:{port}{resource}"
                                    if resource.endswith('/'):
                                        base_url = base_url[:-1]  # Remove trailing slash
                                    
                                    # Create and start a daemon thread for prefetching
                                    prefetch_thread = threading.Thread(
                                        target=prefetch_resources, 
                                        args=(body_parts[1], base_url)
                                    )
                                    prefetch_thread.daemon = True  # Make thread exit when main thread exits
                                    prefetch_thread.start()
                                    print(f"Started prefetching resources from {base_url}")
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