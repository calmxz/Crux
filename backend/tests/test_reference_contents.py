from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
REFERENCE = REPO_ROOT / "docs" / "reference.md"


def _contents_and_sections() -> tuple[list[str], list[str]]:
    lines = REFERENCE.read_text(encoding="utf-8").splitlines()
    start = lines.index("## Contents")
    end = next(i for i in range(start + 1, len(lines)) if lines[i].startswith("## "))
    contents = [
        line.removeprefix("  - ") for line in lines[start + 1 : end] if line.startswith("  - ")
    ]
    sections = [line.removeprefix("### ") for line in lines[end:] if line.startswith("### ")]
    return contents, sections


def test_reference_contents_lists_every_section_in_order():
    # The Contents list is how readers find a section without scanning 900 lines.
    contents, sections = _contents_and_sections()
    assert contents == sections
