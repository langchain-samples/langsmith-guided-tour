---
name: data-brief
description: Write a structured data brief for a dataset. Use this skill when asked to summarize, document, or onboard someone to an internal dataset.
---

# Data Brief Skill

## Format

Produce a brief with these sections, grounded in `search_catalog` output:

- **Dataset** — name and catalog id
- **What it is** — one or two sentences on domain and grain
- **Ownership** — owning team and refresh cadence (freshness)
- **Classification** — data classification and any access requirements; call these out explicitly for Confidential, Restricted, or PII datasets
- **Key metrics** — each metric with its definition, verbatim from the catalog
- **Caveats** — anything an analyst should know before using it (e.g., PII handling, refresh timing)

## Rules

- Ground every field in the catalog entry; do not infer or invent values
- If a requested detail is not in the catalog, state that it is not documented rather than guessing
- Lead with classification when the dataset is Restricted or contains PII

## Length

- Keep it to a single screen — a scannable brief, not a report
