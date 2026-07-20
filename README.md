# LangSmith POC Modules

Self-directed Jupyter notebooks for engineers evaluating LangSmith during a POC. The modules cover the full agent engineering loop — build, trace, evaluate, deploy, and surface failure modes — against a single example agent.

## The Modules

| # | Module | Notebook | Duration |
|---|--------|----------|----------|
| **00** | **Setup** — env, keys, service verification | [`modules/00_setup.ipynb`](modules/00_setup.ipynb) | ~10 min |
| **01** | **Build a Deep Agent** — harness, tools, subagents, backends, middleware, HITL, AGENTS.md, skills | [`modules/01_build_a_deep_agent.ipynb`](modules/01_build_a_deep_agent.ipynb) | ~45 min |
| **02** | **Deploy + Govern** — apply workspace-level gateway policies and ship the agent via LangSmith Deployments | [`modules/02_deploy_and_govern.ipynb`](modules/02_deploy_and_govern.ipynb) | ~25 min |
| **03** | **Tracing** — generate traces and query them with `list_runs` + filter DSL | [`modules/03_tracing.ipynb`](modules/03_tracing.ipynb) | ~20 min |
| **04** | **Finding Failure Modes** — Chat, Insights Agent, and Engine | [`modules/04_finding_failure_modes.ipynb`](modules/04_finding_failure_modes.ipynb) | ~30 min |
| **05** | **Datasets and Experiments** — offline evaluation: final-response, single-step, trajectory | [`modules/05_datasets_and_experiments.ipynb`](modules/05_datasets_and_experiments.ipynb) | ~30 min |
| **06** | **Online Evaluations** — LLM-as-judge run rules that score new traces automatically | [`modules/06_online_evals.ipynb`](modules/06_online_evals.ipynb) | ~25 min |
| **07** | **Annotation Queues** — route low-scoring runs to human review | [`modules/07_annotation_queues.ipynb`](modules/07_annotation_queues.ipynb) | ~20 min |

Modules are designed to run in order; the full sequence is ~3.5 hours. Modules 03–07 form the core observability + evaluation loop.

- **Module 01** introduces the `deepagents` framework from scratch. Move quickly through it if you're already familiar with custom tools, subagents, and prompts.
- **Module 02** covers deployment via LangSmith and requires LangSmith Deployments permissions to run the deploy step.

## Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/getting-started/installation/) (recommended) or pip
- A LangSmith account ([sign up](https://smith.langchain.com))
- An API key from your model provider (OpenAI by default; Anthropic, Azure OpenAI, and AWS Bedrock are also supported — see *Switching Models* below)
- No Tavily API key required — the agent's web search runs on built-in canned content in this POC

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
| `OPENAI_API_KEY` | Modules 01–07 (default model provider) | <https://platform.openai.com/api-keys> |
| `LANGSMITH_API_KEY` | All modules (tracing + evaluations) | <https://smith.langchain.com> |

Module 02 (Deploy) additionally requires a LangSmith **service key** (`lsv2_sk_...`), not a personal access token, for deployment permissions.

## Switching Models

All modules import `model` from `utils/models.py`. Change one line there to swap providers — no notebook edits required.

```python
# utils/models.py

# OpenAI (default)
model = init_chat_model("openai:gpt-5.4-mini")

# Anthropic
# model = init_chat_model("anthropic:claude-sonnet-4-6")

# Azure OpenAI
# from langchain_openai import AzureChatOpenAI
# model = AzureChatOpenAI(azure_deployment="gpt-4.1-mini", streaming=True)

# AWS Bedrock
# from langchain_aws import ChatBedrockConverse
# model = ChatBedrockConverse(provider="anthropic", model_id="...")
```

Then set the matching API key environment variable in `.env`. See `.env.example` for the full set of supported provider variables.

## Deploy + Govern (Module 02)

Module 02 covers two things: wiring up the LangSmith LLM Gateway with a workspace-level PII/secrets policy, then deploying the governed agent to LangSmith Deployments using the `langgraph` CLI (installed by `uv sync`). The deploy config is `langgraph.json` at the repo root. Two graphs are registered: `client_research` (the primary deployable) and `base_research_agent` (a second example for inspection).

Your `LANGSMITH_API_KEY` must have deployment permissions — use a service key (`lsv2_sk_...`), not a personal access token. The gateway sections require `LANGSMITH_API_KEY_GATEWAY` (same value) and `WORKSPACE_ID` — see `.env.example`.

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
│   ├── search.py                              (web search wrapper — canned content, no API key required)
│   └── langsmith_rules.py                     (helpers for run rules + annotation queues)
├── agents/
│   ├── client_research_agent.py               (eval-safe agent imported by Modules 03–06 via utils.config)
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
│   ├── 01_build_a_deep_agent.ipynb
│   ├── 02_deploy_and_govern.ipynb
│   ├── 03_tracing.ipynb
│   ├── 04_finding_failure_modes.ipynb
│   ├── 05_datasets_and_experiments.ipynb
│   ├── 06_online_evals.ipynb
│   └── 07_annotation_queues.ipynb
└── skills/
    └── customize-poc/                         (Claude Code skill for adapting this repo to a new domain)
        ├── SKILL.md
        └── notebook-customization-guide.md
```

## Customizing for a New Domain

The repo ships specialized for a client research use case. To adapt it for a different industry or use case, the `customize-poc` skill at `skills/customize-poc/` walks a coding agent (Claude Code, for example) through seven structured discovery questions, then executes the end-to-end customization across the agent code, configuration, and all eight notebook modules.

### Workflow

1. **Clone the repo:**
   ```bash
   git clone https://github.com/langchain-samples/langsmith-guided-tour.git
   cd langsmith-guided-tour
   ```

2. **Create a branch for your variant.** Use the `examples/<vertical>` naming convention (e.g., `examples/insurance-claims`, `examples/legal-contracts`):
   ```bash
   git checkout -b examples/<your-vertical>
   ```

3. **Open the repo in a coding agent** and invoke the `customize-poc` skill. The skill auto-loads from `.claude/skills/customize-poc/` in any Claude Code session opened on this repo — start the session, then ask the agent to invoke `customize-poc`.

4. **Answer the discovery questions.** The skill asks seven structured follow-ups one at a time (persona, tools, demo data, example queries, eval criteria, deployable identity, skills). Three approval checkpoints — after the spec, after the agent code, before the dataset — catch misunderstandings before they propagate through the notebooks.

5. **Review the output.** The skill runs validation at the end (import probes, notebook syntax checks, residual-content greps). Spot-check a few notebook cells for tone and accuracy before committing.

6. **Commit and push:**
   ```bash
   git add -A
   git commit -m "Add <your-vertical> variant"
   git push origin examples/<your-vertical>
   ```

To contribute a new example back to the samples repo, open a PR against `main`. To keep the variant private (customer-specific work, internal POCs), fork this repo into your own org first and push the branch there.

## Common Issues

**`langgraph deploy` fails with 403 / permission denied**
Your API key is a personal access token. Generate a service key (`lsv2_sk_...`) in LangSmith **Settings → Organizations → Access and Security → API Keys**.

**Notebook can't find `utils` / `agents`**
Each module's setup cell prepends the repo root to `sys.path`. If you moved a notebook, update the `Path().resolve().parent` line to point at the repo root.

**Anthropic API: `tool_use ids were found without tool_result blocks immediately after`**
This appears if you submit a regular message to the deployed agent in Studio while a HITL interrupt is pending. The deployable variant in this repo ships without HITL — but if you re-add `interrupt_on={...}` to `agents/deployable_agents/client_research/agent.py`, send the resume command as a `Command(resume=...)` payload rather than plain text.

**Chat (Module 07) unavailable**
The in-workspace AI assistant requires a model provider API key configured as a workspace secret in LangSmith **Settings**. Configure one before invoking Chat with `Cmd+I` / `Ctrl+I`.
