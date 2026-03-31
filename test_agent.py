"""
test_agent.py - Agent Test Script
Calls the agent directly (without FastAPI) for development and debugging.
"""

import os
import json
from dotenv import load_dotenv
from agent import MultiToolAgent

load_dotenv()


def print_separator(title: str = ""):
    width = 60
    if title:
        print(f"\n{'='*10} {title} {'='*(width - len(title) - 12)}")
    else:
        print("=" * width)


def print_tool_calls(tool_calls: list):
    if not tool_calls:
        print("  (No tool calls)")
        return
    for i, call in enumerate(tool_calls, 1):
        print(f"\n  [{i}] Tool: {call['tool']}  (iteration {call['iteration']})")
        print(f"      Input:  {json.dumps(call['input'], ensure_ascii=False)[:120]}")
        success = call['output'].get('success', False)
        print(f"      Result: {'OK' if success else 'FAILED'}")


def run_test(agent: MultiToolAgent, test_name: str, message: str):
    print_separator(f"Test: {test_name}")
    print(f"Task: {message}\n")

    result = agent.run(message)

    print("\n[Answer]")
    print(result["answer"])

    print("\n[Tool Calls]")
    print_tool_calls(result["tool_calls"])

    status = "SUCCESS" if result["success"] else "FAILED"
    print(f"\n[Stats] Iterations: {result['iterations']} | Status: {status}")


def main():
    print("Multi-Tool AI Agent - Test Runner")
    print_separator()

    if not os.getenv("ANTHROPIC_API_KEY"):
        print("ERROR: ANTHROPIC_API_KEY environment variable not found.")
        print("Please set it in a .env file: ANTHROPIC_API_KEY=your_key_here")
        return

    agent = MultiToolAgent()

    # ---- Test Cases ----

    # Test 1: Code execution (no network needed)
    run_test(
        agent,
        "Code Execution",
        "Calculate the first 15 numbers of the Fibonacci sequence and count how many are even."
    )

    # Test 2: File read/write
    run_test(
        agent,
        "File Operations",
        "Create a file named hello.txt with today's date and an encouraging message, then read it back to confirm."
    )

    # Test 3: Web search (requires internet)
    run_test(
        agent,
        "Web Search",
        "Search for the main new features in Python 3.13 and give me 3 key points."
    )

    # Test 4: Combined task
    run_test(
        agent,
        "Combined Task",
        "Use Python code to find all prime numbers up to 100, then save the results to workspace/primes.txt."
    )

    print_separator("All tests complete")


if __name__ == "__main__":
    main()
