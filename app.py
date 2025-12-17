"""
Call Center Query Agent - FastAPI App
REST API for natural language queries with Logfire observability and session management.
"""

import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

import logfire
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from agents import Runner, SQLiteSession

from src.agents.definitions import create_sql_agent, create_evaluator_agent

# Configure Logfire with token from env
logfire.configure(
    token=os.getenv("LOGFIRE_TOKEN"),
    send_to_logfire=True
)
logfire.instrument_openai_agents()

# Create FastAPI app
app = FastAPI(
    title="Call Center Query Agent",
    description="Natural language queries for call center data",
    version="1.0.0"
)

# Instrument FastAPI with Logfire
logfire.instrument_fastapi(app)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Session database path
SESSION_DB = "sessions/conversations.db"


class QueryRequest(BaseModel):
    question: str
    session_id: str | None = None


class QueryResponse(BaseModel):
    question: str
    answer: str
    session_id: str
    success: bool


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "ok", "service": "call-center-agent"}


@app.get("/health")
async def health():
    """Health check."""
    return {"status": "healthy"}


@app.get("/ui")
async def ui():
    """Serve the web UI."""
    return FileResponse("static/index.html")


@app.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    """
    Execute a natural language query against the call center database.
    Supports session context for follow-up questions.
    """
    # Generate or use existing session_id
    session_id = request.session_id or str(uuid.uuid4())
    
    with logfire.span("query_execution", question=request.question, session_id=session_id):
        try:
            # Create session for conversation context
            session = SQLiteSession(session_id, SESSION_DB)
            logfire.info("Session", session_id=session_id, is_new=(request.session_id is None))
            
            # Create agents
            sql_agent = create_sql_agent()
            evaluator = create_evaluator_agent(sql_agent)
            
            # Step 1: SQL Agent with session context
            with logfire.span("sql_agent_run"):
                sql_result = await Runner.run(
                    sql_agent, 
                    request.question,
                    session=session
                )
                output = sql_result.final_output or ""
            
            # Step 2: Evaluator with session context
            with logfire.span("evaluator_run"):
                eval_prompt = f"""Original question: {request.question}

SQL Agent results:
{output}

Evaluate and summarize the answer."""
                
                eval_result = await Runner.run(
                    evaluator, 
                    eval_prompt,
                    session=session
                )
            
            return QueryResponse(
                question=request.question,
                answer=eval_result.final_output,
                session_id=session_id,
                success=True
            )
            
        except Exception as e:
            logfire.error("Query failed", error=str(e), session_id=session_id)
            raise HTTPException(status_code=500, detail=str(e))


@app.delete("/session/{session_id}")
async def clear_session(session_id: str):
    """Clear a session's conversation history."""
    try:
        session = SQLiteSession(session_id, SESSION_DB)
        await session.clear_session()
        logfire.info("Session cleared", session_id=session_id)
        return {"status": "cleared", "session_id": session_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/examples")
async def examples():
    """Get example queries."""
    return {
        "examples": [
            "How many calls did Theresa make in August?",
            "How many customers do we have named Joseph?",
            "What's the average call duration for VIP customers?",
            "Show me the top 5 employees by call count",
            "List all complaint calls from last month",
        ]
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

