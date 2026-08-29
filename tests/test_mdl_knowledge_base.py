from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
KNOWLEDGE_BASE = REPOSITORY_ROOT / "docs" / "knowledge_base" / "mdl"
INDEX_PATH = KNOWLEDGE_BASE / "README.md"

REQUIRED_HEADINGS = (
    "## Record",
    "## Purpose",
    "## Accepted contract",
    "## Evidence",
    "## Reproduction",
    "## Validation record",
    "## Boundary",
)


def _records():
    return tuple(sorted(KNOWLEDGE_BASE.glob("[0-9][0-9][0-9]_*.md")))


def test_mdl_records_use_the_indexed_heading_contract():
    records = _records()
    index = INDEX_PATH.read_text(encoding="utf-8")

    assert [path.name[:3] for path in records] == [
        f"{number:03d}" for number in range(1, 10)
    ]
    for path in records:
        source = path.read_text(encoding="utf-8")
        positions = [source.index(heading) for heading in REQUIRED_HEADINGS]

        assert positions == sorted(positions), path.name
        assert "| Evidence state |" in source
        assert f"({path.name})" in index


def test_mdl_records_are_clean_utf8_without_known_mojibake():
    for path in (*_records(), INDEX_PATH):
        source = path.read_text(encoding="utf-8")

        assert "вЂ" not in source, path.name
        assert "Г—" not in source, path.name
        assert "`r`n" not in source, path.name
        assert "\ufffd" not in source, path.name


def test_shared_room_record_keeps_renderer_evidence_pending():
    source = (KNOWLEDGE_BASE / "009_shared_multi_window_rooms.md").read_text(
        encoding="utf-8"
    )

    assert (
        "Automated contract complete; RTX renderer validation pending"
        in source
    )
    assert (
        "RTX renderer compilation and visual continuity have not yet been recorded"
        in source
    )
