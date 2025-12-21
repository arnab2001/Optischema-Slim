#!/usr/bin/env python3
"""
Advanced LLM Benchmarking Suite for OptiSchema.
Runs Golden Dataset scenarios, captures full context (prompts, raw responses),
and stores them in the application's SQLite database for tuning.
"""

import requests
import sqlite3
import time
import sys
import os
import json
import asyncio
from datetime import datetime

# Configuration
API_BASE_URL = "http://localhost:8001"
ANALYZE_URL = f"{API_BASE_URL}/api/analysis/analyze"
CONNECT_URL = f"{API_BASE_URL}/api/connection/connect"
DB_PATH = "/home/arnab/Documents/GitHub/Optischema-Slim/backend/optischema.db"

SCENARIOS = [
    {
        "id": "A",
        "name": "The Slam Dunk (Must Fix)",
        "query": "SELECT * FROM golden.orders WHERE user_id = 5678",
        "expected_category": "INDEX",
        "description": "Large table (1M rows), should suggest an index on user_id."
    },
    {
        "id": "B",
        "name": "The Trap (Must Pass)",
        "query": "INSERT INTO golden.orders (user_id, amount) VALUES (123, 45.67)",
        "expected_category": "ADVISORY",
        "description": "Insert statement, should not suggest indexes."
    },
    {
        "id": "C",
        "name": "The Tiny Table (Policy Test)",
        "query": "SELECT * FROM golden.user_roles WHERE code = 'ADMIN'",
        "expected_category": "ADVISORY",
        "description": "Tiny table (15 rows), Seq Scan is faster than Index Scan."
    },
    {
        "id": "D",
        "name": "The Function Scan (Rewrite Test)",
        "query": "SELECT * FROM golden.users WHERE extract(year from created_at) = 2023",
        "expected_category": "REWRITE",
        "description": "Extract function prevents index usage, should suggest a range rewrite."
    },
    {
        "id": "E",
        "name": "The Join Bottleneck (Index Test)",
        "query": "SELECT p.name, r.rating FROM golden.products p JOIN golden.product_reviews r ON p.id = r.product_id WHERE r.rating = 5",
        "expected_category": "INDEX",
        "description": "JOIN on product_id which is missing an index, should suggest an index on product_reviews.product_id."
    },
    {
        "id": "F",
        "name": "The Aggregate Slowness (Rewrite/Index Test)",
        "query": "SELECT event_type, count(*) FROM golden.events GROUP BY event_type ORDER BY count(*) DESC",
        "expected_category": "ADVISORY",
        "description": "High-volume aggregation. Might suggest a covering index or just explain the bottleneck."
    }
]

def ensure_app_connection():
    print("Checking app connection to sandbox database...")
    # The API is running inside Docker, so it should connect to postgres-sandbox:5432
    conn_string = "postgresql://optischema:optischema_pass@postgres-sandbox:5432/optischema_sandbox"
    
    # Try to connect via API
    try:
        # Check health
        resp = requests.get(f"{API_BASE_URL}/health", timeout=5)
        if resp.status_code != 200:
            print(f"Backend is not healthy: {resp.status_code}")
            return False
            
        # Send connection request
        payload = {"connection_string": conn_string}
        r = requests.post(CONNECT_URL, json=payload, timeout=10)
        if r.status_code == 200:
            print(f"App connected to sandbox DB.")
            return True
        else:
            print(f"Failed to connect app to DB: {r.text}")
            return False
    except Exception as e:
        print(f"Error connecting to app: {e}")
        return False

def verify_benchmark_result(scenario_id):
    """Verify result exists in the PostgreSQL golden.benchmark_results table via API."""
    try:
        verify_url = f"{API_BASE_URL}/api/analysis/verify/{scenario_id}"
        resp = requests.get(verify_url, timeout=60)
        if resp.status_code == 200:
            data = resp.json()
            if "error" not in data:
                return data["actual_category"], data["alignment_score"]
            else:
                print(f"Verification data missing in Postgres: {data['error']}")
        else:
            print(f"Verification API failed: {resp.status_code}")
        return None, 0.0
    except Exception as e:
        print(f"Error verifying benchmark result via API: {e}")
        return None, 0.0

def generate_query_load(query, iterations=10):
    """Execute query multiple times via docker exec psql to ensure it shows up in pg_stat_statements."""
    print(f"Generating load ({iterations} iterations)...")
    import subprocess
    
    # We use docker exec to run psql inside the container
    # This avoids local psycopg2 dependency
    try:
        psql_cmd = [
            "docker", "exec", "optischema-postgres-sandbox",
            "psql", "-U", "optischema", "-d", "optischema_sandbox",
            "-c", query
        ]
        
        for _ in range(iterations):
            subprocess.run(psql_cmd, capture_output=True, check=False)
            
    except Exception as e:
        print(f"Load generation failed: {e}")

def run_scenario(scenario):
    print(f"\n[Scenario {scenario['id']}] {scenario['name']}")
    print(f"Query: {scenario['query']}")
    
    # Generate load for complex scenarios to make them "hot"
    if scenario["id"] in ["A", "D", "E", "F"]:
        generate_query_load(scenario["query"])
    
    try:
        # Calculate alignment score for the API to store
        # (We do a preliminary check based on historical expectations)
        
        # We pass scenario_id to trigger the backend save to PostgreSQL
        payload = {
            "query": scenario["query"],
            "scenario_id": scenario["id"]
        }
        
        start_time = time.time()
        response = requests.post(ANALYZE_URL, json=payload, timeout=120)
        duration = time.time() - start_time
        
        if response.status_code != 200:
            print(f"API Error: {response.status_code} - {response.text}")
            return None, 0.0
        
        result = response.json()
        actual_cat = result['suggestion'].get('category')
        
        # Calculate alignment score for verification
        alignment_score = 1.0 if actual_cat == scenario["expected_category"] else 0.0
        
        # In a real scenario, we might re-send or have the backend calculate it.
        # For this implementation, the backend has the logic to save.
        # Let's update the payload to include the score if we really want it stored.
        
        payload["score"] = alignment_score
        requests.post(ANALYZE_URL, json=payload, timeout=10) # Second call to update with score (optional optimization)
        
        # Actually, let's just call verify to see if it's there.
        actual_cat_db, score_db = verify_benchmark_result(scenario["id"])
        
        print(f"Actual Category: {actual_cat}")
        print(f"Verified in Postgres: {actual_cat_db} (Score: {score_db})")
        print(f"Duration: {duration:.2f}s")
        
        return result, alignment_score
    except Exception as e:
        print(f"Request Error: {e}")
        return None, 0.0

def main():
    print("Starting LLM Benchmark Suite...")
    print(f"Logging to: {DB_PATH}")
    
    if not ensure_app_connection():
        print("Aborting: Could not establish app-to-db connection.")
        sys.exit(1)
        
    passed = 0
    total = len(SCENARIOS)
    
    for scenario in SCENARIOS:
        _, score = run_scenario(scenario)
        if score >= 1.0:
            passed += 1
        time.sleep(1) 
        
    print("\n" + "="*40)
    print(f"BENCHMARK SUMMARY: {passed}/{total} scenarios aligned.")
    print("="*40)
    
    if passed == total:
        print("\nGOLDEN DATASET SUCCESS - ALL SCENARIOS ALIGNED")
        sys.exit(0)
    else:
        print("\nSOME SCENARIOS FAILED ALIGNMENT - CHECK DATABASE FOR CONTEXT")
        sys.exit(1)

if __name__ == "__main__":
    main()
