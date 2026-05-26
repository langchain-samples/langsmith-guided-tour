# LangSmith POC Modules

Self-directed Jupyter notebooks for engineers evaluating LangSmith during a POC. The modules cover the full agent engineering loop — build, trace, evaluate, deploy, and surface failure modes — against a single example agent.

## The Modules

| # | Module | Notebook | Duration |
|---|--------|----------|----------|
| **00** | Setup — env, keys, service verification | `modules/00_setup.ipynb` | ~10 min |
| **01** | Build a Deep Agent — harness, tools, subagents, backends, middleware, HITL, AGENTS.md, skills (optional) | `modules/01_build_a_deep_agent_optional.ipynb` | ~45 min |
| **02** | Tracing — generate traces and query them with `list_runs` + filter DSL | `modules/02_tracing.ipynb` | ~20 min |
| **03** | Datasets and Experiments — offline evaluation: final-response, single-step, trajectory | `modules/03_datasets_and_experiments.ipynb` | ~30 min |
| **04** | Online Evaluations — LLM-as-judge run rules that score new traces automatically | `modules/04_online_evals.ipynb` | ~25 min |
| **05** | Annotation Queues — route low-scoring runs to human review | `modules/05_annotation_queues.ipynb` | ~20 min |
| **06** | Deploy — ship the agent via LangSmith Deployments using the `langgraph` CLI (optional) | `modules/06_deploy_optional.ipynb` | ~25 min |
| **07** | Finding Failure Modes — Chat, Insights Agent, and Engine | `modules/07_finding_failure_modes.ipynb` | ~30 min |

Modules are designed to run in order. The full sequence is ~3.5 hours; the required-only path (skipping 01 and 06) is ~2 hours.

**Optional modules** are tagged `_optional` in the filename:
- **Module 01** introduces the `deepagents` framework from scratch. Skip if already familiar with custom tools, subagents, and prompts.
- **Module 06** covers deployment via LangSmith. Skip if you don't have deployment permissions or are using LangSmith strictly for observability and evaluations.

The remaining modules form the core observability + evaluation loop.

## Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/getting-started/installation/) (recommended) or pip
- A LangSmith account ([sign up](https://smith.langchain.com))
- An API key from your model provider (Anthropic by default; OpenAI, Azure OpenAI, and AWS Bedrock are also supported — see *Switching Models* below)
- A Tavily API key for the web search tool ([get one](https://tavily.com))

## Setup

Module 00 walks through this end-to-end with verification cells. The short version:

```bash
# 1. Install dependencies
uv sync

# 2. Create your .env file
cp .env.example .env
# Edit .env and fill in your keys

# 3. Start Jupyter
uv run jupyter notebook
```

Then open `modules/00_setup.ipynb` and run the cells in order to verify Python, dependencies, and credentials.

| Key | Required for | Where to get one |
|---|---|---|
| `ANTHROPIC_API_KEY` | Modules 01–07 (default model provider) | <https://console.anthropic.com> |
| `LANGSMITH_API_KEY` | All modules (tracing + evaluations) | <https://smith.langchain.com> |
| `TAVILY_API_KEY` | Modules 01–06 (web search tool used by the agent) | <https://tavily.com> |

Module 06 (Deploy) additionally requires a LangSmith **service key** (`lsv2_sk_...`), not a personal access token, for deployment permissions.

## Switching Models

All modules import `model` from `utils/models.py`. Change one line there to swap providers — no notebook edits required.

```python
# utils/models.py

# Anthropic (default)
model = init_chat_model("anthropic:claude-sonnet-4-6")

# OpenAI
# model = init_chat_model("openai:gpt-4.1-mini")

# Azure OpenAI
# from langchain_openai import AzureChatOpenAI
# model = AzureChatOpenAI(azure_deployment="gpt-4.1-mini", streaming=True)

# AWS Bedrock
# from langchain_aws import ChatBedrockConverse
# model = ChatBedrockConverse(provider="anthropic", model_id="...")
```

Then set the matching API key environment variable in `.env`. See `.env.example` for the full set of supported provider variables.

## Deploy (Module 06)

Module 06 deploys the agent at `agents/deployable_agents/client_research/` to LangSmith via the `langgraph` CLI (installed by `uv sync`). The deploy config is `langgraph.json` at the repo root. Two graphs are registered: `client_research` (the primary deployable) and `base_research_agent` (a second example for inspection).

Your `LANGSMITH_API_KEY` must have deployment permissions — use a service key (`lsv2_sk_...`), not a personal access token.

## Project Structure

```
langsmith-guided-tour/
├── README.md                                  (this file)
├── pyproject.toml                             (shared dependencies)
├── .env.example
├── langgraph.json                             (registers deployable graphs)
├── utils/
│   ├── config.py                              (active agent + project name — single source of truth)
│   ├── models.py                              (model initialization — swap providers here)
│   ├── search.py                              (resilient Tavily wrapper with canned fallbacks)
│   └── langsmith_rules.py                     (helpers for run rules + annotation queues)
├── agents/
│   ├── client_research_agent.py               (eval-safe agent imported by Modules 02–05 via utils.config)
│   └── deployable_agents/
│       ├── client_research/                   (deployable variant — AGENTS.md, skills, CompositeBackend)
│       │   ├── agent.py
│       │   ├── AGENTS.md
│       │   ├── deepagents.toml
│       │   └── skills/
│       │       ├── client-brief/SKILL.md
│       │       └── portfolio-update/SKILL.md
│       └── base_research_agent/               (second deployable, kept as reference)
│           ├── agent.py
│           ├── AGENTS.md
│           ├── deepagents.toml
│           └── skills/
├── images/                                    (diagrams + screenshots referenced by the notebooks)
├── modules/
│   ├── 00_setup.ipynb
│   ├── 01_build_a_deep_agent_optional.ipynb
│   ├── 02_tracing.ipynb
│   ├── 03_datasets_and_experiments.ipynb
│   ├── 04_online_evals.ipynb
│   ├── 05_annotation_queues.ipynb
│   ├── 06_deploy_optional.ipynb
│   └── 07_finding_failure_modes.ipynb
└── skills/
    └── customize-poc/                         (Claude Code skill for adapting this repo to a new domain)
        ├── SKILL.md
        └── notebook-customization-guide.md
```

## Customizing for a New Domain

The repo ships specialized for a client research use case. To adapt it for a different industry or use case, see the `customize-poc` skill at `skills/customize-poc/`. The skill walks a coding agent (Claude Code, for example) through seven structured discovery questions, then executes the end-to-end customization across the agent code, configuration, and all eight notebook modules.

## Common Issues

**`langgraph deploy` fails with 403 / permission denied**
Your API key is a personal access token. Generate a service key (`lsv2_sk_...`) in LangSmith **Settings → Organizations → Access and Security → API Keys**.

**Notebook can't find `utils` / `agents`**
Each module's setup cell prepends the repo root to `sys.path`. If you moved a notebook, update the `Path().resolve().parent` line to point at the repo root.

**Anthropic API: `tool_use ids were found without tool_result blocks immediately after`**
This appears if you submit a regular message to the deployed agent in Studio while a HITL interrupt is pending. The deployable variant in this repo ships without HITL — but if you re-add `interrupt_on={...}` to `agents/deployable_agents/client_research/agent.py`, send the resume command as a `Command(resume=...)` payload rather than plain text.

**Chat (Module 07) unavailable**
The in-workspace AI assistant requires a model provider API key configured as a workspace secret in LangSmith **Settings**. Configure one before invoking Chat with `Cmd+I` / `Ctrl+I`.
