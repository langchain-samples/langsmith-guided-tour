---
name: customize-poc
description: Use when adapting the langsmith-guided-tour repo for a specific industry or domain-specific use case — triggered by "create a [domain] version of this repo", "customize this for [vertical] POC", "make a [use case] variant of the workshop", or working in a fresh clone of the langsmith-guided-tour template with intent to specialize the example agent and all eight notebook modules at once. Not for single-module edits.
---

# Customizing the LangSmith POC Modules

## Overview

This skill operates on a clean clone of the langsmith-guided-tour template repo. It produces a specialized variant for a specific industry / use case by replacing the example agent, demo data, dataset, judge criteria, and notebook prompts — while preserving the module structure, code conventions, and tone calibrated for engineers evaluating LangSmith.

The skill drives the customization interactively: the user provides a brief use case description, the skill asks 7 structured follow-ups one at a time, then executes the customization end-to-end with three approval checkpoints.

When invoked, **immediately use TodoWrite** to create one task per phase (Discovery / Agent code / Wiring / Notebooks / Validation). Track progress as each completes.

## When to use

Triggers:
- Working in a fresh clone of `langsmith-guided-tour` and asked to "make this for [domain]"
- Explicitly requested: produce a deep-agent use case variant of the workshop content
- Any time the example agent, dataset, or judge criteria must swap across all eight modules

Not for:
- Modifying only one module (edit the file directly)
- Adding new features to the existing modules
- Editing an already-specialized variant (branch from it instead)

## Conventions

Read all five before generating any content. Violating these triggers rework.

1. **Code comments terse.** Match `agents/research_agent.py` and `agents/deployable_agents/base_research_agent/agent.py`. Module docstrings: a few lines, no bullet lists. Function docstrings: 1–3 lines. Inline comments only for non-obvious behavior. No multi-line block comments explaining what code does.

2. **Notebook tone formal.** Direct, declarative, technical. Audience reads SDK signatures — skip Python and LangChain basics, explain LangSmith-specific patterns (filter DSL, judge schemas, AQ workflow, run rules) tersely. No "Let's...", no exclamation points, no second-person conversational asides. For a concrete reference, inspect any cell 0 in the baseline `modules/*.ipynb` — the framing, voice, and density should match.

3. **Never use "tour" or "workshop" in user-facing content.** The repo name is for branding only. Content uses "modules" or "POC". Default `PROJECT_NAME` in `utils/config.py`: `langsmith-poc-<use_case>`, never `langsmith-tour-...` or `*-workshop-*`.

4. **Customization is one-time; the notebooks aren't.** The notebooks are read and run by humans after customization is complete; they should not include configuration steps this skill already handled. `ACTIVE_AGENT` selection, `PROJECT_NAME` defaults, and repo-structure tours are set once during customization and should never appear as steps the reader has to perform.

5. **LangSmith URLs distinct.** `api.smith.langchain.com` is the API endpoint; `smith.langchain.com` is the UI host. Hardcode the UI host for cloud deep links. Never derive UI links by string-munging the API endpoint. For self-hosted, expect them to differ similarly — confirm the UI host with the workspace operator before hardcoding.

## Workflow

### Phase 1 — Discovery

Ask the user for a 1–3 sentence use case description. Then ask the seven structured follow-ups **one at a time**, capturing the answer before moving on. Do not ask them as a batch — the answers compound and incremental thinking produces better answers.

1. **Persona** — who uses the agent? (e.g., wealth advisor, claims adjuster, compliance analyst)
2. **Tools** — what tools does the agent need? `web_search` (Tavily-backed) is almost always included; add one domain-specific lookup tool (e.g., `get_client_profile`, `get_case_history`, `lookup_policy`). Confirm tool names + parameter signatures.
3. **Demo data** — schema for the lookup tool + 3 example records spanning typical domain variety (small / medium / large, simple / complex, etc.).
4. **Example queries** — 8–12 sample queries the agent should handle, covering single-tool, multi-step, and edge-case shapes. These seed warm-up prompts (NB02), dataset examples (NB05), Studio test queries (NB06), and AQ trigger prompts (NB04).
5. **Eval criteria** — 2–4 criteria the LLM judge should enforce (e.g., cited sources, no fabricated entities, no future predictions, regulatory compliance).
6. **Deployable identity** — AGENTS.md content: identity sentence, workflow steps, rules. Draft from above; confirm with the user.
7. **Skills** — 1–2 on-demand skills the deployable should expose (e.g., `client-brief`, `claim-summary`, `policy-comparison`).

After capturing all seven, **summarize the spec back to the user in plain prose**. This is **approval gate 1** — catches misunderstandings cheaply before any code is written.

### Phase 2 — Agent code

Create two parallel agent implementations:

- `agents/<use_case>_agent.py` — eval-safe variant. Mirror the shape of `agents/research_agent.py`. Tools, research subagent, `MemorySaver` per call. Factory function `build_<use_case>_agent()`. No HITL, no FilesystemBackend.
- `agents/deployable_agents/<use_case>/agent.py` — deployable variant. Mirror the shape of `agents/deployable_agents/base_research_agent/agent.py`. Same tools + research subagent, plus AGENTS.md, skills, `CompositeBackend(FilesystemBackend + StoreBackend)`, `interrupt_on={"write_file": True, "edit_file": True}`. Module-level `agent` variable.
- `agents/deployable_agents/<use_case>/AGENTS.md` — identity from Phase 1 step 6.
- `agents/deployable_agents/<use_case>/deepagents.toml` — `name = "langsmith-poc-<use_case>"`, default model from `utils/models.py`.
- `agents/deployable_agents/<use_case>/skills/<skill-name>/SKILL.md` — one per skill from Phase 1 step 7.

The demo data dict is **duplicated** in both agent files — this matches the existing repo pattern of self-contained agent modules. Do not import the data between files.

**Approval gate 2** after writing the agent files: show both to the user before continuing to wiring + notebooks.

### Phase 3 — Wiring

- `utils/config.py`: add a branch to `load_active_agent()` for the new agent, change `ACTIVE_AGENT` default to the new agent's identifier, update the docstring header to list it, change `PROJECT_NAME` default to a domain-specific value (e.g., `langsmith-poc-<use_case>`).
- `langgraph.json`: add a graph entry for the new deployable. Keep `base_research_agent` registered.

### Phase 4 — Notebook customization

See `notebook-customization-guide.md` (in this skill directory) for per-notebook details and the file map. NB05's dataset examples encode the eval semantics for the rest of the loop — **approval gate 3** before generating that notebook.

### Phase 5 — Validation

- Import probe with dummy API keys: `load_active_agent()` builds the new agent; the deployable agent module imports cleanly; `langgraph.json` lists both graphs at the expected paths.
- Notebook syntax check across `modules/*.ipynb`: JSON parses, each code cell parses with `ast`.
- Residual content grep: any leftover identifiers, entity names, or demo data from the baseline template that should have been swapped to the new domain. Reference the baseline `agents/research_agent.py` and `agents/deployable_agents/base_research_agent/` to confirm what terms the baseline contains by default.
- Tone spot-check: three random notebook cells; formal, no "tour" / "workshop", no casual phrasings.

## Common mistakes

| Mistake | Fix |
|---|---|
| Verbose docstrings or multi-paragraph comments | Match `agents/research_agent.py` exactly — terse, no bullet lists in module docstrings |
| "Tour" or "workshop" in user-facing content | Repo name is branding only; content is "modules" or "POC" |
| Trying to evaluate the deployable variant in NB02–NB05 | NB02–NB05 use the eval-safe variant via `load_active_agent()`; the deployable's HITL breaks evals |
| Importing demo data between agent files (DRY temptation) | Keep demo data inline in each agent file — matches existing pattern, keeps modules self-contained |
| Notebooks asking the reader to choose `ACTIVE_AGENT` / `PROJECT_NAME` | These are configured once during customization; the resulting notebooks just import and run |
| Deriving UI deep links from the API endpoint host | Hardcode `https://smith.langchain.com` for cloud; confirm the self-hosted UI host with the workspace operator |
| Casual tone ("Let's...", "Now we'll...", exclamation points) | Match the formal, declarative voice in any baseline `modules/*.ipynb` cell 0 |
| Generating all phases without checkpointing | Three approval gates exist for a reason: spec, agent code, dataset. Do not skip. |

## Reference

- If a past customization exists on another branch or fork, inspect those files as a worked example — useful to see the full end-state of a typical customization before starting a new one.
- LangSmith feature docs referenced by NB07: [Polly](https://docs.langchain.com/langsmith/polly), [Insights Agent](https://docs.langchain.com/langsmith/insights), [Engine](https://docs.langchain.com/langsmith/engine).
