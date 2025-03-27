import os

# Define the directory and file path
cache_dir = './example.com'
cache_file = './example.com/default'

# Create the directory if it doesn't exist
if not os.path.exists(cache_dir):
    os.makedirs(cache_dir)
    print(f"Created directory: {cache_dir}")

# Create the cache file with test content
cache_content = """HTTP/1.1 200 OK
Content-Type: text/html
Content-Length: 44

<html><body><h1>Test Cache</h1></body></html>"""

with open(cache_file, 'w') as f:
    f.write(cache_content)

print(f"Created cache file: {cache_file}")
print(f"Current directory: {os.getcwd()}")
print("Cache file absolute path:", os.path.abspath(cache_file))