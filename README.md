# Modular Workshops

Mix-and-match modules for ~1.5 hour customer workshops. Pick 2-3 modules, run them in order, you're done.

## The Modules

| # | Module | Duration | Notebook |
|---|--------|----------|----------|
| **0** | Fleet — slide intro + open the Fleet UI | ~10 min | `modules/00_fleet.ipynb` |
| **1** | LangGraph 201 — Research agent from scratch (state, nodes, edges, `create_agent` + middleware, supervisor, memory) | ~45 min | `modules/01_langgraph.ipynb` |
| **2** | Deep Agents — Harness, Tools, Subagents, Memory, Middleware, HITL, Skills | ~45 min | `modules/02_deep_agents.ipynb` |
| **3** | Deploy — `langgraph` CLI + LangSmith Deployments | ~15 min | `modules/03_deploy.ipynb` |
| **4** | LangSmith — Tracing, querying traces, offline + online evals, annotation queues | ~30 min | `modules/04_langsmith.ipynb` |

Each module is a standalone Jupyter notebook. Modules share the project's setup, `utils/`, and `agents/` so combining them is as simple as opening multiple notebooks in order.

## Slides
Companion slide deck for all modules: see `slides/README.md` for the links.
Includes an OSS primer and a LangSmith primer in case background is needed for the audience

## Workshop Recipes (~90 min)

A few starting points you can run as-is or remix.

### Recipe A — "Production-ready agents" (Module 2 + 3 + 4)
**90 min · matches the Capital One workshop.** Build a deep agent, ship it to LangSmith Deployments, then evaluate it.

1. Module 2 — Deep Agents (45 min)
2. Module 3 — Deploy (15 min)
3. Module 4 — LangSmith (30 min)

### Recipe B — "LangGraph foundations in Production" (Module 1 + 3 + 4)
**90 min.** For teams new to LangChain who want to understand multi-agent design and use it in production.

1. Module 1 — LangGraph 201 (45 min)
2. Module 3 - Deploy (15 min)
3. Module 4 — LangSmith (30 min)

### Recipe C — "LangGraph to Deep Agents" (Module 1 + 2)
**90 min.** Same research agent, two ways: built by hand in LangGraph, then in ~10 lines with `create_deep_agent()`. Strongest A/B teaching arc.

1. Module 1 — LangGraph 201 (45 min)
2. Module 2 — Deep Agents (45 min)

### Recipe D — "Ship it" (Module 2 + 3)
**60 min.** Quick "build + deploy" demo for teams who already know LangSmith.

1. Module 2 — Deep Agents (45 min)
2. Module 3 — Deploy (15 min)

## Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/getting-started/installation/) (recommended) or pip

## Setup

```bash
# 1. Install dependencies
uv sync

# 2. Configure environment variables
cp .env.example .env
# Edit .env and fill in your keys
```

| Key | Required for | Get one |
|-----|--------------|---------|
| `OPENAI_API_KEY` | Modules 1-4 (default model) | <https://platform.openai.com> |
| `LANGSMITH_API_KEY` | Modules 3 & 4 (recommended for all) | <https://smith.langchain.com> |
| `TAVILY_API_KEY` | Modules 2 & 3 (web search tool) | <https://tavily.com> |

```bash
# 3. Start Jupyter
uv run jupyter notebook
```

Open whichever module(s) your recipe calls for.

## Switching Models

All modules import `model` from `utils/models.py`. Change one line there to swap providers — no notebook edits required.

```python
# utils/models.py

# OpenAI (default)
model = init_chat_model("openai:gpt-4.1-mini")

# Anthropic
# model = init_chat_model("anthropic:claude-sonnet-4-5")

# Azure OpenAI
# from langchain_openai import AzureChatOpenAI
# model = AzureChatOpenAI(azure_deployment="gpt-4.1-mini", streaming=True)

# AWS Bedrock
# from langchain_aws import ChatBedrockConverse
# model = ChatBedrockConverse(provider="anthropic", model_id="...")
```

## Deploy (Module 3)

Module 3 deploys the agent at `agents/deep_agent/` to LangSmith via the `langgraph` CLI (installed by `uv sync`). The deploy config is `langgraph.json` at the workshop root.

Your `LANGSMITH_API_KEY` must have deployment permissions (use a `lsv2_sk_...` service key).

## Project Structure

```
modular-workshops/
├── README.md                       (this file — recipes + setup)
├── pyproject.toml                  (shared dependencies)
├── .env.example
├── langgraph.json                  (registers agents/deep_agent for langgraph dev)
├── utils/
├── agents/
│   ├── research_agent.py           (shared agent factory — Module 2 references, Module 4 imports for eval)
│   └── deep_agent/                 (deployable agent for Module 3)
│       ├── agent.py
│       ├── AGENTS.md
│       └── skills/
│           ├── linkedin-post/SKILL.md
│           └── twitter-post/SKILL.md
├── images/                         (diagrams used by the notebooks)
└── modules/
    ├── 01_langgraph.ipynb          (Module 1)
    ├── 02_deep_agents.ipynb        (Module 2)
    ├── 03_deploy.ipynb             (Module 3)
    └── 04_langsmith.ipynb          (Module 4)
```

## Common Issues

**`langgraph deploy` fails with 403 / permission denied**
Your API key is a personal token. Generate a service key (`lsv2_sk_...`) in LangSmith settings.

**Notebook can't find `utils` / `agents`**
Each module's setup cell prepends `project_root` (the workshop root) to `sys.path`. If you moved a notebook, update the `Path().resolve().parent` line to point at the workshop root.
