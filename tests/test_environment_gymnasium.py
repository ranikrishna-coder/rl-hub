"""Parametric Gymnasium interface compliance tests across environment categories."""
import sys
import os
import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from portal.environment_registry import ENVIRONMENT_REGISTRY, get_environment_class

# Select one representative environment per category
CATEGORY_SAMPLES = {}
for _name, _meta in ENVIRONMENT_REGISTRY.items():
    _cat = _meta.get("category", "unknown")
    if _cat not in CATEGORY_SAMPLES:
        CATEGORY_SAMPLES[_cat] = _name

SAMPLE_ENV_NAMES = list(CATEGORY_SAMPLES.values())


@pytest.mark.parametrize("env_name", SAMPLE_ENV_NAMES)
def test_env_class_loads(env_name):
    """Environment class must load without error."""
    cls = get_environment_class(env_name)
    assert cls is not None, f"Failed to load class for {env_name}"


@pytest.mark.parametrize("env_name", SAMPLE_ENV_NAMES)
def test_env_reset_returns_tuple(env_name):
    """reset() must return (observation, info) per Gymnasium API."""
    cls = get_environment_class(env_name)
    if cls is None:
        pytest.skip(f"Cannot load {env_name}")
    env = cls()
    result = env.reset(seed=42)
    assert isinstance(result, tuple), f"{env_name}.reset() must return tuple"
    assert len(result) == 2, f"{env_name}.reset() must return (obs, info)"
    obs, info = result
    assert obs is not None
    assert isinstance(info, dict)


@pytest.mark.parametrize("env_name", SAMPLE_ENV_NAMES)
def test_env_step_returns_5_tuple(env_name):
    """step() must return (obs, reward, terminated, truncated, info)."""
    cls = get_environment_class(env_name)
    if cls is None:
        pytest.skip(f"Cannot load {env_name}")
    env = cls()
    env.reset(seed=42)
    action = env.action_space.sample()
    result = env.step(action)
    assert len(result) == 5, f"{env_name}.step() must return 5 values, got {len(result)}"
    obs, reward, terminated, truncated, info = result
    assert isinstance(reward, (int, float)), f"{env_name}: reward must be numeric"
    assert isinstance(terminated, bool), f"{env_name}: terminated must be bool"
    assert isinstance(truncated, bool), f"{env_name}: truncated must be bool"
    assert isinstance(info, dict), f"{env_name}: info must be dict"


@pytest.mark.parametrize("env_name", SAMPLE_ENV_NAMES)
def test_env_observation_shape(env_name):
    """Observation should be a numpy array with reasonable shape."""
    cls = get_environment_class(env_name)
    if cls is None:
        pytest.skip(f"Cannot load {env_name}")
    env = cls()
    obs, _ = env.reset(seed=42)
    assert obs is not None, f"{env_name}: observation is None"
    assert hasattr(obs, 'shape'), f"{env_name}: observation has no shape"
    assert len(obs.shape) >= 1, f"{env_name}: observation should be at least 1D"
