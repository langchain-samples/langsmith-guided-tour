# Notebook Customization Guide

Companion to the `customize-poc` skill. Per-notebook customization detail for Phase 4 of the workflow.

## File map

The customization touches these files. Anything not listed stays untouched.

```
agents/<use_case>_agent.py                                     (NEW)
agents/deployable_agents/<use_case>/agent.py                   (NEW)
agents/deployable_agents/<use_case>/AGENTS.md                  (NEW)
agents/deployable_agents/<use_case>/deepagents.toml            (NEW)
agents/deployable_agents/<use_case>/skills/<skill>/SKILL.md    (NEW per skill from Phase 1 step 7)
utils/config.py                                                (MODIFIED — load_active_agent branch + defaults)
langgraph.json                                                 (MODIFIED — add new graph entry)
modules/00_setup.ipynb                                         (MODIFIED — Module Map labels)
modules/01_build_a_deep_agent.ipynb                            (MODIFIED — substantial)
modules/02_tracing.ipynb                                       (MODIFIED — warm-up prompts)
modules/03_online_evals.ipynb                                  (MODIFIED — judge + trigger prompts)
modules/04_annotation_queues.ipynb                             (MODIFIED — trigger prompts)
modules/05_datasets_and_experiments.ipynb                      (MODIFIED — substantial)
modules/06_deploy.ipynb                                        (MODIFIED — §8 + deploy name)
modules/07_finding_failure_modes.ipynb                         (MODIFIED — Polly examples)
```

`agents/deployable_agents/base_research_agent/` is not touched — it serves as the baseline reference for the deployable agent shape.

## Per-notebook detail

### NB00 — Setup

Minimal change. The keys table, the model-provider note, the LangSmith API key creation steps, and the troubleshooting section stay generic across customizations. Only update:

- **Module Map table** (cell 2): row labels may briefly mention the use case if it adds clarity. The notebook references — `01_build_a_deep_agent.ipynb` etc. — stay the same.

### NB01 — Build a Deep Agent

Substantial. The notebook walks through deep-agent capabilities section-by-section: 1.1 (bare agent / built-in filesystem) → 1.2 (custom tools) → 1.3 (subagents) → 1.4 (backends + memory) → 1.5 (middleware) → 1.6 (HITL) → 1.7 (AGENTS.md + skills) → 1.8 (complete agent). Inspect the baseline `modules/01_build_a_deep_agent.ipynb` to confirm the section structure before editing. Swap:

- **§1.2 import line:** `from agents.<use_case>_agent import <tool1>, <tool2>`
- **§1.2 tool printouts:** print names and descriptions of the new tools.
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
- **Screenshot placeholders:** stay as-is. DE captures their own screenshots.

### NB03 — Online Evaluations

Significant. Swap:

- **`judge_prompt`:** rewrite to enforce the eval criteria from Phase 1 step 5. Each criterion gets one bullet in the prompt.
- **`judge_schema`:** the `correctness` boolean + `comment` string shape is generic. The `description` field on the schema should reflect the new domain.
- **Trigger prompts (Step 3):** use new use case queries. Include a mix of well-formed and edge-case prompts.
- **`display_name`** in `create_run_rule`: `<use_case>-online-correctness`.

Verify the judge's failure conditions actually fire on at least one of the trigger prompts — without that, NB04's annotation queue stays empty.

### NB04 — Annotation Queues

Light. Swap:

- **Queue name** in `get_or_create_annotation_queue`: `<use_case>-needs-review`.
- **Routing rule `display_name`:** `<use_case>-route-failures`.
- **Trigger prompts (Step 3):** updated to invite domain-specific failure modes — unknown identifiers, unanswerable specifics, future predictions if relevant to the domain.

The caveat about empty queues stays as-is — applies universally.

### NB05 — Datasets and Experiments

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

### NB06 — Deploy

Update in two places:

- **`langgraph deploy` command (`!cd ... && langgraph deploy --name ...`):** the deployment name uses `langsmith-poc-<use_case>`.
- **§8 test query checklist:** replace with 12 use-case-specific queries spanning four shapes (3 each):
  1. **Profile / lookup only** — one query per demo record from Phase 1 step 3.
  2. **Research only** — diverse domain topics.
  3. **Multi-step** — at least one with a file write to exercise HITL.
  4. **Edge cases** — unknown entity, unanswerable specifics, speculative refusal.
- **"What to watch for" guidance:** reference the new trajectory shapes and the agent's specific edge-case behaviors (e.g., "unknown-entity handling should report not found, not fabricate").

The capability table (§7) and operational follow-ups stay as-is.

### NB07 — Finding Failure Modes

Light. Almost everything generalizes. Swap:

- **Polly section example questions:** use domain-specific examples (e.g., "did any users get an unknown-<entity> response?", "what's the latency distribution for runs that delegated to the research subagent?"). Two or three example questions is enough.
- **Polly screenshot placeholder caption:** mention the new domain in the alt text if useful.

The concept intro on the shift in scale, the Insights configuration steps, the Engine cloud-only callout, and the closing recap all describe LangSmith features that work identically across use cases. Leave them alone.

## Image / screenshot placeholders

The baseline notebooks reference these image paths. The DE captures screenshots from their LangSmith UI against the customized agent — the paths themselves don't change.

```
images/02-traces-list.png
images/02-filter-bar.png
images/03-rule-editor.png
images/03-scored-trace.png
images/04-queue-review.png
images/05-dataset-view.png
images/05-experiment-compare.png
images/06-studio-ui.png
images/07-polly-panel.png
images/07-insights-config.png
images/07-insights-report.png
images/07-engine-issue.png
```

Some screenshots in NB01 (`deepAgentsDiag.png`, `deepAgentSubagents.png`, `deepAgentBackends.png`, `deepAgentMiddleware.png`, `deepAgentHITL.png`, `Offloading Inputs LangChain.png`, `Offloading Results LangChain.png`, `LangChain Summarization.png`) and NB05 (`final-response.png`, `single-step.png`, `trajectory.png`) are conceptual diagrams. They generalize across use cases — leave them as referenced.
