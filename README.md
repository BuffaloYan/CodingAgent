# Agent by Claude

A local-first AI coding assistant with a Gradio 5 UI and LangGraph agent backend.

## Setup

```bash
# 1. Clone / enter the repo
cd agent-by-claude

# 2. Install dependencies
make install

# 3. Copy and fill in your API keys
cp .env.example .env
# Edit .env with your OpenAI / Anthropic / Google keys

# 4. Run
make run
# Opens http://127.0.0.1:7860
```

## Configuration

| File | Purpose |
|---|---|
| `.env` | API keys (never committed) |
| `config.yaml` | Model selection, active project |
| `workspace/` | Root folder for all your projects |

## Usage

- **Chat tab** — Talk to the AI agent; it can read/write files, run shell commands, search code
- **Workspace tab** — VS Code-style file explorer for the active project
- **Projects tab** — Create, switch, and manage projects inside `workspace/`
- **Download tab** — Download individual files or the whole project as a ZIP
- **Settings tab** — Choose your model and update API keys

## Development

```bash
make test    # run pytest
make lint    # ruff check
make fmt     # ruff format
```
