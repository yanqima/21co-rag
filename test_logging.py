#!/usr/bin/env python3
"""Test script to verify Redis logging is working."""

import requests
import json
import time

API_URL = "http://localhost:8000/api/v1"

print("Testing Redis Logging Implementation")
print("=" * 50)

# Test 1: Check health endpoint
print("\n1. Testing health endpoint...")
try:
    response = requests.get(f"{API_URL}/health")
    print(f"   Status: {response.status_code}")
    correlation_id = response.headers.get("X-Correlation-ID")
    print(f"   Correlation ID: {correlation_id}")
except Exception as e:
    print(f"   Error: {e}")

# Test 2: Retrieve logs
print("\n2. Retrieving recent logs...")
try:
    response = requests.get(f"{API_URL}/logs", params={"limit": 10})
    if response.status_code == 200:
        logs_data = response.json()
        print(f"   Found {logs_data['count']} logs")
        if logs_data['logs']:
            print("\n   Recent log entries:")
            for i, log in enumerate(logs_data['logs'][:3]):
                print(f"   [{i+1}] {log.get('timestamp', 'N/A')} - {log.get('event', 'N/A')} - {log.get('level', 'N/A')}")
    else:
        print(f"   Failed to get logs: {response.status_code}")
except Exception as e:
    print(f"   Error: {e}")

# Test 3: Filter by correlation ID
if 'correlation_id' in locals() and correlation_id:
    print(f"\n3. Filtering logs by correlation ID: {correlation_id}")
    try:
        response = requests.get(f"{API_URL}/logs", params={"correlation_id": correlation_id})
        if response.status_code == 200:
            logs_data = response.json()
            print(f"   Found {logs_data['count']} logs for this correlation ID")
            if logs_data['logs']:
                for log in logs_data['logs']:
                    print(f"   - {log.get('event', 'N/A')}")
    except Exception as e:
        print(f"   Error: {e}")

print("\n" + "=" * 50)
print("Testing complete!")
print("\nTo see logs in Streamlit:")
print("1. Open http://localhost:8501")
print("2. Navigate to the 'System Logs' tab")
print("3. Click 'Refresh Logs' to see the latest entries")