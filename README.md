# AI_AGENT_FIX_CODE

A minimal coding agent built from scratch in Python on the Claude API — no agent framework. Given a project and a task, it explores the code, edits files, runs the tests and iterates until they pass.

I built it to understand what happens inside tools like Cursor's Agent mode or Claude Code: the agent loop, tool design, error handling and safety limits.

## How it works

The whole agent is a single loop:

1. Send the conversation history (task + all previous steps) to the model.
2. If the model asks to use a tool, run it and append the result to the history.
3. Repeat until the model answers without a tool call — that means it considers the task done.

The model never executes anything itself. It only returns a request like "call `edit_file` with these arguments"; the Python code decides whether and how to run it.

## Tools

| Tool | What it does |
| --- | --- |
| `list_files` | Lists all files in the project |
| `read_file` | Returns the content of a file |
| `edit_file` | Replaces an exact fragment (`old_str` → `new_str`); the fragment must occur exactly once |
| `run_command` | Runs a shell command in the project directory, after user approval |

Design choices:

- **Edits by exact string replacement**, not by rewriting whole files. It is cheaper and safer; if the fragment doesn't match, the model gets a clear error and corrects itself.
- **Tool errors are returned to the model as text** instead of crashing the program, so the agent can recover on its own.
- **Tool descriptions are part of the prompt** — they tell the model how to use each tool correctly.

## Safety limits

- Every shell command requires explicit approval (`t` to allow).
- File access is restricted to the project directory.
- Shell commands time out after 60 seconds; output is truncated to 5,000 characters.
- The run stops after 25 steps, so a stuck agent can't loop forever and burn tokens.

## Requirements

- Python 3.10+
- An Anthropic API key ([platform.claude.com](https://platform.claude.com))

## Setup

```bash
git clone <repo-url>
cd <repo-name>
pyenv shell 3.12.12
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env  
```

The API key (`GEMINI_API_KEY`) is read from `.env` via `python-dotenv`. The model defaults to `gemini-3.8-flash` and can be changed with `GEMINI_MODEL`, e.g. to `gemini-3.5-flash-lite` if you hit the free tier's daily request limit. The `.env` file is listed in `.gitignore`, so the key never ends up in the repository; only `.env.example` with a placeholder is committed.

## Usage

```bash
# default task: make the failing tests pass
python agent.py project

# custom task
python agent.py project "Add a median function with tests"
```

The repository includes `project/`, a small demo project with three intentional bugs and tests that catch them. Keep a clean copy of it to reset between runs.

Example run (abbreviated, yours will differ):

```
🔧 [1] list_files({})
🔧 [2] read_file({"path": "calculator.py"})
🔧 [3] read_file({"path": "tests/test_calculator.py"})
🔧 [4] edit_file({"path": "calculator.py", ...})
🔧 [5] edit_file({"path": "calculator.py", ...})
⚠️  Agent chce uruchomić: python -m pytest -q
   Zgoda? [t/N] t
   → 3 passed
✅ Agent skończył po 7 krokach.
```

## Project structure

```
.
├── agent.py                  # the agent: prompt, tools, loop
└── project/                  # demo project with bugs
    ├── calculator.py
    └── tests/
        └── test_calculator.py
```

## Limitations

- Sends the full history on every step, so cost grows with each step; there is no context compaction.
- No code search tool — fine for small projects, slow for large ones.
- Runs commands on the host machine (with approval), not in a sandbox.
- Single model, single agent, no planning or subagents.

## Possible next steps

- Auto-approve test commands, keep approval for everything else
- Add a `search` tool (grep) for larger codebases
- Track token usage and cost per run
- Load project instructions from an `AGENTS.md` file into the system prompt
- Run inside Docker to allow unattended runs
- Compare with the same agent built on the Claude Agent SDK

## What I learned

## License

MIT
