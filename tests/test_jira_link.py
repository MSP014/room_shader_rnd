"""Protect Jira worklog rounding and the supported description-to-ADF subset."""

import importlib.util
from pathlib import Path

import pytest


def _load_jira_link():
    path = Path("tools/jira_link.py")
    spec = importlib.util.spec_from_file_location("jira_link", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_worklog_payload_rounds_timestamp_window_and_keeps_context():
    jira_link = _load_jira_link()

    payload, duration_seconds, started = jira_link._build_worklog_payload(
        None,
        "MDL hello-world visual validation",
        "2026-08-18 05:08:00",
        "2026-08-18 05:24:00",
        "Asia/Yerevan",
    )

    assert duration_seconds == 900
    assert payload["timeSpentSeconds"] == 900
    assert payload["started"] == "2026-08-18T05:08:00.000+0400"
    assert payload["comment"]["content"][0]["content"][0]["text"] == (
        "MDL hello-world visual validation"
    )
    assert started.isoformat() == "2026-08-18T05:08:00+04:00"


def test_worklog_payload_rounds_duration_only_calls():
    jira_link = _load_jira_link()

    payload, duration_seconds, started = jira_link._build_worklog_payload(
        "16m",
        None,
        None,
        None,
        "Asia/Yerevan",
    )

    assert payload == {"timeSpentSeconds": 900}
    assert duration_seconds == 900
    assert started is None


def test_worklog_payload_accepts_the_rounded_timestamp_duration():
    jira_link = _load_jira_link()

    payload, duration_seconds, _ = jira_link._build_worklog_payload(
        "15m",
        None,
        "2026-08-18 05:08:00",
        "2026-08-18 05:24:00",
        "Asia/Yerevan",
    )

    assert payload["timeSpentSeconds"] == 900
    assert duration_seconds == 900


def test_worklog_payload_rejects_an_incompatible_duration():
    jira_link = _load_jira_link()

    with pytest.raises(ValueError, match="does not match"):
        jira_link._build_worklog_payload(
            "30m",
            None,
            "2026-08-18 05:08:00",
            "2026-08-18 05:24:00",
            "Asia/Yerevan",
        )


def test_description_adf_supports_headings_and_grouped_lists():
    jira_link = _load_jira_link()

    document = jira_link._adf_document_from_text(
        "# Objective\n"
        "Keep the room proportionate.\n\n"
        "## Controls\n"
        "- Uniform room scale\n"
        "- Aperture offset\n\n"
        "1. Validate in RTX Real-Time\n"
        "2. Validate in Path Tracing"
    )

    assert [node["type"] for node in document["content"]] == [
        "heading",
        "paragraph",
        "heading",
        "bulletList",
        "orderedList",
    ]
    assert document["content"][0]["attrs"] == {"level": 1}
    assert (
        document["content"][3]["content"][1]["content"][0]["content"][0][
            "text"
        ]
        == "Aperture offset"
    )
    assert (
        document["content"][4]["content"][0]["content"][0]["content"][0][
            "text"
        ]
        == "Validate in RTX Real-Time"
    )
