"""
Database utilities for schema extraction and query execution.
"""

import sqlite3
from pathlib import Path
from functools import lru_cache

DB_PATH = Path(__file__).parent.parent.parent / "database" / "call_logs_october_1209.db"


@lru_cache(maxsize=1)
def get_schema() -> dict[str, list[str]]:
    """Get database schema as {table: [columns]} dict. Cached for performance."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row[0] for row in cursor.fetchall()]
    
    schema = {}
    for table in tables:
        cursor.execute(f"PRAGMA table_info({table});")
        schema[table] = [col[1] for col in cursor.fetchall()]
    
    conn.close()
    return schema


@lru_cache(maxsize=1)
def get_schema_context() -> str:
    """Get schema context string for LLM prompts. Cached."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row[0] for row in cursor.fetchall()]
    
    parts = ["DATABASE SCHEMA:"]
    
    for table in tables:
        cursor.execute(f"PRAGMA table_info({table});")
        columns = cursor.fetchall()
        col_defs = [f"{col[1]} ({col[2]})" for col in columns]
        parts.append(f"\nTable: {table}")
        parts.append(f"  Columns: {', '.join(col_defs)}")
        
        # Sample data
        cursor.execute(f"SELECT * FROM {table} LIMIT 2;")
        samples = cursor.fetchall()
        if samples:
            parts.append(f"  Sample: {samples[0]}")
    
    parts.append("\nRELATIONSHIPS:")
    parts.append("- calls.employee_id → employees.employee_id")
    parts.append("- calls.customer_id → customers.customer_id")  
    parts.append("- calls.call_type_id → call_types.type_id")
    parts.append("- calls.transferred_to → employees.employee_id")
    
    conn.close()
    return "\n".join(parts)


def execute_sql(sql: str) -> tuple[list[str], list[tuple]]:
    """Execute SQL and return (headers, rows)."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute(sql)
    headers = [desc[0] for desc in cursor.description]
    rows = cursor.fetchall()
    
    conn.close()
    return headers, rows
