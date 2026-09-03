"""Expose the ORMS runtime through the standard Kit extension lifecycle."""

from __future__ import annotations

from typing import TYPE_CHECKING

import omni.ext

from .runtime_imports import activate_runtime_imports, discover_runtime_root

if TYPE_CHECKING:
    from .service import OrmsRuntimeService


class OrmsRuntimeExtension(omni.ext.IExt):
    """Own one ORMS runtime service for the lifetime of the extension."""

    def __init__(self) -> None:
        super().__init__()
        self._service: OrmsRuntimeService | None = None

    def on_startup(self, ext_id: str) -> None:
        """Register content, Material Library entry, and stage observers."""

        # Installed extensions keep canonical runtime modules under data/. The
        # path must be active before importing the service because its module
        # graph consumes those canonical contracts at import time.
        runtime_root = discover_runtime_root(__file__)
        activate_runtime_imports(runtime_root)
        from .service import OrmsRuntimeService

        self._service = OrmsRuntimeService.discover(ext_id, __file__)
        self._service.start()

    def on_shutdown(self) -> None:
        """Release every ORMS-owned layer, callback, and registration."""

        service, self._service = self._service, None
        if service is not None:
            service.stop()
