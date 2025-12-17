#!/usr/bin/env python3
"""
Standalone agent tests - test each agent individually.
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from agents import Runner
from src.agents.definitions import create_sql_agent, create_evaluator_agent
from src.tools.sql_tools import run_sql_query, validate_sql
from src.utils.database import get_schema, get_schema_context


def test_database_utils():
    """Test database utilities."""
    print("\n" + "="*50)
    print("TEST 1: Database Utilities")
    print("="*50)
    
    # Test schema caching
    print("\n1a. Testing schema extraction (cached):")
    schema = get_schema()
    print(f"  ✓ Found {len(schema)} tables: {list(schema.keys())}")
    
    # Test context
    print("\n1b. Testing schema context:")
    context = get_schema_context()
    print(f"  ✓ Context length: {len(context)} chars")
    print(f"  ✓ First 200 chars:\n    {context[:200]}...")
    
    return True


def test_sql_validation():
    """Test SQL validation."""
    print("\n" + "="*50)
    print("TEST 2: SQL Validation (Injection Prevention)")
    print("="*50)
    
    test_cases = [
        ("SELECT * FROM calls LIMIT 10", True, "Basic SELECT"),
        ("SELECT COUNT(*) FROM employees", True, "Aggregation"),
        ("SELECT * FROM calls; DROP TABLE calls;", False, "SQL Injection"),
        ("DELETE FROM calls WHERE 1=1", False, "DELETE attempt"),
        ("SELECT * FROM fake_table", False, "Unknown table"),
        ("SELECT * FROM calls WHERE notes LIKE '%test%'", True, "LIKE clause"),
    ]
    
    for sql, expected_valid, desc in test_cases:
        is_valid, msg = validate_sql(sql)  # Only takes 1 arg
        status = "✓" if is_valid == expected_valid else "✗"
        print(f"  {status} {desc}: valid={is_valid} (expected {expected_valid})")
        if not is_valid:
            print(f"      Reason: {msg}")
    
    return True


async def test_sql_tool():
    """Test the SQL tool directly."""
    print("\n" + "="*50)
    print("TEST 3: SQL Tool Execution")
    print("="*50)
    
    # Test via direct database query (bypassing tool wrapper)
    from src.utils.database import execute_sql
    
    headers, rows = execute_sql("SELECT COUNT(*) as total FROM calls")
    print(f"  Query: SELECT COUNT(*) as total FROM calls")
    print(f"  Headers: {headers}")
    print(f"  Result: {rows[0][0]} total calls")
    
    return True


async def test_sql_agent():
    """Test SQL agent standalone."""
    print("\n" + "="*50)
    print("TEST 4: SQL Agent (Requires API Key)")
    print("="*50)
    
    if not os.getenv("OPENAI_API_KEY"):
        print("  ⚠ Skipped - OPENAI_API_KEY not set")
        return False
    
    sql_agent = create_sql_agent()
    print(f"  Agent: {sql_agent.name}")
    print(f"  Model: {sql_agent.model}")
    print(f"  Tools: {[t.name for t in sql_agent.tools]}")
    
    # Test query
    question = "How many total calls are in the database?"
    print(f"\n  Testing: '{question}'")
    
    result = await Runner.run(sql_agent, question)
    print(f"  Result: {result.final_output[:500]}...")
    
    return True


async def test_evaluator_agent():
    """Test evaluator agent standalone."""
    print("\n" + "="*50)
    print("TEST 5: Evaluator Agent (Requires API Key)")
    print("="*50)
    
    if not os.getenv("OPENAI_API_KEY"):
        print("  ⚠ Skipped - OPENAI_API_KEY not set")
        return False
    
    sql_agent = create_sql_agent()
    evaluator = create_evaluator_agent(sql_agent)
    
    print(f"  Agent: {evaluator.name}")
    print(f"  Model: {evaluator.model}")
    print(f"  Handoffs: {[h.name for h in evaluator.handoffs]}")
    
    # Test evaluation
    eval_prompt = """Original question: How many calls in the database?

SQL Agent results:
total
-----
50005

Total: 1 row(s)

Evaluate and summarize."""
    
    print(f"\n  Testing evaluation...")
    result = await Runner.run(evaluator, eval_prompt)
    print(f"  Result: {result.final_output[:500]}...")
    
    return True


async def run_all_tests():
    """Run all tests."""
    print("\n🧪 STANDALONE AGENT TESTS")
    print("=" * 50)
    
    # Sync tests
    test_database_utils()
    test_sql_validation()
    await test_sql_tool()
    
    # Async tests (require API key)
    await test_sql_agent()
    await test_evaluator_agent()
    
    print("\n" + "="*50)
    print("✅ All tests completed!")
    print("="*50)


if __name__ == "__main__":
    asyncio.run(run_all_tests())
