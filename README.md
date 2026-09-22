# Agentic Lab

A hands-on playground for building and experimenting with AI agents, from simple tool-using agents to more advanced agentic systems. Examples are standalone Python scripts with predefined tasks, intended for learning and iteration.

## Current examples

| Example | Capabilities |
| --- | --- |
| Tool-using agent | Web search, page reading, sample party-planning tools, and Langfuse tracing. |
| Retrieval agent | Retrieves ideas from a small in-memory knowledge base using BM25. |
| Visual agent | Analyzes remote images with a vision-capable model. |
| Browser agent | Navigates Chrome with Helium/Selenium and uses screenshots as feedback. |
| Multi-agent workflow | Delegates web research, estimates cargo travel times, and generates a map with a visual review step. |

## Project structure

```text
agents/
  browser_agent.py   # Browser automation
  multi_agents.py    # Manager and research agents
  rag_agent.py       # Retrieval-augmented generation
  visual_agents.py  # Image analysis
prompts/            # Prompt templates
tools/              # Shared custom tools
app.py              # Tool-using agent with tracing
main.py             # Incomplete introductory inference experiment
pyproject.toml      # Project metadata and dependencies
uv.lock             # Locked dependencies
```

## Tech stack

Python 3.13+, uv, Hugging Face smolagents and inference, OpenAI models, LangChain/BM25 retrieval, Helium/Selenium, pandas/GeoPandas/Plotly, and Langfuse with OpenInference instrumentation.

## Installation

With Python 3.13+ and [uv](https://docs.astral.sh/uv/) installed, run from the repository root:

```sh
uv sync
```

Install Google Chrome for browser automation and Plotly/Kaleido image export. Examples call external model providers; the relevant credentials and model access are required.

## Environment variables

Create a local `.env` file with the variables needed for your chosen example:

| Variable | Used by |
| --- | --- |
| `HF_TOKEN` | Tool-using, retrieval, and multi-agent examples (Hugging Face inference). |
| `OPENAI_API_KEY` | Visual, browser, and multi-agent examples. |
| `SERPER_API_KEY` | Multi-agent web search. |
| `LANGFUSE_PUBLIC_KEY` | Tracing in `app.py`. |
| `LANGFUSE_SECRET_KEY` | Tracing in `app.py`. |
| `LANGFUSE_BASE_URL` | Your Langfuse instance URL, if different from the SDK default. |

Keep credentials private. Local `.env` files are excluded by `.gitignore`. The commands below explicitly load `.env`, since not every script loads it itself.

## Run examples

Run these commands from the repository root:

```sh
# Tool use and tracing
uv run --env-file .env python app.py

# Retrieval
uv run --env-file .env python -m agents.rag_agent

# Image analysis
uv run --env-file .env python -m agents.visual_agents

# Browser automation (opens a visible Chrome window)
uv run --env-file .env python -m agents.browser_agent

# Multi-agent research and mapping (requests saved_map.png)
uv run --env-file .env python -m agents.multi_agents
```

Edit the task prompt in each script to try a different experiment. `main.py` is currently incomplete: it imports `get_weather`, which is not implemented in `tools/my_tools.py`.

## Roadmap

- Explore additional agent architectures, models, and tool integrations.
- Experiment with richer retrieval sources and persistent memory.
- Add repeatable evaluations and compare agent behavior across tasks.
