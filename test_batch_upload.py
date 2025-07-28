#!/usr/bin/env python3
"""
Test script for batch upload functionality.
"""
import requests
import time
import os
import sys

API_BASE_URL = "http://localhost:8000/api/v1"
BATCH_TEST_DIR = "sample_data/batch_test"

def test_batch_upload():
    """Test batch document upload."""
    # Get all test files
    test_files = []
    for filename in os.listdir(BATCH_TEST_DIR):
        if filename.endswith(('.txt', '.json')):
            filepath = os.path.join(BATCH_TEST_DIR, filename)
            test_files.append(filepath)
    
    print(f"Found {len(test_files)} test files")
    
    # Prepare files for upload
    files = []
    for filepath in test_files:
        with open(filepath, 'rb') as f:
            filename = os.path.basename(filepath)
            files.append(('files', (filename, f.read(), 'text/plain')))
    
    # Upload batch
    print("\nUploading batch...")
    response = requests.post(
        f"{API_BASE_URL}/batch-ingest",
        files=files,
        params={"chunking_strategy": "sliding_window"}
    )
    
    if response.status_code != 200:
        print(f"Upload failed: {response.text}")
        return
    
    result = response.json()
    job_id = result['job_id']
    print(f"Batch upload started! Job ID: {job_id}")
    
    # Poll job status
    print("\nTracking progress...")
    while True:
        response = requests.get(f"{API_BASE_URL}/jobs/{job_id}")
        if response.status_code != 200:
            print(f"Failed to get job status: {response.text}")
            break
        
        job_data = response.json()
        progress = (job_data['completed'] + job_data['failed']) / job_data['total'] * 100
        
        print(f"\rProgress: {progress:.0f}% | Completed: {job_data['completed']} | Failed: {job_data['failed']} | Current: {job_data['current_file']}", end='')
        
        if job_data['status'] == 'completed':
            print("\n\n✅ Batch processing completed!")
            print(f"Total: {job_data['total']}")
            print(f"Completed: {job_data['completed']}")
            print(f"Failed: {job_data['failed']}")
            break
        
        time.sleep(2)

if __name__ == "__main__":
    test_batch_upload()