from utils.notebook import print_files, trace_link


def test_trace_link_prints_label_and_url(capsys):
    trace_link("https://x", "Tracing")
    assert capsys.readouterr().out.strip() == "🔗 Tracing: https://x"


def test_print_files_joins_line_lists(capsys):
    print_files({"/notes.md": {"content": ["a", "b"]}})
    out = capsys.readouterr().out
    assert "/notes.md" in out
    assert "a\nb" in out


def test_print_files_accepts_string_content(capsys):
    print_files({"/plan.md": {"content": "first line\nsecond line"}})
    assert "second line" in capsys.readouterr().out


def test_print_files_truncates_after_20_lines(capsys):
    lines = [f"line {n}" for n in range(1, 26)]
    print_files({"/long.md": {"content": lines}})
    out = capsys.readouterr().out
    assert "line 20" in out
    assert "line 21" not in out
    assert out.rstrip().endswith("…")
