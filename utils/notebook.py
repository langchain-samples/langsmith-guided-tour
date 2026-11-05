"""Small print helpers for notebook output."""

MAX_FILE_LINES = 20


def trace_link(url: str, label: str = "View in LangSmith") -> None:
    """Print a labeled LangSmith link."""
    print(f"🔗 {label}: {url}")


def print_files(files: dict) -> None:
    """Print each file in a deep agent's `files` state, truncated to MAX_FILE_LINES lines."""
    for path, file_data in files.items():
        content = file_data["content"]
        lines = content if isinstance(content, list) else content.splitlines()
        print(path)
        print("\n".join(lines[:MAX_FILE_LINES]))
        if len(lines) > MAX_FILE_LINES:
            print("…")
        print()
