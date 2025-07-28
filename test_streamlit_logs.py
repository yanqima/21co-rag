#!/usr/bin/env python3
"""Visual test for Streamlit logs display."""

import requests
import webbrowser
import time

print("Testing Streamlit Logs Display")
print("=" * 50)

# Make a request to generate logs
print("\n1. Generating test logs...")
test_content = "This is a test document for logging visualization."
files = {'file': ('test_log_viz.txt', test_content.encode(), 'text/plain')}
response = requests.post("http://localhost:8000/api/v1/ingest", files=files)

if response.status_code == 200:
    correlation_id = response.headers.get("X-Correlation-ID")
    print(f"   ✅ Request successful")
    print(f"   Correlation ID: {correlation_id}")
    
    # Wait for processing
    print("\n2. Waiting for processing...")
    time.sleep(3)
    
    # Get the logs
    print("\n3. Fetching logs...")
    log_response = requests.get(
        "http://localhost:8000/api/v1/logs",
        params={"correlation_id": correlation_id}
    )
    
    if log_response.status_code == 200:
        logs = log_response.json()
        print(f"   ✅ Found {logs['count']} logs")
        
        print("\n4. Opening Streamlit...")
        print(f"   - Go to System Logs tab")
        print(f"   - Enter Correlation ID: {correlation_id}")
        print(f"   - Click 'Refresh Logs'")
        print(f"\n   You should see the complete request lifecycle:")
        print("   1. request_started")
        print("   2. document_ingestion_started")
        print("   3. text_extraction_started/completed")
        print("   4. chunking_started/completed") 
        print("   5. embeddings_generation_started/completed")
        print("   6. vector_storage_started/completed")
        print("   7. document_processing_completed")
        print("   8. request_completed")
        
        # Try to open browser
        try:
            webbrowser.open("http://localhost:8501")
        except:
            print("\n   Please open http://localhost:8501 manually")
else:
    print(f"   ❌ Request failed: {response.status_code}")

print("\n" + "=" * 50)