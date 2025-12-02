"""
Audit codebase for SQL injection vulnerabilities.
Scans Python files for dangerous SQL construction patterns.
"""

import os
import re
from pathlib import Path
import sys

def find_sql_injection_risks(directory: str):
    """Find potential SQL injection vulnerabilities."""
    
    risks = []
    
    # Patterns that indicate potential SQL injection
    # We look for f-strings or format() calls containing SQL keywords
    dangerous_patterns = [
        (r'f".*SELECT.*\{.*\}.*"', "f-string with SELECT"),
        (r'f\'.*SELECT.*\{.*\}.*\'', "f-string with SELECT"),
        (r'f".*INSERT.*\{.*\}.*"', "f-string with INSERT"),
        (r'f\'.*INSERT.*\{.*\}.*\'', "f-string with INSERT"),
        (r'f".*UPDATE.*\{.*\}.*"', "f-string with UPDATE"),
        (r'f\'.*UPDATE.*\{.*\}.*\'', "f-string with UPDATE"),
        (r'f".*DELETE.*\{.*\}.*"', "f-string with DELETE"),
        (r'f\'.*DELETE.*\{.*\}.*\'', "f-string with DELETE"),
        (r'\.format\(.*\).*SELECT', ".format() with SELECT"),
        (r'execute\(f"', "execute with f-string"),
        (r'fetch.*\(f"', "fetch with f-string"),
    ]
    
    print(f"🔍 Scanning directory: {directory}")
    
    count = 0
    for py_file in Path(directory).rglob("*.py"):
        # Skip tests and migrations and scripts
        if "test" in str(py_file) or "migration" in str(py_file) or "scripts" in str(py_file):
            continue
            
        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')
                
                for i, line in enumerate(lines, 1):
                    # Skip comments
                    if line.strip().startswith('#'):
                        continue
                        
                    for pattern, description in dangerous_patterns:
                        if re.search(pattern, line, re.IGNORECASE):
                            # Filter out false positives (logging, etc)
                            if "logger" in line or "print" in line:
                                continue
                                
                            risks.append({
                                "file": str(py_file),
                                "line": i,
                                "code": line.strip(),
                                "risk": description
                            })
                            count += 1
        except Exception as e:
            print(f"Error reading {py_file}: {e}")
    
    return risks

if __name__ == "__main__":
    # Get backend directory
    backend_dir = os.path.join(os.path.dirname(__file__), '..', 'backend')
    
    risks = find_sql_injection_risks(backend_dir)
    
    if risks:
        print(f"\n⚠️  Found {len(risks)} potential SQL injection risks:\n")
        for risk in risks:
            print(f"File: {risk['file']}")
            print(f"Line: {risk['line']}")
            print(f"Risk: {risk['risk']}")
            print(f"Code: {risk['code']}")
            print("-" * 50)
        sys.exit(1)
    else:
        print("\n✅ No obvious SQL injection risks found!")
        sys.exit(0)
