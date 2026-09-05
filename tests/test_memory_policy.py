import pytest

from edim_dde_ai.errors import DefinitionError
from edim_dde_ai.session.models import MemoryPolicy


def test_memory_policy_defaults_to_disabled():
    policy = MemoryPolicy.from_raw(None)
    assert policy.strategy == "none"
    assert not policy.enabled


def test_memory_policy_window_enabled():
    policy = MemoryPolicy.from_raw({"strategy": "window", "k": 5})
    assert policy.enabled
    assert policy.k == 5


def test_memory_policy_rejects_invalid_strategy():
    with pytest.raises(DefinitionError, match="memory.strategy"):
        MemoryPolicy.from_raw({"strategy": "unbounded"})
