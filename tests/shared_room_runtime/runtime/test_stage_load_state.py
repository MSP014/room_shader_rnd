"""Protect pure asset-batch timing and terminal-state summaries."""

from tools.omniverse.runtime.stage_load_state import AssetBatchTracker


def test_asset_batch_tracker_records_longest_message_and_completion():
    now = [10.0]
    tracker = AssetBatchTracker(lambda: now[0])
    tracker.start("fixture.usda")
    tracker.record_status("Loading mesh", 10, now[0])
    now[0] = 12.0
    tracker.record_status("Loading material", 12, now[0])
    now[0] = 17.0

    details = tracker.finish(
        "ASSET_BATCH_LOADING_COMPLETE",
        terminal_reason="assets_loaded_event",
        message="",
        files_loaded=12,
        total_files=12,
        streaming_busy=False,
    )

    assert details is not None
    assert details["asset_batch_duration_ms"] == 7000.0
    assert details["longest_loading_message"] == "Loading material"
    assert details["longest_loading_message_ms"] == 5000.0
    assert details["batch_completion_observed"] is True
    assert tracker.active is False


def test_asset_batch_tracker_resets_identifiers_between_stage_runs():
    tracker = AssetBatchTracker(lambda: 1.0)
    tracker.start("first.usda")
    assert tracker.batch_id == 1

    tracker.reset_for_stage_open()
    tracker.start("second.usda")

    assert tracker.batch_id == 1
