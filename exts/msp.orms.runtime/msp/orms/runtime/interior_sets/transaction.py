"""Define structural Interior Set Apply outcomes and rollback failures."""

from __future__ import annotations

from dataclasses import dataclass

from msp.orms.interior_sets.contracts import InteriorSetCollection


@dataclass(frozen=True)
class InteriorSetApplyResult:
    """Report one complete structural settings/runtime transaction."""

    collection: InteriorSetCollection
    rebuild_requested: bool
    applied_revision: int
    draft_revision: int
    status: str


class InteriorSetRollbackError(RuntimeError):
    """Report that settings could not follow runtime back to prior state."""

    def __init__(
        self,
        runtime_error: Exception,
        rollback_error: Exception,
    ) -> None:
        super().__init__(
            "Interior Set runtime rebuild and persistent rollback failed: "
            f"runtime={runtime_error!r}; rollback={rollback_error!r}"
        )
        self.runtime_error = runtime_error
        self.rollback_error = rollback_error
