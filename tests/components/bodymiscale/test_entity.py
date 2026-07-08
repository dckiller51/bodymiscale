"""Tests for bodymiscale entity.py."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from custom_components.bodymiscale.entity import BodyScaleBaseEntity
from custom_components.bodymiscale.metrics import BodyScaleMetricsHandler

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_handler(
    impedance_mode: str = "none",
    name: str = "Alice",
) -> MagicMock:
    """Return a minimal mock BodyScaleMetricsHandler."""
    handler = MagicMock(spec=BodyScaleMetricsHandler)
    handler.config = {
        "name": name,
        "impedance_mode": impedance_mode,
    }
    handler.subscribe = MagicMock(return_value=lambda: None)
    return handler


# ===========================================================================
# BodyScaleBaseEntity
# ===========================================================================


def test_entity_description_missing_raises() -> None:
    """BodyScaleBaseEntity without entity_description must raise ValueError."""
    handler = _make_handler()

    class _BadEntity(BodyScaleBaseEntity):
        pass  # no entity_description class var, none passed

    with pytest.raises(ValueError, match="entity_description"):
        _BadEntity(handler)
