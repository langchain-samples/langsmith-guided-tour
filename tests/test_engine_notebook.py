"""Structure checks for the Engine notebook; no LangSmith calls."""

import json
import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
NOTEBOOK = REPO / "modules" / "03_engine.ipynb"
SECTIONS = [
    "## Setup",
    "## 1. Engine's picture of your agent",
    "## 2. The issue Engine found",
    "## 3. The evidence",
    "## 4. The proposed fix",
    "## 5. Failures become offline examples",
    "## 6. Engine learns from what you do",
    "## 7. Insights",
    "## 8. Red-team a deployment",
    "## Recap",
]
# Engine reveals the fix in section 4; earlier cells describe only the symptom.
FIX_WORDS = ("docstring", "find_client_id", "slug", "CL-0")
STALE = (
    "Suggested Evaluator",
    "every 6 hours",
    "Create Evaluator",
    "list_runs",
    "--status fixing",
    "Accept & Continue",
    '["title"]',
    '["priority"]',
    "ANTHROPIC_API_KEY",
)


def source(cell: dict) -> str:
    return "".join(cell["source"])


@pytest.fixture(scope="module")
def cells() -> list[dict]:
    return json.loads(NOTEBOOK.read_text())["cells"]


def test_outputs_cleared(cells):
    for cell in cells:
        if cell["cell_type"] == "code":
            assert cell["outputs"] == []
            assert cell["execution_count"] is None


def test_sections_in_order(cells):
    headings = []
    for cell in cells:
        if cell["cell_type"] == "markdown":
            headings += [line for line in source(cell).splitlines() if line.startswith("## ")]
    assert headings == SECTIONS


def test_fix_not_named_before_section_4(cells):
    for cell in cells:
        text = source(cell)
        if text.startswith("## 4."):
            return
        for word in FIX_WORDS:
            assert word not in text, word
    pytest.fail("no section 4 heading")


def test_no_stale_claims(cells):
    text = "\n".join(source(cell) for cell in cells)
    for phrase in STALE:
        assert phrase not in text, phrase


def test_every_gate_has_a_fallback(cells):
    for cell in cells:
        for line in source(cell).splitlines():
            if "**Requires:**" in line:
                assert "**Without it:**" in line, line


def test_images_exist_or_are_placeholders(cells):
    for cell in cells:
        for name in re.findall(r"\.\./images/([\w.-]+\.png)", source(cell)):
            assert name.startswith("TODO-03-") or (REPO / "images" / name).exists(), name


def test_recap_is_last(cells):
    last = source(cells[-1])
    assert last.startswith("## Recap")
    assert "**Next:**" in last and "**Docs:**" in last


def test_no_internal_ids(cells):
    text = "\n".join(source(cell) for cell in cells)
    assert not re.search(r"\b(?:[ABDFQT]-\d{3}|M\d\d)\b", text)
    assert "planning/" not in text


def test_old_notebook_removed():
    assert not (REPO / "modules" / "03_finding_failure_modes.ipynb").exists()
