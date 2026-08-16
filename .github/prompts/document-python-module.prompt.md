---
name: document-python-module
description: Add engineer-oriented module header and API docstrings without changing behavior
agent: agent
argument-hint: Path to the .py file or package to document
---

# Document a Python module

Documentation only — **no behavior changes**.

For each module:

1. Module docstring with **Business purpose**, how it fits the platform, and **Public API**
2. Public classes/functions: Args, Returns, short Examples when helpful
3. Private helpers: one-line docstring minimum
4. Inline comments only for non-obvious business rules

Match the style already used in `experiences/`, `web/`, and `nodes/builtin.py`.
Do not reformat unrelated code or invent APIs.
