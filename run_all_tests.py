#!/usr/bin/env python3
"""
Master test script for Proxy-bonus.py
This script runs all three bonus feature tests sequentially
"""

import os
import sys
import subprocess
import time

# Test script filenames
TEST_SCRIPTS = [
    "test_expires_header.py",
    "test_prefetching.py",
    "test_custom_ports.py"
]

def check_proxy_running(host='localhost', port=8081):
    """Check if the proxy server is running on the specified host and port."""
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2)
        s.connect((host, port))
        s.close()
        return True
    except:
        return False

def run_tests():
    """Run all three bonus feature tests."""
    print("\n" + "=" * 80)
    print(" PROXY BONUS FEATURE TESTING SCRIPT ".center(80, "="))
    print("=" * 80 + "\n")
    
    # Check if the proxy is running
    if not check_proxy_running():
        print("ERROR: The proxy server is not running.")
        print("Please start your proxy server (Proxy-bonus.py) before running the tests.")
        print("Example: python Proxy-bonus.py localhost 8081")
        return False
    
    print("Proxy server detected. Running tests...\n")
    
    # Results to track
    results = []
    
    # Run each test script
    for script in TEST_SCRIPTS:
        # Print a separator
        print("\n" + "=" * 80)
        print(f" RUNNING TEST: {script} ".center(80, "="))
        print("=" * 80 + "\n")
        
        try:
            # Run the test script
            result = subprocess.run([sys.executable, script], check=False)
            
            # Check result
            if result.returncode == 0:
                status = "PASSED"
            else:
                status = "FAILED"
            
            results.append((script, status, result.returncode))
            
            # Add a small delay between tests
            time.sleep(2)
            
        except Exception as e:
            print(f"Error running {script}: {e}")
            results.append((script, "ERROR", -1))
    
    # Print summary
    print("\n" + "=" * 80)
    print(" TEST RESULTS SUMMARY ".center(80, "="))
    print("=" * 80)
    
    all_passed = True
    for script, status, code in results:
        status_text = f"{status} (exit code: {code})"
        print(f"{script:<25}: {status_text}")
        if status != "PASSED":
            all_passed = False
    
    print("\nOVERALL RESULT:", "PASSED" if all_passed else "FAILED")
    print("=" * 80 + "\n")
    
    return all_passed

if __name__ == "__main__":
    # Check if all test scripts exist
    missing_scripts = []
    for script in TEST_SCRIPTS:
        if not os.path.exists(script):
            missing_scripts.append(script)
    
    if missing_scripts:
        print("ERROR: The following test scripts are missing:")
        for script in missing_scripts:
            print(f"  - {script}")
        print("\nPlease make sure all test scripts are in the current directory.")
        sys.exit(1)
    
    # Run all tests
    success = run_tests()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)