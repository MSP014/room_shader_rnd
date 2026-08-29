"""Headless observer used by the KRM-93 MDL compile bisection."""

import asyncio
import os
import time

import omni.kit.app
import omni.usd


async def _monitor() -> None:
    app = omni.kit.app.get_app()
    context = omni.usd.get_context()
    started_at = time.monotonic()
    probe_name = os.environ.get("KRM93_COMPILE_PROBE_NAME", "unnamed")
    expected_stage = os.environ.get("KRM93_COMPILE_PROBE_STAGE", "").lower()
    fixture_timeout = float(
        os.environ.get("KRM93_COMPILE_PROBE_TIMEOUT_SECONDS", "35")
    )
    saw_fixture = False
    saw_pending = False
    fixture_started_at = None
    last_status = None
    last_progress_at = started_at
    last_heartbeat_at = started_at
    shader_node_started_at = None
    shader_node_message = "<not-observed>"
    idle_since = None

    print(
        "KRM93_COMPILE_PROBE"
        f" state=OBSERVER_STARTED probe={probe_name}"
        f" fixture_timeout_seconds={fixture_timeout:.1f}"
    )

    while time.monotonic() - started_at < 120.0:
        now = time.monotonic()
        stage = context.get_stage()
        if stage is not None:
            identifier = stage.GetRootLayer().identifier.lower()
            matches_expected = (
                not expected_stage or expected_stage in identifier
            )
            if matches_expected and not saw_fixture:
                saw_fixture = True
                fixture_started_at = now
                last_progress_at = now
                last_heartbeat_at = now
                print(
                    "KRM93_COMPILE_PROBE"
                    f" state=STAGE_DETECTED probe={probe_name}"
                    f" process_elapsed_ms={(now - started_at) * 1000.0:.3f}"
                    f" stage_identifier={identifier}"
                )

        message, files_loaded, total_files = context.get_stage_loading_status()
        message = str(message).strip()
        files_loaded = int(files_loaded)
        total_files = int(total_files)
        pending = bool(str(message).strip()) or (
            total_files > 0 and files_loaded < total_files
        )
        status = (message, files_loaded, total_files, pending)
        if saw_fixture and status != last_status:
            previous_status = last_status
            last_status = status
            last_progress_at = now
            if pending and message.endswith("/Shader"):
                if shader_node_started_at is None:
                    shader_node_started_at = now
                    shader_node_message = message
                    print(
                        "KRM93_COMPILE_PROBE"
                        f" state=SHADER_NODE_BEGIN probe={probe_name}"
                        f" fixture_elapsed_ms={(now - fixture_started_at) * 1000.0:.3f}"
                        f" shader_node={message}"
                    )
            elif (
                not pending
                and shader_node_started_at is not None
                and previous_status is not None
                and previous_status[3]
            ):
                print(
                    "KRM93_COMPILE_PROBE"
                    f" state=SHADER_NODE_COMPLETE probe={probe_name}"
                    f" shader_node_ms={(now - shader_node_started_at) * 1000.0:.3f}"
                    f" shader_node={shader_node_message}"
                )
            shader_node_elapsed = (
                f"{(now - shader_node_started_at) * 1000.0:.3f}"
                if shader_node_started_at is not None
                else "not_observed"
            )
            print(
                "KRM93_COMPILE_PROBE"
                f" state=LOADING_STATUS_CHANGED probe={probe_name}"
                f" fixture_elapsed_ms={(now - fixture_started_at) * 1000.0:.3f}"
                f" pending={pending} files_loaded={files_loaded}"
                f" total_files={total_files}"
                f" loading_message={message or '<empty>'}"
                f" shader_node_ms={shader_node_elapsed}"
            )
        if saw_fixture and now - last_heartbeat_at >= 15.0:
            last_heartbeat_at = now
            print(
                "KRM93_COMPILE_PROBE"
                f" state=LOADING_HEARTBEAT probe={probe_name}"
                f" fixture_elapsed_ms={(now - fixture_started_at) * 1000.0:.3f}"
                f" stalled_ms={(now - last_progress_at) * 1000.0:.3f}"
                f" pending={pending} files_loaded={files_loaded}"
                f" total_files={total_files}"
                f" loading_message={message or '<empty>'}"
            )
        if saw_fixture and pending:
            saw_pending = True
            idle_since = None
        elif saw_fixture and saw_pending:
            idle_since = idle_since or time.monotonic()
            if time.monotonic() - idle_since >= 3.0:
                print(
                    "KRM93_COMPILE_PROBE"
                    f" state=COMPLETE probe={probe_name}"
                    f" fixture_elapsed_ms={(now - fixture_started_at) * 1000.0:.3f}"
                )
                app.post_quit()
                return

        if (
            saw_fixture
            and fixture_started_at is not None
            and now - fixture_started_at >= fixture_timeout
        ):
            shader_node_elapsed = (
                f"{(now - shader_node_started_at) * 1000.0:.3f}"
                if shader_node_started_at is not None
                else "not_observed"
            )
            print(
                "KRM93_COMPILE_PROBE"
                f" state=TIMEOUT probe={probe_name}"
                f" fixture_elapsed_ms={(now - fixture_started_at) * 1000.0:.3f}"
                f" stalled_ms={(now - last_progress_at) * 1000.0:.3f}"
                f" pending={pending} files_loaded={files_loaded}"
                f" total_files={total_files}"
                f" loading_message={message or '<empty>'}"
                f" shader_node_ms={shader_node_elapsed}"
            )
            app.post_quit()
            return

        await app.next_update_async()

    print(
        "KRM93_COMPILE_PROBE"
        f" state=OBSERVER_TIMEOUT probe={probe_name}"
        f" process_elapsed_ms={(time.monotonic() - started_at) * 1000.0:.3f}"
    )
    app.post_quit()


asyncio.ensure_future(_monitor())
