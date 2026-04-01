"""
tool_schemas.py — Claude Tool Use schema definitions

These descriptions tell Claude what each tool does and what
arguments it expects. Kept separate from tools.py so you can
tune Claude's behavior (by editing descriptions) without
touching the business logic.
"""

TOOL_SCHEMAS = [
    {
        "name": "web_search",
        "description": (
            "Search the internet using DuckDuckGo to retrieve current information, "
            "news, industry data, or any facts you are uncertain about. "
            "Returns a list of results with title, snippet, and URL. "
            "Run multiple searches with different keywords if one search is not enough."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type"       : "string",
                    "description": (
                        "Search query string. Use 3–10 keywords for best results. "
                        "Example: 'AI agent frameworks comparison 2025'"
                    ),
                },
                "max_results": {
                    "type"       : "integer",
                    "description": "Number of results to return. Default is 4, maximum is 8.",
                    "default"    : 4,
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "calculate",
        "description": (
            "Evaluate a mathematical expression with full precision. "
            "Use this tool for ALL numerical computations — never do mental math. "
            "Supports arithmetic, percentages, exponentiation, and math library functions "
            "such as math.sqrt(), math.log(), math.pow()."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "expression": {
                    "type"       : "string",
                    "description": (
                        "A valid Python math expression. "
                        "Examples: '100 * 1.15', 'math.sqrt(144)', '(500 + 300) / 4'"
                    ),
                },
            },
            "required": ["expression"],
        },
    },
    {
        "name": "read_file",
        "description": (
            "Read the contents of a file from the outputs/ directory. "
            "Use this when the user asks you to reference a previously saved file, "
            "or when you need to continue working on an existing report."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "filename": {
                    "type"       : "string",
                    "description": (
                        "File name only — do not include a directory path. "
                        "Example: 'report.md' or 'summary.txt'"
                    ),
                },
            },
            "required": ["filename"],
        },
    },
    {
        "name": "write_file",
        "description": (
            "Save content to a file in the outputs/ directory. "
            "Always use this as the final step when producing a report, summary, "
            "or any output the user will want to keep. "
            "Use Markdown formatting for readable reports. "
            "Recommended filename format: topic_YYYYMMDD.md"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "filename": {
                    "type"       : "string",
                    "description": (
                        "File name for the saved file. "
                        "Example: 'ai_trends_report_20250401.md'"
                    ),
                },
                "content": {
                    "type"       : "string",
                    "description": (
                        "Full text content to write. "
                        "Markdown is supported and recommended for reports."
                    ),
                },
            },
            "required": ["filename", "content"],
        },
    },
    {
        "name": "get_datetime",
        "description": (
            "Return the current date and time as a formatted string. "
            "Use this to add a timestamp to the header of generated reports."
        ),
        "input_schema": {
            "type"      : "object",
            "properties": {},
            "required"  : [],
        },
    },
]
