# SPDX-FileCopyrightText: 2026 Maksim Pospelkov
# SPDX-License-Identifier: MIT
"""Traverse composed stage prims with an explicit instance-proxy policy."""

from __future__ import annotations

from collections.abc import Iterator

from pxr import Usd


def iter_composed_prims(
    stage: Usd.Stage,
    *,
    include_instance_proxies: bool = False,
) -> Iterator[Usd.Prim]:
    """Yield ordinary prims and, when requested, instance-proxy descendants."""

    for prim in stage.Traverse():
        yield prim
        if not include_instance_proxies or not prim.IsInstance():
            continue
        for proxy in Usd.PrimRange(
            prim,
            Usd.TraverseInstanceProxies(),
        ):
            if proxy.GetPath() != prim.GetPath():
                yield proxy
