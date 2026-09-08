"""
claude_assist.py — Claude API integration for CodeSentinel.

Two capabilities:
  1. suggest_optimizations() — given source + AST-detected issues, ask Claude
     for concrete performance/quality fixes and (optionally) a rewritten version.
  2. generate_docstrings() — ask Claude to insert docstrings for functions
     that analyzer.py flagged as missing them, returning the full updated file.

Requires the ANTHROPIC_API_KEY environment variable.
"""

import os

import anthropic

MODEL = "claude-sonnet-4-6"

_client = None


def get_client():
    global _client
    if _client is None:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY environment variable is not set. "
                "Set it before running the app, e.g. export ANTHROPIC_API_KEY=sk-ant-..."
            )
        _client = anthropic.Anthropic(api_key=api_key)
    return _client


def _text_from(message) -> str:
    return "".join(
        block.text for block in message.content if getattr(block, "type", None) == "text"
    )


def suggest_optimizations(source: str, issues_summary: str) -> str:
    """Returns Claude's prose suggestions for fixing the flagged issues and
    improving performance. Not guaranteed to be valid code — advisory only."""
    client = get_client()
    system = (
        "You are a senior Python code reviewer focused on correctness, "
        "readability, and performance. Be specific and concise. Reference "
        "line numbers where possible. Use short code snippets only where "
        "they clarify a fix, not full-file rewrites."
    )
    user = (
        f"Static analysis flagged these issues:\n{issues_summary}\n\n"
        f"Source code:\n```python\n{source}\n```\n\n"
        "For each meaningful issue, give a short recommendation. Then list "
        "any additional performance optimizations you notice that the static "
        "analyzer missed."
    )
    message = client.messages.create(
        model=MODEL,
        max_tokens=1200,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return _text_from(message)


def generate_docstrings(source: str, function_names: list) -> str:
    """Asks Claude to return the full file with docstrings added to the
    given function names, preserving all other code exactly."""
    client = get_client()
    system = (
        "You add clear, concise Google-style docstrings to Python functions. "
        "You NEVER change any logic, formatting, or behavior of the code — "
        "you only insert docstrings. Return ONLY the complete updated Python "
        "file, no explanation, no markdown code fences."
    )
    user = (
        f"Add docstrings to these functions (and any others missing one): "
        f"{', '.join(function_names) if function_names else '(all functions missing docstrings)'}\n\n"
        f"```python\n{source}\n```"
    )
    message = client.messages.create(
        model=MODEL,
        max_tokens=4000,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    text = _text_from(message).strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text
        if text.endswith("```"):
            text = text.rsplit("```", 1)[0]
    return text.strip() + "\n"
