"""
Agent definitions for the call center query system.

Architecture:
- SQL Agent: Generates and executes SQL queries
- Evaluator Agent: Reviews results for completeness, hands back to SQL if needed
"""

from datetime import datetime
from agents import Agent
from src.tools.sql_tools import run_sql_query
from src.utils.database import get_schema_context


def create_sql_agent() -> Agent:
    """Create the SQL search agent with database context."""
    schema_context = get_schema_context()
    current_date = datetime.now().strftime("%Y-%m-%d")
    current_year = datetime.now().year
    current_month = datetime.now().strftime("%B")
    
    # Calculate 10 business days ago (roughly 14 calendar days)
    from datetime import timedelta
    ten_biz_days_ago = (datetime.now() - timedelta(days=14)).strftime("%Y-%m-%d")
    
    return Agent(
        name="SQL Search Agent",
        instructions=f"""You are a SQL expert for a call center database. Your job is to:
1. Understand the user's natural language question
2. Generate the appropriate SQL query
3. Execute it using the run_sql_query tool
4. Return the results

CURRENT DATE CONTEXT:
- Today's date: {current_date}
- Current year: {current_year}
- Current month: {current_month}
- Last 10 business days: since {ten_biz_days_ago}
- For "recent" or "latest" queries: use last 10 business days as default

{schema_context}

IMPORTANT NOTES:
- Names may have variations (e.g., "Theresa", "Teresa", "THERESA") - use LIKE with wildcards
- Dates: call_date is DATE format (YYYY-MM-DD), use strftime for month/year filtering
- For "August" queries without year: assume {current_year} or most recent August
- For "last month": use strftime to get month-1 from current date
- VIP customers: vip_status = 1
- transferred_to IS NOT NULL means call was transferred
- Always JOIN tables properly when accessing related data
- For "all" results: remove LIMIT or use high limit, include total count

Generate a single SQL query and execute it. Be precise with JOINs and WHERE clauses.""",
        tools=[run_sql_query],
        model="gpt-5"
    )


def create_evaluator_agent(sql_agent: Agent) -> Agent:
    """Create the evaluator agent that checks results quality."""
    
    return Agent(
        name="Result Evaluator",
        instructions="""You provide DIRECT answers from SQL query results. NO FLUFF.

STRICT RULES:
1. Answer the question in ONE sentence if possible
2. Just state the number/fact - don't explain the query
3. NO phrases like "The query returns...", "Based on the results...", "This directly answers..."
4. Only add context if results are empty or ambiguous

EXAMPLES:
❌ BAD: "The query returned 163 calls. This directly answers the question about Theresa's August calls."
✅ GOOD: "163 calls in August 2025."

❌ BAD: "Based on the SQL results, VIP customers had an average duration of 24.5 minutes."
✅ GOOD: "Average: 24.5 minutes."

If results are clearly wrong/empty, hand off to SQL agent with brief fix request.
Otherwise: JUST ANSWER THE QUESTION.""",
        handoffs=[sql_agent],
        model="gpt-5"
    )


def create_triage_agent(sql_agent: Agent, evaluator_agent: Agent) -> Agent:
    """Create the main triage agent that routes queries."""
    
    return Agent(
        name="Query Router",
        instructions="""You are the entry point for call center data queries.

Route all data questions to the SQL Search Agent first.
After SQL agent returns, hand off to the Evaluator to verify results.

For simple questions, SQL agent can answer directly.
For complex questions that might need refinement, the evaluator will iterate.""",
        handoffs=[sql_agent, evaluator_agent],
        model="gpt-5"
    )
