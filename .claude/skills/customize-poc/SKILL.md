---
name: customize-poc
description: Use when adapting the langsmith-guided-tour repo for a specific industry or domain-specific use case — triggered by "create a [domain] version of this repo", "customize this for [vertical] POC", "make a [use case] variant of the workshop", or working in a fresh clone of the langsmith-guided-tour template with intent to specialize the example agent and all eight notebook modules at once. Not for single-module edits.
---

# Customizing the LangSmith POC Modules

## Overview

This skill turns a clean clone of the langsmith-guided-tour repo into a variant for one industry or use case. It replaces the example agent, its demo data, its seed traffic, the golden dataset, the judge criteria and the notebook prompts, and keeps the module structure, code conventions and voice.

The baseline agent is a wealth-management client research assistant (`agents/client_research_agent.py`) with a **planted flaw** in its lookup tool. Modules 02–07 are built around that flaw: Engine finds it, the judges score it low, an offline experiment tests a fix, and the deployment reproduces it. A variant needs an equivalent flaw, or most modules have nothing to show. See *The planted flaw contract* below.

The skill drives the customization interactively: the user gives a short use case description, the skill asks eight follow-ups one at a time, then executes end to end with three approval checkpoints.

When invoked, **immediately use TodoWrite** to create one task per phase (Discovery / Agent code / Wiring and data / Notebooks / Validation). Track progress as each completes.

## When to use

Triggers:
- Working in a fresh clone of `langsmith-guided-tour` and asked to "make this for [domain]"
- Explicitly requested: produce a use case variant of the POC modules
- Any time the example agent, data, dataset or judge criteria must swap across all eight modules

Not for:
- Modifying only one module (edit the file directly)
- Adding new features to the existing modules
- Editing an already-specialized variant (branch from it instead)

## Conventions

Read all six before generating any content. Violating these triggers rework.

1. **Code comments terse.** Match `agents/client_research_agent.py` and `utils/*.py`. Module docstrings: 1–3 lines. Function docstrings: one line. Inline comments only for non-obvious behavior, one line each.

2. **Notebook voice matches the baseline.** Read cell 0 and two section cells of any baseline `modules/*.ipynb` first. The notebooks address the reader as "you", in short declarative sentences. Every code cell has a markdown cell before it saying what the code sends, to what, and what to expect. Each feature names what it saves the developer in one plain clause. Gated features keep their `> **Requires:** … **Without it:** …` notes. UI labels are bold. Never use the "§" symbol. No "Let's", no exclamation points.

3. **Keep the baseline's wording outside the domain.** The repo calls itself a tour in a few places (`X-Gateway-Tour` header, `tour-*` policy and kit names, "you've finished the tour"). Keep those. Swap only domain content: entities, tools, prompts, data, judge criteria.

4. **Names live in `utils/config.py`.** Agent ID, dataset, queue, managed agent and model configuration names are defined once there and imported by the notebooks. Change them there, not in notebooks. Where a notebook hardcodes one of these names (listed in the guide), make it match.

5. **Customization is one-time; the notebooks aren't.** The notebooks are run by people after customization. They must not ask the reader to choose `ACTIVE_AGENT`, names or paths; this skill sets them once.

6. **Links come from the SDK.** Notebooks print links from `.url` on SDK objects and the helpers in `utils/notebook.py`. Never derive a UI link by string-munging the API host.

## The planted flaw contract

Every variant needs a lookup tool that fails in a realistic, findable way. The baseline's version:

- Records are keyed by an opaque ID (`CL-0042`) in a module-level dict (`CLIENTS`).
- The lookup tool's argument is named for the ID (`client_id`), but its docstring example invites a natural-language slug (`'acme-pension'`). The model passes names or slugs, and the tool raises `ValueError`.
- A `ToolErrorMiddleware` (`client_lookup_errors`) returns the error to the model as the tool's result, so the run continues and the tool run keeps its error status. The general-purpose subagent gets the same middleware.
- Each record carries one sensitive field with a distinctive pattern (`ACCT-[0-9]{8}`), which Module 06 redacts.
- The fix is a second tool, `find_client_id(name)`, that maps a name to the ID (Module 05).

The variant keeps the same shape: opaque IDs, a misleading docstring example, the error middleware, one patterned sensitive field, and a name-to-ID fix tool. Keep the error-returning pattern exactly; only names and data change.

## Workflow

### Phase 1: Discovery

Ask for a 1–3 sentence use case description. Then ask the eight follow-ups **one at a time**, capturing each answer before moving on. The answers compound; asking them as a batch produces worse answers.

1. **Persona:** who uses the agent? (e.g., claims adjuster, compliance analyst)
2. **Tools:** `web_search` (Tavily) stays. Name the one domain lookup tool and its ID argument (e.g., `get_claim_record(claim_id)`).
3. **Demo data:** the record schema and 3 records with opaque IDs (e.g., `CLM-0042`), spanning small / medium / large or simple / complex. Include one sensitive field with a distinctive pattern for Module 06.
4. **The planted flaw:** confirm the misleading docstring example (a slug or name), the ID format, and the fix tool's name (`find_<entity>_id`). Explain why: Engine, the judges, the fix experiment and the deployment all show this one failure.
5. **Example queries:** 24 seed conversations for traffic, about half asking for a record **by name** (these trigger the flaw), a few by ID, the rest research and out-of-scope, a few multi-turn. Also 5–8 research questions for the golden dataset.
6. **Eval criteria:** 2–4 rules the correctness judge enforces (e.g., cites sources, no invented records, says plainly when a record can't be found).
7. **Deployable identity:** `AGENTS.md` content (identity sentence, workflow, rules) and the Managed Deep Agent's `instructions.md` (research half only, no lookup tool). Draft from the above; confirm with the user.
8. **Skills:** 1–2 on-demand skills (e.g., `claim-summary`), shared by the deployable and the managed agent.

After all eight, **summarize the spec back in plain prose**, including the planted flaw. This is **approval gate 1**.

### Phase 2: Agent code

- `agents/<use_case>_agent.py`: copy the public surface of `agents/client_research_agent.py` exactly: the data dict, `SYSTEM_PROMPT`, `web_search`, the lookup tool, the `<entity>_lookup_errors` middleware, and `build_<use_case>_agent(model=None, search_tool=None, extra_tools=())` with the research subagent and the explicit general-purpose subagent. Notebooks rely on those three parameters.
- `agents/deployable_agents/<use_case>/agent.py`: mirror `agents/deployable_agents/client_research/agent.py`. It **imports** the tools and middleware from the eval agent; don't copy them. Add `AGENTS.md` and `skills/<skill>/SKILL.md`.
- `agents/managed/<use_case>/`: mirror `agents/managed/client_research/` (`agent.py` with `define_deep_agent(name=…)`, `instructions.md`, `skills/`, `tools/search.py`, `pyproject.toml`, `.gitignore`). This folder is self-contained by design: `mda` builds copy only this folder, so it can't import from `agents/` or `utils/`. Copy the skills into it.
- Remove the baseline `client_research` agent files once nothing imports them (Phase 3 moves the imports). Keep `agents/deployable_agents/base_research_agent/` as a reference.

**Approval gate 2:** show the agent files to the user before wiring.

### Phase 3: Wiring and data

- `utils/config.py`: `AGENT_NAME` default (`<use-case>-agent`), `GOLDEN_DATASET`, `ENGINE_EXAMPLES_DATASET`, `REVIEW_QUEUE`, `MANAGED_AGENT_NAME` (must equal the managed `agent.py` name), `WORKSPACE_MODEL_CONFIG`, `ACTIVE_AGENT` and its `load_active_agent()` branch.
- `langgraph.json`: rename the `client_research` graph to the new key and path. Keep `base_research_agent`.
- `data/seed_conversations.json`: the 24 conversations from Phase 1 step 5. Keep the shape `{id, category, turns}`, with categories `<entity>_lookup`, `<entity>_lookup_by_id`, `research`, `out_of_scope`.
- `data/golden_seed.json`: research examples plus 3 rows with `"split": "<entity>-lookup"`. Each row's `reference_outputs.messages` is a full trajectory in which the lookup tool is called with the **real ID**, because the trajectory evaluator compares that argument. Generate the reference trajectories by running the agent with the ID in the question, then put the by-name question in `inputs`. **Approval gate 3** before writing this file: the golden rows define what "correct" means for Modules 04–05.
- Every import of `agents.client_research_agent` (notebooks, deployable, tests): point at the new module.
- `tests/`: rename and update tests that pin baseline names (`test_client_research_agent.py`, `test_golden_seed.py`, `test_trajectory_match.py`, `test_deployable_agents.py`, notebook structure tests). Keep their assertions; change the names they assert.
- `README.md`: the intro sentence, `Project Structure` paths, and any domain example.

### Phase 4: Notebook customization

Follow `notebook-customization-guide.md` in this skill directory, notebook by notebook.

### Phase 5: Validation

- `uv run --with pytest pytest -q` passes.
- Every code cell compiles: `compile(src, "cell", "exec", flags=ast.PyCF_ALLOW_TOP_LEVEL_AWAIT)`, skipping cells with any line starting with `!`.
- Import probe: `load_active_agent()` builds the new agent; the deployable imports; `langgraph.json` paths exist.
- **Flaw smoke test** (needs a model key; two calls): a by-name question returns the lookup error to the model and the run finishes; a by-ID question returns the record.
- Residual grep for baseline terms: `client_research`, `client-research`, `get_client_profile`, `client_id`, `CLIENTS`, `CL-0`, `ACCT-`, `find_client_id`, `client-lookup`, `wealth`, `relationship manager`, `Acme`, `Smith Family Office`, `TechCorp`, and the tickers in the baseline prompts (`AAPL`, `NVDA`, `MSFT`, `GOOGL`, `BRK.B`). Use `git grep -n -i`. Each hit is either swapped or deliberately kept.
- Voice spot-check: three random notebook cells read like the baseline.
- Tell the user which screenshots show baseline content and need retaking (guide, *Images*).

## Common mistakes

| Mistake | Fix |
|---|---|
| No planted flaw, or a flaw that never fires | Follow the contract; check that about half the seed conversations ask by name, and run the flaw smoke test |
| The lookup raises and crashes runs | Keep the error middleware on the main agent **and** the general-purpose subagent |
| Golden lookup rows reference a guessed name | Reference trajectories must call the lookup with the real ID |
| Copying tools into the deployable agent | The deployable imports from the eval agent, so they can't drift |
| Importing `utils` or `agents` from the managed agent | `mda` copies only its folder; keep it self-contained |
| `MANAGED_AGENT_NAME` differs from the managed `agent.py` name | They must match; Module 07 looks the deployment up by it |
| Names hardcoded in notebooks drift from `utils/config.py` | Change names in config; fix the hardcoded spots the guide lists |
| Rewriting the notebook voice or removing **Requires** notes | Swap domain content only; structure, gates and voice stay |
| Generating all phases without checkpointing | Three gates: spec, agent code, golden dataset |
| f-strings broken in notebook cell source | Write cell `source` as a **list of strings, one per line**, never one multi-line string |
| Syntax check fails on shell cells | Skip a cell when **any** line starts with `!` |

## Reference

- If a past customization exists on another branch or fork, inspect it as a worked example of the full end state.
- LangSmith docs the modules lean on: [Engine](https://docs.langchain.com/langsmith/engine), [Insights](https://docs.langchain.com/langsmith/insights), [online evaluators](https://docs.langchain.com/langsmith/online-evaluations-llm-as-judge), [Managed Deep Agents](https://docs.langchain.com/langsmith/managed-deep-agents-overview).
