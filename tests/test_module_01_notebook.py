"""Structure and hygiene checks for the Module 1 notebook; no model or network calls."""

import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
NOTEBOOK = REPO_ROOT / "modules" / "01_build_a_deep_agent_optional.ipynb"
EXPECTED_HEADINGS = [
    "# Module 1: Build a deep agent",
    "## Setup",
    "## 1. The harness",
    "## 2. Your own tools and prompt",
    "## 3. Planning with to-dos",
    "## 4. Subagents",
    "## 5. Memory across threads",
    "## 6. Middleware",
    "## 7. Human approval",
    "## 8. AGENTS.md and skills",
    "## 9. Interpreters (beta)",
    "## 10. Dynamic subagents (beta)",
    "## 11. The complete agent",
    "## Recap",
]
BANNED_PATTERNS = [
    r"\bMemorySaver\b",
    r"read_project\(",
    r"list_runs\(",
    r"get_run_url\(",
    r"load_active_agent",
    r"\"\./AGENTS\.md\"",
    r"\"\./skills/\"",
    r"You are a helpful assistant",
    r"LANGSMITH_API_KEY_GATEWAY",
    r"CL-\d",
    r"find_client_id",
    "\u00a7",  # the section sign
    r"\b(?:[ABDFQT]-\d{3}|M\d\d)\b",
]


def load_cells():
    return json.loads(NOTEBOOK.read_text())["cells"]


def source(cell):
    return "".join(cell["source"])


def headings():
    found = []
    for cell in load_cells():
        first_line = source(cell).split("\n", 1)[0]
        if cell["cell_type"] == "markdown" and re.match(r"#{1,2} ", first_line):
            found.append(first_line)
    return found


def numbered_sections():
    sections = {}
    current = None
    for cell in load_cells():
        first_line = source(cell).split("\n", 1)[0]
        if cell["cell_type"] == "markdown" and first_line.startswith("## "):
            current = first_line if re.match(r"## \d+\. ", first_line) else None
            if current:
                sections[current] = []
        if current:
            sections[current].append(cell)
    return sections


def test_outputs_cleared():
    for cell in load_cells():
        if cell["cell_type"] == "code":
            assert cell["outputs"] == [] and cell["execution_count"] is None


def test_headings_in_order():
    assert headings() == EXPECTED_HEADINGS


def test_sections_have_two_to_eight_cells():
    # Define and run are separate cells, so sections run longer than 5
    for heading, cells in numbered_sections().items():
        assert 2 <= len(cells) <= 8, heading


def test_tracing_is_set_by_env_not_wrappers():
    for cell in load_cells():
        if cell["cell_type"] == "code":
            assert "tracing_context" not in source(cell)


def test_reads_reply_text():
    for cell in load_cells():
        if cell["cell_type"] == "code":
            assert not re.search(r"\]\.content\b", source(cell))


def test_no_stale_apis_or_spoilers():
    text = NOTEBOOK.read_text()
    for pattern in BANNED_PATTERNS:
        assert not re.search(pattern, text), pattern


def test_images_exist_or_are_placeholders():
    for cell in load_cells():
        for name in re.findall(r"\.\./images/([^\"')]+)", source(cell)):
            assert (REPO_ROOT / "images" / name).exists() or name.startswith("TODO-01-"), name


def test_beta_sections_are_gated():
    sections = numbered_sections()
    for heading in ("## 9. Interpreters (beta)", "## 10. Dynamic subagents (beta)"):
        intro = source(sections[heading][0])
        assert "> **Requires:**" in intro and "**Without it:**" in intro, heading


def test_complete_agent_returns_tool_errors():
    complete = "".join(source(cell) for cell in numbered_sections()["## 11. The complete agent"])
    assert "client_lookup_errors" in complete and "get_client_profile" in complete


def test_ends_with_recap():
    last = source(load_cells()[-1])
    assert last.startswith("## Recap") and "**Next:** Module 2" in last and "**Docs:**" in last
