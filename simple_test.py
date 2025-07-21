#!/usr/bin/env python3
"""
Simple test for AI prompt - bypasses backend framework to test directly.
"""

import json

# Mock the LLM response to test JSON parsing
MOCK_LLM_RESPONSE = '''```json
{
  "title": "Add Missing Index on users.email Column",
  "description": "Based on actual metrics, this query exhibits high execution time (8.34ms average) with 150 calls representing 2.3% of total database time. The execution plan shows a sequential scan on the users table with a filter on the email column, removing 9,850 rows to return just 1 result. This indicates a missing index on the email column, causing the database to scan the entire table for each lookup.",
  "sql_fix": "CREATE INDEX CONCURRENTLY idx_users_email ON users(email);",
  "rollback_sql": "DROP INDEX CONCURRENTLY idx_users_email;",
  "confidence": 90,
  "estimated_improvement": "75%",
  "risk_level": "Low"
}
```'''

def parse_llm_response(content: str) -> dict:
    """Test the JSON parsing logic from the LLM module."""
    try:
        # Extract JSON from content if it's wrapped in markdown code blocks
        if '```json' in content:
            json_start = content.find('```json') + 7
            json_end = content.find('```', json_start)
            if json_end != -1:
                content = content[json_start:json_end].strip()
        elif '```' in content:
            # Handle cases where it's just wrapped in ```
            lines = content.split('\n')
            in_code_block = False
            json_lines = []
            for line in lines:
                if line.strip() == '```':
                    in_code_block = not in_code_block
                    continue
                if in_code_block:
                    json_lines.append(line)
            content = '\n'.join(json_lines)
        
        # Parse the JSON
        result = json.loads(content)
        
        # Validate required fields and set defaults
        result = {
            "title": result.get("title", "Optimization Recommendation"),
            "description": result.get("description", "No description provided"),
            "sql_fix": result.get("sql_fix"),
            "rollback_sql": result.get("rollback_sql"),
            "confidence": result.get("confidence", 75),
            "estimated_improvement": result.get("estimated_improvement", "Unknown"),
            "risk_level": result.get("risk_level", "Medium")
        }
        
        return result
        
    except Exception as e:
        print(f"JSON parsing failed: {e}")
        print(f"Content being parsed: {repr(content)}")
        raise

def main():
    print("🧪 Testing JSON Parsing Logic\n")
    
    try:
        result = parse_llm_response(MOCK_LLM_RESPONSE)
        print("✅ JSON Parsing: SUCCESS")
        print(f"📋 Title: {result['title']}")
        print(f"🔧 SQL Fix: {result['sql_fix']}")
        print(f"↩️  Rollback: {result['rollback_sql']}")
        print(f"🎯 Confidence: {result['confidence']}%")
        print(f"📈 Improvement: {result['estimated_improvement']}")
        print(f"⚠️  Risk: {result['risk_level']}")
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        
    # Test environment variables
    import os
    print(f"\n🔧 Environment Check:")
    print(f"   GEMINI_API_KEY: {'✓ Set' if os.getenv('GEMINI_API_KEY') else '✗ Missing'}")
    print(f"   DEEPSEEK_API_KEY: {'✓ Set' if os.getenv('DEEPSEEK_API_KEY') else '✗ Missing'}")
    print(f"   LLM_PROVIDER: {os.getenv('LLM_PROVIDER', 'Not set')}")

if __name__ == "__main__":
    main() 