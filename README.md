# CodeSentinel — AI Code Review & Performance Optimization Assistant

Streamlit tool combining Python's `ast` module (static analysis) with the
Claude API (optimization suggestions + auto-generated docstrings).

## Detected static-analysis issues
- Bare `except:` clauses
- Unused imports
- Mutable default arguments
- Missing docstrings
- Overly long functions (>50 lines)
- String-concatenation-in-loop performance smell

## Setup

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-your-key-here
streamlit run app.py
```

Then open the local URL Streamlit prints (default http://localhost:8501).

## Deploying on Replit
1. Create a new Python Repl and upload `app.py`, `analyzer.py`, `claude_assist.py`, `requirements.txt`.
2. Add `ANTHROPIC_API_KEY` in the Secrets tab.
3. Set the run command to:
   `streamlit run app.py --server.port 8080 --server.address 0.0.0.0`
4. Click Run.

## Project structure
```
CodeSentinel/
├── app.py            # Streamlit UI
├── analyzer.py        # AST-based static analysis
├── claude_assist.py   # Claude API: suggestions + docstring generation
└── requirements.txt
```

## Notes on the reported metrics
The 8.3 issues/100 lines, 37% execution-time reduction, and 95% docstring
coverage figures referenced in the project writeup were measured on a
specific 20-script / 500-line benchmark set — re-run your own benchmark
scripts against this codebase to reproduce/validate before citing these
numbers.
