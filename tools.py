"""
tools.py - Agent tool definitions
Includes: web search (DuckDuckGo), file read/write, and code execution
"""

import subprocess
import tempfile
import os
import json
from pathlib import Path
from datetime import datetime

# ============================================================
# Tool Schema Definitions (Claude Tool Use format)
# ============================================================

TOOLS = [
    {
        "name": "web_search",
        "description": "Search the internet for up-to-date information. Use this when you need real-time data, news, documentation, or any information that requires internet access.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search keywords or question"
                },
                "max_results": {
                    "type": "integer",
                    "description": "Number of results to return, default is 5",
                    "default": 5
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "file_operation",
        "description": "Read or write local files. Supports reading file content, writing new files, appending content, listing directory contents, and deleting files.",
        "input_schema": {
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": ["read", "write", "append", "list", "delete"],
                    "description": "Operation type: read, write (overwrite), append, list (directory), delete"
                },
                "path": {
                    "type": "string",
                    "description": "File or directory path (relative to workspace)"
                },
                "content": {
                    "type": "string",
                    "description": "Content to write or append (required for write/append operations)"
                }
            },
            "required": ["operation", "path"]
        }
    },
    {
        "name": "code_execute",
        "description": "Execute Python code in a sandboxed environment. Suitable for data processing, math calculations, format conversion, and other computational tasks. Code runs in an isolated process with a timeout limit.",
        "input_schema": {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "Python code to execute"
                },
                "timeout": {
                    "type": "integer",
                    "description": "Timeout in seconds, default is 10",
                    "default": 10
                }
            },
            "required": ["code"]
        }
    }
]


# ============================================================
# Tool Execution Functions
# ============================================================

def execute_web_search(query: str, max_results: int = 5) -> dict:
    """
    Search the web using DuckDuckGo.
    Requires: pip install duckduckgo-search
    """
    try:
        from ddgs import DDGS

        results = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results):
                results.append({
                    "title": r.get("title", ""),
                    "url": r.get("href", ""),
                    "snippet": r.get("body", "")
                })

        if not results:
            return {"success": False, "error": "No results found"}

        return {
            "success": True,
            "query": query,
            "results_count": len(results),
            "results": results
        }

    except ImportError:
        return {
            "success": False,
            "error": "Please install duckduckgo-search: pip install duckduckgo-search"
        }
    except Exception as e:
        return {"success": False, "error": f"Search failed: {str(e)}"}


def execute_file_operation(operation: str, path: str, content: str = None) -> dict:
    """
    Perform file read/write operations.
    Security: Only allows operations within the ./workspace directory.
    """
    workspace = Path("./workspace").resolve()
    workspace.mkdir(exist_ok=True)

    # Resolve path and enforce workspace boundary
    target = (workspace / path).resolve()
    if not str(target).startswith(str(workspace)):
        return {"success": False, "error": "Security restriction: operations are only allowed within the workspace directory"}

    try:
        if operation == "read":
            if not target.exists():
                return {"success": False, "error": f"File not found: {path}"}
            file_content = target.read_text(encoding="utf-8")
            return {
                "success": True,
                "operation": "read",
                "path": path,
                "size": len(file_content),
                "content": file_content
            }

        elif operation == "write":
            if content is None:
                return {"success": False, "error": "write operation requires a content parameter"}
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
            return {
                "success": True,
                "operation": "write",
                "path": path,
                "bytes_written": len(content.encode("utf-8"))
            }

        elif operation == "append":
            if content is None:
                return {"success": False, "error": "append operation requires a content parameter"}
            target.parent.mkdir(parents=True, exist_ok=True)
            with open(target, "a", encoding="utf-8") as f:
                f.write(content)
            return {
                "success": True,
                "operation": "append",
                "path": path,
                "bytes_appended": len(content.encode("utf-8"))
            }

        elif operation == "list":
            list_target = target if target.is_dir() else workspace
            if not list_target.exists():
                return {"success": False, "error": f"Directory not found: {path}"}
            items = []
            for item in sorted(list_target.iterdir()):
                items.append({
                    "name": item.name,
                    "type": "dir" if item.is_dir() else "file",
                    "size": item.stat().st_size if item.is_file() else None,
                    "modified": datetime.fromtimestamp(item.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                })
            return {
                "success": True,
                "operation": "list",
                "path": str(list_target.relative_to(workspace)),
                "items": items,
                "count": len(items)
            }

        elif operation == "delete":
            if not target.exists():
                return {"success": False, "error": f"File not found: {path}"}
            if target.is_dir():
                return {"success": False, "error": "Directory deletion is not supported"}
            target.unlink()
            return {"success": True, "operation": "delete", "path": path}

        else:
            return {"success": False, "error": f"Unsupported operation: {operation}"}

    except Exception as e:
        return {"success": False, "error": f"File operation failed: {str(e)}"}


def execute_code(code: str, timeout: int = 10) -> dict:
    """
    Execute Python code in an isolated subprocess.
    Security: timeout limit + dangerous module blocklist.
    """
    # Basic security blocklist
    blocked_keywords = [
        "import subprocess", "__import__",
        "rmdir", "shutil.rmtree"
    ]

    code_lower = code.lower()
    for keyword in blocked_keywords:
        if keyword in code_lower:
            return {
                "success": False,
                "error": f"Security restriction: blocked operation '{keyword}'"
            }

    try:
        # Write code to a temp file and execute it
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py",
            delete=False, encoding="utf-8"
        ) as f:
            f.write(code)
            tmp_path = f.name

        result = subprocess.run(
            ["python", tmp_path],
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding="utf-8",
            env={**os.environ, "PYTHONIOENCODING": "utf-8"}
        )

        os.unlink(tmp_path)  # Clean up temp file

        return {
            "success": result.returncode == 0,
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr if result.stderr else None,
            "code_preview": code[:200] + "..." if len(code) > 200 else code
        }

    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "error": f"Code execution timed out (limit: {timeout}s)"
        }
    except Exception as e:
        return {"success": False, "error": f"Execution failed: {str(e)}"}


# ============================================================
# Tool Dispatcher (unified entry point)
# ============================================================

def dispatch_tool(tool_name: str, tool_input: dict) -> str:
    """Dispatch tool call to the corresponding function. Returns a JSON string."""
    if tool_name == "web_search":
        result = execute_web_search(
            query=tool_input["query"],
            max_results=tool_input.get("max_results", 5)
        )
    elif tool_name == "file_operation":
        result = execute_file_operation(
            operation=tool_input["operation"],
            path=tool_input["path"],
            content=tool_input.get("content")
        )
    elif tool_name == "code_execute":
        result = execute_code(
            code=tool_input["code"],
            timeout=tool_input.get("timeout", 10)
        )
    else:
        result = {"success": False, "error": f"Unknown tool: {tool_name}"}

    return json.dumps(result, ensure_ascii=False, indent=2)
