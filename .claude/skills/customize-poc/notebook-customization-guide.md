# Notebook Customization Guide

Companion to the `customize-poc` skill. Per-notebook customization detail for Phase 4 of the workflow.

## Notebook editing mechanics

Two patterns that cause silent failures if ignored:

**Write source as a list of lines, not one string.** Each cell's `source` field in the `.ipynb` JSON should be a list of strings, one per line (each ending with `\n` except the last). Writing it as a single multi-line string causes Python escape sequences like `\n` inside f-strings to become literal newlines in the cell source, producing syntax errors that only surface during `ast.parse` validation.

**Skip Jupyter magic lines in the syntax check.** Cells containing `!` shell commands are not valid Python. Skip any cell where `any(line.startswith('!') for line in src.splitlines())` — the check must look at all lines, not just the first, because many cells mix a comment line with a shell command.

## File map

The customization touches these files. Anything not listed stays untouched.

```
agents/<use_case>_agent.py                                     (NEW)
agents/deployable_agents/<use_case>/agent.py                   (NEW)
agents/deployable_agents/<use_case>/AGENTS.md                  (NEW)
agents/deployable_agents/<use_case>/deepagents.toml            (NEW)
agents/deployable_agents/<use_case>/skills/<skill>/SKILL.md    (NEW per skill from Phase 1 step 7)
utils/config.py                                                (MODIFIED — load_active_agent branch + defaults)
utils/evaluators.py                                            (MODIFIED — correctness_schema description field)
langgraph.json                                                 (MODIFIED — add new graph entry)
modules/00_setup.ipynb                                         (MODIFIED — Module Map labels)
modules/01_build_a_deep_agent_optional.ipynb                   (MODIFIED — substantial)
modules/02_tracing.ipynb                                       (MODIFIED — warm-up prompts)
modules/03_finding_failure_modes.ipynb                         (MODIFIED — Chat examples)
modules/04_datasets_and_experiments.ipynb                      (MODIFIED — substantial)
modules/05_online_evals.ipynb                                  (MODIFIED — judge + trigger prompts)
modules/06_annotation_queues.ipynb                             (MODIFIED — trigger prompts)
modules/07_deploy_optional.ipynb                               (MODIFIED — §7 test queries + deploy name)
```

`agents/deployable_agents/base_research_agent/` is not touched — it serves as the baseline reference for the deployable agent shape.

Modules 01 and 07 are tagged `_optional` in the filename. They can be skipped without breaking the rest of the sequence — 01 covers the introductory deep-agents walkthrough; 07 covers deployment, which requires LangSmith Deployments permissions to actually run.

## Per-notebook detail

### NB00 — Setup

Minimal change. The keys table, the model-provider note, the LangSmith API key creation steps, and the troubleshooting section stay generic across customizations. Only update:

- **Module Map table** (cell 2): row labels may briefly mention the use case if it adds clarity. The notebook references — `01_build_a_deep_agent_optional.ipynb` etc. — stay the same.

### NB01 — Build a Deep Agent (optional)

Substantial. The notebook walks through deep-agent capabilities section-by-section: 1.1 (bare agent / built-in filesystem) → 1.2 (custom tools) → 1.3 (subagents) → 1.4 (backends + memory) → 1.5 (middleware) → 1.6 (HITL) → 1.7 (AGENTS.md + skills) → 1.8 (complete agent). Inspect the baseline `modules/01_build_a_deep_agent_optional.ipynb` to confirm the section structure before editing. Swap:

- **§1.2 inline `web_search` definition:** keep the `@tool` pattern, swap the body if your domain uses a different search/lookup pattern.
- **§1.3 imported tool:** `from agents.<use_case>_agent import <lookup_tool>` (e.g., `get_client_profile` → `get_case_history` for the new domain).
- **§1.3 research subagent** definition: domain-flavor the system prompt (e.g., "research assistant for a wealth management firm" → "research assistant for an insurance carrier").
- **§1.3 main agent system_prompt:** match the deployable's identity language.
- **All demo prompts** (1.1 haiku can stay neutral; 1.2–1.8 should use new use case queries from Phase 1 step 4).
- **§1.4 memory demo prompts:** swap the baseline "remember that..." example with a domain-equivalent fact about a Phase 1 demo record.
- **§1.5 compliance rules:** the baseline rules (no SSNs, cite sources, flag non-public info) generalize across most domains. Adjust the third rule to fit the new domain (e.g., for healthcare: "flag any request involving PHI"; for legal: "cite jurisdiction").
- **§1.6 HITL demo:** prompt should produce a `write_file` call — use a "write a brief/summary on [example demo record]" form.
- **§1.7 AGENTS.md + skill content:** paste verbatim from `agents/deployable_agents/<use_case>/AGENTS.md` and the first skill's SKILL.md.
- **§1.8 complete agent:** swap tool list, subagent, identity.
- **Closing note (last cell):** update the path references to point at `agents/<use_case>_agent.py` and `agents/deployable_agents/<use_case>/agent.py`.

### NB02 — Tracing

Light. Swap:

- **Warm-up prompts (cell 4):** pick 5 from Phase 1 step 4 with varied shapes (single-tool, lookup-only, multi-step, edge case, simple research). The diversity matters — the filter DSL examples need different trace shapes to demonstrate against.
- **Filter examples:** stay generic. If the research subagent has a non-default name (rare), update the by-name filter example (`eq(name, "research-agent")` → new name).
- **Screenshot placeholders:** stay as-is. Capture screenshots separately against the customized agent's LangSmith UI.

### NB03 — Finding Failure Modes

Light. Almost everything generalizes. Swap:

- **Chat section example questions:** use domain-specific examples (e.g., "did any users get an unknown-<entity> response?", "what's the latency distribution for runs that delegated to the research subagent?"). Two or three example questions is enough.
- **Chat screenshot placeholder caption:** mention the new domain in the alt text if useful.

The concept intro on the shift in scale, the Insights configuration steps, the Engine availability callout, and the closing recap all describe LangSmith features that work identically across use cases. Leave them alone.

### NB04 — Datasets and Experiments

Largest swap. **Approval gate 3 fires here.**

- **Dataset name:** `<use_case>-evals`.
- **Five dataset examples** — each carries three reference fields used by the three evaluator types:
  - `reference_answer` — rubric (success criteria, not verbatim expected text) for the LLM judge in Part 2.
  - `expected_first_tool` — the first tool call expected for the single-step eval in Part 3.
  - `trajectory` — full expected tool-call sequence for the trajectory eval in Part 4.

  Pick five Phase 1 step 4 queries spanning:
  1. Lookup only (1 tool, expected_first_tool = the domain lookup tool, trajectory = [lookup])
  2. Research only (1 tool, expected_first_tool = "task", trajectory = ["task"])
  3. Lookup + research (2 tools, expected_first_tool = the lookup tool, trajectory = [lookup, "task"])
  4. Lookup + research + file write (3 tools) — optional fifth shape; useful for trajectory eval depth
  5. Edge case (unknown entity fall-through — agent reports not found)

- **Part 2 judge:** the `CorrectnessGrade` TypedDict + `correctness_judge_prompt` rewrite to enforce the eval criteria. The "rubric is success criteria, not literal text" framing in the prompt stays.

### NB05 — Online Evaluations

Significant. Swap:

- **`judge_prompt`** (Section 2, Step 1 code cell): rewrite to enforce the eval criteria from Phase 1 step 5. Each criterion gets one bullet in the prompt.
- **`display_name`** in `create_run_rule`: `<use_case>-online-correctness`.
- **Trigger prompts (Step 3):** use new use case queries. Include a mix of well-formed and edge-case prompts.

The output schema (`correctness_schema`) is defined in `utils/evaluators.py` and imported into the notebook — update it there during Phase 3. The `description` field should reflect the new domain; the `correctness` boolean + `comment` string shape is generic and usually stays as-is.

Section 1 (UI walkthrough) is generic — the step-by-step instructions and image placeholders apply identically across use cases. Leave it untouched.

Verify the judge's failure conditions actually fire on at least one of the trigger prompts — without that, NB06's annotation queue stays empty.

### NB06 — Annotation Queues

Light. Swap:

- **Queue name** in `get_or_create_annotation_queue`: `<use_case>-needs-review`.
- **Routing rule `display_name`:** `<use_case>-route-failures`.
- **Trigger prompts (Step 3):** updated to invite domain-specific failure modes — unknown identifiers, unanswerable specifics, future predictions if relevant to the domain.

The caveat about empty queues stays as-is — applies universally.

### NB07 — Deploy (optional)

Update in two places:

- **`langgraph deploy` command (`!cd ... && langgraph deploy --name ...`):** the deployment name uses `langsmith-poc-<use_case>`.
- **§7 test query checklist:** replace with 12 use-case-specific queries spanning four shapes (3 each):
  1. **Profile / lookup only** — one query per demo record from Phase 1 step 3.
  2. **Research only** — diverse domain topics.
  3. **Multi-step** — at least one with a file write to exercise HITL.
  4. **Edge cases** — unknown entity, unanswerable specifics, speculative refusal.
- **"What to watch for" guidance:** reference the new trajectory shapes and the agent's specific edge-case behaviors (e.g., "unknown-entity handling should report not found, not fabricate").

The capability table (§6) and operational follow-ups stay as-is.

## Image / screenshot placeholders

The baseline notebooks reference these image paths. Screenshots are captured from the LangSmith UI of the customized agent — the paths themselves don't change.

```
images/warm_up_traces.png
images/filter_traces.png
images/dataset.png
images/experiment_result.png
images/experiments_page.png
images/experiment_comparison.png
images/set_baseline_button.png
images/set_baseline.png
images/03-rule-editor.png
images/online_evals.png
images/annotation_queue.png
images/deployment_home.png
images/deployment_docs.png
images/Studio_testing.png
images/chat.png
images/insights_config.png
images/insights_report.png
images/engine_config.png
images/engine_issue.png
images/engine_triage.png
```

Some screenshots in NB01 (`deepAgentsDiag.png`, `deepAgentSubagents.png`, `deepAgentBackends.png`, `deepAgentMiddleware.png`, `deepAgentHITL.png`, `Offloading Inputs LangChain.png`, `Offloading Results LangChain.png`, `LangChain Summarization.png`) and NB04 (`final-response.png`, `single-step.png`, `trajectory.png`) are conceptual diagrams. They generalize across use cases — leave them as referenced.
