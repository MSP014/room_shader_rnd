# SPDX-FileCopyrightText: 2026 Maksim Pospelkov
# SPDX-License-Identifier: MIT
"""Protect optional filtering of paused tutorial branches from Jira plans."""

from tools.sync_jira import filter_legacy_tutorial_items


def test_filter_legacy_tutorial_items_excludes_epics_and_children():
    issue_map = {
        "KRM-1": {"key": "KRM-1", "parent": None},
        "KRM-2": {"key": "KRM-2", "parent": "KRM-1"},
        "KRM-5": {"key": "KRM-5", "parent": None},
        "KRM-6": {"key": "KRM-6", "parent": "KRM-5"},
        "KRM-7": {"key": "KRM-7", "parent": None},
        "KRM-8": {"key": "KRM-8", "parent": "KRM-7"},
        "KRM-62": {"key": "KRM-62", "parent": None},
        "KRM-85": {"key": "KRM-85", "parent": "KRM-62"},
    }

    filtered = filter_legacy_tutorial_items(issue_map, False)

    assert set(filtered) == {"KRM-62", "KRM-85"}


def test_filter_legacy_tutorial_items_can_include_legacy_scope():
    issue_map = {"KRM-1": {"key": "KRM-1", "parent": None}}

    assert filter_legacy_tutorial_items(issue_map, True) == issue_map
