"""Structure checks for modules/02_tracing.ipynb; no LangSmith or model calls."""

import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK = REPO_ROOT / "modules" / "02_tracing.ipynb"
SECTIONS = [
    "## Setup",
    "## 1. Generate traffic",
    "## 2. Turn on Engine",
    "## 3. A multi-turn thread",
    "## 4. Read the trajectory",
    "## 5. Search with the search bar",
    "## 6. Search with AI",
    "## 7. Query traces from the SDK",
    "## 8. Query from the CLI and your coding agent",
    "## 9. Check on Engine",
    "## Recap",
]
GATED_SECTIONS = ("## 2. Turn on Engine", "## 6. Search with AI")
# Prose must not name the fix before Engine reveals it in Module 3.
FIX_SPOILERS = ("find_client_id", "docstring", "CL-")
REMOVED_APIS = ("list_runs", "fetch_runs", 'os.environ["LANGSMITH_PROJECT"]')


def load_cells():
    return json.loads(NOTEBOOK.read_text())["cells"]


def source(cell):
    return "".join(cell["source"])


def split_sections(cells):
    sections = {}
    current = None
    for cell in cells:
        text = source(cell)
        if cell["cell_type"] == "markdown" and text.startswith("## "):
            current = text.splitlines()[0]
            sections[current] = []
        if current:
            sections[current].append(cell)
    return sections


def test_title_cell():
    first = source(load_cells()[0])
    assert first.startswith("# Module 2: Tracing")
    assert "> ~25 min" in first


def test_sections_in_order():
    assert list(split_sections(load_cells())) == SECTIONS


def test_numbered_sections_have_two_to_five_cells():
    for heading, cells in split_sections(load_cells()).items():
        if heading[3].isdigit():
            assert 2 <= len(cells) <= 5, heading


def test_outputs_cleared():
    for cell in load_cells():
        if cell["cell_type"] == "code":
            assert cell["outputs"] == []
            assert cell["execution_count"] is None


def test_gated_sections_have_requires_blockquote():
    sections = split_sections(load_cells())
    for heading in GATED_SECTIONS:
        text = "\n".join(source(cell) for cell in sections[heading])
        assert "> **Requires:**" in text and "**Without it:**" in text, heading


def test_no_fix_spoilers_in_prose():
    for cell in load_cells():
        if cell["cell_type"] == "markdown":
            for word in FIX_SPOILERS:
                assert word not in source(cell), word


def test_no_removed_apis():
    text = "\n".join(source(cell) for cell in load_cells())
    for api in REMOVED_APIS:
        assert api not in text, api


def test_ai_search_cell_may_raise():
    # AI search is admin opt-in; a headless run must survive it being off.
    cells = [c for c in load_cells() if c["cell_type"] == "code" and "ai_search=" in source(c)]
    assert len(cells) == 1
    assert "raises-exception" in cells[0]["metadata"].get("tags", [])


def test_recap_has_next_and_docs():
    last = source(load_cells()[-1])
    assert last.startswith("## Recap")
    assert "**Next:** Module 3" in last
    assert "**Docs:**" in last


def test_images_exist_or_are_placeholders():
    for cell in load_cells():
        for name in re.findall(r"\.\./images/([\w.-]+\.png)", source(cell)):
            assert name.startswith("TODO-02-") or (REPO_ROOT / "images" / name).exists(), name
