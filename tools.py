"""
tools.py — Tool implementations and dispatcher for the Research Agent

Five tools, all free — no extra API keys required:
  - web_search   : DuckDuckGo search (pip install duckduckgo-search)
  - calculate    : Safe math evaluation
  - read_file    : Read from outputs/ directory
  - write_file   : Write to outputs/ directory
  - get_datetime : Current timestamp

Run standalone to test all tools:
    python tools.py
"""

import os
import math
from datetime import datetime
from pathlib import Path
from duckduckgo_search import DDGS

OUTPUT_DIR = "./outputs"
Path(OUTPUT_DIR).mkdir(exist_ok=True)


# ─────────────────────────────────────────────
# Tool implementations
# ─────────────────────────────────────────────

def web_search(query: str, max_results: int = 4) -> str:
    """
    Search the web using DuckDuckGo. Free, no API key needed.

    Args:
        query      : Search keywords (3–10 words works best)
        max_results: Number of results to return (default 4, max 8)

    Returns:
        Formatted string with title, snippet, and URL for each result.
    """
    try:
        results = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results):
                results.append(
                    f"Title  : {r['title']}\n"
                    f"Snippet: {r['body']}\n"
                    f"URL    : {r['href']}"
                )
        if not results:
            return "No results found. Try different keywords."
        return "\n\n---\n\n".join(results)
    except Exception as e:
        return f"Search error: {e}. Check your internet connection."


def calculate(expression: str) -> str:
    """
    Safely evaluate a mathematical expression.

    Supports: arithmetic, percentages, and math library functions.
    Examples:
        calculate("(100 + 200) * 0.15")
        calculate("math.sqrt(144)")
        calculate("math.log(1000, 10)")

    Args:
        expression: A Python math expression as a string.

    Returns:
        A string showing the expression and its result.
    """
    try:
        allowed = {
            "__builtins__": {},
            "math" : math,
            "abs"  : abs,
            "round": round,
            "min"  : min,
            "max"  : max,
            "sum"  : sum,
            "pow"  : pow,
            "int"  : int,
            "float": float,
        }
        result = eval(expression, allowed)
        return f"{expression} = {result}"
    except ZeroDivisionError:
        return "Error: division by zero."
    except Exception as e:
        return f"Calculation error: {e}. Check the expression format."


def read_file(filename: str) -> str:
    """
    Read a file from the outputs/ directory.

    Args:
        filename: File name only — no path needed (e.g. 'report.md')

    Returns:
        File contents as a string, or an error message with a list
        of available files if the file does not exist.
    """
    filepath = Path(OUTPUT_DIR) / Path(filename).name
    if not filepath.exists():
        existing = [f.name for f in Path(OUTPUT_DIR).iterdir() if f.is_file()]
        hint = f"Available files: {existing}" if existing else "outputs/ is empty."
        return f"File not found: {filename}. {hint}"
    try:
        return filepath.read_text(encoding="utf-8")
    except Exception as e:
        return f"Read error: {e}"


def write_file(filename: str, content: str) -> str:
    """
    Write content to a file in the outputs/ directory.

    Args:
        filename: File name (e.g. 'report_20250401.md').
                  Path traversal characters are stripped for safety.
        content : Text content to write (Markdown supported).

    Returns:
        Confirmation string with file path and size.
    """
    # Safety: strip any path components, write only to OUTPUT_DIR
    filepath = Path(OUTPUT_DIR) / Path(filename).name
    try:
        filepath.write_text(content, encoding="utf-8")
        size_kb = filepath.stat().st_size / 1024
        return (
            f"File saved: {filepath} "
            f"({size_kb:.1f} KB, {len(content)} characters)"
        )
    except Exception as e:
        return f"Write error: {e}"


def get_datetime() -> str:
    """
    Return the current date and time.
    Useful for adding timestamps to generated reports.
    """
    return datetime.now().strftime("%B %d, %Y  %H:%M:%S")


# ─────────────────────────────────────────────
# Dispatcher — single entry point for agent.py
# ─────────────────────────────────────────────

TOOL_FUNCTIONS = {
    "web_search"  : web_search,
    "calculate"   : calculate,
    "read_file"   : read_file,
    "write_file"  : write_file,
    "get_datetime": get_datetime,
}


def run_tool(name: str, inputs: dict) -> str:
    """
    Execute a tool by name with the given inputs.

    This is the single entry point called by agent.py.
    Claude passes the tool name and a dict of arguments;
    this function routes to the correct implementation.

    Args:
        name  : Tool name (must match a key in TOOL_FUNCTIONS)
        inputs: Dict of keyword arguments for the tool function

    Returns:
        Tool result as a plain string.
    """
    if name not in TOOL_FUNCTIONS:
        available = list(TOOL_FUNCTIONS.keys())
        return f"Unknown tool: '{name}'. Available tools: {available}"

    func = TOOL_FUNCTIONS[name]

    # get_datetime takes no arguments
    if name == "get_datetime":
        return func()

    return func(**inputs)


# ─────────────────────────────────────────────
# Standalone tests — run: python tools.py
# ─────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 55)
    print("  tools.py — standalone tests")
    print("=" * 55)

    print("\n[1] web_search")
    result = web_search("Claude AI capabilities 2025", max_results=2)
    print(result[:300] + "...\n")

    print("[2] calculate")
    print(calculate("(8500 * 12) * 1.15"))
    print(calculate("math.sqrt(256)"))
    print(calculate("round(3.14159, 2)"))
    print()

    print("[3] get_datetime")
    print(get_datetime())
    print()

    print("[4] write_file")
    print(write_file(
        "test_report.md",
        "# Test Report\n\nGenerated by tools.py standalone test.\n"
    ))

    print("[5] read_file")
    print(read_file("test_report.md"))

    print("[6] run_tool dispatcher")
    print(run_tool("calculate", {"expression": "100 * 1.3 ** 3"}))
    print(run_tool("get_datetime", {}))
    print(run_tool("unknown_tool", {}))

    print("\n" + "=" * 55)
    print("  All tests complete.")
    print("=" * 55)
