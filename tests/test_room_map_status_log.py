from pathlib import Path

from tools.omniverse import status_log

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
OMNIVERSE_TOOLS_DIRECTORY = REPOSITORY_ROOT / "tools" / "omniverse"


def _fixed_timestamp(content):
    return f"{content} | Local time: fixed"


def _diagnostic_fields():
    return {
        "owner": "CAMERA POSITION BRIDGE",
        "process": "MATERIAL INPUT DISCOVERY",
        "state": "MISSING",
        "details": {"input_path": "/World/Looks/RoomMap/Shader"},
    }


def test_diagnostic_block_separates_owner_state_details_and_timestamp():
    block = status_log.format_room_map_diagnostic_block(
        **_diagnostic_fields(),
        append_local_timestamp=_fixed_timestamp,
    )

    assert block.splitlines() == [
        "",
        "====================",
        "ROOM MAP CAMERA POSITION BRIDGE",
        "process=MATERIAL INPUT DISCOVERY | state=MISSING",
        "input_path=/World/Looks/RoomMap/Shader | Local time: fixed",
        "====================",
    ]


def test_console_helpers_route_the_same_block_to_the_requested_severity():
    warnings = []
    errors = []

    status_log.log_room_map_warning(
        **_diagnostic_fields(),
        log_warning=warnings.append,
        append_local_timestamp=_fixed_timestamp,
    )
    status_log.log_room_map_error(
        **_diagnostic_fields(),
        log_error=errors.append,
        append_local_timestamp=_fixed_timestamp,
    )

    assert warnings == errors
    assert warnings[0].endswith(
        "input_path=/World/Looks/RoomMap/Shader | Local time: fixed\n"
        "===================="
    )


def test_omniverse_runtime_does_not_bypass_the_console_helpers():
    direct_log_calls = ("carb.log_warn(", "carb.log_error(")

    for path in OMNIVERSE_TOOLS_DIRECTORY.glob("*.py"):
        if path.name == "status_log.py":
            continue

        source = path.read_text(encoding="utf-8")
        assert all(call not in source for call in direct_log_calls), path.name
