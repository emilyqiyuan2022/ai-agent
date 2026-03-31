"""
main.py - FastAPI REST Interface
Provides HTTP API for the Agent, supporting both synchronous and SSE streaming responses.
"""

import json
import asyncio
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from agent import MultiToolAgent


# ============================================================
# Application Initialization
# ============================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle management."""
    print("Starting Multi-Tool AI Agent API...")
    app.state.agent = MultiToolAgent()
    print("Agent initialized successfully.")
    yield
    print("API service shutting down.")


app = FastAPI(
    title="Multi-Tool AI Agent API",
    description="""
    ## Multi-Tool AI Agent REST Interface

    An intelligent agent built on Claude Tool Use, supporting:
    - **Web Search**: Real-time search via DuckDuckGo
    - **File Operations**: Read/write files within the workspace directory
    - **Code Execution**: Python sandboxed execution environment

    **Two calling modes:**
    1. `POST /agent/run` - Synchronous call, waits for the complete result
    2. `POST /agent/stream` - SSE streaming response, see tool calls in real time
    """,
    version="1.0.0",
    lifespan=lifespan
)

# CORS configuration (allow all origins in development)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# Request / Response Models
# ============================================================

class ChatTurn(BaseModel):
    user: str = Field(description="User message")
    assistant: str = Field(description="Assistant reply")


class AgentRequest(BaseModel):
    message: str = Field(
        description="User question or task description",
        min_length=1,
        max_length=2000
    )
    chat_history: Optional[list[ChatTurn]] = Field(
        default=None,
        description="Previous conversation turns (optional), used for multi-turn dialogue"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "message": "Search for the latest Python 3.13 features and save the results to a file.",
                "chat_history": []
            }
        }
    }


class ToolCallInfo(BaseModel):
    tool: str
    input: dict
    output: dict
    iteration: int


class AgentResponse(BaseModel):
    answer: str = Field(description="Agent's final answer")
    tool_calls: list[ToolCallInfo] = Field(description="Tool call log")
    iterations: int = Field(description="Number of agent iterations")
    success: bool = Field(description="Whether the task completed successfully")


# ============================================================
# API Routes
# ============================================================

@app.get("/", tags=["Health Check"])
async def root():
    """Root endpoint, returns service status."""
    return {
        "service": "Multi-Tool AI Agent API",
        "status": "running",
        "version": "1.0.0",
        "endpoints": {
            "sync": "POST /agent/run",
            "stream": "POST /agent/stream",
            "docs": "GET /docs"
        }
    }


@app.get("/health", tags=["Health Check"])
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "agent": "ready"}


@app.post(
    "/agent/run",
    response_model=AgentResponse,
    tags=["Agent"],
    summary="Synchronous Agent Call",
    description="Send a task to the agent and wait for the complete result. Best for short tasks or when a full result is needed."
)
async def run_agent(request: AgentRequest):
    """
    Synchronous Agent Call

    - Blocks until the agent completes all tool calls
    - Returns the final answer and complete tool call log
    - Recommended when the task requires fewer than 3 tool calls
    """
    try:
        history = None
        if request.chat_history:
            history = [{"user": t.user, "assistant": t.assistant}
                       for t in request.chat_history]

        # Run the synchronous agent in a thread pool to avoid blocking the event loop
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: app.state.agent.run(request.message, history)
        )

        return AgentResponse(**result)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent execution failed: {str(e)}")


@app.post(
    "/agent/stream",
    tags=["Agent"],
    summary="Streaming Agent Call (SSE)",
    description="Returns the agent's reasoning process and tool call status in real time via Server-Sent Events."
)
async def stream_agent(request: AgentRequest):
    """
    Streaming Agent Call (Server-Sent Events)

    Pushes the following event types in real time:
    - `start`: Agent begins processing
    - `tool_start`: A tool call begins (includes tool name and input)
    - `tool_end`: A tool call completes (includes success/failure status)
    - `answer`: The final answer content
    - `done`: Task complete (includes statistics)
    - `error`: An error occurred

    **Frontend consumption example:**
    ```javascript
    const es = new EventSource('/agent/stream');
    es.onmessage = (e) => {
      const data = JSON.parse(e.data);
      console.log(data.type, data);
    };
    ```
    """
    history = None
    if request.chat_history:
        history = [{"user": t.user, "assistant": t.assistant}
                   for t in request.chat_history]

    async def generate():
        try:
            loop = asyncio.get_event_loop()
            queue = asyncio.Queue()

            def run_agent_sync():
                """Run the agent in a thread and push events to the queue."""
                for event in app.state.agent.run_stream(request.message, history):
                    loop.call_soon_threadsafe(queue.put_nowait, event)
                loop.call_soon_threadsafe(queue.put_nowait, None)  # Sentinel

            loop.run_in_executor(None, run_agent_sync)

            while True:
                event = await queue.get()
                if event is None:
                    break
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

        except Exception as e:
            error_event = {"type": "error", "message": str(e)}
            yield f"data: {json.dumps(error_event, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no"  # Disable Nginx buffering
        }
    )


@app.get(
    "/tools",
    tags=["Tool Info"],
    summary="List available tools"
)
async def list_tools():
    """Returns all tools supported by the agent along with their schemas."""
    from tools import TOOLS
    return {
        "tools_count": len(TOOLS),
        "tools": TOOLS
    }


@app.get(
    "/workspace",
    tags=["Tool Info"],
    summary="List workspace directory contents"
)
async def list_workspace():
    """Lists files in the workspace directory (the sandbox for agent file operations)."""
    from tools import execute_file_operation
    result = execute_file_operation("list", ".")
    return result


# ============================================================
# Entry Point
# ============================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,       # Auto-restart on code changes (development mode)
        log_level="info"
    )
