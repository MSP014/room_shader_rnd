"""Expose the ORMS runtime through the standard Kit extension lifecycle."""

import omni.ext

from .service import OrmsRuntimeService


class OrmsRuntimeExtension(omni.ext.IExt):
    """Own one ORMS runtime service for the lifetime of the extension."""

    def __init__(self) -> None:
        super().__init__()
        self._service: OrmsRuntimeService | None = None

    def on_startup(self, ext_id: str) -> None:
        """Register content, Material Library entry, and stage observers."""

        self._service = OrmsRuntimeService.discover(ext_id, __file__)
        self._service.start()

    def on_shutdown(self) -> None:
        """Release every ORMS-owned layer, callback, and registration."""

        service, self._service = self._service, None
        if service is not None:
            service.stop()
