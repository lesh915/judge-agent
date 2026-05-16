from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Optional

CONFIG_DIR_ENV = "JUDGE_CONFIG_DIR"


def default_config_dir() -> Path:
    """Return the bundled file-based config directory.

    Layout is `judgeagent/judge_agent/config` next to the `core` package. The
    directory can be overridden with JUDGE_CONFIG_DIR so deployments can mount
    environment-specific config without changing code.
    """
    return Path(__file__).resolve().parents[1] / "config"


def config_dir() -> Path:
    override = os.getenv(CONFIG_DIR_ENV)
    return Path(override).expanduser().resolve() if override else default_config_dir()


def _read_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError(f"config file must contain a JSON object: {path}")
    return data


@lru_cache(maxsize=None)
def load_config(name: str, *, config_dir_override: Optional[str] = None) -> Dict[str, Any]:
    base = Path(config_dir_override).expanduser().resolve() if config_dir_override else config_dir()
    path = base / name
    if not path.exists():
        raise FileNotFoundError(f"config file not found: {path}")
    return _read_json(path)


def app_config() -> Dict[str, Any]:
    return load_config("app.json")


def detector_rules_config() -> Dict[str, Any]:
    return load_config("detector_rules.json")


def conversation_config() -> Dict[str, Any]:
    return load_config("conversation.json")


def metrics_config() -> Dict[str, Any]:
    return load_config("metrics.json")


def llm_profiles_config() -> Dict[str, Any]:
    return load_config("llm_profiles.json")


def clear_config_cache() -> None:
    load_config.cache_clear()
