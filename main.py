#!/usr/bin/env python3
"""
Call Center Query Agent - Main Entry Point
Uses OpenAI Agents SDK with a 2-agent loop:
1. SQL Agent - generates and executes queries
2. Evaluator Agent - validates results, iterates if needed
"""

import asyncio
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()  # Load .env from root

from agents import Runner
from src.agents.definitions import create_sql_agent, create_evaluator_agent

# Example query skeletons for harness/testing
EXAMPLE_QUERIES = [
    "How many calls did Theresa make in August?",
    "How many customers do we have named Joseph?",
    "What's the average call duration for VIP customers?",
    "Show me the top 5 employees by call count",
    "List all complaint calls from last month",
]


async def query(question: str, max_retries: int = 2) -> str:
    """Run a natural language query through the agent system with retry logic."""
    # Create agents
    sql_agent = create_sql_agent()
    evaluator = create_evaluator_agent(sql_agent)
    
    last_error = None
    
    for attempt in range(max_retries + 1):
        try:
            # Step 1: SQL Agent gets the data
            sql_result = await Runner.run(sql_agent, question)
            
            # Check for empty or error results
            output = sql_result.final_output or ""
            if "ERROR:" in output and attempt < max_retries:
                raise Exception(f"SQL Error: {output}")
            
            # Step 2: Evaluator checks and summarizes
            eval_prompt = f"""Original question: {question}

SQL Agent results:
{output}

Evaluate these results and provide a clear answer to the user's question.
If results are empty or seem wrong, explain what happened."""
            
            eval_result = await Runner.run(evaluator, eval_prompt)
            return eval_result.final_output
            
        except Exception as e:
            last_error = e
            if attempt < max_retries:
                wait_time = (attempt + 1) * 2  # 2s, 4s backoff
                print(f"  ⚠️  Attempt {attempt + 1} failed: {e}. Retrying in {wait_time}s...")
                await asyncio.sleep(wait_time)
            else:
                raise Exception(f"Query failed after {max_retries + 1} attempts: {last_error}")


async def main():
    """Interactive REPL."""
    print("=" * 60)
    print("  Call Center Query Agent")
    print("  Ask questions about your call data in plain English")
    print("=" * 60)
    
    if not os.getenv("OPENAI_API_KEY"):
        print("\n❌ OPENAI_API_KEY not set. Export it first.")
        return
    
    print("\nType your questions. Type 'exit' to quit.\n")
    
    while True:
        try:
            question = input("🔍 Ask: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n\nGoodbye!")
            break
        
        if not question:
            continue
        if question.lower() in ['exit', 'quit', 'q']:
            print("Goodbye!")
            break
        
        print("\n⏳ Processing...")
        try:
            answer = await query(question)
            print(f"\n✅ Answer:\n{answer}\n")
        except Exception as e:
            print(f"\n❌ Error: {e}\n")


if __name__ == "__main__":
    asyncio.run(main())
