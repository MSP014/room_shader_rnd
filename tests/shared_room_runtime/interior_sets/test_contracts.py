# SPDX-FileCopyrightText: 2026 Maksim Pospelkov
# SPDX-License-Identifier: MIT
"""Protect Interior Set identity, ordering, and draft semantics."""

import pytest
from msp.orms.interior_sets.contracts import (
    DEFAULT_INTERIOR_SET_ID,
    InteriorSetCollection,
    InteriorSetConfig,
    InteriorSetTransaction,
    runtime_set_token,
)

KITCHENS_ID = "11111111-1111-1111-1111-111111111111"
SHOPS_ID = "22222222-2222-2222-2222-222222222222"


def test_add_inherits_default_materials_but_not_structure():
    configured = InteriorSetCollection.default_only(
        (("glass_roughness", 0.25),)
    ).add(set_id=KITCHENS_ID)

    kitchens = configured.by_id(KITCHENS_ID)

    assert kitchens.material_values == (("glass_roughness", 0.25),)
    assert kitchens.selectors == ()
    assert kitchens.atlas_directories == ("", "", "", "")
    assert runtime_set_token(KITCHENS_ID) == (
        "Set_11111111111111111111111111111111"
    )


def test_duplicate_copies_editable_values_but_uses_new_identity():
    kitchens = InteriorSetConfig(
        set_id=KITCHENS_ID,
        name="Kitchens",
        selectors=("*/Kitchens_Windows",),
        atlas_directories=("x1", "x2", "x3", "x4"),
        material_values=(("glass_roughness", 0.3),),
    )
    configured = InteriorSetCollection(
        (InteriorSetCollection.default_only().default, kitchens)
    )

    duplicated = configured.duplicate(KITCHENS_ID, set_id=SHOPS_ID)

    assert duplicated.sets[2].set_id == SHOPS_ID
    assert duplicated.sets[2].name == "Kitchens"
    assert duplicated.sets[2].selectors == kitchens.selectors
    assert duplicated.sets[2].material_values == kitchens.material_values


def test_blank_names_use_ordered_labels_without_becoming_identity():
    configured = InteriorSetCollection.default_only().add(set_id=KITCHENS_ID)

    assert configured.label_for(DEFAULT_INTERIOR_SET_ID) == "ORMS 1"
    assert configured.label_for(KITCHENS_ID) == "ORMS 2"
    assert configured.by_id(KITCHENS_ID).set_id == KITCHENS_ID


def test_default_cannot_be_removed_or_reordered():
    configured = InteriorSetCollection.default_only()

    with pytest.raises(ValueError, match="cannot be removed"):
        configured.remove(DEFAULT_INTERIOR_SET_ID)
    with pytest.raises(ValueError, match="cannot be reordered"):
        configured.move(DEFAULT_INTERIOR_SET_ID, 1)


def test_transaction_keeps_structural_changes_local_until_accept():
    applied = InteriorSetCollection.default_only()
    transaction = InteriorSetTransaction.from_applied(applied)
    candidate = applied.add(set_id=KITCHENS_ID)

    transaction.stage(candidate)

    assert transaction.dirty
    assert transaction.applied_revision == 0
    assert transaction.draft_revision == 1
    assert transaction.applied == applied
    assert transaction.draft == candidate
    assert transaction.revert() == applied
    assert not transaction.dirty
    assert transaction.applied_revision == 0
    assert transaction.draft_revision == 0


def test_transaction_revision_advances_only_for_distinct_drafts():
    applied = InteriorSetCollection.default_only()
    transaction = InteriorSetTransaction.from_applied(applied)
    candidate = applied.add(set_id=KITCHENS_ID)

    transaction.stage(candidate)
    transaction.stage(candidate)
    transaction.accept()

    assert transaction.applied_revision == 1
    assert transaction.draft_revision == 1
    assert not transaction.dirty
