#!/usr/bin/env python3
"""Test full request tracing with correlation ID."""

import requests
import time
import json

API_URL = "http://localhost:8000/api/v1"

print("Testing Full Request Tracing")
print("=" * 50)

# Create a test document
test_content = """
This is a test document for tracing.
It contains information about machine learning and artificial intelligence.
We want to see the full lifecycle of processing this document.
"""

# Upload a document
print("\n1. Uploading test document...")
files = {
    'file': ('test_trace.txt', test_content.encode(), 'text/plain')
}
params = {
    'chunking_strategy': 'sliding_window',
    'chunk_size': 100,
    'chunk_overlap': 20
}

response = requests.post(f"{API_URL}/ingest", files=files, params=params)
correlation_id = response.headers.get("X-Correlation-ID")
print(f"   Status: {response.status_code}")
print(f"   Correlation ID: {correlation_id}")

if response.status_code == 200:
    result = response.json()
    print(f"   Job ID: {result['job_id']}")
    print(f"   Document ID: {result['document_id']}")

# Wait a bit for processing
print("\n2. Waiting for processing to complete...")
time.sleep(3)

# Now trace the full request
print(f"\n3. Tracing request with correlation ID: {correlation_id}")
response = requests.get(f"{API_URL}/logs", params={"correlation_id": correlation_id})

if response.status_code == 200:
    logs_data = response.json()
    print(f"\n   Found {logs_data['count']} logs for this request")
    print("\n   Request lifecycle:")
    
    # Sort logs by timestamp
    logs = sorted(logs_data['logs'], key=lambda x: x.get('timestamp', ''))
    
    for i, log in enumerate(logs):
        timestamp = log.get('timestamp', 'N/A')
        event = log.get('event', 'N/A')
        level = log.get('level', 'info')
        
        # Extract key details
        details = []
        if 'method' in log:
            details.append(f"method={log['method']}")
        if 'path' in log:
            details.append(f"path={log['path']}")
        if 'status_code' in log:
            details.append(f"status={log['status_code']}")
        if 'duration' in log:
            details.append(f"duration={log['duration']:.3f}s")
        if 'document_id' in log:
            details.append(f"doc_id={log['document_id']}")
        if 'filename' in log and log['filename'] != 'middleware.py':
            details.append(f"file={log['filename']}")
        
        detail_str = " | ".join(details) if details else ""
        
        # Level indicators
        level_icon = {"error": "❌", "warning": "⚠️", "info": "✅"}.get(level, "📝")
        
        print(f"   [{i+1}] {level_icon} {timestamp[-12:]} - {event:<25} {detail_str}")

# Test search to generate more logs
print("\n4. Performing a search query...")
search_payload = {
    "query": "machine learning",
    "generate_answer": True,
    "limit": 3
}
response = requests.post(f"{API_URL}/query", json=search_payload)
search_correlation_id = response.headers.get("X-Correlation-ID")
print(f"   Search Correlation ID: {search_correlation_id}")

# Wait and trace search
time.sleep(2)
print(f"\n5. Tracing search request: {search_correlation_id}")
response = requests.get(f"{API_URL}/logs", params={"correlation_id": search_correlation_id})

if response.status_code == 200:
    logs_data = response.json()
    logs = sorted(logs_data['logs'], key=lambda x: x.get('timestamp', ''))
    
    print(f"   Found {len(logs)} logs for search request")
    for log in logs:
        event = log.get('event', 'N/A')
        if 'duration' in log:
            print(f"   - {event} (took {log['duration']:.3f}s)")
        else:
            print(f"   - {event}")

print("\n" + "=" * 50)
print("Tracing complete!")
print(f"\nTo view in Streamlit:")
print(f"1. Go to System Logs tab")
print(f"2. Enter correlation ID: {correlation_id}")
print(f"3. Click 'Refresh Logs' to see the full trace")