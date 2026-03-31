"""
agent.py - Core Agent Logic
Implements the ReAct pattern: Reason -> Act -> Observe loop
"""

import json
import anthropic
from dotenv import load_dotenv
from typing import Generator
from tools import TOOLS, dispatch_tool

load_dotenv()

# ============================================================
# Agent Configuration
# ============================================================

MODEL = "claude-haiku-4-5-20251001"
MAX_ITERATIONS = 10  # Prevent infinite loops

SYSTEM_PROMPT = """You are a powerful AI assistant with access to the following tools:

1. **web_search** - Search the internet for real-time information
2. **file_operation** - Read and write local files (within the workspace directory)
3. **code_execute** - Execute Python code for computation and data processing

Working principles:
- For questions requiring real-time information, use web_search first
- When results need to be saved, use file_operation to write to a file
- For calculations or data processing tasks, use code_execute
- Complex tasks can be completed by combining multiple tools
- After each tool call, analyze the result before deciding the next step
- Keep your final answer concise and clear, highlighting key information

Constraints:
- file_operation is restricted to the ./workspace directory
- code_execute has a 10-second timeout; avoid infinite loops
- If a tool returns an error, try an alternative approach or inform the user
"""


# ============================================================
# Agent Core Class
# ============================================================

class MultiToolAgent:
    def __init__(self):
        self.client = anthropic.Anthropic()
        self.model = MODEL

    def run(self, user_message: str, chat_history: list = None) -> dict:
        """
        Run the agent synchronously and return the complete result.

        Returns:
            {
                "answer": str,        # Final answer
                "tool_calls": list,   # Tool call log
                "iterations": int,    # Number of iterations
                "success": bool
            }
        """
        messages = self._build_messages(user_message, chat_history)
        tool_calls_log = []
        iterations = 0

        while iterations < MAX_ITERATIONS:
            iterations += 1

            response = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=SYSTEM_PROMPT,
                tools=TOOLS,
                messages=messages
            )

            if response.stop_reason == "end_turn":
                # No tool calls, return text directly
                answer = self._extract_text(response)
                return {
                    "answer": answer,
                    "tool_calls": tool_calls_log,
                    "iterations": iterations,
                    "success": True
                }

            elif response.stop_reason == "tool_use":
                # Execute tool calls
                tool_results = []

                for block in response.content:
                    if block.type == "tool_use":
                        tool_name = block.name
                        tool_input = block.input
                        tool_use_id = block.id

                        print(f"  [Tool] Calling: {tool_name}")
                        print(f"  [Input] {json.dumps(tool_input, ensure_ascii=False)[:100]}...")

                        result_str = dispatch_tool(tool_name, tool_input)
                        result_data = json.loads(result_str)

                        tool_calls_log.append({
                            "tool": tool_name,
                            "input": tool_input,
                            "output": result_data,
                            "iteration": iterations
                        })

                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": tool_use_id,
                            "content": result_str
                        })

                        status = "OK" if result_data.get("success") else "FAILED"
                        print(f"  [Result] {status}")

                messages.append({"role": "assistant", "content": response.content})
                messages.append({"role": "user", "content": tool_results})

            else:
                # Other stop reasons (max_tokens, etc.)
                answer = self._extract_text(response)
                return {
                    "answer": answer or "Agent stopped due to reaching a limit",
                    "tool_calls": tool_calls_log,
                    "iterations": iterations,
                    "success": False
                }

        return {
            "answer": "Maximum iterations reached. Task incomplete.",
            "tool_calls": tool_calls_log,
            "iterations": iterations,
            "success": False
        }

    def run_stream(self, user_message: str, chat_history: list = None) -> Generator:
        """
        Run the agent with streaming, yielding status updates progressively.
        Used for SSE streaming responses.
        """
        messages = self._build_messages(user_message, chat_history)
        tool_calls_log = []
        iterations = 0

        yield {"type": "start", "message": "Agent is thinking..."}

        while iterations < MAX_ITERATIONS:
            iterations += 1

            response = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=SYSTEM_PROMPT,
                tools=TOOLS,
                messages=messages
            )

            if response.stop_reason == "end_turn":
                answer = self._extract_text(response)
                yield {"type": "answer", "content": answer}
                yield {
                    "type": "done",
                    "iterations": iterations,
                    "tool_calls_count": len(tool_calls_log)
                }
                return

            elif response.stop_reason == "tool_use":
                tool_results = []

                for block in response.content:
                    if block.type == "tool_use":
                        yield {
                            "type": "tool_start",
                            "tool": block.name,
                            "input": block.input
                        }

                        result_str = dispatch_tool(block.name, block.input)
                        result_data = json.loads(result_str)

                        tool_calls_log.append({
                            "tool": block.name,
                            "input": block.input,
                            "output": result_data,
                            "iteration": iterations
                        })

                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result_str
                        })

                        yield {
                            "type": "tool_end",
                            "tool": block.name,
                            "success": result_data.get("success", False)
                        }

                messages.append({"role": "assistant", "content": response.content})
                messages.append({"role": "user", "content": tool_results})

        yield {
            "type": "error",
            "message": "Maximum iterations reached"
        }

    # ============================================================
    # Helper Methods
    # ============================================================

    def _build_messages(self, user_message: str, chat_history: list = None) -> list:
        """Build the message list including chat history."""
        messages = []
        if chat_history:
            for turn in chat_history:
                messages.append({"role": "user", "content": turn["user"]})
                messages.append({"role": "assistant", "content": turn["assistant"]})
        messages.append({"role": "user", "content": user_message})
        return messages

    def _extract_text(self, response) -> str:
        """Extract plain text content from a response."""
        texts = []
        for block in response.content:
            if hasattr(block, "text"):
                texts.append(block.text)
        return "\n".join(texts)
