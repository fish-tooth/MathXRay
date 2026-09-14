"""Tests for configuration loading and env-var overrides (P0-T03)."""
from __future__ import annotations

import pytest

from src.config import ConfigError, load_config


def _write_yaml(tmp_path, content: str) -> str:
    p = tmp_path / "config.yaml"
    p.write_text(content, encoding="utf-8")
    return str(p)


def _clear_env(monkeypatch) -> None:
    for var in ("HY3_API_KEY", "HY3_BASE_URL", "HY3_MODEL"):
        monkeypatch.delenv(var, raising=False)


@pytest.fixture(autouse=True)
def _isolate_dotenv(monkeypatch) -> None:
    """Keep the real local .env out of tests: load_config must only see the
    environment variables that tests set explicitly."""
    monkeypatch.setattr("src.config.load_dotenv", lambda *a, **k: None)


def test_load_defaults(tmp_path, monkeypatch):
    _clear_env(monkeypatch)
    path = _write_yaml(
        tmp_path,
        "provider:\n  name: hy3\n  base_url: null\n  model: null\n"
        "generation:\n  temperature: 0.0\nrun:\n  seed: 42\n",
    )
    cfg = load_config(path)
    assert cfg.provider["name"] == "hy3"
    assert cfg.base_url is None
    assert cfg.model is None
    assert cfg.api_key == ""
    assert cfg.seed == 42


def test_env_override_api_key(tmp_path, monkeypatch):
    monkeypatch.setenv("HY3_API_KEY", "secret-123")
    path = _write_yaml(tmp_path, "provider:\n  name: hy3\n")
    cfg = load_config(path)
    assert cfg.api_key == "secret-123"
    assert cfg.require_api_key() == "secret-123"


def test_env_override_base_url_and_model(tmp_path, monkeypatch):
    monkeypatch.setenv("HY3_BASE_URL", "https://example.com/v1")
    monkeypatch.setenv("HY3_MODEL", "hy3-model")
    path = _write_yaml(tmp_path, "provider:\n  name: hy3\n  base_url: null\n  model: null\n")
    cfg = load_config(path)
    assert cfg.base_url == "https://example.com/v1"
    assert cfg.model == "hy3-model"


def test_missing_api_key_raises(tmp_path, monkeypatch):
    _clear_env(monkeypatch)
    path = _write_yaml(tmp_path, "provider:\n  name: hy3\n")
    cfg = load_config(path)
    with pytest.raises(ConfigError):
        cfg.require_api_key()


def test_missing_config_file_raises(tmp_path):
    with pytest.raises(ConfigError):
        load_config(tmp_path / "does_not_exist.yaml")


def test_empty_env_value_does_not_override(tmp_path, monkeypatch):
    monkeypatch.setenv("HY3_API_KEY", "")
    path = _write_yaml(tmp_path, "provider:\n  name: hy3\n")
    cfg = load_config(path)
    assert cfg.api_key == ""
