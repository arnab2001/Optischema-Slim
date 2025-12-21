#!/usr/bin/env python3
"""
Automation script to run 4 "Golden Dataset" scenarios through OptiSchema
and verify results against expected outcomes.
"""

import requests
import sqlite3
import time
import sys
import os
import json

# Configuration
API_URL = "http://localhost:8001/api/analysis/analyze"
CONNECT_URL = "http://localhost:8001/connect" # Note: connection router usually prefixed with /api/connection if included in main, let me check main.py
DB_PATH = "/home/arnab/Documents/GitHub/Optischema-Slim/backend/optischema.db"

# Actually, I should check the prefixes in main.py. 
# Looking at the logs, it says "POST /api/analysis/analyze". 
# Usually routers are tagged with prefixes.

def ensure_connection():
    print("Connecting OptiSchema to sandbox database...")
    conn_string = "postgresql://optischema:optischema_pass@postgres-sandbox:5432/optischema_sandbox"
    # Try multiple common prefixes if needed, but let's check main.py first.
    # For now, I'll assume /api/connection/connect based on standard patterns.
    try:
        # Check health first
        resp = requests.get("http://localhost:8001/health")
        print(f"Health check: {resp.status_code}")
        
        # Connect
        payload = {"connection_string": conn_string}
        # Trying common prefixes
        for prefix in ["/api/connection", "/connection", "/api"]:
            url = f"http://localhost:8001{prefix}/connect"
            try:
                r = requests.post(url, json=payload, timeout=10)
                if r.status_code == 200:
                    print(f"✅ Connected via {url}")
                    return True
            except:
                continue
        print("❌ Could not connect to database via API")
        return False
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return False

SCENARIOS = [
    {
        "id": "A",
        "name": "The Slam Dunk (Must Fix)",
        "query": "SELECT * FROM golden.orders WHERE user_id = 5678",
        "expected_category": "INDEX",
        "fail_if": ["ADVISORY"],
        "description": "Large table (1M rows), should suggest an index on user_id."
    },
    {
        "id": "B",
        "name": "The Trap (Must Pass)",
        "query": "INSERT INTO golden.orders (user_id, amount) VALUES (123, 45.67)",
        "expected_category": "ADVISORY",
        "fail_if": ["INDEX"],
        "description": "Insert statement, should not suggest indexes."
    },
    {
        "id": "C",
        "name": "The Tiny Table (Policy Test)",
        "query": "SELECT * FROM golden.user_roles WHERE code = 'ADMIN'",
        "expected_category": "ADVISORY",
        "fail_if": ["INDEX"],
        "description": "Tiny table (15 rows), Seq Scan is faster than Index Scan."
    },
    {
        "id": "D",
        "name": "The Function Scan (Rewrite Test)",
        "query": "SELECT * FROM golden.users WHERE extract(year from created_at) = 2023",
        "expected_category": "REWRITE",
        "fail_if": ["INDEX", "CREATE INDEX"],
        "description": "Extract function prevents index usage, should suggest a range rewrite."
    }
]

def run_analysis(scenario):
    print(f"\n[Scenario {scenario['id']}] {scenario['name']}")
    print(f"Query: {scenario['query']}")
    
    try:
        response = requests.post(API_URL, json={"query": scenario["query"]}, timeout=60)
        if response.status_code != 200:
            print(f"❌ API Error: {response.status_code} - {response.text}")
            return None
        
        return response.json()
    except Exception as e:
        print(f"❌ Request Error: {e}")
        return None

def verify_result(scenario, result):
    if not result:
        return False
    
    suggestion = result.get("suggestion", {})
    actual_category = suggestion.get("category", "UNKNOWN")
    reasoning = suggestion.get("reasoning", "").lower()
    sql = suggestion.get("sql", "") or ""
    
    print(f"Actual Category: {actual_category}")
    # print(f"Reasoning: {reasoning[:100]}...")
    
    # 1. Check Category
    if actual_category != scenario["expected_category"]:
        # Special case for Category D where model might skip REWRITE and suggest INDEX if it hallucinations
        # But per requirements, it must be REWRITE.
        print(f"❌ Failed: Expected category {scenario['expected_category']}, got {actual_category}")
        return False
    
    # 2. Check Fail conditions
    for fail_keyword in scenario["fail_if"]:
        if fail_keyword.upper() == actual_category:
             print(f"❌ Failed: Categorized as {fail_keyword} which is blocked for this scenario.")
             return False
        if fail_keyword.lower() in sql.lower():
             print(f"❌ Failed: Suggestion contains '{fail_keyword}' which is blocked for this scenario.")
             return False

    # 3. Scenario specific checks
    if scenario["id"] == "C":
        if "tiny" not in reasoning and "small" not in reasoning and "15" not in reasoning:
             print("⚠️ Warning: Reasoning didn't mention table size explicitly, but category matches.")
    
    if scenario["id"] == "D":
        if ">=" not in sql or "2023" not in sql:
             print("❌ Failed: Rewrite suggestion doesn't look like a range query rewrite.")
             return False

    print("✅ Passed!")
    return True

def main():
    print("🚀 Starting Golden Dataset Evaluation...")
    
    if not ensure_connection():
        print("❌ Aborting due to connection failure.")
        sys.exit(1)
        
    passed = 0
    total = len(SCENARIOS)
    
    for scenario in SCENARIOS:
        result = run_analysis(scenario)
        if verify_result(scenario, result):
            passed += 1
        time.sleep(1) # Small delay between scenarios
        
    print(f"\nSummary: {passed}/{total} scenarios passed.")
    
    if passed == total:
        print("\n✨ GOLDEN DATASET SUCCESS ✨")
        sys.exit(0)
    else:
        print("\n❌ SOME SCENARIOS FAILED ❌")
        sys.exit(1)

if __name__ == "__main__":
    main()
