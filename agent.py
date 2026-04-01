"""
agent.py — ReAct Agent core loop
ReAct = Reasoning + Acting, alternating until the task is complete.

Run directly for terminal testing:
    python agent.py
"""

import os
import anthropic
from dotenv import load_dotenv
from tools import run_tool
from tool_schemas import TOOL_SCHEMAS

load_dotenv()

MAX_ITERATIONS = 10
MODEL          = "claude-haiku-4-5-20251001"

SYSTEM_PROMPT = """You are a professional research assistant agent.

You have access to the following tools:
- web_search   : Search the internet for up-to-date information
- calculate    : Perform precise mathematical calculations
- read_file    : Read a file from the outputs/ directory
- write_file   : Save content to a file in outputs/
- get_datetime : Get the current date and time

Working principles:
1. When you receive a task, plan your steps before acting
2. Always use the calculate tool for any numerical computation — never mental math
3. After completing your analysis, proactively save a report using write_file
4. Structure your answers clearly using Markdown, and cite your sources
5. If one search is not enough, run additional searches with different keywords"""


def run_agent(
    task: str,
    on_tool_call=None,
    on_tool_result=None,
) -> str:
    """
    Execute a task using the ReAct agent loop.

    Args:
        task          : Plain-English task description from the user
        on_tool_call  : Optional callback fired when a tool is called.
                        Signature: (tool_name: str, tool_input: dict) -> None
        on_tool_result: Optional callback fired when a tool returns.
                        Signature: (tool_name: str, result: str) -> None

    Returns:
        The agent's final text answer as a string.
    """
    # Load API key — supports both .env (local) and environment variable (cloud)
    api_key = os.getenv("ANTHROPIC_API_KEY")
    client  = anthropic.Anthropic(api_key=api_key)

    messages = [{"role": "user", "content": task}]

    print(f"\n{'=' * 55}")
    print(f"Task: {task}")
    print(f"{'=' * 55}")

    for iteration in range(MAX_ITERATIONS):
        print(f"\n[Round {iteration + 1}]")

        # ── Call Claude ──────────────────────────────────
        response = client.messages.create(
            model      = MODEL,
            max_tokens = 4096,
            system     = SYSTEM_PROMPT,
            tools      = TOOL_SCHEMAS,
            messages   = messages,
        )

        # ── Append Claude's reply to message history ─────
        messages.append({
            "role"   : "assistant",
            "content": response.content,
        })

        # ── Print Claude's reasoning text ────────────────
        for block in response.content:
            if hasattr(block, "text") and block.text:
                preview = block.text[:200]
                ellipsis = "..." if len(block.text) > 200 else ""
                print(f"Claude: {preview}{ellipsis}")

        # ── Task complete: Claude stops calling tools ─────
        if response.stop_reason == "end_turn":
            final_text = ""
            for block in response.content:
                if hasattr(block, "text"):
                    final_text += block.text
            print(f"\nFinal answer: {final_text[:300]}...")
            return final_text

        # ── Tool calls: execute every requested tool ──────
        if response.stop_reason == "tool_use":
            tool_results = []

            for block in response.content:
                if block.type != "tool_use":
                    continue

                tool_name  = block.name
                tool_input = block.input

                print(f"  → Calling tool: {tool_name}({tool_input})")

                if on_tool_call:
                    on_tool_call(tool_name, tool_input)

                # Execute the tool
                result = run_tool(tool_name, tool_input)

                # Print a short preview
                preview = str(result)[:120].replace("\n", " ")
                ellipsis = "..." if len(str(result)) > 120 else ""
                print(f"  ← Result: {preview}{ellipsis}")

                if on_tool_result:
                    on_tool_result(tool_name, result)

                tool_results.append({
                    "type"       : "tool_result",
                    "tool_use_id": block.id,
                    "content"    : str(result),
                })

            # Return tool results to Claude for the next round
            messages.append({
                "role"   : "user",
                "content": tool_results,
            })

        else:
            print(f"Unexpected stop_reason: {response.stop_reason} — exiting loop")
            break

    return (
        "Maximum iterations reached. The task may be incomplete — "
        "try rephrasing or breaking it into smaller steps."
    )


# ── Terminal test ─────────────────────────────────────────
if __name__ == "__main__":
    result = run_agent(
        "Search for the latest developments in AI agents in 2025, "
        "summarize the top 3 trends, and save the report to a file."
    )
    print("\n" + "=" * 55)
    print("Done. Check the outputs/ directory for any saved reports.")
