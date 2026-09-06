# SPDX-FileCopyrightText: 2026 Maksim Pospelkov
# SPDX-License-Identifier: MIT
"""Record Phase-5 source integrity and bounded runtime-cost evidence."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from msp.orms.scene.resource_metrics import _resource_snapshot
from msp.orms.scene.source_integrity import (
    StageSourceState,
    capture_stage_source_state,
    source_integrity_details,
)
from msp.orms.scene.status_log import log_room_map_status, log_room_map_warning
from pxr import Sdf, Usd


def _runtime_layers(stage: Usd.Stage) -> tuple[Any, ...]:
    layers = []
    for identifier in stage.GetSessionLayer().subLayerPaths:
        if "orms_" not in identifier.casefold():
            continue
        layer = Sdf.Layer.Find(identifier)
        if layer is not None:
            layers.append(layer)
    return tuple(layers)


def _layer_spec_paths(layer: Any) -> tuple[str, ...]:
    paths: list[str] = []
    layer.Traverse(
        Sdf.Path.absoluteRootPath,
        lambda path: paths.append(str(path)),
    )
    return tuple(paths)


def runtime_structure_details(stage: Usd.Stage) -> dict[str, object]:
    """Count temporary layers, material specs, instances, and USD prototypes."""

    runtime_layers = _runtime_layers(stage)
    spec_paths = tuple(
        path for layer in runtime_layers for path in _layer_spec_paths(layer)
    )
    material_paths = set()
    for path in spec_paths:
        prim_path = path.split(".", 1)[0]
        parts = prim_path.split("/")
        for index, part in enumerate(parts):
            part_key = part.casefold()
            if part_key == "ormsroommapsingle" or (
                part_key.startswith("roommapx") and part_key[8:].isdigit()
            ):
                material_paths.add("/".join(parts[: index + 1]))
                break
    return {
        "runtime_layer_count": len(runtime_layers),
        "runtime_spec_count": len(spec_paths),
        "runtime_material_spec_count": len(material_paths),
        "native_instance_count": sum(
            1 for prim in stage.Traverse() if prim.IsInstance()
        ),
        "usd_prototype_count": len(stage.GetPrototypes()),
        "point_instancer_count": sum(
            1
            for prim in stage.Traverse()
            if prim.GetTypeName() == "PointInstancer"
        ),
    }


class Phase5RuntimeAudit:
    """Own one baseline and log comparable lifecycle samples for one stage."""

    def __init__(
        self,
        stage: Usd.Stage,
        *,
        resource_sampler: Callable[
            [], Mapping[str, object]
        ] = _resource_snapshot,
        log_status: Callable[..., None] = log_room_map_status,
        log_warning: Callable[..., None] = log_room_map_warning,
    ) -> None:
        self._stage = stage
        self._resource_sampler = resource_sampler
        self._log_status = log_status
        self._log_warning = log_warning
        self._baseline: StageSourceState = capture_stage_source_state(stage)
        self._baseline_resources = dict(resource_sampler())
        self._sample_index = 0
        self._first_running_structure: dict[str, object] | None = None
        self._log_status(
            owner="ORMS PHASE 5 AUDIT",
            process="SOURCE AND RESOURCE BASELINE",
            state="CAPTURED",
            details={
                "stage_identifier": self._baseline.root_identifier,
                "source_file_count": len(self._baseline.files),
                "source_file_bytes": sum(
                    item.size for item in self._baseline.files
                ),
                "source_material_digest": self._baseline.material_state[
                    "source_state_digest"
                ],
                "instance_count": len(self._baseline.instance_paths),
                "usd_prototype_count": len(
                    self._baseline.prototype_signatures
                ),
                **self._baseline_resources,
            },
        )

    def owns_stage(self, stage: Usd.Stage) -> bool:
        """Return whether this audit belongs to the exact supplied stage."""

        return self._stage is stage

    def sample(
        self,
        event: str,
        ownership: Mapping[str, object],
    ) -> None:
        """Log one comparable runtime structure and resource measurement."""

        self._sample_index += 1
        structure = runtime_structure_details(self._stage)
        comparable = {
            **structure,
            "runtime_session_count": ownership.get("runtime_session_count", 0),
            "assignment_session_count": ownership.get(
                "assignment_session_count", 0
            ),
            "camera_target_count": ownership.get("camera_target_count", 0),
        }
        classifier_subscription_count = int(
            ownership.get("classifier_subscription_count", 0)
        )
        camera_subscription_count = int(
            ownership.get("camera_subscription_count", 0)
        )
        camera_registered_observer_count = int(
            ownership.get("camera_registered_observer_count", 0)
        )
        if event in {"STARTED", "RESTARTED", "RESUMED"}:
            if self._first_running_structure is None:
                self._first_running_structure = dict(comparable)
            matches_first_running: object = (
                comparable == self._first_running_structure
            )
        else:
            matches_first_running = "not_applicable"
        resources = dict(self._resource_sampler())
        details = {
            "sample_index": self._sample_index,
            "event": event,
            **comparable,
            "classifier_subscription_count": classifier_subscription_count,
            "camera_subscription_count": camera_subscription_count,
            "camera_registered_observer_count": (
                camera_registered_observer_count
            ),
            "camera_update_callback_count": int(
                ownership.get("camera_update_callback_count", 0)
            ),
            "camera_successful_update_count": int(
                ownership.get("camera_successful_update_count", 0)
            ),
            "callback_counts_within_expected_bounds": (
                classifier_subscription_count <= 2
                and camera_subscription_count <= 1
                and camera_registered_observer_count <= 1
            ),
            "structure_matches_first_running_sample": matches_first_running,
            **resources,
        }
        for name in (
            "process_working_set_gib",
            "process_private_commit_gib",
        ):
            baseline_value = self._baseline_resources.get(name)
            current_value = resources.get(name)
            if isinstance(baseline_value, (int, float)) and isinstance(
                current_value, (int, float)
            ):
                details[f"{name}_delta"] = round(
                    float(current_value) - float(baseline_value), 3
                )
        self._log_status(
            owner="ORMS PHASE 5 AUDIT",
            process="LIFECYCLE RESOURCE SAMPLE",
            state=event,
            details=details,
        )

    def finish(self, event: str, ownership: Mapping[str, object]) -> None:
        """Compare the restored stage with the baseline and release the audit."""

        restored = capture_stage_source_state(self._stage)
        integrity = source_integrity_details(self._baseline, restored)
        structure = runtime_structure_details(self._stage)
        runtime_ownership_cleared = all(
            int(value) == 0
            for value in (
                structure["runtime_layer_count"],
                structure["runtime_spec_count"],
                structure["runtime_material_spec_count"],
                ownership.get("runtime_session_count", 0),
                ownership.get("classifier_subscription_count", 0),
                ownership.get("camera_subscription_count", 0),
                ownership.get("camera_registered_observer_count", 0),
                ownership.get("assignment_session_count", 0),
                ownership.get("camera_target_count", 0),
            )
        )
        details = {
            "event": event,
            **integrity,
            **structure,
            "runtime_ownership_cleared": runtime_ownership_cleared,
            **dict(self._resource_sampler()),
        }
        passed = bool(integrity["source_integrity_passed"]) and (
            runtime_ownership_cleared
        )
        sink = self._log_status if passed else self._log_warning
        sink(
            owner="ORMS PHASE 5 AUDIT",
            process="RESTORED SOURCE COMPARISON",
            state="PASSED" if passed else "FAILED",
            details=details,
        )
