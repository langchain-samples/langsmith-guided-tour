---
name: metric-definition
description: Produce a governed definition of a metric. Use this skill when asked what a metric means, how it is calculated, or which dataset it comes from.
---

# Metric Definition Skill

## Format

For each metric, return:

- **Metric** — the metric name
- **Source dataset** — the catalog id it is defined in
- **Definition** — the definition verbatim from the catalog entry
- **Formula** — the calculation, if the definition expresses one
- **Caveats** — classification/access notes when the source dataset is Confidential, Restricted, or PII

## Rules

- Use the definition from `search_catalog` verbatim — do not paraphrase a governed metric
- If the metric is not found in any known dataset, say so; never invent a definition
- When the same metric name could come from more than one dataset, name the dataset you used

## Length

- One short block per metric; no preamble
