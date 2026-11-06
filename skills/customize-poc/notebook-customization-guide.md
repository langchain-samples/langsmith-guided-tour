# Notebook Customization Guide

Companion to the `customize-poc` skill: what to change in each notebook in Phase 4. Cell numbers are 0-based indices in the baseline; confirm them in the file before editing, since they shift as cells change.

## Notebook editing mechanics

Two patterns that cause silent failures if ignored:

**Write source as a list of lines, not one string.** Each cell's `source` in the `.ipynb` JSON is a list of strings, one per line (each ending with `\n` except the last). A single multi-line string turns `\n` escapes inside f-strings into literal newlines, which only fails at `ast.parse`.

**Skip shell lines in the syntax check.** Cells with `!` commands aren't Python. Skip a cell when `any(line.startswith('!') for line in src.splitlines())`; many cells mix a comment line with a shell command.

**Clear outputs** before committing, and keep every `> **Requires:** … **Without it:** …` note, image, and caption in place.

## File map

```
agents/<use_case>_agent.py                          (NEW: replaces agents/client_research_agent.py)
agents/deployable_agents/<use_case>/                (NEW: agent.py imports from the eval agent; AGENTS.md; skills/)
agents/managed/<use_case>/                          (NEW: self-contained Managed Deep Agent folder)
utils/config.py                                     (names, ACTIVE_AGENT, load_active_agent)
langgraph.json                                      (graph key and path)
data/seed_conversations.json                        (24 traffic conversations)
data/golden_seed.json                               (golden dataset seed, with the <entity>-lookup split)
tests/                                              (names the tests pin)
README.md                                           (intro, paths)
modules/00_setup.ipynb                              (light)
modules/01_build_a_deep_agent_optional.ipynb        (heavy: nearly every request string)
modules/02_tracing.ipynb                            (moderate: tool name in filters and queries)
modules/03_engine.ipynb                             (moderate: the issue's words and prose)
modules/04_online_evals.ipynb                       (moderate: judge prompts)
modules/05_offline_evals.ipynb                      (heavy: judge, trajectory match, fix tool, split)
modules/06_govern_optional.ipynb                    (moderate: redaction pattern and prompts)
modules/07_deploy_optional.ipynb                    (moderate: questions and paths)
```

Shared code already carries most of the variant: notebooks import names from `utils/config.py`, build the agent with `build_<use_case>_agent()`, and replay traffic with `utils/traffic.generate_traffic()` from `data/seed_conversations.json`. Generic helpers (`utils/langsmith_rules.py`, `utils/evaluators.py`, `utils/gateway.py`, `utils/deployment.py`, `utils/workspace.py`, `utils/notebook.py`) don't change.

## Per-notebook detail

The baseline names below are what to swap: `get_client_profile` → your lookup tool, `client_id` → its ID argument, `CL-0042` → a real ID from your data, `find_client_id` → your fix tool, `client-lookup` → `<entity>-lookup`.

### NB00: Setup

Light. Swap:
- [9] `client.agents.create(..., name="Client research agent")`: the display name.
- Prose naming `client-research-agent` ([7], [8], [10]) and `client-research-model` ([24]).
- [5] keys table: keep the Tavily row while the agent uses `web_search`.

Leave the key steps, CLI, Remote MCP and section 6 (`share_gateway_key`) alone.

### NB01: Build a deep agent (optional)

Heavy: almost every request string is domain content. Swap:
- [0], [1], [58]: agent name in prose and the recap.
- [5] `HAIKU_REQUEST`: a neutral or domain topic.
- [12] `web_search` docstring and `SYSTEM_PROMPT`; [11], [13] the summary request; [15], [17] the comparison request.
- [19]–[21]: the research subagent's description and prompt, and `NEWS_REQUEST`.
- [23]–[26] memory: `MEMORY_PROMPT` with its `/memories/<entities>/` path and a fact about one demo record, plus the file name the next cells read.
- [28], [29], [31] middleware: `COMPLIANCE_RULES` (keep the shape: one data rule, one sourcing rule, one confidentiality rule) and `EARNINGS_REQUEST`.
- [33], [35] approval: `NOTE_REQUEST` and the file path it writes.
- [40], [41], [43], [44]: `AGENTS_MD` (it tells the agent to call the lookup tool first, which triggers the flaw), the first skill's `SKILL.md`, and `BRIEF_REQUEST`.
- [45]–[47] interpreters: `HOLDINGS`, `CODE_REQUEST`, and the Python check. The check recomputes the same numbers, so keep the data shape (a list of items with a weight and a value) or rewrite both together.
- [49], [51] dynamic subagents: three parallel research topics in `WORKFLOW_REQUEST`.
- [53]–[57] complete agent: imports the lookup tool and `<entity>_lookup_errors`, and `MEETING_REQUEST` asks **by name** so the flaw fires; [57] expects error rows for those lookups.

Leave the harness table, built-in tools, middleware and context-management prose, the interrupt and resume mechanics, and the beta **Requires** notes.

### NB02: Tracing

Moderate. The traffic itself comes from `data/seed_conversations.json`. Swap:
- [2] the agent import; [3] the description of the 24 conversations (their categories).
- [6] Engine setup prose: agent name and agent file path.
- [10] `TURNS`: a two-turn thread on two domain topics.
- [14], [16], [21], [22], [24]: prose about the failed lookup and its argument.
- [15], [23], [25], [27], [28], [30]: the lookup tool's name in filters, CLI `--name`, and `MCP_PROMPT`.
- [17] the typed search `name:<lookup_tool> AND status:error`; [19], [20] the AI search query ("the agent could not find the <entity> the user asked about").

Flaw dependence: traffic must produce failed lookup runs ([15] reads one), several threads with 2+ failures and different IDs ([24]), and root runs that never error ([21]).

### NB03: Engine

Moderate. Swap:
- [4], [7], [9], [27], [28]: "client lookup" wording.
- [8] `LOOKUP_WORDS`: the terms that find the issue in its title or description (tool name, "<entity> lookup", "<entity> id").
- [15], [18]: the argument and the docstring-vs-ID explanation of the proposed fix.
- [22] the examples dataset description; [25] the dataset name in prose (match `ENGINE_EXAMPLES_DATASET`).
- [31] the Insights guided question ("What do <personas> ask this agent for…"); [34] the expected categories.

Flaw dependence: Engine files one issue about the lookup, its evidence shows a bad ID then a rejection, and the fix points at the docstring or a name-to-ID tool. Modules 05 and 07 reuse that issue.

Leave the click paths, triage, Insights and Red Teaming steps, and the **Requires** notes.

### NB04: Online evals and Automations

Moderate. Swap:
- [4] `CORRECTNESS_PROMPT` and [9] `RESOLVED_PROMPT`: the persona and the Phase 1 eval criteria, one sentence each. Keep the 0–1 scale and the schemas.
- [13], [18]: dataset and queue names in prose (match `utils/config.py`).
- [19] `FAILURE_TYPES`: keep `tool_error` and `judge_disagrees`; rename the others only if the domain has better words.
- [31] "low scores cluster on <entity>-lookup questions".

Leave the filters, thresholds, `upsert_*` calls and sections 7–8.

### NB05: Offline evals

Heavy. **This is where approval gate 3's golden rows get used.** Swap:
- [2] imports (the data dict, builder, lookup tool, `web_search`).
- [0], [5]–[7], [24], [26], [32], [36]: prose about the lookup, the split and the fix.
- [11], [34]: the `!langsmith` commands hardcode the dataset name and `--split`; match `GOLDEN_DATASET` and the new split.
- [13] `CORRECTNESS_PROMPT`: the persona and criteria, including "can't find the <entity>".
- [15] trajectory match (tee-up in [14]): `tool_args_match_overrides={"<lookup_tool>": ["<id_arg>"]}`.
- [21] `BASELINE_TOOLS`.
- [27] the fix tool `find_<entity>_id(name)`: searches the data dict by name; its docstring example uses a real ID; the demo call uses a partial name.
- [29] `build_<use_case>_agent(extra_tools=[...])`; [31] the experiment prefix and `variant` (`lookup-fix`).
- [38]–[42]: the split filter and the Playground step that edits the ID argument's description to a real ID.

Flaw dependence: baseline lookup rows score low with `tool_errors` above 0; the fix lowers `tool_errors` and raises the other scores on the split while other rows hold.

### NB06: Govern model and tool calls (optional)

Moderate. Swap:
- [5] the routing question; [18] `desk_question`; [25] `kit_question`: domain research questions.
- [7], [8], [12]: the sensitive field's description and regex (`ACCT-[0-9]{8}` → your pattern).
- [10], [11] `leaky_prompt`: asks for a record **by its real ID** on purpose, so the lookup succeeds and the sensitive field flows into the request.
- [15], [16]: the team value `advisory-desk` and the cap name `tour-<team>-cap`.
- [24] the kit's `web_search` docstring.

Leave policy shapes, headers, the Parallel kit, the tool policy and cleanup.

### NB07: Deploy (optional)

Moderate. Swap:
- [0], [5], [21], [34]: prose naming the lookup tool and the issue.
- [1] the project-based fallback name `--name client-research` and `find_deployment(name=...)`.
- [6] the import line it looks for in the deployable (`from agents.<use_case>_agent import`).
- [18] `LOOKUP_QUESTIONS`: three by-name questions, one per demo record, **no IDs**, so the flaw reproduces on the deployment.
- [20] the graph key (match `langgraph.json`); [22], [23] the managed folder path.
- [32] `RESEARCH_QUESTION` for the managed agent, capped at two searches.

Leave validate / deploy / lookup mechanics, `write_env_subset`, `mda deploy --context-strategy keep-hub`, and the Context Hub TL;DR edit.

## Images

Diagrams generalize; keep them: `deepAgentsDiag.png`, `deepAgentSubagents.png`, `deepAgentBackends.png`, `deepAgentMiddleware.png`, `deepAgentHITL.png`, `Offloading Inputs LangChain.png`, `Offloading Results LangChain.png`, `LangChain Summarization.png`, `trajectory.png`.

UI screenshots are named `NN-<slug>.png` (module number first) and show the baseline agent's data. Keep the paths and alt text structure, and tell the user which ones show baseline content so they can retake them against the variant. Screenshots captioned *Example from another agent* are generic stand-ins and can stay.
