# llm-agent-basics

Hands-on learning project for LLM agent basics: function calling, tool use and on-demand skills – with Python examples for the Gemini API.

## Why Gemini?

The examples use the Gemini API because [Google AI Studio](https://aistudio.google.com/apikey) offers a **free API key** – ideal for learning and experimenting without costs.

The concepts (tool calls, function calling, skills) work the same way with other providers such as OpenAI or Anthropic (Claude). They just didn't offer a free API key, so they aren't used here.

## Examples

| # | File | What it shows |
|---|------|---------------|
| 1 | [`gemini/01_hello.py`](gemini/01_hello.py) | Minimal API call with retry on temporary errors (429/5xx) |
| 2 | [`gemini/02_tool_call.py`](gemini/02_tool_call.py) | Custom (dummy) tool `get_weather` with a manual function-calling loop |
| 3 | [`gemini/03_skills.py`](gemini/03_skills.py) | "Skills" built on tool calls: the model sees only a catalog and loads full instructions via `load_skill` on demand |
| 4 | [`gemini/04_bash_tool.py`](gemini/04_bash_tool.py) | One generic `run_bash` tool instead of specific ones – with safeguards (confirmation, no secrets in env, timeout) |

Skills live in [`gemini/skills/`](gemini/skills/) as Markdown files with `name` / `description` frontmatter. Add a new `.md` file there to add a skill – no code changes needed.

## Specific tools vs. a generic bash tool

A single `bash` tool can do almost anything – that's how coding agents like Claude Code work. But:

- **Security:** the model can run destructive commands, read secrets (e.g. `env`) or be tricked via prompt injection. It needs a sandbox, approval and least privilege.
- **Reliability:** the model must know the right commands and parse raw text output – smaller models make more mistakes. Specific tools have a schema and return structured data.
- **Portability:** shell commands differ between macOS, Linux and Windows.
- **Flexibility:** in return, bash handles tasks nobody anticipated.

Rule of thumb: specific tools for end-user apps, a sandboxed bash tool with approval for developer agents.

## Setup

Requires Python 3.9+.

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
export GEMINI_API_KEY="..."   # from https://aistudio.google.com/apikey
```

### Alternative: setup with uv (if your system Python is older than 3.9)

`pip install` fails with `No matching distribution found for google-genai` on Python 3.8 or older. [uv](https://docs.astral.sh/uv/) downloads a recent Python without touching the system one (no sudo needed):

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
uv venv --python 3.12 .venv
uv pip install -r requirements.txt
```

Note: uv venvs contain no `pip` – use `uv pip install ...` instead. Running the examples works the same as below.

## Run

```bash
.venv/bin/python gemini/01_hello.py
.venv/bin/python gemini/02_tool_call.py "Wie warm ist es in Berlin in Fahrenheit?"
.venv/bin/python gemini/03_skills.py "Schreib ein Haiku über Kaffee."
.venv/bin/python gemini/04_bash_tool.py "Wie viele Python-Dateien gibt es im Ordner gemini?"
```

Example 4 asks for confirmation (`y`) before running each shell command.

The default model is `gemini-3.5-flash-lite`; override it with `GEMINI_MODEL=<model>`.
