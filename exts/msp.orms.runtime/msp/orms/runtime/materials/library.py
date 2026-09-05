# SPDX-FileCopyrightText: 2026 Maksim Pospelkov
# SPDX-License-Identifier: MIT
"""Register ORMS MDL content and one reversible Material Library entry."""

from __future__ import annotations

from collections.abc import Callable

from ..resources import (
    MATERIAL_SOURCE_ASSET,
    MATERIAL_SUBIDENTIFIER,
    ResourceLayout,
)
from .mdl_registration import deregister_mdl_content, register_mdl_content
from .visibility import MaterialVisibilityOwner

_MATERIAL_GROUP = "ORMS"
_MATERIAL_DISPLAY_NAME = "Omniverse Room Map Shader"


class MaterialLibraryRegistration:
    """Own the MDL content and Material Library item added by ORMS."""

    def __init__(
        self,
        *,
        register_content: Callable[[str, str], list[str]] | None = None,
        deregister_content: Callable[[str, list[str]], bool] | None = None,
        add_material: Callable[..., bool] | None = None,
        remove_material: Callable[[str, str], bool] | None = None,
        visibility_owner: MaterialVisibilityOwner | None = None,
    ) -> None:
        self._register_content = register_content
        self._deregister_content = deregister_content
        self._add_material = add_material
        self._remove_material = remove_material
        self._visibility_owner = visibility_owner
        self._extension_name = ""
        self._registered_content: list[str] = []
        self._material_entry_active = False

    def _load_kit_apis(self) -> None:
        if self._register_content is not None:
            return
        import omni.kit.material.library as material_library

        self._register_content = register_mdl_content
        self._deregister_content = deregister_mdl_content
        self._add_material = (
            material_library.add_usd_source_asset_path_to_mtl_lib
        )
        self._remove_material = (
            material_library.remove_usd_source_asset_path_from_mtl_lib
        )
        self._visibility_owner = MaterialVisibilityOwner()

    def start(self, extension_name: str, resources: ResourceLayout) -> None:
        """Register resolvable MDL content before exposing the material entry."""

        if self._registered_content or self._material_entry_active:
            return
        self._load_kit_apis()
        register_content = self._register_content
        deregister_content = self._deregister_content
        add_material = self._add_material
        remove_material = self._remove_material
        if any(
            callback is None
            for callback in (
                register_content,
                deregister_content,
                add_material,
                remove_material,
            )
        ):
            raise RuntimeError(
                "The host did not provide the Material Library APIs"
            )

        registered = register_content(
            extension_name,
            str(resources.mdl_root.resolve()),
        )
        if not registered:
            raise RuntimeError("Could not register the ORMS MDL content path")
        self._extension_name = extension_name
        self._registered_content = list(registered)
        try:
            if self._visibility_owner is not None:
                self._visibility_owner.start(_MATERIAL_DISPLAY_NAME)
            add_material(
                MATERIAL_SOURCE_ASSET,
                MATERIAL_SUBIDENTIFIER,
                _MATERIAL_GROUP,
                display_name=_MATERIAL_DISPLAY_NAME,
            )
            self._material_entry_active = True
            # Kit rebuilds from the source-asset setting once its MDL cache is
            # ready. A synchronous refresh here breaks Material Library 3.1.2.
        except Exception:
            self.stop()
            raise

    def stop(self) -> None:
        """Remove the library entry and MDL content owned by this instance."""

        try:
            if self._visibility_owner is not None:
                self._visibility_owner.stop()
            if (
                self._material_entry_active
                and self._remove_material is not None
            ):
                self._remove_material(
                    MATERIAL_SOURCE_ASSET,
                    MATERIAL_SUBIDENTIFIER,
                )
        finally:
            self._material_entry_active = False
            registered_content, self._registered_content = (
                self._registered_content,
                [],
            )
            extension_name, self._extension_name = self._extension_name, ""
            if registered_content and self._deregister_content is not None:
                self._deregister_content(
                    extension_name,
                    registered_content,
                )
