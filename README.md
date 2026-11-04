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

Skills live in [`gemini/skills/`](gemini/skills/) as Markdown files with `name` / `description` frontmatter. Add a new `.md` file there to add a skill – no code changes needed.

## Setup

Requires Python 3.9+.

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
export GEMINI_API_KEY="..."   # from https://aistudio.google.com/apikey
```

## Run

```bash
.venv/bin/python gemini/01_hello.py
.venv/bin/python gemini/02_tool_call.py "Wie warm ist es in Berlin in Fahrenheit?"
.venv/bin/python gemini/03_skills.py "Schreib ein Haiku über Kaffee."
```

The default model is `gemini-3.5-flash-lite`; override it with `GEMINI_MODEL=<model>`.
