"""SQL tools for the search agent."""

import re
import logfire
from agents import function_tool
from src.utils.database import get_schema, execute_sql


def validate_sql(sql: str) -> tuple[bool, str]:
    """Validate SQL query for safety."""
    sql_upper = sql.upper().strip()
    
    if not sql_upper.startswith("SELECT"):
        return False, "Only SELECT queries allowed"
    
    dangerous = ["INSERT", "UPDATE", "DELETE", "DROP", "CREATE", "ALTER", 
                 "TRUNCATE", "EXEC", "--", ";--"]
    for kw in dangerous:
        if kw in sql_upper:
            return False, f"Blocked keyword: {kw}"
    
    # Check multiple statements
    sql_no_strings = re.sub(r"'[^']*'", "", sql)
    if ";" in sql_no_strings.strip().rstrip(";"):
        return False, "Multiple statements not allowed"
    
    # Validate tables
    schema = get_schema()
    table_pattern = r'\b(?:FROM|JOIN)\s+(\w+)'
    found_tables = re.findall(table_pattern, sql, re.IGNORECASE)
    
    valid_tables = [t.lower() for t in schema.keys()]
    for table in found_tables:
        if table.lower() not in valid_tables:
            return False, f"Unknown table: {table}"
    
    return True, "Valid"


@function_tool
def run_sql_query(sql_query: str) -> str:
    """
    Execute a SQL query against the call center database.
    
    Args:
        sql_query: A valid SELECT SQL query
        
    Returns:
        Query results as formatted text, or error message
    """
    # Log the generated SQL query
    logfire.info("SQL Query Generated", sql=sql_query)
    
    # Validate
    with logfire.span("sql_validation"):
        is_valid, msg = validate_sql(sql_query)
        logfire.info("SQL Validation", is_valid=is_valid, message=msg)
        
    if not is_valid:
        logfire.warn("SQL Validation Failed", error=msg, sql=sql_query)
        return f"ERROR: {msg}"
    
    try:
        # Execute and log DB interaction
        with logfire.span("database_execution", sql=sql_query):
            headers, rows = execute_sql(sql_query)
            logfire.info("DB Query Result", 
                        row_count=len(rows), 
                        columns=headers,
                        sql=sql_query)
        
        if not rows:
            logfire.info("Query returned no results", sql=sql_query)
            return "No results found."
        
        # Format as simple table
        result = [" | ".join(headers)]
        result.append("-" * len(result[0]))
        
        for row in rows[:50]:  # Limit output
            result.append(" | ".join(str(v) if v is not None else "NULL" for v in row))
        
        if len(rows) > 50:
            result.append(f"... and {len(rows) - 50} more rows")
        
        result.append(f"\nTotal: {len(rows)} row(s)")
        
        formatted_result = "\n".join(result)
        logfire.info("Query Result Formatted", preview=formatted_result[:500])
        return formatted_result
        
    except Exception as e:
        logfire.error("SQL Execution Failed", error=str(e), sql=sql_query)
        return f"ERROR: {e}"
