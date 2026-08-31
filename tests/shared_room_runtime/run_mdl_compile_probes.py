"""Run progressively larger Room Map MDL graphs in isolated Kit processes.

This is a compiler bisection, not a renderer readiness test.  Each stage uses a
fresh MDL module filename so persistent shader-cache hits cannot hide which
expression makes the RTX MDL backend stall.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path
from queue import Empty, Queue

_SOURCE_ASSET_PATTERN = re.compile(
    r"uniform asset info:mdl:sourceAsset = @[^@]+@"
)
_SOURCE_SUB_IDENTIFIER_PATTERN = re.compile(
    r'uniform token info:mdl:sourceAsset:subIdentifier = "[^"]+"'
)
_TINT_EXPRESSION = "tint: composited_room_colour"
_EMISSION_EXPRESSION = "intensity: composited_room_colour * emission_strength"
_COMPILE_ERROR_PATTERNS = (
    "MDLC   comp error:",
    "Unable to find SdrShaderNode",
    "Loading MdlModule to DB",
    "USD_MDL (secondary thread)",
)

_PROBE_EXPRESSIONS = {
    "minimal": None,
    "primvar_values": (
        "color("
        "saturate(math::abs(derived_map_position.x)), "
        "saturate(math::abs(safe_room_scale.y)), "
        "saturate(float(active_room_size) / 4.0))"
    ),
    "shared_aperture": (
        "color("
        "saturate(math::abs(shared_ray_origin.x) / positive_extent(safe_room_width)), "
        "saturate(math::abs(shared_ray_origin.y) / positive_extent(safe_room_height)), "
        "saturate(math::abs(shared_ray_origin.z) / positive_extent(safe_room_depth)))"
    ),
    "camera_ray": (
        "color("
        "saturate(math::abs(ray_direction.x)), "
        "saturate(math::abs(ray_direction.y)), "
        "saturate(math::abs(ray_direction.z)))"
    ),
    "front_exit_cutout": (
        "front_exit_hits_primary_aperture "
        "? color(0.0, 1.0, 0.0) "
        ": color(1.0, 0.0, 0.0)"
    ),
    "shared_frame": (
        "color("
        "saturate(math::abs(shared_ray_origin.x) / positive_extent(safe_room_width)), "
        "saturate(math::abs(shared_ray_origin.y) / positive_extent(safe_room_height)), "
        "saturate(math::abs(ray_direction.z)))"
    ),
    "walls_geometry": (
        "color("
        "saturate(room_atlas_coordinate.x), "
        "saturate(room_atlas_coordinate.y), "
        "saturate(room_hit_distance / positive_extent(safe_room_depth)))"
    ),
    "walls_one_lookup": "room_colour",
    "slice_geometry": (
        "color("
        "saturate(slice_1_local_coordinate.x), "
        "saturate(slice_1_local_coordinate.y), "
        "slice_1_is_visible ? 1.0 : 0.0)"
    ),
    "one_slice_lookup": "composited_slice_colour",
    "five_lookups": ("(room_colour + composited_slice_colour) / 2.0"),
    "full_emission_only": "composited_room_colour",
    "full_diffuse_only": "composited_room_colour",
    "full_composition": "composited_room_colour",
}


def _repository_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _replace_output(
    source: str,
    tint_expression: str,
    emission_expression: str | None = None,
) -> str:
    emission_expression = emission_expression or tint_expression
    if _TINT_EXPRESSION not in source:
        raise RuntimeError("Room Map tint expression was not found")
    if _EMISSION_EXPRESSION not in source:
        raise RuntimeError("Room Map emission expression was not found")
    source = source.replace(
        _TINT_EXPRESSION,
        f"tint: {tint_expression}",
        1,
    )
    return source.replace(
        _EMISSION_EXPRESSION,
        f"intensity: ({emission_expression}) * emission_strength",
        1,
    )


def _write_probe_assets(
    temporary_directory: Path,
    probe_name: str,
    repository_root: Path,
) -> tuple[Path, Path]:
    mdl_source = (repository_root / "src" / "mdl" / "room_map.mdl").read_text(
        encoding="utf-8"
    )
    expression = _PROBE_EXPRESSIONS[probe_name]
    if expression is None:
        mdl_source = (
            repository_root
            / "tests"
            / "shared_room_runtime"
            / "mdl_compile_minimal.mdl"
        ).read_text(encoding="utf-8")
    else:
        tint_expression = expression
        emission_expression = expression
        if probe_name == "full_emission_only":
            tint_expression = "color(0.0)"
        elif probe_name == "full_diffuse_only":
            emission_expression = "color(0.0)"
        mdl_source = _replace_output(
            mdl_source,
            tint_expression,
            emission_expression,
        )

    mdl_path = temporary_directory / f"room_map_compile_{probe_name}.mdl"
    mdl_path.write_text(mdl_source, encoding="utf-8")

    fixture_path = (
        repository_root
        / "tests"
        / "shared_room_runtime"
        / "test_room_map_shared_rooms_omniverse.usda"
    )
    stage_source = fixture_path.read_text(encoding="utf-8")
    source_asset = mdl_path.resolve().as_posix()
    stage_source, replacement_count = _SOURCE_ASSET_PATTERN.subn(
        f"uniform asset info:mdl:sourceAsset = @{source_asset}@",
        stage_source,
        count=1,
    )
    if replacement_count != 1:
        raise RuntimeError(
            "Fixture MDL sourceAsset was not replaced exactly once"
        )
    stage_source, replacement_count = _SOURCE_SUB_IDENTIFIER_PATTERN.subn(
        'uniform token info:mdl:sourceAsset:subIdentifier = "room_map"',
        stage_source,
        count=1,
    )
    if replacement_count != 1:
        raise RuntimeError(
            "Fixture MDL sourceAsset subIdentifier was not replaced exactly once"
        )

    # Keep the generated stage beside the source fixture so all existing
    # relative texture and HDRI asset paths remain valid.
    stage_path = fixture_path.with_name(f"_compile_probe_{probe_name}.usda")
    stage_path.write_text(stage_source, encoding="utf-8")
    return mdl_path, stage_path


def _run_probe(
    probe_name: str,
    *,
    repository_root: Path,
    temporary_directory: Path,
    kit_root: Path,
    fixture_timeout_seconds: float,
    process_timeout_seconds: float,
) -> tuple[str, float, Path]:
    _mdl_path, stage_path = _write_probe_assets(
        temporary_directory,
        probe_name,
        repository_root,
    )
    kit_executable = (
        kit_root / "_build" / "windows-x86_64" / "release" / "kit" / "kit.exe"
    )
    app_path = (
        kit_root
        / "_build"
        / "windows-x86_64"
        / "release"
        / "apps"
        / "msp.case03.blackwell.kit"
    )
    extension_folder = (
        repository_root / "tests" / "shared_room_runtime" / "kit_exts"
    )
    observer_path = (
        repository_root
        / "tests"
        / "shared_room_runtime"
        / "mdl_compile_probe_observer.py"
    )
    command = [
        str(kit_executable),
        str(app_path),
        "--ext-folder",
        str(extension_folder),
        "--enable",
        "msp.orms.fixture_launcher",
        "--/app/content/emptyStageOnStart=true",
        (
            "--/exts/msp.orms.fixture_launcher/stagePath="
            + stage_path.resolve().as_posix()
        ),
        "--/app/window/enabled=false",
        "--exec",
        str(observer_path),
    ]
    environment = os.environ.copy()
    environment.update(
        {
            "ORMS_COMPILE_PROBE_NAME": probe_name,
            "ORMS_COMPILE_PROBE_STAGE": stage_path.name.lower(),
            "ORMS_COMPILE_PROBE_TIMEOUT_SECONDS": str(fixture_timeout_seconds),
        }
    )
    log_path = temporary_directory / f"{probe_name}.log"
    started_at = time.monotonic()
    process = subprocess.Popen(
        command,
        cwd=kit_root,
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    output_lines: list[str] = []
    output_queue: Queue[str | None] = Queue()

    def _read_output() -> None:
        assert process.stdout is not None
        for line in process.stdout:
            output_queue.put(line)
        output_queue.put(None)

    reader = threading.Thread(target=_read_output, daemon=True)
    reader.start()
    terminal_marker_seen = False
    process_deadline = started_at + process_timeout_seconds
    while time.monotonic() < process_deadline:
        try:
            line = output_queue.get(timeout=0.5)
        except Empty:
            if process.poll() is not None:
                break
            continue
        if line is None:
            break
        output_lines.append(line)
        if "ORMS_COMPILE_PROBE" in line and any(
            f"state={state}" in line
            for state in ("COMPLETE", "TIMEOUT", "OBSERVER_TIMEOUT")
        ):
            terminal_marker_seen = True
            break

    if terminal_marker_seen and process.poll() is None:
        process.terminate()
    try:
        process.wait(timeout=5.0)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5.0)
    while True:
        try:
            line = output_queue.get_nowait()
        except Empty:
            break
        if line is not None:
            output_lines.append(line)
    if not terminal_marker_seen and time.monotonic() >= process_deadline:
        output_lines.append("ORMS_COMPILE_PROBE state=PROCESS_KILLED\n")
    output = "".join(output_lines)
    duration = time.monotonic() - started_at
    log_path.write_text(output, encoding="utf-8")

    marker_lines = [
        line.strip()
        for line in output.splitlines()
        if "ORMS_COMPILE_PROBE" in line
    ]
    for line in marker_lines:
        print(line, flush=True)
    terminal = next(
        (
            state
            for state in ("COMPLETE", "TIMEOUT", "OBSERVER_TIMEOUT")
            if any(f"state={state}" in line for line in marker_lines)
        ),
        (
            "PROCESS_KILLED"
            if "state=PROCESS_KILLED" in output
            else f"EXIT_{process.returncode}"
        ),
    )
    if any(pattern in output for pattern in _COMPILE_ERROR_PATTERNS):
        terminal = "COMPILE_ERROR"
    try:
        stage_path.unlink()
    except FileNotFoundError:
        pass
    return terminal, duration, log_path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--kit-root",
        type=Path,
        default=(Path(Path(__file__).resolve().anchor) / "omniverse_kit_app"),
    )
    parser.add_argument("--fixture-timeout", type=float, default=35.0)
    parser.add_argument("--process-timeout", type=float, default=100.0)
    parser.add_argument(
        "--keep-logs",
        action="store_true",
        help=(
            "Retain complete Kit logs under "
            "tests/shared_room_runtime/compile_probe_logs."
        ),
    )
    parser.add_argument(
        "--probe",
        action="append",
        choices=tuple(_PROBE_EXPRESSIONS),
        help="Run only selected probe(s); may be repeated.",
    )
    arguments = parser.parse_args()
    repository_root = _repository_root()
    probe_names = arguments.probe or list(_PROBE_EXPRESSIONS)
    results: list[tuple[str, str, float, Path | None]] = []

    runtime_parent = repository_root / "tests" / "shared_room_runtime"
    with tempfile.TemporaryDirectory(
        prefix="_mdl_compile_probe_runtime_",
        dir=runtime_parent,
    ) as raw:
        temporary_directory = Path(raw)
        for probe_name in probe_names:
            print(
                "ORMS_COMPILE_BISECTION"
                f" state=PROBE_BEGIN probe={probe_name}",
                flush=True,
            )
            terminal, duration, log_path = _run_probe(
                probe_name,
                repository_root=repository_root,
                temporary_directory=temporary_directory,
                kit_root=arguments.kit_root.resolve(),
                fixture_timeout_seconds=arguments.fixture_timeout,
                process_timeout_seconds=arguments.process_timeout,
            )
            durable_log_path = None
            if arguments.keep_logs:
                log_directory = (
                    repository_root
                    / "tests"
                    / "shared_room_runtime"
                    / "compile_probe_logs"
                )
                log_directory.mkdir(exist_ok=True)
                durable_log_path = log_directory / f"{probe_name}.log"
                durable_log_path.write_text(
                    log_path.read_text(encoding="utf-8"),
                    encoding="utf-8",
                )
            results.append((probe_name, terminal, duration, durable_log_path))
            print(
                "ORMS_COMPILE_BISECTION"
                f" state=PROBE_END probe={probe_name}"
                f" result={terminal} process_seconds={duration:.3f}"
                f" log={durable_log_path or 'not_retained'}",
                flush=True,
            )

    print("ORMS_COMPILE_BISECTION state=SUMMARY", flush=True)
    for probe_name, terminal, duration, log_path in results:
        print(
            f"probe={probe_name} result={terminal}"
            f" process_seconds={duration:.3f}"
            f" log={log_path or 'not_retained'}",
            flush=True,
        )
    return 0 if all(result[1] == "COMPLETE" for result in results) else 2


if __name__ == "__main__":
    sys.exit(main())
