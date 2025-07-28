#!/usr/bin/env python3
"""Generate test data for profiling demonstration."""

import requests
import time
import random

print("Generating test data for profiling...")
print("=" * 50)

# Generate a few requests with different content sizes
test_documents = [
    ("small_doc.txt", "This is a small test document.", "sliding_window"),
    ("medium_doc.txt", "Machine learning is a subset of artificial intelligence. " * 50, "sentence"),
    ("large_doc.txt", "Data science involves statistics, machine learning, and domain expertise. " * 100, "sliding_window"),
]

correlation_ids = []

for filename, content, strategy in test_documents:
    print(f"\nUploading {filename}...")
    
    files = {'file': (filename, content.encode(), 'text/plain')}
    params = {'chunking_strategy': strategy}
    
    response = requests.post(
        "http://localhost:8000/api/v1/ingest",
        files=files,
        params=params
    )
    
    if response.status_code == 200:
        corr_id = response.headers.get("X-Correlation-ID")
        correlation_ids.append(corr_id)
        print(f"  ✅ Success - Correlation ID: {corr_id}")
    else:
        print(f"  ❌ Failed: {response.status_code}")
    
    # Wait between requests
    time.sleep(random.uniform(1, 3))

# Also make some search requests
print("\nMaking search requests...")
search_queries = ["machine learning", "data science", "artificial intelligence"]

for query in search_queries:
    response = requests.post(
        "http://localhost:8000/api/v1/query",
        json={
            "query": query,
            "generate_answer": True,
            "limit": 3
        }
    )
    
    if response.status_code == 200:
        print(f"  ✅ Search for '{query}' completed")
    
    time.sleep(1)

print("\n" + "=" * 50)
print("Test data generated!")
print("\nTo view profiling:")
print("1. Open http://localhost:8501")
print("2. Go to 'Performance Profiling' tab")
print("3. Click 'Analyze Performance'")
print("\nYou should see:")
print("- Overall performance metrics")
print("- Bottleneck analysis showing embedding generation as slowest")
print("- Time distribution visualization")
print("- Detailed phase statistics")