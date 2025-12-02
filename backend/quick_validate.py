#!/usr/bin/env python3
"""
Quick validation script to check if the stateless backend changes are correct.
This runs without needing database connection.
"""

import ast
import sys
from pathlib import Path

def check_syntax(file_path):
    """Check if a Python file has valid syntax."""
    try:
        with open(file_path, 'r') as f:
            code = f.read()
        ast.parse(code)
        return True, None
    except SyntaxError as e:
        return False, str(e)

def check_file_structure(file_path):
    """Check if file has expected structure."""
    with open(file_path, 'r') as f:
        content = f.read()
    return content

def main():
    """Run validation checks."""
    backend_dir = Path(__file__).parent
    
    print("="*60)
    print("OptiSchema Stateless Backend - Quick Validation")
    print("="*60)
    
    # Files to check
    files_to_check = [
        ("analysis_results_service.py", [
            "class AnalysisResultsService",
            "async def store_analysis_result",
            "async def get_recent_analyses",
            "tenant_id"
        ]),
        ("analysis/pipeline.py", [
            "from analysis_results_service import AnalysisResultsService",
            "async def get_analysis_cache",
            "async def get_recommendations_cache",
            "await AnalysisResultsService"
        ]),
        ("websocket.py", [
            "tenant_id",
            "async def connect(self, websocket: WebSocket, tenant_id",
            "async def broadcast(self, message: WebSocketMessage, subscription_type: str = None, tenant_id",
            "websocket.query_params.get(\"tenant_id\")"
        ]),
        ("routers/analysis.py", [
            "await get_analysis_cache()",
        ]),
        ("routers/suggestions.py", [
            "await get_recommendations_cache()",
        ]),
    ]
    
    all_passed = True
    
    for file_name, expected_patterns in files_to_check:
        file_path = backend_dir / file_name
        
        print(f"\n📄 Checking {file_name}...")
        
        # Check if file exists
        if not file_path.exists():
            print(f"   ❌ File not found!")
            all_passed = False
            continue
        
        # Check syntax
        valid, error = check_syntax(file_path)
        if not valid:
            print(f"   ❌ Syntax error: {error}")
            all_passed = False
            continue
        else:
            print(f"   ✅ Syntax valid")
        
        # Check for expected patterns
        content = check_file_structure(file_path)
        missing_patterns = []
        
        for pattern in expected_patterns:
            if pattern not in content:
                missing_patterns.append(pattern)
        
        if missing_patterns:
            print(f"   ⚠️  Missing expected patterns:")
            for pattern in missing_patterns:
                print(f"      - {pattern}")
            all_passed = False
        else:
            print(f"   ✅ All expected patterns found")
    
    # Check for removed global variables
    print(f"\n📄 Checking analysis/pipeline.py for removed globals...")
    pipeline_path = backend_dir / "analysis/pipeline.py"
    with open(pipeline_path, 'r') as f:
        pipeline_content = f.read()
    
    bad_patterns = [
        "analysis_cache: List[AnalysisResult] = []",
        "recommendations_cache: List[Any] = []",
        "last_analysis_time: Optional[datetime] = None"
    ]
    
    found_bad = []
    for pattern in bad_patterns:
        if pattern in pipeline_content:
            found_bad.append(pattern)
    
    if found_bad:
        print(f"   ❌ Found global state that should be removed:")
        for pattern in found_bad:
            print(f"      - {pattern}")
        all_passed = False
    else:
        print(f"   ✅ No global state variables found (good!)")
    
    # Summary
    print("\n" + "="*60)
    if all_passed:
        print("✅ All validation checks PASSED!")
        print("   The stateless backend changes look good.")
        print("   Ready to start with Docker Compose.")
    else:
        print("❌ Some validation checks FAILED!")
        print("   Please review the issues above.")
    print("="*60)
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())
