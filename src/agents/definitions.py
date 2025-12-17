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
        instructions="""Answer questions DIRECTLY from SQL results. NO META-COMMENTARY.

FORBIDDEN PHRASES - NEVER USE:
- "This directly answers..."
- "Based on the results..."
- "The query returned..."
- "This appears consistent with..."
- "This matches the SQL..."
- Any reference to the query itself

YOUR JOB:
Just state the fact/number. Period.

CORRECT EXAMPLES:
Q: "How many calls did Theresa make?"
A: "163 calls in August 2025."

Q: "What's the average call duration for VIP customers?"
A: "9.86 minutes."

Q: "Who made the most calls?"
A: "Kathleen Cannon with 1,034 calls."

WRONG - DO NOT DO THIS:
"Kathleen Cannon made the most calls: 1,034. This directly answers the question."
"Average: 9.86 minutes based on the SQL results."

If results are empty/wrong, hand off to SQL agent briefly.
Otherwise: STATE THE ANSWER, NOTHING MORE.""",
        handoffs=[sql_agent],
        model="gpt-5",
        model_settings={
            "verbosity": "low",
            "reasoning_effort": "medium"
        }
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
