"""Tests for ECC reasoning."""
import os

import pytest

from ADAM.core.config import reset_settings, get_settings
from ADAM.ecc.reasoning import ECCReasoning


@pytest.fixture()
def reasoning():
    return ECCReasoning()


@pytest.mark.asyncio
async def test_reason_returns_insights(reasoning):
    context = {"graph_context": True, "vector_context": False}
    result = await reasoning.reason("test objective", context)
    assert result["objective"] == "test objective"
    assert "insights" in result
    assert "reasoning" in result
