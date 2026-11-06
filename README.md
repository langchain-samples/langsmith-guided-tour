# LangSmith POC Modules

Self-directed Jupyter notebooks for engineers evaluating LangSmith during a POC. The modules cover the full agent engineering loop (build, trace, find failures, evaluate, govern and deploy) against a single example agent: a client research assistant for a wealth management firm, with a planted flaw in its client lookup tool for LangSmith to find.

## The Modules

| # | Module | Notebook | Duration |
|---|--------|----------|----------|
| **00** | **Setup**: keys, register the agent, first trace, CLI and Remote MCP, a model for LangSmith | [`modules/00_setup.ipynb`](modules/00_setup.ipynb) | ~15 min |
| **01** | **Build a deep agent** (optional): built-in tools, your own tools, planning, subagents, memory, middleware, approvals, skills, interpreters | [`modules/01_build_a_deep_agent_optional.ipynb`](modules/01_build_a_deep_agent_optional.ipynb) | ~45 min |
| **02** | **Tracing**: generate traffic, turn on Engine, read threads and trajectories, search, query traces from code, the CLI and MCP | [`modules/02_tracing.ipynb`](modules/02_tracing.ipynb) | ~25 min |
| **03** | **Engine**: the issue Engine files, its evidence, the proposed fix, offline examples, triage, Insights, Red Teaming | [`modules/03_engine.ipynb`](modules/03_engine.ipynb) | ~25 min |
| **04** | **Online evals and Automations**: LLM judges on every turn and thread, automations that fill a golden dataset and a review queue | [`modules/04_online_evals.ipynb`](modules/04_online_evals.ipynb) | ~25 min |
| **05** | **Offline evals**: the golden dataset, judge and trajectory evaluators, a baseline vs. a fix, comparison, the Playground | [`modules/05_offline_evals.ipynb`](modules/05_offline_evals.ipynb) | ~30 min |
| **06** | **Govern model and tool calls** (optional): LLM Gateway data and spend policies, the Tool Gateway, tool policies | [`modules/06_govern_optional.ipynb`](modules/06_govern_optional.ipynb) | ~30 min |
| **07** | **Deploy** (optional): deploy to a Staging environment, call the Agent Server, Managed Deep Agents, Engine fix validation | [`modules/07_deploy_optional.ipynb`](modules/07_deploy_optional.ipynb) | ~40 min |

Modules are designed to run in order. The full sequence is about 4 hours; the required path (00, 02, 03, 04, 05) is about 2 hours.

**Optional modules** are tagged `_optional` in the filename:
- **Module 01** introduces the `deepagents` framework from scratch. Skip it if you already know custom tools, subagents and middleware.
- **Module 06** needs LLM Gateway and Tool Gateway access, and some sections need an Organization Admin.
- **Module 07** needs a LangSmith Cloud workspace with Deployments enabled.

Beta features (Engine fix validation, Red Teaming, tool policies and others) are gated in the notebooks: each has a **Requires** note and a way to continue without it.

## Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- A LangSmith Cloud account ([sign up](https://smith.langchain.com)) with an agent-based workspace. Project-based and self-hosted workspaces work too: set `LANGSMITH_PROJECT` in `.env` (Module 00 explains).
- Model access: an LLM Gateway key by default, or a provider key (see *Switching Models*)
- A Tavily API key for the agent's web search ([get one](https://tavily.com))

## Setup

Module 00 walks through this end to end with verification cells. The short version:

```bash
# 1. Install dependencies
uv sync

# 2. Create your .env file
cp .env.example .env
# Edit .env and fill in your keys

# 3. Start Jupyter
uv run jupyter notebook
```

Then open `modules/00_setup.ipynb` and run the cells in order.

| Key | Required for | Where to get one |
|---|---|---|
| `LANGSMITH_API_KEY` | All modules (tracing, evals, Engine, deploy) | LangSmith **Settings** → **API Keys** (a Personal Access Token) |
| `LANGSMITH_GATEWAY_API_KEY` | Every model call (default model setup), and Module 06 sections 1–3 | A LangSmith key for a workspace whose LLM Gateway serves the model |
| `TAVILY_API_KEY` | The agent's web search | <https://tavily.com> |

`.env.example` lists the optional settings: workspace ID, agent ID and environment, or a project name for project-based workspaces.

Features that call a model inside LangSmith (Chat, online judges, the Playground, Insights) use your workspace's own LLM Gateway or model configurations, not your `.env`. Module 00 section 6 covers this.

## Switching Models

Every module and agent builds its model from `utils/models.py`. To switch, uncomment one `MODEL_SPEC` / `API_KEY_ENV` pair there; no notebook edits needed.

```python
# utils/models.py

# OpenAI gpt-5.6-luna via the LangSmith LLM Gateway (default)
MODEL_SPEC = {"model": "openai:gpt-5.6-luna", "base_url": "https://gateway.smith.langchain.com/openai", "use_responses_api": True}
API_KEY_ENV = "LANGSMITH_GATEWAY_API_KEY"

# Anthropic, direct
# MODEL_SPEC = {"model": "anthropic:claude-sonnet-4-6"}
# API_KEY_ENV = "ANTHROPIC_API_KEY"
```

The file also has Anthropic through the Gateway, OpenAI direct, Azure OpenAI and AWS Bedrock. Set the matching key in `.env`.

## Deploy (Module 07)

Module 07 deploys the agent with `langgraph deploy --agent-id --agent-environment staging --remote`, so the deployment's traces land in your agent's **Staging** environment. The config is `langgraph.json` at the repo root, with two graphs: `client_research` (the deployable agent, which reuses the notebook agent's tools) and `base_research_agent` (a second example). Deployment secrets come from `.env.deploy`, which the notebook writes with only the model and Tavily keys.

The same module hosts the research half of the agent as a **Managed Deep Agent** from `agents/managed/client_research/` with the `mda` CLI (`uv tool install --upgrade managed-deepagents`, 0.10.1 or later).

Your `LANGSMITH_API_KEY` must be able to create deployments; a **Tracing Only** key can't.

## Project Structure

```
langsmith-guided-tour/
├── README.md
├── pyproject.toml                    (shared dependencies)
├── .env.example
├── langgraph.json                    (registers the deployable graphs)
├── utils/
│   ├── config.py                     (agent, environments, dataset and queue names: single source of truth)
│   ├── models.py                     (model setup: switch providers here)
│   ├── search.py                     (resilient Tavily wrapper with canned fallbacks)
│   ├── traffic.py                    (seed traffic for Modules 02 and 04)
│   ├── notebook.py                   (links printed by the notebooks)
│   ├── workspace.py                  (workspace secrets, model configurations, agent tags)
│   ├── engine_reports.py             (Insights and Red Teaming lookups)
│   ├── langsmith_rules.py            (online judges and automations)
│   ├── evaluators.py                 (offline eval helpers)
│   ├── gateway.py                    (LLM Gateway and Tool Gateway helpers)
│   └── deployment.py                 (deployment secrets and lookups)
├── agents/
│   ├── client_research_agent.py      (the agent every module traces, with its planted flaw)
│   ├── deployable_agents/
│   │   ├── client_research/          (deployable variant: AGENTS.md, skills)
│   │   └── base_research_agent/      (second deployable, kept as reference)
│   └── managed/
│       └── client_research/          (Managed Deep Agent: agent.py, instructions.md, skills/, tools/)
├── data/                             (seed conversations and golden dataset seed)
├── images/                           (diagrams and screenshots used by the notebooks)
├── modules/
│   ├── 00_setup.ipynb
│   ├── 01_build_a_deep_agent_optional.ipynb
│   ├── 02_tracing.ipynb
│   ├── 03_engine.ipynb
│   ├── 04_online_evals.ipynb
│   ├── 05_offline_evals.ipynb
│   ├── 06_govern_optional.ipynb
│   └── 07_deploy_optional.ipynb
├── tests/                            (notebook structure and helper tests: uv run --with pytest pytest -q)
└── skills/
    └── customize-poc/                (Claude Code skill for adapting this repo to a new domain)
```

## Customizing for a New Domain

The repo ships specialized for a client research use case. To adapt it for a different industry or use case, the `customize-poc` skill at `skills/customize-poc/` walks a coding agent (Claude Code, for example) through structured discovery questions, then customizes the agent code, configuration and the notebook modules.

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

3. **Open the repo in a coding agent** and invoke the `customize-poc` skill. The skill auto-loads from `.claude/skills/customize-poc/` in any Claude Code session opened on this repo.

4. **Answer the discovery questions.** The skill asks its follow-ups one at a time (persona, tools, demo data, example queries, eval criteria, deployable identity, skills), with approval checkpoints before changes propagate through the notebooks.

5. **Review the output.** The skill runs validation at the end (import probes, notebook syntax checks, residual-content greps). Spot-check a few notebook cells for tone and accuracy before committing.

6. **Commit and push:**
   ```bash
   git add -A
   git commit -m "Add <your-vertical> variant"
   git push origin examples/<your-vertical>
   ```

To contribute a new example back to the samples repo, open a PR against `main`. To keep the variant private (customer-specific work, internal POCs), fork this repo into your own org first and push the branch there.

## Common Issues

**Online judges score nothing, or feedback shows `Required workspace secret "OPENAI_API_KEY" is missing`**
The judges in Module 04 run on your workspace's own LLM Gateway. Add a provider key as a workspace secret, or Gateway Credits, then rerun the traffic cell.

**Web search returns canned results**
Your Tavily key is out of searches or unreachable. `utils/search.py` falls back to canned results so the notebooks still run; add a key with searches left for live results.

**`langgraph deploy` fails with 403 / permission denied**
Your key can't create deployments. Use a Personal Access Token or service key with deployment permissions, not a **Tracing Only** key.

**Notebook can't find `utils` / `agents`**
Each module's setup cell prepends the repo root to `sys.path`. If you moved a notebook, update the `Path().resolve().parent` line to point at the repo root.

**Chat (Module 03) unavailable**
Chat calls a model inside LangSmith. Give your workspace a model (Module 00 section 6) before opening Chat with `Cmd+I` / `Ctrl+I`.
