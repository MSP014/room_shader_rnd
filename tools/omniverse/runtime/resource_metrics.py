"""Collect low-rate host, Hydra, and renderer resource snapshots."""

from __future__ import annotations

import ctypes
import sys
from typing import Any

_RTX_CUTOUT_OPT_IN_ATTRIBUTE = "omni:rtx:enableCutoutOpacity"
_MDL_ENABLE_OPACITY_INPUT = "inputs:enable_opacity"


def _renderer_snapshot(
    *,
    settings: Any | None = None,
    stage: Any | None = None,
) -> dict[str, object]:
    """Report renderer mode and runtime cutout classification at low rate."""

    try:
        if settings is None:
            import carb.settings

            settings = carb.settings.get_settings()
        if stage is None:
            import omni.usd

            stage = omni.usd.get_context().get_stage()

        setting_paths = {
            "renderer_mode": "/rtx/rendermode",
            "fractional_cutout_opacity": (
                "/rtx/pathtracing/fractionalCutoutOpacity"
            ),
            "opacity_override": ("/rtx/material/omniRtxEnableOpacityOverride"),
        }
        details: dict[str, object] = {
            name: (
                value if (value := settings.get(path)) is not None else "unset"
            )
            for name, path in setting_paths.items()
        }
        if stage is None:
            details.update(
                {
                    "runtime_material_count": 0,
                    "cutout_contract_applicable_material_count": 0,
                    "cutout_opt_in_material_count": 0,
                    "cutout_opt_in_complete": False,
                    "cutout_opt_in_values": "stage_unavailable",
                    "mdl_enable_opacity_material_count": 0,
                    "mdl_enable_opacity_complete": False,
                    "mdl_enable_opacity_values": "stage_unavailable",
                }
            )
            return details

        looks = stage.GetPrimAtPath("/__ORMSRuntime/Looks")
        materials = (
            tuple(
                child
                for child in looks.GetChildren()
                if child.GetTypeName() == "Material"
            )
            if looks and looks.IsValid()
            else ()
        )
        cutout_contract_paths = set()
        values = {}
        mdl_enable_opacity_values = {}
        for material in materials:
            material_path = str(material.GetPath())
            shader = material.GetChild("Shader")
            enable_opacity = shader.GetAttribute(_MDL_ENABLE_OPACITY_INPUT)
            if enable_opacity:
                cutout_contract_paths.add(material_path)
                values[material_path] = material.GetAttribute(
                    _RTX_CUTOUT_OPT_IN_ATTRIBUTE
                ).Get()
                mdl_enable_opacity_values[material_path] = enable_opacity.Get()
            else:
                values[material_path] = "not_applicable"
                mdl_enable_opacity_values[material_path] = "not_applicable"
        enabled_count = sum(value is True for value in values.values())
        mdl_enabled_count = sum(
            value is True for value in mdl_enable_opacity_values.values()
        )
        details.update(
            {
                "runtime_material_count": len(materials),
                "cutout_contract_applicable_material_count": len(
                    cutout_contract_paths
                ),
                "cutout_opt_in_material_count": enabled_count,
                "cutout_opt_in_complete": bool(materials)
                and enabled_count == len(cutout_contract_paths),
                "cutout_opt_in_values": values or "no_runtime_materials",
                "mdl_enable_opacity_material_count": mdl_enabled_count,
                "mdl_enable_opacity_complete": bool(materials)
                and mdl_enabled_count == len(cutout_contract_paths),
                "mdl_enable_opacity_values": (
                    mdl_enable_opacity_values or "no_runtime_materials"
                ),
            }
        )
        return details
    except Exception as error:
        return {"renderer_metrics": f"unavailable: {error!r}"}


def _windows_memory_snapshot() -> dict[str, object]:
    """Return process and host memory counters without a third-party module."""

    if sys.platform != "win32":
        return {"host_memory_metrics": "unsupported_platform"}

    class _ProcessMemoryCountersEx(ctypes.Structure):
        _fields_ = [
            ("cb", ctypes.c_ulong),
            ("PageFaultCount", ctypes.c_ulong),
            ("PeakWorkingSetSize", ctypes.c_size_t),
            ("WorkingSetSize", ctypes.c_size_t),
            ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
            ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
            ("PagefileUsage", ctypes.c_size_t),
            ("PeakPagefileUsage", ctypes.c_size_t),
            ("PrivateUsage", ctypes.c_size_t),
        ]

    class _MemoryStatusEx(ctypes.Structure):
        _fields_ = [
            ("dwLength", ctypes.c_ulong),
            ("dwMemoryLoad", ctypes.c_ulong),
            ("ullTotalPhys", ctypes.c_ulonglong),
            ("ullAvailPhys", ctypes.c_ulonglong),
            ("ullTotalPageFile", ctypes.c_ulonglong),
            ("ullAvailPageFile", ctypes.c_ulonglong),
            ("ullTotalVirtual", ctypes.c_ulonglong),
            ("ullAvailVirtual", ctypes.c_ulonglong),
            ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
        ]

    gib = float(1024**3)
    details: dict[str, object] = {}
    try:
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        psapi = ctypes.WinDLL("psapi", use_last_error=True)
        get_current_process = kernel32.GetCurrentProcess
        get_current_process.argtypes = []
        get_current_process.restype = ctypes.c_void_p
        get_process_memory_info = psapi.GetProcessMemoryInfo
        get_process_memory_info.argtypes = [
            ctypes.c_void_p,
            ctypes.POINTER(_ProcessMemoryCountersEx),
            ctypes.c_ulong,
        ]
        get_process_memory_info.restype = ctypes.c_int

        counters = _ProcessMemoryCountersEx()
        counters.cb = ctypes.sizeof(counters)
        success = get_process_memory_info(
            get_current_process(),
            ctypes.byref(counters),
            counters.cb,
        )
        if success:
            details.update(
                {
                    "process_working_set_gib": round(
                        counters.WorkingSetSize / gib,
                        3,
                    ),
                    "process_private_commit_gib": round(
                        counters.PrivateUsage / gib,
                        3,
                    ),
                }
            )
        else:
            details["process_memory_error"] = (
                "GetProcessMemoryInfo failed: "
                f"winerror={ctypes.get_last_error()}"
            )
    except Exception as error:
        details["process_memory_error"] = repr(error)

    try:
        if "kernel32" not in locals():
            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        global_memory_status = kernel32.GlobalMemoryStatusEx
        global_memory_status.argtypes = [ctypes.POINTER(_MemoryStatusEx)]
        global_memory_status.restype = ctypes.c_int
        memory = _MemoryStatusEx()
        memory.dwLength = ctypes.sizeof(memory)
        if global_memory_status(ctypes.byref(memory)):
            details.update(
                {
                    "system_available_memory_gib": round(
                        memory.ullAvailPhys / gib,
                        3,
                    ),
                    "system_memory_load_percent": int(memory.dwMemoryLoad),
                }
            )
        else:
            details["system_memory_error"] = (
                "GlobalMemoryStatusEx failed: "
                f"winerror={ctypes.get_last_error()}"
            )
    except Exception as error:
        details["system_memory_error"] = repr(error)
    return details


def _hydra_memory_snapshot() -> dict[str, object]:
    """Read public Hydra device counters when that extension is available."""

    try:
        import omni.hydra.engine.stats as engine_stats

        devices = engine_stats.get_device_info(0)
        if not devices:
            return {"gpu_memory_metrics": "no_device"}
        device = devices[0]
        memory_fields = {
            str(name): value
            for name, value in device.items()
            if "memory" in str(name).lower() or "budget" in str(name).lower()
        }
        details: dict[str, object] = {
            "gpu_device": device.get("description", "unavailable"),
            "gpu_memory_fields": memory_fields or "unavailable",
        }
        total_fields = {
            str(item.get("category", "unknown")): item.get("size")
            for item in engine_stats.get_mem_stats()
            if "total" in str(item.get("category", "")).lower()
        }
        details["hydra_total_memory_fields"] = total_fields or "unavailable"
        return details
    except Exception as error:
        return {"gpu_memory_metrics": f"unavailable: {error!r}"}


def _resource_snapshot() -> dict[str, object]:
    details = _windows_memory_snapshot()
    details.update(_hydra_memory_snapshot())
    details.update(_renderer_snapshot())
    return details
